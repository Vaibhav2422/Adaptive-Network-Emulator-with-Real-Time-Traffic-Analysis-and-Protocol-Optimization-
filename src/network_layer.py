"""
Network Layer implementation for the Adaptive Network Emulator.

This module implements IP addressing, subnetting, and packet forwarding logic.
It provides the foundation for routing algorithms (Dijkstra and Distance Vector)
to be implemented in subsequent tasks.

Validates: Requirements 4.1, 4.6
"""

import ipaddress
import logging
import time
from typing import Dict, Optional, Tuple, Set, Callable
from dataclasses import dataclass
from src.data_models import Packet, RouteEntry, NetworkTopology
from src.routing_table import RoutingTable
from src.icmp_simulator import ICMPSimulator, ICMPMessage, ICMPType


logger = logging.getLogger(__name__)


class NetworkLayer:
    """
    Network Layer implementation with IP addressing and packet forwarding.
    
    This class manages IP address assignment, subnet calculations, and basic
    packet forwarding logic. It uses a RoutingTable instance to manage routing
    information that will be populated by routing algorithms in later tasks.
    
    Attributes:
        node_id: Unique identifier for this network node
        ip_address: IP address assigned to this node
        subnet_mask: Subnet mask for this node's network
        routing_table: RoutingTable instance for managing routes
    """
    
    def __init__(self, node_id: str, ip_address: str, subnet_mask: str = "255.255.255.0"):
        """
        Initialize the Network Layer.
        
        Args:
            node_id: Unique identifier for this node
            ip_address: IP address for this node (e.g., "192.168.1.1")
            subnet_mask: Subnet mask (default: "255.255.255.0")
            
        Raises:
            ValueError: If IP address or subnet mask is invalid
        """
        self.node_id = node_id
        
        # Validate and store IP address
        try:
            self._ip_obj = ipaddress.IPv4Address(ip_address)
            self.ip_address = ip_address
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid IP address '{ip_address}': {e}")
        
        # Validate and store subnet mask
        try:
            self._mask_obj = ipaddress.IPv4Address(subnet_mask)
            self.subnet_mask = subnet_mask
            # Calculate prefix length from subnet mask
            self._prefix_length = sum(bin(int(octet)).count('1') 
                                     for octet in subnet_mask.split('.'))
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid subnet mask '{subnet_mask}': {e}")
        
        # Create network object for subnet calculations
        self._network = ipaddress.IPv4Network(
            f"{ip_address}/{self._prefix_length}", 
            strict=False
        )
        
        # Initialize routing table using RoutingTable class
        self.routing_table = RoutingTable(node_id)
        
        # Track topology state for change detection
        self._topology_hash: Optional[int] = None
        self._failed_links: set = set()
        
        # Initialize ICMP simulator
        self.icmp_simulator = ICMPSimulator(node_id, ip_address)
        
        logger.info(
            f"NetworkLayer initialized for node {node_id}: "
            f"IP={ip_address}, Subnet={self._network}, Mask={subnet_mask}"
        )
    
    def assign_ip_address(self, ip_address: str, subnet_mask: str = "255.255.255.0") -> None:
        """
        Assign or update the IP address for this node.
        
        Args:
            ip_address: New IP address
            subnet_mask: New subnet mask (default: "255.255.255.0")
            
        Raises:
            ValueError: If IP address or subnet mask is invalid
        """
        try:
            self._ip_obj = ipaddress.IPv4Address(ip_address)
            self.ip_address = ip_address
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid IP address '{ip_address}': {e}")
        
        try:
            self._mask_obj = ipaddress.IPv4Address(subnet_mask)
            self.subnet_mask = subnet_mask
            self._prefix_length = sum(bin(int(octet)).count('1') 
                                     for octet in subnet_mask.split('.'))
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid subnet mask '{subnet_mask}': {e}")
        
        self._network = ipaddress.IPv4Network(
            f"{ip_address}/{self._prefix_length}", 
            strict=False
        )
        
        logger.info(
            f"Node {self.node_id} IP address updated: "
            f"IP={ip_address}, Subnet={self._network}"
        )
    
    def validate_ip_address(self, ip_address: str) -> bool:
        """
        Validate an IP address format.
        
        Args:
            ip_address: IP address string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            ipaddress.IPv4Address(ip_address)
            return True
        except ipaddress.AddressValueError:
            return False
    
    def calculate_subnet(self, ip_address: str, subnet_mask: str) -> Tuple[str, str, str, int]:
        """
        Calculate subnet information for a given IP address and mask.
        
        Args:
            ip_address: IP address
            subnet_mask: Subnet mask
            
        Returns:
            Tuple of (network_address, broadcast_address, first_host, num_hosts)
            
        Raises:
            ValueError: If IP address or subnet mask is invalid
        """
        try:
            prefix_length = sum(bin(int(octet)).count('1') 
                               for octet in subnet_mask.split('.'))
            network = ipaddress.IPv4Network(f"{ip_address}/{prefix_length}", strict=False)
            
            network_address = str(network.network_address)
            broadcast_address = str(network.broadcast_address)
            
            # Calculate first usable host address
            hosts = list(network.hosts())
            first_host = str(hosts[0]) if hosts else network_address
            
            # Number of usable hosts (excluding network and broadcast addresses)
            num_hosts = network.num_addresses - 2 if network.num_addresses > 2 else 0
            
            return network_address, broadcast_address, first_host, num_hosts
            
        except (ipaddress.AddressValueError, ValueError) as e:
            raise ValueError(f"Invalid IP address or subnet mask: {e}")
    
    def is_same_subnet(self, ip1: str, ip2: str, subnet_mask: str) -> bool:
        """
        Check if two IP addresses are in the same subnet.
        
        Args:
            ip1: First IP address
            ip2: Second IP address
            subnet_mask: Subnet mask to use for comparison
            
        Returns:
            True if both IPs are in the same subnet, False otherwise
            
        Raises:
            ValueError: If any IP address or subnet mask is invalid
        """
        try:
            prefix_length = sum(bin(int(octet)).count('1') 
                               for octet in subnet_mask.split('.'))
            
            network1 = ipaddress.IPv4Network(f"{ip1}/{prefix_length}", strict=False)
            network2 = ipaddress.IPv4Network(f"{ip2}/{prefix_length}", strict=False)
            
            return network1.network_address == network2.network_address
            
        except (ipaddress.AddressValueError, ValueError) as e:
            raise ValueError(f"Invalid IP address or subnet mask: {e}")
    
    def is_in_subnet(self, ip_address: str) -> bool:
        """
        Check if an IP address is in this node's subnet.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if the IP is in this node's subnet, False otherwise
        """
        try:
            ip_obj = ipaddress.IPv4Address(ip_address)
            return ip_obj in self._network
        except ipaddress.AddressValueError:
            return False
    
    def add_route(self, route_entry: RouteEntry) -> None:
        """
        Add or update a route in the routing table.
        
        Args:
            route_entry: RouteEntry object containing routing information
        """
        self.routing_table.add(route_entry)
    
    def remove_route(self, destination: str) -> bool:
        """
        Remove a route from the routing table.
        
        Args:
            destination: Destination IP address or network
            
        Returns:
            True if route was removed, False if not found
        """
        return self.routing_table.remove(destination)
    
    def get_next_hop(self, dest_ip: str) -> Optional[str]:
        """
        Get the next hop for a destination IP address.
        
        This method looks up the routing table to find the next hop for
        forwarding a packet to the destination. It supports both exact
        matches and subnet-based routing.
        
        Args:
            dest_ip: Destination IP address
            
        Returns:
            Next hop IP address, or None if no route found
        """
        return self.routing_table.lookup(dest_ip, self._network)
    
    def forward_packet(self, packet: Packet) -> Optional[str]:
        """
        Determine the next hop for forwarding a packet.
        
        This method implements the packet forwarding logic by looking up
        the routing table and determining where to send the packet next.
        
        Args:
            packet: Packet to forward
            
        Returns:
            Next hop IP address, or None if packet cannot be forwarded
        """
        # Check if this packet is for us
        if packet.dest_ip == self.ip_address:
            logger.debug(
                f"Node {self.node_id}: Packet {packet.packet_id} "
                f"reached destination"
            )
            return None  # Packet has reached its destination
        
        # Look up next hop
        next_hop = self.get_next_hop(packet.dest_ip)
        
        if next_hop:
            logger.debug(
                f"Node {self.node_id}: Forwarding packet {packet.packet_id} "
                f"to {packet.dest_ip} via {next_hop}"
            )
        else:
            logger.warning(
                f"Node {self.node_id}: Cannot forward packet {packet.packet_id} "
                f"to {packet.dest_ip} - no route"
            )
        
        return next_hop
    
    def get_routing_table(self) -> Dict[str, RouteEntry]:
        """
        Get a copy of the current routing table.
        
        Returns:
            Dictionary mapping destination addresses to RouteEntry objects
        """
        return self.routing_table.get_all()
    
    def clear_routing_table(self) -> None:
        """Clear all routes from the routing table."""
        self.routing_table.clear()
    
    def detect_topology_change(self, topology: NetworkTopology) -> bool:
        """
        Detect if the network topology has changed.
        
        This method computes a hash of the topology and compares it with
        the previous hash to detect changes in nodes or links.
        
        Args:
            topology: Current network topology
            
        Returns:
            True if topology has changed, False otherwise
        """
        # Compute hash of topology
        topology_str = f"{sorted(topology.nodes)}"
        for link in sorted(topology.links, key=lambda l: (l.node_a, l.node_b)):
            topology_str += f"{link.node_a}{link.node_b}{link.cost}"
        
        current_hash = hash(topology_str)
        
        # Check if this is the first topology or if it changed
        if self._topology_hash is None:
            self._topology_hash = current_hash
            logger.info(f"Node {self.node_id}: Initial topology recorded")
            return True
        
        if current_hash != self._topology_hash:
            logger.info(f"Node {self.node_id}: Topology change detected")
            self._topology_hash = current_hash
            return True
        
        return False
    
    def invalidate_routes_via_node(self, failed_node: str) -> int:
        """
        Invalidate all routes that go through a failed node.
        
        Args:
            failed_node: Node ID that has failed
            
        Returns:
            Number of routes invalidated
        """
        routes_to_remove = []
        
        for dest, route in self.routing_table.get_all().items():
            if route.next_hop == failed_node or dest == failed_node:
                routes_to_remove.append(dest)
        
        count = 0
        for dest in routes_to_remove:
            if self.routing_table.remove(dest):
                count += 1
                logger.info(
                    f"Node {self.node_id}: Invalidated route to {dest} "
                    f"(via failed node {failed_node})"
                )
        
        return count
    
    def invalidate_routes_via_link(self, node_a: str, node_b: str) -> int:
        """
        Invalidate routes that depend on a failed link.
        
        Args:
            node_a: First endpoint of failed link
            node_b: Second endpoint of failed link
            
        Returns:
            Number of routes invalidated
        """
        # Track this failed link
        link_id = tuple(sorted([node_a, node_b]))
        self._failed_links.add(link_id)
        
        # For simplicity, invalidate routes to both endpoints
        # In a real implementation, we'd need to check if routes actually use this link
        count = 0
        
        # If we're node_a, invalidate routes through node_b
        if self.node_id == node_a:
            count = self.invalidate_routes_via_node(node_b)
        # If we're node_b, invalidate routes through node_a
        elif self.node_id == node_b:
            count = self.invalidate_routes_via_node(node_a)
        
        logger.info(
            f"Node {self.node_id}: Link failure between {node_a} and {node_b}, "
            f"invalidated {count} routes"
        )
        
        return count
    
    def mark_route_stale(self, destination: str, max_age_seconds: float = 180.0) -> bool:
        """
        Check if a route is stale based on its timestamp.
        
        Args:
            destination: Destination address
            max_age_seconds: Maximum age in seconds before route is considered stale
            
        Returns:
            True if route is stale and was removed, False otherwise
        """
        route = self.routing_table.get(destination)
        if route is None:
            return False
        
        age = time.time() - route.timestamp
        if age > max_age_seconds:
            self.routing_table.remove(destination)
            logger.info(
                f"Node {self.node_id}: Removed stale route to {destination} "
                f"(age: {age:.1f}s)"
            )
            return True
        
        return False
    
    def refresh_route_timestamp(self, destination: str) -> bool:
        """
        Refresh the timestamp of a route to mark it as recently validated.
        
        Args:
            destination: Destination address
            
        Returns:
            True if route was refreshed, False if not found
        """
        return self.routing_table.update(destination, timestamp=time.time())
    
    def trigger_routing_update(self, update_callback: Optional[Callable] = None) -> None:
        """
        Trigger a routing table update.
        
        This method can be called when topology changes are detected to
        trigger recomputation of routes. An optional callback can be provided
        to perform the actual routing algorithm computation.
        
        Args:
            update_callback: Optional callback function to recompute routes
        """
        logger.info(f"Node {self.node_id}: Routing update triggered")
        
        if update_callback:
            update_callback()
        else:
            logger.debug(
                f"Node {self.node_id}: No update callback provided, "
                f"manual route recomputation required"
            )
    
    def handle_icmp_message(self, message: ICMPMessage) -> Optional[ICMPMessage]:
        """
        Handle an incoming ICMP message.
        
        Args:
            message: ICMP message to handle
            
        Returns:
            Optional ICMP reply message
        """
        if message.icmp_type == ICMPType.ECHO_REQUEST:
            # Generate echo reply
            return self.icmp_simulator.handle_echo_request(message)
        elif message.icmp_type == ICMPType.ECHO_REPLY:
            # Process echo reply
            self.icmp_simulator.handle_echo_reply(message)
            return None
        elif message.icmp_type == ICMPType.DESTINATION_UNREACHABLE:
            # Process destination unreachable
            self.icmp_simulator.handle_destination_unreachable(message)
            return None
        elif message.icmp_type == ICMPType.TIME_EXCEEDED:
            # Process time exceeded
            self.icmp_simulator.handle_time_exceeded(message)
            return None
        
        return None
    
    def send_destination_unreachable(self, dest_ip: str, original_packet: Optional[Packet] = None) -> ICMPMessage:
        """
        Send a destination unreachable ICMP message.
        
        Args:
            dest_ip: Destination that is unreachable
            original_packet: Optional original packet that couldn't be delivered
            
        Returns:
            ICMP destination unreachable message
        """
        from src.icmp_simulator import ICMPCode
        
        original_data = b''
        if original_packet:
            # In a real implementation, we'd serialize the packet header
            original_data = original_packet.packet_id.encode()
        
        return self.icmp_simulator.create_destination_unreachable(
            dest_ip,
            code=ICMPCode.HOST_UNREACHABLE,
            original_packet_data=original_data
        )
    
    def check_packet_ttl(self, packet: Packet, ttl: int) -> Tuple[bool, Optional[ICMPMessage]]:
        """
        Check if a packet's TTL has expired.
        
        Args:
            packet: Packet to check
            ttl: Current TTL value
            
        Returns:
            Tuple of (should_forward, icmp_message)
        """
        return self.icmp_simulator.check_ttl(ttl, packet.dest_ip)
