"""
Verification tests for routing correctness.

Tests Dijkstra and Distance Vector routing on sample topologies to verify:
- Shortest paths are computed correctly
- Routing tables are consistent
- Dynamic updates work within time bounds
"""

import pytest
import time
from src.dijkstra_router import DijkstraRouter
from src.distance_vector_router import DistanceVectorRouter
from src.data_models import NetworkTopology, Link


class TestDijkstraRoutingCorrectness:
    """Verify Dijkstra routing on sample topologies."""
    
    def test_simple_triangle_topology(self):
        """
        Test Dijkstra on triangle topology:
        
        A --10-- B
        |        |
        30      15
        |        |
        +------- C
        
        Expected: A->C should go through B (cost 25) not direct (cost 30)
        """
        router = DijkstraRouter("node_a")
        
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 30.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Verify shortest path to C
        assert "node_c" in paths
        cost_c, next_hop_c = paths["node_c"]
        assert cost_c == 25.0, f"Expected cost 25.0, got {cost_c}"
        assert next_hop_c == "node_b", f"Expected next hop node_b, got {next_hop_c}"
        
        # Verify routing table
        routing_table = router.generate_routing_table()
        route_c = routing_table.get("node_c")
        assert route_c is not None
        assert route_c.cost == 25.0
        assert route_c.next_hop == "node_b"
    
    def test_complex_mesh_topology(self):
        """
        Test Dijkstra on mesh topology:
        
        A --5-- B --10-- D
        |       |        |
        15      8        5
        |       |        |
        C ------+--12--- E
        
        Expected paths from A:
        - A->B: 5 (direct)
        - A->C: 13 (via B, cost 5+8)
        - A->D: 15 (via B, cost 5+10)
        - A->E: 20 (via B->D, cost 5+10+5)
        """
        router = DijkstraRouter("node_a")
        
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
        
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Verify all shortest paths
        expected_paths = {
            "node_b": (5.0, "node_b"),
            "node_c": (13.0, "node_b"),
            "node_d": (15.0, "node_b"),
            "node_e": (20.0, "node_b")
        }
        
        for dest, (expected_cost, expected_next_hop) in expected_paths.items():
            assert dest in paths, f"No path to {dest}"
            cost, next_hop = paths[dest]
            assert cost == expected_cost, f"Path to {dest}: expected cost {expected_cost}, got {cost}"
            assert next_hop == expected_next_hop, f"Path to {dest}: expected next hop {expected_next_hop}, got {next_hop}"


class TestDistanceVectorRoutingCorrectness:
    """Verify Distance Vector routing on sample topologies."""
    
    def test_simple_linear_topology_convergence(self):
        """
        Test Distance Vector convergence on linear topology:
        A --10-- B --15-- C
        
        Expected after convergence:
        - A knows: B(10), C(25)
        - B knows: A(10), C(15)
        - C knows: A(25), B(15)
        """
        router_a = DistanceVectorRouter("node_a")
        router_b = DistanceVectorRouter("node_b")
        router_c = DistanceVectorRouter("node_c")
        
        # Set up topology
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router_a.update_topology(topology)
        router_b.update_topology(topology)
        router_c.update_topology(topology)
        
        # Simulate DV exchanges until convergence
        max_iterations = 10
        for _ in range(max_iterations):
            # Exchange DVs
            dv_a = router_a.get_distance_vector()
            dv_b = router_b.get_distance_vector()
            dv_c = router_c.get_distance_vector()
            
            # Each router receives DVs from neighbors
            router_a.receive_distance_vector(dv_b)
            router_b.receive_distance_vector(dv_a)
            router_b.receive_distance_vector(dv_c)
            router_c.receive_distance_vector(dv_b)
        
        # Verify convergence
        assert router_a.my_distance_vector["node_b"] == 10.0
        assert router_a.my_distance_vector["node_c"] == 25.0
        
        assert router_b.my_distance_vector["node_a"] == 10.0
        assert router_b.my_distance_vector["node_c"] == 15.0
        
        assert router_c.my_distance_vector["node_a"] == 25.0
        assert router_c.my_distance_vector["node_b"] == 15.0
        
        # Verify routing tables
        route_c = router_a.routing_table.get("node_c")
        assert route_c is not None
        assert route_c.cost == 25.0
        assert route_c.next_hop == "node_b"
    
    def test_triangle_topology_convergence(self):
        """
        Test Distance Vector on triangle topology:
        
        A --10-- B
        |        |
        30      15
        |        |
        +------- C
        
        Expected: A->C should converge to path through B (cost 25)
        """
        router_a = DistanceVectorRouter("node_a")
        router_b = DistanceVectorRouter("node_b")
        router_c = DistanceVectorRouter("node_c")
        
        # Set up topology
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 30.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router_a.update_topology(topology)
        router_b.update_topology(topology)
        router_c.update_topology(topology)
        
        # Simulate DV exchanges
        max_iterations = 10
        for _ in range(max_iterations):
            dv_a = router_a.get_distance_vector()
            dv_b = router_b.get_distance_vector()
            dv_c = router_c.get_distance_vector()
            
            router_a.receive_distance_vector(dv_b)
            router_a.receive_distance_vector(dv_c)
            router_b.receive_distance_vector(dv_a)
            router_b.receive_distance_vector(dv_c)
            router_c.receive_distance_vector(dv_a)
            router_c.receive_distance_vector(dv_b)
        
        # Verify A chooses better path through B
        assert router_a.my_distance_vector["node_c"] == 25.0
        
        route_c = router_a.routing_table.get("node_c")
        assert route_c is not None
        assert route_c.cost == 25.0
        assert route_c.next_hop == "node_b"


class TestDynamicRoutingUpdates:
    """Verify dynamic routing updates within time bounds."""
    
    def test_dijkstra_updates_after_link_failure(self):
        """
        Test that Dijkstra updates routing within 5 seconds of topology change.
        
        Initial topology:
        A --5-- B --10-- C
        |               |
        +------20-------+
        
        After link A-B fails:
        A       B --10-- C
        |               |
        +------20-------+
        
        Expected: A->C should switch from path via B (15) to direct (20)
        """
        router = DijkstraRouter("node_a")
        
        # Initial topology
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 5.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router.update_topology(topology)
        paths_before = router.compute_shortest_paths()
        
        # Verify initial path
        assert paths_before["node_c"][0] == 15.0
        assert paths_before["node_c"][1] == "node_b"
        
        # Simulate link failure by removing A-B link
        start_time = time.time()
        
        links_after_failure = [
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology_after = NetworkTopology(nodes, links_after_failure)
        
        router.update_topology(topology_after)
        paths_after = router.compute_shortest_paths()
        
        update_time = time.time() - start_time
        
        # Verify routing updated
        assert paths_after["node_c"][0] == 20.0
        assert paths_after["node_c"][1] == "node_c"
        
        # Verify update happened within 5 seconds
        assert update_time < 5.0, f"Routing update took {update_time}s, expected < 5s"
    
    def test_distance_vector_updates_after_link_failure(self):
        """
        Test that Distance Vector updates routing within reasonable time after link failure.
        """
        router_a = DistanceVectorRouter("node_a")
        router_b = DistanceVectorRouter("node_b")
        router_c = DistanceVectorRouter("node_c")
        
        # Initial topology
        nodes = ["node_a", "node_b", "node_c"]
        links = [
            Link("node_a", "node_b", 5.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology = NetworkTopology(nodes, links)
        
        router_a.update_topology(topology)
        router_b.update_topology(topology)
        router_c.update_topology(topology)
        
        # Initial convergence
        for _ in range(10):
            dv_a = router_a.get_distance_vector()
            dv_b = router_b.get_distance_vector()
            dv_c = router_c.get_distance_vector()
            
            router_a.receive_distance_vector(dv_b)
            router_a.receive_distance_vector(dv_c)
            router_b.receive_distance_vector(dv_a)
            router_b.receive_distance_vector(dv_c)
            router_c.receive_distance_vector(dv_a)
            router_c.receive_distance_vector(dv_b)
        
        # Verify initial state
        assert router_a.my_distance_vector["node_c"] == 15.0
        
        # Simulate link failure
        start_time = time.time()
        
        links_after_failure = [
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 20.0, 0.0, 0.0, 0.0, 0.0)
        ]
        topology_after = NetworkTopology(nodes, links_after_failure)
        
        router_a.update_topology(topology_after)
        router_b.update_topology(topology_after)
        router_c.update_topology(topology_after)
        
        # Re-converge
        for _ in range(10):
            dv_a = router_a.get_distance_vector()
            dv_b = router_b.get_distance_vector()
            dv_c = router_c.get_distance_vector()
            
            router_a.receive_distance_vector(dv_b)
            router_a.receive_distance_vector(dv_c)
            router_b.receive_distance_vector(dv_a)
            router_b.receive_distance_vector(dv_c)
            router_c.receive_distance_vector(dv_a)
            router_c.receive_distance_vector(dv_b)
        
        update_time = time.time() - start_time
        
        # Verify routing updated to use direct path
        assert router_a.my_distance_vector["node_c"] == 20.0
        
        # Verify update happened within 5 seconds
        assert update_time < 5.0, f"Routing update took {update_time}s, expected < 5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
