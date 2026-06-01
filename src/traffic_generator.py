"""
Traffic Generator for the Adaptive Network Emulator.
Validates: Requirements 10.1, 10.2
"""

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrafficPattern(Enum):
    CONSTANT = "constant"
    BURSTY   = "bursty"
    PERIODIC = "periodic"


class CongestionLevel(Enum):
    NONE   = "none"
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


@dataclass
class FlowConfig:
    """Configuration for a single traffic flow. Validates: Requirement 10.2"""
    flow_id: str
    source: str
    destination: str
    pattern: str
    rate_bps: float
    packet_size_bytes: int = 1024
    burst_prob: float = 0.3
    burst_mult: float = 5.0
    period_s: float = 10.0
    protocol: str = "TCP"
    congestion_level: str = "none"
    random_seed: Optional[int] = None


@dataclass
class GeneratedPacket:
    """A single packet produced by the traffic generator."""
    packet_id: str
    flow_id: str
    source: str
    destination: str
    size_bytes: int
    protocol: str
    timestamp: float
    pattern: str
    is_burst: bool = False


@dataclass
class FlowStats:
    """Statistics for a single flow."""
    flow_id: str
    packets_generated: int
    bytes_generated: int
    burst_packets: int
    actual_rate_bps: float
    elapsed_s: float


class TrafficGenerator:
    """
    Generates configurable traffic patterns for emulator flows.
    Patterns: CONSTANT (steady), BURSTY (random bursts), PERIODIC (sinusoidal)
    Validates: Requirements 10.1, 10.2
    """

    _CONGESTION_DROP = {
        "none":   0.0,
        "low":    0.05,
        "medium": 0.15,
        "high":   0.40,
    }

    def __init__(self):
        self._flows: Dict[str, FlowConfig] = {}
        self._rngs: Dict[str, random.Random] = {}
        self._flow_stats: Dict[str, FlowStats] = {}
        self._packet_counter: int = 0

    def add_flow(self, config: FlowConfig) -> None:
        """Register a new traffic flow."""
        self._flows[config.flow_id] = config
        seed = config.random_seed if config.random_seed is not None else id(config)
        self._rngs[config.flow_id] = random.Random(seed)
        self._flow_stats[config.flow_id] = FlowStats(
            flow_id=config.flow_id,
            packets_generated=0, bytes_generated=0,
            burst_packets=0, actual_rate_bps=0.0, elapsed_s=0.0,
        )

    def remove_flow(self, flow_id: str) -> bool:
        """Remove a flow by ID."""
        if flow_id not in self._flows:
            return False
        del self._flows[flow_id]
        del self._rngs[flow_id]
        del self._flow_stats[flow_id]
        return True

    def list_flows(self) -> List[str]:
        return list(self._flows.keys())

    def generate_tick(self, tick: int, sim_time: float) -> List[GeneratedPacket]:
        """Generate packets for ALL flows for one tick."""
        all_packets: List[GeneratedPacket] = []
        for flow_id, cfg in self._flows.items():
            pkts = self._generate_flow_tick(cfg, tick, sim_time)
            all_packets.extend(pkts)
            self._update_stats(flow_id, pkts, sim_time)
        return all_packets

    def generate_flow_tick(self, flow_id: str, tick: int, sim_time: float) -> List[GeneratedPacket]:
        """Generate packets for a SINGLE flow for one tick."""
        if flow_id not in self._flows:
            return []
        cfg  = self._flows[flow_id]
        pkts = self._generate_flow_tick(cfg, tick, sim_time)
        self._update_stats(flow_id, pkts, sim_time)
        return pkts

    def _generate_flow_tick(self, cfg: FlowConfig, tick: int, sim_time: float) -> List[GeneratedPacket]:
        rng       = self._rngs[cfg.flow_id]
        base_pkts = self._packets_per_tick(cfg)
        is_burst  = False

        if cfg.pattern == TrafficPattern.CONSTANT.value:
            n_packets = base_pkts

        elif cfg.pattern == TrafficPattern.BURSTY.value:
            if rng.random() < cfg.burst_prob:
                n_packets = max(1, int(base_pkts * cfg.burst_mult))
                is_burst  = True
            else:
                n_packets = 0

        elif cfg.pattern == TrafficPattern.PERIODIC.value:
            phase     = (2 * math.pi * sim_time) / max(cfg.period_s, 0.001)
            scale     = (math.sin(phase) + 1.0) / 2.0
            n_packets = max(0, int(base_pkts * scale * 2))

        else:
            n_packets = base_pkts

        drop_prob = self._CONGESTION_DROP.get(cfg.congestion_level, 0.0)
        packets: List[GeneratedPacket] = []
        for _ in range(n_packets):
            if rng.random() < drop_prob:
                continue
            self._packet_counter += 1
            packets.append(GeneratedPacket(
                packet_id=f"{cfg.flow_id}_pkt_{self._packet_counter}",
                flow_id=cfg.flow_id,
                source=cfg.source,
                destination=cfg.destination,
                size_bytes=cfg.packet_size_bytes,
                protocol=cfg.protocol,
                timestamp=time.time(),
                pattern=cfg.pattern,
                is_burst=is_burst,
            ))
        return packets

    @staticmethod
    def _packets_per_tick(cfg: FlowConfig) -> int:
        if cfg.packet_size_bytes <= 0:
            return 0
        return max(1, int(cfg.rate_bps / (cfg.packet_size_bytes * 8)))

    def _update_stats(self, flow_id: str, packets: List[GeneratedPacket], sim_time: float) -> None:
        stats = self._flow_stats[flow_id]
        stats.packets_generated += len(packets)
        stats.bytes_generated   += sum(p.size_bytes for p in packets)
        stats.burst_packets     += sum(1 for p in packets if p.is_burst)
        stats.elapsed_s          = max(sim_time, 0.001)
        stats.actual_rate_bps    = (stats.bytes_generated * 8) / stats.elapsed_s

    def get_flow_stats(self, flow_id: str) -> Optional[FlowStats]:
        return self._flow_stats.get(flow_id)

    def get_all_stats(self) -> Dict[str, FlowStats]:
        return dict(self._flow_stats)

    def reset_stats(self) -> None:
        for fid in self._flow_stats:
            self._flow_stats[fid] = FlowStats(
                flow_id=fid, packets_generated=0, bytes_generated=0,
                burst_packets=0, actual_rate_bps=0.0, elapsed_s=0.0,
            )
        self._packet_counter = 0
