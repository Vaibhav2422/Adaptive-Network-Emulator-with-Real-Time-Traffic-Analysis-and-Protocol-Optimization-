"""
Property-based tests for Transport Layer sliding window mechanism.

Feature: adaptive-network-emulator
Properties: 6 (Sliding window constraint), 7 (Sequence number monotonicity)
Validates: Requirements 3.5, 3.7

Tests verify that the sliding window mechanism correctly enforces flow control
and maintains sequence number ordering across all valid scenarios.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.transport_layer import SlidingWindow


# Custom strategies for generating test data

@st.composite
def sliding_window_strategy(draw):
    """Generate random valid SlidingWindow instances."""
    window_size = draw(st.integers(min_value=1, max_value=64))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    return SlidingWindow(
        window_size=window_size,
        max_seq_num=max_seq_num
    )


@st.composite
def window_with_state_strategy(draw):
    """Generate SlidingWindow with some packets already sent."""
    window_size = draw(st.integers(min_value=2, max_value=64))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
    
    # Send some packets (but not fill the window completely)
    num_to_send = draw(st.integers(min_value=0, max_value=window_size - 1))
    sent_seq_nums = []
    for _ in range(num_to_send):
        if window.can_send():
            seq_num = window.get_next_sequence_number()
            sent_seq_nums.append(seq_num)
    
    return window, sent_seq_nums


class TestSlidingWindowConstraint:
    """
    Property tests for sliding window constraint.
    
    Property 6: Sliding window constraint
    Validates: Requirements 3.5
    
    For any protocol, unacknowledged packets should never exceed window size.
    """
    
    @settings(max_examples=100)
    @given(window=sliding_window_strategy())
    def test_window_constraint_on_send(self, window):
        """
        Property: Unacknowledged packets never exceed window size during sends.
        
        For any sliding window, repeatedly sending packets should never result
        in more unacknowledged packets than the configured window size.
        
        Validates: Requirement 3.5
        """
        # Try to send more packets than window size
        sent_count = 0
        for _ in range(window.window_size * 2):
            if window.can_send():
                window.get_next_sequence_number()
                sent_count += 1
                # Verify constraint is maintained
                assert window.get_unacked_count() <= window.window_size
            else:
                # Window is full, should not be able to send
                break
        
        # Should have sent exactly window_size packets
        assert sent_count == window.window_size
        assert window.get_unacked_count() == window.window_size
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_window_constraint_with_acks(self, data):
        """
        Property: Unacknowledged packets never exceed window size with acknowledgments.
        
        For any sequence of sends and acknowledgments, the number of unacknowledged
        packets should never exceed the window size.
        
        Validates: Requirement 3.5
        """
        window_size = data.draw(st.integers(min_value=1, max_value=64))
        window = SlidingWindow(window_size=window_size)
        
        sent_seq_nums = []
        
        # Perform random sequence of sends and acks
        num_operations = data.draw(st.integers(min_value=10, max_value=100))
        
        for _ in range(num_operations):
            operation = data.draw(st.sampled_from(['send', 'ack']))
            
            if operation == 'send' and window.can_send():
                seq_num = window.get_next_sequence_number()
                sent_seq_nums.append(seq_num)
                # Verify constraint after send
                assert window.get_unacked_count() <= window.window_size
            
            elif operation == 'ack' and sent_seq_nums:
                # Acknowledge a random unacked packet
                unacked = list(window.unacked_packets)
                if unacked:
                    ack_seq = data.draw(st.sampled_from(unacked))
                    window.acknowledge(ack_seq)
                    # Verify constraint after ack
                    assert window.get_unacked_count() <= window.window_size
    
    @settings(max_examples=100)
    @given(window_size=st.integers(min_value=1, max_value=64))
    def test_window_blocks_when_full(self, window_size):
        """
        Property: Window blocks sends when full.
        
        For any window size, after sending window_size packets without
        acknowledgments, can_send() should return False.
        
        Validates: Requirement 3.5
        """
        window = SlidingWindow(window_size=window_size)
        
        # Fill the window
        for _ in range(window_size):
            assert window.can_send() is True
            window.get_next_sequence_number()
        
        # Window should now be full
        assert window.can_send() is False
        assert window.get_unacked_count() == window_size
        
        # Attempting to get next sequence number should raise error
        with pytest.raises(RuntimeError, match="Cannot send: window is full"):
            window.get_next_sequence_number()
    
    @settings(max_examples=100)
    @given(window_state=window_with_state_strategy())
    def test_window_usage_accuracy(self, window_state):
        """
        Property: Window usage accurately reflects unacked count.
        
        For any window state, window usage should equal unacked_count / window_size.
        
        Validates: Requirement 3.5
        """
        window, sent_seq_nums = window_state
        
        expected_usage = len(sent_seq_nums) / window.window_size
        actual_usage = window.get_window_usage()
        
        assert abs(actual_usage - expected_usage) < 0.001
        assert 0.0 <= actual_usage <= 1.0
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_window_slides_on_base_ack(self, data):
        """
        Property: Window slides forward when base is acknowledged.
        
        For any window, acknowledging the base packet should cause the
        window to slide forward, allowing new packets to be sent.
        
        Validates: Requirement 3.5
        """
        window_size = data.draw(st.integers(min_value=2, max_value=32))
        window = SlidingWindow(window_size=window_size)
        
        # Fill the window
        sent_seq_nums = []
        for _ in range(window_size):
            seq_num = window.get_next_sequence_number()
            sent_seq_nums.append(seq_num)
        
        # Window should be full
        assert window.can_send() is False
        
        # Acknowledge the base packet
        base_seq = sent_seq_nums[0]
        window.acknowledge(base_seq)
        
        # Window should slide and allow one more send
        assert window.can_send() is True
        assert window.get_unacked_count() == window_size - 1


class TestSequenceNumberMonotonicity:
    """
    Property tests for sequence number monotonicity.
    
    Property 7: Sequence number monotonicity
    Validates: Requirements 3.7
    
    For any packet sequence, sequence numbers should be monotonically increasing.
    """
    
    @settings(max_examples=100)
    @given(window=sliding_window_strategy(), num_packets=st.integers(min_value=1, max_value=50))
    def test_sequence_numbers_monotonically_increase(self, window, num_packets):
        """
        Property: Sequence numbers are monotonically increasing.
        
        For any sequence of packets sent, each sequence number should be
        greater than the previous one (modulo wraparound).
        
        Validates: Requirement 3.7
        """
        # Limit num_packets to avoid wraparound in this test
        assume(num_packets < window.max_seq_num // 2)
        
        seq_nums = []
        
        # Send packets and collect sequence numbers
        for _ in range(num_packets):
            if window.can_send():
                seq_num = window.get_next_sequence_number()
                seq_nums.append(seq_num)
            else:
                # Acknowledge oldest to make room
                if window.unacked_packets:
                    oldest = min(window.unacked_packets)
                    window.acknowledge(oldest)
                    seq_num = window.get_next_sequence_number()
                    seq_nums.append(seq_num)
        
        # Verify monotonicity (each seq_num > previous)
        for i in range(1, len(seq_nums)):
            assert seq_nums[i] > seq_nums[i-1], \
                f"Sequence numbers not monotonic: {seq_nums[i-1]} -> {seq_nums[i]}"
    
    @settings(max_examples=100)
    @given(window_size=st.integers(min_value=1, max_value=32))
    def test_sequence_numbers_start_at_zero(self, window_size):
        """
        Property: First sequence number is zero.
        
        For any new window, the first sequence number should be 0.
        
        Validates: Requirement 3.7
        """
        window = SlidingWindow(window_size=window_size)
        
        first_seq = window.get_next_sequence_number()
        assert first_seq == 0
    
    @settings(max_examples=100)
    @given(window=sliding_window_strategy())
    def test_sequence_numbers_increment_by_one(self, window):
        """
        Property: Sequence numbers increment by exactly one.
        
        For any consecutive packets, the sequence number should increase
        by exactly 1 (modulo max_seq_num).
        
        Validates: Requirement 3.7
        """
        # Send multiple packets and verify increments
        prev_seq = None
        
        for _ in range(min(10, window.window_size)):
            if window.can_send():
                seq_num = window.get_next_sequence_number()
                
                if prev_seq is not None:
                    expected_next = (prev_seq + 1) % window.max_seq_num
                    assert seq_num == expected_next, \
                        f"Sequence number did not increment by 1: {prev_seq} -> {seq_num}"
                
                prev_seq = seq_num
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_sequence_number_wraparound(self, data):
        """
        Property: Sequence numbers wrap around at max_seq_num.
        
        For any window, when sequence numbers reach max_seq_num,
        they should wrap around to 0.
        
        Validates: Requirement 3.7
        """
        # Use small max_seq_num to test wraparound
        max_seq_num = data.draw(st.integers(min_value=10, max_value=100))
        window_size = data.draw(st.integers(min_value=1, max_value=min(8, max_seq_num // 2)))
        
        window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
        
        # Send packets until we see wraparound
        seq_nums = []
        for _ in range(max_seq_num + 10):
            if window.can_send():
                seq_num = window.get_next_sequence_number()
                seq_nums.append(seq_num)
            else:
                # Acknowledge oldest to continue
                if window.unacked_packets:
                    oldest = min(window.unacked_packets)
                    window.acknowledge(oldest)
        
        # Verify we saw wraparound (sequence number went back to 0)
        if len(seq_nums) > max_seq_num:
            assert 0 in seq_nums[max_seq_num:], "Sequence numbers did not wrap around"
    
    @settings(max_examples=100)
    @given(window=sliding_window_strategy())
    def test_sequence_number_validation(self, window):
        """
        Property: Sequence number validation works correctly.
        
        For any window, validate_sequence_number should return True for
        valid sequence numbers and False for invalid ones.
        
        Validates: Requirement 3.7
        """
        # Valid sequence numbers
        assert window.validate_sequence_number(0) is True
        assert window.validate_sequence_number(window.max_seq_num - 1) is True
        assert window.validate_sequence_number(window.max_seq_num // 2) is True
        
        # Invalid sequence numbers
        assert window.validate_sequence_number(-1) is False
        assert window.validate_sequence_number(window.max_seq_num) is False
        assert window.validate_sequence_number(window.max_seq_num + 1) is False
