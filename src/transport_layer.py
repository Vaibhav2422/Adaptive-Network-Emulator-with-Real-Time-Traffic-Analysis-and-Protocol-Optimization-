"""
Transport Layer implementation for the Adaptive Network Emulator.

This module implements the core sliding window mechanism used by both
Go-Back-N and Selective Repeat protocols. It provides reliable data transfer
with flow control and sequence number management.

Validates: Requirements 3.5, 3.7
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
import time


@dataclass
class SlidingWindow:
    """
    Implements the sliding window mechanism for reliable data transfer.
    
    The sliding window controls the number of unacknowledged packets in flight,
    providing flow control and ensuring reliable delivery. It maintains the
    window state (base and next sequence number) and tracks acknowledgments.
    
    Attributes:
        window_size: Maximum number of unacknowledged packets allowed
        base: Sequence number of oldest unacknowledged packet
        next_seq: Next sequence number to be used
        unacked_packets: Set of sequence numbers for unacknowledged packets
        ack_received: Dict mapping sequence numbers to acknowledgment timestamps
        max_seq_num: Maximum sequence number before wraparound (default 2^32)
    
    Validates: Requirements 3.5 (sliding window flow control), 3.7 (sequence numbers)
    """
    window_size: int
    base: int = 0
    next_seq: int = 0
    unacked_packets: Set[int] = field(default_factory=set)
    ack_received: Dict[int, float] = field(default_factory=dict)
    max_seq_num: int = 2**32
    
    def __post_init__(self):
        """Validate window configuration."""
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        if self.max_seq_num < 1:
            raise ValueError("max_seq_num must be at least 1")
    
    def can_send(self) -> bool:
        """
        Check if a new packet can be sent within the window constraint.
        
        Returns:
            True if the number of unacknowledged packets is less than window_size
        
        Validates: Requirement 3.5 (window constraint)
        """
        return len(self.unacked_packets) < self.window_size
    
    def get_next_sequence_number(self) -> int:
        """
        Generate the next sequence number for a new packet.
        
        Returns:
            The next sequence number to use
        
        Validates: Requirement 3.7 (sequence number generation)
        """
        if not self.can_send():
            raise RuntimeError("Cannot send: window is full")
        
        seq_num = self.next_seq
        self.next_seq = (self.next_seq + 1) % self.max_seq_num
        self.unacked_packets.add(seq_num)
        
        return seq_num
    
    def validate_sequence_number(self, seq_num: int) -> bool:
        """
        Validate that a sequence number is within the valid range.
        
        Args:
            seq_num: Sequence number to validate
        
        Returns:
            True if sequence number is valid
        
        Validates: Requirement 3.7 (sequence number validation)
        """
        return 0 <= seq_num < self.max_seq_num
    
    def is_in_window(self, seq_num: int) -> bool:
        """
        Check if a sequence number is within the current window.
        
        Args:
            seq_num: Sequence number to check
        
        Returns:
            True if sequence number is in the current window
        """
        if not self.validate_sequence_number(seq_num):
            return False
        
        # Handle wraparound case
        if self.base <= self.next_seq:
            return self.base <= seq_num < self.next_seq
        else:
            # Wraparound: window spans across max_seq_num boundary
            return seq_num >= self.base or seq_num < self.next_seq
    
    def acknowledge(self, ack_num: int) -> bool:
        """
        Process an acknowledgment for a sequence number.
        
        Args:
            ack_num: Sequence number being acknowledged
        
        Returns:
            True if acknowledgment was processed successfully
        
        Validates: Requirement 3.5 (acknowledgment tracking)
        """
        if not self.validate_sequence_number(ack_num):
            return False
        
        if ack_num not in self.unacked_packets:
            return False
        
        # Record acknowledgment
        self.ack_received[ack_num] = time.time()
        self.unacked_packets.discard(ack_num)
        
        # Slide window forward if base is acknowledged
        while self.base in self.ack_received and self.base != self.next_seq:
            self.base = (self.base + 1) % self.max_seq_num
        
        return True
    
    def get_unacked_count(self) -> int:
        """
        Get the number of unacknowledged packets.
        
        Returns:
            Number of packets sent but not yet acknowledged
        
        Validates: Requirement 3.5 (window constraint monitoring)
        """
        return len(self.unacked_packets)
    
    def get_window_usage(self) -> float:
        """
        Get the current window utilization as a percentage.
        
        Returns:
            Window usage from 0.0 to 1.0
        """
        return len(self.unacked_packets) / self.window_size
    
    def reset(self):
        """Reset the window to initial state."""
        self.base = 0
        self.next_seq = 0
        self.unacked_packets.clear()
        self.ack_received.clear()
    
    def get_state(self) -> Dict:
        """
        Get the current window state for debugging/logging.
        
        Returns:
            Dictionary containing window state information
        """
        return {
            'window_size': self.window_size,
            'base': self.base,
            'next_seq': self.next_seq,
            'unacked_count': len(self.unacked_packets),
            'unacked_packets': sorted(list(self.unacked_packets)),
            'window_usage': self.get_window_usage()
        }


@dataclass
class TransportProtocol:
    """
    Base class for transport protocols (GBN, SR).
    
    This abstract base class defines the interface that all transport protocols
    must implement. Specific protocols (Go-Back-N, Selective Repeat) will
    extend this class.
    
    Attributes:
        window: SlidingWindow instance for flow control
        timeout_ms: Retransmission timeout in milliseconds
    """
    window: SlidingWindow
    timeout_ms: int
    
    def send_segment(self, data: bytes, dest: str) -> Optional[int]:
        """
        Send a data segment.
        
        Args:
            data: Data to send
            dest: Destination identifier
        
        Returns:
            Sequence number assigned to the segment, or None if window is full
        """
        raise NotImplementedError("Subclasses must implement send_segment")
    
    def handle_acknowledgment(self, ack_num: int) -> None:
        """
        Handle an acknowledgment.
        
        Args:
            ack_num: Sequence number being acknowledged
        """
        raise NotImplementedError("Subclasses must implement handle_acknowledgment")
    
    def handle_timeout(self, seq_num: int) -> None:
        """
        Handle a timeout for a specific sequence number.
        
        Args:
            seq_num: Sequence number that timed out
        """
        raise NotImplementedError("Subclasses must implement handle_timeout")
