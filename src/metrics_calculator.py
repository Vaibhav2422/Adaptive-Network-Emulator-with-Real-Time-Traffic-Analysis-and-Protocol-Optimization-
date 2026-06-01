"""
Metrics Calculator for the Adaptive Network Emulator.

Calculates throughput, latency, packet loss, retransmissions, and jitter
from a list of CapturedPacket objects produced by TrafficAnalyzer.

Validates: Requirements 7.2, 7.3, 7.4, 7.5
"""

import logging
import statistics
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from src.traffic_analyzer import CapturedPacket

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Result data-classes
# ─────────────────────────────────────────────

@dataclass
class ThroughputResult:
    """
    Result of a throughput calculation.

    Attributes:
        bytes_delivered: Total bytes successfully delivered (recv_time is not None).
        time_interval_s: Time window used for the calculation (seconds).
        throughput_bps:  Throughput in bits per second.
        throughput_Bps:  Throughput in bytes per second.
    """
    bytes_delivered: int
    time_interval_s: float
    throughput_bps: float
    throughput_Bps: float


@dataclass
class LatencyResult:
    """
    Per-packet and aggregate latency statistics.

    Attributes:
        per_packet_ms:    List of individual (recv - send) latencies in ms.
        mean_ms:          Mean latency in ms.
        min_ms:           Minimum latency in ms.
        max_ms:           Maximum latency in ms.
        median_ms:        Median latency in ms.
        p95_ms:           95th-percentile latency in ms.
    """
    per_packet_ms: List[float]
    mean_ms: float
    min_ms: float
    max_ms: float
    median_ms: float
    p95_ms: float


@dataclass
class PacketLossResult:
    """
    Packet-loss statistics for a session.

    Attributes:
        packets_sent:     Total packets sent.
        packets_lost:     Packets that were never received (recv_time is None).
        loss_percentage:  (packets_lost / packets_sent) × 100.
    """
    packets_sent: int
    packets_lost: int
    loss_percentage: float


@dataclass
class RetransmissionResult:
    """
    Retransmission statistics for a session.

    Attributes:
        total_packets:       Total packets in the session.
        retransmission_count: Packets flagged as retransmissions.
        retransmission_rate:  retransmission_count / total_packets (0-1).
    """
    total_packets: int
    retransmission_count: int
    retransmission_rate: float


@dataclass
class JitterResult:
    """
    Jitter (inter-packet delay variation) statistics.

    Attributes:
        per_interval_ms:  List of |latency[i] - latency[i-1]| values in ms.
        mean_jitter_ms:   Mean jitter in ms.
        max_jitter_ms:    Maximum jitter in ms.
        variance_ms2:     Variance of latency values in ms².
    """
    per_interval_ms: List[float]
    mean_jitter_ms: float
    max_jitter_ms: float
    variance_ms2: float


@dataclass
class SessionMetrics:
    """Aggregate metrics for an entire capture session."""
    throughput: ThroughputResult
    latency: LatencyResult
    packet_loss: PacketLossResult
    retransmissions: RetransmissionResult
    jitter: JitterResult


# ─────────────────────────────────────────────
# MetricsCalculator
# ─────────────────────────────────────────────

class MetricsCalculator:
    """
    Calculates network performance metrics from captured packet data.

    All methods are stateless and accept a list of CapturedPacket objects
    so they can be used independently or together via calculate_all().

    Validates: Requirements 7.2 (throughput), 7.3 (latency),
               7.4 (packet loss), 7.5 (retransmissions)
    """

    # ── Throughput ────────────────────────────────────────────────────────

    def calculate_throughput(
        self,
        packets: List[CapturedPacket],
        time_interval_s: Optional[float] = None,
    ) -> ThroughputResult:
        """
        Calculate throughput for a list of packets.

        Throughput = (total bytes successfully delivered) / (time interval)

        Only packets with a non-None recv_time are considered "delivered".
        If time_interval_s is not provided it is inferred as
        (last recv_time − first send_time).

        Args:
            packets:        List of CapturedPacket objects.
            time_interval_s: Explicit time window in seconds (optional).

        Returns:
            ThroughputResult with bytes, interval, and bps / Bps values.

        Validates: Requirement 7.2
        """
        if not packets:
            return ThroughputResult(
                bytes_delivered=0,
                time_interval_s=0.0,
                throughput_bps=0.0,
                throughput_Bps=0.0,
            )

        delivered = [p for p in packets if p.recv_time is not None]
        bytes_delivered = sum(p.size_bytes for p in delivered)

        # Determine time interval
        if time_interval_s is not None:
            interval = time_interval_s
        elif delivered:
            send_times = [p.send_time for p in packets]
            recv_times = [p.recv_time for p in delivered]
            interval = max(recv_times) - min(send_times)
        else:
            interval = 0.0

        if interval <= 0:
            throughput_Bps = 0.0
            throughput_bps = 0.0
        else:
            throughput_Bps = bytes_delivered / interval
            throughput_bps = throughput_Bps * 8

        logger.debug(
            "Throughput: %d bytes / %.6f s = %.2f bps",
            bytes_delivered, interval, throughput_bps,
        )

        return ThroughputResult(
            bytes_delivered=bytes_delivered,
            time_interval_s=interval,
            throughput_bps=throughput_bps,
            throughput_Bps=throughput_Bps,
        )

    # ── Latency ───────────────────────────────────────────────────────────

    def calculate_latency(self, packets: List[CapturedPacket]) -> LatencyResult:
        """
        Calculate per-packet and aggregate latency statistics.

        Latency = receive_timestamp − send_timestamp (in milliseconds).
        Only packets with a non-None recv_time are included.

        Args:
            packets: List of CapturedPacket objects.

        Returns:
            LatencyResult with per-packet values and aggregates.

        Validates: Requirement 7.3
        """
        latencies_ms = [
            (p.recv_time - p.send_time) * 1000.0
            for p in packets
            if p.recv_time is not None
        ]

        if not latencies_ms:
            return LatencyResult(
                per_packet_ms=[],
                mean_ms=0.0,
                min_ms=0.0,
                max_ms=0.0,
                median_ms=0.0,
                p95_ms=0.0,
            )

        sorted_lats = sorted(latencies_ms)
        p95_idx = int(len(sorted_lats) * 0.95)
        p95 = sorted_lats[min(p95_idx, len(sorted_lats) - 1)]

        result = LatencyResult(
            per_packet_ms=latencies_ms,
            mean_ms=statistics.mean(latencies_ms),
            min_ms=min(latencies_ms),
            max_ms=max(latencies_ms),
            median_ms=statistics.median(latencies_ms),
            p95_ms=p95,
        )

        logger.debug(
            "Latency: mean=%.3f ms, min=%.3f ms, max=%.3f ms",
            result.mean_ms, result.min_ms, result.max_ms,
        )
        return result

    # ── Packet Loss ───────────────────────────────────────────────────────

    def calculate_packet_loss(self, packets: List[CapturedPacket]) -> PacketLossResult:
        """
        Calculate packet loss for a session.

        Loss = (packets_lost / packets_sent) × 100
        A packet is "lost" when its recv_time is None.

        Args:
            packets: List of CapturedPacket objects.

        Returns:
            PacketLossResult with sent, lost, and percentage values.

        Validates: Requirement 7.4
        """
        packets_sent = len(packets)
        packets_lost = sum(1 for p in packets if p.recv_time is None)

        if packets_sent == 0:
            loss_pct = 0.0
        else:
            loss_pct = (packets_lost / packets_sent) * 100.0

        logger.debug(
            "Packet loss: %d / %d = %.2f%%",
            packets_lost, packets_sent, loss_pct,
        )

        return PacketLossResult(
            packets_sent=packets_sent,
            packets_lost=packets_lost,
            loss_percentage=loss_pct,
        )

    # ── Retransmissions ───────────────────────────────────────────────────

    def calculate_retransmissions(
        self, packets: List[CapturedPacket]
    ) -> RetransmissionResult:
        """
        Count retransmitted packets in the session.

        A packet is a retransmission when its is_retransmission flag is True.

        Args:
            packets: List of CapturedPacket objects.

        Returns:
            RetransmissionResult with count and rate.

        Validates: Requirement 7.5
        """
        total = len(packets)
        retransmit_count = sum(1 for p in packets if p.is_retransmission)
        rate = retransmit_count / total if total > 0 else 0.0

        logger.debug(
            "Retransmissions: %d / %d (rate=%.4f)",
            retransmit_count, total, rate,
        )

        return RetransmissionResult(
            total_packets=total,
            retransmission_count=retransmit_count,
            retransmission_rate=rate,
        )

    # ── Jitter ────────────────────────────────────────────────────────────

    def calculate_jitter(self, packets: List[CapturedPacket]) -> JitterResult:
        """
        Calculate jitter (inter-packet delay variation).

        Jitter is computed as the mean absolute difference between consecutive
        packet latencies, which models RFC 3550 jitter estimation.

        Variance is the statistical variance of all per-packet latencies.

        Args:
            packets: List of CapturedPacket objects (order matters).

        Returns:
            JitterResult with per-interval jitter, mean, max, and variance.
        """
        latencies_ms = [
            (p.recv_time - p.send_time) * 1000.0
            for p in packets
            if p.recv_time is not None
        ]

        if len(latencies_ms) < 2:
            # variance() requires at least 2 data points — return 0.0 for 0 or 1 packet
            return JitterResult(
                per_interval_ms=[],
                mean_jitter_ms=0.0,
                max_jitter_ms=0.0,
                variance_ms2=0.0,
            )

        intervals = [
            abs(latencies_ms[i] - latencies_ms[i - 1])
            for i in range(1, len(latencies_ms))
        ]

        result = JitterResult(
            per_interval_ms=intervals,
            mean_jitter_ms=statistics.mean(intervals),
            max_jitter_ms=max(intervals),
            variance_ms2=statistics.variance(latencies_ms),
        )

        logger.debug(
            "Jitter: mean=%.3f ms, max=%.3f ms, variance=%.3f ms²",
            result.mean_jitter_ms, result.max_jitter_ms, result.variance_ms2,
        )
        return result

    # ── All-in-one ────────────────────────────────────────────────────────

    def calculate_all(
        self,
        packets: List[CapturedPacket],
        time_interval_s: Optional[float] = None,
    ) -> SessionMetrics:
        """
        Calculate all metrics for a capture session in one call.

        Args:
            packets:         List of CapturedPacket objects.
            time_interval_s: Optional explicit time window for throughput.

        Returns:
            SessionMetrics aggregating all individual results.
        """
        return SessionMetrics(
            throughput=self.calculate_throughput(packets, time_interval_s),
            latency=self.calculate_latency(packets),
            packet_loss=self.calculate_packet_loss(packets),
            retransmissions=self.calculate_retransmissions(packets),
            jitter=self.calculate_jitter(packets),
        )
