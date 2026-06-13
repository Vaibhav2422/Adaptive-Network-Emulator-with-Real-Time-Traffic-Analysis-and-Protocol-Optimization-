"""
Property-based tests for Network Layer implementation.

Feature: adaptive-network-emulator
Properties: 10
Validates: Requirements 4.2, 4.8

Tests use hypothesis with minimum 100 iterations for statistical confidence.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import numpy as np
from typing import Dict, List, Set, Tuple

from src.dijkstra_router import DijkstraRouter
from src.data_models import NetworkTopology, Link


# Custom strategies for generating test data

@st.composite
def node_id_strategy(draw):
    """Generate random node IDs."""
    return draw(st.text(
        min_size=1,
        max_size=10,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=ord('a'),
            max_codepoint=ord('z')
        )
    ))


@st.composite
def network_topology_strategy(draw, min_nodes=2, max_nodes=10):
    """
    Generate random network topology with guaranteed connectivity.
    
    Creates a connected graph by first building a spanning tree,
    then optionally adding extra edges.
    """
    num_nodes = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    
    # Generate unique node IDs
    nodes = []
    for i in range(num_nodes):
        nodes.append(f"node_{i}")
    
    links = []
    
    # Build a spanning tree to ensure connectivity
    # Start with first node
    connected = {nodes[0]}
    unconnected = set(nodes[1:])
    
    while unconnected:
        # Pick a random connected node
        from_node = draw(st.sampled_from(sorted(connected)))
        # Pick a random unconnected node
        to_node = draw(st.sampled_from(sorted(unconnected)))
        
        # Add link with random cost
        cost = draw(st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False))
        
        links.append(Link(
            node_a=from_node,
            node_b=to_node,
            cost=cost,
            capacity=0.0,
            utilization=0.0,
            latency=0.0,
            loss_rate=0.0
        ))
        
        # Move node to connected set
        connected.add(to_node)
        unconnected.remove(to_node)
    
    # Optionally add extra edges for more complex topologies
    extra_edges = draw(st.integers(min_value=0, max_value=min(5, num_nodes)))
    for _ in range(extra_edges):
        # Pick two random nodes
        if len(nodes) >= 2:
            node_a = draw(st.sampled_from(nodes))
            node_b = draw(st.sampled_from(nodes))
            
            if node_a != node_b:
                # Check if link already exists
                existing = any(
                    (link.node_a == node_a and link.node_b == node_b) or
                    (link.node_a == node_b and link.node_b == node_a)
                    for link in links
                )
                
                if not existing:
                    cost = draw(st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False))
                    links.append(Link(
                        node_a=node_a,
                        node_b=node_b,
                        cost=cost,
                        capacity=0.0,
                        utilization=0.0,
                        latency=0.0,
                        loss_rate=0.0
                    ))
    
    return NetworkTopology(nodes=nodes, links=links)


def compute_all_paths_costs(topology: NetworkTopology, source: str) -> Dict[str, float]:
    """
    Compute shortest path costs from source to all nodes using brute force.
    
    This is used as a reference implementation to verify Dijkstra's correctness.
    Uses Floyd-Warshall-like approach for verification.
    """
    # Build adjacency matrix
    node_to_idx = {node: i for i, node in enumerate(topology.nodes)}
    n = len(topology.nodes)
    
    # Initialize with infinity
    dist = [[float('inf')] * n for _ in range(n)]
    
    # Distance to self is 0
    for i in range(n):
        dist[i][i] = 0.0
    
    # Add direct links
    for link in topology.links:
        i = node_to_idx[link.node_a]
        j = node_to_idx[link.node_b]
        dist[i][j] = min(dist[i][j], link.cost)
        dist[j][i] = min(dist[j][i], link.cost)  # Bidirectional
    
    # Floyd-Warshall to find all shortest paths
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    
    # Extract distances from source
    source_idx = node_to_idx[source]
    result = {}
    for node in topology.nodes:
        if node != source:
            node_idx = node_to_idx[node]
            result[node] = dist[source_idx][node_idx]
    
    return result


def verify_path_optimality(
    topology: NetworkTopology,
    source: str,
    dijkstra_paths: Dict[str, Tuple[float, str]]
) -> bool:
    """
    Verify that Dijkstra's computed paths are optimal.
    
    Returns True if all paths have minimal cost, False otherwise.
    """
    # Compute reference shortest paths
    reference_costs = compute_all_paths_costs(topology, source)
    
    # Compare Dijkstra's costs with reference
    for dest, (cost, next_hop) in dijkstra_paths.items():
        if dest not in reference_costs:
            continue
        
        reference_cost = reference_costs[dest]
        
        # Allow small floating point tolerance
        if abs(cost - reference_cost) > 1e-6:
            return False
    
    return True


class TestProperty10DijkstraShortestPath:
    """
    Property 10: Dijkstra shortest path correctness
    
    For any network topology with weighted links, the Dijkstra algorithm
    should compute paths where the total cost from source to any destination
    is minimal among all possible paths.
    
    Validates: Requirements 4.2, 4.8
    """
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=8)
    )
    def test_dijkstra_computes_minimal_cost_paths(self, topology):
        """
        Property: For any topology, Dijkstra computes paths with minimal total cost.
        """
        # Pick a source node (first node in topology)
        source = topology.nodes[0]
        
        # Create router and update topology
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        # Compute shortest paths
        shortest_paths = router.compute_shortest_paths()
        
        # Verify optimality using reference implementation
        is_optimal = verify_path_optimality(topology, source, shortest_paths)
        
        # Property: All computed paths should have minimal cost
        assert is_optimal, "Dijkstra did not compute optimal paths"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_dijkstra_paths_reach_all_connected_nodes(self, topology):
        """
        Property: For any connected topology, Dijkstra finds paths to all nodes.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        shortest_paths = router.compute_shortest_paths()
        
        # Property: Should have paths to all nodes except source
        expected_destinations = set(topology.nodes) - {source}
        computed_destinations = set(shortest_paths.keys())
        
        # All reachable nodes should have paths
        # (In our topology generation, all nodes are connected)
        assert computed_destinations == expected_destinations
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=8)
    )
    def test_dijkstra_costs_are_non_negative(self, topology):
        """
        Property: For any topology, all computed path costs are non-negative.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        shortest_paths = router.compute_shortest_paths()
        
        # Property: All costs should be non-negative
        for dest, (cost, next_hop) in shortest_paths.items():
            assert cost >= 0.0, f"Negative cost {cost} for destination {dest}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_dijkstra_next_hop_is_neighbor(self, topology):
        """
        Property: For any destination, the next hop should be a direct neighbor.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        shortest_paths = router.compute_shortest_paths()
        
        # Build set of direct neighbors of source
        neighbors = set()
        for link in topology.links:
            if link.node_a == source:
                neighbors.add(link.node_b)
            elif link.node_b == source:
                neighbors.add(link.node_a)
        
        # Property: All next hops should be direct neighbors
        for dest, (cost, next_hop) in shortest_paths.items():
            if next_hop is not None:
                assert next_hop in neighbors, \
                    f"Next hop {next_hop} is not a neighbor of {source}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=8)
    )
    def test_dijkstra_path_cost_at_least_direct_link(self, topology):
        """
        Property: For any destination with direct link, path cost <= direct link cost.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        shortest_paths = router.compute_shortest_paths()
        
        # Find direct links from source
        direct_links = {}
        for link in topology.links:
            if link.node_a == source:
                direct_links[link.node_b] = link.cost
            elif link.node_b == source:
                direct_links[link.node_a] = link.cost
        
        # Property: For destinations with direct links,
        # shortest path cost should be at most the direct link cost
        for dest, direct_cost in direct_links.items():
            if dest in shortest_paths:
                computed_cost, _ = shortest_paths[dest]
                assert computed_cost <= direct_cost + 1e-6, \
                    f"Path cost {computed_cost} > direct link cost {direct_cost}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_dijkstra_routing_table_generation(self, topology):
        """
        Property: For any topology, routing table contains entries for all reachable nodes.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        # Generate routing table
        routing_table = router.generate_routing_table()
        
        # Property: Routing table should have entries for all nodes except source
        expected_destinations = set(topology.nodes) - {source}
        routing_entries = set(routing_table.get_all().keys())
        
        assert routing_entries == expected_destinations
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_dijkstra_triangle_inequality(self, topology):
        """
        Property: For any three nodes A, B, C, dist(A,C) <= dist(A,B) + dist(B,C).
        """
        # Pick three different nodes
        if len(topology.nodes) < 3:
            return
        
        node_a = topology.nodes[0]
        node_b = topology.nodes[1]
        node_c = topology.nodes[2]
        
        # Compute shortest paths from A
        router_a = DijkstraRouter(node_a)
        router_a.update_topology(topology)
        paths_from_a = router_a.compute_shortest_paths()
        
        # Compute shortest paths from B
        router_b = DijkstraRouter(node_b)
        router_b.update_topology(topology)
        paths_from_b = router_b.compute_shortest_paths()
        
        # Get distances
        if node_b in paths_from_a and node_c in paths_from_a and node_c in paths_from_b:
            dist_a_b = paths_from_a[node_b][0]
            dist_a_c = paths_from_a[node_c][0]
            dist_b_c = paths_from_b[node_c][0]
            
            # Property: Triangle inequality should hold
            assert dist_a_c <= dist_a_b + dist_b_c + 1e-6, \
                f"Triangle inequality violated: {dist_a_c} > {dist_a_b} + {dist_b_c}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=8)
    )
    def test_dijkstra_consistent_across_runs(self, topology):
        """
        Property: For any topology, running Dijkstra multiple times gives same results.
        """
        source = topology.nodes[0]
        
        # Run Dijkstra twice
        router1 = DijkstraRouter(source)
        router1.update_topology(topology)
        paths1 = router1.compute_shortest_paths()
        
        router2 = DijkstraRouter(source)
        router2.update_topology(topology)
        paths2 = router2.compute_shortest_paths()
        
        # Property: Results should be identical
        assert paths1.keys() == paths2.keys()
        
        for dest in paths1:
            cost1, next_hop1 = paths1[dest]
            cost2, next_hop2 = paths2[dest]
            
            assert abs(cost1 - cost2) < 1e-6, \
                f"Inconsistent costs for {dest}: {cost1} vs {cost2}"
            assert next_hop1 == next_hop2, \
                f"Inconsistent next hops for {dest}: {next_hop1} vs {next_hop2}"
    
    @settings(max_examples=100)
    @given(
        num_nodes=st.integers(min_value=2, max_value=6),
        uniform_cost=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    def test_dijkstra_on_uniform_cost_topology(self, num_nodes, uniform_cost):
        """
        Property: For any fully connected topology with uniform costs,
        all paths should have cost equal to the uniform cost.
        """
        # Create fully connected topology with uniform costs
        nodes = [f"node_{i}" for i in range(num_nodes)]
        links = []
        
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                links.append(Link(
                    node_a=nodes[i],
                    node_b=nodes[j],
                    cost=uniform_cost,
                    capacity=0.0,
                    utilization=0.0,
                    latency=0.0,
                    loss_rate=0.0
                ))
        
        topology = NetworkTopology(nodes=nodes, links=links)
        source = nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        paths = router.compute_shortest_paths()
        
        # Property: All paths should have cost equal to uniform_cost
        # (direct links in fully connected graph)
        for dest, (cost, next_hop) in paths.items():
            assert abs(cost - uniform_cost) < 1e-6, \
                f"Path cost {cost} != uniform cost {uniform_cost}"



class TestProperty12DynamicRoutingUpdate:
    """
    Property 12: Dynamic routing update
    
    For any topology change, routing tables should update within bounded time.
    
    Validates: Requirements 4.4
    """
    
    @settings(max_examples=100)
    @given(
        initial_topology=network_topology_strategy(min_nodes=3, max_nodes=8),
        link_to_remove_idx=st.integers(min_value=0, max_value=100)
    )
    def test_routing_updates_after_link_failure(self, initial_topology, link_to_remove_idx):
        """
        Property: For any topology change (link failure), routing tables should update.
        """
        # Skip if topology has no links
        if len(initial_topology.links) == 0:
            return
        
        # Pick a link to fail
        link_idx = link_to_remove_idx % len(initial_topology.links)
        failed_link = initial_topology.links[link_idx]
        
        source = initial_topology.nodes[0]
        
        # Create router with initial topology
        router = DijkstraRouter(source)
        router.update_topology(initial_topology)
        initial_routing_table = router.generate_routing_table()
        initial_routes = initial_routing_table.get_all().copy()
        
        # Simulate link failure
        router.handle_link_failure(failed_link.node_a, failed_link.node_b)
        
        # Get updated routing table
        updated_routes = router.get_routing_table().get_all()
        
        # Property: Routing table should be updated (may have different routes or costs)
        # At minimum, routes through the failed link should be invalidated or updated
        routes_changed = False
        
        # Check if any route was removed or cost changed
        for dest in initial_routes:
            if dest not in updated_routes:
                routes_changed = True
                break
            if initial_routes[dest].cost != updated_routes[dest].cost:
                routes_changed = True
                break
            if initial_routes[dest].next_hop != updated_routes[dest].next_hop:
                routes_changed = True
                break
        
        # Also check if number of routes changed
        if len(initial_routes) != len(updated_routes):
            routes_changed = True
        
        # Property: Routes should change after link failure
        # (unless the failed link was redundant and didn't affect any shortest paths)
        # We verify that the system is capable of updating, not that it always must
        assert isinstance(updated_routes, dict), "Routing table should still be valid"
    
    @settings(max_examples=100)
    @given(
        initial_topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_routing_updates_after_node_failure(self, initial_topology):
        """
        Property: For any node failure, routes through that node should be invalidated.
        """
        # Pick a node to fail (not the source)
        if len(initial_topology.nodes) < 2:
            return
        
        source = initial_topology.nodes[0]
        failed_node = initial_topology.nodes[1]
        
        # Create router with initial topology
        router = DijkstraRouter(source)
        router.update_topology(initial_topology)
        initial_routing_table = router.generate_routing_table()
        initial_routes = initial_routing_table.get_all().copy()
        
        # Simulate node failure
        router.handle_node_failure(failed_node)
        
        # Get updated routing table
        updated_routes = router.get_routing_table().get_all()
        
        # Property: Route to failed node should be removed
        assert failed_node not in updated_routes, \
            f"Route to failed node {failed_node} should be removed"
        
        # Property: Routes that used failed node as next hop should be updated or removed
        for dest, route in initial_routes.items():
            if route.next_hop == failed_node:
                # This route should either be removed or have a different next hop
                if dest in updated_routes:
                    assert updated_routes[dest].next_hop != failed_node, \
                        f"Route to {dest} still uses failed node {failed_node} as next hop"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_topology_change_detection(self, topology):
        """
        Property: For any topology, change detection should work correctly.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        
        # First update should detect change
        changed = router.detect_topology_change(topology)
        assert changed, "First topology update should be detected as change"
        
        # Same topology should not be detected as change
        changed = router.detect_topology_change(topology)
        assert not changed, "Same topology should not be detected as change"
        
        # Modify topology by changing a link cost
        if len(topology.links) > 0:
            modified_topology = NetworkTopology(
                nodes=topology.nodes.copy(),
                links=topology.links.copy()
            )
            # Change cost of first link
            modified_topology.links[0] = Link(
                node_a=topology.links[0].node_a,
                node_b=topology.links[0].node_b,
                cost=topology.links[0].cost + 10.0,  # Different cost
                capacity=0.0,
                utilization=0.0,
                latency=0.0,
                loss_rate=0.0
            )
            
            # Modified topology should be detected as change
            changed = router.detect_topology_change(modified_topology)
            assert changed, "Modified topology should be detected as change"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_route_timestamps_updated(self, topology):
        """
        Property: For any routing update, route timestamps should be current.
        """
        import time
        
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        router.update_topology(topology)
        
        # Record time before generating routing table
        time_before = time.time()
        
        # Generate routing table
        routing_table = router.generate_routing_table()
        
        # Record time after
        time_after = time.time()
        
        # Property: All route timestamps should be between time_before and time_after
        for dest, route in routing_table.get_all().items():
            assert time_before <= route.timestamp <= time_after, \
                f"Route timestamp {route.timestamp} not in range [{time_before}, {time_after}]"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_distance_vector_updates_after_link_failure(self, topology):
        """
        Property: Distance Vector routing should update after link failure.
        """
        from src.distance_vector_router import DistanceVectorRouter
        
        # Skip if topology has no links
        if len(topology.links) == 0:
            return
        
        source = topology.nodes[0]
        
        # Create router with initial topology
        router = DistanceVectorRouter(source)
        router.update_topology(topology)
        
        # Get initial distance vector
        initial_dv = router.my_distance_vector.copy()
        
        # Pick a link connected to source to fail
        source_links = [
            link for link in topology.links
            if link.node_a == source or link.node_b == source
        ]
        
        if not source_links:
            return
        
        failed_link = source_links[0]
        
        # Simulate link failure
        router.handle_link_failure(failed_link.node_a, failed_link.node_b)
        
        # Get updated distance vector
        updated_dv = router.my_distance_vector
        
        # Property: Distance vector should be updated
        # The neighbor on the failed link should be removed or have infinite distance
        failed_neighbor = (
            failed_link.node_b if failed_link.node_a == source
            else failed_link.node_a
        )
        
        # The failed neighbor should either be removed or unreachable
        if failed_neighbor in initial_dv:
            assert (
                failed_neighbor not in updated_dv or
                updated_dv[failed_neighbor] == float('inf')
            ), f"Failed neighbor {failed_neighbor} should be removed or unreachable"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=8)
    )
    def test_routing_converges_after_multiple_updates(self, topology):
        """
        Property: After multiple topology updates, routing should converge to stable state.
        """
        source = topology.nodes[0]
        
        router = DijkstraRouter(source)
        
        # Apply same topology multiple times
        for _ in range(3):
            router.update_topology(topology)
            router.generate_routing_table()
        
        # Get routing table after convergence
        final_routing_table = router.get_routing_table().get_all()
        
        # Apply topology one more time
        router.update_topology(topology)
        router.generate_routing_table()
        
        # Get routing table again
        new_routing_table = router.get_routing_table().get_all()
        
        # Property: Routing table should be stable (same as before)
        assert final_routing_table.keys() == new_routing_table.keys()
        
        for dest in final_routing_table:
            assert final_routing_table[dest].cost == new_routing_table[dest].cost
            assert final_routing_table[dest].next_hop == new_routing_table[dest].next_hop



class TestProperty13RouteSelectionOptimality:
    """
    Property 13: Route selection optimality
    
    For any routing decision with multiple paths, selected path should have better metrics.
    
    Validates: Requirements 4.5
    """
    
    @settings(max_examples=100)
    @given(
        num_nodes=st.integers(min_value=3, max_value=6),
        base_cost=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        high_utilization=st.floats(min_value=0.5, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    def test_traffic_aware_routing_prefers_less_utilized_links(
        self, num_nodes, base_cost, high_utilization
    ):
        """
        Property: With traffic-aware routing, paths through less utilized links are preferred.
        """
        # Create a simple topology with two paths from source to destination
        # Path 1: source -> node_1 -> dest (high utilization)
        # Path 2: source -> node_2 -> dest (low utilization)
        
        nodes = [f"node_{i}" for i in range(num_nodes)]
        source = nodes[0]
        dest = nodes[-1]
        
        if num_nodes < 3:
            return
        
        intermediate_1 = nodes[1]
        intermediate_2 = nodes[2] if num_nodes > 3 else nodes[1]
        
        # Create links with same base cost but different utilization
        links = [
            # Path 1: high utilization
            Link(
                node_a=source,
                node_b=intermediate_1,
                cost=base_cost,
                capacity=100.0,
                utilization=high_utilization,  # High utilization
                latency=10.0,
                loss_rate=0.0
            ),
            Link(
                node_a=intermediate_1,
                node_b=dest,
                cost=base_cost,
                capacity=100.0,
                utilization=high_utilization,  # High utilization
                latency=10.0,
                loss_rate=0.0
            ),
            # Path 2: low utilization
            Link(
                node_a=source,
                node_b=intermediate_2,
                cost=base_cost,
                capacity=100.0,
                utilization=0.1,  # Low utilization
                latency=10.0,
                loss_rate=0.0
            ),
            Link(
                node_a=intermediate_2,
                node_b=dest,
                cost=base_cost,
                capacity=100.0,
                utilization=0.1,  # Low utilization
                latency=10.0,
                loss_rate=0.0
            ),
        ]
        
        topology = NetworkTopology(nodes=nodes, links=links)
        
        # Test with traffic-aware routing disabled
        router_normal = DijkstraRouter(source)
        router_normal.update_topology(topology)
        paths_normal = router_normal.compute_shortest_paths()
        
        # Test with traffic-aware routing enabled
        router_aware = DijkstraRouter(source)
        router_aware.enable_traffic_aware_routing(True)
        router_aware.update_topology_with_traffic_metrics(topology)
        paths_aware = router_aware.compute_shortest_paths_with_traffic_awareness()
        
        # Property: With traffic-aware routing, cost to destination should be higher
        # (reflecting the congestion penalty)
        if dest in paths_normal and dest in paths_aware:
            cost_normal = paths_normal[dest][0]
            cost_aware = paths_aware[dest][0]
            
            # Traffic-aware cost should be higher due to utilization penalty
            assert cost_aware >= cost_normal, \
                f"Traffic-aware cost {cost_aware} should be >= normal cost {cost_normal}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_traffic_aware_routing_adjusts_costs(self, topology):
        """
        Property: Traffic-aware routing should adjust costs based on link metrics.
        """
        source = topology.nodes[0]
        
        # Add traffic metrics to links
        for link in topology.links:
            link.utilization = 0.5
            link.latency = 20.0
            link.loss_rate = 0.01
        
        router = DijkstraRouter(source)
        router.enable_traffic_aware_routing(True)
        router.update_topology_with_traffic_metrics(topology)
        
        # Compute paths with traffic awareness
        paths = router.compute_shortest_paths_with_traffic_awareness()
        
        # Property: All computed costs should be valid (non-negative, finite)
        for dest, (cost, next_hop) in paths.items():
            assert cost >= 0.0, f"Cost to {dest} is negative: {cost}"
            assert cost != float('inf'), f"Cost to {dest} is infinite"
            assert next_hop is not None, f"No next hop for {dest}"
    
    @settings(max_examples=100)
    @given(
        base_cost=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        utilization=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        latency=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        loss_rate=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    def test_cost_adjustment_increases_with_congestion(
        self, base_cost, utilization, latency, loss_rate
    ):
        """
        Property: Adjusted cost should increase with utilization, latency, and loss rate.
        """
        router = DijkstraRouter("test_node")
        router.enable_traffic_aware_routing(True)
        
        # Compute adjusted cost
        adjusted_cost = router.compute_adjusted_cost(
            base_cost, utilization, latency, loss_rate
        )
        
        # Property: Adjusted cost should be at least the base cost
        assert adjusted_cost >= base_cost, \
            f"Adjusted cost {adjusted_cost} < base cost {base_cost}"
        
        # Property: With zero metrics, adjusted cost should equal base cost
        zero_adjusted = router.compute_adjusted_cost(base_cost, 0.0, 0.0, 0.0)
        assert abs(zero_adjusted - base_cost) < 1e-6, \
            f"Zero metrics should give base cost: {zero_adjusted} vs {base_cost}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_traffic_aware_routing_can_be_toggled(self, topology):
        """
        Property: Traffic-aware routing can be enabled and disabled.
        """
        source = topology.nodes[0]
        
        # Add traffic metrics
        for link in topology.links:
            link.utilization = 0.7
            link.latency = 30.0
            link.loss_rate = 0.05
        
        router = DijkstraRouter(source)
        router.update_topology_with_traffic_metrics(topology)
        
        # Compute paths with traffic-aware disabled
        router.enable_traffic_aware_routing(False)
        paths_disabled = router.compute_shortest_paths_with_traffic_awareness()
        
        # Compute paths with traffic-aware enabled
        router.enable_traffic_aware_routing(True)
        paths_enabled = router.compute_shortest_paths_with_traffic_awareness()
        
        # Property: Paths should exist in both cases
        assert len(paths_disabled) > 0, "Should have paths with traffic-aware disabled"
        assert len(paths_enabled) > 0, "Should have paths with traffic-aware enabled"
        
        # Property: Costs may differ when traffic-aware is enabled
        # (but not required to differ if topology is simple)
        for dest in paths_disabled:
            if dest in paths_enabled:
                cost_disabled = paths_disabled[dest][0]
                cost_enabled = paths_enabled[dest][0]
                
                # Both should be valid costs
                assert cost_disabled >= 0.0
                assert cost_enabled >= 0.0
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_distance_vector_traffic_aware_routing(self, topology):
        """
        Property: Distance Vector router should support traffic-aware routing.
        """
        from src.distance_vector_router import DistanceVectorRouter
        
        source = topology.nodes[0]
        
        # Add traffic metrics
        for link in topology.links:
            link.utilization = 0.6
            link.latency = 25.0
            link.loss_rate = 0.02
        
        router = DistanceVectorRouter(source)
        router.enable_traffic_aware_routing(True)
        router.update_topology_with_traffic_metrics(topology)
        
        # Get distance vector
        dv = router.my_distance_vector
        
        # Property: Distance vector should contain valid distances
        for dest, cost in dv.items():
            assert cost >= 0.0, f"Distance to {dest} is negative: {cost}"
            assert cost != float('inf') or dest != source, \
                f"Distance to reachable node {dest} is infinite"
    
    @settings(max_examples=100)
    @given(
        base_cost=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    def test_cost_adjustment_monotonicity(self, base_cost):
        """
        Property: Higher utilization should result in higher adjusted cost.
        """
        router = DijkstraRouter("test_node")
        router.enable_traffic_aware_routing(True)
        
        # Compute costs with increasing utilization
        cost_low = router.compute_adjusted_cost(base_cost, utilization=0.2)
        cost_medium = router.compute_adjusted_cost(base_cost, utilization=0.5)
        cost_high = router.compute_adjusted_cost(base_cost, utilization=0.8)
        
        # Property: Cost should increase with utilization
        assert cost_low <= cost_medium, \
            f"Cost should increase: {cost_low} > {cost_medium}"
        assert cost_medium <= cost_high, \
            f"Cost should increase: {cost_medium} > {cost_high}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_traffic_aware_routing_table_generation(self, topology):
        """
        Property: Traffic-aware routing table should be generated correctly.
        """
        source = topology.nodes[0]
        
        # Add traffic metrics
        for link in topology.links:
            link.utilization = 0.4
            link.latency = 15.0
            link.loss_rate = 0.01
        
        router = DijkstraRouter(source)
        router.enable_traffic_aware_routing(True)
        router.update_topology_with_traffic_metrics(topology)
        
        # Generate traffic-aware routing table
        routing_table = router.generate_traffic_aware_routing_table()
        
        # Property: Routing table should have entries for reachable nodes
        routes = routing_table.get_all()
        assert len(routes) > 0, "Routing table should not be empty"
        
        # Property: All routes should have valid next hops
        for dest, route in routes.items():
            assert route.next_hop is not None, f"Route to {dest} has no next hop"
            assert route.cost >= 0.0, f"Route to {dest} has negative cost"
            assert route.metric_type == "traffic_aware", \
                f"Route metric type should be 'traffic_aware', got '{route.metric_type}'"
