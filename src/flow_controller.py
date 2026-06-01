"""
Flow Controller implementation for the Adaptive Network Emulator.

This module implements flow control mechanisms for the transport layer,
managing sender window adjustment based on receiver capacity to prevent
overwhelming the receiver.

Validates: Requirement 3.5
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FlowController:
    """
    Implements flow control for transport protocols.
    
    Flow control manages the transmission rate to prevent the sender from
    overwhelming the receiver. The receiver advertises its available buffer
    space (receiver window), and the sender adjusts its sending window
    accordingly.
    
    Attributes:
        sender_window_size: Current sender window size
        receiver_window_size: Advertised receiver window size
        max_window_size: Maximum allowed window size
        min_window_size: Minimum allowed window size (default 1)
        effective_window_size: Actual window size used (min of sender and receiver)
        
    Validates: Requirement 3.5 (sliding window flow control)
    """
    sender_window_size: int
    receiver_window_size: int = field(default=None)
    max_window_size: int = 64
    min_window_size: int = 1
    effective_window_size: int = field(init=False)
    
    def __post_init__(self):
        """Initialize flow controller and validate parameters."""
        if self.sender_window_size < self.min_window_size:
            raise ValueError(f"sender_window_size must be at least {self.min_window_size}")
        if self.sender_window_size > self.max_window_size:
            raise ValueError(f"sender_window_size cannot exceed {self.max_window_size}")
        
        # Initialize receiver window to sender window if not set
        if self.receiver_window_size is None:
            self.receiver_window_size = self.sender_window_size
        
        # Calculate effective window size
        self._update_effective_window()
    
    def advertise_receiver_window(self, available_buffer: int) -> int:
        """
        Advertise the receiver's available buffer space.
        
        The receiver calls this method to advertise how much buffer space
        it has available. This value is sent to the sender in acknowledgments.
        
        Args:
            available_buffer: Number of packets the receiver can buffer
        
        Returns:
            The advertised receiver window size
            
        Validates: Requirement 3.5 (receiver window advertisement)
        """
        # Ensure receiver window is within valid range
        self.receiver_window_size = max(self.min_window_size, 
                                       min(available_buffer, self.max_window_size))
        
        # Update effective window
        self._update_effective_window()
        
        return self.receiver_window_size
    
    def adjust_sender_window(self, advertised_window: int) -> int:
        """
        Adjust sender window based on receiver's advertised window.
        
        The sender calls this method when it receives an advertised window
        size from the receiver. The sender's effective window is the minimum
        of its own window and the receiver's advertised window.
        
        Args:
            advertised_window: Window size advertised by receiver
        
        Returns:
            The new effective window size
            
        Validates: Requirement 3.5 (sender window adjustment based on receiver capacity)
        """
        # Update receiver window with advertised value
        self.receiver_window_size = max(self.min_window_size,
                                       min(advertised_window, self.max_window_size))
        
        # Update effective window
        self._update_effective_window()
        
        return self.effective_window_size
    
    def set_sender_window(self, window_size: int) -> int:
        """
        Set the sender's window size.
        
        This allows the sender to adjust its own window size (e.g., for
        congestion control). The effective window will still be limited
        by the receiver's advertised window.
        
        Args:
            window_size: New sender window size
        
        Returns:
            The new effective window size
        """
        # Ensure sender window is within valid range
        self.sender_window_size = max(self.min_window_size,
                                     min(window_size, self.max_window_size))
        
        # Update effective window
        self._update_effective_window()
        
        return self.effective_window_size
    
    def get_effective_window_size(self) -> int:
        """
        Get the current effective window size.
        
        The effective window size is the minimum of the sender's window
        and the receiver's advertised window. This is the actual window
        size that should be used for transmission.
        
        Returns:
            The effective window size
        """
        return self.effective_window_size
    
    def can_send(self, unacked_count: int) -> bool:
        """
        Check if the sender can send more packets.
        
        Args:
            unacked_count: Number of currently unacknowledged packets
        
        Returns:
            True if more packets can be sent within the effective window
        """
        return unacked_count < self.effective_window_size
    
    def get_available_window(self, unacked_count: int) -> int:
        """
        Get the number of additional packets that can be sent.
        
        Args:
            unacked_count: Number of currently unacknowledged packets
        
        Returns:
            Number of additional packets that can be sent
        """
        return max(0, self.effective_window_size - unacked_count)
    
    def _update_effective_window(self):
        """
        Update the effective window size.
        
        The effective window is the minimum of sender and receiver windows,
        ensuring we don't exceed either limit.
        """
        self.effective_window_size = min(self.sender_window_size, 
                                        self.receiver_window_size)
    
    def get_state(self) -> dict:
        """
        Get the current flow control state for debugging/logging.
        
        Returns:
            Dictionary containing flow control state information
        """
        return {
            'sender_window_size': self.sender_window_size,
            'receiver_window_size': self.receiver_window_size,
            'effective_window_size': self.effective_window_size,
            'max_window_size': self.max_window_size,
            'min_window_size': self.min_window_size
        }
    
    def reset(self, initial_window_size: Optional[int] = None):
        """
        Reset flow controller to initial state.
        
        Args:
            initial_window_size: Optional new initial window size
        """
        if initial_window_size is not None:
            self.sender_window_size = max(self.min_window_size,
                                         min(initial_window_size, self.max_window_size))
        
        self.receiver_window_size = self.sender_window_size
        self._update_effective_window()
