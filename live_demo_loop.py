#!/usr/bin/env python3
"""
Continuous Live Network Emulator Demo

This version loops forever - you can open the browser anytime!
The simulation restarts automatically after each cycle.
"""

import time
import random
import logging
from datetime import datetime, timezone

from src.dashboard_enhanced import EnhancedDashboard as Dashboard, ProtocolState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContinuousDemo:
    """Continuous looping demo."""
    
    def __init__(self, dashboard: Dashboard):
        self.dashboard = dashboard
        self.nodes = {"A": "10.0.0.1", "B": "10.0.0.2", "C": "10.0.0.3", "D": "10.0.0.4"}
        self.cycle_count = 0
        
    def reset_metrics(self):
        """Reset metrics for new cycle."""
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.total_packets_lost = 0
        self.total_retransmissions = 0
        self.latencies = []
        self.start_time = time.time()
        
    def setup_network(self):
        """Create network topology."""
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
    
    def simulate_traffic_pattern(self, pattern: str):
        """Simulate different traffic patterns."""
        if pattern == "normal":
            self._send_packet("A", "10.0.0.2", size=1024)
            time.sleep(0.1)
            self._send_packet("C", "10.0.0.4", size=1024)
        elif pattern == "burst":
            for _ in range(5):
                self._send_packet("A", "10.0.0.2", size=2048)
                self._send_packet("B", "10.0.0.3", size=2048)
                time.sleep(0.05)
        elif pattern == "congestion":
            for _ in range(10):
                self._send_packet("A", "10.0.0.2", size=4096)
                self._send_packet("C", "10.0.0.4", size=4096)
                self._send_packet("B", "10.0.0.3", size=4096)
                time.sleep(0.02)
    
    def _send_packet(self, from_node: str, to_ip: str, size: int):
        """Send a packet and track metrics."""
        self.total_packets_sent += 1
        success_rate = 0.95
        latency = random.uniform(5, 50)
        
        if random.random() < success_rate:
            self.total_packets_received += 1
            self.latencies.append(latency)
        else:
            self.total_packets_lost += 1
            if random.random() < 0.8:
                self.total_retransmissions += 1
                self.total_packets_received += 1
                self.latencies.append(latency * 2)
    
    def update_metrics(self):
        """Calculate and push metrics."""
        if self.total_packets_sent == 0:
            return
        
        loss_pct = (self.total_packets_lost / self.total_packets_sent) * 100
        avg_latency = sum(self.latencies[-100:]) / len(self.latencies[-100:]) if self.latencies else 0
        p95_latency = sorted(self.latencies[-100:])[-5] if len(self.latencies) >= 5 else avg_latency
        throughput_bps = (self.total_packets_received / max(1, time.time() - self.start_time)) * 1500 * 8
        
        if len(self.latencies) >= 2:
            jitter = sum(abs(self.latencies[i] - self.latencies[i-1]) 
                        for i in range(1, min(len(self.latencies), 100))) / min(len(self.latencies)-1, 99)
        else:
            jitter = 0
        
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
        """Update topology visualization."""
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
        """Update protocol state."""
        self.dashboard.api.update_protocol_state(
            ProtocolState(
                protocol="Adaptive-TCP",
                window_size=window_size,
                unacked_packets=unacked,
                retransmission_count=self.total_retransmissions,
                state=state
            )
        )
    
    def run_one_cycle(self):
        """Run one complete demo cycle."""
        self.cycle_count += 1
        self.reset_metrics()
        self.setup_network()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} - PHASE 1: Normal Operation (20s)")
        logger.info(f"{'='*60}")
        self.dashboard.api.add_alert(f"Cycle {self.cycle_count} started - Normal traffic", severity="info")
        
        for i in range(40):
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("normal")
            self.update_protocol_state(window_size=32, unacked=2, state="sending")
            time.sleep(0.5)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} - PHASE 2: Traffic Burst (15s)")
        logger.info(f"{'='*60}")
        self.dashboard.api.add_alert("Traffic burst detected", severity="warning")
        
        for i in range(15):
            self.simulate_traffic_pattern("burst")
            self.update_metrics()
            self.update_topology_state("normal")
            self.update_protocol_state(window_size=48, unacked=8, state="sending")
            time.sleep(1.0)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} - PHASE 3: Network Congestion (20s)")
        logger.info(f"{'='*60}")
        self.dashboard.api.add_alert("Network congestion - Reducing window size", severity="critical")
        
        for i in range(40):
            self.simulate_traffic_pattern("congestion")
            self.total_packets_lost += random.randint(2, 5)
            self.update_metrics()
            self.update_topology_state("congestion")
            window = max(8, 48 - i)
            self.update_protocol_state(window_size=window, unacked=window//2, state="congested")
            time.sleep(0.5)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} - PHASE 4: Node Failure (15s)")
        logger.info(f"{'='*60}")
        self.dashboard.api.add_alert("Node C failed - Rerouting", severity="critical")
        
        for i in range(15):
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("failure")
            self.update_protocol_state(window_size=16, unacked=4, state="waiting")
            time.sleep(1.0)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} - PHASE 5: Recovery (15s)")
        logger.info(f"{'='*60}")
        self.dashboard.api.add_alert("Network recovered", severity="info")
        
        for i in range(30):
            self.simulate_traffic_pattern("normal")
            self.update_metrics()
            self.update_topology_state("normal")
            window = min(32, 16 + i)
            self.update_protocol_state(window_size=window, unacked=2, state="sending")
            time.sleep(0.5)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CYCLE {self.cycle_count} COMPLETE")
        logger.info(f"Packets: {self.total_packets_sent} sent, {self.total_packets_received} received")
        logger.info(f"Loss: {self.total_packets_lost} ({(self.total_packets_lost/self.total_packets_sent)*100:.1f}%)")
        logger.info(f"{'='*60}\n")
    
    def run_forever(self):
        """Run demo cycles forever."""
        logger.info("🔄 CONTINUOUS DEMO MODE - Loops forever!")
        logger.info("Open browser anytime: http://127.0.0.1:5000")
        logger.info("Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.run_one_cycle()
                logger.info("⏸️  Waiting 5 seconds before next cycle...\n")
                time.sleep(5)
            except KeyboardInterrupt:
                logger.info("\n\n🛑 Stopping continuous demo...")
                break


def main():
    """Main entry point."""
    print("=" * 70)
    print("  CONTINUOUS NETWORK EMULATOR DEMO")
    print("  Loops Forever - Open Browser Anytime!")
    print("=" * 70)
    print()
    print("This demo runs continuously in a loop.")
    print("You can open the browser at ANY time and see live updates!")
    print()
    print("URL: http://127.0.0.1:5000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Start dashboard
    dashboard = Dashboard(host="127.0.0.1", port=5000)
    dashboard.start(threaded=True)
    
    time.sleep(2)
    
    print("✓ Dashboard started")
    print("✓ Starting continuous simulation...")
    print()
    
    # Run continuous demo
    demo = ContinuousDemo(dashboard)
    
    try:
        demo.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.stop()
        print("✓ Demo stopped")


if __name__ == "__main__":
    main()
