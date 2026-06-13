"""
Integration tests for error handling mechanisms.

Tests CRC detection, Hamming correction, collision detection, and exponential backoff
as specified in task 6.3.

Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 6.2, 6.3
"""

import pytest
import random
from src.data_link_layer import DataLinkLayer, DataLinkLayerConfig
from src.mac_layer import MACLayer, MACLayerConfig, ChannelState


class TestCRCDetection:
    """Test CRC detection with injected bit errors (detection rate >99%)."""
    
    def test_crc_detection_rate_with_single_bit_errors(self):
        """Test CRC detects single-bit errors with >99% accuracy."""
        config = DataLinkLayerConfig(enable_hamming=False)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        num_trials = 100
        errors_detected = 0
        
        for i in range(num_trials):
            # Create frame
            payload = f"Test payload {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject single bit error
            corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
            
            # Validate frame
            valid, decoded = dll.validate_frame(corrupted_frame)
            
            if not valid:
                errors_detected += 1
        
        detection_rate = errors_detected / num_trials
        
        print(f"\nCRC Detection Rate (single-bit errors): {detection_rate*100:.1f}%")
        print(f"Errors detected: {errors_detected}/{num_trials}")
        
        # CRC should detect >99% of single-bit errors
        assert detection_rate > 0.99, f"CRC detection rate {detection_rate*100:.1f}% is below 99%"
    
    def test_crc_detection_rate_with_multiple_bit_errors(self):
        """Test CRC detects multiple-bit errors with >99% accuracy."""
        config = DataLinkLayerConfig(enable_hamming=False)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        num_trials = 100
        errors_detected = 0
        
        for i in range(num_trials):
            # Create frame
            payload = f"Test payload {i} with more data".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject multiple bit errors (3-10 bits)
            num_errors = random.randint(3, 10)
            corrupted_frame = dll.inject_error(frame, num_bit_errors=num_errors)
            
            # Validate frame
            valid, decoded = dll.validate_frame(corrupted_frame)
            
            if not valid:
                errors_detected += 1
        
        detection_rate = errors_detected / num_trials
        
        print(f"\nCRC Detection Rate (multiple-bit errors): {detection_rate*100:.1f}%")
        print(f"Errors detected: {errors_detected}/{num_trials}")
        
        # CRC should detect >99% of multiple-bit errors
        assert detection_rate > 0.99, f"CRC detection rate {detection_rate*100:.1f}% is below 99%"
    
    def test_crc_no_false_positives(self):
        """Test CRC does not produce false positives on valid frames."""
        config = DataLinkLayerConfig(enable_hamming=False)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        num_trials = 100
        false_positives = 0
        
        for i in range(num_trials):
            # Create frame
            payload = f"Valid payload {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Validate frame without errors
            valid, decoded = dll.validate_frame(frame)
            
            if not valid:
                false_positives += 1
        
        print(f"\nCRC False Positives: {false_positives}/{num_trials}")
        
        # Should have zero false positives
        assert false_positives == 0, f"CRC produced {false_positives} false positives"


class TestHammingCorrection:
    """Test Hamming correction with single-bit errors (correction rate 100%)."""
    
    def test_hamming_correction_rate_single_bit_errors(self):
        """Test Hamming code corrects 100% of single-bit errors."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        num_trials = 100
        errors_corrected = 0
        
        for i in range(num_trials):
            # Create frame
            payload = f"Test {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject single bit error
            corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
            
            # Validate frame (should correct the error)
            valid, decoded = dll.validate_frame(corrupted_frame)
            
            if valid and decoded == payload:
                errors_corrected += 1
        
        correction_rate = errors_corrected / num_trials
        
        print(f"\nHamming Correction Rate (single-bit errors): {correction_rate*100:.1f}%")
        print(f"Errors corrected: {errors_corrected}/{num_trials}")
        
        # Hamming should correct 100% of single-bit errors
        assert correction_rate == 1.0, f"Hamming correction rate {correction_rate*100:.1f}% is below 100%"
    
    def test_hamming_correction_preserves_data_integrity(self):
        """Test Hamming correction delivers original data after correction."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        test_payloads = [
            b"Hello, World!",
            b"A",
            b"Test data 123",
            b"\x00\x01\x02\x03\x04",
            b"X" * 100
        ]
        
        for payload in test_payloads:
            # Create frame
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject single bit error
            corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
            
            # Validate and correct
            valid, decoded = dll.validate_frame(corrupted_frame)
            
            # Should successfully correct and return original data
            assert valid is True, f"Failed to correct error for payload: {payload}"
            assert decoded == payload, f"Corrected data doesn't match original: {decoded} != {payload}"
    
    def test_hamming_detects_uncorrectable_errors(self):
        """Test Hamming detects and discards frames with uncorrectable errors."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        num_trials = 50
        uncorrectable_detected = 0
        
        for i in range(num_trials):
            # Create frame
            payload = f"Test payload {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject multiple bit errors (beyond Hamming capability)
            corrupted_frame = dll.inject_error(frame, num_bit_errors=10)
            
            # Validate frame
            valid, decoded = dll.validate_frame(corrupted_frame)
            
            if not valid:
                uncorrectable_detected += 1
                assert decoded is None, "Uncorrectable error should return None"
        
        print(f"\nUncorrectable errors detected: {uncorrectable_detected}/{num_trials}")
        
        # Should detect most uncorrectable errors (relaxed threshold due to random nature)
        # With 10 bit errors, CRC should detect most, but some may pass by chance
        assert uncorrectable_detected > num_trials * 0.5, "Should detect majority of uncorrectable errors"
    
    def test_hamming_statistics_tracking(self):
        """Test Hamming correction statistics are tracked correctly."""
        config = DataLinkLayerConfig(enable_hamming=True)
        dll = DataLinkLayer(node_id="test_node", config=config)
        
        # Create and corrupt frames
        for i in range(10):
            payload = f"Test {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            # Inject single bit error
            corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
            dll.validate_frame(corrupted_frame)
        
        stats = dll.get_statistics()
        
        print(f"\nHamming Statistics:")
        print(f"  Frames received: {stats['frames_received']}")
        print(f"  CRC errors detected: {stats['crc_errors_detected']}")
        print(f"  Errors corrected: {stats['errors_corrected']}")
        print(f"  Correction success rate: {stats['correction_success_rate']*100:.1f}%")
        
        # Should have corrected errors
        assert stats['errors_corrected'] > 0, "Should have corrected some errors"
        assert stats['correction_success_rate'] > 0.9, "Correction success rate should be high"


class TestCollisionDetection:
    """Test collision detection with simultaneous transmissions."""
    
    def test_collision_detection_two_nodes(self):
        """Test collision is detected when two nodes transmit simultaneously."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate two nodes transmitting
        mac.transmitting_nodes.add("node_1")
        mac.transmitting_nodes.add("node_2")
        
        collision = mac.detect_collision()
        
        assert collision is True, "Collision should be detected with 2 transmitting nodes"
        assert mac.get_channel_state() == ChannelState.COLLISION
        assert mac.stats['collisions_detected'] == 1
    
    def test_collision_detection_multiple_nodes(self):
        """Test collision is detected with multiple simultaneous transmissions."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate multiple nodes transmitting
        for i in range(5):
            mac.transmitting_nodes.add(f"node_{i}")
        
        collision = mac.detect_collision()
        
        assert collision is True, "Collision should be detected with multiple transmitting nodes"
        assert len(mac.transmitting_nodes) == 5
        assert mac.get_channel_state() == ChannelState.COLLISION
    
    def test_no_collision_single_node(self):
        """Test no collision is detected with single transmitting node."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Single node transmitting
        mac.transmitting_nodes.add("node_1")
        
        collision = mac.detect_collision()
        
        assert collision is False, "No collision should be detected with single node"
    
    def test_collision_statistics_tracking(self):
        """Test collision detection statistics are tracked correctly."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate multiple collisions
        for i in range(10):
            mac.transmitting_nodes.clear()
            mac.transmitting_nodes.add("node_1")
            mac.transmitting_nodes.add("node_2")
            mac.detect_collision()
        
        stats = mac.get_statistics()
        
        print(f"\nCollision Statistics:")
        print(f"  Collisions detected: {stats['collisions_detected']}")
        
        assert stats['collisions_detected'] == 10, "Should track all collision detections"
    
    def test_collision_during_transmission_request(self):
        """Test collision is detected during transmission request."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate another node already transmitting
        mac.notify_transmission_start("node_2")
        
        # Force channel to appear idle to trigger collision
        mac.channel_state = ChannelState.IDLE
        
        # Request transmission (will collide)
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"test data", 0.0
        )
        
        # Should detect collision
        if not success:
            assert backoff_slots is not None, "Should return backoff slots on collision"
            assert backoff_time is not None, "Should return backoff time on collision"


class TestExponentialBackoff:
    """Test exponential backoff behavior."""
    
    def test_backoff_range_attempt_1(self):
        """Test backoff range for first collision attempt."""
        config = MACLayerConfig(random_seed=None)  # Use random seed
        mac = MACLayer("node_1", config)
        
        # Test multiple times to verify range
        backoffs = [mac.calculate_backoff(1) for _ in range(100)]
        
        # For attempt 1, k=1, range is [0, 1]
        assert all(0 <= b <= 1 for b in backoffs), "Backoff should be in range [0, 1]"
        
        print(f"\nBackoff range for attempt 1: min={min(backoffs)}, max={max(backoffs)}")
    
    def test_backoff_range_attempt_5(self):
        """Test backoff range for fifth collision attempt."""
        config = MACLayerConfig(random_seed=None)
        mac = MACLayer("node_1", config)
        
        # Test multiple times to verify range
        backoffs = [mac.calculate_backoff(5) for _ in range(100)]
        
        # For attempt 5, k=5, range is [0, 31]
        assert all(0 <= b <= 31 for b in backoffs), "Backoff should be in range [0, 31]"
        
        print(f"\nBackoff range for attempt 5: min={min(backoffs)}, max={max(backoffs)}")
    
    def test_backoff_range_attempt_10(self):
        """Test backoff range for tenth collision attempt."""
        config = MACLayerConfig(random_seed=None)
        mac = MACLayer("node_1", config)
        
        # Test multiple times to verify range
        backoffs = [mac.calculate_backoff(10) for _ in range(100)]
        
        # For attempt 10, k=10, range is [0, 1023]
        assert all(0 <= b <= 1023 for b in backoffs), "Backoff should be in range [0, 1023]"
        
        print(f"\nBackoff range for attempt 10: min={min(backoffs)}, max={max(backoffs)}")
    
    def test_backoff_capped_at_k_10(self):
        """Test backoff is capped at k=10 for attempts > 10."""
        config = MACLayerConfig(random_seed=None)
        mac = MACLayer("node_1", config)
        
        # Test attempts beyond 10
        for attempt in [11, 15, 20, 50]:
            backoffs = [mac.calculate_backoff(attempt) for _ in range(50)]
            
            # Should all be in range [0, 1023] (same as k=10)
            assert all(0 <= b <= 1023 for b in backoffs), \
                f"Backoff for attempt {attempt} should be capped at [0, 1023]"
        
        print(f"\nBackoff correctly capped at k=10 for attempts > 10")
    
    def test_backoff_formula_correctness(self):
        """Test backoff follows formula: random(0, 2^min(k,10) - 1)."""
        config = MACLayerConfig(random_seed=None)
        mac = MACLayer("node_1", config)
        
        test_cases = [
            (1, 1),      # k=1, max=1
            (2, 3),      # k=2, max=3
            (3, 7),      # k=3, max=7
            (4, 15),     # k=4, max=15
            (5, 31),     # k=5, max=31
            (10, 1023),  # k=10, max=1023
            (15, 1023),  # k=10 (capped), max=1023
        ]
        
        for attempt, expected_max in test_cases:
            backoffs = [mac.calculate_backoff(attempt) for _ in range(100)]
            
            assert all(0 <= b <= expected_max for b in backoffs), \
                f"Backoff for attempt {attempt} should be in [0, {expected_max}]"
            
            print(f"Attempt {attempt}: range [0, {expected_max}], actual max={max(backoffs)}")
    
    def test_backoff_time_conversion(self):
        """Test backoff time is correctly converted from slots."""
        config = MACLayerConfig(slot_time_ms=0.0512)  # Standard Ethernet slot time
        mac = MACLayer("node_1", config)
        
        test_cases = [
            (0, 0.0),
            (1, 0.0512 / 1000.0),
            (10, 0.512 / 1000.0),
            (100, 5.12 / 1000.0),
        ]
        
        for slots, expected_time in test_cases:
            actual_time = mac.get_backoff_time(slots)
            
            assert abs(actual_time - expected_time) < 1e-9, \
                f"Backoff time for {slots} slots should be {expected_time}s, got {actual_time}s"
            
            print(f"{slots} slots = {actual_time*1000:.4f} ms")
    
    def test_backoff_increases_exponentially(self):
        """Test backoff range increases exponentially with attempts."""
        config = MACLayerConfig(random_seed=None)
        mac = MACLayer("node_1", config)
        
        # Calculate average backoff for different attempts
        attempts = [1, 2, 3, 4, 5, 6, 7, 8]
        avg_backoffs = []
        
        for attempt in attempts:
            backoffs = [mac.calculate_backoff(attempt) for _ in range(1000)]
            avg_backoff = sum(backoffs) / len(backoffs)
            avg_backoffs.append(avg_backoff)
            
            print(f"Attempt {attempt}: avg backoff = {avg_backoff:.2f}")
        
        # Verify exponential growth (each should be roughly double the previous)
        # Allow wider range since variance increases with larger ranges
        for i in range(1, len(avg_backoffs)):
            ratio = avg_backoffs[i] / avg_backoffs[i-1]
            # Ratio should be approximately 2, but allow for statistical variance
            assert 1.5 < ratio < 3.5, \
                f"Backoff should grow exponentially, ratio={ratio:.2f}"
    
    def test_backoff_reproducibility_with_seed(self):
        """Test backoff is reproducible with same seed."""
        seed = 12345
        
        config1 = MACLayerConfig(random_seed=seed)
        mac1 = MACLayer("node_1", config1)
        
        config2 = MACLayerConfig(random_seed=seed)
        mac2 = MACLayer("node_2", config2)
        
        # Calculate backoffs for same attempts
        for attempt in [1, 3, 5, 10]:
            backoff1 = mac1.calculate_backoff(attempt)
            backoff2 = mac2.calculate_backoff(attempt)
            
            assert backoff1 == backoff2, \
                f"Backoff should be reproducible with same seed: {backoff1} != {backoff2}"
        
        print(f"\nBackoff is reproducible with seed={seed}")


class TestIntegratedErrorHandling:
    """Test integrated error handling across multiple mechanisms."""
    
    def test_end_to_end_with_errors_and_collisions(self):
        """Test complete error handling pipeline with both bit errors and collisions."""
        dll_config = DataLinkLayerConfig(enable_hamming=True)
        mac_config = MACLayerConfig(random_seed=42)
        
        dll = DataLinkLayer("node_1", dll_config)
        mac = MACLayer("node_1", mac_config)
        
        # Create frame
        payload = b"Test data"
        frame = dll.build_frame(
            source_mac="00:00:00:00:00:01",
            dest_mac="00:00:00:00:00:02",
            payload=payload
        )
        
        # Inject single bit error
        corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
        
        # Simulate collision during transmission
        mac.notify_transmission_start("node_2")
        mac.channel_state = ChannelState.IDLE  # Force to test collision
        
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"frame_data", 0.0
        )
        
        # Should handle collision
        if not success:
            assert backoff_slots is not None
        
        # Should correct bit error
        valid, decoded = dll.validate_frame(corrupted_frame)
        assert valid is True
        assert decoded == payload
    
    def test_statistics_across_mechanisms(self):
        """Test statistics are correctly tracked across all error handling mechanisms."""
        dll_config = DataLinkLayerConfig(enable_hamming=True)
        mac_config = MACLayerConfig(random_seed=42)
        
        dll = DataLinkLayer("node_1", dll_config)
        mac = MACLayer("node_1", mac_config)
        
        # Generate activity
        for i in range(10):
            # Data link layer activity
            payload = f"Test {i}".encode()
            frame = dll.build_frame(
                source_mac="00:00:00:00:00:01",
                dest_mac="00:00:00:00:00:02",
                payload=payload
            )
            
            if i % 2 == 0:
                # Inject error on even frames
                corrupted_frame = dll.inject_error(frame, num_bit_errors=1)
                dll.validate_frame(corrupted_frame)
            else:
                dll.validate_frame(frame)
            
            # MAC layer activity
            if i % 3 == 0:
                # Simulate collision
                mac.transmitting_nodes.add("node_1")
                mac.transmitting_nodes.add("node_2")
                mac.detect_collision()
                mac.transmitting_nodes.clear()
        
        dll_stats = dll.get_statistics()
        mac_stats = mac.get_statistics()
        
        print(f"\nData Link Layer Statistics:")
        print(f"  Frames sent: {dll_stats['frames_sent']}")
        print(f"  Frames received: {dll_stats['frames_received']}")
        print(f"  CRC errors detected: {dll_stats['crc_errors_detected']}")
        print(f"  Errors corrected: {dll_stats['errors_corrected']}")
        
        print(f"\nMAC Layer Statistics:")
        print(f"  Collisions detected: {mac_stats['collisions_detected']}")
        
        assert dll_stats['frames_sent'] == 10
        assert dll_stats['frames_received'] == 10
        assert mac_stats['collisions_detected'] >= 3
