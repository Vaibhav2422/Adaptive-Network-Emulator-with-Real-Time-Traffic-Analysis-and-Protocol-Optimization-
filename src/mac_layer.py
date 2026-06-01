"""
MAC Layer implementation for the Adaptive Network Emulator.

Implements CSMA/CD (Carrier Sense Multiple Access with Collision Detection)
simulation with exponential backoff algorithm.

Validates: Requirements 6.1, 6.2, 6.3, 6.6
"""

import random
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ChannelState(Enum):
    """Channel state for CSMA/CD."""
    IDLE = "idle"
    BUSY = "busy"
    COLLISION = "collision"


@dataclass
class MACLayerConfig:
    """Configuration for MAC Layer."""
    slot_time_ms: float = 0.0512  # 51.2 microseconds (Ethernet standard)
    max_retries: int = 16  # Maximum transmission attempts
    random_seed: Optional[int] = None


@dataclass
class TransmissionAttempt:
    """Tracks a transmission attempt."""
    frame_id: str
    attempt_count: int
    backoff_slots: int
    timestamp: float


class MACLayer:
    """
    MAC Layer implementing CSMA/CD simulation.
    
    Features:
    - Carrier sensing before transmission
    - Collision detection for simultaneous transmissions
    - Exponential backoff algorithm
    - Transmission attempt tracking
    - Max retry limit enforcement
    
    This is a simplified simulation that models the logical behavior
    of CSMA/CD without actual physical signal detection.
    """
    
    def __init__(self, node_id: str, config: MACLayerConfig):
        """
        Initialize MAC Layer.
        
        Args:
            node_id: Identifier for this node
            config: MAC layer configuration
        """
        self.node_id = node_id
        self.config = config
        self.logger = logging.getLogger(f"emulator.mac_layer.{node_id}")
        
        # Channel state management
        self.channel_state = ChannelState.IDLE
        self.transmitting_nodes = set()  # Nodes currently transmitting
        
        # Transmission tracking
        self.current_attempt: Optional[TransmissionAttempt] = None
        self.transmission_history = []
        
        # Statistics
        self.stats = {
            'total_transmissions': 0,
            'successful_transmissions': 0,
            'collisions_detected': 0,
            'carrier_sense_busy': 0,
            'max_retries_exceeded': 0,
            'total_backoff_time': 0.0
        }
        
        # Initialize random number generator with seed if provided
        if config.random_seed is not None:
            self.rng = random.Random(config.random_seed)
        else:
            self.rng = random.Random()
        
        self.logger.info(
            f"MAC Layer initialized: slot_time={config.slot_time_ms} ms, "
            f"max_retries={config.max_retries}"
        )
    
    def sense_channel(self) -> bool:
        """
        Sense the channel to check if it's idle.
        
        This implements the "Carrier Sense" part of CSMA/CD.
        Before attempting transmission, the node checks if the
        channel is currently idle.
        
        Returns:
            True if channel is idle, False if busy
        """
        is_idle = self.channel_state == ChannelState.IDLE
        
        if not is_idle:
            self.stats['carrier_sense_busy'] += 1
            self.logger.debug(
                f"Carrier sense: channel BUSY (state={self.channel_state.value})"
            )
        else:
            self.logger.debug("Carrier sense: channel IDLE")
        
        return is_idle
    
    def detect_collision(self) -> bool:
        """
        Detect if a collision has occurred.
        
        A collision occurs when multiple nodes attempt to transmit
        simultaneously. This is detected by checking if more than
        one node is currently transmitting.
        
        Returns:
            True if collision detected
        """
        collision = len(self.transmitting_nodes) > 1
        
        if collision:
            self.channel_state = ChannelState.COLLISION
            self.stats['collisions_detected'] += 1
            self.logger.warning(
                f"COLLISION detected: {len(self.transmitting_nodes)} nodes transmitting "
                f"({', '.join(self.transmitting_nodes)})"
            )
        
        return collision
    
    def calculate_backoff(self, attempt_count: int) -> int:
        """
        Calculate exponential backoff time in slots.
        
        Implements the exponential backoff algorithm:
        - Backoff slots = random(0, 2^min(k, 10) - 1)
        - k = collision attempt number
        
        Args:
            attempt_count: Number of transmission attempts (collisions)
        
        Returns:
            Number of backoff slots
        """
        # Exponential backoff: k = min(attempt_count, 10)
        k = min(attempt_count, 10)
        max_slots = (2 ** k) - 1
        
        # Random backoff in range [0, max_slots]
        backoff_slots = self.rng.randint(0, max_slots)
        
        self.logger.debug(
            f"Exponential backoff: attempt={attempt_count}, k={k}, "
            f"max_slots={max_slots}, backoff={backoff_slots} slots"
        )
        
        return backoff_slots
    
    def get_backoff_time(self, backoff_slots: int) -> float:
        """
        Convert backoff slots to time in seconds.
        
        Args:
            backoff_slots: Number of backoff slots
        
        Returns:
            Backoff time in seconds
        """
        return backoff_slots * (self.config.slot_time_ms / 1000.0)
    
    def request_transmission(self, frame_id: str, frame_data: bytes,
                           timestamp: float,
                           callback: Optional[Callable] = None) -> tuple[bool, Optional[int], Optional[float]]:
        """
        Request transmission of a frame.
        
        This method implements the complete CSMA/CD algorithm:
        1. Sense the channel
        2. If idle, attempt transmission
        3. Detect collisions
        4. On collision, execute exponential backoff
        5. Track attempts and enforce max retry limit
        
        Args:
            frame_id: Unique identifier for the frame
            frame_data: Frame data to transmit
            timestamp: Current simulation time
            callback: Optional callback on successful transmission
        
        Returns:
            Tuple of (success, backoff_slots, backoff_time):
            - success: True if transmission can proceed, False if must backoff or failed
            - backoff_slots: Number of backoff slots (None if no backoff needed)
            - backoff_time: Backoff time in seconds (None if no backoff needed)
        """
        # Initialize attempt tracking if this is a new frame
        if self.current_attempt is None or self.current_attempt.frame_id != frame_id:
            self.current_attempt = TransmissionAttempt(
                frame_id=frame_id,
                attempt_count=0,
                backoff_slots=0,
                timestamp=timestamp
            )
        
        attempt_count = self.current_attempt.attempt_count
        
        # Check if max retries exceeded
        if attempt_count >= self.config.max_retries:
            self.stats['max_retries_exceeded'] += 1
            self.logger.error(
                f"Max retries exceeded for frame {frame_id}: {attempt_count} attempts"
            )
            self.current_attempt = None
            return False, None, None
        
        # Step 1: Carrier sense - check if channel is idle
        if not self.sense_channel():
            # Channel is busy, must wait
            self.logger.debug(f"Frame {frame_id}: channel busy, waiting")
            return False, None, None
        
        # Step 2: Attempt transmission
        self.stats['total_transmissions'] += 1
        self.current_attempt.attempt_count += 1
        
        # Mark this node as transmitting
        self.transmitting_nodes.add(self.node_id)
        self.channel_state = ChannelState.BUSY
        
        self.logger.debug(
            f"Frame {frame_id}: transmission attempt {self.current_attempt.attempt_count}"
        )
        
        # Step 3: Check for collision (would be detected during transmission)
        # In simulation, we check immediately after starting transmission
        if self.detect_collision():
            # Collision detected - abort transmission
            self.transmitting_nodes.discard(self.node_id)
            
            # Calculate exponential backoff
            backoff_slots = self.calculate_backoff(self.current_attempt.attempt_count)
            backoff_time = self.get_backoff_time(backoff_slots)
            
            self.current_attempt.backoff_slots = backoff_slots
            self.stats['total_backoff_time'] += backoff_time
            
            self.logger.warning(
                f"Frame {frame_id}: collision on attempt {self.current_attempt.attempt_count}, "
                f"backing off {backoff_slots} slots ({backoff_time*1000:.3f} ms)"
            )
            
            # Update channel state if no other nodes transmitting
            if len(self.transmitting_nodes) == 0:
                self.channel_state = ChannelState.IDLE
            
            return False, backoff_slots, backoff_time
        
        # No collision - transmission successful
        self.stats['successful_transmissions'] += 1
        self.logger.info(
            f"Frame {frame_id}: transmission successful on attempt {self.current_attempt.attempt_count}"
        )
        
        # Record in history
        self.transmission_history.append({
            'frame_id': frame_id,
            'timestamp': timestamp,
            'attempts': self.current_attempt.attempt_count,
            'success': True
        })
        
        # Invoke callback if provided
        if callback:
            callback(frame_data)
        
        # Reset attempt tracking
        self.current_attempt = None
        
        return True, None, None
    
    def complete_transmission(self) -> None:
        """
        Mark transmission as complete and release the channel.
        
        This should be called after the frame has been fully transmitted
        to update the channel state.
        """
        self.transmitting_nodes.discard(self.node_id)
        
        # Update channel state
        if len(self.transmitting_nodes) == 0:
            self.channel_state = ChannelState.IDLE
            self.logger.debug("Transmission complete, channel now IDLE")
        elif len(self.transmitting_nodes) == 1:
            self.channel_state = ChannelState.BUSY
        else:
            self.channel_state = ChannelState.COLLISION
    
    def notify_transmission_start(self, node_id: str) -> None:
        """
        Notify MAC layer that another node has started transmitting.
        
        This is used in simulation to coordinate channel state across nodes.
        
        Args:
            node_id: ID of node that started transmitting
        """
        self.transmitting_nodes.add(node_id)
        
        if len(self.transmitting_nodes) > 1:
            self.channel_state = ChannelState.COLLISION
        else:
            self.channel_state = ChannelState.BUSY
        
        self.logger.debug(
            f"Node {node_id} started transmission, "
            f"channel state: {self.channel_state.value}"
        )
    
    def notify_transmission_end(self, node_id: str) -> None:
        """
        Notify MAC layer that another node has finished transmitting.
        
        Args:
            node_id: ID of node that finished transmitting
        """
        self.transmitting_nodes.discard(node_id)
        
        if len(self.transmitting_nodes) == 0:
            self.channel_state = ChannelState.IDLE
        elif len(self.transmitting_nodes) == 1:
            self.channel_state = ChannelState.BUSY
        else:
            self.channel_state = ChannelState.COLLISION
        
        self.logger.debug(
            f"Node {node_id} finished transmission, "
            f"channel state: {self.channel_state.value}"
        )
    
    def get_statistics(self) -> dict:
        """
        Get MAC layer statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['total_transmissions'] > 0:
            stats['success_rate'] = (
                stats['successful_transmissions'] / stats['total_transmissions']
            )
            stats['collision_rate'] = (
                stats['collisions_detected'] / stats['total_transmissions']
            )
        else:
            stats['success_rate'] = 0.0
            stats['collision_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self.stats = {
            'total_transmissions': 0,
            'successful_transmissions': 0,
            'collisions_detected': 0,
            'carrier_sense_busy': 0,
            'max_retries_exceeded': 0,
            'total_backoff_time': 0.0
        }
        self.logger.debug("Statistics reset")
    
    def get_channel_state(self) -> ChannelState:
        """
        Get current channel state.
        
        Returns:
            Current channel state
        """
        return self.channel_state
    
    def get_current_attempt(self) -> Optional[TransmissionAttempt]:
        """
        Get current transmission attempt information.
        
        Returns:
            Current transmission attempt or None
        """
        return self.current_attempt
