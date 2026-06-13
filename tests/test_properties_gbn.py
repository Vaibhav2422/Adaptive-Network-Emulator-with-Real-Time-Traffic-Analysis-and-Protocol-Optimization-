"""
Property-based tests for Go-Back-N (GBN) protocol.

Feature: adaptive-network-emulator
Properties: 4 (GBN retransmission behavior), 8 (Window advancement on ACK)
Validates: Requirements 3.3, 3.8

Tests verify that GBN correctly implements retransmission from lost packet
onward and properly advances the window on acknowledgments.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.gbn_protocol import GBNProtocol
from src.transport_layer import SlidingWindow
from src.data_models import Segment


# Custom strategies for generating test data

@st.composite
def gbn_protocol_strategy(draw):
    """Generate random valid GBNProtocol instances."""
    window_size = draw(st.integers(min_value=2, max_value=32))
    timeout_ms = draw(st.integers(min_value=10, max_value=1000))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
    protocol = GBNProtocol(window=window, timeout_ms=timeout_ms)
    
    return protocol


@st.composite
def gbn_with_sent_packets_strategy(draw):
    """Generate GBNProtocol with some packets already sent."""
    window_size = draw(st.integers(min_value=4, max_value=32))
    timeout_ms = draw(st.integers(min_value=10, max_value=1000))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
    protocol = GBNProtocol(window=window, timeout_ms=timeout_ms)
    
    # Send some packets
    num_to_send = draw(st.integers(min_value=2, max_value=window_size))
    sent_seq_nums = []
    
    for i in range(num_to_send):
        data = draw(st.binary(min_size=1, max_size=100))
        seq_num = protocol.send_segment(data, dest="test_dest")
        if seq_num is not None:
            sent_seq_nums.append(seq_num)
    
    return protocol, sent_seq_nums


class TestGBNRetransmissionBehavior:
    """
    Property tests for GBN retransmission behavior.
    
    Property 4: GBN retransmission behavior
    Validates: Requirements 3.3
    
    For any sequence with packet N lost, all packets from N onward should be retransmitted.
    """
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_gbn_retransmits_from_lost_packet_onward(self, protocol_state):
        """
        Property: GBN retransmits all packets from lost packet onward.
        
        For any sequence of sent packets, when packet N times out, all packets
        from N onward (all unacknowledged packets starting from N) should be
        included in the retransmission list.
        
        Validates: Requirement 3.3
        """
        protocol, sent_seq_nums = protocol_state
        
        # Skip if no packets were sent
        assume(len(sent_seq_nums) > 0)
        
        # Pick a packet to simulate timeout (any unacked packet)
        unacked = list(protocol.window.unacked_packets)
        assume(len(unacked) > 0)
        
        # Choose a packet to timeout (not necessarily the first one)
        timeout_seq = min(unacked)  # Use the oldest unacked packet
        
        # Get the list of unacked packets at this point
        unacked_before = sorted(list(protocol.window.unacked_packets))
        
        # Find position of timeout packet
        if timeout_seq in unacked_before:
            timeout_idx = unacked_before.index(timeout_seq)
            expected_retransmit = unacked_before[timeout_idx:]
        else:
            expected_retransmit = unacked_before
        
        # Handle timeout
        retransmitted_segments = protocol.handle_timeout(timeout_seq)
        
        # Extract sequence numbers from retransmitted segments
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted_segments]
        
        # Verify all packets from timeout_seq onward are retransmitted
        assert len(retransmitted_seq_nums) == len(expected_retransmit), \
            f"Expected {len(expected_retransmit)} retransmissions, got {len(retransmitted_seq_nums)}"
        
        # Verify the retransmitted packets match expected
        assert set(retransmitted_seq_nums) == set(expected_retransmit), \
            f"Retransmitted packets {retransmitted_seq_nums} don't match expected {expected_retransmit}"
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_gbn_retransmits_all_unacked_on_timeout(self, protocol_state):
        """
        Property: GBN retransmits all unacknowledged packets on timeout.
        
        When any packet times out in GBN, all currently unacknowledged packets
        should be retransmitted (from the timed-out packet onward).
        
        Validates: Requirement 3.3
        """
        protocol, sent_seq_nums = protocol_state
        
        # Skip if no packets were sent
        assume(len(sent_seq_nums) > 0)
        
        unacked_before = sorted(list(protocol.window.unacked_packets))
        assume(len(unacked_before) > 0)
        
        # Simulate timeout on the first unacked packet (base)
        timeout_seq = unacked_before[0]
        
        # Handle timeout
        retransmitted_segments = protocol.handle_timeout(timeout_seq)
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted_segments]
        
        # All unacked packets should be retransmitted
        assert set(retransmitted_seq_nums) == set(unacked_before), \
            f"Not all unacked packets retransmitted. Expected {unacked_before}, got {retransmitted_seq_nums}"
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_gbn_retransmission_includes_all_subsequent_packets(self, data):
        """
        Property: GBN retransmission includes all subsequent packets.
        
        For any window with multiple unacked packets, if packet at position i
        times out, all packets at positions i, i+1, i+2, ... should be retransmitted.
        
        Validates: Requirement 3.3
        """
        window_size = data.draw(st.integers(min_value=4, max_value=16))
        protocol = GBNProtocol(
            window=SlidingWindow(window_size=window_size),
            timeout_ms=100
        )
        
        # Send multiple packets to fill window partially
        num_packets = data.draw(st.integers(min_value=3, max_value=window_size))
        sent_seq_nums = []
        
        for _ in range(num_packets):
            data_bytes = data.draw(st.binary(min_size=1, max_size=50))
            seq_num = protocol.send_segment(data_bytes, dest="test")
            if seq_num is not None:
                sent_seq_nums.append(seq_num)
        
        assume(len(sent_seq_nums) >= 3)
        
        # Choose a packet in the middle to timeout
        unacked = sorted(list(protocol.window.unacked_packets))
        timeout_idx = len(unacked) // 2  # Middle packet
        timeout_seq = unacked[timeout_idx]
        
        # Expected: all packets from timeout_idx onward
        expected_retransmit = unacked[timeout_idx:]
        
        # Handle timeout
        retransmitted = protocol.handle_timeout(timeout_seq)
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted]
        
        # Verify all subsequent packets are included
        assert set(retransmitted_seq_nums) == set(expected_retransmit), \
            f"Retransmission didn't include all subsequent packets. Expected {expected_retransmit}, got {retransmitted_seq_nums}"
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_gbn_retransmission_preserves_order(self, protocol_state):
        """
        Property: GBN retransmission preserves packet order.
        
        For any retransmission, packets should be retransmitted in the same
        order they were originally sent (by sequence number).
        
        Validates: Requirement 3.3
        """
        protocol, sent_seq_nums = protocol_state
        
        assume(len(sent_seq_nums) > 1)
        
        unacked = sorted(list(protocol.window.unacked_packets))
        assume(len(unacked) > 1)
        
        # Timeout the first unacked packet
        timeout_seq = unacked[0]
        
        # Handle timeout
        retransmitted = protocol.handle_timeout(timeout_seq)
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted]
        
        # Verify order is preserved (should be sorted)
        assert retransmitted_seq_nums == sorted(retransmitted_seq_nums), \
            f"Retransmitted packets not in order: {retransmitted_seq_nums}"
    
    @settings(max_examples=100)
    @given(protocol=gbn_protocol_strategy())
    def test_gbn_no_retransmission_when_all_acked(self, protocol):
        """
        Property: GBN doesn't retransmit when all packets are acknowledged.
        
        For any protocol state where all packets are acknowledged, timeout
        should not trigger any retransmissions.
        
        Validates: Requirement 3.3
        """
        # Send and immediately acknowledge all packets
        for _ in range(protocol.window.window_size):
            if protocol.window.can_send():
                data = b"test data"
                seq_num = protocol.send_segment(data, dest="test")
                if seq_num is not None:
                    # Immediately acknowledge
                    protocol.handle_acknowledgment(seq_num)
        
        # All packets should be acknowledged
        assert len(protocol.window.unacked_packets) == 0
        
        # Timeout should not retransmit anything
        retransmitted = protocol.handle_timeout(0)
        assert len(retransmitted) == 0, \
            "GBN retransmitted packets when all were acknowledged"


class TestWindowAdvancementOnACK:
    """
    Property tests for window advancement on acknowledgment.
    
    Property 8: Window advancement on ACK
    Validates: Requirements 3.8
    
    For any ACK received, window should slide forward appropriately.
    """
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_window_advances_on_cumulative_ack(self, protocol_state):
        """
        Property: Window advances on cumulative acknowledgment.
        
        For any GBN protocol with sent packets, acknowledging packet N should
        acknowledge all packets up to and including N, advancing the window.
        
        Validates: Requirement 3.8
        """
        protocol, sent_seq_nums = protocol_state
        
        assume(len(sent_seq_nums) > 0)
        
        # Get initial window state
        initial_base = protocol.window.base
        initial_unacked = len(protocol.window.unacked_packets)
        
        # Acknowledge the first sent packet (cumulative ACK)
        ack_seq = sent_seq_nums[0]
        protocol.handle_acknowledgment(ack_seq)
        
        # Window should have advanced
        assert len(protocol.window.unacked_packets) < initial_unacked or initial_unacked == 0, \
            "Window did not advance after acknowledgment"
        
        # The acknowledged packet should no longer be unacked
        assert ack_seq not in protocol.window.unacked_packets, \
            f"Acknowledged packet {ack_seq} still in unacked set"
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_cumulative_ack_acknowledges_all_previous(self, data):
        """
        Property: Cumulative ACK acknowledges all previous packets.
        
        For any GBN protocol, acknowledging packet N should acknowledge
        all packets with sequence numbers <= N.
        
        Validates: Requirement 3.8
        """
        window_size = data.draw(st.integers(min_value=4, max_value=16))
        protocol = GBNProtocol(
            window=SlidingWindow(window_size=window_size),
            timeout_ms=100
        )
        
        # Send multiple packets
        num_packets = data.draw(st.integers(min_value=3, max_value=window_size))
        sent_seq_nums = []
        
        for _ in range(num_packets):
            data_bytes = data.draw(st.binary(min_size=1, max_size=50))
            seq_num = protocol.send_segment(data_bytes, dest="test")
            if seq_num is not None:
                sent_seq_nums.append(seq_num)
        
        assume(len(sent_seq_nums) >= 3)
        
        # Choose a packet in the middle to acknowledge
        ack_idx = len(sent_seq_nums) // 2
        ack_seq = sent_seq_nums[ack_idx]
        
        # Packets that should be acknowledged (all up to and including ack_seq)
        expected_acked = sent_seq_nums[:ack_idx + 1]
        
        # Acknowledge the packet
        protocol.handle_acknowledgment(ack_seq)
        
        # Verify all previous packets are acknowledged
        for seq in expected_acked:
            assert seq not in protocol.window.unacked_packets, \
                f"Packet {seq} should be acknowledged but is still unacked"
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_window_allows_new_sends_after_ack(self, protocol_state):
        """
        Property: Window allows new sends after acknowledgment.
        
        For any full window, acknowledging packets should free up space
        and allow new packets to be sent.
        
        Validates: Requirement 3.8
        """
        protocol, sent_seq_nums = protocol_state
        
        # Fill the window completely
        while protocol.window.can_send():
            data = b"fill window"
            protocol.send_segment(data, dest="test")
        
        # Window should be full
        initial_can_send = protocol.window.can_send()
        assume(initial_can_send is False)
        
        # Acknowledge some packets
        if sent_seq_nums:
            protocol.handle_acknowledgment(sent_seq_nums[0])
        
        # Window should now allow sending
        assert protocol.window.can_send() is True, \
            "Window did not allow new sends after acknowledgment"
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_window_base_advances_on_base_ack(self, data):
        """
        Property: Window base advances when base packet is acknowledged.
        
        For any window, acknowledging the base packet should cause the
        base to advance to the next unacknowledged packet.
        
        Validates: Requirement 3.8
        """
        window_size = data.draw(st.integers(min_value=2, max_value=16))
        protocol = GBNProtocol(
            window=SlidingWindow(window_size=window_size),
            timeout_ms=100
        )
        
        # Send some packets
        num_packets = data.draw(st.integers(min_value=2, max_value=window_size))
        sent_seq_nums = []
        
        for _ in range(num_packets):
            data_bytes = data.draw(st.binary(min_size=1, max_size=50))
            seq_num = protocol.send_segment(data_bytes, dest="test")
            if seq_num is not None:
                sent_seq_nums.append(seq_num)
        
        assume(len(sent_seq_nums) >= 2)
        
        # Get initial base
        initial_base = protocol.window.base
        
        # Acknowledge the base packet
        protocol.handle_acknowledgment(initial_base)
        
        # Base should have advanced
        assert protocol.window.base != initial_base, \
            "Window base did not advance after acknowledging base packet"
    
    @settings(max_examples=100)
    @given(protocol_state=gbn_with_sent_packets_strategy())
    def test_ack_removes_from_sent_segments(self, protocol_state):
        """
        Property: Acknowledgment removes segments from sent_segments.
        
        For any acknowledged packet, it should be removed from the
        sent_segments dictionary (no longer needs timeout tracking).
        
        Validates: Requirement 3.8
        """
        protocol, sent_seq_nums = protocol_state
        
        assume(len(sent_seq_nums) > 0)
        
        # Get initial sent_segments count
        initial_count = len(protocol.sent_segments)
        
        # Acknowledge a packet
        ack_seq = sent_seq_nums[0]
        protocol.handle_acknowledgment(ack_seq)
        
        # Acknowledged packet should be removed from sent_segments
        assert ack_seq not in protocol.sent_segments, \
            f"Acknowledged packet {ack_seq} still in sent_segments"
        
        # sent_segments count should decrease
        assert len(protocol.sent_segments) <= initial_count, \
            "sent_segments count did not decrease after acknowledgment"
