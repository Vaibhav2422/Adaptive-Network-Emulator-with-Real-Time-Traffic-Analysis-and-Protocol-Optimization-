"""
Performance Logger for the Adaptive Network Emulator.

Provides structured JSON logging of metrics with ISO 8601 timestamps,
and packet categorization by protocol and layer.

Validates: Requirements 7.6, 7.8
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from src.traffic_analyzer import CapturedPacket
from src.metrics_calculator import MetricsCalculator, SessionMetrics
from src.statistics_collector import StatisticsCollector, WindowStats


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class MetricEntry:
    """
    A single metric log entry with an ISO 8601 timestamp.

    Validates: Requirement 7.6 (every metric has an associated timestamp)
    """
    timestamp: str          # ISO 8601 format
    metric_name: str
    value: Any
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def now_iso() -> str:
        """Return current UTC time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()


@dataclass
class PacketCategory:
    """
    Categorisation result for a single packet.

    Validates: Requirement 7.8
    """
    packet_id: str
    protocol_category: str   # TCP | UDP | ICMP | OTHER
    layer_category: str      # Application | Transport | Network | DataLink | Physical
    timestamp: str           # ISO 8601


# ─────────────────────────────────────────────
# Layer categorisation helper
# ─────────────────────────────────────────────

# Map raw layer strings → canonical category names
_LAYER_MAP: Dict[str, str] = {
    "application": "Application",
    "transport":   "Transport",
    "network":     "Network",
    "data_link":   "DataLink",
    "datalink":    "DataLink",
    "mac":         "DataLink",
    "physical":    "Physical",
}

_PROTOCOL_MAP: Dict[str, str] = {
    "tcp":  "TCP",
    "udp":  "UDP",
    "icmp": "ICMP",
}


def _categorise_protocol(protocol: str) -> str:
    return _PROTOCOL_MAP.get(protocol.lower(), "OTHER")


def _categorise_layer(layer: str) -> str:
    return _LAYER_MAP.get(layer.lower(), layer.capitalize())


# ─────────────────────────────────────────────
# PerformanceLogger
# ─────────────────────────────────────────────

class PerformanceLogger:
    """
    Logs network performance metrics to structured JSON files.

    Features:
    - ISO 8601 timestamps on every log entry           (Req 7.6)
    - Packet categorisation by protocol and layer      (Req 7.8)
    - JSON Lines format (one JSON object per line)
    - In-memory log for testing / programmatic access

    Usage::

        plogger = PerformanceLogger(log_dir="logs/")
        plogger.log_session_metrics(packets)
        plogger.log_packet_categories(packets)
        plogger.flush()
    """

    def __init__(self, log_dir: str = "logs", filename_prefix: str = "metrics"):
        """
        Initialise the PerformanceLogger.

        Args:
            log_dir:          Directory where log files are written.
            filename_prefix:  Prefix for log file names.
        """
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = filename_prefix
        self._calculator = MetricsCalculator()

        # In-memory stores
        self._metric_entries: List[MetricEntry] = []
        self._packet_categories: List[PacketCategory] = []

        # Open log file (JSON Lines)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._log_path = self._log_dir / f"{filename_prefix}_{ts}.jsonl"
        self._log_file = open(self._log_path, "a", encoding="utf-8")

        logger.info("PerformanceLogger writing to %s", self._log_path)

    # ── Metric logging ────────────────────────────────────────────────────

    def log_metric(
        self,
        metric_name: str,
        value: Any,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> MetricEntry:
        """
        Log a single named metric with the current timestamp.

        Args:
            metric_name: Human-readable metric name.
            value:       Metric value (number, string, etc.).
            unit:        Optional unit string (e.g. "bps", "ms", "%").
            tags:        Optional key-value tags for filtering.

        Returns:
            MetricEntry that was recorded.

        Validates: Requirement 7.6 (timestamp association)
        """
        entry = MetricEntry(
            timestamp=MetricEntry.now_iso(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {},
        )
        self._metric_entries.append(entry)
        self._write_json({"type": "metric", **asdict(entry)})
        return entry

    def log_session_metrics(
        self,
        packets: List[CapturedPacket],
        session_id: str = "",
        time_interval_s: Optional[float] = None,
    ) -> SessionMetrics:
        """
        Calculate and log all metrics for a capture session.

        Args:
            packets:         List of CapturedPacket objects.
            session_id:      Optional session label.
            time_interval_s: Optional explicit time window for throughput.

        Returns:
            SessionMetrics containing all calculated metrics.
        """
        metrics = self._calculator.calculate_all(packets, time_interval_s)
        tags = {"session_id": session_id} if session_id else {}

        self.log_metric("throughput_bps",      metrics.throughput.throughput_bps,        "bps",  tags)
        self.log_metric("throughput_Bps",       metrics.throughput.throughput_Bps,         "Bps",  tags)
        self.log_metric("bytes_delivered",      metrics.throughput.bytes_delivered,        "bytes",tags)
        self.log_metric("latency_mean_ms",      metrics.latency.mean_ms,                  "ms",   tags)
        self.log_metric("latency_median_ms",    metrics.latency.median_ms,                "ms",   tags)
        self.log_metric("latency_p95_ms",       metrics.latency.p95_ms,                   "ms",   tags)
        self.log_metric("latency_min_ms",       metrics.latency.min_ms,                   "ms",   tags)
        self.log_metric("latency_max_ms",       metrics.latency.max_ms,                   "ms",   tags)
        self.log_metric("packet_loss_pct",      metrics.packet_loss.loss_percentage,       "%",    tags)
        self.log_metric("packets_sent",         metrics.packet_loss.packets_sent,          "",     tags)
        self.log_metric("packets_lost",         metrics.packet_loss.packets_lost,          "",     tags)
        self.log_metric("retransmissions",      metrics.retransmissions.retransmission_count, "", tags)
        self.log_metric("retransmission_rate",  metrics.retransmissions.retransmission_rate,  "", tags)
        self.log_metric("jitter_mean_ms",       metrics.jitter.mean_jitter_ms,            "ms",   tags)
        self.log_metric("jitter_max_ms",        metrics.jitter.max_jitter_ms,             "ms",   tags)

        return metrics

    def log_window_stats(self, stats: WindowStats, window_label: str = "") -> None:
        """
        Log a WindowStats snapshot.

        Args:
            stats:        WindowStats object.
            window_label: Label string (e.g. "10s").
        """
        tags = {"window": window_label}
        self.log_metric("window_throughput_bps",   stats.throughput_bps,   "bps", tags)
        self.log_metric("window_latency_mean_ms",  stats.latency_mean_ms,  "ms",  tags)
        self.log_metric("window_latency_p95_ms",   stats.latency_p95_ms,   "ms",  tags)
        self.log_metric("window_loss_pct",         stats.loss_percentage,  "%",   tags)
        self.log_metric("window_retransmissions",  stats.retransmissions,  "",    tags)
        self.log_metric("window_packet_count",     stats.packet_count,     "",    tags)

    # ── Packet categorisation ─────────────────────────────────────────────

    def categorise_packet(self, packet: CapturedPacket) -> PacketCategory:
        """
        Categorise a single packet by protocol and layer.

        Args:
            packet: CapturedPacket to categorise.

        Returns:
            PacketCategory with protocol and layer labels.

        Validates: Requirement 7.8
        """
        category = PacketCategory(
            packet_id=packet.packet_id,
            protocol_category=_categorise_protocol(packet.protocol),
            layer_category=_categorise_layer(packet.layer),
            timestamp=MetricEntry.now_iso(),
        )
        self._packet_categories.append(category)
        self._write_json({"type": "packet_category", **asdict(category)})
        return category

    def log_packet_categories(
        self, packets: List[CapturedPacket]
    ) -> List[PacketCategory]:
        """
        Categorise and log a list of packets.

        Args:
            packets: List of CapturedPacket objects.

        Returns:
            List of PacketCategory results.
        """
        return [self.categorise_packet(p) for p in packets]

    # ── Query ─────────────────────────────────────────────────────────────

    def get_metric_entries(self) -> List[MetricEntry]:
        """Return all in-memory metric entries."""
        return list(self._metric_entries)

    def get_packet_categories(self) -> List[PacketCategory]:
        """Return all in-memory packet categories."""
        return list(self._packet_categories)

    def get_log_path(self) -> Path:
        """Return the path of the active log file."""
        return self._log_path

    # ── I/O ───────────────────────────────────────────────────────────────

    def flush(self) -> None:
        """Flush the log file buffer to disk."""
        if not self._log_file.closed:
            self._log_file.flush()

    def close(self) -> None:
        """Flush and close the log file."""
        self.flush()
        if not self._log_file.closed:
            self._log_file.close()

    def read_log_file(self) -> List[Dict]:
        """
        Read and parse the current log file.

        Returns:
            List of parsed JSON objects from the log file.
        """
        self.flush()
        entries = []
        try:
            with open(self._log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Error reading log file: %s", exc)
        return entries

    # ── Helpers ───────────────────────────────────────────────────────────

    def _write_json(self, obj: Dict) -> None:
        """Write a single JSON object as a line to the log file."""
        try:
            self._log_file.write(json.dumps(obj) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write log entry: %s", exc)
