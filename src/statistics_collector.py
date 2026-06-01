"""
Statistics Collector for the Adaptive Network Emulator.

Aggregates metrics over rolling time windows and tracks protocol/layer
distribution statistics.

Validates: Requirements 7.6, 7.8
"""

import time
import statistics
from collections import deque
from typing import Dict, List, Optional, Deque
from dataclasses import dataclass, field

from src.traffic_analyzer import CapturedPacket
from src.metrics_calculator import MetricsCalculator


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class WindowStats:
    """Statistics calculated over a specific time window."""
    window_seconds: float
    packet_count: int
    bytes_total: int
    throughput_bps: float
    latency_mean_ms: float
    latency_median_ms: float
    latency_p95_ms: float
    loss_percentage: float
    retransmissions: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProtocolDistribution:
    """Protocol distribution statistics (TCP/UDP/ICMP percentages)."""
    tcp_count: int
    udp_count: int
    icmp_count: int
    other_count: int
    total: int
    tcp_pct: float
    udp_pct: float
    icmp_pct: float
    other_pct: float


@dataclass
class LayerProcessingStats:
    """Per-layer processing time statistics."""
    layer_name: str
    packet_count: int
    mean_ms: float
    max_ms: float
    total_ms: float


# Standard rolling window durations in seconds
WINDOWS = {"1s": 1, "10s": 10, "60s": 60, "5min": 300}


# ─────────────────────────────────────────────
# StatisticsCollector
# ─────────────────────────────────────────────

class StatisticsCollector:
    """
    Aggregates network metrics over multiple rolling time windows.

    Maintains a sliding buffer of CapturedPacket objects and recomputes
    statistics on demand for each window (1s, 10s, 60s, 5min).

    Also tracks:
    - Protocol distribution (TCP / UDP / ICMP percentages)
    - Per-layer processing times

    Validates: Requirements 7.6, 7.8
    """

    def __init__(self, max_buffer: int = 100_000):
        self._buffer: Deque[CapturedPacket] = deque(maxlen=max_buffer)
        self._calculator = MetricsCalculator()
        self._layer_times: Dict[str, List[float]] = {}

    # ── Packet ingestion ──────────────────────────────────────────────────

    def add_packet(self, packet: CapturedPacket) -> None:
        """Add a single packet to the rolling buffer."""
        self._buffer.append(packet)
        # Record per-layer processing time if present in headers
        for layer_name, layer_data in packet.headers.items():
            if isinstance(layer_data, dict) and "processing_time_ms" in layer_data:
                self._layer_times.setdefault(layer_name, []).append(
                    float(layer_data["processing_time_ms"])
                )

    def add_packets(self, packets: List[CapturedPacket]) -> None:
        """Add multiple packets at once."""
        for pkt in packets:
            self.add_packet(pkt)

    # ── Rolling window stats ──────────────────────────────────────────────

    def get_window_stats(self, window_seconds: float) -> WindowStats:
        """
        Calculate statistics for the most recent window_seconds of traffic.

        Validates: Requirement 7.6
        """
        now = time.time()
        cutoff = now - window_seconds
        window_packets = [p for p in self._buffer if p.send_time >= cutoff]

        if not window_packets:
            return WindowStats(
                window_seconds=window_seconds, packet_count=0, bytes_total=0,
                throughput_bps=0.0, latency_mean_ms=0.0, latency_median_ms=0.0,
                latency_p95_ms=0.0, loss_percentage=0.0, retransmissions=0,
            )

        throughput = self._calculator.calculate_throughput(window_packets, time_interval_s=window_seconds)
        latency    = self._calculator.calculate_latency(window_packets)
        loss       = self._calculator.calculate_packet_loss(window_packets)
        retx       = self._calculator.calculate_retransmissions(window_packets)

        return WindowStats(
            window_seconds=window_seconds,
            packet_count=len(window_packets),
            bytes_total=sum(p.size_bytes for p in window_packets),
            throughput_bps=throughput.throughput_bps,
            latency_mean_ms=latency.mean_ms,
            latency_median_ms=latency.median_ms,
            latency_p95_ms=latency.p95_ms,
            loss_percentage=loss.loss_percentage,
            retransmissions=retx.retransmission_count,
        )

    def get_all_window_stats(self) -> Dict[str, WindowStats]:
        """Calculate stats for all standard rolling windows (1s/10s/60s/5min)."""
        return {label: self.get_window_stats(secs) for label, secs in WINDOWS.items()}

    # ── Protocol distribution ─────────────────────────────────────────────

    def get_protocol_distribution(
        self, packets: Optional[List[CapturedPacket]] = None
    ) -> ProtocolDistribution:
        """
        Calculate TCP/UDP/ICMP distribution percentages.

        Validates: Requirement 7.8
        """
        source = packets if packets is not None else list(self._buffer)
        total  = len(source)

        if total == 0:
            return ProtocolDistribution(
                tcp_count=0, udp_count=0, icmp_count=0, other_count=0,
                total=0, tcp_pct=0.0, udp_pct=0.0, icmp_pct=0.0, other_pct=0.0,
            )

        tcp   = sum(1 for p in source if p.protocol.upper() == "TCP")
        udp   = sum(1 for p in source if p.protocol.upper() == "UDP")
        icmp  = sum(1 for p in source if p.protocol.upper() == "ICMP")
        other = total - tcp - udp - icmp

        def pct(n: int) -> float:
            return (n / total) * 100.0

        return ProtocolDistribution(
            tcp_count=tcp, udp_count=udp, icmp_count=icmp, other_count=other,
            total=total,
            tcp_pct=pct(tcp), udp_pct=pct(udp),
            icmp_pct=pct(icmp), other_pct=pct(other),
        )

    # ── Per-layer processing times ────────────────────────────────────────

    def get_layer_processing_stats(self) -> Dict[str, LayerProcessingStats]:
        """Return per-layer processing time statistics."""
        result: Dict[str, LayerProcessingStats] = {}
        for layer_name, times in self._layer_times.items():
            if not times:
                continue
            result[layer_name] = LayerProcessingStats(
                layer_name=layer_name,
                packet_count=len(times),
                mean_ms=statistics.mean(times),
                max_ms=max(times),
                total_ms=sum(times),
            )
        return result

    def clear(self) -> None:
        """Clear the packet buffer and layer timing data."""
        self._buffer.clear()
        self._layer_times.clear()

    def buffer_size(self) -> int:
        """Return current number of packets in the buffer."""
        return len(self._buffer)
