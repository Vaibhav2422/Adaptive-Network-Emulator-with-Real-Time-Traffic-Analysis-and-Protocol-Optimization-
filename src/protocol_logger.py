"""
Comprehensive Logging System for the Adaptive Network Emulator.

Provides hierarchical structured logging per-layer, per-node, and system-wide.
All log entries are JSON-formatted and written to separate component log files.

Validates: Requirement 10.3
"""

import json
import logging
import logging.handlers
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class LogLevel(Enum):
    DEBUG    = "DEBUG"
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


class NetworkLayer(Enum):
    PHYSICAL    = "physical"
    MAC         = "mac"
    DATA_LINK   = "data_link"
    NETWORK     = "network"
    TRANSPORT   = "transport"
    APPLICATION = "application"
    SYSTEM      = "system"


class NetworkCondition(Enum):
    NORMAL      = "normal"
    CONGESTION  = "congestion"
    HIGH_LOSS   = "high_loss"
    HIGH_LATENCY = "high_latency"
    DEGRADED    = "degraded"


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class ProtocolLogEntry:
    """
    A single structured protocol behavior log entry.

    Validates: Requirement 10.3
    """
    entry_id:       str
    timestamp:      str                  # ISO 8601
    layer:          str                  # NetworkLayer value
    node_id:        str
    event_type:     str                  # e.g. "packet_sent", "ack_received"
    condition:      str                  # NetworkCondition value
    level:          str                  # LogLevel value
    message:        str
    metadata:       Dict[str, Any] = field(default_factory=dict)
    protocol:       str = ""
    packet_id:      str = ""
    sequence_num:   int = -1
    window_size:    int = -1
    loss_pct:       float = 0.0
    latency_ms:     float = 0.0


@dataclass
class LayerLogSummary:
    """Summary of log entries for a single layer."""
    layer:          str
    total_entries:  int
    by_level:       Dict[str, int]
    by_condition:   Dict[str, int]
    by_event_type:  Dict[str, int]
    nodes_seen:     List[str]


# ─────────────────────────────────────────────
# JSON log formatter
# ─────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        # Attach any extra fields added via LoggerAdapter / extra={}
        for key in ("layer", "node_id", "event_type", "condition",
                    "protocol", "packet_id", "metadata"):
            if hasattr(record, key):
                obj[key] = getattr(record, key)
        if record.exc_info:
            obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(obj)


# ─────────────────────────────────────────────
# ProtocolLogger  (task 24.1)
# ─────────────────────────────────────────────

class ProtocolLogger:
    """
    Hierarchical structured logging system.

    Features:
    - One log file per network layer  (physical.jsonl, mac.jsonl, …)
    - One system-wide log file        (system.jsonl)
    - Per-node log files              (node_<id>.jsonl)
    - Configurable log level
    - In-memory entry store for querying / export
    - Thread-safe

    Validates: Requirement 10.3
    """

    def __init__(
        self,
        log_dir: str = "logs",
        level: str = LogLevel.INFO.value,
        max_bytes: int = 10 * 1024 * 1024,   # 10 MB per file
        backup_count: int = 3,
    ):
        self._log_dir     = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._level       = getattr(logging, level, logging.INFO)
        self._max_bytes   = max_bytes
        self._backup_count = backup_count

        self._entries: List[ProtocolLogEntry] = []
        self._entry_counter = 0
        self._lock = threading.Lock()

        # stdlib loggers: one per layer + system
        self._loggers: Dict[str, logging.Logger] = {}
        self._node_loggers: Dict[str, logging.Logger] = {}

        for layer in NetworkLayer:
            self._loggers[layer.value] = self._make_logger(
                f"emulator.{layer.value}", f"{layer.value}.jsonl"
            )
        # system logger
        self._loggers["system"] = self._make_logger(
            "emulator.system", "system.jsonl"
        )

    # ── Public logging API ────────────────────────────────────────────────

    def log(
        self,
        layer: str,
        node_id: str,
        event_type: str,
        message: str,
        condition: str = NetworkCondition.NORMAL.value,
        level: str = LogLevel.INFO.value,
        protocol: str = "",
        packet_id: str = "",
        sequence_num: int = -1,
        window_size: int = -1,
        loss_pct: float = 0.0,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProtocolLogEntry:
        """
        Log a protocol behavior event.

        Args:
            layer:        NetworkLayer value string.
            node_id:      ID of the emulator node.
            event_type:   Short event identifier (e.g. "packet_sent").
            message:      Human-readable description.
            condition:    Current NetworkCondition value.
            level:        LogLevel value string.
            protocol:     Protocol name (TCP, UDP, GBN, SR, …).
            packet_id:    Optional packet identifier.
            sequence_num: Sequence number for transport-layer events.
            window_size:  Window size at time of event.
            loss_pct:     Current loss percentage.
            latency_ms:   Current latency in ms.
            metadata:     Additional key-value pairs.

        Returns:
            ProtocolLogEntry stored in memory.

        Validates: Requirement 10.3
        """
        with self._lock:
            self._entry_counter += 1
            entry = ProtocolLogEntry(
                entry_id=f"log_{self._entry_counter}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                layer=layer,
                node_id=node_id,
                event_type=event_type,
                condition=condition,
                level=level,
                message=message,
                metadata=metadata or {},
                protocol=protocol,
                packet_id=packet_id,
                sequence_num=sequence_num,
                window_size=window_size,
                loss_pct=loss_pct,
                latency_ms=latency_ms,
            )
            self._entries.append(entry)

        # Write to the appropriate layer logger
        stdlib_level = getattr(logging, level, logging.INFO)
        logger       = self._get_layer_logger(layer)
        extra        = {
            "layer":      layer,
            "node_id":    node_id,
            "event_type": event_type,
            "condition":  condition,
            "protocol":   protocol,
            "packet_id":  packet_id,
            "metadata":   metadata or {},
        }
        logger.log(stdlib_level, message, extra=extra)

        # Also write to node-specific log
        self._get_node_logger(node_id).log(stdlib_level, message, extra=extra)

        return entry

    # Convenience per-layer methods
    def log_physical(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.PHYSICAL.value, node_id, event_type, message, **kwargs)

    def log_mac(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.MAC.value, node_id, event_type, message, **kwargs)

    def log_data_link(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.DATA_LINK.value, node_id, event_type, message, **kwargs)

    def log_network(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.NETWORK.value, node_id, event_type, message, **kwargs)

    def log_transport(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.TRANSPORT.value, node_id, event_type, message, **kwargs)

    def log_application(self, node_id: str, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.APPLICATION.value, node_id, event_type, message, **kwargs)

    def log_system(self, event_type: str, message: str, **kwargs) -> ProtocolLogEntry:
        return self.log(NetworkLayer.SYSTEM.value, "system", event_type, message, **kwargs)

    # ── Query API ─────────────────────────────────────────────────────────

    def get_entries(
        self,
        layer:     Optional[str] = None,
        node_id:   Optional[str] = None,
        condition: Optional[str] = None,
        level:     Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[ProtocolLogEntry]:
        """Filter in-memory log entries."""
        with self._lock:
            entries = list(self._entries)
        if layer:
            entries = [e for e in entries if e.layer == layer]
        if node_id:
            entries = [e for e in entries if e.node_id == node_id]
        if condition:
            entries = [e for e in entries if e.condition == condition]
        if level:
            entries = [e for e in entries if e.level == level]
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        return entries

    def get_all_entries(self) -> List[ProtocolLogEntry]:
        with self._lock:
            return list(self._entries)

    def get_layer_summary(self, layer: str) -> LayerLogSummary:
        entries = self.get_entries(layer=layer)
        by_level:      Dict[str, int] = {}
        by_condition:  Dict[str, int] = {}
        by_event_type: Dict[str, int] = {}
        nodes: set = set()
        for e in entries:
            by_level[e.level]           = by_level.get(e.level, 0) + 1
            by_condition[e.condition]   = by_condition.get(e.condition, 0) + 1
            by_event_type[e.event_type] = by_event_type.get(e.event_type, 0) + 1
            nodes.add(e.node_id)
        return LayerLogSummary(
            layer=layer,
            total_entries=len(entries),
            by_level=by_level,
            by_condition=by_condition,
            by_event_type=by_event_type,
            nodes_seen=sorted(nodes),
        )

    def get_log_files(self) -> List[Path]:
        """Return paths to all log files created."""
        return sorted(self._log_dir.glob("*.jsonl"))

    def set_level(self, level: str) -> None:
        """Change log level dynamically."""
        stdlib_level = getattr(logging, level, logging.INFO)
        self._level  = stdlib_level
        for lgr in self._loggers.values():
            lgr.setLevel(stdlib_level)
        for lgr in self._node_loggers.values():
            lgr.setLevel(stdlib_level)

    def close(self) -> None:
        """Close all file handlers (required on Windows before deleting log dir)."""
        for lgr in list(self._loggers.values()) + list(self._node_loggers.values()):
            for handler in lgr.handlers[:]:
                handler.flush()
                handler.close()
                lgr.removeHandler(handler)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._entry_counter = 0

    # ── Internal ─────────────────────────────────────────────────────────

    def _make_logger(self, name: str, filename: str) -> logging.Logger:
        lgr = logging.getLogger(name)
        lgr.setLevel(self._level)
        lgr.propagate = False
        if not lgr.handlers:
            path    = self._log_dir / filename
            handler = logging.handlers.RotatingFileHandler(
                path,
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(JSONFormatter())
            lgr.addHandler(handler)
        return lgr

    def _get_layer_logger(self, layer: str) -> logging.Logger:
        if layer not in self._loggers:
            self._loggers[layer] = self._make_logger(
                f"emulator.{layer}", f"{layer}.jsonl"
            )
        return self._loggers[layer]

    def _get_node_logger(self, node_id: str) -> logging.Logger:
        safe = node_id.replace("/", "_").replace("\\", "_")
        if safe not in self._node_loggers:
            self._node_loggers[safe] = self._make_logger(
                f"emulator.node.{safe}", f"node_{safe}.jsonl"
            )
        return self._node_loggers[safe]
