"""
Data Link Layer implementation for the Adaptive Network Emulator.

Provides framing, error detection (CRC), and error correction (Hamming Code).
This layer is responsible for reliable transmission over the physical medium
by detecting and correcting errors.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from src.data_models import Frame
from src.utils import calculate_crc32, verify_crc32, flip_bit_in_bytes


@dataclass
class DataLinkLayerConfig:
    """Configuration for Data Link Layer."""
    preamble: bytes = b'\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xD5'  # Standard Ethernet preamble
    trailer: bytes = b'\xFF'  # Simple trailer marker
    enable_hamming: bool = True  # Enable Hamming code error correction
    random_seed: Optional[int] = None


class DataLinkLayer:
    """
    Data Link Layer implementing framing, CRC error detection, and Hamming error correction.
    
    Features:
    - Frame construction with preamble, header, payload, CRC, and trailer
    - CRC-32 error detection
    - Hamming code error correction for single-bit errors
    - Frame validation
    - Error injection for testing
    
    Frame Structure:
    ┌──────────┬──────────┬─────────┬──────────┬──────────┐
    │ Preamble │  Header  │ Payload │  CRC     │  Trailer │
    │ (8 bytes)│ (varies) │ (data)  │ (4 bytes)│ (1 byte) │
    └──────────┴──────────┴─────────┴──────────┴──────────┘
    """
    
    def __init__(self, node_id: str, config: DataLinkLayerConfig):
        """
        Initialize Data Link Layer.
        
        Args:
            node_id: Identifier for this node
            config: Data link layer configuration
        """
        self.node_id = node_id
        self.config = config
        self.logger = logging.getLogger(f"emulator.data_link_layer.{node_id}")
        
        # Statistics
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'crc_errors_detected': 0,
            'errors_corrected': 0,
            'uncorrectable_errors': 0,
            'frames_discarded': 0
        }
        
        self.logger.info(
            f"Data Link Layer initialized: hamming_enabled={config.enable_hamming}"
        )
    
    def build_frame(self, source_mac: str, dest_mac: str, payload: bytes) -> Frame:
        """
        Construct a frame with preamble, header, payload, CRC, and trailer.
        
        The frame structure includes:
        - Preamble: For synchronization (8 bytes)
        - Header: Source and destination MAC addresses
        - Payload: Data from upper layer
        - CRC: 32-bit checksum for error detection
        - Trailer: End-of-frame marker (1 byte)
        
        Args:
            source_mac: Source MAC address
            dest_mac: Destination MAC address
            payload: Payload data
        
        Returns:
            Constructed Frame object
        
        Validates: Requirements 5.1, 5.2
        """
        # Apply Hamming code to payload if enabled
        if self.config.enable_hamming:
            encoded_payload = self._hamming_encode(payload)
        else:
            encoded_payload = payload
        
        # Calculate CRC over header and encoded payload
        # Header consists of source and dest MAC addresses
        header_data = source_mac.encode() + dest_mac.encode()
        crc_data = header_data + encoded_payload
        crc = calculate_crc32(crc_data)
        
        # Create frame
        frame = Frame(
            preamble=self.config.preamble,
            source_mac=source_mac,
            dest_mac=dest_mac,
            payload=encoded_payload,
            crc=crc,
            error_corrected=False
        )
        
        self.stats['frames_sent'] += 1
        self.logger.debug(
            f"Frame built: src={source_mac}, dest={dest_mac}, "
            f"payload_size={len(payload)} bytes, crc={crc:08x}"
        )
        
        return frame
    
    def validate_frame(self, frame: Frame) -> Tuple[bool, Optional[bytes]]:
        """
        Validate a received frame by checking CRC and attempting error correction.
        
        Process:
        1. Verify CRC checksum
        2. If CRC fails, attempt Hamming code error correction
        3. If correction succeeds, re-verify CRC
        4. Return validation result and corrected payload
        
        Args:
            frame: Frame to validate
        
        Returns:
            Tuple of (valid, payload):
            - valid: True if frame is valid (or was corrected)
            - payload: Decoded payload (None if frame is invalid)
        
        Validates: Requirements 5.4, 5.5, 5.6, 5.8, 5.9
        """
        self.stats['frames_received'] += 1
        
        # Calculate CRC over header and payload
        header_data = frame.source_mac.encode() + frame.dest_mac.encode()
        crc_data = header_data + frame.payload
        
        # Verify CRC
        if verify_crc32(crc_data, frame.crc):
            # CRC valid - decode payload
            if self.config.enable_hamming:
                payload = self._hamming_decode(frame.payload)
            else:
                payload = frame.payload
            
            self.logger.debug(
                f"Frame valid: src={frame.source_mac}, dest={frame.dest_mac}, "
                f"payload_size={len(payload)} bytes"
            )
            return True, payload
        
        # CRC failed - attempt error correction
        self.stats['crc_errors_detected'] += 1
        self.logger.warning(
            f"CRC error detected: src={frame.source_mac}, dest={frame.dest_mac}"
        )
        
        if not self.config.enable_hamming:
            # No error correction available
            self.stats['frames_discarded'] += 1
            self.logger.error("Frame discarded: no error correction enabled")
            return False, None
        
        # Attempt Hamming code error correction
        corrected, corrected_payload = self._hamming_correct(frame.payload)
        
        if not corrected:
            # Uncorrectable error
            self.stats['uncorrectable_errors'] += 1
            self.stats['frames_discarded'] += 1
            self.logger.error(
                f"Uncorrectable error: frame discarded, src={frame.source_mac}"
            )
            return False, None
        
        # Error corrected - verify CRC with corrected data
        corrected_crc_data = header_data + corrected_payload
        if not verify_crc32(corrected_crc_data, frame.crc):
            # CRC still fails after correction
            self.stats['uncorrectable_errors'] += 1
            self.stats['frames_discarded'] += 1
            self.logger.error(
                f"CRC verification failed after correction: frame discarded"
            )
            return False, None
        
        # Successfully corrected
        self.stats['errors_corrected'] += 1
        frame.error_corrected = True
        
        # Decode corrected payload
        payload = self._hamming_decode(corrected_payload)
        
        self.logger.info(
            f"Error corrected: src={frame.source_mac}, dest={frame.dest_mac}"
        )
        return True, payload
    
    def inject_error(self, frame: Frame, num_bit_errors: int = 1) -> Frame:
        """
        Inject bit errors into a frame for testing.
        
        This method flips random bits in the frame payload to simulate
        transmission errors. Used for testing error detection and correction.
        
        Args:
            frame: Frame to inject errors into
            num_bit_errors: Number of bits to flip
        
        Returns:
            Frame with errors injected
        
        Validates: Requirements 5.7
        """
        import random
        
        if num_bit_errors == 0:
            return frame
        
        # Create a copy of the frame
        corrupted_payload = bytearray(frame.payload)
        
        # Flip random bits
        payload_bits = len(corrupted_payload) * 8
        bit_positions = random.sample(range(payload_bits), min(num_bit_errors, payload_bits))
        
        for bit_pos in bit_positions:
            byte_idx = bit_pos // 8
            bit_idx = bit_pos % 8
            corrupted_payload[byte_idx] ^= (1 << bit_idx)
        
        # Create new frame with corrupted payload
        corrupted_frame = Frame(
            preamble=frame.preamble,
            source_mac=frame.source_mac,
            dest_mac=frame.dest_mac,
            payload=bytes(corrupted_payload),
            crc=frame.crc,  # Keep original CRC to trigger error detection
            error_corrected=False
        )
        
        self.logger.debug(
            f"Injected {num_bit_errors} bit error(s) into frame"
        )
        
        return corrupted_frame
    
    def _hamming_encode(self, data: bytes) -> bytes:
        """
        Encode data with Hamming code for error correction.
        
        Implements Hamming(7,4) code which can correct single-bit errors.
        Each 4 data bits are encoded into 7 bits (4 data + 3 parity).
        
        Args:
            data: Data to encode
        
        Returns:
            Encoded data with parity bits
        
        Validates: Requirements 5.3, 5.6
        """
        # For simplicity, we'll encode each byte independently
        # In a real implementation, this would be more sophisticated
        encoded = bytearray()
        
        for byte in data:
            # Split byte into two nibbles (4 bits each)
            high_nibble = (byte >> 4) & 0x0F
            low_nibble = byte & 0x0F
            
            # Encode each nibble with Hamming(7,4)
            high_encoded = self._hamming_encode_nibble(high_nibble)
            low_encoded = self._hamming_encode_nibble(low_nibble)
            
            # Pack into bytes (7 bits each, total 14 bits = 2 bytes with 2 bits unused)
            encoded_word = (high_encoded << 7) | low_encoded
            encoded.append((encoded_word >> 8) & 0xFF)
            encoded.append(encoded_word & 0xFF)
        
        return bytes(encoded)
    
    def _hamming_encode_nibble(self, nibble: int) -> int:
        """
        Encode a 4-bit nibble with Hamming(7,4) code.
        
        Hamming(7,4) positions:
        - Position 1 (p1): Parity bit covering positions 1,3,5,7
        - Position 2 (p2): Parity bit covering positions 2,3,6,7
        - Position 3 (d1): Data bit 1
        - Position 4 (p4): Parity bit covering positions 4,5,6,7
        - Position 5 (d2): Data bit 2
        - Position 6 (d3): Data bit 3
        - Position 7 (d4): Data bit 4
        
        Args:
            nibble: 4-bit data value
        
        Returns:
            7-bit encoded value
        """
        # Extract data bits
        d1 = (nibble >> 3) & 1
        d2 = (nibble >> 2) & 1
        d3 = (nibble >> 1) & 1
        d4 = nibble & 1
        
        # Calculate parity bits
        p1 = d1 ^ d2 ^ d4  # Covers positions 3,5,7
        p2 = d1 ^ d3 ^ d4  # Covers positions 3,6,7
        p4 = d2 ^ d3 ^ d4  # Covers positions 5,6,7
        
        # Construct 7-bit code: p1 p2 d1 p4 d2 d3 d4
        encoded = (p1 << 6) | (p2 << 5) | (d1 << 4) | (p4 << 3) | (d2 << 2) | (d3 << 1) | d4
        
        return encoded
    
    def _hamming_decode(self, encoded_data: bytes) -> bytes:
        """
        Decode Hamming-encoded data.
        
        Args:
            encoded_data: Hamming-encoded data
        
        Returns:
            Decoded original data
        """
        decoded = bytearray()
        
        # Process two bytes at a time (one encoded byte)
        for i in range(0, len(encoded_data), 2):
            if i + 1 >= len(encoded_data):
                break
            
            # Extract two 7-bit codes
            encoded_word = (encoded_data[i] << 8) | encoded_data[i + 1]
            high_encoded = (encoded_word >> 7) & 0x7F
            low_encoded = encoded_word & 0x7F
            
            # Decode each nibble
            high_nibble = self._hamming_decode_nibble(high_encoded)
            low_nibble = self._hamming_decode_nibble(low_encoded)
            
            # Combine nibbles into byte
            decoded.append((high_nibble << 4) | low_nibble)
        
        return bytes(decoded)
    
    def _hamming_decode_nibble(self, encoded: int) -> int:
        """
        Decode a Hamming(7,4) encoded nibble.
        
        Args:
            encoded: 7-bit encoded value
        
        Returns:
            4-bit decoded value
        """
        # Extract bits: p1 p2 d1 p4 d2 d3 d4
        p1 = (encoded >> 6) & 1
        p2 = (encoded >> 5) & 1
        d1 = (encoded >> 4) & 1
        p4 = (encoded >> 3) & 1
        d2 = (encoded >> 2) & 1
        d3 = (encoded >> 1) & 1
        d4 = encoded & 1
        
        # Reconstruct nibble from data bits
        nibble = (d1 << 3) | (d2 << 2) | (d3 << 1) | d4
        
        return nibble
    
    def _hamming_correct(self, encoded_data: bytes) -> Tuple[bool, bytes]:
        """
        Attempt to correct errors in Hamming-encoded data.
        
        Detects and corrects single-bit errors using Hamming code syndrome.
        Returns False if errors are uncorrectable (multiple bit errors).
        
        Args:
            encoded_data: Potentially corrupted Hamming-encoded data
        
        Returns:
            Tuple of (success, corrected_data):
            - success: True if correction succeeded or no errors found
            - corrected_data: Corrected data (or original if no errors)
        
        Validates: Requirements 5.6, 5.7, 5.8, 5.9
        """
        corrected = bytearray()
        
        # Process two bytes at a time
        for i in range(0, len(encoded_data), 2):
            if i + 1 >= len(encoded_data):
                break
            
            # Extract two 7-bit codes
            encoded_word = (encoded_data[i] << 8) | encoded_data[i + 1]
            high_encoded = (encoded_word >> 7) & 0x7F
            low_encoded = encoded_word & 0x7F
            
            # Correct each nibble
            high_corrected, high_success = self._hamming_correct_nibble(high_encoded)
            low_corrected, low_success = self._hamming_correct_nibble(low_encoded)
            
            if not (high_success and low_success):
                # Uncorrectable error detected
                return False, encoded_data
            
            # Pack corrected codes back
            corrected_word = (high_corrected << 7) | low_corrected
            corrected.append((corrected_word >> 8) & 0xFF)
            corrected.append(corrected_word & 0xFF)
        
        return True, bytes(corrected)
    
    def _hamming_correct_nibble(self, encoded: int) -> Tuple[int, bool]:
        """
        Correct a single Hamming(7,4) encoded nibble.
        
        Uses syndrome calculation to detect and correct single-bit errors.
        
        Args:
            encoded: 7-bit encoded value (possibly corrupted)
        
        Returns:
            Tuple of (corrected_value, success):
            - corrected_value: Corrected 7-bit value
            - success: True if correction succeeded (0 or 1 bit error)
        """
        # Extract bits
        p1 = (encoded >> 6) & 1
        p2 = (encoded >> 5) & 1
        d1 = (encoded >> 4) & 1
        p4 = (encoded >> 3) & 1
        d2 = (encoded >> 2) & 1
        d3 = (encoded >> 1) & 1
        d4 = encoded & 1
        
        # Calculate syndrome
        s1 = p1 ^ d1 ^ d2 ^ d4  # Check positions 1,3,5,7
        s2 = p2 ^ d1 ^ d3 ^ d4  # Check positions 2,3,6,7
        s4 = p4 ^ d2 ^ d3 ^ d4  # Check positions 4,5,6,7
        
        syndrome = (s4 << 2) | (s2 << 1) | s1
        
        if syndrome == 0:
            # No error detected
            return encoded, True
        
        # Single-bit error at position indicated by syndrome
        # Syndrome value directly gives the error position (1-7)
        error_position = syndrome
        
        if error_position > 7:
            # Invalid syndrome - uncorrectable
            return encoded, False
        
        # Correct the bit at error_position (counting from right, 1-indexed)
        corrected = encoded ^ (1 << (7 - error_position))
        
        return corrected, True
    
    def get_statistics(self) -> dict:
        """
        Get Data Link Layer statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['frames_received'] > 0:
            stats['error_rate'] = (
                stats['crc_errors_detected'] / stats['frames_received']
            )
            stats['correction_success_rate'] = (
                stats['errors_corrected'] / 
                max(stats['crc_errors_detected'], 1)
            )
        else:
            stats['error_rate'] = 0.0
            stats['correction_success_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'crc_errors_detected': 0,
            'errors_corrected': 0,
            'uncorrectable_errors': 0,
            'frames_discarded': 0
        }
        self.logger.debug("Statistics reset")
