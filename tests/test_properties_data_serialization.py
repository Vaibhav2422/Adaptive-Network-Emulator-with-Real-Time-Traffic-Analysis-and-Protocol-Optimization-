"""
Property-based tests for data serialization.

Feature: adaptive-network-emulator
Property: Serialization round-trip
Validates: Requirements 11.3

For any valid data structure, serializing then deserializing should produce
an equivalent object. Tests use hypothesis with minimum 100 iterations.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from src.data_models import (
    Packet, Segment, Frame, RouteEntry, Link, NetworkTopology,
    NetworkMetrics, EmulatorConfig
)


# Custom strategies for generating valid test data

@st.composite
def packet_strategy(draw):
    """Generate random valid Packet instances."""
    return Packet(
        packet_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',)))),
        timestamp=draw(st.floats(min_value=0.0, max_value=2e9, allow_nan=False, allow_infinity=False)),
        source_ip=draw(st.from_regex(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', fullmatch=True)),
        dest_ip=draw(st.from_regex(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', fullmatch=True)),
        protocol=draw(st.sampled_from(['TCP', 'UDP', 'ICMP', 'IGMP'])),
        payload=draw(st.binary(min_size=0, max_size=1500)),
        headers=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',))),
            values=st.binary(min_size=0, max_size=100),
            max_size=10
        ))
    )


@st.composite
def segment_strategy(draw):
    """Generate random valid Segment instances."""
    return Segment(
        sequence_num=draw(st.integers(min_value=0, max_value=2**32-1)),
        ack_num=draw(st.integers(min_value=0, max_value=2**32-1)),
        window_size=draw(st.integers(min_value=1, max_value=65535)),
        flags=draw(st.sets(st.sampled_from(['SYN', 'ACK', 'FIN', 'RST', 'PSH', 'URG']), max_size=6)),
        data=draw(st.binary(min_size=0, max_size=1500)),
        checksum=draw(st.integers(min_value=0, max_value=2**32-1))
    )


@st.composite
def frame_strategy(draw):
    """Generate random valid Frame instances."""
    return Frame(
        preamble=draw(st.binary(min_size=1, max_size=8)),
        dest_mac=draw(st.from_regex(r'[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}', fullmatch=True)),
        source_mac=draw(st.from_regex(r'[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}', fullmatch=True)),
        payload=draw(st.binary(min_size=0, max_size=1500)),
        crc=draw(st.integers(min_value=0, max_value=2**32-1)),
        error_corrected=draw(st.booleans())
    )


@st.composite
def route_entry_strategy(draw):
    """Generate random valid RouteEntry instances."""
    return RouteEntry(
        destination=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',)))),
        next_hop=draw(st.from_regex(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', fullmatch=True)),
        cost=draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        interface=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',)))),
        timestamp=draw(st.floats(min_value=0.0, max_value=2e9, allow_nan=False, allow_infinity=False)),
        metric_type=draw(st.sampled_from(['hop_count', 'latency', 'bandwidth']))
    )


@st.composite
def link_strategy(draw):
    """Generate random valid Link instances."""
    return Link(
        node_a=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',)))),
        node_b=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',)))),
        cost=draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        capacity=draw(st.floats(min_value=1.0, max_value=1e12, allow_nan=False, allow_infinity=False)),
        utilization=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        latency=draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        loss_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    )


@st.composite
def network_topology_strategy(draw):
    """Generate random valid NetworkTopology instances."""
    num_nodes = draw(st.integers(min_value=2, max_value=10))
    nodes = [f"node_{i}" for i in range(num_nodes)]
    
    # Generate random links
    num_links = draw(st.integers(min_value=1, max_value=min(20, num_nodes * (num_nodes - 1) // 2)))
    links = []
    for _ in range(num_links):
        link = draw(link_strategy())
        links.append(link)
    
    # Generate adjacency matrix
    adj_matrix = draw(st.lists(
        st.lists(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False), 
                 min_size=num_nodes, max_size=num_nodes),
        min_size=num_nodes, max_size=num_nodes
    ))
    
    return NetworkTopology(
        nodes=nodes,
        links=links,
        adjacency_matrix=np.array(adj_matrix)
    )


@st.composite
def network_metrics_strategy(draw):
    """Generate random valid NetworkMetrics instances."""
    return NetworkMetrics(
        timestamp=draw(st.floats(min_value=0.0, max_value=2e9, allow_nan=False, allow_infinity=False)),
        throughput=draw(st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)),
        latency=draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)),
        packet_loss=draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        retransmissions=draw(st.integers(min_value=0, max_value=1000000)),
        jitter=draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        active_connections=draw(st.integers(min_value=0, max_value=10000)),
        queue_depth=draw(st.dictionaries(
            keys=st.sampled_from(['application', 'transport', 'network', 'data_link', 'mac', 'physical']),
            values=st.integers(min_value=0, max_value=10000),
            max_size=6
        ))
    )


@st.composite
def emulator_config_strategy(draw):
    """Generate random valid EmulatorConfig instances."""
    return EmulatorConfig(
        num_nodes=draw(st.integers(min_value=2, max_value=100)),
        topology_type=draw(st.sampled_from(['mesh', 'star', 'ring', 'custom'])),
        routing_algorithm=draw(st.sampled_from(['dijkstra', 'distance_vector'])),
        transport_protocol=draw(st.sampled_from(['gbn', 'sr'])),
        window_size=draw(st.integers(min_value=1, max_value=1024)),
        timeout_ms=draw(st.integers(min_value=1, max_value=60000)),
        error_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        loss_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        enable_optimization=draw(st.booleans()),
        capture_packets=draw(st.booleans())
    )


# Property tests for serialization round-trip

class TestPacketSerialization:
    """Property tests for Packet serialization."""
    
    @settings(max_examples=100)
    @given(packet=packet_strategy())
    def test_packet_dict_round_trip(self, packet):
        """
        Property: For any Packet, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        # Serialize to dict and deserialize
        serialized = packet.to_dict()
        deserialized = Packet.from_dict(serialized)
        
        # Verify all fields match
        assert deserialized.packet_id == packet.packet_id
        assert deserialized.timestamp == packet.timestamp
        assert deserialized.source_ip == packet.source_ip
        assert deserialized.dest_ip == packet.dest_ip
        assert deserialized.protocol == packet.protocol
        assert deserialized.payload == packet.payload
        assert deserialized.headers == packet.headers
    
    @settings(max_examples=100)
    @given(packet=packet_strategy())
    def test_packet_json_round_trip(self, packet):
        """
        Property: For any Packet, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        # Serialize to JSON and deserialize
        json_str = packet.to_json()
        deserialized = Packet.from_json(json_str)
        
        # Verify all fields match
        assert deserialized.packet_id == packet.packet_id
        assert deserialized.timestamp == packet.timestamp
        assert deserialized.source_ip == packet.source_ip
        assert deserialized.dest_ip == packet.dest_ip
        assert deserialized.protocol == packet.protocol
        assert deserialized.payload == packet.payload
        assert deserialized.headers == packet.headers


class TestSegmentSerialization:
    """Property tests for Segment serialization."""
    
    @settings(max_examples=100)
    @given(segment=segment_strategy())
    def test_segment_dict_round_trip(self, segment):
        """
        Property: For any Segment, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = segment.to_dict()
        deserialized = Segment.from_dict(serialized)
        
        assert deserialized.sequence_num == segment.sequence_num
        assert deserialized.ack_num == segment.ack_num
        assert deserialized.window_size == segment.window_size
        assert deserialized.flags == segment.flags
        assert deserialized.data == segment.data
        assert deserialized.checksum == segment.checksum
    
    @settings(max_examples=100)
    @given(segment=segment_strategy())
    def test_segment_json_round_trip(self, segment):
        """
        Property: For any Segment, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = segment.to_json()
        deserialized = Segment.from_json(json_str)
        
        assert deserialized.sequence_num == segment.sequence_num
        assert deserialized.ack_num == segment.ack_num
        assert deserialized.window_size == segment.window_size
        assert deserialized.flags == segment.flags
        assert deserialized.data == segment.data
        assert deserialized.checksum == segment.checksum


class TestFrameSerialization:
    """Property tests for Frame serialization."""
    
    @settings(max_examples=100)
    @given(frame=frame_strategy())
    def test_frame_dict_round_trip(self, frame):
        """
        Property: For any Frame, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = frame.to_dict()
        deserialized = Frame.from_dict(serialized)
        
        assert deserialized.preamble == frame.preamble
        assert deserialized.dest_mac == frame.dest_mac
        assert deserialized.source_mac == frame.source_mac
        assert deserialized.payload == frame.payload
        assert deserialized.crc == frame.crc
        assert deserialized.error_corrected == frame.error_corrected
    
    @settings(max_examples=100)
    @given(frame=frame_strategy())
    def test_frame_json_round_trip(self, frame):
        """
        Property: For any Frame, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = frame.to_json()
        deserialized = Frame.from_json(json_str)
        
        assert deserialized.preamble == frame.preamble
        assert deserialized.dest_mac == frame.dest_mac
        assert deserialized.source_mac == frame.source_mac
        assert deserialized.payload == frame.payload
        assert deserialized.crc == frame.crc
        assert deserialized.error_corrected == frame.error_corrected


class TestRouteEntrySerialization:
    """Property tests for RouteEntry serialization."""
    
    @settings(max_examples=100)
    @given(entry=route_entry_strategy())
    def test_route_entry_dict_round_trip(self, entry):
        """
        Property: For any RouteEntry, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = entry.to_dict()
        deserialized = RouteEntry.from_dict(serialized)
        
        assert deserialized.destination == entry.destination
        assert deserialized.next_hop == entry.next_hop
        assert deserialized.cost == entry.cost
        assert deserialized.interface == entry.interface
        assert deserialized.timestamp == entry.timestamp
        assert deserialized.metric_type == entry.metric_type
    
    @settings(max_examples=100)
    @given(entry=route_entry_strategy())
    def test_route_entry_json_round_trip(self, entry):
        """
        Property: For any RouteEntry, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = entry.to_json()
        deserialized = RouteEntry.from_json(json_str)
        
        assert deserialized.destination == entry.destination
        assert deserialized.next_hop == entry.next_hop
        assert deserialized.cost == entry.cost
        assert deserialized.interface == entry.interface
        assert deserialized.timestamp == entry.timestamp
        assert deserialized.metric_type == entry.metric_type


class TestLinkSerialization:
    """Property tests for Link serialization."""
    
    @settings(max_examples=100)
    @given(link=link_strategy())
    def test_link_dict_round_trip(self, link):
        """
        Property: For any Link, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = link.to_dict()
        deserialized = Link.from_dict(serialized)
        
        assert deserialized.node_a == link.node_a
        assert deserialized.node_b == link.node_b
        assert deserialized.cost == link.cost
        assert deserialized.capacity == link.capacity
        assert deserialized.utilization == link.utilization
        assert deserialized.latency == link.latency
        assert deserialized.loss_rate == link.loss_rate
    
    @settings(max_examples=100)
    @given(link=link_strategy())
    def test_link_json_round_trip(self, link):
        """
        Property: For any Link, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = link.to_json()
        deserialized = Link.from_json(json_str)
        
        assert deserialized.node_a == link.node_a
        assert deserialized.node_b == link.node_b
        assert deserialized.cost == link.cost
        assert deserialized.capacity == link.capacity
        assert deserialized.utilization == link.utilization
        assert deserialized.latency == link.latency
        assert deserialized.loss_rate == link.loss_rate


class TestNetworkTopologySerialization:
    """Property tests for NetworkTopology serialization."""
    
    @settings(max_examples=100)
    @given(topology=network_topology_strategy())
    def test_topology_dict_round_trip(self, topology):
        """
        Property: For any NetworkTopology, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = topology.to_dict()
        deserialized = NetworkTopology.from_dict(serialized)
        
        assert deserialized.nodes == topology.nodes
        assert len(deserialized.links) == len(topology.links)
        assert np.array_equal(deserialized.adjacency_matrix, topology.adjacency_matrix)
    
    @settings(max_examples=100)
    @given(topology=network_topology_strategy())
    def test_topology_json_round_trip(self, topology):
        """
        Property: For any NetworkTopology, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = topology.to_json()
        deserialized = NetworkTopology.from_json(json_str)
        
        assert deserialized.nodes == topology.nodes
        assert len(deserialized.links) == len(topology.links)
        assert np.array_equal(deserialized.adjacency_matrix, topology.adjacency_matrix)


class TestNetworkMetricsSerialization:
    """Property tests for NetworkMetrics serialization."""
    
    @settings(max_examples=100)
    @given(metrics=network_metrics_strategy())
    def test_metrics_dict_round_trip(self, metrics):
        """
        Property: For any NetworkMetrics, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = metrics.to_dict()
        deserialized = NetworkMetrics.from_dict(serialized)
        
        assert deserialized.timestamp == metrics.timestamp
        assert deserialized.throughput == metrics.throughput
        assert deserialized.latency == metrics.latency
        assert deserialized.packet_loss == metrics.packet_loss
        assert deserialized.retransmissions == metrics.retransmissions
        assert deserialized.jitter == metrics.jitter
        assert deserialized.active_connections == metrics.active_connections
        assert deserialized.queue_depth == metrics.queue_depth
    
    @settings(max_examples=100)
    @given(metrics=network_metrics_strategy())
    def test_metrics_json_round_trip(self, metrics):
        """
        Property: For any NetworkMetrics, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = metrics.to_json()
        deserialized = NetworkMetrics.from_json(json_str)
        
        assert deserialized.timestamp == metrics.timestamp
        assert deserialized.throughput == metrics.throughput
        assert deserialized.latency == metrics.latency
        assert deserialized.packet_loss == metrics.packet_loss
        assert deserialized.retransmissions == metrics.retransmissions
        assert deserialized.jitter == metrics.jitter
        assert deserialized.active_connections == metrics.active_connections
        assert deserialized.queue_depth == metrics.queue_depth


class TestEmulatorConfigSerialization:
    """Property tests for EmulatorConfig serialization."""
    
    @settings(max_examples=100)
    @given(config=emulator_config_strategy())
    def test_config_dict_round_trip(self, config):
        """
        Property: For any EmulatorConfig, to_dict followed by from_dict produces equivalent object.
        Validates: Requirements 11.3
        """
        serialized = config.to_dict()
        deserialized = EmulatorConfig.from_dict(serialized)
        
        assert deserialized.num_nodes == config.num_nodes
        assert deserialized.topology_type == config.topology_type
        assert deserialized.routing_algorithm == config.routing_algorithm
        assert deserialized.transport_protocol == config.transport_protocol
        assert deserialized.window_size == config.window_size
        assert deserialized.timeout_ms == config.timeout_ms
        assert deserialized.error_rate == config.error_rate
        assert deserialized.loss_rate == config.loss_rate
        assert deserialized.enable_optimization == config.enable_optimization
        assert deserialized.capture_packets == config.capture_packets
    
    @settings(max_examples=100)
    @given(config=emulator_config_strategy())
    def test_config_json_round_trip(self, config):
        """
        Property: For any EmulatorConfig, to_json followed by from_json produces equivalent object.
        Validates: Requirements 11.3
        """
        json_str = config.to_json()
        deserialized = EmulatorConfig.from_json(json_str)
        
        assert deserialized.num_nodes == config.num_nodes
        assert deserialized.topology_type == config.topology_type
        assert deserialized.routing_algorithm == config.routing_algorithm
        assert deserialized.transport_protocol == config.transport_protocol
        assert deserialized.window_size == config.window_size
        assert deserialized.timeout_ms == config.timeout_ms
        assert deserialized.error_rate == config.error_rate
        assert deserialized.loss_rate == config.loss_rate
        assert deserialized.enable_optimization == config.enable_optimization
        assert deserialized.capture_packets == config.capture_packets
