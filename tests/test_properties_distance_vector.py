"""
Property-based tests for Distance Vector routing implementation.

Feature: adaptive-network-emulator
Property: 11
Validates: Requirements 4.3

Tests use hypothesis with minimum 100 iterations for statistical confidence.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List, Set

from src.distance_vector_router import DistanceVectorRouter, DistanceVector
from src.data_models import NetworkTopology, Link


# Custom strategies for generating test data

@st.composite
def network_topology_strategy(draw, min_nodes=2, max_nodes=8):
    """
    Generate random network topology with guaranteed connectivity.
    
    Creates a connected graph by first building a spanning tree,
    then optionally adding extra edges.
    """
    num_nodes = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    
    # Generate unique node IDs
    nodes = [f"node_{i}" for i in range(num_nodes)]
    
    links = []
    
    # Build a spanning tree to ensure connectivity
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
    extra_edges = draw(st.integers(min_value=0, max_value=min(3, num_nodes - 1)))
    for _ in range(extra_edges):
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


def simulate_distance_vector_exchange(
    routers: Dict[str, DistanceVectorRouter],
    max_iterations: int = 100
) -> int:
    """
    Simulate distance vector exchange between routers until convergence.
    
    Args:
        routers: Dictionary mapping node IDs to router instances
        max_iterations: Maximum number of exchange rounds
    
    Returns:
        Number of iterations until convergence (or max_iterations if not converged)
    """
    for iteration in range(max_iterations):
        changed = False
        
        # Each router sends its distance vector to all neighbors
        for node_id, router in routers.items():
            for neighbor_id in router.neighbors:
                if neighbor_id in routers:
                    # Get distance vector with split horizon
                    dv = router.get_distance_vector(requesting_neighbor=neighbor_id)
                    
                    # Neighbor receives the distance vector
                    neighbor_router = routers[neighbor_id]
                    if neighbor_router.receive_distance_vector(dv):
                        changed = True
        
        # If no changes occurred, we've converged
        if not changed:
            return iteration + 1
    
    return max_iterations


def verify_routing_consistency(routers: Dict[str, DistanceVectorRouter]) -> bool:
    """
    Verify that routing is consistent across all routers.
    
    Checks that:
    1. All routers can reach all other routers
    2. Routes form valid paths (no loops)
    3. Next hops are valid neighbors
    
    Returns:
        True if routing is consistent, False otherwise
    """
    all_nodes = set(routers.keys())
    
    for source_id, source_router in routers.items():
        # Check that source can reach all other nodes
        reachable = set(source_router.my_distance_vector.keys())
        
        if not all_nodes.issubset(reachable):
            return False
        
        # Check that next hops are valid neighbors
        for dest_id in all_nodes:
            if dest_id == source_id:
                continue
            
            route = source_router.routing_table.get(dest_id)
            if route is None:
                return False
            
            # Next hop should be a neighbor
            if route.next_hop not in source_router.neighbors:
                return False
    
    return True


def verify_no_routing_loops(routers: Dict[str, DistanceVectorRouter]) -> bool:
    """
    Verify that there are no routing loops.
    
    For each source-destination pair, follow the next hops and ensure
    we don't visit the same node twice.
    
    Returns:
        True if no loops detected, False otherwise
    """
    all_nodes = set(routers.keys())
    
    for source_id in all_nodes:
        for dest_id in all_nodes:
            if source_id == dest_id:
                continue
            
            # Follow the path from source to destination
            current = source_id
            visited = set()
            max_hops = len(all_nodes)
            
            for _ in range(max_hops):
                if current == dest_id:
                    break
                
                if current in visited:
                    # Loop detected
                    return False
                
                visited.add(current)
                
                # Get next hop
                router = routers[current]
                route = router.routing_table.get(dest_id)
                
                if route is None:
                    # No route found
                    return False
                
                current = route.next_hop
            
            # If we didn't reach destination within max_hops, there's a problem
            if current != dest_id:
                return False
    
    return True


class TestProperty11DistanceVectorConvergence:
    """
    Property 11: Distance Vector convergence
    
    For any stable network topology, the Distance Vector algorithm should
    converge such that all nodes have consistent routing information and
    packets can reach their destinations via valid paths.
    
    Validates: Requirements 4.3
    """
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_converges(self, topology):
        """
        Property: For any stable topology, DV converges to consistent routing.
        """
        # Create routers for all nodes
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
        
        # Update each router with its neighbors from topology
        for router_id, router in routers.items():
            router.update_topology(topology)
        
        # Simulate distance vector exchange
        iterations = simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: Should converge within reasonable iterations
        # For n nodes, DV should converge in at most n-1 iterations
        max_expected_iterations = len(topology.nodes)
        assert iterations <= max_expected_iterations, \
            f"DV did not converge within {max_expected_iterations} iterations"
        
        # Property: Routing should be consistent after convergence
        assert verify_routing_consistency(routers), \
            "Routing is not consistent after convergence"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_no_routing_loops(self, topology):
        """
        Property: For any stable topology, DV produces loop-free routes.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: No routing loops should exist
        assert verify_no_routing_loops(routers), \
            "Routing loops detected after convergence"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_all_nodes_reachable(self, topology):
        """
        Property: For any connected topology, all nodes can reach all other nodes.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: Each router should have routes to all other nodes
        all_nodes = set(topology.nodes)
        for node_id, router in routers.items():
            reachable = set(router.my_distance_vector.keys())
            assert all_nodes == reachable, \
                f"Node {node_id} cannot reach all nodes: {all_nodes - reachable}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_distance_vector_next_hops_are_neighbors(self, topology):
        """
        Property: For any destination, the next hop must be a direct neighbor.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: All next hops should be direct neighbors
        for node_id, router in routers.items():
            for dest_id in topology.nodes:
                if dest_id == node_id:
                    continue
                
                route = router.routing_table.get(dest_id)
                assert route is not None, \
                    f"No route from {node_id} to {dest_id}"
                
                assert route.next_hop in router.neighbors, \
                    f"Next hop {route.next_hop} is not a neighbor of {node_id}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_costs_non_negative(self, topology):
        """
        Property: For any topology, all computed distances are non-negative.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: All distances should be non-negative
        for node_id, router in routers.items():
            for dest_id, distance in router.my_distance_vector.items():
                assert distance >= 0.0, \
                    f"Negative distance {distance} from {node_id} to {dest_id}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_stable_after_convergence(self, topology):
        """
        Property: After convergence, additional exchanges don't change routing.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        iterations = simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Save current distance vectors
        saved_dvs = {
            node_id: router.my_distance_vector.copy()
            for node_id, router in routers.items()
        }
        
        # Perform additional exchange rounds
        additional_changed = False
        for _ in range(5):
            for node_id, router in routers.items():
                for neighbor_id in router.neighbors:
                    if neighbor_id in routers:
                        dv = router.get_distance_vector(requesting_neighbor=neighbor_id)
                        if routers[neighbor_id].receive_distance_vector(dv):
                            additional_changed = True
        
        # Property: No changes should occur after convergence
        assert not additional_changed, \
            "Routing changed after convergence"
        
        # Verify distance vectors are unchanged
        for node_id, router in routers.items():
            assert router.my_distance_vector == saved_dvs[node_id], \
                f"Distance vector changed for {node_id} after convergence"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=3, max_nodes=6)
    )
    def test_distance_vector_split_horizon_prevents_loops(self, topology):
        """
        Property: Split horizon prevents advertising routes back to their source.
        """
        # Create and initialize routers
        routers = {}
        for node_id in topology.nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: When getting DV for a neighbor, routes learned from that
        # neighbor should not be included (split horizon)
        for node_id, router in routers.items():
            for neighbor_id in router.neighbors:
                dv = router.get_distance_vector(requesting_neighbor=neighbor_id)
                
                # Check each destination in the DV
                for dest_id in dv.distances:
                    route = router.routing_table.get(dest_id)
                    if route is not None:
                        # If route goes through this neighbor, it shouldn't be in DV
                        if route.next_hop == neighbor_id:
                            assert dest_id not in dv.distances or dest_id == node_id, \
                                f"Split horizon violated: {node_id} advertised route to " \
                                f"{dest_id} back to {neighbor_id}"
    
    @settings(max_examples=100)
    @given(
        num_nodes=st.integers(min_value=2, max_value=5),
        uniform_cost=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    def test_distance_vector_uniform_cost_topology(self, num_nodes, uniform_cost):
        """
        Property: For fully connected topology with uniform costs,
        all distances should equal the uniform cost.
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
        
        # Create and initialize routers
        routers = {}
        for node_id in nodes:
            routers[node_id] = DistanceVectorRouter(node_id)
            routers[node_id].update_topology(topology)
        
        # Simulate distance vector exchange until convergence
        simulate_distance_vector_exchange(routers, max_iterations=100)
        
        # Property: All distances should equal uniform_cost (direct links)
        for node_id, router in routers.items():
            for dest_id in nodes:
                if dest_id != node_id:
                    distance = router.get_distance_to(dest_id)
                    assert distance is not None
                    assert abs(distance - uniform_cost) < 1e-6, \
                        f"Distance {distance} != uniform cost {uniform_cost}"
    
    @settings(max_examples=100)
    @given(
        topology=network_topology_strategy(min_nodes=2, max_nodes=6)
    )
    def test_distance_vector_convergence_is_deterministic(self, topology):
        """
        Property: For any topology, DV converges to the same result across runs.
        """
        # First run
        routers1 = {}
        for node_id in topology.nodes:
            routers1[node_id] = DistanceVectorRouter(node_id)
            routers1[node_id].update_topology(topology)
        
        simulate_distance_vector_exchange(routers1, max_iterations=100)
        
        # Second run
        routers2 = {}
        for node_id in topology.nodes:
            routers2[node_id] = DistanceVectorRouter(node_id)
            routers2[node_id].update_topology(topology)
        
        simulate_distance_vector_exchange(routers2, max_iterations=100)
        
        # Property: Results should be identical
        for node_id in topology.nodes:
            dv1 = routers1[node_id].my_distance_vector
            dv2 = routers2[node_id].my_distance_vector
            
            assert dv1.keys() == dv2.keys(), \
                f"Different destinations for {node_id}"
            
            for dest_id in dv1:
                assert abs(dv1[dest_id] - dv2[dest_id]) < 1e-6, \
                    f"Different distances for {node_id} to {dest_id}: " \
                    f"{dv1[dest_id]} vs {dv2[dest_id]}"
