"""
Simplified integration tests for packet forwarding.

Tests packet forwarding correctness by verifying:
- Packets can be forwarded through routing tables
- Next hop lookups work correctly
- Routing tables are populated correctly from routing algorithms
"""

import pytest
import time
from src.network_layer import NetworkLayer
from src.dijkstra_router import DijkstraRouter
from src.distance_vector_router import DistanceVectorRouter
from src.data_models import Packet, NetworkTopology, Link


class TestPacketForwardingBasics:
    """Test basic packet forwarding functionality."""
    
    def test_forward_packet_to_destination(self):
        """Test that packet is delivered when it reaches destination."""
        node = NetworkLayer("node_a", "192.168.1.1")
        
        packet = Packet(
            packet_id="pkt_1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="192.168.1.1",  # This node's IP
            protocol="TCP",
            payload=b"test"
        )
        
        # Should return None (packet delivered)
        next_hop = node.forward_packet(packet)
        assert next_hop is None
    
    def test_forward_packet_with_route(self):
        """Test that packet is forwarded using routing table."""
        node = NetworkLayer("node_a", "192.168.1.1")
        
        # Set up topology and compute routes
        nodes = ["node_a", "node_b"]
        links = [Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)]
        topology = NetworkTopology(nodes, links)
        
        router = DijkstraRouter("node_a")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Install routes
        for dest, route in routing_table.get_all().items():
            node.add_route(route)
        
        # Create packet to node_b
        packet = Packet(
            packet_id="pkt_2",
            timestamp=time.time(),
            source_ip="192.168.1.1",
            dest_ip="node_b",  # Using node ID as destination
            protocol="TCP",
            payload=b"test"
        )
        
        # Should return next hop
        next_hop = node.forward_packet(packet)
        assert next_hop is not None
        assert next_hop == "node_b"
    
    def test_forward_packet_no_route(self):
        """Test that packet forwarding fails when no route exists."""
        node = NetworkLayer("node_a", "192.168.1.1")
        
        packet = Packet(
            packet_id="pkt_3",
            timestamp=time.time(),
            source_ip="192.168.1.1",
            dest_ip="10.0.0.1",  # No route to this destination
            protocol="TCP",
            payload=b"test"
        )
        
        # Should return None (no route)
        next_hop = node.forward_packet(packet)
        assert next_hop is None


class TestRoutingTablePopulation:
    """Test that routing tables are populated correctly from routing algorithms."""
    
    def test_dijkstra_populates_routing_table(self):
        """Test that Dijkstra algorithm populates routing table correctly."""
        # Create simple topology: A -- B -- C
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for node_a
        router = DijkstraRouter("node_a")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Verify routing table has entries
        assert routing_table.size() > 0
        
        # Verify route to node_b exists
        route_b = routing_table.get("node_b")
        assert route_b is not None
        assert route_b.destination == "node_b"
        assert route_b.next_hop == "node_b"
        assert route_b.cost == 10.0
        
        # Verify route to node_c exists
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.destination == "node_c"
        assert route_c.next_hop == "node_b"  # Via node_b
        assert route_c.cost == 25.0
    
    def test_distance_vector_populates_routing_table(self):
        """Test that Distance Vector algorithm populates routing table correctly."""
        # Create routers
        router_a = DistanceVectorRouter("node_a")
        router_b = DistanceVectorRouter("node_b")
        
        # Set up topology
        nodes = ["node_a", "node_b"]
        links = [Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)]
        topology = NetworkTopology(nodes, links)
        
        router_a.update_topology(topology)
        router_b.update_topology(topology)
        
        # Exchange distance vectors
        dv_b = router_b.get_distance_vector()
        router_a.receive_distance_vector(dv_b)
        
        # Generate routing table
        routing_table = router_a.generate_routing_table()
        
        # Verify routing table has entry for node_b
        assert routing_table.size() > 0
        route_b = routing_table.get("node_b")
        assert route_b is not None
        assert route_b.destination == "node_b"
        assert route_b.next_hop == "node_b"
        assert route_b.cost == 10.0
    
    def test_routing_table_with_multiple_destinations(self):
        """Test routing table with multiple destinations."""
        # Create topology: A -- B -- C -- D
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for node_a
        router = DijkstraRouter("node_a")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Verify all destinations are reachable
        assert routing_table.size() == 3  # B, C, D
        
        # Verify each route
        route_b = routing_table.get("node_b")
        assert route_b is not None
        assert route_b.cost == 10.0
        
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.cost == 25.0
        assert route_c.next_hop == "node_b"
        
        route_d = routing_table.get("node_d")
        assert route_d is not None
        assert route_d.cost == 45.0
        assert route_d.next_hop == "node_b"


class TestMultiHopForwarding:
    """Test multi-hop packet forwarding scenarios."""
    
    def test_3_hop_forwarding_logic(self):
        """
        Test 3-hop forwarding logic.
        
        Topology: A -- B -- C -- D
        Test: Verify routing tables allow forwarding from A to D
        """
        # Create topology
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for each node
        routing_tables = {}
        for node_id in nodes:
            router = DijkstraRouter(node_id)
            router.update_topology(topology)
            routing_tables[node_id] = router.generate_routing_table()
        
        # Verify node_a can reach node_d
        route_d_from_a = routing_tables["node_a"].get("node_d")
        assert route_d_from_a is not None
        assert route_d_from_a.next_hop == "node_b"
        
        # Verify node_b can reach node_d
        route_d_from_b = routing_tables["node_b"].get("node_d")
        assert route_d_from_b is not None
        assert route_d_from_b.next_hop == "node_c"
        
        # Verify node_c can reach node_d
        route_d_from_c = routing_tables["node_c"].get("node_d")
        assert route_d_from_c is not None
        assert route_d_from_c.next_hop == "node_d"
        
        # This demonstrates that packets can be forwarded hop-by-hop
        # A -> B -> C -> D using the routing tables
    
    def test_mesh_topology_routing(self):
        """
        Test routing in mesh topology with multiple paths.
        
        Topology:
        A --5-- B --10-- D
        |       |        |
        15      8        5
        |       |        |
        C ------+--12--- E
        """
        nodes = ["node_a", "node_b", "node_c", "node_d", "node_e"]
        links = [
            Link("node_a", "node_b", 5.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 8.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_e", 12.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_d", "node_e", 5.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for node_a
        router = DijkstraRouter("node_a")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Verify shortest path to node_e is via B->D (cost 20)
        route_e = routing_table.get("node_e")
        assert route_e is not None
        assert route_e.cost == 20.0
        assert route_e.next_hop == "node_b"
    
    def test_star_topology_routing(self):
        """
        Test routing in star topology.
        
        All nodes connect through central node A.
        """
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for node_b
        router = DijkstraRouter("node_b")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Verify all routes go through node_a
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.next_hop == "node_a"
        assert route_c.cost == 20.0
        
        route_d = routing_table.get("node_d")
        assert route_d is not None
        assert route_d.next_hop == "node_a"
        assert route_d.cost == 20.0
    
    def test_ring_topology_routing(self):
        """
        Test routing in ring topology.
        
        Topology: A --- B
                  |     |
                  D --- C
        """
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_d", "node_a", 10.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        # Compute routes for node_a
        router = DijkstraRouter("node_a")
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Verify shortest paths (2 hops max in ring of 4)
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.cost == 20.0  # 2 hops
        
        # Path should be either A->B->C or A->D->C (both cost 20)
        assert route_c.next_hop in ["node_b", "node_d"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
