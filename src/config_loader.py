"""
Task 25.1 & 25.2 – Configuration system and startup validation.

Requirements: 11.2, 11.3, 11.5, 11.7
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ─────────────────────────────────────────────────────────────
# Validation error
# ─────────────────────────────────────────────────────────────

@dataclass
class ConfigError:
    field: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        if self.value is not None:
            return f"[{self.field}] {self.message} (got: {self.value!r})"
        return f"[{self.field}] {self.message}"


class ConfigValidationError(Exception):
    """Raised on invalid configuration; carries all errors found."""

    def __init__(self, errors: List[ConfigError]) -> None:
        self.errors = errors
        lines = "\n  - ".join(str(e) for e in errors)
        super().__init__(f"Configuration validation failed:\n  - {lines}")

    def __len__(self) -> int:
        return len(self.errors)


# ─────────────────────────────────────────────────────────────
# Config dataclasses (25.1)
# ─────────────────────────────────────────────────────────────

@dataclass
class NodeConfig:
    node_id: str
    node_type: str          # "sender" | "receiver" | "router"
    position: Optional[Dict[str, float]] = None


@dataclass
class LinkConfig:
    source: str
    target: str
    bandwidth_mbps: float   # > 0
    delay_ms: float         # >= 0
    loss_pct: float         # 0..100


@dataclass
class TopologyConfig:
    nodes: List[NodeConfig]
    links: List[LinkConfig]


@dataclass
class ProtocolConfig:
    protocol: str                           # "GBN" | "SR" | "ADAPTIVE"
    window_size: int                        # 1..1024
    timeout_ms: float                       # > 0
    max_retransmissions: int                # >= 0
    ack_mode: str = "cumulative"            # "cumulative" | "selective"
    adaptive_alpha: Optional[float] = None  # 0 < alpha < 1 (only for ADAPTIVE)


@dataclass
class ExperimentConfig:
    name: str
    duration_s: float                       # > 0
    packet_size_bytes: int                  # 64..65535
    traffic_pattern: str                    # "cbr" | "bursty" | "trace"
    repetitions: int = 1                    # >= 1
    random_seed: Optional[int] = None


@dataclass
class EmulatorConfig:
    topology: TopologyConfig
    protocol: ProtocolConfig
    experiment: ExperimentConfig


# ─────────────────────────────────────────────────────────────
# Validator (25.2)
# ─────────────────────────────────────────────────────────────

_VALID_NODE_TYPES      = {"sender", "receiver", "router"}
_VALID_PROTOCOLS       = {"GBN", "SR", "ADAPTIVE"}
_VALID_ACK_MODES       = {"cumulative", "selective"}
_VALID_TRAFFIC_PATTERNS = {"cbr", "bursty", "trace"}


def _collect_errors(raw: Dict[str, Any]) -> List[ConfigError]:
    errors: List[ConfigError] = []

    # ── topology ──────────────────────────────────────────────
    topology = raw.get("topology")
    if topology is None:
        errors.append(ConfigError("topology", "Missing required section"))
    else:
        nodes_raw = topology.get("nodes")
        if not nodes_raw:
            errors.append(ConfigError("topology.nodes", "At least one node required"))
        else:
            node_ids = set()
            for idx, n in enumerate(nodes_raw):
                prefix = f"topology.nodes[{idx}]"
                nid = n.get("node_id")
                if not nid or not isinstance(nid, str) or not nid.strip():
                    errors.append(ConfigError(f"{prefix}.node_id", "Must be a non-empty string", nid))
                else:
                    if nid in node_ids:
                        errors.append(ConfigError(f"{prefix}.node_id", "Duplicate node_id", nid))
                    node_ids.add(nid)

                ntype = n.get("node_type")
                if ntype not in _VALID_NODE_TYPES:
                    errors.append(ConfigError(f"{prefix}.node_type",
                                              f"Must be one of {sorted(_VALID_NODE_TYPES)}", ntype))

        links_raw = topology.get("links", [])
        for idx, lnk in enumerate(links_raw):
            prefix = f"topology.links[{idx}]"
            for end in ("source", "target"):
                v = lnk.get(end)
                if not v or not isinstance(v, str):
                    errors.append(ConfigError(f"{prefix}.{end}", "Must be a non-empty string", v))

            bw = lnk.get("bandwidth_mbps")
            if bw is None:
                errors.append(ConfigError(f"{prefix}.bandwidth_mbps", "Missing required field"))
            elif not isinstance(bw, (int, float)) or bw <= 0:
                errors.append(ConfigError(f"{prefix}.bandwidth_mbps", "Must be > 0", bw))

            delay = lnk.get("delay_ms")
            if delay is None:
                errors.append(ConfigError(f"{prefix}.delay_ms", "Missing required field"))
            elif not isinstance(delay, (int, float)) or delay < 0:
                errors.append(ConfigError(f"{prefix}.delay_ms", "Must be >= 0", delay))

            loss = lnk.get("loss_pct")
            if loss is None:
                errors.append(ConfigError(f"{prefix}.loss_pct", "Missing required field"))
            elif not isinstance(loss, (int, float)) or not (0.0 <= loss <= 100.0):
                errors.append(ConfigError(f"{prefix}.loss_pct", "Must be in [0, 100]", loss))

    # ── protocol ──────────────────────────────────────────────
    proto = raw.get("protocol")
    if proto is None:
        errors.append(ConfigError("protocol", "Missing required section"))
    else:
        pname = proto.get("protocol")
        if pname not in _VALID_PROTOCOLS:
            errors.append(ConfigError("protocol.protocol",
                                      f"Must be one of {sorted(_VALID_PROTOCOLS)}", pname))

        ws = proto.get("window_size")
        if ws is None:
            errors.append(ConfigError("protocol.window_size", "Missing required field"))
        elif not isinstance(ws, int) or not (1 <= ws <= 1024):
            errors.append(ConfigError("protocol.window_size", "Must be integer in [1, 1024]", ws))

        to = proto.get("timeout_ms")
        if to is None:
            errors.append(ConfigError("protocol.timeout_ms", "Missing required field"))
        elif not isinstance(to, (int, float)) or to <= 0:
            errors.append(ConfigError("protocol.timeout_ms", "Must be > 0", to))

        max_ret = proto.get("max_retransmissions")
        if max_ret is None:
            errors.append(ConfigError("protocol.max_retransmissions", "Missing required field"))
        elif not isinstance(max_ret, int) or max_ret < 0:
            errors.append(ConfigError("protocol.max_retransmissions", "Must be integer >= 0", max_ret))

        ack_mode = proto.get("ack_mode", "cumulative")
        if ack_mode not in _VALID_ACK_MODES:
            errors.append(ConfigError("protocol.ack_mode",
                                      f"Must be one of {sorted(_VALID_ACK_MODES)}", ack_mode))

        if pname == "ADAPTIVE":
            alpha = proto.get("adaptive_alpha")
            if alpha is None:
                errors.append(ConfigError("protocol.adaptive_alpha",
                                          "Required when protocol=ADAPTIVE"))
            elif not isinstance(alpha, (int, float)) or not (0.0 < alpha < 1.0):
                errors.append(ConfigError("protocol.adaptive_alpha",
                                          "Must be float in (0, 1)", alpha))

        # Conflicting setting: SR protocol must use selective acks
        if pname == "SR" and proto.get("ack_mode", "selective") != "selective":
            errors.append(ConfigError("protocol.ack_mode",
                                      "SR protocol requires ack_mode=selective",
                                      proto.get("ack_mode")))

    # ── experiment ────────────────────────────────────────────
    exp = raw.get("experiment")
    if exp is None:
        errors.append(ConfigError("experiment", "Missing required section"))
    else:
        name = exp.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append(ConfigError("experiment.name", "Must be a non-empty string", name))

        dur = exp.get("duration_s")
        if dur is None:
            errors.append(ConfigError("experiment.duration_s", "Missing required field"))
        elif not isinstance(dur, (int, float)) or dur <= 0:
            errors.append(ConfigError("experiment.duration_s", "Must be > 0", dur))

        psize = exp.get("packet_size_bytes")
        if psize is None:
            errors.append(ConfigError("experiment.packet_size_bytes", "Missing required field"))
        elif not isinstance(psize, int) or not (64 <= psize <= 65535):
            errors.append(ConfigError("experiment.packet_size_bytes",
                                      "Must be integer in [64, 65535]", psize))

        pattern = exp.get("traffic_pattern")
        if pattern not in _VALID_TRAFFIC_PATTERNS:
            errors.append(ConfigError("experiment.traffic_pattern",
                                      f"Must be one of {sorted(_VALID_TRAFFIC_PATTERNS)}", pattern))

        reps = exp.get("repetitions", 1)
        if not isinstance(reps, int) or reps < 1:
            errors.append(ConfigError("experiment.repetitions", "Must be integer >= 1", reps))

    return errors


# ─────────────────────────────────────────────────────────────
# Config loader (25.1 + 25.2)
# ─────────────────────────────────────────────────────────────

class ConfigLoader:
    """
    Load and validate emulator configuration from YAML or a raw dict.

    Raises ConfigValidationError on any validation failure so callers
    receive clear, actionable error messages (Requirement 11.5, 11.7).
    """

    # ── public API ────────────────────────────────────────────

    @classmethod
    def from_file(cls, path: str | Path) -> EmulatorConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_yaml(cls, yaml_text: str) -> EmulatorConfig:
        raw = yaml.safe_load(yaml_text) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> EmulatorConfig:
        """Validate *raw* dict and return a typed EmulatorConfig, or raise."""
        errors = _collect_errors(raw)
        if errors:
            raise ConfigValidationError(errors)
        return cls._build(raw)

    @classmethod
    def validate(cls, raw: Dict[str, Any]) -> List[ConfigError]:
        """Return list of errors without raising (useful for testing)."""
        return _collect_errors(raw)

    # ── private ───────────────────────────────────────────────

    @staticmethod
    def _build(raw: Dict[str, Any]) -> EmulatorConfig:
        topo_raw = raw["topology"]
        nodes = [
            NodeConfig(
                node_id=n["node_id"],
                node_type=n["node_type"],
                position=n.get("position"),
            )
            for n in topo_raw.get("nodes", [])
        ]
        links = [
            LinkConfig(
                source=lnk["source"],
                target=lnk["target"],
                bandwidth_mbps=float(lnk["bandwidth_mbps"]),
                delay_ms=float(lnk["delay_ms"]),
                loss_pct=float(lnk["loss_pct"]),
            )
            for lnk in topo_raw.get("links", [])
        ]

        p = raw["protocol"]
        protocol = ProtocolConfig(
            protocol=p["protocol"],
            window_size=int(p["window_size"]),
            timeout_ms=float(p["timeout_ms"]),
            max_retransmissions=int(p["max_retransmissions"]),
            ack_mode=p.get("ack_mode", "cumulative"),
            adaptive_alpha=p.get("adaptive_alpha"),
        )

        e = raw["experiment"]
        experiment = ExperimentConfig(
            name=e["name"].strip(),
            duration_s=float(e["duration_s"]),
            packet_size_bytes=int(e["packet_size_bytes"]),
            traffic_pattern=e["traffic_pattern"],
            repetitions=int(e.get("repetitions", 1)),
            random_seed=e.get("random_seed"),
        )

        return EmulatorConfig(
            topology=TopologyConfig(nodes=nodes, links=links),
            protocol=protocol,
            experiment=experiment,
        )
