"""
Unit tests for Physical Layer implementation.

Tests delay calculations, loss simulation, and bit error injection.

Validates: Requirements 6.4
"""

import pytest
from src.physical_layer import PhysicalLayer, PhysicalLayerConfig


class TestPhysicalLayerDelayCalculations:
    """Test delay calculation functionality."""
    
    def test_transmission_delay_calculation(self):
        """Test transmission delay is calculated correctly based on size and bit rate."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,  # 100 Mbps
            propagation_delay_ms=0.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Test with 1000 bytes
        # Expected: (1000 * 8 bits) / (100_000_000 bps) = 0.00008 seconds = 0.08 ms
        delay = layer.calculate_transmission_delay(1000)
        assert abs(delay - 0.00008) < 1e-9
    
    def test_transmission_delay_different_sizes(self):
        """Test transmission delay scales with packet size."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,  # 100 Mbps
            propagation_delay_ms=0.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Larger packet should have proportionally larger delay
        delay_small = layer.calculate_transmission_delay(100)
        delay_large = layer.calculate_transmission_delay(1000)
        
        assert abs(delay_large - delay_small * 10) < 1e-9
    
    def test_propagation_delay(self):
        """Test propagation delay is returned correctly."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,  # 10 ms
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Expected: 10 ms = 0.01 seconds
        delay = layer.get_propagation_delay()
        assert abs(delay - 0.01) < 1e-9
    
    def test_total_delay(self):
        """Test total delay is sum of transmission and propagation delays."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,  # 100 Mbps
            propagation_delay_ms=10.0,  # 10 ms
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # For 1000 bytes:
        # Transmission: 0.00008 s = 0.08 ms
        # Propagation: 0.01 s = 10 ms
        # Total: 10.08 ms = 0.01008 s
        total_delay = layer.get_total_delay(1000)
        expected = 0.01008
        assert abs(total_delay - expected) < 1e-6
    
    def test_delay_with_different_bit_rates(self):
        """Test delay changes with different bit rates."""
        # 100 Mbps
        config1 = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=0.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer1 = PhysicalLayer(config1)
        
        # 10 Mbps (10x slower)
        config2 = PhysicalLayerConfig(
            bit_rate_bps=10_000_000,
            propagation_delay_ms=0.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer2 = PhysicalLayer(config2)
        
        delay1 = layer1.calculate_transmission_delay(1000)
        delay2 = layer2.calculate_transmission_delay(1000)
        
        # Slower bit rate should have 10x longer delay
        assert abs(delay2 - delay1 * 10) < 1e-9


class TestPhysicalLayerLossSimulation:
    """Test packet loss simulation functionality."""
    
    def test_no_loss_with_zero_rate(self):
        """Test that no packets are lost when loss rate is 0."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,  # No loss
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Transmit 100 packets, all should succeed
        data = b"test data"
        successes = 0
        for _ in range(100):
            success, _, _ = layer.transmit(data, "dest1")
            if success:
                successes += 1
        
        assert successes == 100
    
    def test_all_loss_with_100_percent_rate(self):
        """Test that all packets are lost when loss rate is 1.0."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=1.0,  # 100% loss
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Transmit 100 packets, all should fail
        data = b"test data"
        failures = 0
        for _ in range(100):
            success, _, _ = layer.transmit(data, "dest1")
            if not success:
                failures += 1
        
        assert failures == 100
    
    def test_loss_rate_approximately_correct(self):
        """Test that loss rate is approximately correct over many transmissions."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.3,  # 30% loss
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Transmit 1000 packets
        data = b"test data"
        successes = 0
        for _ in range(1000):
            success, _, _ = layer.transmit(data, "dest1")
            if success:
                successes += 1
        
        # Expected: ~700 successes (70% success rate)
        # Allow 5% tolerance
        expected_successes = 700
        assert 650 <= successes <= 750
    
    def test_dropped_packet_returns_none(self):
        """Test that dropped packets return None for data."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=1.0,  # Force drop
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        data = b"test data"
        success, transmitted_data, delay = layer.transmit(data, "dest1")
        
        assert not success
        assert transmitted_data is None
        assert delay > 0  # Delay is still calculated
    
    def test_set_loss_rate(self):
        """Test updating loss rate dynamically."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Initially no loss
        data = b"test data"
        success, _, _ = layer.transmit(data, "dest1")
        assert success
        
        # Set to 100% loss
        layer.set_loss_rate(1.0)
        success, _, _ = layer.transmit(data, "dest1")
        assert not success
    
    def test_set_loss_rate_validation(self):
        """Test that invalid loss rates are rejected."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        with pytest.raises(ValueError):
            layer.set_loss_rate(-0.1)
        
        with pytest.raises(ValueError):
            layer.set_loss_rate(1.5)


class TestPhysicalLayerBitErrorInjection:
    """Test bit error injection functionality."""
    
    def test_no_errors_with_zero_rate(self):
        """Test that no bit errors occur when error rate is 0."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,  # No errors
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        data = b"test data with some content"
        success, transmitted_data, _ = layer.transmit(data, "dest1")
        
        assert success
        assert transmitted_data == data
    
    def test_errors_injected_with_nonzero_rate(self):
        """Test that bit errors are injected when error rate is non-zero."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.1,  # 10% bit error rate (very high for testing)
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # With 10% bit error rate and reasonable data size, 
        # we should see some errors
        data = b"test data with some content" * 10  # 280 bytes = 2240 bits
        errors_detected = 0
        
        for _ in range(10):
            success, transmitted_data, _ = layer.transmit(data, "dest1")
            if transmitted_data != data:
                errors_detected += 1
        
        # Should see errors in most transmissions
        assert errors_detected > 0
    
    def test_bit_error_injection_changes_data(self):
        """Test that bit error injection actually modifies the data."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.5,  # Very high rate to ensure errors
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        data = b"A" * 100  # 100 bytes of same character
        success, transmitted_data, _ = layer.transmit(data, "dest1")
        
        assert success
        assert transmitted_data != data  # Should have errors
        assert len(transmitted_data) == len(data)  # Length unchanged
    
    def test_inject_bit_errors_directly(self):
        """Test the inject_bit_errors method directly."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # With 0% error rate, data should be unchanged
        data = b"test data"
        result = layer.inject_bit_errors(data)
        assert result == data
        
        # With 100% error rate, data should be different
        layer.set_bit_error_rate(1.0)
        result = layer.inject_bit_errors(data)
        assert result != data
    
    def test_set_bit_error_rate(self):
        """Test updating bit error rate dynamically."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        data = b"test data"
        
        # Initially no errors
        result = layer.inject_bit_errors(data)
        assert result == data
        
        # Set to 100% error rate
        layer.set_bit_error_rate(1.0)
        result = layer.inject_bit_errors(data)
        assert result != data
    
    def test_set_bit_error_rate_validation(self):
        """Test that invalid bit error rates are rejected."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        with pytest.raises(ValueError):
            layer.set_bit_error_rate(-0.1)
        
        with pytest.raises(ValueError):
            layer.set_bit_error_rate(1.5)


class TestPhysicalLayerConfiguration:
    """Test configuration management."""
    
    def test_set_bit_rate(self):
        """Test updating bit rate."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Initial delay
        delay1 = layer.calculate_transmission_delay(1000)
        
        # Change bit rate to 50 Mbps (half speed)
        layer.set_bit_rate(50_000_000)
        delay2 = layer.calculate_transmission_delay(1000)
        
        # Delay should double
        assert abs(delay2 - delay1 * 2) < 1e-9
    
    def test_set_propagation_delay(self):
        """Test updating propagation delay."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        # Initial delay
        delay1 = layer.get_propagation_delay()
        assert abs(delay1 - 0.01) < 1e-9
        
        # Change to 20 ms
        layer.set_propagation_delay(20.0)
        delay2 = layer.get_propagation_delay()
        assert abs(delay2 - 0.02) < 1e-9
    
    def test_get_config(self):
        """Test retrieving current configuration."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.05,
            bit_error_rate=0.001,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        retrieved_config = layer.get_config()
        assert retrieved_config.bit_rate_bps == 100_000_000
        assert retrieved_config.propagation_delay_ms == 10.0
        assert retrieved_config.loss_rate == 0.05
        assert retrieved_config.bit_error_rate == 0.001
        assert retrieved_config.random_seed == 42


class TestPhysicalLayerTransmit:
    """Test the complete transmit functionality."""
    
    def test_successful_transmission(self):
        """Test successful transmission returns correct values."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        data = b"test data"
        success, transmitted_data, delay = layer.transmit(data, "dest1")
        
        assert success
        assert transmitted_data == data
        assert delay > 0
    
    def test_transmission_with_callback(self):
        """Test that callback is invoked on successful transmission."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.0,
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        callback_invoked = []
        
        def callback(data, dest):
            callback_invoked.append((data, dest))
        
        data = b"test data"
        success, _, _ = layer.transmit(data, "dest1", callback=callback)
        
        assert success
        assert len(callback_invoked) == 1
        assert callback_invoked[0][0] == data
        assert callback_invoked[0][1] == "dest1"
    
    def test_callback_not_invoked_on_loss(self):
        """Test that callback is not invoked when packet is dropped."""
        config = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=1.0,  # Force drop
            bit_error_rate=0.0,
            random_seed=42
        )
        layer = PhysicalLayer(config)
        
        callback_invoked = []
        
        def callback(data, dest):
            callback_invoked.append((data, dest))
        
        data = b"test data"
        success, _, _ = layer.transmit(data, "dest1", callback=callback)
        
        assert not success
        assert len(callback_invoked) == 0
    
    def test_reproducibility_with_seed(self):
        """Test that same seed produces same results."""
        # Create two layers with same seed
        config1 = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.3,
            bit_error_rate=0.01,
            random_seed=12345
        )
        layer1 = PhysicalLayer(config1)
        
        config2 = PhysicalLayerConfig(
            bit_rate_bps=100_000_000,
            propagation_delay_ms=10.0,
            loss_rate=0.3,
            bit_error_rate=0.01,
            random_seed=12345
        )
        layer2 = PhysicalLayer(config2)
        
        # Transmit same data multiple times
        data = b"test data" * 10
        results1 = []
        results2 = []
        
        for _ in range(20):
            success1, data1, _ = layer1.transmit(data, "dest1")
            success2, data2, _ = layer2.transmit(data, "dest1")
            results1.append((success1, data1))
            results2.append((success2, data2))
        
        # Results should be identical
        assert results1 == results2
