"""
Unit tests for data models.

Tests serialization/deserialization and validation for all data structures.
"""

import pytest
import json
import numpy as np
from src.data_models import (
    Packet, Segment, Frame, RouteEntry, Link, NetworkTopology,
    NetworkMetrics, EmulatorConfig
)


class TestPacket:
    """Tests for Packet dataclass."""
    
    def test_packet_creation(self):
        """Test basic packet creation."""
        packet = Packet(
            packet_id="pkt_001",
            timestamp=1234567890.0,
            source_ip="192.168.1.1",
            dest_ip="192.168.1.2",
            protocol="TCP",
            payload=b"Hello, World!",
            headers={"layer4": b"\x00\x01\x02"}
        )
        
        assert packet.packet_id == "pkt_001"
        assert packet.source_ip == "192.168.1.1"
        assert packet.payload == b"Hello, World!"
    
    def test_packet_serialization(self):
        """Test packet to_dict and from_dict."""
        original = Packet(
            packet_id="pkt_002",
            timestamp=1234567890.5,
            source_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            protocol="UDP",
            payload=b"\x01\x02\x03\x04",
            headers={"test": b"\xff\xfe"}
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = Packet.from_dict(data)
        
        assert restored.packet_id == original.packet_id
        assert restored.timestamp == original.timestamp
        assert restored.source_ip == original.source_ip
        assert restored.dest_ip == original.dest_ip
        assert restored.protocol == original.protocol
        assert restored.payload == original.payload
        assert restored.headers == original.headers
    
    def test_packet_json_serialization(self):
        """Test packet to_json and from_json."""
        original = Packet(
            packet_id="pkt_003",
            timestamp=1234567891.0,
            source_ip="172.16.0.1",
            dest_ip="172.16.0.2",
            protocol="ICMP",
            payload=b"ping",
            headers={}
        )
        
        json_str = original.to_json()
        restored = Packet.from_json(json_str)
        
        assert restored.packet_id == original.packet_id
        assert restored.payload == original.payload


class TestSegment:
    """Tests for Segment dataclass."""
    
    def test_segment_creation(self):
        """Test basic segment creation."""
        segment = Segment(
            sequence_num=100,
            ack_num=50,
            window_size=64,
            flags={"SYN", "ACK"},
            data=b"segment data",
            checksum=0x1234
        )
        
        assert segment.sequence_num == 100
        assert segment.ack_num == 50
        assert "SYN" in segment.flags
        assert "ACK" in segment.flags
    
    def test_segment_serialization(self):
        """Test segment to_dict and from_dict."""
        original = Segment(
            sequence_num=200,
            ack_num=150,
            window_size=32,
            flags={"ACK", "FIN"},
            data=b"test data",
            checksum=0xABCD
        )
        
        data = original.to_dict()
        restored = Segment.from_dict(data)
        
        assert restored.sequence_num == original.sequence_num
        assert restored.ack_num == original.ack_num
        assert restored.window_size == original.window_size
        assert restored.flags == original.flags
        assert restored.data == original.data
        assert restored.checksum == original.checksum
    
    def test_segment_json_serialization(self):
        """Test segment to_json and from_json."""
        original = Segment(
            sequence_num=300,
            ack_num=250,
            window_size=16,
            flags={"PSH"},
            data=b"json test",
            checksum=0x5678
        )
        
        json_str = original.to_json()
        restored = Segment.from_json(json_str)
        
        assert restored.sequence_num == original.sequence_num
        assert restored.data == original.data


class TestFrame:
    """Tests for Frame dataclass."""
    
    def test_frame_creation(self):
        """Test basic frame creation."""
        frame = Frame(
            preamble=b"\xAA\xAA\xAA\xAA",
            dest_mac="00:11:22:33:44:55",
            source_mac="AA:BB:CC:DD:EE:FF",
            payload=b"frame payload",
            crc=0x12345678,
            error_corrected=False
        )
        
        assert frame.dest_mac == "00:11:22:33:44:55"
        assert frame.source_mac == "AA:BB:CC:DD:EE:FF"
        assert frame.error_corrected is False
    
    def test_frame_serialization(self):
        """Test frame to_dict and from_dict."""
        original = Frame(
            preamble=b"\x55\x55",
            dest_mac="11:22:33:44:55:66",
            source_mac="66:55:44:33:22:11",
            payload=b"test payload",
            crc=0xDEADBEEF,
            error_corrected=True
        )
        
        data = original.to_dict()
        restored = Frame.from_dict(data)
        
        assert restored.preamble == original.preamble
        assert restored.dest_mac == original.dest_mac
        assert restored.source_mac == original.source_mac
        assert restored.payload == original.payload
        assert restored.crc == original.crc
        assert restored.error_corrected == original.error_corrected
    
    def test_frame_json_serialization(self):
        """Test frame to_json and from_json."""
        original = Frame(
            preamble=b"\xFF",
            dest_mac="AA:AA:AA:AA:AA:AA",
            source_mac="BB:BB:BB:BB:BB:BB",
            payload=b"json frame",
            crc=0xCAFEBABE
        )
        
        json_str = original.to_json()
        restored = Frame.from_json(json_str)
        
        assert restored.payload == original.payload
        assert restored.crc == original.crc


class TestRouteEntry:
    """Tests for RouteEntry dataclass."""
    
    def test_route_entry_creation(self):
        """Test basic route entry creation."""
        entry = RouteEntry(
            destination="192.168.1.0/24",
            next_hop="192.168.0.1",
            cost=10.5,
            interface="eth0",
            timestamp=1234567890.0,
            metric_type="latency"
        )
        
        assert entry.destination == "192.168.1.0/24"
        assert entry.cost == 10.5
        assert entry.metric_type == "latency"
    
    def test_route_entry_serialization(self):
        """Test route entry to_dict and from_dict."""
        original = RouteEntry(
            destination="10.0.0.0/8",
            next_hop="10.0.0.1",
            cost=5.0,
            interface="eth1",
            timestamp=1234567891.0,
            metric_type="hop_count"
        )
        
        data = original.to_dict()
        restored = RouteEntry.from_dict(data)
        
        assert restored.destination == original.destination
        assert restored.next_hop == original.next_hop
        assert restored.cost == original.cost
        assert restored.interface == original.interface
        assert restored.timestamp == original.timestamp
        assert restored.metric_type == original.metric_type


class TestLink:
    """Tests for Link dataclass."""
    
    def test_link_creation(self):
        """Test basic link creation."""
        link = Link(
            node_a="node1",
            node_b="node2",
            cost=15.0,
            capacity=1000000.0,
            utilization=0.5,
            latency=10.0,
            loss_rate=0.01
        )
        
        assert link.node_a == "node1"
        assert link.node_b == "node2"
        assert link.utilization == 0.5
    
    def test_link_serialization(self):
        """Test link to_dict and from_dict."""
        original = Link(
            node_a="A",
            node_b="B",
            cost=20.0,
            capacity=500000.0,
            utilization=0.75,
            latency=25.0,
            loss_rate=0.05
        )
        
        data = original.to_dict()
        restored = Link.from_dict(data)
        
        assert restored.node_a == original.node_a
        assert restored.node_b == original.node_b
        assert restored.cost == original.cost
        assert restored.capacity == original.capacity
        assert restored.utilization == original.utilization
        assert restored.latency == original.latency
        assert restored.loss_rate == original.loss_rate


class TestNetworkTopology:
    """Tests for NetworkTopology dataclass."""
    
    def test_topology_creation(self):
        """Test basic topology creation."""
        links = [
            Link("A", "B", 10.0, 1e6, 0.5, 10.0, 0.01),
            Link("B", "C", 15.0, 1e6, 0.3, 15.0, 0.02)
        ]
        adj_matrix = np.array([[0, 10, 0], [10, 0, 15], [0, 15, 0]])
        
        topology = NetworkTopology(
            nodes=["A", "B", "C"],
            links=links,
            adjacency_matrix=adj_matrix
        )
        
        assert len(topology.nodes) == 3
        assert len(topology.links) == 2
        assert topology.adjacency_matrix.shape == (3, 3)
    
    def test_topology_serialization(self):
        """Test topology to_dict and from_dict."""
        links = [Link("X", "Y", 5.0, 1e6, 0.2, 5.0, 0.0)]
        adj_matrix = np.array([[0, 5], [5, 0]])
        
        original = NetworkTopology(
            nodes=["X", "Y"],
            links=links,
            adjacency_matrix=adj_matrix
        )
        
        data = original.to_dict()
        restored = NetworkTopology.from_dict(data)
        
        assert restored.nodes == original.nodes
        assert len(restored.links) == len(original.links)
        assert np.array_equal(restored.adjacency_matrix, original.adjacency_matrix)
    
    def test_topology_json_serialization(self):
        """Test topology to_json and from_json."""
        links = [Link("P", "Q", 8.0, 1e6, 0.4, 8.0, 0.01)]
        adj_matrix = np.array([[0, 8], [8, 0]])
        
        original = NetworkTopology(
            nodes=["P", "Q"],
            links=links,
            adjacency_matrix=adj_matrix
        )
        
        json_str = original.to_json()
        restored = NetworkTopology.from_json(json_str)
        
        assert restored.nodes == original.nodes
        assert np.array_equal(restored.adjacency_matrix, original.adjacency_matrix)


class TestNetworkMetrics:
    """Tests for NetworkMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test basic metrics creation."""
        metrics = NetworkMetrics(
            timestamp=1234567890.0,
            throughput=1000000.0,
            latency=25.5,
            packet_loss=2.5,
            retransmissions=10,
            jitter=5.0,
            active_connections=5,
            queue_depth={"transport": 10, "network": 5}
        )
        
        assert metrics.throughput == 1000000.0
        assert metrics.latency == 25.5
        assert metrics.queue_depth["transport"] == 10
    
    def test_metrics_serialization(self):
        """Test metrics to_dict and from_dict."""
        original = NetworkMetrics(
            timestamp=1234567891.0,
            throughput=500000.0,
            latency=50.0,
            packet_loss=5.0,
            retransmissions=20,
            jitter=10.0,
            active_connections=3,
            queue_depth={"application": 2, "transport": 8}
        )
        
        data = original.to_dict()
        restored = NetworkMetrics.from_dict(data)
        
        assert restored.timestamp == original.timestamp
        assert restored.throughput == original.throughput
        assert restored.latency == original.latency
        assert restored.packet_loss == original.packet_loss
        assert restored.retransmissions == original.retransmissions
        assert restored.jitter == original.jitter
        assert restored.active_connections == original.active_connections
        assert restored.queue_depth == original.queue_depth


class TestEmulatorConfig:
    """Tests for EmulatorConfig dataclass."""
    
    def test_config_creation(self):
        """Test basic config creation."""
        config = EmulatorConfig(
            num_nodes=5,
            topology_type="mesh",
            routing_algorithm="dijkstra",
            transport_protocol="gbn",
            window_size=16,
            timeout_ms=1000,
            error_rate=0.001,
            loss_rate=0.05,
            enable_optimization=True,
            capture_packets=False
        )
        
        assert config.num_nodes == 5
        assert config.topology_type == "mesh"
        assert config.routing_algorithm == "dijkstra"
    
    def test_config_serialization(self):
        """Test config to_dict and from_dict."""
        original = EmulatorConfig(
            num_nodes=3,
            topology_type="star",
            routing_algorithm="distance_vector",
            transport_protocol="sr",
            window_size=32,
            timeout_ms=2000,
            error_rate=0.01,
            loss_rate=0.1,
            enable_optimization=False,
            capture_packets=True
        )
        
        data = original.to_dict()
        restored = EmulatorConfig.from_dict(data)
        
        assert restored.num_nodes == original.num_nodes
        assert restored.topology_type == original.topology_type
        assert restored.routing_algorithm == original.routing_algorithm
        assert restored.transport_protocol == original.transport_protocol
        assert restored.window_size == original.window_size
        assert restored.timeout_ms == original.timeout_ms
        assert restored.error_rate == original.error_rate
        assert restored.loss_rate == original.loss_rate
        assert restored.enable_optimization == original.enable_optimization
        assert restored.capture_packets == original.capture_packets
    
    def test_config_validation_valid(self):
        """Test validation with valid config."""
        config = EmulatorConfig(
            num_nodes=4,
            topology_type="ring",
            routing_algorithm="dijkstra",
            transport_protocol="gbn",
            window_size=8,
            timeout_ms=500,
            error_rate=0.0,
            loss_rate=0.0,
            enable_optimization=True,
            capture_packets=True
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_invalid_num_nodes(self):
        """Test validation with invalid num_nodes."""
        config = EmulatorConfig(
            num_nodes=1,
            topology_type="mesh",
            routing_algorithm="dijkstra",
            transport_protocol="gbn",
            window_size=8,
            timeout_ms=500,
            error_rate=0.0,
            loss_rate=0.0,
            enable_optimization=True,
            capture_packets=True
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("num_nodes" in err for err in errors)
    
    def test_config_validation_invalid_topology(self):
        """Test validation with invalid topology_type."""
        config = EmulatorConfig(
            num_nodes=3,
            topology_type="invalid",
            routing_algorithm="dijkstra",
            transport_protocol="gbn",
            window_size=8,
            timeout_ms=500,
            error_rate=0.0,
            loss_rate=0.0,
            enable_optimization=True,
            capture_packets=True
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("topology_type" in err for err in errors)
    
    def test_config_validation_invalid_rates(self):
        """Test validation with invalid error/loss rates."""
        config = EmulatorConfig(
            num_nodes=3,
            topology_type="mesh",
            routing_algorithm="dijkstra",
            transport_protocol="gbn",
            window_size=8,
            timeout_ms=500,
            error_rate=1.5,
            loss_rate=-0.1,
            enable_optimization=True,
            capture_packets=True
        )
        
        errors = config.validate()
        assert len(errors) >= 2
        assert any("error_rate" in err for err in errors)
        assert any("loss_rate" in err for err in errors)
