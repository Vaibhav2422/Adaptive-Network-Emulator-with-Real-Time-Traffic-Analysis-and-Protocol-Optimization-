"""
Distance Vector Routing Implementation

This module implements the Distance Vector routing algorithm using the Bellman-Ford
algorithm. It exchanges distance vectors with neighbors and updates routing tables
based on received information. Implements split horizon to prevent routing loops.

Validates: Requirements 4.3
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

from src.data_models import RouteEntry, Link, NetworkTopology
from src.routing_table import RoutingTable


logger = logging.getLogger(__name__)


@dataclass
class DistanceVector:
    """
    Represents a distance vector advertisement.
    
    Attributes:
        node_id: Node advertising the distance vector
        distances: Dictionary mapping destination node IDs to costs
        timestamp: Time of last update
    """
    node_id: str
    distances: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class DistanceVectorRouter:
    """
    Implements Distance Vector routing algorithm using Bellman-Ford.
    
    This class maintains distance vectors from neighbors and computes shortest
    paths using the distributed Bellman-Ford algorithm. It implements split
    horizon to prevent routing loops.
    
    Attributes:
        node_id: Identifier for this node
        neighbors: Dictionary mapping neighbor IDs to link costs
        distance_vectors: Distance vectors received from neighbors
        routing_table: RoutingTable instance for managing routes
        my_distance_vector: This node's distance vector to advertise
    """
    
    def __init__(self, node_id: str):
        """
        Initialize Distance Vector router.
        
        Args:
            node_id: Identifier for this node
        """
        self.node_id = node_id
        self.neighbors: Dict[str, float] = {}
        self.distance_vectors: Dict[str, DistanceVector] = {}
        self.routing_table = RoutingTable(node_id)
        self.my_distance_vector: Dict[str, float] = {}
        self._last_topology_hash: Optional[int] = None
        self._update_callbacks: List[Callable] = []
        
        # Traffic-aware routing state
        self._link_metrics: Dict[str, Dict[str, float]] = {}
        self._traffic_aware_enabled: bool = False
        
        # Initialize own distance vector (distance to self is 0)
        self.my_distance_vector[node_id] = 0.0
        
        logger.info(f"DistanceVectorRouter initialized for node {node_id}")
    
    def update_neighbors(self, neighbors: Dict[str, float]) -> None:
        """
        Update the list of direct neighbors and their link costs.
        
        Args:
            neighbors: Dictionary mapping neighbor node IDs to link costs
        """
        self.neighbors = neighbors.copy()
        logger.debug(f"Node {self.node_id}: Updated neighbors: {neighbors}")
        
        # Update distance vector for direct neighbors
        for neighbor, cost in neighbors.items():
            self.my_distance_vector[neighbor] = cost
        
        # Update routing table for direct neighbors
        self._update_routing_table_for_neighbors()
    
    def receive_distance_vector(self, dv: DistanceVector) -> bool:
        """
        Receive and process a distance vector from a neighbor.
        
        Args:
            dv: DistanceVector received from a neighbor
            
        Returns:
            True if this caused an update to routing table, False otherwise
        """
        if dv.node_id not in self.neighbors:
            logger.warning(
                f"Node {self.node_id}: Received DV from non-neighbor {dv.node_id}"
            )
            return False
        
        # Store the distance vector
        self.distance_vectors[dv.node_id] = dv
        
        logger.debug(
            f"Node {self.node_id}: Received DV from {dv.node_id}: {dv.distances}"
        )
        
        # Recompute routes using Bellman-Ford
        return self._bellman_ford_update()
    
    def _bellman_ford_update(self) -> bool:
        """
        Update routing table using Bellman-Ford algorithm.
        
        This implements the core Distance Vector algorithm:
        For each destination d, compute:
            distance[d] = min over all neighbors n of (cost_to_n + n.distance[d])
        
        Returns:
            True if routing table changed, False otherwise
        """
        old_distances = self.my_distance_vector.copy()
        new_distances: Dict[str, float] = {self.node_id: 0.0}
        next_hops: Dict[str, str] = {}
        
        # Collect all known destinations
        all_destinations = set([self.node_id])
        for neighbor in self.neighbors:
            all_destinations.add(neighbor)
        for dv in self.distance_vectors.values():
            all_destinations.update(dv.distances.keys())
        
        # For each destination, find minimum cost path through neighbors
        for dest in all_destinations:
            if dest == self.node_id:
                continue
            
            min_cost = float('inf')
            best_next_hop = None
            
            # Check direct connection
            if dest in self.neighbors:
                min_cost = self.neighbors[dest]
                best_next_hop = dest
            
            # Check paths through neighbors
            for neighbor, link_cost in self.neighbors.items():
                if neighbor in self.distance_vectors:
                    neighbor_dv = self.distance_vectors[neighbor]
                    if dest in neighbor_dv.distances:
                        cost_through_neighbor = link_cost + neighbor_dv.distances[dest]
                        if cost_through_neighbor < min_cost:
                            min_cost = cost_through_neighbor
                            best_next_hop = neighbor
            
            # Update if we found a path
            if best_next_hop is not None and min_cost != float('inf'):
                new_distances[dest] = min_cost
                next_hops[dest] = best_next_hop
        
        # Check if distances changed
        changed = (new_distances != old_distances)
        
        if changed:
            self.my_distance_vector = new_distances
            self._update_routing_table(next_hops)
            self._notify_update_callbacks()
            logger.info(
                f"Node {self.node_id}: Distance vector updated: {new_distances}"
            )
        
        return changed
    
    def _update_routing_table(self, next_hops: Dict[str, str]) -> None:
        """
        Update routing table based on computed next hops.
        
        Args:
            next_hops: Dictionary mapping destinations to next hop nodes
        """
        # Clear existing routes
        self.routing_table.clear()
        
        # Add new routes
        current_time = time.time()
        for dest, next_hop in next_hops.items():
            if dest in self.my_distance_vector:
                route_entry = RouteEntry(
                    destination=dest,
                    next_hop=next_hop,
                    cost=self.my_distance_vector[dest],
                    interface="eth0",
                    timestamp=current_time,
                    metric_type="hop_count"
                )
                self.routing_table.add(route_entry)
    
    def _update_routing_table_for_neighbors(self) -> None:
        """
        Update routing table for direct neighbors.
        
        This ensures direct neighbors are always in the routing table.
        """
        current_time = time.time()
        for neighbor, cost in self.neighbors.items():
            route_entry = RouteEntry(
                destination=neighbor,
                next_hop=neighbor,
                cost=cost,
                interface="eth0",
                timestamp=current_time,
                metric_type="hop_count"
            )
            self.routing_table.add(route_entry)
    
    def get_distance_vector(self, requesting_neighbor: Optional[str] = None) -> DistanceVector:
        """
        Get this node's distance vector for advertisement.
        
        Implements split horizon: don't advertise routes back to the neighbor
        that provided them.
        
        Args:
            requesting_neighbor: Neighbor requesting the distance vector (for split horizon)
            
        Returns:
            DistanceVector object to advertise
        """
        if requesting_neighbor is None:
            # No split horizon, return full distance vector
            return DistanceVector(
                node_id=self.node_id,
                distances=self.my_distance_vector.copy(),
                timestamp=time.time()
            )
        
        # Apply split horizon: don't advertise routes learned from this neighbor
        filtered_distances = {}
        
        for dest, cost in self.my_distance_vector.items():
            # Check if this route goes through the requesting neighbor
            route = self.routing_table.get(dest)
            
            if route is None or route.next_hop != requesting_neighbor:
                # Safe to advertise this route
                filtered_distances[dest] = cost
            else:
                # Don't advertise routes back to the neighbor that provided them
                logger.debug(
                    f"Node {self.node_id}: Split horizon - not advertising "
                    f"route to {dest} back to {requesting_neighbor}"
                )
        
        return DistanceVector(
            node_id=self.node_id,
            distances=filtered_distances,
            timestamp=time.time()
        )
    
    def update_topology(self, topology: NetworkTopology) -> None:
        """
        Update neighbors from a NetworkTopology object.
        
        This extracts direct neighbors for this node from the topology.
        
        Args:
            topology: NetworkTopology object containing nodes and links
        """
        # Build neighbor list from topology
        neighbors: Dict[str, float] = {}
        
        for link in topology.links:
            if link.node_a == self.node_id:
                neighbors[link.node_b] = link.cost
            elif link.node_b == self.node_id:
                neighbors[link.node_a] = link.cost
        
        self.update_neighbors(neighbors)
    
    def generate_routing_table(self, interface: str = "eth0", metric_type: str = "hop_count") -> RoutingTable:
        """
        Generate routing table from current distance vector.
        
        Args:
            interface: Interface identifier for routes
            metric_type: Type of metric used (hop_count, latency, bandwidth)
        
        Returns:
            RoutingTable object with current routes
        """
        # Routing table is already maintained, just update metadata if needed
        current_time = time.time()
        
        for dest, route in self.routing_table.get_all().items():
            if route.interface != interface or route.metric_type != metric_type:
                self.routing_table.update(
                    dest,
                    interface=interface,
                    metric_type=metric_type,
                    timestamp=current_time
                )
        
        return self.routing_table
    
    def get_routing_table(self) -> RoutingTable:
        """
        Get the current routing table.
        
        Returns:
            RoutingTable object
        """
        return self.routing_table
    
    def clear_distance_vectors(self) -> None:
        """Clear all received distance vectors."""
        self.distance_vectors.clear()
        logger.debug(f"Node {self.node_id}: Cleared distance vectors")
    
    def get_distance_to(self, destination: str) -> Optional[float]:
        """
        Get the distance to a specific destination.
        
        Args:
            destination: Destination node ID
            
        Returns:
            Distance to destination, or None if unreachable
        """
        return self.my_distance_vector.get(destination)
    
    def is_converged(self, previous_distances: Dict[str, float]) -> bool:
        """
        Check if the routing has converged by comparing with previous state.
        
        Args:
            previous_distances: Previous distance vector to compare against
            
        Returns:
            True if distances haven't changed, False otherwise
        """
        return self.my_distance_vector == previous_distances
    
    def detect_topology_change(self, topology: NetworkTopology) -> bool:
        """
        Detect if the topology has changed since last update.
        
        Args:
            topology: Current network topology
            
        Returns:
            True if topology changed, False otherwise
        """
        # Compute hash of topology
        topology_str = f"{sorted(topology.nodes)}"
        for link in sorted(topology.links, key=lambda l: (l.node_a, l.node_b)):
            topology_str += f"{link.node_a}{link.node_b}{link.cost}"
        
        current_hash = hash(topology_str)
        
        if self._last_topology_hash is None or current_hash != self._last_topology_hash:
            self._last_topology_hash = current_hash
            logger.info(f"DistanceVectorRouter {self.node_id}: Topology change detected")
            return True
        
        return False
    
    def handle_link_failure(self, node_a: str, node_b: str) -> None:
        """
        Handle a link failure by updating neighbors and distance vectors.
        
        Args:
            node_a: First endpoint of failed link
            node_b: Second endpoint of failed link
        """
        logger.info(
            f"DistanceVectorRouter {self.node_id}: Handling link failure "
            f"between {node_a} and {node_b}"
        )
        
        # If we're one of the endpoints, remove the neighbor
        if self.node_id == node_a and node_b in self.neighbors:
            del self.neighbors[node_b]
            # Remove from our distance vector
            if node_b in self.my_distance_vector:
                del self.my_distance_vector[node_b]
            # Trigger update
            self._bellman_ford_update()
            self._notify_update_callbacks()
        elif self.node_id == node_b and node_a in self.neighbors:
            del self.neighbors[node_a]
            # Remove from our distance vector
            if node_a in self.my_distance_vector:
                del self.my_distance_vector[node_a]
            # Trigger update
            self._bellman_ford_update()
            self._notify_update_callbacks()
    
    def handle_node_failure(self, failed_node: str) -> None:
        """
        Handle a node failure by removing it from neighbors and distance vectors.
        
        Args:
            failed_node: Node that has failed
        """
        logger.info(
            f"DistanceVectorRouter {self.node_id}: Handling node failure of {failed_node}"
        )
        
        # Remove from neighbors if present
        if failed_node in self.neighbors:
            del self.neighbors[failed_node]
        
        # Remove from our distance vector
        if failed_node in self.my_distance_vector:
            del self.my_distance_vector[failed_node]
        
        # Remove distance vectors from failed node
        if failed_node in self.distance_vectors:
            del self.distance_vectors[failed_node]
        
        # Trigger update
        self._bellman_ford_update()
        self._notify_update_callbacks()
    
    def register_update_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when routing table is updated.
        
        Args:
            callback: Function to call on routing updates
        """
        self._update_callbacks.append(callback)
    
    def _notify_update_callbacks(self) -> None:
        """Notify all registered callbacks of routing table update."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(
                    f"DistanceVectorRouter {self.node_id}: Error in update callback: {e}"
                )
    
    def enable_traffic_aware_routing(self, enabled: bool = True) -> None:
        """
        Enable or disable traffic-aware route selection.
        
        Args:
            enabled: True to enable traffic-aware routing, False to disable
        """
        self._traffic_aware_enabled = enabled
        logger.info(
            f"DistanceVectorRouter {self.node_id}: Traffic-aware routing "
            f"{'enabled' if enabled else 'disabled'}"
        )
    
    def update_link_metrics(
        self,
        neighbor: str,
        utilization: Optional[float] = None,
        latency: Optional[float] = None,
        loss_rate: Optional[float] = None
    ) -> None:
        """
        Update traffic metrics for a link to a neighbor.
        
        Args:
            neighbor: Neighbor node ID
            utilization: Link utilization (0.0 to 1.0)
            latency: Link latency in milliseconds
            loss_rate: Packet loss rate (0.0 to 1.0)
        """
        if neighbor not in self._link_metrics:
            self._link_metrics[neighbor] = {}
        
        if utilization is not None:
            self._link_metrics[neighbor]['utilization'] = utilization
        if latency is not None:
            self._link_metrics[neighbor]['latency'] = latency
        if loss_rate is not None:
            self._link_metrics[neighbor]['loss_rate'] = loss_rate
        
        logger.debug(
            f"DistanceVectorRouter {self.node_id}: Updated metrics for neighbor {neighbor}: "
            f"util={utilization}, latency={latency}, loss={loss_rate}"
        )
    
    def compute_adjusted_cost(
        self,
        base_cost: float,
        utilization: float = 0.0,
        latency: float = 0.0,
        loss_rate: float = 0.0
    ) -> float:
        """
        Compute adjusted link cost based on traffic conditions.
        
        Args:
            base_cost: Base link cost
            utilization: Link utilization (0.0 to 1.0)
            latency: Link latency in milliseconds
            loss_rate: Packet loss rate (0.0 to 1.0)
            
        Returns:
            Adjusted cost
        """
        if not self._traffic_aware_enabled:
            return base_cost
        
        # Same adjustment formula as Dijkstra router
        utilization_factor = (utilization ** 2) * 2.0 if utilization > 0.0 else 0.0
        latency_factor = (latency / 10.0) * 0.1 if latency > 0.0 else 0.0
        loss_factor = loss_rate * 50.0 if loss_rate > 0.0 else 0.0
        
        adjustment = 1.0 + utilization_factor + latency_factor + loss_factor
        adjusted_cost = base_cost * adjustment
        
        return adjusted_cost
    
    def update_neighbors_with_traffic_metrics(
        self,
        neighbors: Dict[str, float],
        traffic_metrics: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        """
        Update neighbors with traffic-aware costs.
        
        Args:
            neighbors: Dictionary mapping neighbor IDs to base costs
            traffic_metrics: Optional dictionary of traffic metrics per neighbor
        """
        # Update base neighbors
        self.neighbors = neighbors.copy()
        
        # Update traffic metrics if provided
        if traffic_metrics:
            for neighbor, metrics in traffic_metrics.items():
                self.update_link_metrics(
                    neighbor,
                    utilization=metrics.get('utilization'),
                    latency=metrics.get('latency'),
                    loss_rate=metrics.get('loss_rate')
                )
        
        # Update distance vector with adjusted costs
        for neighbor, base_cost in neighbors.items():
            if self._traffic_aware_enabled and neighbor in self._link_metrics:
                metrics = self._link_metrics[neighbor]
                adjusted_cost = self.compute_adjusted_cost(
                    base_cost,
                    utilization=metrics.get('utilization', 0.0),
                    latency=metrics.get('latency', 0.0),
                    loss_rate=metrics.get('loss_rate', 0.0)
                )
                self.my_distance_vector[neighbor] = adjusted_cost
            else:
                self.my_distance_vector[neighbor] = base_cost
        
        # Update routing table for direct neighbors
        self._update_routing_table_for_neighbors()
    
    def update_topology_with_traffic_metrics(self, topology: NetworkTopology) -> None:
        """
        Update neighbors and traffic metrics from a NetworkTopology object.
        
        Args:
            topology: NetworkTopology object containing nodes, links, and traffic metrics
        """
        # Build neighbor list and traffic metrics from topology
        neighbors: Dict[str, float] = {}
        traffic_metrics: Dict[str, Dict[str, float]] = {}
        
        for link in topology.links:
            if link.node_a == self.node_id:
                neighbors[link.node_b] = link.cost
                traffic_metrics[link.node_b] = {
                    'utilization': link.utilization,
                    'latency': link.latency,
                    'loss_rate': link.loss_rate
                }
            elif link.node_b == self.node_id:
                neighbors[link.node_a] = link.cost
                traffic_metrics[link.node_a] = {
                    'utilization': link.utilization,
                    'latency': link.latency,
                    'loss_rate': link.loss_rate
                }
        
        self.update_neighbors_with_traffic_metrics(neighbors, traffic_metrics)
