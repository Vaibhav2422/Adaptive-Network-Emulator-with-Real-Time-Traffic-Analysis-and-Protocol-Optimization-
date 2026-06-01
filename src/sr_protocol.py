"""
Selective Repeat (SR) Protocol implementation for the Adaptive Network Emulator.

This module implements the Selective Repeat reliable data transfer protocol with
sliding window flow control. SR retransmits only the specific lost packets,
making it more efficient than Go-Back-N.

Validates: Requirements 3.2, 3.4
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable
import time
from src.transport_layer import TransportProtocol, SlidingWindow
from src.data_models import Segment
from src.flow_controller import FlowController
from src.congestion_detector import CongestionDetector


@dataclass
class SRProtocol(TransportProtocol):
    """
    Selective Repeat protocol implementation.
    
    SR uses a sliding window for flow control and implements selective
    acknowledgments. When a packet is lost, only that specific packet
    is retransmitted, not subsequent packets.
    
    The receiver buffers out-of-order packets and delivers them in order
    once gaps are filled.
    
    Attributes:
        window: SlidingWindow instance for flow control
        timeout_ms: Retransmission timeout in milliseconds
        sent_segments: Dict mapping sequence numbers to (segment, timestamp)
        send_callback: Optional callback function to actually send segments
        receiver_buffer: Dict mapping sequence numbers to received segments (receiver side)
        expected_seq: Next expected sequence number for in-order delivery (receiver side)
        receiver_window_size: Size of receiver window for buffering
        flow_controller: FlowController instance for managing window sizes
        congestion_detector: CongestionDetector instance for congestion control
        
    Validates: Requirements 3.2 (SR protocol), 3.4 (selective retransmission), 3.5 (flow control), 3.6 (congestion control)
    """
    window: SlidingWindow
    timeout_ms: int
    sent_segments: Dict[int, tuple[Segment, float]] = field(default_factory=dict)
    send_callback: Optional[Callable[[Segment, str], None]] = None
    receiver_buffer: Dict[int, Segment] = field(default_factory=dict)
    expected_seq: int = 0  # Receiver side: next expected sequence number for delivery
    receiver_window_size: int = field(default=None)
    flow_controller: Optional[FlowController] = None
    congestion_detector: Optional[CongestionDetector] = None
    
    def __post_init__(self):
        """Initialize receiver window size, flow controller, and congestion detector if not set."""
        if self.receiver_window_size is None:
            self.receiver_window_size = self.window.window_size
        
        if self.flow_controller is None:
            self.flow_controller = FlowController(
                sender_window_size=self.window.window_size,
                max_window_size=self.window.window_size * 2
            )
        
        if self.congestion_detector is None:
            self.congestion_detector = CongestionDetector(
                min_window_size=1,
                max_window_size=self.window.window_size * 2
            )
    
    def send_segment(self, data: bytes, dest: str) -> Optional[int]:
        """
        Send a data segment using SR protocol.
        
        Args:
            data: Data to send
            dest: Destination identifier
        
        Returns:
            Sequence number assigned to the segment, or None if window is full
            
        Validates: Requirement 3.2 (SR send logic with individual packet tracking), 3.5 (flow control)
        """
        # Check both sliding window and flow control constraints
        if not self.window.can_send():
            return None
        
        if not self.flow_controller.can_send(self.window.get_unacked_count()):
            return None
        
        # Get next sequence number from window
        seq_num = self.window.get_next_sequence_number()
        
        # Get effective window size from flow controller
        effective_window = self.flow_controller.get_effective_window_size()
        
        # Create segment with advertised receiver window
        segment = Segment(
            sequence_num=seq_num,
            ack_num=0,  # Not used in SR sender
            window_size=effective_window,
            flags={'DATA'},
            data=data,
            checksum=self._compute_checksum(data)
        )
        
        # Store segment with timestamp for timeout detection
        timestamp = time.time()
        self.sent_segments[seq_num] = (segment, timestamp)
        
        # Record packet sent for congestion detection
        self.congestion_detector.record_packet_sent()
        
        # Send segment if callback is provided
        if self.send_callback:
            self.send_callback(segment, dest)
        
        return seq_num
    
    def handle_acknowledgment(self, ack_num: int, advertised_window: Optional[int] = None) -> None:
        """
        Handle a selective acknowledgment in SR.
        
        In SR, an ACK for sequence number N acknowledges only packet N,
        not previous packets. Each packet is acknowledged individually.
        
        Args:
            ack_num: Sequence number being acknowledged (selective)
            advertised_window: Optional receiver window size advertisement
            
        Validates: Requirement 3.2 (SR selective acknowledgment handling), 3.5 (flow control), 3.6 (congestion control)
        """
        # Update flow control if receiver advertises window
        if advertised_window is not None:
            self.flow_controller.adjust_sender_window(advertised_window)
        
        # Record RTT for acknowledged packet
        if ack_num in self.sent_segments:
            _, send_time = self.sent_segments[ack_num]
            current_time = time.time()
            rtt_ms = (current_time - send_time) * 1000  # Convert to ms
            self.congestion_detector.record_rtt_sample(rtt_ms)
        
        # SR uses selective ACKs: ACK N means only packet N is acknowledged
        if ack_num in self.window.unacked_packets:
            self.window.acknowledge(ack_num)
            # Remove from sent_segments
            if ack_num in self.sent_segments:
                del self.sent_segments[ack_num]
        
        # Adapt window size based on congestion detection
        current_window = self.flow_controller.sender_window_size
        new_window = self.congestion_detector.adapt_window_size(current_window)
        if new_window != current_window:
            self.flow_controller.set_sender_window(new_window)
    
    def handle_timeout(self, seq_num: int) -> List[Segment]:
        """
        Handle a timeout for a specific sequence number in SR.
        
        In SR, when a timeout occurs for packet N, only packet N is
        retransmitted. Other packets are not affected.
        
        Args:
            seq_num: Sequence number that timed out
            
        Returns:
            List containing only the timed-out segment (single element)
            
        Validates: Requirement 3.4 (SR selective retransmission of lost packets only), 3.6 (congestion detection)
        """
        # Record packet loss for congestion detection
        self.congestion_detector.record_packet_loss()
        
        segments_to_retransmit = []
        
        # Only retransmit the specific packet that timed out
        if seq_num in self.sent_segments:
            segment, _ = self.sent_segments[seq_num]
            # Update timestamp
            self.sent_segments[seq_num] = (segment, time.time())
            segments_to_retransmit.append(segment)
        
        return segments_to_retransmit
    
    def check_timeouts(self) -> List[tuple[int, List[Segment]]]:
        """
        Check for timed-out packets and return segments to retransmit.
        
        In SR, each packet has its own timer, so multiple packets can
        timeout independently. Uses adaptive timeout based on RTT measurements.
        
        Returns:
            List of (seq_num, segments_to_retransmit) tuples
            
        Validates: Requirement 3.6 (timeout adjustment based on RTT)
        """
        current_time = time.time()
        
        # Use adaptive timeout based on RTT
        adaptive_timeout_ms = self.congestion_detector.calculate_timeout(self.timeout_ms)
        timeout_threshold = adaptive_timeout_ms / 1000.0  # Convert to seconds
        
        timed_out = []
        
        for seq_num, (segment, timestamp) in list(self.sent_segments.items()):
            if current_time - timestamp > timeout_threshold:
                # This packet has timed out
                segments = self.handle_timeout(seq_num)
                if segments:
                    timed_out.append((seq_num, segments))
        
        return timed_out
    
    def receive_segment(self, segment: Segment) -> Optional[tuple[int, int]]:
        """
        Receive a segment on the receiver side (SR receiver logic).
        
        SR receiver accepts out-of-order packets and buffers them.
        It sends selective ACKs for each correctly received packet.
        Packets are delivered in order once gaps are filled.
        
        Args:
            segment: Received segment
            
        Returns:
            Tuple of (ACK number, advertised receiver window), or None if segment is rejected
            
        Validates: Requirement 3.2 (SR receiver buffering for out-of-order packets), 3.5 (receiver window advertisement)
        """
        # Verify checksum
        if not self._verify_checksum(segment):
            # Discard corrupted segment
            return None
        
        seq_num = segment.sequence_num
        
        # Check if packet is within receiver window
        if not self._is_in_receiver_window(seq_num):
            # Outside receiver window, discard
            return None
        
        # Buffer the packet (even if out of order)
        self.receiver_buffer[seq_num] = segment
        
        # Deliver in-order packets to upper layer
        while self.expected_seq in self.receiver_buffer:
            # Packet is ready for delivery
            delivered_segment = self.receiver_buffer.pop(self.expected_seq)
            self.expected_seq = (self.expected_seq + 1) % self.window.max_seq_num
        
        # Calculate available receiver buffer space
        available_buffer = self.receiver_window_size - len(self.receiver_buffer)
        advertised_window = self.flow_controller.advertise_receiver_window(available_buffer)
        
        # Send selective ACK for this specific packet with advertised window
        return (seq_num, advertised_window)
    
    def _is_in_receiver_window(self, seq_num: int) -> bool:
        """
        Check if a sequence number is within the receiver window.
        
        Args:
            seq_num: Sequence number to check
        
        Returns:
            True if sequence number is in the receiver window
        """
        if not self.window.validate_sequence_number(seq_num):
            return False
        
        # Receiver window: [expected_seq, expected_seq + receiver_window_size)
        window_end = (self.expected_seq + self.receiver_window_size) % self.window.max_seq_num
        
        # Handle wraparound case
        if self.expected_seq <= window_end:
            return self.expected_seq <= seq_num < window_end
        else:
            # Wraparound: window spans across max_seq_num boundary
            return seq_num >= self.expected_seq or seq_num < window_end
    
    def _compute_checksum(self, data: bytes) -> int:
        """Compute simple checksum for data."""
        return sum(data) % (2**16)
    
    def _verify_checksum(self, segment: Segment) -> bool:
        """Verify segment checksum."""
        computed = self._compute_checksum(segment.data)
        return computed == segment.checksum
    
    def get_state(self) -> Dict:
        """
        Get current protocol state for debugging/logging.
        
        Returns:
            Dictionary containing protocol state information
        """
        return {
            'protocol': 'SR',
            'window_state': self.window.get_state(),
            'flow_control_state': self.flow_controller.get_state(),
            'congestion_state': self.congestion_detector.get_state(),
            'timeout_ms': self.timeout_ms,
            'adaptive_timeout_ms': self.congestion_detector.calculate_timeout(self.timeout_ms),
            'sent_segments_count': len(self.sent_segments),
            'expected_seq': self.expected_seq,
            'receiver_buffer_size': len(self.receiver_buffer),
            'unacked_packets': sorted(list(self.window.unacked_packets))
        }
    
    def reset(self):
        """Reset protocol to initial state."""
        self.window.reset()
        self.sent_segments.clear()
        self.receiver_buffer.clear()
        self.expected_seq = 0
        self.flow_controller.reset()
        self.congestion_detector.reset()
