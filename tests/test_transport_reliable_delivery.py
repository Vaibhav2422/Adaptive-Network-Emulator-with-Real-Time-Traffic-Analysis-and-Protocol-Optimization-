"""
Integration tests for Transport Layer reliable delivery under various network conditions.

This module tests reliable delivery with:
- 10% packet loss (delivery rate: 100%)
- 50ms latency variation
- Various window sizes (1, 4, 16, 64)

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import pytest
import time
import random
from src.gbn_protocol import GBNProtocol
from src.sr_protocol import SRProtocol
from src.transport_layer import SlidingWindow
from src.data_models import Segment


class SimulatedNetwork:
    """Simulates network with configurable loss and latency."""
    
    def __init__(self, loss_rate=0.0, latency_ms=0, latency_variation_ms=0):
        self.loss_rate = loss_rate
        self.latency_ms = latency_ms
        self.latency_variation_ms = latency_variation_ms
        self.in_flight_packets = []
        random.seed(42)  # For reproducibility
    
    def send(self, segment, dest):
        """Simulate sending a segment through the network."""
        # Simulate packet loss
        if random.random() < self.loss_rate:
            # Packet is lost
            return False
        
        # Calculate delivery time with latency variation
        base_latency = self.latency_ms / 1000.0  # Convert to seconds
        variation = random.uniform(-self.latency_variation_ms, self.latency_variation_ms) / 1000.0
        delivery_time = time.time() + base_latency + variation
        
        # Store packet for later delivery
        self.in_flight_packets.append((delivery_time, segment, dest))
        return True
    
    def receive(self, current_time):
        """Receive packets that have arrived by current_time."""
        arrived = []
        remaining = []
        
        for delivery_time, segment, dest in self.in_flight_packets:
            if current_time >= delivery_time:
                arrived.append((segment, dest))
            else:
                remaining.append((delivery_time, segment, dest))
        
        self.in_flight_packets = remaining
        return arrived


class TestReliableDeliveryWithPacketLoss:
    """Test reliable delivery with 10% packet loss."""
    
    def test_gbn_reliable_delivery_with_10_percent_loss(self):
        """
        Test GBN reliable delivery with 10% packet loss.
        
        Expected: 100% delivery rate despite packet loss.
        Validates: Requirements 3.1, 3.3, 3.5
        """
        # Create network with 10% loss
        network = SimulatedNetwork(loss_rate=0.1)
        
        # Create GBN protocol with window size 8
        window = SlidingWindow(window_size=8)
        protocol = GBNProtocol(window=window, timeout_ms=50)
        
        # Set up send callback to use simulated network
        sent_packets = []
        def send_callback(segment, dest):
            sent_packets.append(segment.sequence_num)
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send 20 packets
        num_packets = 20
        sent_seqs = []
        for i in range(num_packets):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            if seq is not None:
                sent_seqs.append(seq)
            
            # Process network and acknowledgments
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                # Simulate receiver sending ACK
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check for timeouts and retransmit
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        # Continue processing until all packets are acknowledged
        max_iterations = 100
        iteration = 0
        while protocol.window.get_unacked_count() > 0 and iteration < max_iterations:
            iteration += 1
            time.sleep(0.01)  # Small delay
            
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check for timeouts and retransmit
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        # Verify all packets were eventually acknowledged (100% delivery)
        assert protocol.window.get_unacked_count() == 0
        assert len(sent_seqs) == num_packets
    
    def test_sr_reliable_delivery_with_10_percent_loss(self):
        """
        Test SR reliable delivery with 10% packet loss.
        
        Expected: 100% delivery rate despite packet loss.
        Validates: Requirements 3.2, 3.4, 3.5
        """
        # Create network with 10% loss
        network = SimulatedNetwork(loss_rate=0.1)
        
        # Create SR protocol with window size 8
        window = SlidingWindow(window_size=8)
        protocol = SRProtocol(window=window, timeout_ms=50)
        
        # Set up send callback to use simulated network
        sent_packets = []
        def send_callback(segment, dest):
            sent_packets.append(segment.sequence_num)
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send 20 packets
        num_packets = 20
        sent_seqs = []
        for i in range(num_packets):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            if seq is not None:
                sent_seqs.append(seq)
            
            # Process network and acknowledgments
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                # Simulate receiver sending selective ACK
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check for timeouts and retransmit
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        # Continue processing until all packets are acknowledged
        max_iterations = 100
        iteration = 0
        while protocol.window.get_unacked_count() > 0 and iteration < max_iterations:
            iteration += 1
            time.sleep(0.01)  # Small delay
            
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check for timeouts and retransmit
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        # Verify all packets were eventually acknowledged (100% delivery)
        assert protocol.window.get_unacked_count() == 0
        assert len(sent_seqs) == num_packets


class TestReliableDeliveryWithLatencyVariation:
    """Test reliable delivery with 50ms latency variation."""
    
    def test_gbn_with_latency_variation(self):
        """
        Test GBN with 50ms latency variation.
        
        Expected: Successful delivery, slower completion.
        Validates: Requirements 3.1, 3.6
        """
        # Create network with latency variation
        network = SimulatedNetwork(loss_rate=0.0, latency_ms=20, latency_variation_ms=50)
        
        # Create GBN protocol
        window = SlidingWindow(window_size=4)
        protocol = GBNProtocol(window=window, timeout_ms=200)  # Higher timeout for latency
        
        # Set up send callback
        def send_callback(segment, dest):
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send 10 packets
        num_packets = 10
        sent_seqs = []
        start_time = time.time()
        
        for i in range(num_packets):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            if seq is not None:
                sent_seqs.append(seq)
            
            # Process network
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            time.sleep(0.01)  # Small delay between sends
        
        # Continue processing until all acknowledged
        max_iterations = 200
        iteration = 0
        while protocol.window.get_unacked_count() > 0 and iteration < max_iterations:
            iteration += 1
            time.sleep(0.01)
            
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all packets delivered
        assert protocol.window.get_unacked_count() == 0
        # Verify it took some time due to latency (at least 0.1 seconds)
        assert duration > 0.1
    
    def test_sr_with_latency_variation(self):
        """
        Test SR with 50ms latency variation.
        
        Expected: Successful delivery, slower completion.
        Validates: Requirements 3.2, 3.6
        """
        # Create network with latency variation
        network = SimulatedNetwork(loss_rate=0.0, latency_ms=20, latency_variation_ms=50)
        
        # Create SR protocol
        window = SlidingWindow(window_size=4)
        protocol = SRProtocol(window=window, timeout_ms=200)
        
        # Set up send callback
        def send_callback(segment, dest):
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send 10 packets
        num_packets = 10
        sent_seqs = []
        start_time = time.time()
        
        for i in range(num_packets):
            seq = protocol.send_segment(f"data_{i}".encode(), "dest")
            if seq is not None:
                sent_seqs.append(seq)
            
            # Process network
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            time.sleep(0.01)
        
        # Continue processing until all acknowledged
        max_iterations = 200
        iteration = 0
        while protocol.window.get_unacked_count() > 0 and iteration < max_iterations:
            iteration += 1
            time.sleep(0.01)
            
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all packets delivered
        assert protocol.window.get_unacked_count() == 0
        # Verify it took some time due to latency
        assert duration > 0.1


class TestVariousWindowSizes:
    """Test with various window sizes (1, 4, 16, 64)."""
    
    @pytest.mark.parametrize("window_size", [1, 4, 16, 64])
    def test_gbn_with_various_window_sizes(self, window_size):
        """
        Test GBN with various window sizes.
        
        Expected: All data delivered correctly regardless of window size.
        Validates: Requirements 3.1, 3.5
        """
        # Create network with some loss
        network = SimulatedNetwork(loss_rate=0.05)
        
        # Create GBN protocol with specified window size
        window = SlidingWindow(window_size=window_size)
        protocol = GBNProtocol(window=window, timeout_ms=50)
        
        # Set up send callback
        def send_callback(segment, dest):
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send packets
        num_packets = 15
        sent_seqs = []
        packets_to_send = num_packets
        
        # Send and process loop
        max_iterations = 300
        iteration = 0
        while (packets_to_send > 0 or protocol.window.get_unacked_count() > 0) and iteration < max_iterations:
            iteration += 1
            
            # Try to send if we have more packets to send
            if packets_to_send > 0 and protocol.window.can_send():
                seq = protocol.send_segment(f"data_{len(sent_seqs)}".encode(), "dest")
                if seq is not None:
                    sent_seqs.append(seq)
                    packets_to_send -= 1
            
            # Process network
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check timeouts
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
            
            time.sleep(0.005)
        
        # Verify all packets delivered
        assert protocol.window.get_unacked_count() == 0
        assert len(sent_seqs) == num_packets
    
    @pytest.mark.parametrize("window_size", [1, 4, 16, 64])
    def test_sr_with_various_window_sizes(self, window_size):
        """
        Test SR with various window sizes.
        
        Expected: All data delivered correctly regardless of window size.
        Validates: Requirements 3.2, 3.5
        """
        # Create network with some loss
        network = SimulatedNetwork(loss_rate=0.05)
        
        # Create SR protocol with specified window size
        window = SlidingWindow(window_size=window_size)
        protocol = SRProtocol(window=window, timeout_ms=50)
        
        # Set up send callback
        def send_callback(segment, dest):
            network.send(segment, dest)
        
        protocol.send_callback = send_callback
        
        # Send packets
        num_packets = 15
        sent_seqs = []
        packets_to_send = num_packets
        
        # Send and process loop
        max_iterations = 300
        iteration = 0
        while (packets_to_send > 0 or protocol.window.get_unacked_count() > 0) and iteration < max_iterations:
            iteration += 1
            
            # Try to send if we have more packets to send
            if packets_to_send > 0 and protocol.window.can_send():
                seq = protocol.send_segment(f"data_{len(sent_seqs)}".encode(), "dest")
                if seq is not None:
                    sent_seqs.append(seq)
                    packets_to_send -= 1
            
            # Process network
            current_time = time.time()
            arrived = network.receive(current_time)
            for segment, dest in arrived:
                protocol.handle_acknowledgment(segment.sequence_num)
            
            # Check timeouts
            timed_out = protocol.check_timeouts()
            for seq_num, segments in timed_out:
                for seg in segments:
                    network.send(seg, "dest")
            
            time.sleep(0.005)
        
        # Verify all packets delivered
        assert protocol.window.get_unacked_count() == 0
        assert len(sent_seqs) == num_packets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
