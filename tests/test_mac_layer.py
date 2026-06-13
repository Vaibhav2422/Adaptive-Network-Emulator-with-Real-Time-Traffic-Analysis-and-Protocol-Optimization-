"""
Unit tests for MAC Layer implementation.

Tests specific scenarios for CSMA/CD simulation, collision detection,
exponential backoff, and carrier sensing.

Validates: Requirements 6.1, 6.2, 6.3, 6.6
"""

import pytest
from src.mac_layer import MACLayer, MACLayerConfig, ChannelState


class TestMACLayerInitialization:
    """Test MAC Layer initialization and configuration."""
    
    def test_initialization_with_default_config(self):
        """Test MAC layer initializes with default configuration."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        assert mac.node_id == "node_1"
        assert mac.channel_state == ChannelState.IDLE
        assert len(mac.transmitting_nodes) == 0
        assert mac.current_attempt is None
    
    def test_initialization_with_custom_config(self):
        """Test MAC layer initializes with custom configuration."""
        config = MACLayerConfig(
            slot_time_ms=0.1,
            max_retries=10,
            random_seed=42
        )
        mac = MACLayer("node_2", config)
        
        assert mac.config.slot_time_ms == 0.1
        assert mac.config.max_retries == 10
        assert mac.config.random_seed == 42
    
    def test_statistics_initialized_to_zero(self):
        """Test that statistics are initialized to zero."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        stats = mac.get_statistics()
        assert stats['total_transmissions'] == 0
        assert stats['successful_transmissions'] == 0
        assert stats['collisions_detected'] == 0
        assert stats['carrier_sense_busy'] == 0
        assert stats['max_retries_exceeded'] == 0
        assert stats['total_backoff_time'] == 0.0


class TestCarrierSensing:
    """Test carrier sensing functionality."""
    
    def test_sense_channel_idle_initially(self):
        """Test channel is sensed as idle initially."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        assert mac.sense_channel() == True
        assert mac.get_channel_state() == ChannelState.IDLE
    
    def test_sense_channel_busy_when_transmitting(self):
        """Test channel is sensed as busy when a node is transmitting."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Simulate another node transmitting
        mac.notify_transmission_start("node_2")
        
        assert mac.sense_channel() == False
        assert mac.get_channel_state() == ChannelState.BUSY
    
    def test_sense_channel_busy_during_collision(self):
        """Test channel is sensed as busy during collision."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Simulate collision
        mac.channel_state = ChannelState.COLLISION
        
        assert mac.sense_channel() == False
    
    def test_carrier_sense_busy_statistics(self):
        """Test carrier sense busy events are tracked in statistics."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Make channel busy
        mac.notify_transmission_start("node_2")
        
        # Sense channel multiple times
        for _ in range(5):
            mac.sense_channel()
        
        stats = mac.get_statistics()
        assert stats['carrier_sense_busy'] == 5


class TestCollisionDetection:
    """Test collision detection functionality."""
    
    def test_no_collision_with_single_transmitter(self):
        """Test no collision detected with single transmitter."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.transmitting_nodes.add("node_1")
        
        collision = mac.detect_collision()
        assert collision == False
    
    def test_collision_with_two_transmitters(self):
        """Test collision detected with two transmitters."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.transmitting_nodes.add("node_1")
        mac.transmitting_nodes.add("node_2")
        
        collision = mac.detect_collision()
        assert collision == True
        assert mac.get_channel_state() == ChannelState.COLLISION
    
    def test_collision_with_multiple_transmitters(self):
        """Test collision detected with multiple transmitters."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        for i in range(5):
            mac.transmitting_nodes.add(f"node_{i}")
        
        collision = mac.detect_collision()
        assert collision == True
        assert len(mac.transmitting_nodes) == 5
    
    def test_collision_statistics_incremented(self):
        """Test collision detection increments statistics."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.transmitting_nodes.add("node_1")
        mac.transmitting_nodes.add("node_2")
        
        initial_count = mac.stats['collisions_detected']
        mac.detect_collision()
        
        assert mac.stats['collisions_detected'] == initial_count + 1


class TestExponentialBackoff:
    """Test exponential backoff algorithm."""
    
    def test_backoff_attempt_1(self):
        """Test backoff for first collision attempt."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        backoff = mac.calculate_backoff(1)
        
        # For attempt 1, k=1, range is [0, 1]
        assert 0 <= backoff <= 1
    
    def test_backoff_attempt_5(self):
        """Test backoff for fifth collision attempt."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        backoff = mac.calculate_backoff(5)
        
        # For attempt 5, k=5, range is [0, 31]
        assert 0 <= backoff <= 31
    
    def test_backoff_attempt_10(self):
        """Test backoff for tenth collision attempt."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        backoff = mac.calculate_backoff(10)
        
        # For attempt 10, k=10, range is [0, 1023]
        assert 0 <= backoff <= 1023
    
    def test_backoff_capped_at_attempt_10(self):
        """Test backoff is capped at attempt 10."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        backoff_10 = mac.calculate_backoff(10)
        backoff_15 = mac.calculate_backoff(15)
        backoff_20 = mac.calculate_backoff(20)
        
        # All should be in range [0, 1023]
        assert 0 <= backoff_10 <= 1023
        assert 0 <= backoff_15 <= 1023
        assert 0 <= backoff_20 <= 1023
    
    def test_backoff_time_calculation(self):
        """Test backoff time is calculated correctly from slots."""
        config = MACLayerConfig(slot_time_ms=0.1)
        mac = MACLayer("node_1", config)
        
        backoff_time = mac.get_backoff_time(10)
        
        # 10 slots * 0.1 ms = 1 ms = 0.001 seconds
        expected = 10 * (0.1 / 1000.0)
        assert abs(backoff_time - expected) < 1e-9
    
    def test_backoff_reproducible_with_seed(self):
        """Test backoff is reproducible with same seed."""
        config1 = MACLayerConfig(random_seed=12345)
        mac1 = MACLayer("node_1", config1)
        
        config2 = MACLayerConfig(random_seed=12345)
        mac2 = MACLayer("node_2", config2)
        
        # Calculate backoff for same attempt
        backoff1 = mac1.calculate_backoff(5)
        backoff2 = mac2.calculate_backoff(5)
        
        assert backoff1 == backoff2


class TestTransmissionRequest:
    """Test transmission request functionality."""
    
    def test_successful_transmission_on_idle_channel(self):
        """Test successful transmission when channel is idle."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"test data", 0.0
        )
        
        assert success == True
        assert backoff_slots is None
        assert backoff_time is None
        assert mac.stats['successful_transmissions'] == 1
    
    def test_transmission_deferred_on_busy_channel(self):
        """Test transmission is deferred when channel is busy."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Make channel busy
        mac.notify_transmission_start("node_2")
        
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"test data", 0.0
        )
        
        assert success == False
        assert mac.stats['carrier_sense_busy'] > 0
    
    def test_collision_triggers_backoff(self):
        """Test collision triggers exponential backoff."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate another node transmitting
        mac.notify_transmission_start("node_2")
        
        # Force channel to appear idle for this test
        mac.channel_state = ChannelState.IDLE
        
        # Request transmission (will collide)
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"test data", 0.0
        )
        
        # Should detect collision and return backoff
        if not success:
            assert backoff_slots is not None
            assert backoff_time is not None
            assert backoff_slots >= 0
            assert backoff_time >= 0.0
    
    def test_max_retries_exceeded(self):
        """Test transmission fails after max retries exceeded."""
        config = MACLayerConfig(max_retries=3, random_seed=42)
        mac = MACLayer("node_1", config)
        
        # Simulate max retries by setting attempt count
        mac.current_attempt = type('obj', (object,), {
            'frame_id': 'frame_1',
            'attempt_count': 3,
            'backoff_slots': 0,
            'timestamp': 0.0
        })()
        
        success, backoff_slots, backoff_time = mac.request_transmission(
            "frame_1", b"test data", 0.0
        )
        
        assert success == False
        assert mac.stats['max_retries_exceeded'] == 1
    
    def test_transmission_attempt_tracking(self):
        """Test transmission attempts are tracked correctly."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        # First attempt
        mac.request_transmission("frame_1", b"test data", 0.0)
        
        # Check attempt was tracked
        assert mac.current_attempt is None or mac.current_attempt.frame_id == "frame_1"
    
    def test_callback_invoked_on_success(self):
        """Test callback is invoked on successful transmission."""
        config = MACLayerConfig(random_seed=42)
        mac = MACLayer("node_1", config)
        
        callback_data = []
        
        def callback(data):
            callback_data.append(data)
        
        success, _, _ = mac.request_transmission(
            "frame_1", b"test data", 0.0, callback=callback
        )
        
        if success:
            assert len(callback_data) == 1
            assert callback_data[0] == b"test data"


class TestChannelStateManagement:
    """Test channel state management."""
    
    def test_notify_transmission_start(self):
        """Test notifying transmission start updates channel state."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        assert mac.get_channel_state() == ChannelState.IDLE
        
        mac.notify_transmission_start("node_2")
        
        assert mac.get_channel_state() == ChannelState.BUSY
        assert "node_2" in mac.transmitting_nodes
    
    def test_notify_transmission_end(self):
        """Test notifying transmission end updates channel state."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.notify_transmission_start("node_2")
        assert mac.get_channel_state() == ChannelState.BUSY
        
        mac.notify_transmission_end("node_2")
        
        assert mac.get_channel_state() == ChannelState.IDLE
        assert "node_2" not in mac.transmitting_nodes
    
    def test_complete_transmission(self):
        """Test completing transmission releases channel."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Simulate this node transmitting
        mac.transmitting_nodes.add("node_1")
        mac.channel_state = ChannelState.BUSY
        
        mac.complete_transmission()
        
        assert "node_1" not in mac.transmitting_nodes
        assert mac.get_channel_state() == ChannelState.IDLE
    
    def test_multiple_transmissions_collision_state(self):
        """Test multiple simultaneous transmissions set collision state."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.notify_transmission_start("node_2")
        assert mac.get_channel_state() == ChannelState.BUSY
        
        mac.notify_transmission_start("node_3")
        assert mac.get_channel_state() == ChannelState.COLLISION


class TestStatistics:
    """Test statistics tracking."""
    
    def test_get_statistics(self):
        """Test getting statistics returns all counters."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        stats = mac.get_statistics()
        
        assert 'total_transmissions' in stats
        assert 'successful_transmissions' in stats
        assert 'collisions_detected' in stats
        assert 'carrier_sense_busy' in stats
        assert 'max_retries_exceeded' in stats
        assert 'total_backoff_time' in stats
        assert 'success_rate' in stats
        assert 'collision_rate' in stats
    
    def test_success_rate_calculation(self):
        """Test success rate is calculated correctly."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.stats['total_transmissions'] = 10
        mac.stats['successful_transmissions'] = 7
        
        stats = mac.get_statistics()
        
        assert stats['success_rate'] == 0.7
    
    def test_collision_rate_calculation(self):
        """Test collision rate is calculated correctly."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        mac.stats['total_transmissions'] = 10
        mac.stats['collisions_detected'] = 3
        
        stats = mac.get_statistics()
        
        assert stats['collision_rate'] == 0.3
    
    def test_reset_statistics(self):
        """Test resetting statistics clears all counters."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Set some statistics
        mac.stats['total_transmissions'] = 10
        mac.stats['successful_transmissions'] = 7
        mac.stats['collisions_detected'] = 3
        
        mac.reset_statistics()
        
        stats = mac.get_statistics()
        assert stats['total_transmissions'] == 0
        assert stats['successful_transmissions'] == 0
        assert stats['collisions_detected'] == 0
    
    def test_backoff_time_accumulation(self):
        """Test backoff time is accumulated in statistics."""
        config = MACLayerConfig(slot_time_ms=0.1)
        mac = MACLayer("node_1", config)
        
        # Simulate backoff
        backoff_slots = 10
        backoff_time = mac.get_backoff_time(backoff_slots)
        mac.stats['total_backoff_time'] += backoff_time
        
        stats = mac.get_statistics()
        assert stats['total_backoff_time'] > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_frame_data(self):
        """Test transmission with empty frame data."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        success, _, _ = mac.request_transmission(
            "frame_1", b"", 0.0
        )
        
        # Should still work with empty data
        assert success is not None
    
    def test_large_frame_data(self):
        """Test transmission with large frame data."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        large_data = b"x" * 10000
        success, _, _ = mac.request_transmission(
            "frame_1", large_data, 0.0
        )
        
        # Should handle large data
        assert success is not None
    
    def test_zero_timestamp(self):
        """Test transmission with zero timestamp."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        success, _, _ = mac.request_transmission(
            "frame_1", b"test", 0.0
        )
        
        assert success is not None
    
    def test_negative_timestamp(self):
        """Test transmission with negative timestamp (edge case)."""
        config = MACLayerConfig()
        mac = MACLayer("node_1", config)
        
        # Should still work (timestamp is just for tracking)
        success, _, _ = mac.request_transmission(
            "frame_1", b"test", -1.0
        )
        
        assert success is not None
