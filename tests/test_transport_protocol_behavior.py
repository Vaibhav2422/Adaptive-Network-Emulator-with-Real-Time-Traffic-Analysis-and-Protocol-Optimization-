"""
Integration tests for Transport Layer protocol behavior verification.

This module tests specific protocol behaviors for GBN and SR protocols:
- GBN retransmission: verify all packets from N onward retransmitted
- SR selective retransmission: verify only lost packet retransmitted
- Window constraint: verify unacked packets never exceed window size
- Congestion adaptation: verify window reduces on packet loss

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import pytest
import time
from src.gbn_protocol import GBNProtocol
from src.sr_protocol import SRProtocol
from src.transport_layer import SlidingWindow
from src.data_models import Segment


class TestGBNRetransmissionBehavior:
    """Test GBN retransmission behavior: all packets from N onward."""
    
    def test_gbn_retransmits_from_lost_packet_onward(self):
        """
        Verify that when packet N is lost, GBN retransmits all packets from N onward.
        
        Validates: Requirement 3.3 (GBN retransmission behavior)
        """
        # Create GBN protocol with window size 8
        window = SlidingWindow(window_size=8)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Send 5 packets
        sent_seqs = []
        for i in range(5):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Verify 5 packets sent
        assert len(protocol.sent_segments) == 5
        assert protocol.window.get_unacked_count() == 5
        
        # Simulate timeout for packet 2 (index 2)
        timeout_seq = sent_seqs[2]
        retransmit_segments = protocol.handle_timeout(timeout_seq)
        
        # Verify that packets from 2 onward are retransmitted (packets 2, 3, 4)
        assert len(retransmit_segments) == 3
        retransmit_seqs = [seg.sequence_num for seg in retransmit_segments]
        expected_seqs = sent_seqs[2:]  # Packets 2, 3, 4
        assert retransmit_seqs == expected_seqs
    
    def test_gbn_retransmission_includes_all_subsequent(self):
        """
        Verify that GBN retransmission includes all subsequent packets.
        
        Validates: Requirement 3.3
        """
        window = SlidingWindow(window_size=10)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Send 8 packets
        sent_seqs = []
        for i in range(8):
            seq = protocol.send_segment(f"packet_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Acknowledge first 3 packets (0, 1, 2)
        protocol.handle_acknowledgment(sent_seqs[2])
        
        # Now unacked packets are 3, 4, 5, 6, 7
        assert protocol.window.get_unacked_count() == 5
        
        # Timeout on packet 4
        retransmit_segments = protocol.handle_timeout(sent_seqs[4])
        
        # Should retransmit packets 4, 5, 6, 7 (all from 4 onward)
        assert len(retransmit_segments) == 4
        retransmit_seqs = [seg.sequence_num for seg in retransmit_segments]
        assert retransmit_seqs == sent_seqs[4:8]


class TestSRSelectiveRetransmissionBehavior:
    """Test SR selective retransmission: only lost packet retransmitted."""
    
    def test_sr_retransmits_only_lost_packet(self):
        """
        Verify that when packet N is lost, SR retransmits only packet N.
        
        Validates: Requirement 3.4 (SR selective retransmission)
        """
        # Create SR protocol with window size 8
        window = SlidingWindow(window_size=8)
        protocol = SRProtocol(window=window, timeout_ms=100)
        
        # Send 5 packets
        sent_seqs = []
        for i in range(5):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Verify 5 packets sent
        assert len(protocol.sent_segments) == 5
        assert protocol.window.get_unacked_count() == 5
        
        # Simulate timeout for packet 2
        timeout_seq = sent_seqs[2]
        retransmit_segments = protocol.handle_timeout(timeout_seq)
        
        # Verify that ONLY packet 2 is retransmitted
        assert len(retransmit_segments) == 1
        assert retransmit_segments[0].sequence_num == timeout_seq
    
    def test_sr_does_not_retransmit_subsequent_packets(self):
        """
        Verify that SR does not retransmit packets after the lost packet.
        
        Validates: Requirement 3.4
        """
        window = SlidingWindow(window_size=10)
        protocol = SRProtocol(window=window, timeout_ms=100)
        
        # Send 8 packets
        sent_seqs = []
        for i in range(8):
            seq = protocol.send_segment(f"packet_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Acknowledge packets 0, 1, 2, 5, 6, 7 (leaving 3, 4 unacked)
        for seq in [sent_seqs[0], sent_seqs[1], sent_seqs[2], 
                    sent_seqs[5], sent_seqs[6], sent_seqs[7]]:
            protocol.handle_acknowledgment(seq)
        
        # Now only packets 3 and 4 are unacked
        assert protocol.window.get_unacked_count() == 2
        
        # Timeout on packet 3
        retransmit_segments = protocol.handle_timeout(sent_seqs[3])
        
        # Should retransmit ONLY packet 3, not packet 4
        assert len(retransmit_segments) == 1
        assert retransmit_segments[0].sequence_num == sent_seqs[3]


class TestWindowConstraint:
    """Test window constraint: unacked packets never exceed window size."""
    
    def test_gbn_window_constraint(self):
        """
        Verify that GBN never exceeds window size for unacked packets.
        
        Validates: Requirement 3.5 (sliding window constraint)
        """
        window_size = 4
        window = SlidingWindow(window_size=window_size)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Send packets up to window size
        for i in range(window_size):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            assert seq is not None
        
        # Verify window is full
        assert protocol.window.get_unacked_count() == window_size
        
        # Try to send one more packet - should fail
        seq = protocol.send_segment(b"extra_data", "dest")
        assert seq is None  # Cannot send, window is full
        
        # Acknowledge one packet
        protocol.handle_acknowledgment(0)
        
        # Now should be able to send one more
        seq = protocol.send_segment(b"new_data", "dest")
        assert seq is not None
        
        # Verify constraint still holds
        assert protocol.window.get_unacked_count() <= window_size
    
    def test_sr_window_constraint(self):
        """
        Verify that SR never exceeds window size for unacked packets.
        
        Validates: Requirement 3.5
        """
        window_size = 6
        window = SlidingWindow(window_size=window_size)
        protocol = SRProtocol(window=window, timeout_ms=100)
        
        # Send packets up to window size
        sent_seqs = []
        for i in range(window_size):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            assert seq is not None
            sent_seqs.append(seq)
        
        # Verify window is full
        assert protocol.window.get_unacked_count() == window_size
        
        # Try to send one more packet - should fail
        seq = protocol.send_segment(b"extra_data", "dest")
        assert seq is None
        
        # Selectively acknowledge packets 1, 3, 5
        for seq in [sent_seqs[1], sent_seqs[3], sent_seqs[5]]:
            protocol.handle_acknowledgment(seq)
        
        # Now should be able to send 3 more packets
        for i in range(3):
            seq = protocol.send_segment(f"new_data_{i}".encode(), "dest")
            assert seq is not None
        
        # Verify constraint still holds
        assert protocol.window.get_unacked_count() <= window_size


class TestCongestionAdaptation:
    """Test congestion adaptation: window reduces on packet loss."""
    
    def test_gbn_window_reduces_on_packet_loss(self):
        """
        Verify that GBN reduces window size when packet loss is detected.
        
        Validates: Requirement 3.6 (congestion adaptation)
        """
        window = SlidingWindow(window_size=16)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Get initial window size
        initial_window = protocol.flow_controller.sender_window_size
        
        # Send some packets
        for i in range(5):
            protocol.send_segment(f"data_{i}".encode(), "dest")
        
        # Simulate packet losses to trigger congestion detection
        for _ in range(10):
            protocol.congestion_detector.record_packet_sent()
            protocol.congestion_detector.record_packet_loss()
        
        # Check that congestion is detected
        assert protocol.congestion_detector.detect_congestion() is True
        
        # Adapt window size
        new_window = protocol.congestion_detector.adapt_window_size(initial_window)
        
        # Verify window size decreased
        assert new_window < initial_window
    
    def test_sr_window_reduces_on_packet_loss(self):
        """
        Verify that SR reduces window size when packet loss is detected.
        
        Validates: Requirement 3.6
        """
        window = SlidingWindow(window_size=16)
        protocol = SRProtocol(window=window, timeout_ms=100)
        
        # Get initial window size
        initial_window = protocol.flow_controller.sender_window_size
        
        # Send some packets
        for i in range(5):
            protocol.send_segment(f"data_{i}".encode(), "dest")
        
        # Simulate packet losses to trigger congestion detection
        for _ in range(10):
            protocol.congestion_detector.record_packet_sent()
            protocol.congestion_detector.record_packet_loss()
        
        # Check that congestion is detected
        assert protocol.congestion_detector.detect_congestion() is True
        
        # Adapt window size
        new_window = protocol.congestion_detector.adapt_window_size(initial_window)
        
        # Verify window size decreased
        assert new_window < initial_window
    
    def test_window_increases_without_congestion(self):
        """
        Verify that window size increases when no congestion is detected.
        
        Validates: Requirement 3.6
        """
        window = SlidingWindow(window_size=8)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Get initial window size
        initial_window = protocol.flow_controller.sender_window_size
        
        # Send packets without loss (low loss rate)
        for _ in range(100):
            protocol.congestion_detector.record_packet_sent()
        # Only 2 losses out of 100 = 2% loss rate (below 5% threshold)
        protocol.congestion_detector.record_packet_loss()
        protocol.congestion_detector.record_packet_loss()
        
        # Check that no congestion is detected
        assert protocol.congestion_detector.detect_congestion() is False
        
        # Adapt window size
        new_window = protocol.congestion_detector.adapt_window_size(initial_window)
        
        # Verify window size increased
        assert new_window > initial_window


class TestProtocolBehaviorIntegration:
    """Integration tests for complete protocol behavior."""
    
    def test_gbn_complete_transmission_with_loss(self):
        """
        Test complete GBN transmission with packet loss and retransmission.
        
        Validates: Requirements 3.1, 3.3, 3.5
        """
        window = SlidingWindow(window_size=4)
        protocol = GBNProtocol(window=window, timeout_ms=100)
        
        # Send 4 packets (fill window)
        sent_seqs = []
        for i in range(4):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Acknowledge first 2 packets
        protocol.handle_acknowledgment(sent_seqs[1])
        
        # Window should slide, allowing 2 more sends
        assert protocol.window.get_unacked_count() == 2
        
        # Send 2 more packets
        for i in range(2):
            seq = protocol.send_segment(f"data_{i+4}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Simulate timeout on packet 2
        retransmit_segments = protocol.handle_timeout(sent_seqs[2])
        
        # Should retransmit packets 2, 3, 4, 5
        assert len(retransmit_segments) == 4
        
        # Acknowledge all packets
        protocol.handle_acknowledgment(sent_seqs[5])
        
        # All packets should be acknowledged
        assert protocol.window.get_unacked_count() == 0
    
    def test_sr_complete_transmission_with_loss(self):
        """
        Test complete SR transmission with packet loss and selective retransmission.
        
        Validates: Requirements 3.2, 3.4, 3.5
        """
        window = SlidingWindow(window_size=4)
        protocol = SRProtocol(window=window, timeout_ms=100)
        
        # Send 4 packets (fill window)
        sent_seqs = []
        for i in range(4):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Selectively acknowledge packets 0, 1, 3 (leaving 2 unacked)
        protocol.handle_acknowledgment(sent_seqs[0])
        protocol.handle_acknowledgment(sent_seqs[1])
        protocol.handle_acknowledgment(sent_seqs[3])
        
        # Window should allow 3 more sends
        assert protocol.window.get_unacked_count() == 1
        
        # Send 3 more packets
        for i in range(3):
            seq = protocol.send_segment(f"data_{i+4}".encode(), "dest")
            sent_seqs.append(seq)
        
        # Simulate timeout on packet 2
        retransmit_segments = protocol.handle_timeout(sent_seqs[2])
        
        # Should retransmit ONLY packet 2
        assert len(retransmit_segments) == 1
        assert retransmit_segments[0].sequence_num == sent_seqs[2]
        
        # Acknowledge remaining packets
        for seq in sent_seqs[2:]:
            protocol.handle_acknowledgment(seq)
        
        # All packets should be acknowledged
        assert protocol.window.get_unacked_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
