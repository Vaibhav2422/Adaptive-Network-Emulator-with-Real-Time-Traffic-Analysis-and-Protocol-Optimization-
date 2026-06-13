"""
Property-based tests for Selective Repeat (SR) protocol.

Feature: adaptive-network-emulator
Property: 5 (SR selective retransmission)
Validates: Requirements 3.4

Tests verify that SR correctly implements selective retransmission,
retransmitting only the specific lost packet rather than all subsequent packets.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.sr_protocol import SRProtocol
from src.transport_layer import SlidingWindow
from src.data_models import Segment


# Custom strategies for generating test data

@st.composite
def sr_protocol_strategy(draw):
    """Generate random valid SRProtocol instances."""
    window_size = draw(st.integers(min_value=2, max_value=32))
    timeout_ms = draw(st.integers(min_value=10, max_value=1000))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
    protocol = SRProtocol(window=window, timeout_ms=timeout_ms)
    
    return protocol


@st.composite
def sr_with_sent_packets_strategy(draw):
    """Generate SRProtocol with some packets already sent."""
    window_size = draw(st.integers(min_value=4, max_value=32))
    timeout_ms = draw(st.integers(min_value=10, max_value=1000))
    max_seq_num = draw(st.integers(min_value=100, max_value=2**16))
    
    window = SlidingWindow(window_size=window_size, max_seq_num=max_seq_num)
    protocol = SRProtocol(window=window, timeout_ms=timeout_ms)
    
    # Send some packets
    num_to_send = draw(st.integers(min_value=2, max_value=window_size))
    sent_seq_nums = []
    
    for i in range(num_to_send):
        data = draw(st.binary(min_size=1, max_size=100))
        seq_num = protocol.send_segment(data, dest="test_dest")
        if seq_num is not None:
            sent_seq_nums.append(seq_num)
    
    return protocol, sent_seq_nums


class TestSRSelectiveRetransmission:
    """
    Property tests for SR selective retransmission behavior.
    
    Property 5: SR selective retransmission
    Validates: Requirements 3.4
    
    For any sequence with packet N lost, only packet N should be retransmitted.
    """
    
    @settings(max_examples=100)
    @given(protocol_state=sr_with_sent_packets_strategy())
    def test_sr_retransmits_only_lost_packet(self, protocol_state):
        """
        Property: SR retransmits only the specific lost packet.
        
        For any sequence of sent packets, when packet N times out, only packet N
        should be retransmitted, not any other packets.
        
        Validates: Requirement 3.4
        """
        protocol, sent_seq_nums = protocol_state
        
        # Skip if no packets were sent
        assume(len(sent_seq_nums) > 0)
        
        # Pick a packet to simulate timeout (any unacked packet)
        unacked = list(protocol.window.unacked_packets)
        assume(len(unacked) > 0)
        
        # Choose a packet to timeout
        timeout_seq = unacked[0]
        
        # Handle timeout
        retransmitted_segments = protocol.handle_timeout(timeout_seq)
        
        # Extract sequence numbers from retransmitted segments
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted_segments]
        
        # Verify only the timed-out packet is retransmitted
        assert len(retransmitted_seq_nums) == 1, \
            f"SR should retransmit only 1 packet, but retransmitted {len(retransmitted_seq_nums)}"
        
        assert retransmitted_seq_nums[0] == timeout_seq, \
            f"SR retransmitted packet {retransmitted_seq_nums[0]} instead of timed-out packet {timeout_seq}"
    
    @settings(max_examples=100)
    @given(protocol_state=sr_with_sent_packets_strategy())
    def test_sr_does_not_retransmit_subsequent_packets(self, protocol_state):
        """
        Property: SR does not retransmit subsequent packets.
        
        When packet N times out in SR, packets N+1, N+2, etc. should NOT be
        retransmitted (unlike GBN).
        
        Validates: Requirement 3.4
        """
        protocol, sent_seq_nums = protocol_state
        
        # Skip if we don't have multiple packets
        assume(len(sent_seq_nums) > 1)
        
        unacked = sorted(list(protocol.window.unacked_packets))
        assume(len(unacked) > 1)
        
        # Timeout a packet that's not the last one
        timeout_idx = 0  # First packet
        timeout_seq = unacked[timeout_idx]
        
        # Get subsequent packets
        subsequent_packets = unacked[timeout_idx + 1:]
        
        # Handle timeout
        retransmitted_segments = protocol.handle_timeout(timeout_seq)
        retransmitted_seq_nums = [seg.sequence_num for seg in retransmitted_segments]
        
        # Verify no subsequent packets are retransmitted
        for subsequent_seq in subsequent_packets:
            assert subsequent_seq not in retransmitted_seq_nums, \
                f"SR incorrectly retransmitted subsequent packet {subsequent_seq}"
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_sr_retransmits_exactly_one_packet_on_timeout(self, data):
        """
        Property: SR retransmits exactly one packet on timeout.
        
        For any SR protocol with multiple unacked packets, if packet at position i
        times out, exactly one packet (packet i) should be retransmitted.
        
        Validates: Requirement 3.4
        """
        window_size = data.draw(st.integers(min_value=4, max_value=16))
        protocol = SRProtocol(
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
        
        # Handle timeout
        retransmitted = protocol.handle_timeout(timeout_seq)
        
        # Verify exactly one packet is retransmitted
        assert len(retransmitted) == 1, \
            f"SR should retransmit exactly 1 packet, but retransmitted {len(retransmitted)}"
        
        # Verify it's the correct packet
        assert retransmitted[0].sequence_num == timeout_seq, \
            f"SR retransmitted wrong packet: expected {timeout_seq}, got {retransmitted[0].sequence_num}"
    
    @settings(max_examples=100)
    @given(protocol_state=sr_with_sent_packets_strategy())
    def test_sr_multiple_timeouts_retransmit_independently(self, protocol_state):
        """
        Property: SR handles multiple timeouts independently.
        
        For any SR protocol, if multiple packets timeout, each should be
        retransmitted independently (one packet per timeout).
        
        Validates: Requirement 3.4
        """
        protocol, sent_seq_nums = protocol_state
        
        # Skip if we don't have multiple packets
        assume(len(sent_seq_nums) >= 2)
        
        unacked = sorted(list(protocol.window.unacked_packets))
        assume(len(unacked) >= 2)
        
        # Simulate timeout for first packet
        timeout_seq_1 = unacked[0]
        retransmitted_1 = protocol.handle_timeout(timeout_seq_1)
        
        # Simulate timeout for second packet
        timeout_seq_2 = unacked[1]
        retransmitted_2 = protocol.handle_timeout(timeout_seq_2)
        
        # Each timeout should retransmit exactly one packet
        assert len(retransmitted_1) == 1, \
            f"First timeout should retransmit 1 packet, got {len(retransmitted_1)}"
        assert len(retransmitted_2) == 1, \
            f"Second timeout should retransmit 1 packet, got {len(retransmitted_2)}"
        
        # Each should retransmit the correct packet
        assert retransmitted_1[0].sequence_num == timeout_seq_1
        assert retransmitted_2[0].sequence_num == timeout_seq_2
    
    @settings(max_examples=100)
    @given(protocol=sr_protocol_strategy())
    def test_sr_no_retransmission_when_all_acked(self, protocol):
        """
        Property: SR doesn't retransmit when all packets are acknowledged.
        
        For any protocol state where all packets are acknowledged, timeout
        should not trigger any retransmissions.
        
        Validates: Requirement 3.4
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
            "SR retransmitted packets when all were acknowledged"
    
    @settings(max_examples=100)
    @given(protocol_state=sr_with_sent_packets_strategy())
    def test_sr_retransmission_does_not_affect_other_packets(self, protocol_state):
        """
        Property: SR retransmission doesn't affect other packets' state.
        
        For any SR protocol, retransmitting packet N should not change the
        state of other unacknowledged packets.
        
        Validates: Requirement 3.4
        """
        protocol, sent_seq_nums = protocol_state
        
        assume(len(sent_seq_nums) > 1)
        
        unacked_before = set(protocol.window.unacked_packets)
        assume(len(unacked_before) > 1)
        
        # Pick a packet to timeout
        timeout_seq = min(unacked_before)
        
        # Handle timeout
        protocol.handle_timeout(timeout_seq)
        
        # Unacked packets should remain the same (retransmission doesn't acknowledge)
        unacked_after = set(protocol.window.unacked_packets)
        assert unacked_before == unacked_after, \
            "Retransmission changed the set of unacknowledged packets"
    
    @settings(max_examples=100)
    @given(data=st.data())
    def test_sr_selective_ack_acknowledges_only_one_packet(self, data):
        """
        Property: SR selective ACK acknowledges only one packet.
        
        For any SR protocol, acknowledging packet N should acknowledge only
        packet N, not any other packets (unlike GBN's cumulative ACK).
        
        Validates: Requirement 3.4 (selective acknowledgment is part of SR)
        """
        window_size = data.draw(st.integers(min_value=4, max_value=16))
        protocol = SRProtocol(
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
        
        # Get initial unacked count
        initial_unacked = set(protocol.window.unacked_packets)
        
        # Choose a packet in the middle to acknowledge
        ack_idx = len(sent_seq_nums) // 2
        ack_seq = sent_seq_nums[ack_idx]
        
        # Acknowledge the packet
        protocol.handle_acknowledgment(ack_seq)
        
        # Only the acknowledged packet should be removed
        final_unacked = set(protocol.window.unacked_packets)
        removed_packets = initial_unacked - final_unacked
        
        assert len(removed_packets) == 1, \
            f"SR selective ACK should remove exactly 1 packet, but removed {len(removed_packets)}"
        
        assert ack_seq in removed_packets, \
            f"SR selective ACK should remove packet {ack_seq}, but removed {removed_packets}" 