"""
Utility functions for the Adaptive Network Emulator.

This module provides common utility functions used throughout the emulator:
- Checksum calculation (CRC-32, simple checksums)
- Bit manipulation helpers
- Time management for simulation
- Random number generation with seed support for reproducibility

Validates: Requirements 10.7 (reproducibility with seeds)
"""

import random
import time
import zlib
from typing import Optional


# ============================================================================
# Random Number Generation with Seed Support
# ============================================================================

class SeededRandom:
    """
    Random number generator with seed support for reproducibility.
    
    This class wraps Python's random module to provide reproducible random
    number generation. All random operations in the emulator should use this
    class to ensure experiments can be reproduced with the same seed.
    
    Validates: Requirements 10.7
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the random number generator.
        
        Args:
            seed: Random seed for reproducibility. If None, uses system time.
        """
        self._rng = random.Random(seed)
        self._seed = seed
    
    def seed(self, seed: int) -> None:
        """Set the random seed."""
        self._seed = seed
        self._rng.seed(seed)
    
    def get_seed(self) -> Optional[int]:
        """Get the current seed."""
        return self._seed
    
    def random(self) -> float:
        """Generate a random float in [0.0, 1.0)."""
        return self._rng.random()
    
    def randint(self, a: int, b: int) -> int:
        """Generate a random integer in [a, b]."""
        return self._rng.randint(a, b)
    
    def uniform(self, a: float, b: float) -> float:
        """Generate a random float in [a, b]."""
        return self._rng.uniform(a, b)
    
    def choice(self, seq):
        """Choose a random element from a non-empty sequence."""
        return self._rng.choice(seq)
    
    def shuffle(self, seq) -> None:
        """Shuffle a sequence in place."""
        self._rng.shuffle(seq)
    
    def sample(self, population, k: int):
        """Choose k unique random elements from a population."""
        return self._rng.sample(population, k)
    
    def gauss(self, mu: float, sigma: float) -> float:
        """Generate a random number from Gaussian distribution."""
        return self._rng.gauss(mu, sigma)


# Global seeded random instance
_global_rng: Optional[SeededRandom] = None


def set_global_seed(seed: int) -> None:
    """
    Set the global random seed for the emulator.
    
    This should be called once at emulator startup to ensure reproducibility.
    
    Args:
        seed: Random seed value
    """
    global _global_rng
    _global_rng = SeededRandom(seed)


def get_random() -> SeededRandom:
    """
    Get the global random number generator.
    
    Returns:
        Global SeededRandom instance
    
    Raises:
        RuntimeError: If global seed has not been set
    """
    global _global_rng
    if _global_rng is None:
        # Initialize with None seed (system time) if not explicitly set
        _global_rng = SeededRandom()
    return _global_rng


# ============================================================================
# Checksum Calculation
# ============================================================================

def calculate_crc32(data: bytes) -> int:
    """
    Calculate CRC-32 checksum for data.
    
    Uses the standard CRC-32 algorithm (same as used in Ethernet, ZIP, etc.).
    
    Args:
        data: Bytes to calculate checksum for
    
    Returns:
        32-bit CRC checksum as unsigned integer
    """
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc32(data: bytes, expected_crc: int) -> bool:
    """
    Verify CRC-32 checksum.
    
    Args:
        data: Data to verify
        expected_crc: Expected CRC value
    
    Returns:
        True if checksum matches, False otherwise
    """
    return calculate_crc32(data) == expected_crc


def calculate_checksum(data: bytes) -> int:
    """
    Calculate simple 16-bit checksum (Internet checksum).
    
    This is the checksum algorithm used in TCP/UDP/IP headers.
    Sums 16-bit words and folds carry bits back into the sum.
    
    Args:
        data: Bytes to calculate checksum for
    
    Returns:
        16-bit checksum as unsigned integer
    """
    # Pad data to even length if necessary
    if len(data) % 2 == 1:
        data = data + b'\x00'
    
    # Sum all 16-bit words
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
    
    # Fold 32-bit sum to 16 bits
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    
    # One's complement
    return (~total) & 0xFFFF


def verify_checksum(data: bytes, expected_checksum: int) -> bool:
    """
    Verify 16-bit checksum.
    
    Args:
        data: Data to verify
        expected_checksum: Expected checksum value
    
    Returns:
        True if checksum matches, False otherwise
    """
    return calculate_checksum(data) == expected_checksum


# ============================================================================
# Bit Manipulation
# ============================================================================

def set_bit(value: int, bit_position: int) -> int:
    """
    Set a specific bit to 1.
    
    Args:
        value: Original value
        bit_position: Position of bit to set (0 = LSB)
    
    Returns:
        Value with bit set
    """
    return value | (1 << bit_position)


def clear_bit(value: int, bit_position: int) -> int:
    """
    Clear a specific bit to 0.
    
    Args:
        value: Original value
        bit_position: Position of bit to clear (0 = LSB)
    
    Returns:
        Value with bit cleared
    """
    return value & ~(1 << bit_position)


def toggle_bit(value: int, bit_position: int) -> int:
    """
    Toggle a specific bit.
    
    Args:
        value: Original value
        bit_position: Position of bit to toggle (0 = LSB)
    
    Returns:
        Value with bit toggled
    """
    return value ^ (1 << bit_position)


def get_bit(value: int, bit_position: int) -> int:
    """
    Get the value of a specific bit.
    
    Args:
        value: Value to check
        bit_position: Position of bit to get (0 = LSB)
    
    Returns:
        0 or 1
    """
    return (value >> bit_position) & 1


def flip_bit_in_bytes(data: bytes, bit_position: int) -> bytes:
    """
    Flip a specific bit in a byte array.
    
    Args:
        data: Byte array
        bit_position: Absolute bit position (0 = first bit of first byte)
    
    Returns:
        New byte array with bit flipped
    """
    byte_array = bytearray(data)
    byte_index = bit_position // 8
    bit_index = bit_position % 8
    
    if byte_index >= len(byte_array):
        raise ValueError(f"Bit position {bit_position} out of range for {len(data)} bytes")
    
    byte_array[byte_index] ^= (1 << (7 - bit_index))  # MSB first
    return bytes(byte_array)


def count_bits(value: int) -> int:
    """
    Count the number of set bits (population count).
    
    Args:
        value: Value to count bits in
    
    Returns:
        Number of 1 bits
    """
    count = 0
    while value:
        count += value & 1
        value >>= 1
    return count


def bytes_to_bits(data: bytes) -> str:
    """
    Convert bytes to binary string representation.
    
    Args:
        data: Bytes to convert
    
    Returns:
        Binary string (e.g., "10110101")
    """
    return ''.join(format(byte, '08b') for byte in data)


def bits_to_bytes(bits: str) -> bytes:
    """
    Convert binary string to bytes.
    
    Args:
        bits: Binary string (e.g., "10110101")
    
    Returns:
        Bytes
    
    Raises:
        ValueError: If bits string length is not multiple of 8
    """
    if len(bits) % 8 != 0:
        raise ValueError("Bits string length must be multiple of 8")
    
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte_array.append(int(bits[i:i+8], 2))
    return bytes(byte_array)


# ============================================================================
# Time Management
# ============================================================================

class SimulationClock:
    """
    Simulation clock for managing virtual time.
    
    The simulation uses virtual time that can run faster or slower than
    real time. This allows for fast-forward simulation and precise control
    over timing.
    """
    
    def __init__(self, start_time: float = 0.0, speed_multiplier: float = 1.0):
        """
        Initialize simulation clock.
        
        Args:
            start_time: Initial virtual time (seconds)
            speed_multiplier: Speed relative to real time (1.0 = real-time)
        """
        self._virtual_time = start_time
        self._real_start_time = time.time()
        self._speed_multiplier = speed_multiplier
        self._paused = False
        self._pause_time = 0.0
    
    def now(self) -> float:
        """
        Get current virtual time.
        
        Returns:
            Current virtual time in seconds
        """
        if self._paused:
            return self._virtual_time
        
        real_elapsed = time.time() - self._real_start_time
        return self._virtual_time + (real_elapsed * self._speed_multiplier)
    
    def advance(self, delta: float) -> None:
        """
        Manually advance virtual time.
        
        Used in discrete event simulation to jump to next event time.
        
        Args:
            delta: Time to advance (seconds)
        """
        self._virtual_time += delta
        self._real_start_time = time.time()
    
    def set_time(self, virtual_time: float) -> None:
        """
        Set virtual time to specific value.
        
        Args:
            virtual_time: New virtual time (seconds)
        """
        self._virtual_time = virtual_time
        self._real_start_time = time.time()
    
    def set_speed(self, multiplier: float) -> None:
        """
        Set simulation speed multiplier.
        
        Args:
            multiplier: Speed multiplier (1.0 = real-time, 10.0 = 10x faster)
        """
        # Update virtual time to current before changing speed
        self._virtual_time = self.now()
        self._speed_multiplier = multiplier
        self._real_start_time = time.time()
    
    def pause(self) -> None:
        """Pause the simulation clock."""
        if not self._paused:
            self._virtual_time = self.now()
            self._paused = True
            self._pause_time = time.time()
    
    def resume(self) -> None:
        """Resume the simulation clock."""
        if self._paused:
            self._paused = False
            self._real_start_time = time.time()
    
    def is_paused(self) -> bool:
        """Check if clock is paused."""
        return self._paused
    
    def reset(self, start_time: float = 0.0) -> None:
        """
        Reset the clock.
        
        Args:
            start_time: New start time (seconds)
        """
        self._virtual_time = start_time
        self._real_start_time = time.time()
        self._paused = False


def timestamp_to_iso(timestamp: float) -> str:
    """
    Convert Unix timestamp to ISO 8601 format.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
    
    Returns:
        ISO 8601 formatted string
    """
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(timestamp)) + \
           f'.{int((timestamp % 1) * 1000):03d}Z'


def iso_to_timestamp(iso_string: str) -> float:
    """
    Convert ISO 8601 format to Unix timestamp.
    
    Args:
        iso_string: ISO 8601 formatted string
    
    Returns:
        Unix timestamp (seconds since epoch)
    """
    import calendar
    
    # Handle with or without milliseconds
    if '.' in iso_string:
        time_part, ms_part = iso_string.rstrip('Z').split('.')
        ms = int(ms_part) / 1000.0
    else:
        time_part = iso_string.rstrip('Z')
        ms = 0.0
    
    struct_time = time.strptime(time_part, '%Y-%m-%dT%H:%M:%S')
    # Use timegm for UTC time instead of mktime (which uses local time)
    return calendar.timegm(struct_time) + ms


def ms_to_seconds(milliseconds: float) -> float:
    """Convert milliseconds to seconds."""
    return milliseconds / 1000.0


def seconds_to_ms(seconds: float) -> float:
    """Convert seconds to milliseconds."""
    return seconds * 1000.0


def us_to_seconds(microseconds: float) -> float:
    """Convert microseconds to seconds."""
    return microseconds / 1_000_000.0


def seconds_to_us(seconds: float) -> float:
    """Convert seconds to microseconds."""
    return seconds * 1_000_000.0
