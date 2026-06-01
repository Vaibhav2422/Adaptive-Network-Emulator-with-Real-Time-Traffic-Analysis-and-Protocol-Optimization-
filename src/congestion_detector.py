"""
Congestion Detector implementation for the Adaptive Network Emulator.

This module implements congestion detection and adaptation mechanisms for
the transport layer, monitoring packet loss and latency to detect congestion
and adapt transmission parameters accordingly.

Validates: Requirement 3.6
"""

from dataclasses import dataclass, field
from typing import List, Optional
import time
from collections import deque


@dataclass
class CongestionDetector:
    """
    Implements congestion detection and adaptation for transport protocols.
    
    The congestion detector monitors packet loss rate and latency increases
    to detect network congestion. When congestion is detected, it adapts
    transmission parameters (window size, timeout) to reduce load on the
    network. When conditions improve, it gradually increases parameters.
    
    Attributes:
        loss_threshold: Packet loss rate threshold for congestion detection (default 0.05 = 5%)
        latency_threshold_ms: Latency increase threshold in milliseconds (default 50ms)
        window_decrease_factor: Factor to decrease window on congestion (default 0.5)
        window_increase_step: Step to increase window on improvement (default 1)
        min_window_size: Minimum window size (default 1)
        max_window_size: Maximum window size (default 64)
        rtt_samples: Recent RTT samples for timeout calculation
        max_rtt_samples: Maximum number of RTT samples to keep (default 10)
        packet_loss_count: Count of lost packets
        packet_sent_count: Count of sent packets
        baseline_rtt_ms: Baseline RTT in milliseconds
        current_rtt_ms: Current RTT in milliseconds
        congestion_detected: Whether congestion is currently detected
        
    Validates: Requirement 3.6 (congestion detection and adaptation)
    """
    loss_threshold: float = 0.05  # 5% packet loss threshold
    latency_threshold_ms: float = 50.0  # 50ms latency increase threshold
    window_decrease_factor: float = 0.5  # Halve window on congestion
    window_increase_step: int = 1  # Increase window by 1 on improvement
    min_window_size: int = 1
    max_window_size: int = 64
    rtt_samples: deque = field(default_factory=lambda: deque(maxlen=10))
    max_rtt_samples: int = 10
    packet_loss_count: int = 0
    packet_sent_count: int = 0
    baseline_rtt_ms: Optional[float] = None
    current_rtt_ms: Optional[float] = None
    congestion_detected: bool = False
    
    def __post_init__(self):
        """Validate congestion detector parameters."""
        if self.loss_threshold < 0 or self.loss_threshold > 1:
            raise ValueError("loss_threshold must be between 0 and 1")
        if self.latency_threshold_ms < 0:
            raise ValueError("latency_threshold_ms must be non-negative")
        if self.window_decrease_factor <= 0 or self.window_decrease_factor >= 1:
            raise ValueError("window_decrease_factor must be between 0 and 1")
        if self.window_increase_step < 1:
            raise ValueError("window_increase_step must be at least 1")
    
    def record_packet_sent(self) -> None:
        """
        Record that a packet was sent.
        
        This is used to track the total number of packets sent for
        calculating packet loss rate.
        
        Validates: Requirement 3.6 (packet loss rate monitoring)
        """
        self.packet_sent_count += 1
    
    def record_packet_loss(self) -> None:
        """
        Record that a packet was lost.
        
        This is used to track packet losses for calculating loss rate
        and detecting congestion.
        
        Validates: Requirement 3.6 (packet loss rate monitoring)
        """
        self.packet_loss_count += 1
    
    def record_rtt_sample(self, rtt_ms: float) -> None:
        """
        Record a Round-Trip Time (RTT) sample.
        
        RTT samples are used to calculate current RTT and detect
        latency increases that indicate congestion.
        
        Args:
            rtt_ms: RTT sample in milliseconds
        
        Validates: Requirement 3.6 (latency increase detection)
        """
        if rtt_ms < 0:
            return  # Invalid RTT
        
        self.rtt_samples.append(rtt_ms)
        
        # Update current RTT (average of recent samples)
        if len(self.rtt_samples) > 0:
            self.current_rtt_ms = sum(self.rtt_samples) / len(self.rtt_samples)
        
        # Set baseline RTT if not set (use first few samples)
        if self.baseline_rtt_ms is None and len(self.rtt_samples) >= 3:
            self.baseline_rtt_ms = self.current_rtt_ms
    
    def get_packet_loss_rate(self) -> float:
        """
        Calculate the current packet loss rate.
        
        Returns:
            Packet loss rate as a fraction (0.0 to 1.0)
        
        Validates: Requirement 3.6 (packet loss rate monitoring)
        """
        if self.packet_sent_count == 0:
            return 0.0
        
        return self.packet_loss_count / self.packet_sent_count
    
    def get_latency_increase(self) -> float:
        """
        Calculate the latency increase from baseline.
        
        Returns:
            Latency increase in milliseconds, or 0 if baseline not established
        
        Validates: Requirement 3.6 (latency increase detection)
        """
        if self.baseline_rtt_ms is None or self.current_rtt_ms is None:
            return 0.0
        
        return max(0.0, self.current_rtt_ms - self.baseline_rtt_ms)
    
    def detect_congestion(self) -> bool:
        """
        Detect if congestion is occurring based on loss rate and latency.
        
        Congestion is detected if:
        - Packet loss rate exceeds threshold, OR
        - Latency increase exceeds threshold
        
        Returns:
            True if congestion is detected
        
        Validates: Requirement 3.6 (congestion detection)
        """
        loss_rate = self.get_packet_loss_rate()
        latency_increase = self.get_latency_increase()
        
        # Detect congestion if either threshold is exceeded
        congestion = (loss_rate > self.loss_threshold or 
                     latency_increase > self.latency_threshold_ms)
        
        self.congestion_detected = congestion
        return congestion
    
    def adapt_window_size(self, current_window_size: int) -> int:
        """
        Adapt window size based on congestion detection.
        
        If congestion is detected, reduce window size.
        If no congestion, gradually increase window size.
        
        Args:
            current_window_size: Current window size
        
        Returns:
            New adapted window size
        
        Validates: Requirement 3.6 (window size reduction/increase on congestion)
        """
        if self.detect_congestion():
            # Congestion detected: reduce window size
            new_window_size = int(current_window_size * self.window_decrease_factor)
            new_window_size = max(self.min_window_size, new_window_size)
        else:
            # No congestion: gradually increase window size
            new_window_size = current_window_size + self.window_increase_step
            new_window_size = min(self.max_window_size, new_window_size)
        
        return new_window_size
    
    def calculate_timeout(self, base_timeout_ms: int) -> int:
        """
        Calculate adaptive timeout based on RTT measurements.
        
        The timeout is calculated as: timeout = base_timeout + (alpha * RTT)
        where alpha is a multiplier (typically 2-4) to account for variance.
        
        Args:
            base_timeout_ms: Base timeout in milliseconds
        
        Returns:
            Adapted timeout in milliseconds
        
        Validates: Requirement 3.6 (timeout adjustment based on RTT)
        """
        if self.current_rtt_ms is None or len(self.rtt_samples) < 2:
            # Not enough data, use base timeout
            return base_timeout_ms
        
        # Calculate RTT variance
        mean_rtt = self.current_rtt_ms
        variance = sum((rtt - mean_rtt) ** 2 for rtt in self.rtt_samples) / len(self.rtt_samples)
        std_dev = variance ** 0.5
        
        # Timeout = mean RTT + 4 * std_dev (standard TCP approach)
        adaptive_timeout = mean_rtt + (4 * std_dev)
        
        # Ensure timeout is at least the base timeout
        adaptive_timeout = max(base_timeout_ms, adaptive_timeout)
        
        return int(adaptive_timeout)
    
    def reset_statistics(self) -> None:
        """
        Reset packet loss and latency statistics.
        
        This can be called periodically to get fresh measurements
        or after a congestion event has been handled.
        """
        self.packet_loss_count = 0
        self.packet_sent_count = 0
        self.congestion_detected = False
        # Keep RTT samples and baseline for continuity
    
    def reset(self) -> None:
        """
        Reset congestion detector to initial state.
        
        This clears all statistics and RTT samples.
        """
        self.packet_loss_count = 0
        self.packet_sent_count = 0
        self.rtt_samples.clear()
        self.baseline_rtt_ms = None
        self.current_rtt_ms = None
        self.congestion_detected = False
    
    def get_state(self) -> dict:
        """
        Get the current congestion detector state for debugging/logging.
        
        Returns:
            Dictionary containing congestion detector state information
        """
        return {
            'packet_loss_rate': self.get_packet_loss_rate(),
            'packet_loss_count': self.packet_loss_count,
            'packet_sent_count': self.packet_sent_count,
            'current_rtt_ms': self.current_rtt_ms,
            'baseline_rtt_ms': self.baseline_rtt_ms,
            'latency_increase_ms': self.get_latency_increase(),
            'congestion_detected': self.congestion_detected,
            'loss_threshold': self.loss_threshold,
            'latency_threshold_ms': self.latency_threshold_ms,
            'rtt_samples_count': len(self.rtt_samples)
        }
