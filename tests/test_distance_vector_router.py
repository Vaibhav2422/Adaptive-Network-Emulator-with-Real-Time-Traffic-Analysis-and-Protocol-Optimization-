"""
Unit tests for Distance Vector Router implementation.

Tests specific scenarios and edge cases for the Distance Vector routing algorithm.
"""

import pytest
import time
from src.distance_vector_router import DistanceVectorRouter, DistanceVector
from src.data_models import NetworkTopology, Link, RouteEntry


class TestDistanceVectorRouterInitialization:
    """Test DistanceVectorRouter initialization."""
    
    def test_initialization(self):
        """Test basic router initialization."""
        router = DistanceVectorRouter("node_1")
        
        assert router.node_id == "node_1"
        assert len(router.neighbors) == 0
        assert len(router.distance_vectors) == 0
        assert router.routing_table.size() == 0
        assert router.my_distance_vector == {"node_1": 0.0}
    
    def test_multiple_routers(self):
        """Test creating multiple independent routers."""
        router1 = DistanceVectorRouter("node_1")
        router2 = DistanceVectorRouter("node_2")
        
        assert router1.node_id != router2.node_id
        assert router1.neighbors is not router2.neighbors
        assert router1.my_distance_vector is not router2.my_distance_vector


class TestNeighborManagement:
    """Test neighbor management."""
    
    def test_update_neighbors(self):
        """Test updating neighbor list."""
        router = DistanceVectorRouter("node_1")
        
        neighbors = {"node_2": 10.0, "node_3": 20.0}
        router.update_neighbors(neighbors)
        
        assert router.neighbors == neighbors
        assert router.my_distance_vector["node_2"] == 10.0
        assert router.my_distance_vector["node_3"] == 20.0
    
    def test_update_neighbors_replaces_old(self):
        """Test that updating neighbors replaces old neighbor list."""
        router = DistanceVectorRouter("node_1")
        
        # Initial neighbors
        neighbors1 = {"node_2": 10.0, "node_3": 20.0}
        router.update_neighbors(neighbors1)
        
        # Update with different neighbors
        neighbors2 = {"node_2": 15.0, "node_4": 25.0}
        router.update_neighbors(neighbors2)
        
        assert router.neighbors == neighbors2
        assert "node_3" not in router.neighbors
        assert "node_4" in router.neighbors
    
    def test_update_topology(self):
        """Test updating neighbors from topology."""
        router = DistanceVectorRouter("node_1")
        
        nodes = ["node_1", "node_2", "node_3"]
        links = [
            Link("node_1", "node_2", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_2", "node_3", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        
        # Should only have node_2 as neighbor
        assert len(router.neighbors) == 1
        assert "node_2" in router.neighbors
        assert router.neighbors["node_2"] == 10.0


class TestDistanceVectorExchange:
    """Test distance vector exchange and processing."""
    
    def test_receive_distance_vector_from_neighbor(self):
        """Test receiving distance vector from a neighbor."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Receive DV from node_2
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        
        changed = router.receive_distance_vector(dv)
        
        assert changed  # Should cause update
        assert "node_2" in router.distance_vectors
        assert router.distance_vectors["node_2"].distances == dv.distances
    
    def test_receive_distance_vector_from_non_neighbor(self):
        """Test receiving distance vector from non-neighbor is rejected."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Try to receive DV from node_3 (not a neighbor)
        dv = DistanceVector(
            node_id="node_3",
            distances={"node_3": 0.0}
        )
        
        changed = router.receive_distance_vector(dv)
        
        assert not changed
        assert "node_3" not in router.distance_vectors
    
    def test_bellman_ford_update_simple(self):
        """Test Bellman-Ford update with simple topology."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Receive DV from node_2 advertising node_3
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        
        router.receive_distance_vector(dv)
        
        # Should learn route to node_3 through node_2
        assert "node_3" in router.my_distance_vector
        assert router.my_distance_vector["node_3"] == 25.0  # 10 + 15
        
        # Check routing table
        route = router.routing_table.get("node_3")
        assert route is not None
        assert route.next_hop == "node_2"
        assert route.cost == 25.0
    
    def test_bellman_ford_chooses_shortest_path(self):
        """Test that Bellman-Ford chooses the shortest path."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0, "node_3": 30.0})
        
        # Receive DV from node_2 advertising shorter path to node_3
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 5.0}
        )
        
        router.receive_distance_vector(dv)
        
        # Should choose path through node_2 (cost 15) over direct (cost 30)
        assert router.my_distance_vector["node_3"] == 15.0
        
        route = router.routing_table.get("node_3")
        assert route.next_hop == "node_2"
    
    def test_bellman_ford_updates_on_better_path(self):
        """Test that Bellman-Ford updates when better path is found."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0, "node_3": 50.0})
        
        # Initially use direct path to node_3
        dv1 = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0}
        )
        router.receive_distance_vector(dv1)
        
        assert router.my_distance_vector["node_3"] == 50.0
        
        # Now node_2 advertises better path to node_3
        dv2 = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        changed = router.receive_distance_vector(dv2)
        
        assert changed
        assert router.my_distance_vector["node_3"] == 25.0  # Better path
        
        route = router.routing_table.get("node_3")
        assert route.next_hop == "node_2"


class TestSplitHorizon:
    """Test split horizon implementation."""
    
    def test_split_horizon_filters_routes(self):
        """Test that split horizon doesn't advertise routes back to source."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Learn route to node_3 through node_2
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        router.receive_distance_vector(dv)
        
        # Get DV for node_2 (should not include node_3)
        dv_for_node2 = router.get_distance_vector(requesting_neighbor="node_2")
        
        assert "node_3" not in dv_for_node2.distances
        assert "node_1" in dv_for_node2.distances  # Own distance
    
    def test_split_horizon_allows_other_routes(self):
        """Test that split horizon allows routes not learned from requester."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0, "node_3": 20.0})
        
        # Learn route to node_4 through node_3
        dv = DistanceVector(
            node_id="node_3",
            distances={"node_3": 0.0, "node_4": 15.0}
        )
        router.receive_distance_vector(dv)
        
        # Get DV for node_2 (should include node_4 since not learned from node_2)
        dv_for_node2 = router.get_distance_vector(requesting_neighbor="node_2")
        
        assert "node_4" in dv_for_node2.distances
        assert dv_for_node2.distances["node_4"] == 35.0  # 20 + 15
    
    def test_get_distance_vector_without_split_horizon(self):
        """Test getting full distance vector without split horizon."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        router.receive_distance_vector(dv)
        
        # Get DV without specifying neighbor (no split horizon)
        full_dv = router.get_distance_vector()
        
        assert "node_3" in full_dv.distances
        assert full_dv.distances["node_3"] == 25.0


class TestRoutingTableGeneration:
    """Test routing table generation."""
    
    def test_generate_routing_table(self):
        """Test generating routing table."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        router.receive_distance_vector(dv)
        
        routing_table = router.generate_routing_table()
        
        assert routing_table.size() == 2
        assert routing_table.get("node_2") is not None
        assert routing_table.get("node_3") is not None
    
    def test_generate_routing_table_with_custom_interface(self):
        """Test routing table generation with custom interface."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Need to trigger routing table creation first
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0}
        )
        router.receive_distance_vector(dv)
        
        routing_table = router.generate_routing_table(interface="eth1")
        
        route = routing_table.get("node_2")
        assert route.interface == "eth1"
    
    def test_generate_routing_table_with_custom_metric_type(self):
        """Test routing table generation with custom metric type."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # Need to trigger routing table creation first
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0}
        )
        router.receive_distance_vector(dv)
        
        routing_table = router.generate_routing_table(metric_type="latency")
        
        route = routing_table.get("node_2")
        assert route.metric_type == "latency"


class TestConvergence:
    """Test convergence detection."""
    
    def test_is_converged_true(self):
        """Test convergence detection when distances haven't changed."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        previous = router.my_distance_vector.copy()
        
        # No changes
        converged = router.is_converged(previous)
        assert converged
    
    def test_is_converged_false(self):
        """Test convergence detection when distances changed."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        previous = router.my_distance_vector.copy()
        
        # Receive new DV causing change
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        router.receive_distance_vector(dv)
        
        converged = router.is_converged(previous)
        assert not converged


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_get_distance_to_reachable(self):
        """Test getting distance to reachable destination."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        distance = router.get_distance_to("node_2")
        assert distance == 10.0
    
    def test_get_distance_to_unreachable(self):
        """Test getting distance to unreachable destination."""
        router = DistanceVectorRouter("node_1")
        
        distance = router.get_distance_to("node_99")
        assert distance is None
    
    def test_clear_distance_vectors(self):
        """Test clearing distance vectors."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0}
        )
        router.receive_distance_vector(dv)
        
        assert len(router.distance_vectors) > 0
        
        router.clear_distance_vectors()
        
        assert len(router.distance_vectors) == 0
    
    def test_get_routing_table(self):
        """Test getting routing table."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        routing_table = router.get_routing_table()
        
        assert routing_table is router.routing_table


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_neighbors(self):
        """Test with no neighbors."""
        router = DistanceVectorRouter("node_1")
        
        # Should only know about itself
        assert len(router.my_distance_vector) == 1
        assert router.my_distance_vector["node_1"] == 0.0
    
    def test_zero_cost_link(self):
        """Test with zero-cost link."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 0.0})
        
        assert router.my_distance_vector["node_2"] == 0.0
    
    def test_large_cost_values(self):
        """Test with large cost values."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 1000000.0})
        
        dv = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 2000000.0}
        )
        router.receive_distance_vector(dv)
        
        assert router.my_distance_vector["node_3"] == 3000000.0
    
    def test_disconnected_node(self):
        """Test with disconnected node in topology."""
        router = DistanceVectorRouter("node_1")
        
        nodes = ["node_1", "node_2", "node_3"]
        links = [
            Link("node_1", "node_2", 10.0, 0.0, 0.0, 0.0, 0.0)
            # node_3 is disconnected
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        
        # Should only know about node_2
        assert "node_2" in router.neighbors
        assert "node_3" not in router.neighbors
    
    def test_multiple_updates_same_neighbor(self):
        """Test receiving multiple updates from same neighbor."""
        router = DistanceVectorRouter("node_1")
        router.update_neighbors({"node_2": 10.0})
        
        # First update
        dv1 = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 15.0}
        )
        router.receive_distance_vector(dv1)
        
        assert router.my_distance_vector["node_3"] == 25.0
        
        # Second update with different distance
        dv2 = DistanceVector(
            node_id="node_2",
            distances={"node_2": 0.0, "node_3": 20.0}
        )
        router.receive_distance_vector(dv2)
        
        assert router.my_distance_vector["node_3"] == 30.0


class TestComplexTopologies:
    """Test with complex network topologies."""
    
    def test_linear_topology(self):
        """Test with linear topology: A -- B -- C."""
        router_a = DistanceVectorRouter("node_a")
        router_b = DistanceVectorRouter("node_b")
        router_c = DistanceVectorRouter("node_c")
        
        # Set up neighbors
        router_a.update_neighbors({"node_b": 10.0})
        router_b.update_neighbors({"node_a": 10.0, "node_c": 15.0})
        router_c.update_neighbors({"node_b": 15.0})
        
        # Exchange DVs: B -> A
        dv_b = router_b.get_distance_vector()
        router_a.receive_distance_vector(dv_b)
        
        # A should learn about C through B
        assert router_a.my_distance_vector["node_c"] == 25.0
        
        route = router_a.routing_table.get("node_c")
        assert route.next_hop == "node_b"
    
    def test_triangle_topology(self):
        """Test with triangle topology."""
        router_a = DistanceVectorRouter("node_a")
        router_a.update_neighbors({"node_b": 10.0, "node_c": 30.0})
        
        # Receive DV from B advertising shorter path to C
        dv_b = DistanceVector(
            node_id="node_b",
            distances={"node_b": 0.0, "node_c": 5.0}
        )
        router_a.receive_distance_vector(dv_b)
        
        # Should choose path through B (cost 15) over direct (cost 30)
        assert router_a.my_distance_vector["node_c"] == 15.0
        
        route = router_a.routing_table.get("node_c")
        assert route.next_hop == "node_b"
