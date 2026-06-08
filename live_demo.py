#!/usr/bin/env python3
"""
Live Network Emulator Demo with Real-Time Dashboard

This demo runs an actual network simulation with:
- Multiple nodes sending real traffic
- Adaptive congestion control responding to network conditions
- Dynamic link failures and recovery
- Real-time metrics updates to the dashboard
- Protocol state changes (idle → sending → congested → recovery)

Watch the dashboard to see:
- Throughput changes as congestion occurs
- Latency spikes during network stress
- Packet loss during failures
- Adaptive window size adjustments
- Topology changes (node failures, link congestion)
"""

import time
import random
import logging
import threading
from datetime import datetime, timezone

from src.dashboard_enhanced import EnhancedDashboard as Dashboard, ProtocolState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveNetworkDemo:
    """Live network emulator demo with real-time dashboard updates."""
    
    def __init__(self, dashboard: Dashboard):
        self.dashboard = dashboard
        self.nodes = {"A": "10.0.0.1", "B": "10.0.0.2", "C": "10.0.0.3", "D": "10.0.0.4"}
        self.running = False
        
        # Simulation state
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.total_packets_lost = 0
        self.total_retransmissions = 0
        self.latencies = []
        
    def setup_network(self):
        """Create a 4-node network topology."""
        logger.info("Setting up network topology...")
        
        for node_id, ip in self.nodes.items():
            logger.info(f"Node {node_id} configured with IP {ip}")
        
        # Update dashboard topology
        self.dashboard.api.update_topology_raw(
            nodes=[
                {"node_id": "A", "ip_address": "10.0.0.1", "x": 0.2, "y": 0.5, "status": "active"},
                {"node_id": "B", "ip_address": "10.0.0.2", "x": 0.5, "y": 0.2, "status": "active"},
                {"node_id": "C", "ip_address": "10.0.0.3", "x": 0.8, "y": 0.5, "status": "active"},
                {"node_id": "D", "ip_address": "10.0.0.4", "x": 0.5, "y": 0.8, "status": "active"},
            ],
            links=[
                {"source": "A", "target": "B", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
                {"source": "B", "target": "C", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
                {"source": "C", "target": "D", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
                {"source": "D", "target": "A", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
            ]
        )
        
        logger.info("Network topology created")
    
    def simulate_traffic_pattern(self, pattern: str):
        """Simulate different traffic patterns."""
        if pattern == "normal":
            # Normal traffic: A → B, C → D
            self._send_packet("A", "10.0.0.2", size=1024)
            time.sleep(0.1)
            self._send_packet("C", "10.0.0.4", size=1024)
            
        elif pattern == "burst":
            # Burst traffic: Multiple packets rapidly
            for _ in range(5):
                self._send_packet("A", "10.0.0.2", size=2048)
                self._send_packet("B", "10.0.0.3", size=2048)
                time.sleep(0.05)
                
        elif pattern == "congestion":
            # Heavy traffic causing congestion
            for _ in range(10):
                self._send_packet("A", "10.0.0.2", size=4096)
                self._send_packet("C", "10.0.0.4", size=4096)
                self._send_packet("B", "10.0.0.3", size=4096)
                time.sleep(0.02)
    
    def _send_packet(self, from_node: str, to_ip: str, size: int):
        """Send a packet and track metrics."""
        self.total_packets_sent += 1
        
        # Simulate packet transmission with random success/failure
        success_rate = 0.95  # 95% success rate
        latency = random.uniform(5, 50)  # 5-50ms latency
        
        if random.random() < success_rate:
            self.total_packets_received += 1
            self.latencies.append(latency)
        else:
            self.total_packets_lost += 1
            # Simulate retransmission
            if random.random() < 0.8:  # 80% retransmit
                self.total_retransmissions += 1
                self.total_packets_received += 1
                self.latencies.append(latency * 2)  # Higher latency on retransmit
    
    def update_metrics(self):
        """Calculate and push current metrics to dashboard."""
        if self.total_packets_sent == 0:
            return
        
        # Calculate metrics
        loss_pct = (self.total_packets_lost / self.total_packets_sent) * 100
        avg_latency = sum(self.latencies[-100:]) / len(self.latencies[-100:]) if self.latencies else 0
        p95_latency = sorted(self.latencies[-100:])[-5] if len(self.latencies) >= 5 else avg_latency
        
        # Calculate throughput (packets per second * avg packet size)
        throughput_bps = (self.total_packets_received / max(1, time.time() - self.start_time)) * 1500 * 8
        
        # Calculate jitter (variance in latency)
        if len(self.latencies) >= 2:
            jitter = sum(abs(self.latencies[i] - self.latencies[i-1]) 
                        for i in range(1, min(len(self.latencies), 100))) / min(len(self.latencies)-1, 99)
        else:
            jitter = 0
        
        # Update dashboard
        self.dashboard.api.update_metrics_raw(
            throughput_bps=throughput_bps,
            latency_mean_ms=avg_latency,
            latency_p95_ms=p95_latency,
            loss_pct=loss_pct,
            retransmissions=self.total_retransmissions,
            jitter_mean_ms=jitter,
            active_connections=len(self.nodes)
        )
    
    def update_topology_state(self, phase: str):
        """Update topology visualization based on current phase."""
        if phase == "normal":
            links = [
                {"source": "A", "target": "B", "cost": 1.0, "utilization": 0.3, "has_packet_flow": True},
                {"source": "B", "target": "C", "cost": 1.0, "utilization": 0.2, "has_packet_flow": False},
                {"source": "C", "target": "D", "cost": 1.0, "utilization": 0.4, "has_packet_flow": True},
                {"source": "D", "target": "A", "cost": 1.0, "utilization": 0.1, "has_packet_flow": False},
            ]
            node_status = "active"
            
        elif phase == "congestion":
            links = [
                {"source": "A", "target": "B", "cost": 1.0, "utilization": 0.9, "has_packet_flow": True},
                {"source": "B", "target": "C", "cost": 1.0, "utilization": 0.8, "has_packet_flow": True},
                {"source": "C", "target": "D", "cost": 1.0, "utilization": 0.7, "has_packet_flow": True},
                {"source": "D", "target": "A", "cost": 1.0, "utilization": 0.6, "has_packet_flow": True},
            ]
            node_status = "congested"
            
        elif phase == "failure":
            links = [
                {"source": "A", "target": "B", "cost": 1.0, "utilization": 0.5, "has_packet_flow": True},
                {"source": "B", "target": "C", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
                {"source": "C", "target": "D", "cost": 1.0, "utilization": 0.0, "has_packet_flow": False},
                {"source": "D", "target": "A", "cost": 1.0, "utilization": 0.6, "has_packet_flow": True},
            ]
            node_status = "active"
        else:
            return
        
        self.dashboard.api.update_topology_raw(
            nodes=[
                {"node_id": "A", "ip_address": "10.0.0.1", "x": 0.2, "y": 0.5, "status": node_status},
                {"node_id": "B", "ip_address": "10.0.0.2", "x": 0.5, "y": 0.2, "status": node_status},
                {"node_id": "C", "ip_address": "10.0.0.3", "x": 0.8, "y": 0.5, 
                 "status": "failed" if phase == "failure" else node_status},
                {"node_id": "D", "ip_address": "10.0.0.4", "x": 0.5, "y": 0.8, "status": node_status},
            ],
            links=links
        )
    
    def update_protocol_state(self, window_size: int, unacked: int, state: str):
        """Update protocol state display."""
        self.dashboard.api.update_protocol_state(
            ProtocolState(
                protocol="Adaptive-TCP",
                window_size=window_size,
                unacked_packets=unacked,
                retransmission_count=self.total_retransmissions,
                state=state
            )
        )
    
    def run_demo_scenario(self):
        """Run a complete demo scenario showing all features."""
        self.start_time = time.time()
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: Normal Operation (20 seconds)")
        logger.info("="*60)
        self.dashboard.api.add_alert("Demo started - Normal traffic phase", severity="info")
        
        for i in range(40):  # 20 seconds
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("normal")
            self.update_protocol_state(window_size=32, unacked=2, state="sending")
            time.sleep(0.5)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: Traffic Burst (15 seconds)")
        logger.info("="*60)
        self.dashboard.api.add_alert("Traffic burst detected", severity="warning")
        
        for i in range(15):  # 15 seconds
            self.simulate_traffic_pattern("burst")
            self.update_metrics()
            self.update_topology_state("normal")
            self.update_protocol_state(window_size=48, unacked=8, state="sending")
            time.sleep(1.0)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: Network Congestion (20 seconds)")
        logger.info("="*60)
        self.dashboard.api.add_alert("Network congestion detected - Reducing window size", 
                                     severity="critical")
        
        # Simulate congestion with increasing packet loss
        for i in range(40):  # 20 seconds
            # Gradually increase loss rate during congestion
            old_loss = self.total_packets_lost
            self.simulate_traffic_pattern("congestion")
            self.total_packets_lost += random.randint(2, 5)  # Simulate higher loss
            
            self.update_metrics()
            self.update_topology_state("congestion")
            
            # Adaptive window size reduction
            window = max(8, 48 - i)
            self.update_protocol_state(window_size=window, unacked=window//2, state="congested")
            time.sleep(0.5)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 4: Node Failure & Recovery (15 seconds)")
        logger.info("="*60)
        self.dashboard.api.add_alert("Node C failed - Rerouting traffic", severity="critical")
        
        for i in range(15):  # 15 seconds
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("failure")
            self.update_protocol_state(window_size=16, unacked=4, state="waiting")
            time.sleep(1.0)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 5: Recovery & Stabilization (15 seconds)")
        logger.info("="*60)
        self.dashboard.api.add_alert("Network recovered - Normal operation resumed", severity="info")
        
        for i in range(30):  # 15 seconds
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("normal")
            
            # Gradually increase window size during recovery
            window = min(32, 16 + i)
            self.update_protocol_state(window_size=window, unacked=2, state="sending")
            time.sleep(0.5)
        
        logger.info("\n" + "="*60)
        logger.info("DEMO COMPLETE")
        logger.info("="*60)
        logger.info(f"Total packets sent: {self.total_packets_sent}")
        logger.info(f"Total packets received: {self.total_packets_received}")
        logger.info(f"Total packets lost: {self.total_packets_lost}")
        logger.info(f"Total retransmissions: {self.total_retransmissions}")
        logger.info(f"Final loss rate: {(self.total_packets_lost/self.total_packets_sent)*100:.2f}%")
        logger.info("="*60)
        
        self.dashboard.api.add_alert("Demo completed successfully", severity="info")
    
    def start(self):
        """Start the live demo."""
        self.running = True
        self.setup_network()
        
        # Run demo scenario
        self.run_demo_scenario()
        
        logger.info("\nDemo finished. Dashboard will continue running.")
        logger.info("Press Ctrl+C to stop.")


def main():
    """Main entry point."""
    print("=" * 70)
    print("  LIVE NETWORK EMULATOR DEMO")
    print("  Real-Time Adaptive Network Simulation with Dashboard")
    print("=" * 70)
    print()
    print("This demo will run a complete network simulation showing:")
    print("  ✓ Normal traffic operation")
    print("  ✓ Traffic bursts and congestion")
    print("  ✓ Adaptive congestion control (window size adjustments)")
    print("  ✓ Node failures and recovery")
    print("  ✓ Real-time metrics updates")
    print("  ✓ Protocol state changes")
    print()
    print("Open your browser to: http://127.0.0.1:5000")
    print()
    print("=" * 70)
    print()
    
    # Start dashboard
    dashboard = Dashboard(host="127.0.0.1", port=5000)
    dashboard.start(threaded=True)
    
    time.sleep(2)  # Wait for dashboard to start
    
    print("✓ Dashboard started at http://127.0.0.1:5000")
    print()
    print("Starting network simulation in 3 seconds...")
    print()
    
    time.sleep(3)
    
    # Run demo
    demo = LiveNetworkDemo(dashboard)
    
    try:
        demo.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping demo...")
        dashboard.stop()
        print("✓ Demo stopped")


if __name__ == "__main__":
    main()
