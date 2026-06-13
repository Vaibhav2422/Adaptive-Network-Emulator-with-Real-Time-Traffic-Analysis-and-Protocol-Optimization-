"""
Unit tests for Dijkstra Router implementation.

Tests specific scenarios and edge cases for the Dijkstra routing algorithm.
"""

import pytest
import time
from src.dijkstra_router import DijkstraRouter, LinkStateEntry
from src.data_models import NetworkTopology, Link, RouteEntry


class TestDijkstraRouterInitialization:
    """Test DijkstraRouter initialization."""
    
    def test_initialization(self):
        """Test basic router initialization."""
        router = DijkstraRouter("node_1")
        
        assert router.node_id == "node_1"
        assert len(router.link_state_db) == 0
        assert router.routing_table.size() == 0
        assert router.sequence_num == 0
    
    def test_multiple_routers(self):
        """Test creating multiple independent routers."""
        router1 = DijkstraRouter("node_1")
        router2 = DijkstraRouter("node_2")
        
        assert router1.node_id != router2.node_id
        assert router1.link_state_db is not router2.link_state_db


class TestLinkStateDatabase:
    """Test link-state database management."""
    
    def test_update_link_state_new_entry(self):
        """Test adding new link-state entry."""
        router = DijkstraRouter("node_1")
        
        neighbors = {"node_2": 10.0, "node_3": 20.0}
        router.update_link_state("node_1", neighbors)
        
        assert "node_1" in router.link_state_db
        assert router.link_state_db["node_1"].neighbors == neighbors
        assert router.link_state_db["node_1"].sequence_num == 0
    
    def test_update_link_state_existing_entry(self):
        """Test updating existing link-state entry."""
        router = DijkstraRouter("node_1")
        
        # Initial update
        neighbors1 = {"node_2": 10.0}
        router.update_link_state("node_1", neighbors1)
        initial_seq = router.link_state_db["node_1"].sequence_num
        
        # Update with new neighbors
        neighbors2 = {"node_2": 15.0, "node_3": 20.0}
        router.update_link_state("node_1", neighbors2)
        
        assert router.link_state_db["node_1"].neighbors == neighbors2
        assert router.link_state_db["node_1"].sequence_num == initial_seq + 1
    
    def test_update_topology(self):
        """Test updating link-state database from topology."""
        router = DijkstraRouter("node_1")
        
        # Create simple topology
        nodes = ["node_1", "node_2", "node_3"]
        links = [
            Link("node_1", "node_2", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_2", "node_3", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        
        # Verify all nodes in link-state database
        assert len(router.link_state_db) == 3
        assert "node_1" in router.link_state_db
        assert "node_2" in router.link_state_db
        assert "node_3" in router.link_state_db
        
        # Verify bidirectional links
        assert router.link_state_db["node_1"].neighbors["node_2"] == 10.0
        assert router.link_state_db["node_2"].neighbors["node_1"] == 10.0
        assert router.link_state_db["node_2"].neighbors["node_3"] == 15.0
        assert router.link_state_db["node_3"].neighbors["node_2"] == 15.0
    
    def test_clear_link_state_db(self):
        """Test clearing link-state database."""
        router = DijkstraRouter("node_1")
        
        neighbors = {"node_2": 10.0}
        router.update_link_state("node_1", neighbors)
        
        assert len(router.link_state_db) > 0
        
        router.clear_link_state_db()
        
        assert len(router.link_state_db) == 0
    
    def test_get_link_state_db(self):
        """Test getting copy of link-state database."""
        router = DijkstraRouter("node_1")
        
        neighbors = {"node_2": 10.0}
        router.update_link_state("node_1", neighbors)
        
        db_copy = router.get_link_state_db()
        
        # Verify it's a copy
        assert db_copy is not router.link_state_db
        assert "node_1" in db_copy


class TestShortestPathComputation:
    """Test Dijkstra's shortest path computation."""
    
    def test_simple_linear_topology(self):
        """Test shortest paths in linear topology: A -- B -- C."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Verify paths
        assert "node_b" in paths
        assert "node_c" in paths
        
        # Path to B: direct link, cost 10
        cost_b, next_hop_b = paths["node_b"]
        assert cost_b == 10.0
        assert next_hop_b == "node_b"
        
        # Path to C: through B, cost 25
        cost_c, next_hop_c = paths["node_c"]
        assert cost_c == 25.0
        assert next_hop_c == "node_b"  # Next hop is B
    
    def test_triangle_topology(self):
        """Test shortest paths in triangle topology."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 30.0, 0.0, 0.0, 0.0, 0.0)  # Longer direct path
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Path to C should go through B (cost 25) not direct (cost 30)
        cost_c, next_hop_c = paths["node_c"]
        assert cost_c == 25.0
        assert next_hop_c == "node_b"
    
    def test_disconnected_node(self):
        """Test with disconnected node."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)
            # node_c is disconnected
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Should have path to B but not to C
        assert "node_b" in paths
        assert "node_c" not in paths
    
    def test_single_node(self):
        """Test with single node (no paths)."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a"]
        links = []
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # No paths (only source node)
        assert len(paths) == 0
    
    def test_multiple_equal_cost_paths(self):
        """Test with multiple equal-cost paths."""
        router = DijkstraRouter("node_a")
        
        # Diamond topology with equal costs
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Path to D should have cost 20 (through either B or C)
        cost_d, next_hop_d = paths["node_d"]
        assert cost_d == 20.0
        assert next_hop_d in ["node_b", "node_c"]


class TestRoutingTableGeneration:
    """Test routing table generation from shortest paths."""
    
    def test_generate_routing_table(self):
        """Test generating routing table from computed paths."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        routing_table = router.generate_routing_table()
        
        # Should have entries for B and C
        assert routing_table.size() == 2
        
        # Check entry for B
        route_b = routing_table.get("node_b")
        assert route_b is not None
        assert route_b.destination == "node_b"
        assert route_b.next_hop == "node_b"
        assert route_b.cost == 10.0
        
        # Check entry for C
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.destination == "node_c"
        assert route_c.next_hop == "node_b"
        assert route_c.cost == 25.0
    
    def test_routing_table_with_custom_interface(self):
        """Test routing table generation with custom interface."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b"]
        links = [Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        routing_table = router.generate_routing_table(interface="eth1")
        
        route = routing_table.get("node_b")
        assert route.interface == "eth1"
    
    def test_routing_table_with_custom_metric_type(self):
        """Test routing table generation with custom metric type."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b"]
        links = [Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        routing_table = router.generate_routing_table(metric_type="latency")
        
        route = routing_table.get("node_b")
        assert route.metric_type == "latency"
    
    def test_routing_table_cleared_on_regeneration(self):
        """Test that routing table is cleared when regenerated."""
        router = DijkstraRouter("node_a")
        
        # First topology
        nodes1 = ["node_a", "node_b", "node_c"]
        links1 = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology1 = NetworkTopology(nodes1, links1)
        
        router.update_topology(topology1)
        routing_table1 = router.generate_routing_table()
        
        assert routing_table1.size() == 2
        
        # Second topology (smaller)
        nodes2 = ["node_a", "node_b"]
        links2 = [Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0)]
        topology2 = NetworkTopology(nodes2, links2)
        
        router.update_topology(topology2)
        routing_table2 = router.generate_routing_table()
        
        # Should only have 1 entry now
        assert routing_table2.size() == 1
        assert routing_table2.get("node_c") is None


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_topology(self):
        """Test with empty topology."""
        router = DijkstraRouter("node_a")
        
        topology = NetworkTopology(nodes=[], links=[])
        router.update_topology(topology)
        
        paths = router.compute_shortest_paths()
        assert len(paths) == 0
    
    def test_self_loop_ignored(self):
        """Test that self-loops are handled correctly."""
        router = DijkstraRouter("node_a")
        
        # Manually add self-loop in link-state
        router.update_link_state("node_a", {"node_a": 5.0, "node_b": 10.0})
        router.update_link_state("node_b", {"node_a": 10.0})
        
        paths = router.compute_shortest_paths()
        
        # Should still find path to B
        assert "node_b" in paths
        cost_b, _ = paths["node_b"]
        assert cost_b == 10.0
    
    def test_zero_cost_link(self):
        """Test with zero-cost link."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b"]
        links = [Link("node_a", "node_b", 0.0, 0.0, 0.0, 0.0, 0.0)]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        cost_b, _ = paths["node_b"]
        assert cost_b == 0.0
    
    def test_large_cost_values(self):
        """Test with large cost values."""
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 1000000.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 2000000.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        cost_c, _ = paths["node_c"]
        assert cost_c == 3000000.0
