"""
Data models for the Adaptive Network Emulator.

This module defines all core data structures used throughout the emulator,
including packet structures, routing information, network topology, metrics,
and configuration. All dataclasses include serialization/deserialization
methods for logging and persistence.

Validates: Requirements 11.3
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set
import json
import numpy as np


@dataclass
class Packet:
    """
    Represents a network packet at the Network Layer.
    
    Attributes:
        packet_id: Unique identifier for the packet
        timestamp: Creation timestamp (seconds since epoch)
        source_ip: Source IP address
        dest_ip: Destination IP address
        protocol: Protocol type (TCP, UDP, ICMP, etc.)
        payload: Packet payload data
        headers: Layer-specific headers as key-value pairs
    """
    packet_id: str
    timestamp: float
    source_ip: str
    dest_ip: str
    protocol: str
    payload: bytes
    headers: Dict[str, bytes] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize packet to dictionary."""
        return {
            'packet_id': self.packet_id,
            'timestamp': self.timestamp,
            'source_ip': self.source_ip,
            'dest_ip': self.dest_ip,
            'protocol': self.protocol,
            'payload': self.payload.hex(),
            'headers': {k: v.hex() for k, v in self.headers.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Packet':
        """Deserialize packet from dictionary."""
        return cls(
            packet_id=data['packet_id'],
            timestamp=data['timestamp'],
            source_ip=data['source_ip'],
            dest_ip=data['dest_ip'],
            protocol=data['protocol'],
            payload=bytes.fromhex(data['payload']),
            headers={k: bytes.fromhex(v) for k, v in data['headers'].items()}
        )
    
    def to_json(self) -> str:
        """Serialize packet to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Packet':
        """Deserialize packet from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Segment:
    """
    Represents a transport layer segment (TCP/UDP).
    
    Attributes:
        sequence_num: Sequence number for ordering
        ack_num: Acknowledgment number
        window_size: Receiver window size for flow control
        flags: Set of control flags (SYN, ACK, FIN, etc.)
        data: Segment payload data
        checksum: Checksum for error detection
    """
    sequence_num: int
    ack_num: int
    window_size: int
    flags: Set[str]
    data: bytes
    checksum: int
    
    def to_dict(self) -> dict:
        """Serialize segment to dictionary."""
        return {
            'sequence_num': self.sequence_num,
            'ack_num': self.ack_num,
            'window_size': self.window_size,
            'flags': list(self.flags),
            'data': self.data.hex(),
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Segment':
        """Deserialize segment from dictionary."""
        return cls(
            sequence_num=data['sequence_num'],
            ack_num=data['ack_num'],
            window_size=data['window_size'],
            flags=set(data['flags']),
            data=bytes.fromhex(data['data']),
            checksum=data['checksum']
        )
    
    def to_json(self) -> str:
        """Serialize segment to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Segment':
        """Deserialize segment from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Frame:
    """
    Represents a data link layer frame.
    
    Attributes:
        preamble: Frame preamble for synchronization
        dest_mac: Destination MAC address
        source_mac: Source MAC address
        payload: Frame payload (typically a packet)
        crc: CRC checksum for error detection
        error_corrected: Flag indicating if errors were corrected
    """
    preamble: bytes
    dest_mac: str
    source_mac: str
    payload: bytes
    crc: int
    error_corrected: bool = False
    
    def to_dict(self) -> dict:
        """Serialize frame to dictionary."""
        return {
            'preamble': self.preamble.hex(),
            'dest_mac': self.dest_mac,
            'source_mac': self.source_mac,
            'payload': self.payload.hex(),
            'crc': self.crc,
            'error_corrected': self.error_corrected
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Frame':
        """Deserialize frame from dictionary."""
        return cls(
            preamble=bytes.fromhex(data['preamble']),
            dest_mac=data['dest_mac'],
            source_mac=data['source_mac'],
            payload=bytes.fromhex(data['payload']),
            crc=data['crc'],
            error_corrected=data['error_corrected']
        )
    
    def to_json(self) -> str:
        """Serialize frame to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Frame':
        """Deserialize frame from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class RouteEntry:
    """
    Represents a routing table entry.
    
    Attributes:
        destination: Destination network/host address
        next_hop: Next hop router address
        cost: Route cost/metric
        interface: Outgoing interface identifier
        timestamp: Last update timestamp
        metric_type: Type of metric (hop_count, latency, bandwidth)
    """
    destination: str
    next_hop: str
    cost: float
    interface: str
    timestamp: float
    metric_type: str
    
    def to_dict(self) -> dict:
        """Serialize route entry to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RouteEntry':
        """Deserialize route entry from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize route entry to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RouteEntry':
        """Deserialize route entry from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Link:
    """
    Represents a network link between two nodes.
    
    Attributes:
        node_a: First node identifier
        node_b: Second node identifier
        cost: Link cost for routing
        capacity: Link capacity in bytes/sec
        utilization: Current utilization (0.0 to 1.0)
        latency: Link latency in milliseconds
        loss_rate: Packet loss rate (0.0 to 1.0)
    """
    node_a: str
    node_b: str
    cost: float
    capacity: float
    utilization: float
    latency: float
    loss_rate: float
    
    def to_dict(self) -> dict:
        """Serialize link to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Deserialize link from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize link to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Link':
        """Deserialize link from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class NetworkTopology:
    """
    Represents the complete network topology.
    
    Attributes:
        nodes: List of node identifiers
        links: List of links between nodes
        adjacency_matrix: Adjacency matrix representation (numpy array)
    """
    nodes: List[str]
    links: List[Link]
    adjacency_matrix: np.ndarray = field(default_factory=lambda: np.array([]))
    
    def to_dict(self) -> dict:
        """Serialize topology to dictionary."""
        return {
            'nodes': self.nodes,
            'links': [link.to_dict() for link in self.links],
            'adjacency_matrix': self.adjacency_matrix.tolist()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NetworkTopology':
        """Deserialize topology from dictionary."""
        return cls(
            nodes=data['nodes'],
            links=[Link.from_dict(link_data) for link_data in data['links']],
            adjacency_matrix=np.array(data['adjacency_matrix'])
        )
    
    def to_json(self) -> str:
        """Serialize topology to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NetworkTopology':
        """Deserialize topology from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class NetworkMetrics:
    """
    Represents network performance metrics.
    
    Attributes:
        timestamp: Measurement timestamp
        throughput: Throughput in bytes/sec
        latency: Average latency in milliseconds
        packet_loss: Packet loss percentage (0-100)
        retransmissions: Number of retransmitted packets
        jitter: Jitter in milliseconds
        active_connections: Number of active connections
        queue_depth: Queue depth per layer
    """
    timestamp: float
    throughput: float
    latency: float
    packet_loss: float
    retransmissions: int
    jitter: float
    active_connections: int
    queue_depth: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize metrics to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NetworkMetrics':
        """Deserialize metrics from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize metrics to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NetworkMetrics':
        """Deserialize metrics from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class EmulatorConfig:
    """
    Configuration for the network emulator.
    
    Attributes:
        num_nodes: Number of nodes in the network
        topology_type: Topology type (mesh, star, ring, custom)
        routing_algorithm: Routing algorithm (dijkstra, distance_vector)
        transport_protocol: Transport protocol (gbn, sr)
        window_size: Sliding window size
        timeout_ms: Timeout in milliseconds
        error_rate: Bit error rate (0.0 to 1.0)
        loss_rate: Packet loss rate (0.0 to 1.0)
        enable_optimization: Enable adaptive optimization
        capture_packets: Enable packet capture
    """
    num_nodes: int
    topology_type: str
    routing_algorithm: str
    transport_protocol: str
    window_size: int
    timeout_ms: int
    error_rate: float
    loss_rate: float
    enable_optimization: bool
    capture_packets: bool
    
    def to_dict(self) -> dict:
        """Serialize config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EmulatorConfig':
        """Deserialize config from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize config to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EmulatorConfig':
        """Deserialize config from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def validate(self) -> List[str]:
        """
        Validate configuration parameters.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if self.num_nodes < 2:
            errors.append("num_nodes must be at least 2")
        
        if self.topology_type not in ['mesh', 'star', 'ring', 'custom']:
            errors.append(f"Invalid topology_type: {self.topology_type}")
        
        if self.routing_algorithm not in ['dijkstra', 'distance_vector']:
            errors.append(f"Invalid routing_algorithm: {self.routing_algorithm}")
        
        if self.transport_protocol not in ['gbn', 'sr']:
            errors.append(f"Invalid transport_protocol: {self.transport_protocol}")
        
        if self.window_size < 1:
            errors.append("window_size must be at least 1")
        
        if self.timeout_ms < 1:
            errors.append("timeout_ms must be at least 1")
        
        if not (0.0 <= self.error_rate <= 1.0):
            errors.append("error_rate must be between 0.0 and 1.0")
        
        if not (0.0 <= self.loss_rate <= 1.0):
            errors.append("loss_rate must be between 0.0 and 1.0")
        
        return errors
