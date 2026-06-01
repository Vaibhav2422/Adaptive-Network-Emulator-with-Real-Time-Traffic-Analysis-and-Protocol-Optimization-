"""
Physical Layer implementation for the Adaptive Network Emulator.

Provides abstract transmission channel with configurable delay, loss, and bit errors.
This is a simplified model that simulates physical transmission without actual
signal-level modeling.

Validates: Requirements 6.4
"""

import random
import logging
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class PhysicalLayerConfig:
    """Configuration for Physical Layer."""
    bit_rate_bps: float = 100_000_000  # 100 Mbps default
    propagation_delay_ms: float = 10.0  # 10ms default
    loss_rate: float = 0.0  # 0% loss default
    bit_error_rate: float = 0.0  # 0% bit error default
    random_seed: Optional[int] = None


class PhysicalLayer:
    """
    Abstract transmission channel with configurable characteristics.
    
    Simulates:
    - Transmission delay (based on packet size and bit rate)
    - Propagation delay (fixed delay representing distance)
    - Random packet loss
    - Bit error injection
    
    This is an abstraction that does not model actual physical signals,
    electromagnetic propagation, or interference. It provides a simplified
    model suitable for educational purposes and protocol testing.
    """
    
    def __init__(self, config: PhysicalLayerConfig):
        """
        Initialize Physical Layer.
        
        Args:
            config: Physical layer configuration
        """
        self.config = config
        self.logger = logging.getLogger("emulator.physical_layer")
        
        # Initialize random number generator with seed if provided
        if config.random_seed is not None:
            self.rng = random.Random(config.random_seed)
        else:
            self.rng = random.Random()
        
        self.logger.info(
            f"Physical Layer initialized: bit_rate={config.bit_rate_bps/1e6:.1f} Mbps, "
            f"propagation_delay={config.propagation_delay_ms} ms, "
            f"loss_rate={config.loss_rate*100:.2f}%, "
            f"bit_error_rate={config.bit_error_rate*100:.4f}%"
        )
    
    def calculate_transmission_delay(self, data_size_bytes: int) -> float:
        """
        Calculate transmission delay based on data size and bit rate.
        
        Transmission delay = (data size in bits) / (bit rate in bps)
        
        Args:
            data_size_bytes: Size of data in bytes
        
        Returns:
            Transmission delay in seconds
        """
        data_size_bits = data_size_bytes * 8
        delay_seconds = data_size_bits / self.config.bit_rate_bps
        return delay_seconds
    
    def get_propagation_delay(self) -> float:
        """
        Get propagation delay.
        
        Returns:
            Propagation delay in seconds
        """
        return self.config.propagation_delay_ms / 1000.0
    
    def get_total_delay(self, data_size_bytes: int) -> float:
        """
        Calculate total delay (transmission + propagation).
        
        Args:
            data_size_bytes: Size of data in bytes
        
        Returns:
            Total delay in seconds
        """
        transmission_delay = self.calculate_transmission_delay(data_size_bytes)
        propagation_delay = self.get_propagation_delay()
        return transmission_delay + propagation_delay
    
    def should_drop_packet(self) -> bool:
        """
        Determine if packet should be dropped based on loss rate.
        
        Returns:
            True if packet should be dropped
        """
        return self.rng.random() < self.config.loss_rate
    
    def inject_bit_errors(self, data: bytes) -> bytes:
        """
        Inject random bit errors into data based on bit error rate.
        
        For each bit in the data, there is a probability (bit_error_rate)
        that the bit will be flipped.
        
        Args:
            data: Original data
        
        Returns:
            Data with potential bit errors injected
        """
        if self.config.bit_error_rate == 0.0:
            return data
        
        # Convert bytes to bytearray for mutation
        data_array = bytearray(data)
        
        # Process each byte
        for byte_idx in range(len(data_array)):
            byte_val = data_array[byte_idx]
            
            # Check each bit in the byte
            for bit_idx in range(8):
                if self.rng.random() < self.config.bit_error_rate:
                    # Flip the bit
                    byte_val ^= (1 << bit_idx)
            
            data_array[byte_idx] = byte_val
        
        return bytes(data_array)
    
    def transmit(self, data: bytes, dest: str,
                callback: Optional[Callable[[bytes, str], None]] = None) -> tuple[bool, Optional[bytes], float]:
        """
        Simulate transmission of data through the physical channel.
        
        This method:
        1. Calculates transmission and propagation delays
        2. Simulates packet loss
        3. Injects bit errors
        4. Returns the result
        
        Args:
            data: Data to transmit
            dest: Destination identifier
            callback: Optional callback to invoke on successful transmission
        
        Returns:
            Tuple of (success, transmitted_data, delay):
            - success: True if packet was not dropped
            - transmitted_data: Data with potential bit errors (None if dropped)
            - delay: Total delay in seconds
        """
        data_size = len(data)
        total_delay = self.get_total_delay(data_size)
        
        # Check for packet loss
        if self.should_drop_packet():
            self.logger.debug(
                f"Packet dropped (loss simulation): size={data_size} bytes, dest={dest}"
            )
            return False, None, total_delay
        
        # Inject bit errors
        transmitted_data = self.inject_bit_errors(data)
        
        # Log if errors were injected
        if transmitted_data != data:
            num_different_bytes = sum(1 for a, b in zip(data, transmitted_data) if a != b)
            self.logger.debug(
                f"Bit errors injected: {num_different_bytes} bytes affected, "
                f"size={data_size} bytes, dest={dest}"
            )
        
        self.logger.debug(
            f"Transmission successful: size={data_size} bytes, "
            f"delay={total_delay*1000:.3f} ms, dest={dest}"
        )
        
        # Invoke callback if provided
        if callback:
            callback(transmitted_data, dest)
        
        return True, transmitted_data, total_delay
    
    def set_bit_rate(self, bit_rate_bps: float) -> None:
        """
        Update bit rate configuration.
        
        Args:
            bit_rate_bps: New bit rate in bits per second
        """
        self.config.bit_rate_bps = bit_rate_bps
        self.logger.info(f"Bit rate updated to {bit_rate_bps/1e6:.1f} Mbps")
    
    def set_propagation_delay(self, delay_ms: float) -> None:
        """
        Update propagation delay configuration.
        
        Args:
            delay_ms: New propagation delay in milliseconds
        """
        self.config.propagation_delay_ms = delay_ms
        self.logger.info(f"Propagation delay updated to {delay_ms} ms")
    
    def set_loss_rate(self, loss_rate: float) -> None:
        """
        Update packet loss rate configuration.
        
        Args:
            loss_rate: New loss rate (0.0 to 1.0)
        """
        if not (0.0 <= loss_rate <= 1.0):
            raise ValueError("Loss rate must be between 0.0 and 1.0")
        self.config.loss_rate = loss_rate
        self.logger.info(f"Loss rate updated to {loss_rate*100:.2f}%")
    
    def set_bit_error_rate(self, bit_error_rate: float) -> None:
        """
        Update bit error rate configuration.
        
        Args:
            bit_error_rate: New bit error rate (0.0 to 1.0)
        """
        if not (0.0 <= bit_error_rate <= 1.0):
            raise ValueError("Bit error rate must be between 0.0 and 1.0")
        self.config.bit_error_rate = bit_error_rate
        self.logger.info(f"Bit error rate updated to {bit_error_rate*100:.4f}%")
    
    def get_config(self) -> PhysicalLayerConfig:
        """
        Get current configuration.
        
        Returns:
            Current physical layer configuration
        """
        return self.config
