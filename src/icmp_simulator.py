"""
ICMP-like Diagnostics Simulator

This module implements logical ICMP-like behavior for network diagnostics,
including echo request/reply (ping), destination unreachable messages,
and TTL expiration handling.

Validates: Requirements 4.7
"""

import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class ICMPType(Enum):
    """ICMP message types."""
    ECHO_REQUEST = 8
    ECHO_REPLY = 0
    DESTINATION_UNREACHABLE = 3
    TIME_EXCEEDED = 11


class ICMPCode(Enum):
    """ICMP message codes."""
    # For DESTINATION_UNREACHABLE
    NET_UNREACHABLE = 0
    HOST_UNREACHABLE = 1
    PROTOCOL_UNREACHABLE = 2
    PORT_UNREACHABLE = 3
    
    # For TIME_EXCEEDED
    TTL_EXCEEDED = 0
    FRAGMENT_REASSEMBLY_TIME_EXCEEDED = 1
    
    # For ECHO_REQUEST/REPLY
    NO_CODE = 0


@dataclass
class ICMPMessage:
    """
    Represents an ICMP message.
    
    Attributes:
        icmp_type: Type of ICMP message
        code: ICMP code (subtype)
        source_ip: Source IP address
        dest_ip: Destination IP address
        identifier: Identifier for matching requests/replies
        sequence_num: Sequence number for ordering
        data: Optional payload data
        timestamp: Time when message was created
    """
    icmp_type: ICMPType
    code: ICMPCode
    source_ip: str
    dest_ip: str
    identifier: int = 0
    sequence_num: int = 0
    data: bytes = b''
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Serialize ICMP message to dictionary."""
        return {
            'icmp_type': self.icmp_type.name,
            'code': self.code.name,
            'source_ip': self.source_ip,
            'dest_ip': self.dest_ip,
            'identifier': self.identifier,
            'sequence_num': self.sequence_num,
            'data': self.data.hex(),
            'timestamp': self.timestamp
        }


@dataclass
class PingResult:
    """
    Result of a ping operation.
    
    Attributes:
        destination: Destination IP address
        success: Whether ping was successful
        round_trip_time: Round-trip time in milliseconds
        ttl: Time-to-live value
        sequence_num: Sequence number of the ping
        error_message: Error message if ping failed
    """
    destination: str
    success: bool
    round_trip_time: Optional[float] = None
    ttl: Optional[int] = None
    sequence_num: int = 0
    error_message: Optional[str] = None


class ICMPSimulator:
    """
    Simulates ICMP-like diagnostic functionality.
    
    This class provides ping-like echo request/reply, destination unreachable
    messages, and TTL expiration handling for network diagnostics.
    
    Attributes:
        node_id: Identifier for this node
        node_ip: IP address of this node
        default_ttl: Default TTL value for outgoing packets
        ping_identifier: Identifier for ping sessions
        ping_sequence: Sequence number for ping packets
        pending_pings: Dictionary of pending ping requests
    """
    
    def __init__(self, node_id: str, node_ip: str, default_ttl: int = 64):
        """
        Initialize ICMP simulator.
        
        Args:
            node_id: Identifier for this node
            node_ip: IP address of this node
            default_ttl: Default TTL value (default: 64)
        """
        self.node_id = node_id
        self.node_ip = node_ip
        self.default_ttl = default_ttl
        
        # Ping state
        self.ping_identifier = hash(node_id) % 65536  # 16-bit identifier
        self.ping_sequence = 0
        self.pending_pings: Dict[int, Dict] = {}
        
        logger.info(
            f"ICMPSimulator initialized for node {node_id} "
            f"(IP: {node_ip}, TTL: {default_ttl})"
        )
    
    def create_echo_request(
        self,
        dest_ip: str,
        data: bytes = b'',
        ttl: Optional[int] = None
    ) -> tuple[ICMPMessage, int]:
        """
        Create an ICMP echo request (ping).
        
        Args:
            dest_ip: Destination IP address
            data: Optional payload data
            ttl: Optional TTL value (uses default if not specified)
            
        Returns:
            Tuple of (ICMPMessage, TTL value)
        """
        self.ping_sequence += 1
        sequence_num = self.ping_sequence
        
        message = ICMPMessage(
            icmp_type=ICMPType.ECHO_REQUEST,
            code=ICMPCode.NO_CODE,
            source_ip=self.node_ip,
            dest_ip=dest_ip,
            identifier=self.ping_identifier,
            sequence_num=sequence_num,
            data=data,
            timestamp=time.time()
        )
        
        # Store pending ping
        self.pending_pings[sequence_num] = {
            'dest_ip': dest_ip,
            'send_time': message.timestamp,
            'ttl': ttl or self.default_ttl
        }
        
        logger.debug(
            f"Node {self.node_id}: Created echo request to {dest_ip} "
            f"(seq={sequence_num})"
        )
        
        return message, ttl or self.default_ttl
    
    def create_echo_reply(self, request: ICMPMessage) -> ICMPMessage:
        """
        Create an ICMP echo reply in response to a request.
        
        Args:
            request: The echo request message
            
        Returns:
            ICMPMessage echo reply
        """
        reply = ICMPMessage(
            icmp_type=ICMPType.ECHO_REPLY,
            code=ICMPCode.NO_CODE,
            source_ip=self.node_ip,
            dest_ip=request.source_ip,
            identifier=request.identifier,
            sequence_num=request.sequence_num,
            data=request.data,
            timestamp=time.time()
        )
        
        logger.debug(
            f"Node {self.node_id}: Created echo reply to {request.source_ip} "
            f"(seq={request.sequence_num})"
        )
        
        return reply
    
    def handle_echo_request(self, request: ICMPMessage) -> ICMPMessage:
        """
        Handle an incoming echo request and generate a reply.
        
        Args:
            request: The echo request message
            
        Returns:
            ICMPMessage echo reply
        """
        logger.info(
            f"Node {self.node_id}: Received echo request from {request.source_ip} "
            f"(seq={request.sequence_num})"
        )
        
        return self.create_echo_reply(request)
    
    def handle_echo_reply(self, reply: ICMPMessage) -> Optional[PingResult]:
        """
        Handle an incoming echo reply and compute ping result.
        
        Args:
            reply: The echo reply message
            
        Returns:
            PingResult if this reply matches a pending ping, None otherwise
        """
        sequence_num = reply.sequence_num
        
        if sequence_num not in self.pending_pings:
            logger.warning(
                f"Node {self.node_id}: Received unexpected echo reply "
                f"(seq={sequence_num})"
            )
            return None
        
        # Get pending ping info
        ping_info = self.pending_pings.pop(sequence_num)
        
        # Calculate round-trip time
        rtt = (time.time() - ping_info['send_time']) * 1000  # Convert to ms
        
        result = PingResult(
            destination=ping_info['dest_ip'],
            success=True,
            round_trip_time=rtt,
            ttl=ping_info['ttl'],
            sequence_num=sequence_num
        )
        
        logger.info(
            f"Node {self.node_id}: Ping to {result.destination} successful "
            f"(seq={sequence_num}, rtt={rtt:.2f}ms)"
        )
        
        return result
    
    def create_destination_unreachable(
        self,
        dest_ip: str,
        code: ICMPCode = ICMPCode.HOST_UNREACHABLE,
        original_packet_data: bytes = b''
    ) -> ICMPMessage:
        """
        Create a destination unreachable message.
        
        Args:
            dest_ip: Destination that is unreachable
            code: Specific unreachable code
            original_packet_data: Data from the original packet
            
        Returns:
            ICMPMessage destination unreachable
        """
        message = ICMPMessage(
            icmp_type=ICMPType.DESTINATION_UNREACHABLE,
            code=code,
            source_ip=self.node_ip,
            dest_ip=dest_ip,
            data=original_packet_data[:64],  # Include first 64 bytes of original
            timestamp=time.time()
        )
        
        logger.info(
            f"Node {self.node_id}: Created destination unreachable for {dest_ip} "
            f"(code={code.name})"
        )
        
        return message
    
    def handle_destination_unreachable(
        self,
        message: ICMPMessage
    ) -> Optional[PingResult]:
        """
        Handle a destination unreachable message.
        
        Args:
            message: The destination unreachable message
            
        Returns:
            PingResult with error information if related to a pending ping
        """
        logger.warning(
            f"Node {self.node_id}: Received destination unreachable from "
            f"{message.source_ip} (code={message.code.name})"
        )
        
        # Try to match with pending pings
        # In a real implementation, we'd parse the original packet data
        # For simplicity, we'll just mark the most recent ping as failed
        if self.pending_pings:
            sequence_num = max(self.pending_pings.keys())
            ping_info = self.pending_pings.pop(sequence_num)
            
            result = PingResult(
                destination=ping_info['dest_ip'],
                success=False,
                sequence_num=sequence_num,
                error_message=f"Destination unreachable: {message.code.name}"
            )
            
            return result
        
        return None
    
    def create_time_exceeded(
        self,
        dest_ip: str,
        code: ICMPCode = ICMPCode.TTL_EXCEEDED,
        original_packet_data: bytes = b''
    ) -> ICMPMessage:
        """
        Create a time exceeded message (TTL expired).
        
        Args:
            dest_ip: Destination of the original packet
            code: Specific time exceeded code
            original_packet_data: Data from the original packet
            
        Returns:
            ICMPMessage time exceeded
        """
        message = ICMPMessage(
            icmp_type=ICMPType.TIME_EXCEEDED,
            code=code,
            source_ip=self.node_ip,
            dest_ip=dest_ip,
            data=original_packet_data[:64],
            timestamp=time.time()
        )
        
        logger.info(
            f"Node {self.node_id}: Created time exceeded for {dest_ip} "
            f"(code={code.name})"
        )
        
        return message
    
    def handle_time_exceeded(self, message: ICMPMessage) -> Optional[PingResult]:
        """
        Handle a time exceeded message.
        
        Args:
            message: The time exceeded message
            
        Returns:
            PingResult with error information if related to a pending ping
        """
        logger.warning(
            f"Node {self.node_id}: Received time exceeded from "
            f"{message.source_ip} (code={message.code.name})"
        )
        
        # Try to match with pending pings
        if self.pending_pings:
            sequence_num = max(self.pending_pings.keys())
            ping_info = self.pending_pings.pop(sequence_num)
            
            result = PingResult(
                destination=ping_info['dest_ip'],
                success=False,
                sequence_num=sequence_num,
                error_message=f"Time exceeded: {message.code.name}"
            )
            
            return result
        
        return None
    
    def check_ttl(self, ttl: int, dest_ip: str) -> tuple[bool, Optional[ICMPMessage]]:
        """
        Check if TTL has expired and generate time exceeded message if needed.
        
        Args:
            ttl: Current TTL value
            dest_ip: Destination IP address
            
        Returns:
            Tuple of (should_forward, icmp_message)
            - should_forward: True if packet should be forwarded, False if dropped
            - icmp_message: Time exceeded message if TTL expired, None otherwise
        """
        if ttl <= 0:
            logger.warning(
                f"Node {self.node_id}: TTL expired for packet to {dest_ip}"
            )
            
            message = self.create_time_exceeded(
                dest_ip,
                code=ICMPCode.TTL_EXCEEDED
            )
            
            return False, message
        
        return True, None
    
    def ping(
        self,
        dest_ip: str,
        count: int = 4,
        timeout: float = 5.0,
        data_size: int = 32
    ) -> List[PingResult]:
        """
        Perform a ping operation (simplified simulation).
        
        Note: This is a simplified version that creates ping requests.
        In a full implementation, this would integrate with the network layer
        to actually send packets and wait for replies.
        
        Args:
            dest_ip: Destination IP address
            count: Number of ping packets to send
            timeout: Timeout in seconds for each ping
            data_size: Size of ping data in bytes
            
        Returns:
            List of PingResult objects
        """
        results = []
        data = b'x' * data_size
        
        logger.info(
            f"Node {self.node_id}: Starting ping to {dest_ip} "
            f"(count={count}, timeout={timeout}s)"
        )
        
        for i in range(count):
            # Create echo request
            request, ttl = self.create_echo_request(dest_ip, data)
            
            # In a real implementation, we would:
            # 1. Send the request through the network layer
            # 2. Wait for a reply or timeout
            # 3. Process the reply
            
            # For now, we just create the request and log it
            logger.debug(
                f"Node {self.node_id}: Ping {i+1}/{count} to {dest_ip} "
                f"(seq={request.sequence_num})"
            )
        
        return results
    
    def get_pending_pings(self) -> Dict[int, Dict]:
        """
        Get dictionary of pending ping requests.
        
        Returns:
            Dictionary mapping sequence numbers to ping info
        """
        return self.pending_pings.copy()
    
    def clear_pending_pings(self) -> None:
        """Clear all pending ping requests."""
        count = len(self.pending_pings)
        self.pending_pings.clear()
        logger.debug(f"Node {self.node_id}: Cleared {count} pending pings")
    
    def timeout_pending_pings(self, timeout: float = 5.0) -> List[PingResult]:
        """
        Check for and timeout pending pings that have exceeded the timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            List of PingResult objects for timed out pings
        """
        current_time = time.time()
        timed_out = []
        results = []
        
        for sequence_num, ping_info in self.pending_pings.items():
            age = current_time - ping_info['send_time']
            if age > timeout:
                timed_out.append(sequence_num)
                
                result = PingResult(
                    destination=ping_info['dest_ip'],
                    success=False,
                    sequence_num=sequence_num,
                    error_message=f"Request timed out ({age:.1f}s)"
                )
                results.append(result)
        
        # Remove timed out pings
        for sequence_num in timed_out:
            del self.pending_pings[sequence_num]
            logger.warning(
                f"Node {self.node_id}: Ping seq={sequence_num} timed out"
            )
        
        return results
