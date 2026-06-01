"""
Network Topology implementation for the Adaptive Network Emulator.

This module implements the NetworkTopology class for managing nodes and links,
and provides topology builders for common network patterns (mesh, star, ring).

Validates: Requirements 1.1, 11.2
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from src.node import Node, NodeConfig
from src.physical_layer import PhysicalLayer, PhysicalLayerConfig
from src.data_models import Link


@dataclass
class TopologyConfig:
    """Configuration for network topology."""
    topology_type: str = "mesh"  # mesh, star, ring, custom
    num_nodes: int = 3
    base_ip: str = "192.168.1.0"
    subnet_mask: str = "255.255.255.0"
    
    # Physical layer defaults
    bit_rate_bps: float = 100_000_000
    propagation_delay_ms: float = 10.0
    loss_rate: float = 0.0
    bit_error_rate: float = 0.0
    
    # Transport layer defaults
    transport_protocol: str = "GBN"
    window_size: int = 8
    timeout_ms: int = 100
    
    # Random seed for reproducibility
    random_seed: Optional[int] = None


class NetworkTopology:
    """
    Network topology manager.
    
    Manages a collection of nodes and the links between them. Provides
    methods for creating common topology patterns and managing node-to-node
    communication.
    
    Attributes:
        config: Topology configuration
        nodes: Dictionary of node_id -> Node
        links: List of Link objects
        physical_layer: Shared physical layer instance
    
    Validates: Requirements 1.1, 11.2
    """
    
    def __init__(self, config: TopologyConfig):
        """
        Initialize network topology.
        
        Args:
            config: Topology configuration
        """
        self.config = config
        self.logger = logging.getLogger("emulator.topology")
        
        # Create shared physical layer
        physical_config = PhysicalLayerConfig(
            bit_rate_bps=config.bit_rate_bps,
            propagation_delay_ms=config.propagation_delay_ms,
            loss_rate=config.loss_rate,
            bit_error_rate=config.bit_error_rate,
            random_seed=config.random_seed
        )
        self.physical_layer = PhysicalLayer(physical_config)
        
        # Initialize node and link storage
        self.nodes: Dict[str, Node] = {}
        self.links: List[Link] = []
        
        # Adjacency information for routing
        self.adjacency: Dict[str, Set[str]] = {}
        
        self.logger.info(
            f"Network topology initialized: type={config.topology_type}, "
            f"nodes={config.num_nodes}"
        )
    
    def add_node(self, node_id: str, ip_address: Optional[str] = None,
                 mac_address: Optional[str] = None) -> Node:
        """
        Add a node to the topology.
        
        Args:
            node_id: Unique node identifier
            ip_address: IP address (auto-generated if None)
            mac_address: MAC address (auto-generated if None)
        
        Returns:
            Created Node instance
        """
        # Auto-generate IP if not provided
        if ip_address is None:
            node_num = len(self.nodes) + 1
            base_octets = self.config.base_ip.split('.')
            ip_address = f"{base_octets[0]}.{base_octets[1]}.{base_octets[2]}.{node_num}"
        
        # Auto-generate MAC if not provided
        if mac_address is None:
            node_num = len(self.nodes) + 1
            mac_address = f"00:00:00:00:00:{node_num:02X}"
        
        # Create node configuration
        node_config = NodeConfig(
            node_id=node_id,
            ip_address=ip_address,
            mac_address=mac_address,
            subnet_mask=self.config.subnet_mask,
            transport_protocol=self.config.transport_protocol,
            window_size=self.config.window_size,
            timeout_ms=self.config.timeout_ms,
            bit_rate_bps=self.config.bit_rate_bps,
            propagation_delay_ms=self.config.propagation_delay_ms,
            loss_rate=self.config.loss_rate,
            bit_error_rate=self.config.bit_error_rate,
            random_seed=self.config.random_seed
        )
        
        # Create node with shared physical layer
        node = Node(node_config, self.physical_layer)
        
        # Add to topology
        self.nodes[node_id] = node
        self.adjacency[node_id] = set()
        
        self.logger.info(
            f"Node added: {node_id} (IP={ip_address}, MAC={mac_address})"
        )
        
        return node
    
    def add_link(self, node_a_id: str, node_b_id: str, cost: float = 1.0,
                 capacity: float = 100.0, bidirectional: bool = True) -> Link:
        """
        Add a link between two nodes.
        
        Args:
            node_a_id: First node identifier
            node_b_id: Second node identifier
            cost: Link cost (for routing)
            capacity: Link capacity in Mbps
            bidirectional: Whether link is bidirectional
        
        Returns:
            Created Link instance
        """
        if node_a_id not in self.nodes:
            raise ValueError(f"Node {node_a_id} not found")
        if node_b_id not in self.nodes:
            raise ValueError(f"Node {node_b_id} not found")
        
        # Create link
        link = Link(
            node_a=node_a_id,
            node_b=node_b_id,
            cost=cost,
            capacity=capacity,
            utilization=0.0,
            latency=self.config.propagation_delay_ms,
            loss_rate=self.config.loss_rate
        )
        
        self.links.append(link)
        
        # Update adjacency
        self.adjacency[node_a_id].add(node_b_id)
        if bidirectional:
            self.adjacency[node_b_id].add(node_a_id)
        
        self.logger.info(
            f"Link added: {node_a_id} <-> {node_b_id} "
            f"(cost={cost}, capacity={capacity} Mbps, bidirectional={bidirectional})"
        )
        
        return link
    
    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from the topology.
        
        Args:
            node_id: Node identifier to remove
        
        Returns:
            True if node was removed
        """
        if node_id not in self.nodes:
            return False
        
        # Remove node
        del self.nodes[node_id]
        
        # Remove from adjacency
        if node_id in self.adjacency:
            del self.adjacency[node_id]
        
        # Remove from other nodes' adjacency lists
        for neighbors in self.adjacency.values():
            neighbors.discard(node_id)
        
        # Remove links involving this node
        self.links = [link for link in self.links 
                     if link.node_a != node_id and link.node_b != node_id]
        
        self.logger.info(f"Node removed: {node_id}")
        return True
    
    def remove_link(self, node_a_id: str, node_b_id: str) -> bool:
        """
        Remove a link between two nodes.
        
        Args:
            node_a_id: First node identifier
            node_b_id: Second node identifier
        
        Returns:
            True if link was removed
        """
        # Remove from links list
        initial_count = len(self.links)
        self.links = [link for link in self.links 
                     if not ((link.node_a == node_a_id and link.node_b == node_b_id) or
                            (link.node_a == node_b_id and link.node_b == node_a_id))]
        
        if len(self.links) == initial_count:
            return False
        
        # Update adjacency
        if node_a_id in self.adjacency:
            self.adjacency[node_a_id].discard(node_b_id)
        if node_b_id in self.adjacency:
            self.adjacency[node_b_id].discard(node_a_id)
        
        self.logger.info(f"Link removed: {node_a_id} <-> {node_b_id}")
        return True
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_all_nodes(self) -> Dict[str, Node]:
        """Get all nodes."""
        return self.nodes.copy()
    
    def get_all_links(self) -> List[Link]:
        """Get all links."""
        return self.links.copy()
    
    def get_neighbors(self, node_id: str) -> Set[str]:
        """Get neighbors of a node."""
        return self.adjacency.get(node_id, set()).copy()
    
    def send_message(self, source_id: str, dest_id: str, message: str,
                    protocol: str = "TCP") -> bool:
        """
        Send a message from one node to another.
        
        Args:
            source_id: Source node identifier
            dest_id: Destination node identifier
            message: Message to send
            protocol: Protocol to use (TCP or UDP)
        
        Returns:
            True if message was sent successfully
        """
        source_node = self.nodes.get(source_id)
        dest_node = self.nodes.get(dest_id)
        
        if not source_node or not dest_node:
            self.logger.error(f"Cannot send message: node not found")
            return False
        
        # Get destination IP
        dest_ip = dest_node.get_ip_address()
        
        # Send message
        return source_node.send_message(dest_ip, message, protocol)
    
    def build_mesh_topology(self) -> None:
        """
        Build a full mesh topology.
        
        In a mesh topology, every node is connected to every other node.
        """
        self.logger.info(f"Building mesh topology with {self.config.num_nodes} nodes")
        
        # Create nodes
        for i in range(self.config.num_nodes):
            node_id = f"node_{i}"
            self.add_node(node_id)
        
        # Create links between all pairs
        node_ids = list(self.nodes.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                self.add_link(node_ids[i], node_ids[j], cost=1.0)
        
        self.logger.info(
            f"Mesh topology created: {len(self.nodes)} nodes, {len(self.links)} links"
        )
    
    def build_star_topology(self, center_node_id: Optional[str] = None) -> None:
        """
        Build a star topology.
        
        In a star topology, one central node is connected to all other nodes.
        
        Args:
            center_node_id: ID for center node (auto-generated if None)
        """
        self.logger.info(f"Building star topology with {self.config.num_nodes} nodes")
        
        # Create center node
        if center_node_id is None:
            center_node_id = "node_center"
        center_node = self.add_node(center_node_id)
        
        # Create peripheral nodes and connect to center
        for i in range(self.config.num_nodes - 1):
            node_id = f"node_{i}"
            self.add_node(node_id)
            self.add_link(center_node_id, node_id, cost=1.0)
        
        self.logger.info(
            f"Star topology created: {len(self.nodes)} nodes, {len(self.links)} links, "
            f"center={center_node_id}"
        )
    
    def build_ring_topology(self) -> None:
        """
        Build a ring topology.
        
        In a ring topology, each node is connected to exactly two neighbors,
        forming a closed loop.
        """
        self.logger.info(f"Building ring topology with {self.config.num_nodes} nodes")
        
        # Create nodes
        node_ids = []
        for i in range(self.config.num_nodes):
            node_id = f"node_{i}"
            self.add_node(node_id)
            node_ids.append(node_id)
        
        # Create ring links
        for i in range(len(node_ids)):
            next_i = (i + 1) % len(node_ids)
            self.add_link(node_ids[i], node_ids[next_i], cost=1.0)
        
        self.logger.info(
            f"Ring topology created: {len(self.nodes)} nodes, {len(self.links)} links"
        )
    
    def build_topology(self) -> None:
        """
        Build topology based on configuration.
        
        Automatically builds the topology specified in the configuration.
        """
        topology_type = self.config.topology_type.lower()
        
        if topology_type == "mesh":
            self.build_mesh_topology()
        elif topology_type == "star":
            self.build_star_topology()
        elif topology_type == "ring":
            self.build_ring_topology()
        elif topology_type == "custom":
            self.logger.info("Custom topology - nodes and links must be added manually")
        else:
            raise ValueError(f"Unknown topology type: {topology_type}")
    
    def get_topology_info(self) -> Dict:
        """
        Get topology information.
        
        Returns:
            Dictionary containing topology details
        """
        return {
            'type': self.config.topology_type,
            'num_nodes': len(self.nodes),
            'num_links': len(self.links),
            'nodes': {
                node_id: {
                    'ip': node.get_ip_address(),
                    'mac': node.get_mac_address(),
                    'neighbors': list(self.adjacency.get(node_id, set()))
                }
                for node_id, node in self.nodes.items()
            },
            'links': [
                {
                    'node_a': link.node_a,
                    'node_b': link.node_b,
                    'cost': link.cost,
                    'capacity': link.capacity
                }
                for link in self.links
            ]
        }
    
    def print_topology(self) -> None:
        """Print topology information to console."""
        info = self.get_topology_info()
        
        print(f"\n{'='*60}")
        print(f"Network Topology: {info['type']}")
        print(f"{'='*60}")
        print(f"Nodes: {info['num_nodes']}, Links: {info['num_links']}")
        print(f"\nNodes:")
        for node_id, node_info in info['nodes'].items():
            neighbors_str = ', '.join(node_info['neighbors']) if node_info['neighbors'] else 'none'
            print(f"  {node_id}: IP={node_info['ip']}, Neighbors=[{neighbors_str}]")
        print(f"\nLinks:")
        for link in info['links']:
            print(f"  {link['node_a']} <-> {link['node_b']} (cost={link['cost']})")
        print(f"{'='*60}\n")
