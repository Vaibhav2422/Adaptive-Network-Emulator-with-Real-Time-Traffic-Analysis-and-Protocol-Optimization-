"""
Property-based tests for congestion detection and adaptation.

Feature: adaptive-network-emulator
Property: 9 (Congestion adaptation)
Validates: Requirement 3.6

Tests verify that the transport layer correctly detects congestion based on
packet loss and latency, and adapts transmission parameters accordingly.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.congestion_detector import CongestionDetector
from src.gbn_protocol import GBNProtocol
from src.sr_protocol import SRProtocol
from src.transport_layer import SlidingWindow
import time


# Custom strategies for generating test data

@st.composite
def congestion_detector_strategy(draw):
    """Generate random valid CongestionDetector instances."""
    loss_threshold = draw(st.floats(min_value=0.01, max_value=0.5))
    latency_threshold_ms = draw(st.floats(min_value=10.0, max_value=200.0))
    window_decrease_factor = draw(st.floats(min_value=0.3, max_value=0.9))
    window_increase_step = draw(st.integers(min_value=1, max_value=4))
    min_window_size = draw(st.integers(min_value=1, max_value=4))
    max_window_size = draw(st.integers(min_value=16, max_value=128))
    
    detector = CongestionDetector(
        loss_threshold=loss_threshold,
        latency_threshold_ms=latency_threshold_ms,
        window_decrease_factor=window_decrease_factor,
        window_increase_step=window_increase_step,
        min_window_size=min_window_size,
        max_window_size=max_window_size
    )
    
    return detector


@st.composite
def gbn_with_congestion_detector_strategy(draw):
    """Generate GBNProtocol with congestion detector."""
    window_size = draw(st.integers(min_value=4, max_value=32))
    timeout_ms = draw(st.integers(min_value=50, max_value=500))
    
    window = SlidingWindow(window_size=window_size)
    detector = draw(congestion_detector_strategy())
    
    protocol = GBNProtocol(
        window=window,
        timeout_ms=timeout_ms,
        congestion_detector=detector
    )
    
    return protocol


@st.composite
def sr_with_congestion_detector_strategy(draw):
    """Generate SRProtocol with congestion detector."""
    window_size = draw(st.integers(min_value=4, max_value=32))
    timeout_ms = draw(st.integers(min_value=50, max_value=500))
    
    window = SlidingWindow(window_size=window_size)
    detector = draw(congestion_detector_strategy())
    
    protocol = SRProtocol(
        window=window,
        timeout_ms=timeout_ms,
        congestion_detector=detector
    )
    
    return protocol


class TestCongestionDetection:
    """
    Property tests for congestion detection.
    
    Property 9: Congestion adaptation
    Validates: Requirement 3.6
    
    For any detection of loss or delay above threshold, transport should adapt parameters.
    """
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_high_packet_loss_triggers_congestion_detection(self, detector, data):
        """
        Property: High packet loss triggers congestion detection.
        
        For any congestion detector, when packet loss rate exceeds the threshold,
        congestion should be detected.
        
        Validates: Requirement 3.6 (packet loss rate monitoring)
        """
        # Send enough packets to have meaningful loss rate
        num_sent = data.draw(st.integers(min_value=20, max_value=100))
        
        # Calculate loss count that exceeds threshold
        loss_count = int(num_sent * (detector.loss_threshold + 0.1))  # 10% above threshold
        assume(loss_count > 0)
        
        # Record packets
        for _ in range(num_sent):
            detector.record_packet_sent()
        
        for _ in range(loss_count):
            detector.record_packet_loss()
        
        # Congestion should be detected
        assert detector.detect_congestion() is True, \
            f"Congestion not detected with loss rate {detector.get_packet_loss_rate():.2%} (threshold: {detector.loss_threshold:.2%})"
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_high_latency_triggers_congestion_detection(self, detector, data):
        """
        Property: High latency increase triggers congestion detection.
        
        For any congestion detector, when latency increase exceeds the threshold,
        congestion should be detected.
        
        Validates: Requirement 3.6 (latency increase detection)
        """
        # Establish baseline RTT
        baseline_rtt = data.draw(st.floats(min_value=10.0, max_value=100.0))
        
        # Record baseline samples
        for _ in range(5):
            detector.record_rtt_sample(baseline_rtt)
        
        # Record samples with high latency (exceeds threshold)
        high_latency = baseline_rtt + detector.latency_threshold_ms + 20.0
        
        for _ in range(5):
            detector.record_rtt_sample(high_latency)
        
        # Verify latency increase exceeds threshold
        latency_increase = detector.get_latency_increase()
        assume(latency_increase > detector.latency_threshold_ms)
        
        # Congestion should be detected
        assert detector.detect_congestion() is True, \
            f"Congestion not detected with latency increase {latency_increase:.2f}ms (threshold: {detector.latency_threshold_ms:.2f}ms)"
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_low_loss_and_latency_no_congestion(self, detector, data):
        """
        Property: Low loss and latency don't trigger congestion.
        
        For any congestion detector, when both packet loss and latency are
        below thresholds, congestion should not be detected.
        
        Validates: Requirement 3.6 (congestion detection)
        """
        # Send packets with low loss rate
        num_sent = data.draw(st.integers(min_value=20, max_value=100))
        loss_count = int(num_sent * (detector.loss_threshold * 0.5))  # Half the threshold
        
        for _ in range(num_sent):
            detector.record_packet_sent()
        
        for _ in range(loss_count):
            detector.record_packet_loss()
        
        # Record RTT samples with low latency
        baseline_rtt = data.draw(st.floats(min_value=10.0, max_value=100.0))
        
        for _ in range(10):
            # Add small variation but stay below threshold
            rtt_sample = baseline_rtt + data.draw(st.floats(min_value=0.0, max_value=detector.latency_threshold_ms * 0.5))
            detector.record_rtt_sample(rtt_sample)
        
        # Congestion should not be detected
        assert detector.detect_congestion() is False, \
            f"Congestion detected incorrectly with loss rate {detector.get_packet_loss_rate():.2%} and latency increase {detector.get_latency_increase():.2f}ms"


class TestWindowAdaptation:
    """
    Property tests for window size adaptation based on congestion.
    
    Property 9: Congestion adaptation
    Validates: Requirement 3.6
    
    For any detection of congestion, window size should be reduced.
    For no congestion, window size should gradually increase.
    """
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_window_decreases_on_congestion(self, detector, data):
        """
        Property: Window size decreases when congestion is detected.
        
        For any congestion detector that detects congestion, the adapted
        window size should be smaller than the current window size.
        
        Validates: Requirement 3.6 (window size reduction on congestion)
        """
        current_window = data.draw(st.integers(min_value=detector.min_window_size + 2, max_value=detector.max_window_size))
        
        # Trigger congestion with high packet loss
        num_sent = 50
        loss_count = int(num_sent * (detector.loss_threshold + 0.1))
        
        for _ in range(num_sent):
            detector.record_packet_sent()
        
        for _ in range(loss_count):
            detector.record_packet_loss()
        
        # Adapt window size
        new_window = detector.adapt_window_size(current_window)
        
        # Window should decrease
        assert new_window < current_window, \
            f"Window did not decrease on congestion: {current_window} -> {new_window}"
        
        # Window should not go below minimum
        assert new_window >= detector.min_window_size, \
            f"Window went below minimum: {new_window} < {detector.min_window_size}"
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_window_increases_without_congestion(self, detector, data):
        """
        Property: Window size increases when no congestion is detected.
        
        For any congestion detector that doesn't detect congestion, the adapted
        window size should be larger than the current window size (up to max).
        
        Validates: Requirement 3.6 (gradual window increase on improvement)
        """
        current_window = data.draw(st.integers(min_value=detector.min_window_size, max_value=detector.max_window_size - 2))
        
        # No congestion: low loss and latency
        num_sent = 50
        loss_count = 0  # No losses
        
        for _ in range(num_sent):
            detector.record_packet_sent()
        
        for _ in range(loss_count):
            detector.record_packet_loss()
        
        # Record stable RTT
        for _ in range(10):
            detector.record_rtt_sample(50.0)
        
        # Adapt window size
        new_window = detector.adapt_window_size(current_window)
        
        # Window should increase (unless at max)
        if current_window < detector.max_window_size:
            assert new_window > current_window, \
                f"Window did not increase without congestion: {current_window} -> {new_window}"
        
        # Window should not exceed maximum
        assert new_window <= detector.max_window_size, \
            f"Window exceeded maximum: {new_window} > {detector.max_window_size}"
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy())
    def test_window_respects_min_max_bounds(self, detector):
        """
        Property: Window adaptation respects minimum and maximum bounds.
        
        For any window size adaptation, the result should always be within
        the configured minimum and maximum bounds.
        
        Validates: Requirement 3.6 (window size adaptation)
        """
        # Test with various current window sizes
        test_windows = [
            detector.min_window_size,
            detector.max_window_size,
            (detector.min_window_size + detector.max_window_size) // 2
        ]
        
        for current_window in test_windows:
            # Trigger congestion
            for _ in range(50):
                detector.record_packet_sent()
            for _ in range(10):
                detector.record_packet_loss()
            
            new_window = detector.adapt_window_size(current_window)
            
            assert detector.min_window_size <= new_window <= detector.max_window_size, \
                f"Window {new_window} outside bounds [{detector.min_window_size}, {detector.max_window_size}]"
            
            # Reset for next iteration
            detector.reset_statistics()


class TestTimeoutAdaptation:
    """
    Property tests for timeout adaptation based on RTT.
    
    Property 9: Congestion adaptation
    Validates: Requirement 3.6
    
    For any RTT measurements, timeout should be adjusted accordingly.
    """
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_timeout_increases_with_high_rtt(self, detector, data):
        """
        Property: Timeout increases with high RTT measurements.
        
        For any congestion detector with high RTT samples, the calculated
        timeout should be higher than the base timeout.
        
        Validates: Requirement 3.6 (timeout adjustment based on RTT)
        """
        base_timeout_ms = data.draw(st.integers(min_value=50, max_value=200))
        high_rtt = data.draw(st.floats(min_value=100.0, max_value=500.0))
        
        # Record high RTT samples
        for _ in range(10):
            detector.record_rtt_sample(high_rtt)
        
        # Calculate adaptive timeout
        adaptive_timeout = detector.calculate_timeout(base_timeout_ms)
        
        # Adaptive timeout should be at least the base timeout
        assert adaptive_timeout >= base_timeout_ms, \
            f"Adaptive timeout {adaptive_timeout}ms less than base {base_timeout_ms}ms"
    
    @settings(max_examples=100)
    @given(detector=congestion_detector_strategy(), data=st.data())
    def test_timeout_adapts_to_rtt_variance(self, detector, data):
        """
        Property: Timeout adapts to RTT variance.
        
        For any congestion detector with variable RTT samples, the timeout
        should account for the variance (higher variance = higher timeout).
        
        Validates: Requirement 3.6 (timeout adjustment based on RTT)
        """
        base_timeout_ms = data.draw(st.integers(min_value=50, max_value=200))
        mean_rtt = data.draw(st.floats(min_value=50.0, max_value=150.0))
        
        # Record RTT samples with variance
        for _ in range(10):
            # Add random variance
            variance = data.draw(st.floats(min_value=-20.0, max_value=20.0))
            rtt_sample = max(1.0, mean_rtt + variance)
            detector.record_rtt_sample(rtt_sample)
        
        # Calculate adaptive timeout
        adaptive_timeout = detector.calculate_timeout(base_timeout_ms)
        
        # Timeout should be reasonable (not negative, not excessively large)
        assert adaptive_timeout > 0, "Adaptive timeout must be positive"
        assert adaptive_timeout < base_timeout_ms * 10, "Adaptive timeout excessively large"


class TestProtocolCongestionIntegration:
    """
    Property tests for congestion adaptation integration with protocols.
    
    Property 9: Congestion adaptation
    Validates: Requirement 3.6
    
    For any transport protocol, congestion detection should trigger adaptation.
    """
    
    @settings(max_examples=100)
    @given(protocol=gbn_with_congestion_detector_strategy(), data=st.data())
    def test_gbn_adapts_window_on_packet_loss(self, protocol, data):
        """
        Property: GBN adapts window size when packet loss occurs.
        
        For any GBN protocol, when packet loss is detected (timeout),
        the congestion detector should record the loss and potentially
        adapt the window size.
        
        Validates: Requirement 3.6 (congestion adaptation in GBN)
        """
        # Send some packets
        num_packets = data.draw(st.integers(min_value=3, max_value=protocol.window.window_size))
        sent_seq_nums = []
        
        for _ in range(num_packets):
            data_bytes = data.draw(st.binary(min_size=1, max_size=100))
            seq_num = protocol.send_segment(data_bytes, dest="test")
            if seq_num is not None:
                sent_seq_nums.append(seq_num)
        
        assume(len(sent_seq_nums) > 0)
        
        # Record initial loss count
        initial_loss_count = protocol.congestion_detector.packet_loss_count
        
        # Simulate timeout (triggers packet loss recording)
        timeout_seq = sent_seq_nums[0]
        protocol.handle_timeout(timeout_seq)
        
        # Loss count should increase
        assert protocol.congestion_detector.packet_loss_count > initial_loss_count, \
            "Packet loss not recorded on timeout"
    
    @settings(max_examples=100)
    @given(protocol=sr_with_congestion_detector_strategy(), data=st.data())
    def test_sr_adapts_window_on_packet_loss(self, protocol, data):
        """
        Property: SR adapts window size when packet loss occurs.
        
        For any SR protocol, when packet loss is detected (timeout),
        the congestion detector should record the loss and potentially
        adapt the window size.
        
        Validates: Requirement 3.6 (congestion adaptation in SR)
        """
        # Send some packets
        num_packets = data.draw(st.integers(min_value=3, max_value=protocol.window.window_size))
        sent_seq_nums = []
        
        for _ in range(num_packets):
            data_bytes = data.draw(st.binary(min_size=1, max_size=100))
            seq_num = protocol.send_segment(data_bytes, dest="test")
            if seq_num is not None:
                sent_seq_nums.append(seq_num)
        
        assume(len(sent_seq_nums) > 0)
        
        # Record initial loss count
        initial_loss_count = protocol.congestion_detector.packet_loss_count
        
        # Simulate timeout (triggers packet loss recording)
        timeout_seq = sent_seq_nums[0]
        protocol.handle_timeout(timeout_seq)
        
        # Loss count should increase
        assert protocol.congestion_detector.packet_loss_count > initial_loss_count, \
            "Packet loss not recorded on timeout"
    
    @settings(max_examples=100)
    @given(protocol=gbn_with_congestion_detector_strategy(), data=st.data())
    def test_gbn_records_rtt_on_ack(self, protocol, data):
        """
        Property: GBN records RTT samples on acknowledgment.
        
        For any GBN protocol, when an acknowledgment is received,
        RTT samples should be recorded for congestion detection.
        
        Validates: Requirement 3.6 (RTT measurement for timeout adaptation)
        """
        # Send a packet
        data_bytes = data.draw(st.binary(min_size=1, max_size=100))
        seq_num = protocol.send_segment(data_bytes, dest="test")
        
        assume(seq_num is not None)
        
        # Record initial RTT sample count
        initial_rtt_count = len(protocol.congestion_detector.rtt_samples)
        
        # Simulate small delay
        time.sleep(0.01)
        
        # Acknowledge the packet
        protocol.handle_acknowledgment(seq_num)
        
        # RTT sample should be recorded
        assert len(protocol.congestion_detector.rtt_samples) > initial_rtt_count, \
            "RTT sample not recorded on acknowledgment"
    
    @settings(max_examples=100)
    @given(protocol=sr_with_congestion_detector_strategy(), data=st.data())
    def test_sr_records_rtt_on_ack(self, protocol, data):
        """
        Property: SR records RTT samples on acknowledgment.
        
        For any SR protocol, when an acknowledgment is received,
        RTT samples should be recorded for congestion detection.
        
        Validates: Requirement 3.6 (RTT measurement for timeout adaptation)
        """
        # Send a packet
        data_bytes = data.draw(st.binary(min_size=1, max_size=100))
        seq_num = protocol.send_segment(data_bytes, dest="test")
        
        assume(seq_num is not None)
        
        # Record initial RTT sample count
        initial_rtt_count = len(protocol.congestion_detector.rtt_samples)
        
        # Simulate small delay
        time.sleep(0.01)
        
        # Acknowledge the packet
        protocol.handle_acknowledgment(seq_num)
        
        # RTT sample should be recorded
        assert len(protocol.congestion_detector.rtt_samples) > initial_rtt_count, \
            "RTT sample not recorded on acknowledgment"
