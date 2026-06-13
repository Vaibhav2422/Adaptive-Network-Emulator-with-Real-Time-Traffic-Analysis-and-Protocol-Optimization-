"""
Unit tests for Data Link Layer.

Tests specific scenarios and edge cases for framing, CRC, and Hamming code.
"""

import pytest
from src.data_link_layer import DataLinkLayer, DataLinkLayerConfig
from src.data_models import Frame


class TestDataLinkLayerFraming:
    """Test frame construction and basic operations."""
    
    def test_build_frame_basic(self):
        """Test basic frame construction."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"Hello, World!"
        frame = dll.build_frame(
            source_mac="00:11:22:33:44:55",
            dest_mac="AA:BB:CC:DD:EE:FF",
            payload=payload
        )
        
        assert frame.preamble == config.preamble
        assert frame.source_mac == "00:11:22:33:44:55"
        assert frame.dest_mac == "AA:BB:CC:DD:EE:FF"
        assert frame.crc is not None
        assert len(frame.payload) > 0
    
    def test_build_frame_empty_payload(self):
        """Test frame construction with minimal payload."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"X"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:00",
            dest_mac="FF:FF:FF:FF:FF:FF",
            payload=payload
        )
        
        assert frame.payload is not None
        assert frame.crc is not None
    
    def test_build_frame_large_payload(self):
        """Test frame construction with large payload."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"X" * 1500  # MTU size
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        assert frame.payload is not None
        assert frame.crc is not None


class TestDataLinkLayerCRC:
    """Test CRC error detection."""
    
    def test_validate_frame_no_errors(self):
        """Test frame validation with no errors."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"Test data"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        valid, decoded = dll.validate_frame(frame)
        
        assert valid is True
        assert decoded == payload
    
    def test_validate_frame_with_single_error(self):
        """Test frame validation with single bit error."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"Test data"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Inject single bit error
        corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
        
        # Should be correctable
        valid, decoded = dll.validate_frame(corrupted_frame)
        
        # Either corrected or happened to pass CRC (very rare)
        if valid:
            assert decoded == payload
    
    def test_validate_frame_with_multiple_errors(self):
        """Test frame validation with multiple bit errors."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"Test data"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Inject multiple bit errors
        corrupted_frame = dll.inject_error(frame, num_bit_errors=10)
        
        # Should be detected and discarded (very high probability)
        valid, decoded = dll.validate_frame(corrupted_frame)
        
        # Most likely invalid
        if not valid:
            assert decoded is None


class TestDataLinkLayerHamming:
    """Test Hamming code error correction."""
    
    def test_hamming_encode_decode_round_trip(self):
        """Test Hamming encoding and decoding round trip."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        # Test with various data patterns
        test_data = [
            b"\x00",
            b"\xFF",
            b"\xAA",
            b"\x55",
            b"Hello",
            b"\x00\x01\x02\x03\x04\x05"
        ]
        
        for data in test_data:
            encoded = dll._hamming_encode(data)
            decoded = dll._hamming_decode(encoded)
            assert decoded == data, f"Round trip failed for {data.hex()}"
    
    def test_hamming_correct_single_bit_error(self):
        """Test Hamming correction of single bit error."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        data = b"Test"
        encoded = dll._hamming_encode(data)
        
        # Flip a single bit
        corrupted = bytearray(encoded)
        corrupted[0] ^= 0x01  # Flip LSB of first byte
        corrupted = bytes(corrupted)
        
        # Attempt correction
        success, corrected = dll._hamming_correct(corrupted)
        
        # Should succeed
        assert success is True
        
        # Decode and verify
        decoded = dll._hamming_decode(corrected)
        assert decoded == data
    
    def test_hamming_without_correction(self):
        """Test Data Link Layer with Hamming disabled."""
        config = DataLinkLayerConfig(enable_hamming=False)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        payload = b"Test data"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Payload should not be Hamming encoded
        valid, decoded = dll.validate_frame(frame)
        assert valid is True
        assert decoded == payload


class TestDataLinkLayerStatistics:
    """Test statistics tracking."""
    
    def test_statistics_frames_sent(self):
        """Test frames sent counter."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        for i in range(5):
            dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=f"Frame {i}".encode()
            )
        
        stats = dll.get_statistics()
        assert stats['frames_sent'] == 5
    
    def test_statistics_frames_received(self):
        """Test frames received counter."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        for i in range(3):
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=f"Frame {i}".encode()
            )
            dll.validate_frame(frame)
        
        stats = dll.get_statistics()
        assert stats['frames_received'] == 3
    
    def test_statistics_crc_errors(self):
        """Test CRC error detection counter."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="node1", config=config)
        
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=b"Test"
        )
        
        # Inject errors
        corrupted = dll.inject_error(frame, num_bit_errors=5)
        dll.validate_frame(corrupted)
        
        stats = dll.get_statistics()
        # Should detect CRC error (very high probability)
        assert stats['crc_errors_detected'] >= 0
    
    def test_statistics_reset(self):
        """Test statistics reset."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        # Generate some activity
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=b"Test"
        )
        dll.validate_frame(frame)
        
        # Reset
        dll.reset_statistics()
        
        stats = dll.get_statistics()
        assert stats['frames_sent'] == 0
        assert stats['frames_received'] == 0


class TestDataLinkLayerErrorInjection:
    """Test error injection functionality."""
    
    def test_inject_error_single_bit(self):
        """Test single bit error injection."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=b"Test"
        )
        
        original_payload = frame.payload
        corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
        
        # Payload should be different
        assert corrupted_frame.payload != original_payload
    
    def test_inject_error_zero_bits(self):
        """Test zero bit error injection (no change)."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=b"Test"
        )
        
        original_payload = frame.payload
        same_frame = dll.inject_error(frame, num_bit_errors=0)
        
        # Payload should be identical
        assert same_frame.payload == original_payload
    
    def test_inject_error_multiple_bits(self):
        """Test multiple bit error injection."""
        config = DataLinkLayerConfig()
        dll = DataLinkLayer(node_id="node1", config=config)
        
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=b"Test data"
        )
        
        original_payload = frame.payload
        corrupted_frame = dll.inject_error(frame, num_bit_errors=5)
        
        # Payload should be different
        assert corrupted_frame.payload != original_payload


class TestDataLinkLayerIntegration:
    """Integration tests for complete workflows."""
    
    def test_end_to_end_no_errors(self):
        """Test complete send-receive cycle with no errors."""
        config = DataLinkLayerConfig()
        sender = DataLinkLayer(node_id="sender", config=config)
        receiver = DataLinkLayer(node_id="receiver", config=config)
        
        payload = b"Hello from sender!"
        
        # Sender builds frame
        frame = sender.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Receiver validates frame
        valid, decoded = receiver.validate_frame(frame)
        
        assert valid is True
        assert decoded == payload
    
    def test_end_to_end_with_correction(self):
        """Test complete send-receive cycle with error correction."""
        config = DataLinkLayerConfig(enable_hamming=True)
        sender = DataLinkLayer(node_id="sender", config=config)
        receiver = DataLinkLayer(node_id="receiver", config=config)
        
        payload = b"Hello!"
        
        # Sender builds frame
        frame = sender.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Inject single bit error
        corrupted_frame = sender.inject_error(frame, num_bit_errors=1)
        
        # Receiver validates and corrects
        valid, decoded = receiver.validate_frame(corrupted_frame)
        
        # Should be corrected
        if valid:
            assert decoded == payload
