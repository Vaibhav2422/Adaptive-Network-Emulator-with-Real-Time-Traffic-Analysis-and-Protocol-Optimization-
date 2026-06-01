"""
Node implementation for the Adaptive Network Emulator.

This module implements the Node class that integrates all protocol layers
(Application, Transport, Network, Data Link, MAC, Physical) into a complete
protocol stack. It handles data flow between layers with proper encapsulation
and decapsulation.

Validates: Requirements 1.1, 1.2, 1.4, 1.5
"""

import logging
import time
from typing import Optional, Dict, Callable
from dataclasses import dataclass, field

from src.application_layer import ApplicationLayer, ConnectionMode
from src.transport_layer import SlidingWindow
from src.gbn_protocol import GBNProtocol
from src.sr_protocol import SRProtocol
from src.network_layer import NetworkLayer
from src.data_link_layer import DataLinkLayer, DataLinkLayerConfig
from src.mac_layer import MACLayer, MACLayerConfig
from src.physical_layer import PhysicalLayer, PhysicalLayerConfig
from src.data_models import Packet, Segment, Frame
from src.flow_controller import FlowController
from src.congestion_detector import CongestionDetector


@dataclass
class NodeConfig:
    """Configuration for a network node."""
    node_id: str
    ip_address: str
    mac_address: str
    subnet_mask: str = "255.255.255.0"
    
    # Transport layer config
    transport_protocol: str = "GBN"  # GBN or SR
    window_size: int = 8
    timeout_ms: int = 100
    
    # Physical layer config
    bit_rate_bps: float = 100_000_000  # 100 Mbps
    propagation_delay_ms: float = 10.0
    loss_rate: float = 0.0
    bit_error_rate: float = 0.0
    
    # MAC layer config
    slot_time_ms: float = 0.0512
    max_retries: int = 16
    
    # Data link layer config
    enable_hamming: bool = True
    
    # Random seed for reproducibility
    random_seed: Optional[int] = None


class Node:
    """
    Network node with complete protocol stack.
    
    A Node represents a simulated network device with all protocol layers
    from Application to Physical. It handles:
    - Data encapsulation as data flows down the stack
    - Data decapsulation as data flows up the stack
    - Layer-to-layer communication through well-defined interfaces
    - Protocol stack configuration and management
    
    Attributes:
        config: Node configuration
        application_layer: Application layer instance
        transport_layer: Transport layer protocol instance (GBN or SR)
        network_layer: Network layer instance
        data_link_layer: Data link layer instance
        mac_layer: MAC layer instance
        physical_layer: Physical layer instance
        flow_controller: Flow control instance
        congestion_detector: Congestion detection instance
    
    Validates: Requirements 1.1, 1.2, 1.4, 1.5
    """
    
    def __init__(self, config: NodeConfig, physical_layer: PhysicalLayer):
        """
        Initialize a network node with complete protocol stack.
        
        Args:
            config: Node configuration
            physical_layer: Shared physical layer instance
        """
        self.config = config
        self.logger = logging.getLogger(f"emulator.node.{config.node_id}")
        
        # Store physical layer (shared across nodes)
        self.physical_layer = physical_layer
        
        # Initialize MAC layer
        mac_config = MACLayerConfig(
            slot_time_ms=config.slot_time_ms,
            max_retries=config.max_retries,
            random_seed=config.random_seed
        )
        self.mac_layer = MACLayer(config.node_id, mac_config)
        
        # Initialize Data Link layer
        dl_config = DataLinkLayerConfig(
            enable_hamming=config.enable_hamming,
            random_seed=config.random_seed
        )
        self.data_link_layer = DataLinkLayer(config.node_id, dl_config)
        
        # Initialize Network layer
        self.network_layer = NetworkLayer(
            config.node_id,
            config.ip_address,
            config.subnet_mask
        )
        
        # Initialize Transport layer
        window = SlidingWindow(window_size=config.window_size)
        
        if config.transport_protocol.upper() == "GBN":
            self.transport_layer = GBNProtocol(
                window=window,
                timeout_ms=config.timeout_ms
            )
        elif config.transport_protocol.upper() == "SR":
            self.transport_layer = SRProtocol(
                window=window,
                timeout_ms=config.timeout_ms
            )
        else:
            raise ValueError(f"Unknown transport protocol: {config.transport_protocol}")
        
        # Initialize Flow Controller and Congestion Detector
        self.flow_controller = FlowController(
            sender_window_size=config.window_size,
            max_window_size=config.window_size * 2
        )
        self.congestion_detector = CongestionDetector(
            min_window_size=1,
            max_window_size=config.window_size * 2
        )
        
        # Initialize Application layer with transport callback
        self.application_layer = ApplicationLayer(node_id=config.node_id)
        self.application_layer.transport_send_callback = self._application_to_transport
        
        # Set up transport layer callbacks
        self.transport_layer.send_callback = self._transport_to_network
        
        # Receive buffers for each layer
        self.receive_buffers: Dict[str, list] = {
            'application': [],
            'transport': [],
            'network': [],
            'data_link': [],
            'mac': [],
            'physical': []
        }
        
        self.logger.info(
            f"Node initialized: IP={config.ip_address}, MAC={config.mac_address}, "
            f"Protocol={config.transport_protocol}"
        )
    
    # ========== Downward Data Flow (Encapsulation) ==========
    
    def _application_to_transport(self, dest: str, data: bytes, protocol: str, **kwargs) -> None:
        """
        Send data from Application layer to Transport layer.
        
        Encapsulation: Application data → Transport segment
        
        Args:
            dest: Destination node ID
            data: Application data
            protocol: Protocol type (TCP/UDP)
            **kwargs: Additional parameters (connection_id, etc.)
        """
        self.logger.debug(
            f"Application → Transport: {len(data)} bytes to {dest} via {protocol}"
        )
        
        # Create segment and send through transport layer
        seq_num = self.transport_layer.send_segment(data, dest)
        
        if seq_num is not None:
            self.logger.debug(f"Transport assigned sequence number: {seq_num}")
    
    def _transport_to_network(self, dest: str, segment: Segment) -> None:
        """
        Send segment from Transport layer to Network layer.
        
        Encapsulation: Transport segment → Network packet
        
        Args:
            dest: Destination IP address
            segment: Transport layer segment
        """
        self.logger.debug(
            f"Transport → Network: seq={segment.sequence_num} to {dest}"
        )
        
        # Create packet with segment as payload
        packet = Packet(
            packet_id=f"pkt_{self.config.node_id}_{segment.sequence_num}_{time.time()}",
            timestamp=time.time(),
            source_ip=self.config.ip_address,
            dest_ip=dest,
            protocol=self.config.transport_protocol,
            payload=self._serialize_segment(segment),
            headers={}
        )
        
        # Add to network layer headers
        packet.headers['network'] = self._create_network_header(packet)
        
        # Send to data link layer
        self._network_to_data_link(packet)
    
    def _network_to_data_link(self, packet: Packet) -> None:
        """
        Send packet from Network layer to Data Link layer.
        
        Encapsulation: Network packet → Data link frame
        
        Args:
            packet: Network layer packet
        """
        self.logger.debug(
            f"Network → Data Link: packet {packet.packet_id} to {packet.dest_ip}"
        )
        
        # Determine destination MAC address (simplified - in real network would use ARP)
        dest_mac = self._resolve_mac_address(packet.dest_ip)
        
        # Build frame with packet as payload
        frame = self.data_link_layer.build_frame(
            source_mac=self.config.mac_address,
            dest_mac=dest_mac,
            payload=self._serialize_packet(packet)
        )
        
        # Send to MAC layer
        self._data_link_to_mac(frame, dest_mac)
    
    def _data_link_to_mac(self, frame: Frame, dest_mac: str) -> None:
        """
        Send frame from Data Link layer to MAC layer.
        
        Encapsulation: Data link frame → MAC transmission
        
        Args:
            frame: Data link layer frame
            dest_mac: Destination MAC address
        """
        self.logger.debug(
            f"Data Link → MAC: frame to {dest_mac}"
        )
        
        # Serialize frame for transmission
        frame_data = self._serialize_frame(frame)
        
        # Request transmission through MAC layer
        frame_id = f"frame_{self.config.node_id}_{time.time()}"
        success, backoff_slots, backoff_time = self.mac_layer.request_transmission(
            frame_id=frame_id,
            frame_data=frame_data,
            timestamp=time.time(),
            callback=lambda data: self._mac_to_physical(data, dest_mac)
        )
        
        if success:
            self.logger.debug("MAC layer: transmission successful")
        elif backoff_slots is not None:
            self.logger.debug(
                f"MAC layer: collision, backing off {backoff_slots} slots "
                f"({backoff_time*1000:.3f} ms)"
            )
        else:
            self.logger.debug("MAC layer: channel busy, waiting")
    
    def _mac_to_physical(self, frame_data: bytes, dest_mac: str) -> None:
        """
        Send frame from MAC layer to Physical layer.
        
        Encapsulation: MAC frame → Physical transmission
        
        Args:
            frame_data: Serialized frame data
            dest_mac: Destination MAC address
        """
        self.logger.debug(
            f"MAC → Physical: {len(frame_data)} bytes to {dest_mac}"
        )
        
        # Transmit through physical layer
        success, transmitted_data, delay = self.physical_layer.transmit(
            data=frame_data,
            dest=dest_mac,
            callback=None  # Callback handled by receiving node
        )
        
        if success:
            self.logger.debug(
                f"Physical transmission successful: delay={delay*1000:.3f} ms"
            )
            # Mark MAC transmission as complete
            self.mac_layer.complete_transmission()
        else:
            self.logger.warning("Physical transmission failed: packet lost")
            self.mac_layer.complete_transmission()
    
    # ========== Upward Data Flow (Decapsulation) ==========
    
    def receive_from_physical(self, frame_data: bytes, source_mac: str) -> None:
        """
        Receive data from Physical layer.
        
        Decapsulation: Physical transmission → MAC frame
        
        Args:
            frame_data: Received frame data
            source_mac: Source MAC address
        """
        self.logger.debug(
            f"Physical → MAC: {len(frame_data)} bytes from {source_mac}"
        )
        
        # Deserialize frame
        frame = self._deserialize_frame(frame_data)
        
        # Check if frame is for this node
        if frame.dest_mac != self.config.mac_address and frame.dest_mac != "FF:FF:FF:FF:FF:FF":
            self.logger.debug(f"Frame not for this node (dest={frame.dest_mac}), ignoring")
            return
        
        # Pass to data link layer
        self._physical_to_data_link(frame)
    
    def _physical_to_data_link(self, frame: Frame) -> None:
        """
        Process frame at Data Link layer.
        
        Decapsulation: Data link frame → Network packet
        
        Args:
            frame: Received frame
        """
        self.logger.debug(
            f"MAC → Data Link: frame from {frame.source_mac}"
        )
        
        # Validate frame (CRC check, error correction)
        valid, payload = self.data_link_layer.validate_frame(frame)
        
        if not valid:
            self.logger.warning("Frame validation failed, discarding")
            return
        
        if payload is None:
            self.logger.warning("Frame payload is None after validation, discarding")
            return
        
        # Deserialize packet from payload
        packet = self._deserialize_packet(payload)
        
        # Pass to network layer
        self._data_link_to_network(packet)
    
    def _data_link_to_network(self, packet: Packet) -> None:
        """
        Process packet at Network layer.
        
        Decapsulation: Network packet → Transport segment
        
        Args:
            packet: Received packet
        """
        self.logger.debug(
            f"Data Link → Network: packet {packet.packet_id} from {packet.source_ip}"
        )
        
        # Check if packet is for this node
        if packet.dest_ip != self.config.ip_address:
            # Forward packet if we're a router
            next_hop = self.network_layer.forward_packet(packet)
            if next_hop:
                self.logger.info(f"Forwarding packet {packet.packet_id} to {next_hop}")
                # In a full implementation, would re-encapsulate and forward
            else:
                self.logger.warning(f"Cannot forward packet {packet.packet_id}, no route")
            return
        
        # Packet is for us - pass to transport layer
        self._network_to_transport(packet)
    
    def _network_to_transport(self, packet: Packet) -> None:
        """
        Process packet at Transport layer.
        
        Decapsulation: Network packet → Transport segment → Application data
        
        Args:
            packet: Received packet
        """
        self.logger.debug(
            f"Network → Transport: packet {packet.packet_id}"
        )
        
        # Deserialize segment from packet payload
        segment = self._deserialize_segment(packet.payload)
        
        # Process segment at transport layer
        self.transport_layer.receive_segment(segment)
        
        # If segment contains data, pass to application layer
        if segment.data:
            self._transport_to_application(segment.data, packet.source_ip)
    
    def _transport_to_application(self, data: bytes, source_ip: str) -> None:
        """
        Deliver data to Application layer.
        
        Decapsulation: Transport data → Application data
        
        Args:
            data: Application data
            source_ip: Source IP address
        """
        self.logger.debug(
            f"Transport → Application: {len(data)} bytes from {source_ip}"
        )
        
        # Store in application receive buffer
        self.receive_buffers['application'].append((source_ip, data))
        
        # Notify application layer
        # In a full implementation, would trigger application callbacks
    
    # ========== Serialization/Deserialization Helpers ==========
    
    def _serialize_segment(self, segment: Segment) -> bytes:
        """Serialize a transport segment to bytes."""
        import pickle
        return pickle.dumps(segment)
    
    def _deserialize_segment(self, data: bytes) -> Segment:
        """Deserialize bytes to a transport segment."""
        import pickle
        return pickle.loads(data)
    
    def _serialize_packet(self, packet: Packet) -> bytes:
        """Serialize a network packet to bytes."""
        import pickle
        return pickle.dumps(packet)
    
    def _deserialize_packet(self, data: bytes) -> Packet:
        """Deserialize bytes to a network packet."""
        import pickle
        return pickle.loads(data)
    
    def _serialize_frame(self, frame: Frame) -> bytes:
        """Serialize a data link frame to bytes."""
        import pickle
        return pickle.dumps(frame)
    
    def _deserialize_frame(self, data: bytes) -> Frame:
        """Deserialize bytes to a data link frame."""
        import pickle
        return pickle.loads(data)
    
    def _create_network_header(self, packet: Packet) -> bytes:
        """Create network layer header."""
        # Simplified header with TTL, protocol, etc.
        header = {
            'ttl': 64,
            'protocol': packet.protocol,
            'source_ip': packet.source_ip,
            'dest_ip': packet.dest_ip
        }
        import pickle
        return pickle.dumps(header)
    
    def _resolve_mac_address(self, ip_address: str) -> str:
        """
        Resolve IP address to MAC address.
        
        Simplified implementation - in real network would use ARP.
        For simulation, we use a simple mapping.
        """
        # For simulation, derive MAC from IP
        # In real implementation, would maintain ARP table
        octets = ip_address.split('.')
        if len(octets) == 4:
            return f"00:00:00:{octets[1]}:{octets[2]}:{octets[3]}"
        return "00:00:00:00:00:00"
    
    # ========== Public Interface ==========
    
    def send_message(self, dest_ip: str, message: str, protocol: str = "TCP") -> bool:
        """
        Send a text message to a destination node.
        
        This is the top-level interface for sending data. The message will
        flow down through all layers with proper encapsulation at each layer.
        
        Args:
            dest_ip: Destination IP address
            message: Text message to send
            protocol: Protocol to use (TCP or UDP)
        
        Returns:
            True if message was sent successfully
        
        Validates: Requirement 1.1 (layered architecture)
        """
        self.logger.info(f"Sending message to {dest_ip}: '{message[:50]}...'")
        return self.application_layer.send_message(dest_ip, message, protocol)
    
    def receive_message(self) -> Optional[tuple[str, str]]:
        """
        Receive a message from the application layer.
        
        Returns:
            Tuple of (source_ip, message) or None if no messages available
        """
        if self.receive_buffers['application']:
            source_ip, data = self.receive_buffers['application'].pop(0)
            message = data.decode('utf-8', errors='replace')
            self.logger.info(f"Received message from {source_ip}: '{message[:50]}...'")
            return source_ip, message
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get statistics from all layers.
        
        Returns:
            Dictionary containing statistics from each layer
        """
        return {
            'node_id': self.config.node_id,
            'ip_address': self.config.ip_address,
            'mac_address': self.config.mac_address,
            'data_link': self.data_link_layer.get_statistics(),
            'mac': self.mac_layer.get_statistics(),
            'transport': self.transport_layer.get_state() if hasattr(self.transport_layer, 'get_state') else {},
            'routing_table': self.network_layer.get_routing_table()
        }
    
    def get_node_id(self) -> str:
        """Get node identifier."""
        return self.config.node_id
    
    def get_ip_address(self) -> str:
        """Get IP address."""
        return self.config.ip_address
    
    def get_mac_address(self) -> str:
        """Get MAC address."""
        return self.config.mac_address
