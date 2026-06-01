"""
Application Layer implementation for the Adaptive Network Emulator.

This module implements socket handlers for TCP and UDP communication,
supporting both client-server and peer-to-peer modes. It provides
connection management and data transfer services.

Validates: Requirements 2.1, 2.4, 2.6
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Callable
from enum import Enum
import time
import uuid
from src.file_transfer_service import FileTransferService, MessageService


class ConnectionMode(Enum):
    """Connection mode types."""
    CLIENT_SERVER = "client_server"
    PEER_TO_PEER = "peer_to_peer"


class ConnectionState(Enum):
    """Connection state types."""
    CLOSED = "closed"
    LISTENING = "listening"
    CONNECTING = "connecting"
    ESTABLISHED = "established"
    CLOSING = "closing"


@dataclass
class Connection:
    """
    Represents a connection between two nodes.
    
    Attributes:
        connection_id: Unique connection identifier
        local_node: Local node identifier
        remote_node: Remote node identifier
        protocol: Protocol type (TCP or UDP)
        mode: Connection mode (client-server or peer-to-peer)
        state: Current connection state
        created_at: Connection creation timestamp
        closed_at: Connection closure timestamp (None if still open)
    """
    connection_id: str
    local_node: str
    remote_node: str
    protocol: str
    mode: ConnectionMode
    state: ConnectionState = ConnectionState.CLOSED
    created_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    
    def is_active(self) -> bool:
        """Check if connection is active."""
        return self.state == ConnectionState.ESTABLISHED
    
    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self.state == ConnectionState.CLOSED


@dataclass
class SocketHandler:
    """
    Base class for socket handlers.
    
    Provides common functionality for TCP and UDP socket handlers.
    
    Attributes:
        node_id: Node identifier for this socket handler
        connections: Dictionary of active connections
        send_callback: Callback function for sending data to transport layer
        receive_buffer: Buffer for received data
    """
    node_id: str
    connections: Dict[str, Connection] = field(default_factory=dict)
    send_callback: Optional[Callable] = None
    receive_buffer: Dict[str, bytes] = field(default_factory=dict)
    
    def _generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        return f"conn_{uuid.uuid4().hex[:8]}"
    
    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get connection by ID."""
        return self.connections.get(connection_id)
    
    def get_active_connections(self) -> Dict[str, Connection]:
        """Get all active connections."""
        return {
            conn_id: conn 
            for conn_id, conn in self.connections.items() 
            if conn.is_active()
        }
    
    def close_connection(self, connection_id: str) -> bool:
        """
        Close a connection and clean up resources.
        
        Args:
            connection_id: Connection identifier
        
        Returns:
            True if connection was closed successfully
        
        Validates: Requirement 2.6 (connection teardown)
        """
        conn = self.connections.get(connection_id)
        if not conn:
            return False
        
        # Update connection state
        conn.state = ConnectionState.CLOSING
        
        # Clean up receive buffer
        if connection_id in self.receive_buffer:
            del self.receive_buffer[connection_id]
        
        # Mark as closed
        conn.state = ConnectionState.CLOSED
        conn.closed_at = time.time()
        
        return True


@dataclass
class TCPSocketHandler(SocketHandler):
    """
    TCP socket handler for reliable communication.
    
    Implements connection establishment, data transfer, and teardown
    for TCP-like reliable communication.
    
    Validates: Requirements 2.1, 2.4, 2.6
    """
    
    def establish_connection(
        self, 
        remote_node: str, 
        mode: ConnectionMode = ConnectionMode.CLIENT_SERVER
    ) -> Optional[str]:
        """
        Establish a TCP connection to a remote node.
        
        Args:
            remote_node: Remote node identifier
            mode: Connection mode (client-server or peer-to-peer)
        
        Returns:
            Connection ID if successful, None otherwise
        
        Validates: Requirement 2.4 (client-server and peer-to-peer modes)
        """
        # Generate connection ID
        connection_id = self._generate_connection_id()
        
        # Create connection object
        conn = Connection(
            connection_id=connection_id,
            local_node=self.node_id,
            remote_node=remote_node,
            protocol="TCP",
            mode=mode,
            state=ConnectionState.CONNECTING
        )
        
        # Store connection
        self.connections[connection_id] = conn
        
        # Simulate connection establishment (3-way handshake)
        # In a real implementation, this would send SYN, receive SYN-ACK, send ACK
        conn.state = ConnectionState.ESTABLISHED
        
        # Initialize receive buffer
        self.receive_buffer[connection_id] = b""
        
        return connection_id
    
    def send_data(self, connection_id: str, data: bytes) -> bool:
        """
        Send data over a TCP connection.
        
        Args:
            connection_id: Connection identifier
            data: Data to send
        
        Returns:
            True if data was sent successfully
        
        Validates: Requirement 2.1 (reliable text message transmission)
        """
        conn = self.connections.get(connection_id)
        if not conn or not conn.is_active():
            return False
        
        # Use callback to send to transport layer
        if self.send_callback:
            self.send_callback(
                dest=conn.remote_node,
                data=data,
                protocol="TCP",
                connection_id=connection_id
            )
        
        return True
    
    def receive_data(self, connection_id: str) -> Optional[bytes]:
        """
        Receive data from a TCP connection.
        
        Args:
            connection_id: Connection identifier
        
        Returns:
            Received data, or None if no data available
        
        Validates: Requirement 2.1 (reliable text message transmission)
        """
        conn = self.connections.get(connection_id)
        if not conn or not conn.is_active():
            return None
        
        # Get data from receive buffer
        data = self.receive_buffer.get(connection_id, b"")
        if data:
            self.receive_buffer[connection_id] = b""
            return data
        
        return None
    
    def handle_incoming_data(self, connection_id: str, data: bytes) -> None:
        """
        Handle incoming data from transport layer.
        
        Args:
            connection_id: Connection identifier
            data: Received data
        """
        if connection_id in self.receive_buffer:
            self.receive_buffer[connection_id] += data


@dataclass
class UDPSocketHandler(SocketHandler):
    """
    UDP socket handler for unreliable communication.
    
    Implements connectionless data transfer without reliability guarantees.
    
    Validates: Requirements 2.1, 2.3
    """
    
    def send_datagram(self, remote_node: str, data: bytes) -> bool:
        """
        Send a UDP datagram to a remote node.
        
        Args:
            remote_node: Remote node identifier
            data: Data to send
        
        Returns:
            True if datagram was sent
        
        Validates: Requirement 2.3 (UDP file transfer without reliability)
        """
        # Create a pseudo-connection for tracking
        connection_id = self._generate_connection_id()
        
        conn = Connection(
            connection_id=connection_id,
            local_node=self.node_id,
            remote_node=remote_node,
            protocol="UDP",
            mode=ConnectionMode.PEER_TO_PEER,
            state=ConnectionState.ESTABLISHED
        )
        
        self.connections[connection_id] = conn
        
        # Use callback to send to transport layer
        if self.send_callback:
            self.send_callback(
                dest=remote_node,
                data=data,
                protocol="UDP",
                connection_id=connection_id
            )
        
        # UDP is connectionless, so we can close immediately
        conn.state = ConnectionState.CLOSED
        conn.closed_at = time.time()
        
        return True
    
    def receive_datagram(self) -> Optional[Tuple[str, bytes]]:
        """
        Receive a UDP datagram.
        
        Returns:
            Tuple of (source_node, data) or None if no data available
        
        Validates: Requirement 2.3 (UDP file transfer)
        """
        # Check all receive buffers for data
        for connection_id, data in self.receive_buffer.items():
            if data:
                conn = self.connections.get(connection_id)
                if conn:
                    self.receive_buffer[connection_id] = b""
                    return (conn.remote_node, data)
        
        return None
    
    def handle_incoming_datagram(self, source_node: str, data: bytes) -> None:
        """
        Handle incoming datagram from transport layer.
        
        Args:
            source_node: Source node identifier
            data: Received data
        """
        # Create a pseudo-connection for tracking
        connection_id = self._generate_connection_id()
        
        conn = Connection(
            connection_id=connection_id,
            local_node=self.node_id,
            remote_node=source_node,
            protocol="UDP",
            mode=ConnectionMode.PEER_TO_PEER,
            state=ConnectionState.ESTABLISHED
        )
        
        self.connections[connection_id] = conn
        self.receive_buffer[connection_id] = data


@dataclass
class ApplicationLayer:
    """
    Application Layer implementation.
    
    Provides high-level interface for network communication using TCP and UDP.
    Manages socket handlers and provides unified API for data transfer.
    
    Attributes:
        node_id: Node identifier
        tcp_handler: TCP socket handler
        udp_handler: UDP socket handler
        file_transfer_service: File transfer service
        message_service: Message service
        transport_send_callback: Callback to send data to transport layer
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    node_id: str
    tcp_handler: TCPSocketHandler = field(init=False)
    udp_handler: UDPSocketHandler = field(init=False)
    file_transfer_service: FileTransferService = field(init=False)
    message_service: MessageService = field(init=False)
    transport_send_callback: Optional[Callable] = None
    
    def __post_init__(self):
        """Initialize socket handlers and services."""
        self.tcp_handler = TCPSocketHandler(
            node_id=self.node_id,
            send_callback=self.transport_send_callback
        )
        self.udp_handler = UDPSocketHandler(
            node_id=self.node_id,
            send_callback=self.transport_send_callback
        )
        self.file_transfer_service = FileTransferService()
        self.message_service = MessageService()
    
    def send_message(
        self, 
        node_id: str, 
        message: str, 
        protocol: str = "TCP"
    ) -> bool:
        """
        Send a text message to a remote node.
        
        Args:
            node_id: Destination node identifier
            message: Text message to send
            protocol: Protocol to use (TCP or UDP)
        
        Returns:
            True if message was sent successfully
        
        Validates: Requirement 2.1 (text message transmission)
        """
        data = message.encode('utf-8')
        
        if protocol.upper() == "TCP":
            # Establish connection if needed
            connection_id = self.tcp_handler.establish_connection(
                node_id, 
                ConnectionMode.CLIENT_SERVER
            )
            if not connection_id:
                return False
            
            # Send data
            success = self.tcp_handler.send_data(connection_id, data)
            
            # Close connection
            self.tcp_handler.close_connection(connection_id)
            
            return success
        
        elif protocol.upper() == "UDP":
            return self.udp_handler.send_datagram(node_id, data)
        
        return False
    
    def receive_data(self) -> Optional[Tuple[str, bytes]]:
        """
        Receive data from any connection.
        
        Returns:
            Tuple of (source_node, data) or None if no data available
        """
        # Check TCP connections first
        for connection_id in list(self.tcp_handler.connections.keys()):
            data = self.tcp_handler.receive_data(connection_id)
            if data:
                conn = self.tcp_handler.get_connection(connection_id)
                if conn:
                    return (conn.remote_node, data)
        
        # Check UDP datagrams
        result = self.udp_handler.receive_datagram()
        if result:
            return result
        
        return None
    
    def establish_connection(
        self, 
        remote_node: str, 
        mode: ConnectionMode = ConnectionMode.CLIENT_SERVER
    ) -> Optional[str]:
        """
        Establish a TCP connection to a remote node.
        
        Args:
            remote_node: Remote node identifier
            mode: Connection mode (client-server or peer-to-peer)
        
        Returns:
            Connection ID if successful, None otherwise
        
        Validates: Requirements 2.4, 2.6 (connection establishment)
        """
        return self.tcp_handler.establish_connection(remote_node, mode)
    
    def close_connection(self, connection_id: str) -> bool:
        """
        Close a connection and clean up resources.
        
        Args:
            connection_id: Connection identifier
        
        Returns:
            True if connection was closed successfully
        
        Validates: Requirement 2.6 (connection teardown)
        """
        return self.tcp_handler.close_connection(connection_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.tcp_handler.get_active_connections())
    
    def cleanup_all_connections(self) -> None:
        """
        Clean up all connections and resources.
        
        Validates: Requirement 2.6 (connection lifecycle cleanup)
        """
        # Close all TCP connections
        for connection_id in list(self.tcp_handler.connections.keys()):
            self.tcp_handler.close_connection(connection_id)
        
        # Clear UDP receive buffers
        self.udp_handler.receive_buffer.clear()
        self.udp_handler.connections.clear()
    
    def send_file(
        self, 
        node_id: str, 
        file_path: str, 
        protocol: str = "TCP"
    ) -> Optional[str]:
        """
        Send a file to a remote node.
        
        Args:
            node_id: Destination node identifier
            file_path: Path to the file to send
            protocol: Protocol to use (TCP or UDP)
        
        Returns:
            File transfer ID if successful, None otherwise
        
        Validates: Requirements 2.2 (TCP file transfer), 2.3 (UDP file transfer)
        """
        # Create a send callback that uses the appropriate protocol
        def send_segment(dest, data, protocol, file_id):
            if protocol.upper() == "TCP":
                # Establish connection
                connection_id = self.tcp_handler.establish_connection(
                    dest, 
                    ConnectionMode.CLIENT_SERVER
                )
                if connection_id:
                    self.tcp_handler.send_data(connection_id, data)
                    self.tcp_handler.close_connection(connection_id)
            else:
                self.udp_handler.send_datagram(dest, data)
        
        # Send file using file transfer service
        return self.file_transfer_service.send_file(
            file_path=file_path,
            dest_node=node_id,
            protocol=protocol,
            send_callback=send_segment
        )
    
    def receive_file_segment(self, segment_data: bytes) -> bool:
        """
        Receive a file segment.
        
        Args:
            segment_data: Serialized segment data
        
        Returns:
            True if segment was received successfully
        """
        return self.file_transfer_service.receive_segment(segment_data)
    
    def get_received_file(self, file_id: str) -> Optional[bytes]:
        """
        Get a received file by ID.
        
        Args:
            file_id: File transfer identifier
        
        Returns:
            Complete file data, or None if transfer is incomplete
        
        Validates: Requirement 2.5 (file integrity verification)
        """
        return self.file_transfer_service.get_received_file(file_id)
    
    def verify_file_integrity(self, file_id: str, expected_checksum: str) -> bool:
        """
        Verify the integrity of a received file.
        
        Args:
            file_id: File transfer identifier
            expected_checksum: Expected file checksum
        
        Returns:
            True if file integrity is verified
        
        Validates: Requirement 2.5 (file integrity verification)
        """
        return self.file_transfer_service.verify_file_integrity(
            file_id, 
            expected_checksum
        )
