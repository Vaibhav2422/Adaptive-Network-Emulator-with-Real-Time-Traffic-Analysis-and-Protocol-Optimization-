"""
Dijkstra Link-State Routing Implementation

This module implements Dijkstra's shortest path algorithm for link-state routing.
It maintains a link-state database and computes shortest paths to all destinations.
"""

import heapq
import time
import logging
from typing import Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field

from src.data_models import RouteEntry, Link, NetworkTopology
from src.routing_table import RoutingTable


logger = logging.getLogger(__name__)


@dataclass
class LinkStateEntry:
    """
    Represents a link-state advertisement.
    
    Attributes:
        node_id: Node advertising the link state
        neighbors: Dictionary mapping neighbor node IDs to link costs
        sequence_num: Sequence number for freshness
        timestamp: Time of last update
    """
    node_id: str
    neighbors: Dict[str, float]
    sequence_num: int = 0
    timestamp: float = field(default_factory=time.time)


class DijkstraRouter:
    """
    Implements Dijkstra link-state routing algorithm.
    
    This class maintains a link-state database containing topology information
    from all nodes and computes shortest paths using Dijkstra's algorithm.
    """
    
    def __init__(self, node_id: str):
        """
        Initialize Dijkstra router.
        
        Args:
            node_id: Identifier for this node
        """
        self.node_id = node_id
        self.link_state_db: Dict[str, LinkStateEntry] = {}
        self.routing_table = RoutingTable(node_id)
        self.sequence_num = 0
        self._last_topology_hash: Optional[int] = None
        self._update_callbacks: List[Callable] = []
        
        # Traffic-aware routing state
        self._link_metrics: Dict[Tuple[str, str], Dict[str, float]] = {}
        self._traffic_aware_enabled: bool = False
        self._cost_adjustment_factor: float = 1.0
    
    def update_link_state(self, node_id: str, neighbors: Dict[str, float]) -> None:
        """
        Update link-state database with new information.
        
        Args:
            node_id: Node advertising the link state
            neighbors: Dictionary mapping neighbor IDs to link costs
        """
        current_time = time.time()
        
        # Check if this is a new entry or an update
        if node_id in self.link_state_db:
            existing = self.link_state_db[node_id]
            # Only update if this is newer information
            sequence_num = existing.sequence_num + 1
        else:
            sequence_num = 0
        
        # Create or update link-state entry
        self.link_state_db[node_id] = LinkStateEntry(
            node_id=node_id,
            neighbors=neighbors.copy(),
            sequence_num=sequence_num,
            timestamp=current_time
        )
    
    def build_topology_from_link_state_db(self) -> NetworkTopology:
        """
        Build a NetworkTopology object from the link-state database.
        
        Returns:
            NetworkTopology object representing the current network state
        """
        # Collect all nodes
        nodes = list(self.link_state_db.keys())
        
        # Build links from link-state database
        links = []
        seen_links = set()
        
        for node_id, ls_entry in self.link_state_db.items():
            for neighbor, cost in ls_entry.neighbors.items():
                # Create a canonical link identifier to avoid duplicates
                link_id = tuple(sorted([node_id, neighbor]))
                
                if link_id not in seen_links:
                    seen_links.add(link_id)
                    links.append(Link(
                        node_a=node_id,
                        node_b=neighbor,
                        cost=cost,
                        capacity=0.0,  # Not used in routing
                        utilization=0.0,
                        latency=0.0,
                        loss_rate=0.0
                    ))
        
        return NetworkTopology(nodes=nodes, links=links)
    
    def compute_shortest_paths(self) -> Dict[str, Tuple[float, Optional[str]]]:
        """
        Compute shortest paths from this node to all other nodes using Dijkstra's algorithm.
        
        Returns:
            Dictionary mapping destination node IDs to (cost, next_hop) tuples
        """
        # Initialize distances and previous nodes
        distances: Dict[str, float] = {self.node_id: 0.0}
        previous: Dict[str, Optional[str]] = {self.node_id: None}
        visited: Set[str] = set()
        
        # Priority queue: (distance, node_id)
        pq: List[Tuple[float, str]] = [(0.0, self.node_id)]
        
        while pq:
            current_dist, current_node = heapq.heappop(pq)
            
            # Skip if already visited
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Skip if this node has no link-state information
            if current_node not in self.link_state_db:
                continue
            
            # Examine neighbors
            ls_entry = self.link_state_db[current_node]
            for neighbor, link_cost in ls_entry.neighbors.items():
                if neighbor in visited:
                    continue
                
                # Calculate distance through current node
                new_dist = current_dist + link_cost
                
                # Update if this is a shorter path
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))
        
        # Build result with next hops
        result: Dict[str, Tuple[float, Optional[str]]] = {}
        
        for dest in distances:
            if dest == self.node_id:
                continue
            
            # Trace back to find next hop
            next_hop = self._find_next_hop(dest, previous)
            result[dest] = (distances[dest], next_hop)
        
        return result
    
    def _find_next_hop(self, destination: str, previous: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Find the next hop for a destination by tracing back through the path.
        
        Args:
            destination: Destination node ID
            previous: Dictionary mapping nodes to their previous node in the shortest path
        
        Returns:
            Next hop node ID, or None if no path exists
        """
        if destination not in previous:
            return None
        
        # Trace back from destination to source
        current = destination
        path = [current]
        
        while previous[current] is not None:
            current = previous[current]
            path.append(current)
        
        # Path is now [destination, ..., source]
        # Reverse to get [source, ..., destination]
        path.reverse()
        
        # Next hop is the second node in the path (first after source)
        if len(path) >= 2:
            return path[1]
        
        return None
    
    def generate_routing_table(self, interface: str = "eth0", metric_type: str = "hop_count") -> RoutingTable:
        """
        Generate routing table from computed shortest paths.
        
        Args:
            interface: Interface identifier for routes
            metric_type: Type of metric used (hop_count, latency, bandwidth)
        
        Returns:
            RoutingTable object with routes to all reachable destinations
        """
        # Clear existing routing table
        self.routing_table.clear()
        
        # Compute shortest paths
        shortest_paths = self.compute_shortest_paths()
        
        # Add routes to routing table
        current_time = time.time()
        for destination, (cost, next_hop) in shortest_paths.items():
            if next_hop is not None:
                route_entry = RouteEntry(
                    destination=destination,
                    next_hop=next_hop,
                    cost=cost,
                    interface=interface,
                    timestamp=current_time,
                    metric_type=metric_type
                )
                self.routing_table.add(route_entry)
        
        # Notify callbacks
        self._notify_update_callbacks()
        
        return self.routing_table
    
    def update_topology(self, topology: NetworkTopology) -> None:
        """
        Update link-state database from a NetworkTopology object.
        
        Args:
            topology: NetworkTopology object containing nodes and links
        """
        # Build adjacency information from topology
        adjacency: Dict[str, Dict[str, float]] = {node: {} for node in topology.nodes}
        
        for link in topology.links:
            # Add bidirectional links
            adjacency[link.node_a][link.node_b] = link.cost
            adjacency[link.node_b][link.node_a] = link.cost
        
        # Update link-state database for all nodes
        for node_id, neighbors in adjacency.items():
            self.update_link_state(node_id, neighbors)
    
    def get_link_state_db(self) -> Dict[str, LinkStateEntry]:
        """
        Get the current link-state database.
        
        Returns:
            Dictionary mapping node IDs to LinkStateEntry objects
        """
        return self.link_state_db.copy()
    
    def clear_link_state_db(self) -> None:
        """Clear the link-state database."""
        self.link_state_db.clear()
    
    def get_routing_table(self) -> RoutingTable:
        """
        Get the current routing table.
        
        Returns:
            RoutingTable object
        """
        return self.routing_table
    
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
            logger.info(f"DijkstraRouter {self.node_id}: Topology change detected")
            return True
        
        return False
    
    def handle_link_failure(self, node_a: str, node_b: str) -> None:
        """
        Handle a link failure by updating link-state database.
        
        Args:
            node_a: First endpoint of failed link
            node_b: Second endpoint of failed link
        """
        logger.info(
            f"DijkstraRouter {self.node_id}: Handling link failure "
            f"between {node_a} and {node_b}"
        )
        
        # Remove link from link-state database
        if node_a in self.link_state_db:
            ls_entry = self.link_state_db[node_a]
            if node_b in ls_entry.neighbors:
                del ls_entry.neighbors[node_b]
                ls_entry.sequence_num += 1
                ls_entry.timestamp = time.time()
        
        if node_b in self.link_state_db:
            ls_entry = self.link_state_db[node_b]
            if node_a in ls_entry.neighbors:
                del ls_entry.neighbors[node_a]
                ls_entry.sequence_num += 1
                ls_entry.timestamp = time.time()
        
        # Trigger routing table update
        self.generate_routing_table()
    
    def handle_node_failure(self, failed_node: str) -> None:
        """
        Handle a node failure by removing it from link-state database.
        
        Args:
            failed_node: Node that has failed
        """
        logger.info(
            f"DijkstraRouter {self.node_id}: Handling node failure of {failed_node}"
        )
        
        # Remove node from link-state database
        if failed_node in self.link_state_db:
            del self.link_state_db[failed_node]
        
        # Remove references to failed node from other entries
        for node_id, ls_entry in self.link_state_db.items():
            if failed_node in ls_entry.neighbors:
                del ls_entry.neighbors[failed_node]
                ls_entry.sequence_num += 1
                ls_entry.timestamp = time.time()
        
        # Trigger routing table update
        self.generate_routing_table()
    
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
                    f"DijkstraRouter {self.node_id}: Error in update callback: {e}"
                )
    
    def enable_traffic_aware_routing(self, enabled: bool = True) -> None:
        """
        Enable or disable traffic-aware route selection.
        
        When enabled, link costs are adjusted based on current utilization and latency.
        
        Args:
            enabled: True to enable traffic-aware routing, False to disable
        """
        self._traffic_aware_enabled = enabled
        logger.info(
            f"DijkstraRouter {self.node_id}: Traffic-aware routing "
            f"{'enabled' if enabled else 'disabled'}"
        )
    
    def update_link_metrics(
        self,
        node_a: str,
        node_b: str,
        utilization: Optional[float] = None,
        latency: Optional[float] = None,
        loss_rate: Optional[float] = None
    ) -> None:
        """
        Update traffic metrics for a link.
        
        Args:
            node_a: First endpoint of link
            node_b: Second endpoint of link
            utilization: Link utilization (0.0 to 1.0)
            latency: Link latency in milliseconds
            loss_rate: Packet loss rate (0.0 to 1.0)
        """
        # Create canonical link identifier
        link_id = tuple(sorted([node_a, node_b]))
        
        if link_id not in self._link_metrics:
            self._link_metrics[link_id] = {}
        
        if utilization is not None:
            self._link_metrics[link_id]['utilization'] = utilization
        if latency is not None:
            self._link_metrics[link_id]['latency'] = latency
        if loss_rate is not None:
            self._link_metrics[link_id]['loss_rate'] = loss_rate
        
        logger.debug(
            f"DijkstraRouter {self.node_id}: Updated metrics for link {node_a}-{node_b}: "
            f"util={utilization}, latency={latency}, loss={loss_rate}"
        )
    
    def get_link_metrics(self, node_a: str, node_b: str) -> Dict[str, float]:
        """
        Get current traffic metrics for a link.
        
        Args:
            node_a: First endpoint of link
            node_b: Second endpoint of link
            
        Returns:
            Dictionary of metrics (utilization, latency, loss_rate)
        """
        link_id = tuple(sorted([node_a, node_b]))
        return self._link_metrics.get(link_id, {}).copy()
    
    def compute_adjusted_cost(
        self,
        base_cost: float,
        utilization: float = 0.0,
        latency: float = 0.0,
        loss_rate: float = 0.0
    ) -> float:
        """
        Compute adjusted link cost based on traffic conditions.
        
        The adjusted cost increases with utilization, latency, and loss rate
        to discourage routing through congested or problematic links.
        
        Formula: adjusted_cost = base_cost * (1 + utilization_factor + latency_factor + loss_factor)
        
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
        
        # Utilization factor: increases exponentially as utilization approaches 1.0
        # At 50% utilization, adds 25% to cost
        # At 80% utilization, adds 100% to cost
        # At 90% utilization, adds 200% to cost
        utilization_factor = 0.0
        if utilization > 0.0:
            # Exponential penalty for high utilization
            utilization_factor = (utilization ** 2) * 2.0
        
        # Latency factor: normalized by typical latency (assume 10ms is baseline)
        # Every 10ms of latency adds 10% to cost
        latency_factor = 0.0
        if latency > 0.0:
            latency_factor = (latency / 10.0) * 0.1
        
        # Loss rate factor: each 1% loss adds 50% to cost
        # At 5% loss, adds 250% to cost
        loss_factor = 0.0
        if loss_rate > 0.0:
            loss_factor = loss_rate * 50.0
        
        # Compute adjusted cost
        adjustment = 1.0 + utilization_factor + latency_factor + loss_factor
        adjusted_cost = base_cost * adjustment * self._cost_adjustment_factor
        
        logger.debug(
            f"DijkstraRouter {self.node_id}: Cost adjustment: "
            f"base={base_cost:.2f}, util_factor={utilization_factor:.2f}, "
            f"latency_factor={latency_factor:.2f}, loss_factor={loss_factor:.2f}, "
            f"adjusted={adjusted_cost:.2f}"
        )
        
        return adjusted_cost
    
    def set_cost_adjustment_factor(self, factor: float) -> None:
        """
        Set the global cost adjustment factor.
        
        This factor is multiplied with all adjusted costs to control
        the aggressiveness of traffic-aware routing.
        
        Args:
            factor: Adjustment factor (1.0 = normal, >1.0 = more aggressive, <1.0 = less aggressive)
        """
        self._cost_adjustment_factor = max(0.1, factor)
        logger.info(
            f"DijkstraRouter {self.node_id}: Cost adjustment factor set to {factor}"
        )
    
    def compute_shortest_paths_with_traffic_awareness(self) -> Dict[str, Tuple[float, Optional[str]]]:
        """
        Compute shortest paths considering current traffic conditions.
        
        This method is similar to compute_shortest_paths but uses adjusted costs
        based on link utilization, latency, and loss rate.
        
        Returns:
            Dictionary mapping destination node IDs to (cost, next_hop) tuples
        """
        if not self._traffic_aware_enabled:
            # Fall back to regular shortest path computation
            return self.compute_shortest_paths()
        
        # Initialize distances and previous nodes
        distances: Dict[str, float] = {self.node_id: 0.0}
        previous: Dict[str, Optional[str]] = {self.node_id: None}
        visited: Set[str] = set()
        
        # Priority queue: (distance, node_id)
        pq: List[Tuple[float, str]] = [(0.0, self.node_id)]
        
        while pq:
            current_dist, current_node = heapq.heappop(pq)
            
            # Skip if already visited
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Skip if this node has no link-state information
            if current_node not in self.link_state_db:
                continue
            
            # Examine neighbors
            ls_entry = self.link_state_db[current_node]
            for neighbor, base_cost in ls_entry.neighbors.items():
                if neighbor in visited:
                    continue
                
                # Get traffic metrics for this link
                link_id = tuple(sorted([current_node, neighbor]))
                metrics = self._link_metrics.get(link_id, {})
                
                # Compute adjusted cost
                adjusted_cost = self.compute_adjusted_cost(
                    base_cost,
                    utilization=metrics.get('utilization', 0.0),
                    latency=metrics.get('latency', 0.0),
                    loss_rate=metrics.get('loss_rate', 0.0)
                )
                
                # Calculate distance through current node
                new_dist = current_dist + adjusted_cost
                
                # Update if this is a shorter path
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))
        
        # Build result with next hops
        result: Dict[str, Tuple[float, Optional[str]]] = {}
        
        for dest in distances:
            if dest == self.node_id:
                continue
            
            # Trace back to find next hop
            next_hop = self._find_next_hop(dest, previous)
            result[dest] = (distances[dest], next_hop)
        
        return result
    
    def update_topology_with_traffic_metrics(self, topology: NetworkTopology) -> None:
        """
        Update link-state database and traffic metrics from a NetworkTopology object.
        
        This method extracts both routing information and traffic metrics from the topology.
        
        Args:
            topology: NetworkTopology object containing nodes, links, and traffic metrics
        """
        # Update link-state database (standard topology update)
        self.update_topology(topology)
        
        # Update traffic metrics from links
        for link in topology.links:
            self.update_link_metrics(
                link.node_a,
                link.node_b,
                utilization=link.utilization,
                latency=link.latency,
                loss_rate=link.loss_rate
            )
    
    def generate_traffic_aware_routing_table(
        self,
        interface: str = "eth0",
        metric_type: str = "traffic_aware"
    ) -> RoutingTable:
        """
        Generate routing table using traffic-aware shortest paths.
        
        Args:
            interface: Interface identifier for routes
            metric_type: Type of metric used
        
        Returns:
            RoutingTable object with traffic-aware routes
        """
        # Clear existing routing table
        self.routing_table.clear()
        
        # Compute traffic-aware shortest paths
        shortest_paths = self.compute_shortest_paths_with_traffic_awareness()
        
        # Add routes to routing table
        current_time = time.time()
        for destination, (cost, next_hop) in shortest_paths.items():
            if next_hop is not None:
                route_entry = RouteEntry(
                    destination=destination,
                    next_hop=next_hop,
                    cost=cost,
                    interface=interface,
                    timestamp=current_time,
                    metric_type=metric_type
                )
                self.routing_table.add(route_entry)
        
        # Notify callbacks
        self._notify_update_callbacks()
        
        return self.routing_table
