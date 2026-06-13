"""
Integration tests for end-to-end communication through all layers.

Tests message transmission, file transfer, and behavior under various
network conditions (error rates, loss rates).

Feature: adaptive-network-emulator
Validates: Requirements 1.1, 1.2, 2.1, 2.2
"""

import pytest
from src.node import Node, NodeConfig
from src.network_topology import NetworkTopology, TopologyConfig
from src.physical_layer import PhysicalLayer, PhysicalLayerConfig


class TestEndToEndCommunication:
    """Integration tests for end-to-end communication."""
    
    def test_message_transmission_through_all_layers(self):
        """
        Test message transmission through all layers.
        
        Validates: Requirements 1.1, 1.2, 2.1
        """
        # Create a simple two-node topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            base_ip="192.168.1.0",
            transport_protocol="GBN",
            window_size=8,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        
        # Add two nodes
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        
        # Add link between nodes
        topology.add_link("node_a", "node_b", cost=1.0)
        
        # Send message from node_a to node_b
        message = "Hello from node_a!"
        dest_ip = node_b.get_ip_address()
        
        # Send message
        success = node_a.send_message(dest_ip, message, protocol="TCP")
        
        # Verify message was sent
        assert success, "Message should be sent successfully"
        
        # Verify node statistics
        stats_a = node_a.get_statistics()
        assert stats_a['node_id'] == "node_a"
        assert stats_a['ip_address'] == "192.168.1.1"
    
    def test_message_transmission_with_different_protocols(self):
        """
        Test message transmission with TCP and UDP protocols.
        
        Validates: Requirements 2.1
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Test TCP
        message_tcp = "TCP message"
        success_tcp = node_a.send_message(node_b.get_ip_address(), message_tcp, "TCP")
        assert success_tcp, "TCP message should be sent"
        
        # Test UDP
        message_udp = "UDP message"
        success_udp = node_a.send_message(node_b.get_ip_address(), message_udp, "UDP")
        assert success_udp, "UDP message should be sent"
    
    def test_message_transmission_with_packet_loss(self):
        """
        Test message transmission with packet loss.
        
        Validates: Requirements 1.1, 1.2
        """
        # Create topology with 10% packet loss
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            window_size=8,
            loss_rate=0.1,  # 10% loss
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Send message
        message = "Message with potential loss"
        success = node_a.send_message(node_b.get_ip_address(), message, "TCP")
        
        # Message should still be sent (transport layer handles retransmission)
        assert success, "Message should be sent despite packet loss"
    
    def test_message_transmission_with_bit_errors(self):
        """
        Test message transmission with bit errors.
        
        Validates: Requirements 1.1, 1.2, 5.6, 5.8
        """
        # Create topology with bit errors
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            window_size=8,
            loss_rate=0.0,
            bit_error_rate=0.0001,  # 0.01% bit error rate
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Send message
        message = "Message with potential bit errors"
        success = node_a.send_message(node_b.get_ip_address(), message, "TCP")
        
        # Message should be sent (error correction handles single-bit errors)
        assert success, "Message should be sent despite bit errors"
    
    def test_multiple_messages_sequential(self):
        """
        Test sending multiple messages sequentially.
        
        Validates: Requirements 1.1, 2.1
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Send multiple messages
        messages = [
            "First message",
            "Second message",
            "Third message",
            "Fourth message",
            "Fifth message"
        ]
        
        for i, message in enumerate(messages):
            success = node_a.send_message(node_b.get_ip_address(), message, "TCP")
            assert success, f"Message {i+1} should be sent successfully"
    
    def test_bidirectional_communication(self):
        """
        Test bidirectional communication between nodes.
        
        Validates: Requirements 1.1, 2.1
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Send message from A to B
        message_a_to_b = "Hello from A"
        success_a = node_a.send_message(node_b.get_ip_address(), message_a_to_b, "TCP")
        assert success_a, "Message from A to B should be sent"
        
        # Send message from B to A
        message_b_to_a = "Hello from B"
        success_b = node_b.send_message(node_a.get_ip_address(), message_b_to_a, "TCP")
        assert success_b, "Message from B to A should be sent"
    
    def test_mesh_topology_communication(self):
        """
        Test communication in a mesh topology.
        
        Validates: Requirements 1.1, 11.2
        """
        # Create mesh topology
        config = TopologyConfig(
            topology_type="mesh",
            num_nodes=3,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        topology.build_mesh_topology()
        
        # Get nodes
        nodes = topology.get_all_nodes()
        assert len(nodes) == 3, "Should have 3 nodes"
        
        # Get node IDs
        node_ids = list(nodes.keys())
        
        # Test communication between all pairs
        for i in range(len(node_ids)):
            for j in range(len(node_ids)):
                if i != j:
                    source_node = nodes[node_ids[i]]
                    dest_node = nodes[node_ids[j]]
                    
                    message = f"Message from {node_ids[i]} to {node_ids[j]}"
                    success = source_node.send_message(
                        dest_node.get_ip_address(),
                        message,
                        "TCP"
                    )
                    assert success, f"Message from {node_ids[i]} to {node_ids[j]} should be sent"
    
    def test_star_topology_communication(self):
        """
        Test communication in a star topology.
        
        Validates: Requirements 1.1, 11.2
        """
        # Create star topology
        config = TopologyConfig(
            topology_type="star",
            num_nodes=4,  # 1 center + 3 peripheral
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        topology.build_star_topology()
        
        # Get nodes
        nodes = topology.get_all_nodes()
        assert len(nodes) == 4, "Should have 4 nodes"
        
        # Get center node
        center_node = nodes.get("node_center")
        assert center_node is not None, "Center node should exist"
        
        # Test communication from center to peripherals
        for node_id, node in nodes.items():
            if node_id != "node_center":
                message = f"Message from center to {node_id}"
                success = center_node.send_message(
                    node.get_ip_address(),
                    message,
                    "TCP"
                )
                assert success, f"Message from center to {node_id} should be sent"
    
    def test_ring_topology_communication(self):
        """
        Test communication in a ring topology.
        
        Validates: Requirements 1.1, 11.2
        """
        # Create ring topology
        config = TopologyConfig(
            topology_type="ring",
            num_nodes=4,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        topology.build_ring_topology()
        
        # Get nodes
        nodes = topology.get_all_nodes()
        assert len(nodes) == 4, "Should have 4 nodes"
        
        # Test communication around the ring
        node_ids = sorted(nodes.keys())
        for i in range(len(node_ids)):
            next_i = (i + 1) % len(node_ids)
            source_node = nodes[node_ids[i]]
            dest_node = nodes[node_ids[next_i]]
            
            message = f"Message from {node_ids[i]} to {node_ids[next_i]}"
            success = source_node.send_message(
                dest_node.get_ip_address(),
                message,
                "TCP"
            )
            assert success, f"Message from {node_ids[i]} to {node_ids[next_i]} should be sent"
    
    def test_topology_info_retrieval(self):
        """
        Test retrieving topology information.
        
        Validates: Requirement 11.2
        """
        # Create topology
        config = TopologyConfig(
            topology_type="mesh",
            num_nodes=3,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        topology.build_mesh_topology()
        
        # Get topology info
        info = topology.get_topology_info()
        
        # Verify info structure
        assert 'type' in info
        assert 'num_nodes' in info
        assert 'num_links' in info
        assert 'nodes' in info
        assert 'links' in info
        
        # Verify values
        assert info['type'] == "mesh"
        assert info['num_nodes'] == 3
        assert info['num_links'] == 3  # Full mesh with 3 nodes has 3 links
        
        # Verify node info
        for node_id, node_info in info['nodes'].items():
            assert 'ip' in node_info
            assert 'mac' in node_info
            assert 'neighbors' in node_info
    
    def test_node_statistics(self):
        """
        Test retrieving node statistics.
        
        Validates: Requirements 1.1, 1.2
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Send some messages
        for i in range(5):
            node_a.send_message(node_b.get_ip_address(), f"Message {i}", "TCP")
        
        # Get statistics
        stats = node_a.get_statistics()
        
        # Verify statistics structure
        assert 'node_id' in stats
        assert 'ip_address' in stats
        assert 'mac_address' in stats
        assert 'data_link' in stats
        assert 'mac' in stats
        assert 'transport' in stats
        assert 'routing_table' in stats
        
        # Verify values
        assert stats['node_id'] == "node_a"
        assert stats['ip_address'] == "192.168.1.1"
        
        # Verify data link statistics
        dl_stats = stats['data_link']
        assert 'frames_sent' in dl_stats
        assert 'frames_received' in dl_stats
        
        # Verify MAC statistics
        mac_stats = stats['mac']
        assert 'total_transmissions' in mac_stats
        assert 'successful_transmissions' in mac_stats


class TestFileTransfer:
    """Integration tests for file transfer through all layers."""
    
    def test_file_transfer_simulation(self):
        """
        Test simulated file transfer through all layers.
        
        Note: This is a simplified test that simulates file transfer
        by sending file-like data through the protocol stack.
        
        Validates: Requirements 2.2
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Simulate file data
        file_data = b"This is simulated file content" * 100  # ~3KB
        file_message = f"FILE:{file_data.hex()}"
        
        # Send file data
        success = node_a.send_message(node_b.get_ip_address(), file_message, "TCP")
        assert success, "File data should be sent successfully"
    
    def test_large_data_transfer(self):
        """
        Test transfer of large data through all layers.
        
        Validates: Requirements 1.1, 1.2, 2.2
        """
        # Create topology
        config = TopologyConfig(
            topology_type="custom",
            num_nodes=2,
            transport_protocol="GBN",
            window_size=16,  # Larger window for large data
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        
        topology = NetworkTopology(config)
        node_a = topology.add_node("node_a", ip_address="192.168.1.1")
        node_b = topology.add_node("node_b", ip_address="192.168.1.2")
        topology.add_link("node_a", "node_b")
        
        # Create large message (10KB)
        large_message = "X" * 10000
        
        # Send large message
        success = node_a.send_message(node_b.get_ip_address(), large_message, "TCP")
        assert success, "Large message should be sent successfully"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
