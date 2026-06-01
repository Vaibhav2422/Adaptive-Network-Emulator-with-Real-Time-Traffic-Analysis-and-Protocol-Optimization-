"""
Routing Table implementation for the Adaptive Network Emulator.

This module provides a dedicated RoutingTable class for managing routing
information, including add/update/lookup operations and serialization.

Validates: Requirements 4.6
"""

import json
import logging
import ipaddress
from typing import Dict, Optional, List
from src.data_models import RouteEntry


logger = logging.getLogger(__name__)


class RoutingTable:
    """
    Routing table for managing network routes.
    
    This class provides operations for adding, updating, removing, and looking up
    routes. It supports both exact matches and longest prefix matching for
    subnet-based routing.
    
    Attributes:
        node_id: Identifier for the node owning this routing table
        routes: Dictionary mapping destination addresses to RouteEntry objects
    """
    
    def __init__(self, node_id: str):
        """
        Initialize the routing table.
        
        Args:
            node_id: Unique identifier for the node owning this table
        """
        self.node_id = node_id
        self.routes: Dict[str, RouteEntry] = {}
        logger.debug(f"RoutingTable initialized for node {node_id}")
    
    def add(self, route_entry: RouteEntry) -> None:
        """
        Add or update a route in the routing table.
        
        If a route to the same destination already exists, it will be replaced.
        
        Args:
            route_entry: RouteEntry object containing routing information
        """
        self.routes[route_entry.destination] = route_entry
        logger.debug(
            f"Node {self.node_id}: Added/updated route to {route_entry.destination} "
            f"via {route_entry.next_hop} (cost={route_entry.cost})"
        )
    
    def update(self, destination: str, **kwargs) -> bool:
        """
        Update specific fields of an existing route.
        
        Args:
            destination: Destination address of the route to update
            **kwargs: Fields to update (next_hop, cost, interface, timestamp, metric_type)
            
        Returns:
            True if route was updated, False if route not found
        """
        if destination not in self.routes:
            logger.warning(
                f"Node {self.node_id}: Cannot update route to {destination} - not found"
            )
            return False
        
        route = self.routes[destination]
        
        # Update allowed fields
        for field in ['next_hop', 'cost', 'interface', 'timestamp', 'metric_type']:
            if field in kwargs:
                setattr(route, field, kwargs[field])
        
        logger.debug(
            f"Node {self.node_id}: Updated route to {destination} with {kwargs}"
        )
        return True
    
    def remove(self, destination: str) -> bool:
        """
        Remove a route from the routing table.
        
        Args:
            destination: Destination address of the route to remove
            
        Returns:
            True if route was removed, False if not found
        """
        if destination in self.routes:
            del self.routes[destination]
            logger.debug(f"Node {self.node_id}: Removed route to {destination}")
            return True
        
        logger.debug(
            f"Node {self.node_id}: Cannot remove route to {destination} - not found"
        )
        return False
    
    def lookup(self, dest_ip: str, local_network: Optional[ipaddress.IPv4Network] = None) -> Optional[str]:
        """
        Look up the next hop for a destination IP address.
        
        This method implements longest prefix matching for subnet-based routing.
        It checks for exact matches first, then subnet matches, and finally
        falls back to a default route if available.
        
        Args:
            dest_ip: Destination IP address to look up
            local_network: Optional local network for direct delivery check
            
        Returns:
            Next hop IP address, or None if no route found
        """
        # Check for exact match first
        if dest_ip in self.routes:
            next_hop = self.routes[dest_ip].next_hop
            logger.debug(
                f"Node {self.node_id}: Route to {dest_ip} via {next_hop} (exact match)"
            )
            return next_hop
        
        # Check if destination is in local network (direct delivery)
        if local_network:
            try:
                dest_ip_obj = ipaddress.IPv4Address(dest_ip)
                if dest_ip_obj in local_network:
                    logger.debug(
                        f"Node {self.node_id}: {dest_ip} is in local network, "
                        f"direct delivery"
                    )
                    return dest_ip
            except ipaddress.AddressValueError:
                pass
        
        # Longest prefix match for subnet-based routing
        try:
            dest_ip_obj = ipaddress.IPv4Address(dest_ip)
            
            best_match = None
            best_prefix_len = -1
            
            for dest_network, route_entry in self.routes.items():
                try:
                    # Try to parse as network (CIDR notation)
                    if '/' in dest_network:
                        network = ipaddress.IPv4Network(dest_network, strict=False)
                        if dest_ip_obj in network:
                            prefix_len = network.prefixlen
                            if prefix_len > best_prefix_len:
                                best_match = route_entry
                                best_prefix_len = prefix_len
                except ValueError:
                    # Not a valid network, skip
                    continue
            
            if best_match:
                logger.debug(
                    f"Node {self.node_id}: Route to {dest_ip} via "
                    f"{best_match.next_hop} (subnet match, prefix={best_prefix_len})"
                )
                return best_match.next_hop
            
        except ipaddress.AddressValueError:
            logger.warning(f"Node {self.node_id}: Invalid destination IP: {dest_ip}")
            return None
        
        # Check for default route (0.0.0.0/0)
        if "0.0.0.0/0" in self.routes:
            default_route = self.routes["0.0.0.0/0"]
            logger.debug(
                f"Node {self.node_id}: Using default route for {dest_ip} "
                f"via {default_route.next_hop}"
            )
            return default_route.next_hop
        
        logger.debug(f"Node {self.node_id}: No route to {dest_ip}")
        return None
    
    def get(self, destination: str) -> Optional[RouteEntry]:
        """
        Get a specific route entry by destination.
        
        Args:
            destination: Destination address
            
        Returns:
            RouteEntry if found, None otherwise
        """
        return self.routes.get(destination)
    
    def get_all(self) -> Dict[str, RouteEntry]:
        """
        Get a copy of all routes in the table.
        
        Returns:
            Dictionary mapping destination addresses to RouteEntry objects
        """
        return self.routes.copy()
    
    def clear(self) -> None:
        """Clear all routes from the routing table."""
        self.routes.clear()
        logger.info(f"Node {self.node_id}: Routing table cleared")
    
    def size(self) -> int:
        """
        Get the number of routes in the table.
        
        Returns:
            Number of routes
        """
        return len(self.routes)
    
    def to_dict(self) -> dict:
        """
        Serialize the routing table to a dictionary.
        
        Returns:
            Dictionary representation of the routing table
        """
        return {
            "node_id": self.node_id,
            "routes": {
                dest: route.to_dict() 
                for dest, route in self.routes.items()
            }
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize the routing table to a JSON string.
        
        Args:
            indent: Optional indentation level for pretty printing
            
        Returns:
            JSON string representation of the routing table
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RoutingTable':
        """
        Deserialize a routing table from a dictionary.
        
        Args:
            data: Dictionary containing routing table data
            
        Returns:
            RoutingTable instance
        """
        table = cls(data["node_id"])
        for dest, route_data in data.get("routes", {}).items():
            route = RouteEntry.from_dict(route_data)
            table.add(route)
        return table
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RoutingTable':
        """
        Deserialize a routing table from a JSON string.
        
        Args:
            json_str: JSON string containing routing table data
            
        Returns:
            RoutingTable instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_log_format(self) -> List[str]:
        """
        Format the routing table for logging.
        
        Returns:
            List of formatted strings, one per route
        """
        if not self.routes:
            return [f"Node {self.node_id}: Routing table is empty"]
        
        lines = [f"Node {self.node_id}: Routing table ({len(self.routes)} routes):"]
        lines.append(f"{'Destination':<20} {'Next Hop':<15} {'Cost':<10} {'Interface':<10} {'Metric Type':<15}")
        lines.append("-" * 80)
        
        for dest, route in sorted(self.routes.items()):
            lines.append(
                f"{dest:<20} {route.next_hop:<15} {route.cost:<10.2f} "
                f"{route.interface:<10} {route.metric_type:<15}"
            )
        
        return lines
    
    def __str__(self) -> str:
        """String representation of the routing table."""
        return "\n".join(self.to_log_format())
    
    def __repr__(self) -> str:
        """Developer-friendly representation of the routing table."""
        return f"RoutingTable(node_id='{self.node_id}', routes={len(self.routes)})"
