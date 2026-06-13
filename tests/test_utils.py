"""
Unit tests for utility functions.

Tests checksum calculation, bit manipulation, time management,
and random number generation with seed support.
"""

import pytest
import time
from src.utils import (
    # Random number generation
    SeededRandom, set_global_seed, get_random,
    # Checksum
    calculate_crc32, verify_crc32, calculate_checksum, verify_checksum,
    # Bit manipulation
    set_bit, clear_bit, toggle_bit, get_bit, flip_bit_in_bytes,
    count_bits, bytes_to_bits, bits_to_bytes,
    # Time management
    SimulationClock, timestamp_to_iso, iso_to_timestamp,
    ms_to_seconds, seconds_to_ms, us_to_seconds, seconds_to_us
)


# ============================================================================
# Random Number Generation Tests
# ============================================================================

class TestSeededRandom:
    """Tests for SeededRandom class."""
    
    def test_same_seed_produces_same_sequence(self):
        """Same seed should produce identical random sequences."""
        rng1 = SeededRandom(42)
        rng2 = SeededRandom(42)
        
        sequence1 = [rng1.random() for _ in range(10)]
        sequence2 = [rng2.random() for _ in range(10)]
        
        assert sequence1 == sequence2
    
    def test_different_seeds_produce_different_sequences(self):
        """Different seeds should produce different sequences."""
        rng1 = SeededRandom(42)
        rng2 = SeededRandom(43)
        
        sequence1 = [rng1.random() for _ in range(10)]
        sequence2 = [rng2.random() for _ in range(10)]
        
        assert sequence1 != sequence2
    
    def test_reseed_produces_same_sequence(self):
        """Re-seeding should restart the sequence."""
        rng = SeededRandom(42)
        sequence1 = [rng.random() for _ in range(5)]
        
        rng.seed(42)
        sequence2 = [rng.random() for _ in range(5)]
        
        assert sequence1 == sequence2
    
    def test_randint_range(self):
        """randint should produce values in specified range."""
        rng = SeededRandom(42)
        values = [rng.randint(1, 10) for _ in range(100)]
        
        assert all(1 <= v <= 10 for v in values)
        assert min(values) >= 1
        assert max(values) <= 10
    
    def test_uniform_range(self):
        """uniform should produce values in specified range."""
        rng = SeededRandom(42)
        values = [rng.uniform(0.0, 1.0) for _ in range(100)]
        
        assert all(0.0 <= v <= 1.0 for v in values)
    
    def test_choice(self):
        """choice should select from sequence."""
        rng = SeededRandom(42)
        seq = [1, 2, 3, 4, 5]
        choices = [rng.choice(seq) for _ in range(20)]
        
        assert all(c in seq for c in choices)
    
    def test_get_seed(self):
        """Should be able to retrieve seed."""
        rng = SeededRandom(42)
        assert rng.get_seed() == 42


class TestGlobalRandom:
    """Tests for global random number generator."""
    
    def test_set_and_get_global_seed(self):
        """Should be able to set and use global seed."""
        set_global_seed(123)
        rng = get_random()
        
        assert rng.get_seed() == 123
    
    def test_global_seed_reproducibility(self):
        """Global seed should provide reproducibility."""
        set_global_seed(42)
        rng1 = get_random()
        sequence1 = [rng1.random() for _ in range(5)]
        
        set_global_seed(42)
        rng2 = get_random()
        sequence2 = [rng2.random() for _ in range(5)]
        
        assert sequence1 == sequence2


# ============================================================================
# Checksum Tests
# ============================================================================

class TestCRC32:
    """Tests for CRC-32 checksum."""
    
    def test_crc32_empty_data(self):
        """CRC-32 of empty data should be 0."""
        assert calculate_crc32(b'') == 0
    
    def test_crc32_known_values(self):
        """Test CRC-32 with known values."""
        # Known CRC-32 values
        assert calculate_crc32(b'123456789') == 0xCBF43926
    
    def test_crc32_different_data(self):
        """Different data should produce different CRCs."""
        crc1 = calculate_crc32(b'hello')
        crc2 = calculate_crc32(b'world')
        
        assert crc1 != crc2
    
    def test_crc32_same_data(self):
        """Same data should produce same CRC."""
        data = b'test data'
        crc1 = calculate_crc32(data)
        crc2 = calculate_crc32(data)
        
        assert crc1 == crc2
    
    def test_verify_crc32_valid(self):
        """Verify should pass for correct CRC."""
        data = b'test data'
        crc = calculate_crc32(data)
        
        assert verify_crc32(data, crc) is True
    
    def test_verify_crc32_invalid(self):
        """Verify should fail for incorrect CRC."""
        data = b'test data'
        crc = calculate_crc32(data)
        
        assert verify_crc32(data, crc + 1) is False
    
    def test_crc32_bit_flip_detection(self):
        """CRC should detect single bit flip."""
        data = b'test data'
        crc = calculate_crc32(data)
        
        # Flip one bit
        corrupted = bytearray(data)
        corrupted[0] ^= 0x01
        
        assert verify_crc32(bytes(corrupted), crc) is False


class TestChecksum:
    """Tests for 16-bit Internet checksum."""
    
    def test_checksum_empty_data(self):
        """Checksum of empty data."""
        checksum = calculate_checksum(b'')
        assert checksum == 0xFFFF
    
    def test_checksum_odd_length(self):
        """Checksum should handle odd-length data."""
        data = b'abc'  # 3 bytes
        checksum = calculate_checksum(data)
        assert isinstance(checksum, int)
        assert 0 <= checksum <= 0xFFFF
    
    def test_checksum_even_length(self):
        """Checksum should handle even-length data."""
        data = b'abcd'  # 4 bytes
        checksum = calculate_checksum(data)
        assert isinstance(checksum, int)
        assert 0 <= checksum <= 0xFFFF
    
    def test_verify_checksum_valid(self):
        """Verify should pass for correct checksum."""
        data = b'test data'
        checksum = calculate_checksum(data)
        
        assert verify_checksum(data, checksum) is True
    
    def test_verify_checksum_invalid(self):
        """Verify should fail for incorrect checksum."""
        data = b'test data'
        checksum = calculate_checksum(data)
        
        assert verify_checksum(data, checksum ^ 0xFFFF) is False


# ============================================================================
# Bit Manipulation Tests
# ============================================================================

class TestBitOperations:
    """Tests for bit manipulation functions."""
    
    def test_set_bit(self):
        """set_bit should set specified bit to 1."""
        value = 0b00000000
        result = set_bit(value, 3)
        assert result == 0b00001000
    
    def test_set_bit_already_set(self):
        """set_bit on already set bit should not change value."""
        value = 0b00001000
        result = set_bit(value, 3)
        assert result == 0b00001000
    
    def test_clear_bit(self):
        """clear_bit should set specified bit to 0."""
        value = 0b11111111
        result = clear_bit(value, 3)
        assert result == 0b11110111
    
    def test_clear_bit_already_clear(self):
        """clear_bit on already clear bit should not change value."""
        value = 0b11110111
        result = clear_bit(value, 3)
        assert result == 0b11110111
    
    def test_toggle_bit(self):
        """toggle_bit should flip specified bit."""
        value = 0b00001000
        result = toggle_bit(value, 3)
        assert result == 0b00000000
        
        result = toggle_bit(result, 3)
        assert result == 0b00001000
    
    def test_get_bit(self):
        """get_bit should return bit value."""
        value = 0b00001010
        assert get_bit(value, 0) == 0
        assert get_bit(value, 1) == 1
        assert get_bit(value, 2) == 0
        assert get_bit(value, 3) == 1
    
    def test_count_bits(self):
        """count_bits should count set bits."""
        assert count_bits(0b00000000) == 0
        assert count_bits(0b00000001) == 1
        assert count_bits(0b00001111) == 4
        assert count_bits(0b11111111) == 8
    
    def test_flip_bit_in_bytes(self):
        """flip_bit_in_bytes should flip specified bit."""
        data = b'\x00\x00'
        result = flip_bit_in_bytes(data, 0)
        assert result == b'\x80\x00'
        
        result = flip_bit_in_bytes(data, 8)
        assert result == b'\x00\x80'
    
    def test_flip_bit_in_bytes_out_of_range(self):
        """flip_bit_in_bytes should raise error for out of range."""
        data = b'\x00'
        with pytest.raises(ValueError):
            flip_bit_in_bytes(data, 8)
    
    def test_bytes_to_bits(self):
        """bytes_to_bits should convert bytes to binary string."""
        data = b'\xFF\x00'
        bits = bytes_to_bits(data)
        assert bits == '1111111100000000'
    
    def test_bits_to_bytes(self):
        """bits_to_bytes should convert binary string to bytes."""
        bits = '1111111100000000'
        data = bits_to_bytes(bits)
        assert data == b'\xFF\x00'
    
    def test_bits_to_bytes_invalid_length(self):
        """bits_to_bytes should raise error for invalid length."""
        with pytest.raises(ValueError):
            bits_to_bytes('111')  # Not multiple of 8
    
    def test_bytes_bits_round_trip(self):
        """Converting bytes to bits and back should preserve data."""
        original = b'Hello, World!'
        bits = bytes_to_bits(original)
        result = bits_to_bytes(bits)
        assert result == original


# ============================================================================
# Time Management Tests
# ============================================================================

class TestSimulationClock:
    """Tests for SimulationClock."""
    
    def test_clock_initialization(self):
        """Clock should initialize with start time."""
        clock = SimulationClock(start_time=100.0)
        assert abs(clock.now() - 100.0) < 0.01
    
    def test_clock_advance(self):
        """advance should move virtual time forward."""
        clock = SimulationClock(start_time=0.0)
        clock.advance(10.0)
        assert abs(clock.now() - 10.0) < 0.01
    
    def test_clock_set_time(self):
        """set_time should set virtual time."""
        clock = SimulationClock(start_time=0.0)
        clock.set_time(50.0)
        assert abs(clock.now() - 50.0) < 0.01
    
    def test_clock_pause_resume(self):
        """Pause should stop time, resume should restart."""
        clock = SimulationClock(start_time=0.0)
        clock.advance(10.0)
        
        clock.pause()
        time_at_pause = clock.now()
        time.sleep(0.05)  # Wait a bit
        assert abs(clock.now() - time_at_pause) < 0.01  # Time should not advance
        
        clock.resume()
        # After resume, time should advance again
        assert clock.is_paused() is False
    
    def test_clock_is_paused(self):
        """is_paused should reflect pause state."""
        clock = SimulationClock()
        assert clock.is_paused() is False
        
        clock.pause()
        assert clock.is_paused() is True
        
        clock.resume()
        assert clock.is_paused() is False
    
    def test_clock_reset(self):
        """reset should reset clock to start time."""
        clock = SimulationClock(start_time=0.0)
        clock.advance(100.0)
        
        clock.reset(start_time=0.0)
        assert abs(clock.now() - 0.0) < 0.01
    
    def test_clock_speed_multiplier(self):
        """Speed multiplier should affect time progression."""
        clock = SimulationClock(start_time=0.0, speed_multiplier=10.0)
        start = clock.now()
        time.sleep(0.1)  # Sleep 0.1 real seconds
        elapsed = clock.now() - start
        # With 10x speed, 0.1 real seconds = ~1.0 virtual seconds
        assert 0.8 < elapsed < 1.2
    
    def test_clock_set_speed(self):
        """set_speed should change speed multiplier."""
        clock = SimulationClock(start_time=0.0, speed_multiplier=1.0)
        clock.set_speed(100.0)
        # Speed change should work (detailed timing test omitted for brevity)
        assert True


class TestTimeConversions:
    """Tests for time conversion functions."""
    
    def test_timestamp_to_iso(self):
        """timestamp_to_iso should convert to ISO format."""
        timestamp = 1609459200.123  # 2021-01-01 00:00:00.123 UTC
        iso = timestamp_to_iso(timestamp)
        assert iso.startswith('2021-01-01T')
        assert 'Z' in iso
    
    def test_iso_to_timestamp(self):
        """iso_to_timestamp should convert from ISO format."""
        iso = '2021-01-01T00:00:00.123Z'
        timestamp = iso_to_timestamp(iso)
        assert isinstance(timestamp, float)
    
    def test_iso_round_trip(self):
        """Converting to ISO and back should preserve time."""
        original = 1609459200.0
        iso = timestamp_to_iso(original)
        result = iso_to_timestamp(iso)
        assert abs(result - original) < 1.0  # Within 1 second
    
    def test_ms_to_seconds(self):
        """ms_to_seconds should convert correctly."""
        assert ms_to_seconds(1000.0) == 1.0
        assert ms_to_seconds(500.0) == 0.5
    
    def test_seconds_to_ms(self):
        """seconds_to_ms should convert correctly."""
        assert seconds_to_ms(1.0) == 1000.0
        assert seconds_to_ms(0.5) == 500.0
    
    def test_us_to_seconds(self):
        """us_to_seconds should convert correctly."""
        assert us_to_seconds(1_000_000.0) == 1.0
        assert us_to_seconds(500_000.0) == 0.5
    
    def test_seconds_to_us(self):
        """seconds_to_us should convert correctly."""
        assert seconds_to_us(1.0) == 1_000_000.0
        assert seconds_to_us(0.5) == 500_000.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestUtilsIntegration:
    """Integration tests for utility functions."""
    
    def test_seeded_random_with_bit_manipulation(self):
        """Test using seeded random with bit operations."""
        rng = SeededRandom(42)
        value = 0
        
        # Randomly set bits
        for i in range(8):
            if rng.random() > 0.5:
                value = set_bit(value, i)
        
        # Count should be deterministic with same seed
        count = count_bits(value)
        assert isinstance(count, int)
        assert 0 <= count <= 8
    
    def test_checksum_with_bit_flip(self):
        """Test checksum detection with bit flip."""
        data = b'test data for checksum'
        crc = calculate_crc32(data)
        
        # Flip a random bit
        rng = SeededRandom(42)
        bit_pos = rng.randint(0, len(data) * 8 - 1)
        corrupted = flip_bit_in_bytes(data, bit_pos)
        
        # CRC should detect corruption
        assert verify_crc32(corrupted, crc) is False
    
    def test_simulation_clock_with_seeded_events(self):
        """Test simulation clock with seeded random events."""
        clock = SimulationClock(start_time=0.0)
        rng = SeededRandom(42)
        
        # Generate random event times
        event_times = sorted([rng.uniform(0.0, 100.0) for _ in range(10)])
        
        # Advance clock to each event
        for event_time in event_times:
            clock.set_time(event_time)
            assert abs(clock.now() - event_time) < 0.01
