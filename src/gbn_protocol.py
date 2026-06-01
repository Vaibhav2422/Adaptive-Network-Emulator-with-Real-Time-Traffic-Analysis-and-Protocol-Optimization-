"""
Go-Back-N (GBN) Protocol implementation for the Adaptive Network Emulator.

This module implements the Go-Back-N reliable data transfer protocol with
sliding window flow control. GBN retransmits all packets from a lost packet
onward when a timeout occurs.

Validates: Requirements 3.1, 3.3, 3.8
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable
import time
from src.transport_layer import TransportProtocol, SlidingWindow
from src.data_models import Segment
from src.flow_controller import FlowController
from src.congestion_detector import CongestionDetector


@dataclass
class GBNProtocol(TransportProtocol):
    """
    Go-Back-N protocol implementation.
    
    GBN uses a sliding window for flow control and implements cumulative
    acknowledgments. When a packet is lost, all packets from the lost packet
    onward are retransmitted.
    
    Attributes:
        window: SlidingWindow instance for flow control
        timeout_ms: Retransmission timeout in milliseconds
        sent_segments: Dict mapping sequence numbers to (segment, timestamp)
        send_callback: Optional callback function to actually send segments
        expected_ack: Next expected acknowledgment number (receiver side)
        flow_controller: FlowController instance for managing window sizes
        receiver_buffer_capacity: Receiver's buffer capacity for flow control
        congestion_detector: CongestionDetector instance for congestion control
        
    Validates: Requirements 3.1 (GBN protocol), 3.3 (retransmission), 3.5 (flow control), 3.6 (congestion control), 3.8 (ACK handling)
    """
    window: SlidingWindow
    timeout_ms: int
    sent_segments: Dict[int, tuple[Segment, float]] = field(default_factory=dict)
    send_callback: Optional[Callable[[Segment, str], None]] = None
    expected_ack: int = 0  # Receiver side: next expected sequence number
    flow_controller: Optional[FlowController] = None
    receiver_buffer_capacity: int = field(default=None)
    congestion_detector: Optional[CongestionDetector] = None
    
    def __post_init__(self):
        """Initialize flow controller and congestion detector if not provided."""
        if self.flow_controller is None:
            self.flow_controller = FlowController(
                sender_window_size=self.window.window_size,
                max_window_size=self.window.window_size * 2
            )
        
        if self.receiver_buffer_capacity is None:
            self.receiver_buffer_capacity = self.window.window_size
        
        if self.congestion_detector is None:
            self.congestion_detector = CongestionDetector(
                min_window_size=1,
                max_window_size=self.window.window_size * 2
            )
    
    def send_segment(self, data: bytes, dest: str) -> Optional[int]:
        """
        Send a data segment using GBN protocol.
        
        Args:
            data: Data to send
            dest: Destination identifier
        
        Returns:
            Sequence number assigned to the segment, or None if window is full
            
        Validates: Requirement 3.1 (GBN send logic with window management), 3.5 (flow control)
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
            ack_num=0,  # Not used in GBN sender
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
        Handle a cumulative acknowledgment in GBN.
        
        In GBN, an ACK for sequence number N acknowledges all packets
        up to and including N. This advances the window forward.
        
        Args:
            ack_num: Sequence number being acknowledged (cumulative)
            advertised_window: Optional receiver window size advertisement
            
        Validates: Requirement 3.5 (flow control), 3.6 (congestion control), 3.8 (window advancement on ACK)
        """
        # Update flow control if receiver advertises window
        if advertised_window is not None:
            self.flow_controller.adjust_sender_window(advertised_window)
        
        # Record RTT for acknowledged packets
        current_time = time.time()
        for seq_num in list(self.window.unacked_packets):
            if self._is_seq_less_or_equal(seq_num, ack_num):
                if seq_num in self.sent_segments:
                    _, send_time = self.sent_segments[seq_num]
                    rtt_ms = (current_time - send_time) * 1000  # Convert to ms
                    self.congestion_detector.record_rtt_sample(rtt_ms)
        
        # GBN uses cumulative ACKs: ACK N means all packets <= N are acknowledged
        # Acknowledge all packets from base up to and including ack_num
        packets_to_ack = []
        
        for seq_num in list(self.window.unacked_packets):
            # Check if this packet should be acknowledged
            if self._is_seq_less_or_equal(seq_num, ack_num):
                packets_to_ack.append(seq_num)
        
        # Acknowledge all packets
        for seq_num in packets_to_ack:
            self.window.acknowledge(seq_num)
            # Remove from sent_segments
            if seq_num in self.sent_segments:
                del self.sent_segments[seq_num]
        
        # Adapt window size based on congestion detection
        current_window = self.flow_controller.sender_window_size
        new_window = self.congestion_detector.adapt_window_size(current_window)
        if new_window != current_window:
            self.flow_controller.set_sender_window(new_window)
    
    def handle_timeout(self, seq_num: int) -> List[Segment]:
        """
        Handle a timeout for a specific sequence number in GBN.
        
        In GBN, when a timeout occurs for packet N, all packets from N onward
        (all unacknowledged packets) are retransmitted.
        
        Args:
            seq_num: Sequence number that timed out
            
        Returns:
            List of segments to retransmit (all from seq_num onward)
            
        Validates: Requirement 3.3 (GBN retransmits from lost packet onward), 3.6 (congestion detection)
        """
        # Record packet loss for congestion detection
        self.congestion_detector.record_packet_loss()
        
        segments_to_retransmit = []
        
        # Get all unacknowledged packets in order
        unacked = sorted(list(self.window.unacked_packets))
        
        # Find the position of the timed-out packet
        if seq_num in unacked:
            idx = unacked.index(seq_num)
            # Retransmit from this packet onward
            packets_to_retransmit = unacked[idx:]
        else:
            # If the specific packet is not in unacked, retransmit all unacked
            packets_to_retransmit = unacked
        
        # Collect segments to retransmit
        for pkt_seq in packets_to_retransmit:
            if pkt_seq in self.sent_segments:
                segment, _ = self.sent_segments[pkt_seq]
                # Update timestamp
                self.sent_segments[pkt_seq] = (segment, time.time())
                segments_to_retransmit.append(segment)
        
        return segments_to_retransmit
    
    def check_timeouts(self) -> List[tuple[int, List[Segment]]]:
        """
        Check for timed-out packets and return segments to retransmit.
        
        Uses adaptive timeout based on RTT measurements.
        
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
                    break  # In GBN, we only need to detect one timeout
        
        return timed_out
    
    def receive_segment(self, segment: Segment) -> Optional[tuple[int, int]]:
        """
        Receive a segment on the receiver side (GBN receiver logic).
        
        GBN receiver only accepts in-order packets. Out-of-order packets
        are discarded, and the receiver sends an ACK for the last correctly
        received in-order packet.
        
        Args:
            segment: Received segment
            
        Returns:
            Tuple of (ACK number, advertised receiver window), or None if segment is rejected
            
        Validates: Requirement 3.1 (GBN receiver accepts only in-order packets), 3.5 (receiver window advertisement)
        """
        # Verify checksum
        if not self._verify_checksum(segment):
            # Discard corrupted segment
            return None
        
        # Calculate available receiver buffer space
        available_buffer = self.receiver_buffer_capacity
        advertised_window = self.flow_controller.advertise_receiver_window(available_buffer)
        
        # Check if this is the expected sequence number
        if segment.sequence_num == self.expected_ack:
            # This is the expected packet, accept it
            self.expected_ack = (self.expected_ack + 1) % self.window.max_seq_num
            # Return ACK for this packet with advertised window
            return (segment.sequence_num, advertised_window)
        else:
            # Out-of-order packet, discard and send ACK for last in-order packet
            # ACK for the last correctly received packet (expected_ack - 1)
            if self.expected_ack == 0:
                return None  # No packets received yet
            else:
                last_ack = (self.expected_ack - 1) % self.window.max_seq_num
                return (last_ack, advertised_window)
    
    def _compute_checksum(self, data: bytes) -> int:
        """Compute simple checksum for data."""
        return sum(data) % (2**16)
    
    def _verify_checksum(self, segment: Segment) -> bool:
        """Verify segment checksum."""
        computed = self._compute_checksum(segment.data)
        return computed == segment.checksum
    
    def _is_seq_less_or_equal(self, seq1: int, seq2: int) -> bool:
        """
        Check if seq1 <= seq2 considering wraparound.
        
        This handles the case where sequence numbers wrap around at max_seq_num.
        """
        # Simple case: no wraparound
        if self.window.base <= seq2:
            return self.window.base <= seq1 <= seq2
        else:
            # Wraparound case
            return seq1 >= self.window.base or seq1 <= seq2
    
    def get_state(self) -> Dict:
        """
        Get current protocol state for debugging/logging.
        
        Returns:
            Dictionary containing protocol state information
        """
        return {
            'protocol': 'GBN',
            'window_state': self.window.get_state(),
            'flow_control_state': self.flow_controller.get_state(),
            'congestion_state': self.congestion_detector.get_state(),
            'timeout_ms': self.timeout_ms,
            'adaptive_timeout_ms': self.congestion_detector.calculate_timeout(self.timeout_ms),
            'sent_segments_count': len(self.sent_segments),
            'expected_ack': self.expected_ack,
            'unacked_packets': sorted(list(self.window.unacked_packets))
        }
    
    def reset(self):
        """Reset protocol to initial state."""
        self.window.reset()
        self.sent_segments.clear()
        self.expected_ack = 0
        self.flow_controller.reset()
        self.congestion_detector.reset()
