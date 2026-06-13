"""
Integration test for frame transmission through layers.

Tests the complete data flow from application data through Physical Layer
and back up, verifying that headers are added/removed correctly at each layer
and data integrity is preserved.

Task 6.2: Integration test: Frame transmission through layers
- Test frame transmission: Application data → Physical Layer → back up
- Verify headers added/removed correctly at each layer
- Test with various payload sizes (1 byte, 1KB, 64KB)
- Expected: Data integrity preserved, headers correct
"""

import pytest
from src.physical_layer import PhysicalLayer, PhysicalLayerConfig
from src.mac_layer import MACLayer, MACLayerConfig
from src.data_link_layer import DataLinkLayer, DataLinkLayerConfig
from src.data_models import Frame


class TestFrameTransmissionIntegration:
    """Integration tests for frame transmission through layers."""
    
    @pytest.fixture
    def physical_layer(self):
        """Create a Physical Layer instance with no errors."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,  # 100 Mbps
            propagation_delay_ms=1.0,
            loss_rate=0.0,  # No loss for integration test
            bit_error_rate=0.0,  # No errors for integration test
            random_seed=42
        )
        return PhysicalLayer(config)
    
    @pytest.fixture
    def mac_layer(self):
        """Create a MAC Layer instance."""
        config = MACLayerConfig(
            slot_time_ms=0.0512,
            max_retries=16,
            random_seed=42
        )
        return MACLayer(node_id="node1", config=config)
    
    @pytest.fixture
    def data_link_layer(self):
        """Create a Data Link Layer instance."""
        config = DataLinkLayerConfig(
            enable_hamming=True,
            random_seed=42
        )
        return DataLinkLayer(node_id="node1", config=config)
    
    def test_frame_transmission_1_byte(self, physical_layer, mac_layer, data_link_layer):
        """
        Test frame transmission with 1 byte payload.
        
        Verifies:
        - Data Link Layer adds frame structure (preamble, header, CRC, trailer)
        - Physical Layer transmits the frame
        - Data Link Layer validates and extracts original payload
        - Original data is preserved
        """
        # Original application data
        original_data = b'X'
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Step 1: Data Link Layer - Build frame (encapsulation)
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        
        # Verify frame structure
        assert frame.preamble == data_link_layer.config.preamble
        assert frame.source_mac == source_mac
        assert frame.dest_mac == dest_mac
        assert frame.crc != 0  # CRC should be calculated
        assert len(frame.payload) > 0  # Payload should be encoded
        
        # Step 2: MAC Layer - Request transmission (carrier sense)
        # For integration test, assume channel is idle
        assert mac_layer.sense_channel() is True
        
        # Step 3: Physical Layer - Transmit frame
        # Serialize frame for transmission
        frame_bytes = self._serialize_frame(frame)
        success, transmitted_data, delay = physical_layer.transmit(
            frame_bytes, dest_mac
        )
        
        # Verify transmission succeeded
        assert success is True
        assert transmitted_data is not None
        assert delay > 0  # Should have some delay
        
        # Step 4: Physical Layer - Receive (at destination)
        received_frame_bytes = transmitted_data
        
        # Step 5: Data Link Layer - Deserialize and validate frame (decapsulation)
        received_frame = self._deserialize_frame(received_frame_bytes)
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        # Verify frame validation succeeded
        assert valid is True
        assert decoded_payload is not None
        
        # Step 6: Verify data integrity - original data preserved
        assert decoded_payload == original_data
        
        # Verify headers were added and removed correctly
        assert received_frame.source_mac == source_mac
        assert received_frame.dest_mac == dest_mac
    
    def test_frame_transmission_1kb(self, physical_layer, mac_layer, data_link_layer):
        """
        Test frame transmission with 1KB payload.
        
        Verifies the same flow with a larger payload to ensure
        the system handles typical packet sizes correctly.
        """
        # Original application data - 1KB
        original_data = b'A' * 1024
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Encapsulation: Data Link Layer builds frame
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        
        # Verify frame structure
        assert frame.source_mac == source_mac
        assert frame.dest_mac == dest_mac
        assert frame.crc != 0
        
        # MAC Layer carrier sense
        assert mac_layer.sense_channel() is True
        
        # Physical Layer transmission
        frame_bytes = self._serialize_frame(frame)
        success, transmitted_data, delay = physical_layer.transmit(
            frame_bytes, dest_mac
        )
        
        assert success is True
        assert transmitted_data is not None
        
        # Calculate expected delay for 1KB payload
        # Frame overhead: preamble (8) + header (~40) + CRC (4) + trailer (1)
        # Plus Hamming encoding overhead (roughly 2x for encoded payload)
        expected_min_delay = physical_layer.calculate_transmission_delay(1024)
        assert delay >= expected_min_delay
        
        # Decapsulation: Data Link Layer validates and extracts payload
        received_frame = self._deserialize_frame(transmitted_data)
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        assert valid is True
        assert decoded_payload == original_data
    
    def test_frame_transmission_64kb(self, physical_layer, mac_layer, data_link_layer):
        """
        Test frame transmission with 64KB payload.
        
        Verifies the system handles large payloads correctly,
        which is important for file transfer and bulk data transmission.
        """
        # Original application data - 64KB
        original_data = b'B' * (64 * 1024)
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Encapsulation: Data Link Layer builds frame
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        
        # Verify frame structure
        assert frame.source_mac == source_mac
        assert frame.dest_mac == dest_mac
        assert frame.crc != 0
        
        # MAC Layer carrier sense
        assert mac_layer.sense_channel() is True
        
        # Physical Layer transmission
        frame_bytes = self._serialize_frame(frame)
        success, transmitted_data, delay = physical_layer.transmit(
            frame_bytes, dest_mac
        )
        
        assert success is True
        assert transmitted_data is not None
        
        # Verify delay is proportional to payload size
        expected_min_delay = physical_layer.calculate_transmission_delay(64 * 1024)
        assert delay >= expected_min_delay
        
        # Decapsulation: Data Link Layer validates and extracts payload
        received_frame = self._deserialize_frame(transmitted_data)
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        assert valid is True
        assert decoded_payload == original_data
    
    def test_headers_added_removed_correctly(self, physical_layer, mac_layer, data_link_layer):
        """
        Test that headers are added and removed correctly at each layer.
        
        Verifies:
        - Data Link Layer adds: preamble, MAC addresses, CRC, trailer
        - Physical Layer adds: transmission metadata (delay)
        - On receive path, headers are stripped in reverse order
        - Original payload is recovered without corruption
        """
        original_data = b'Test payload for header verification'
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Track data size at each layer
        original_size = len(original_data)
        
        # Data Link Layer encapsulation
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        
        # Verify Data Link Layer added headers
        assert frame.preamble is not None and len(frame.preamble) > 0
        assert frame.source_mac == source_mac
        assert frame.dest_mac == dest_mac
        assert frame.crc != 0
        
        # Payload should be larger due to Hamming encoding
        assert len(frame.payload) >= original_size
        
        # Serialize frame (includes all headers)
        frame_bytes = self._serialize_frame(frame)
        frame_size = len(frame_bytes)
        
        # Frame should be larger than original data due to headers
        assert frame_size > original_size
        
        # Physical Layer transmission
        success, transmitted_data, delay = physical_layer.transmit(
            frame_bytes, dest_mac
        )
        
        assert success is True
        
        # Physical Layer should preserve frame size
        assert len(transmitted_data) == frame_size
        
        # Decapsulation: Remove headers in reverse order
        received_frame = self._deserialize_frame(transmitted_data)
        
        # Verify frame headers are intact
        assert received_frame.preamble == frame.preamble
        assert received_frame.source_mac == source_mac
        assert received_frame.dest_mac == dest_mac
        assert received_frame.crc == frame.crc
        
        # Data Link Layer validation removes headers and decodes payload
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        assert valid is True
        
        # Final payload should match original exactly
        assert len(decoded_payload) == original_size
        assert decoded_payload == original_data
    
    def test_data_integrity_with_various_patterns(self, physical_layer, mac_layer, data_link_layer):
        """
        Test data integrity with various data patterns.
        
        Tests different byte patterns to ensure the encoding/decoding
        process doesn't introduce artifacts or corruption.
        """
        test_patterns = [
            b'\x00' * 100,  # All zeros
            b'\xFF' * 100,  # All ones
            b'\xAA' * 100,  # Alternating pattern
            bytes(range(256)),  # All byte values
            b'The quick brown fox jumps over the lazy dog',  # ASCII text
        ]
        
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        for pattern in test_patterns:
            # Encapsulation
            frame = data_link_layer.build_frame(source_mac, dest_mac, pattern)
            
            # Transmission
            frame_bytes = self._serialize_frame(frame)
            success, transmitted_data, _ = physical_layer.transmit(
                frame_bytes, dest_mac
            )
            
            assert success is True
            
            # Decapsulation
            received_frame = self._deserialize_frame(transmitted_data)
            valid, decoded_payload = data_link_layer.validate_frame(received_frame)
            
            # Verify integrity
            assert valid is True
            assert decoded_payload == pattern, f"Data integrity failed for pattern: {pattern[:20]}"
    
    def test_frame_transmission_with_mac_statistics(self, physical_layer, mac_layer, data_link_layer):
        """
        Test frame transmission and verify MAC layer statistics are updated.
        
        Verifies that the MAC layer correctly tracks transmission attempts
        and updates statistics.
        """
        original_data = b'Test data for MAC statistics'
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Reset MAC statistics
        mac_layer.reset_statistics()
        
        # Build frame
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        frame_bytes = self._serialize_frame(frame)
        
        # Request transmission through MAC layer
        success, backoff_slots, backoff_time = mac_layer.request_transmission(
            frame_id="test_frame_1",
            frame_data=frame_bytes,
            timestamp=0.0
        )
        
        # Should succeed (no collision in single-node test)
        assert success is True
        assert backoff_slots is None
        assert backoff_time is None
        
        # Complete transmission
        mac_layer.complete_transmission()
        
        # Verify MAC statistics
        stats = mac_layer.get_statistics()
        assert stats['total_transmissions'] == 1
        assert stats['successful_transmissions'] == 1
        assert stats['collisions_detected'] == 0
        
        # Transmit through physical layer
        success, transmitted_data, _ = physical_layer.transmit(
            frame_bytes, dest_mac
        )
        
        assert success is True
        
        # Verify data integrity
        received_frame = self._deserialize_frame(transmitted_data)
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        assert valid is True
        assert decoded_payload == original_data
    
    # Helper methods for frame serialization/deserialization
    
    def _serialize_frame(self, frame: Frame) -> bytes:
        """
        Serialize a frame to bytes for transmission.
        
        This simulates the process of converting the frame structure
        into a byte stream for physical transmission.
        """
        # Simple serialization: concatenate all frame components
        frame_bytes = (
            frame.preamble +
            frame.source_mac.encode() +
            frame.dest_mac.encode() +
            frame.payload +
            frame.crc.to_bytes(4, byteorder='big')
        )
        return frame_bytes
    
    def _deserialize_frame(self, frame_bytes: bytes) -> Frame:
        """
        Deserialize bytes back into a Frame object.
        
        This simulates the process of parsing received bytes
        back into the frame structure.
        """
        # Parse frame components
        preamble_len = 8  # Standard preamble length
        preamble = frame_bytes[:preamble_len]
        
        # MAC addresses are variable length strings, but we know the format
        # For simplicity, assume fixed encoding length
        mac_len = len("AA:BB:CC:DD:EE:01".encode())
        offset = preamble_len
        
        source_mac = frame_bytes[offset:offset + mac_len].decode()
        offset += mac_len
        
        dest_mac = frame_bytes[offset:offset + mac_len].decode()
        offset += mac_len
        
        # CRC is last 4 bytes
        crc = int.from_bytes(frame_bytes[-4:], byteorder='big')
        
        # Payload is everything between MAC addresses and CRC
        payload = frame_bytes[offset:-4]
        
        return Frame(
            preamble=preamble,
            source_mac=source_mac,
            dest_mac=dest_mac,
            payload=payload,
            crc=crc,
            error_corrected=False
        )


class TestFrameTransmissionWithErrors:
    """Integration tests for frame transmission with error conditions."""
    
    @pytest.fixture
    def physical_layer_with_errors(self):
        """Create a Physical Layer instance with bit errors."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=1.0,
            loss_rate=0.0,
            bit_error_rate=0.0001,  # Small error rate
            random_seed=42
        )
        return PhysicalLayer(config)
    
    @pytest.fixture
    def data_link_layer(self):
        """Create a Data Link Layer instance."""
        config = DataLinkLayerConfig(
            enable_hamming=True,
            random_seed=42
        )
        return DataLinkLayer(node_id="node1", config=config)
    
    def test_frame_transmission_with_error_detection(self, physical_layer_with_errors, data_link_layer):
        """
        Test that CRC error detection works when bit errors are introduced.
        
        Note: With a very small bit error rate, most frames will be error-free,
        but this test verifies the error detection mechanism is in place.
        """
        original_data = b'Test data for error detection'
        source_mac = "AA:BB:CC:DD:EE:01"
        dest_mac = "AA:BB:CC:DD:EE:02"
        
        # Build frame
        frame = data_link_layer.build_frame(source_mac, dest_mac, original_data)
        frame_bytes = self._serialize_frame(frame)
        
        # Transmit with potential bit errors
        success, transmitted_data, _ = physical_layer_with_errors.transmit(
            frame_bytes, dest_mac
        )
        
        assert success is True
        
        # Receive and validate
        received_frame = self._deserialize_frame(transmitted_data)
        valid, decoded_payload = data_link_layer.validate_frame(received_frame)
        
        # Frame should either be valid (no errors) or invalid (errors detected)
        # If valid, payload should match original
        if valid:
            assert decoded_payload == original_data
        else:
            # Errors were detected and couldn't be corrected
            assert decoded_payload is None
    
    def _serialize_frame(self, frame: Frame) -> bytes:
        """Serialize a frame to bytes for transmission."""
        frame_bytes = (
            frame.preamble +
            frame.source_mac.encode() +
            frame.dest_mac.encode() +
            frame.payload +
            frame.crc.to_bytes(4, byteorder='big')
        )
        return frame_bytes
    
    def _deserialize_frame(self, frame_bytes: bytes) -> Frame:
        """Deserialize bytes back into a Frame object."""
        preamble_len = 8
        preamble = frame_bytes[:preamble_len]
        
        mac_len = len("AA:BB:CC:DD:EE:01".encode())
        offset = preamble_len
        
        source_mac = frame_bytes[offset:offset + mac_len].decode()
        offset += mac_len
        
        dest_mac = frame_bytes[offset:offset + mac_len].decode()
        offset += mac_len
        
        crc = int.from_bytes(frame_bytes[-4:], byteorder='big')
        payload = frame_bytes[offset:-4]
        
        return Frame(
            preamble=preamble,
            source_mac=source_mac,
            dest_mac=dest_mac,
            payload=payload,
            crc=crc,
            error_corrected=False
        )
