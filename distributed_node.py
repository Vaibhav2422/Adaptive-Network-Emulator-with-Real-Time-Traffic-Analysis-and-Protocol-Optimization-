#!/usr/bin/env python3
"""
Distributed Network Node

Run this on multiple laptops to create a real distributed network!

Usage:
    Laptop 1 (Dashboard + Node A):
        python distributed_node.py --node A --dashboard

    Laptop 2 (Node B):
        python distributed_node.py --node B --peer 192.168.1.100

    Laptop 3 (Node C):
        python distributed_node.py --node C --peer 192.168.1.100

    Laptop 4 (Node D):
        python distributed_node.py --node D --peer 192.168.1.100
"""

import socket
import threading
import time
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistributedNode:
    """A network node that can run on a separate machine."""
    
    def __init__(self, node_id: str, port: int = 5001, dashboard_host: Optional[str] = None):
        self.node_id = node_id
        self.port = port
        self.dashboard_host = dashboard_host
        self.peers: Dict[str, str] = {}
        self.running = False
        
        # Packet counters
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0
        self.bytes_received = 0

        # Latency tracking: seq -> send_time
        self._pending_acks: Dict[int, float] = {}
        self._seq = 0
        self._lock = threading.Lock()

        # Rolling latency samples (last 50)
        self._latency_samples: List[float] = []
        self._prev_latency: float = 0.0

        # Throughput window
        self._bytes_in_window = 0
        self._window_start = time.time()

        # Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        """Start the node."""
        self.running = True
        
        # Bind to port
        self.sock.bind(('0.0.0.0', self.port))
        logger.info(f"Node {self.node_id} started on port {self.port}")
        
        # Start receiver thread
        receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        receiver_thread.start()
        
        # Start sender thread
        sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        sender_thread.start()
        
        # Start metrics reporter thread
        if self.dashboard_host:
            metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
            metrics_thread.start()
        
        logger.info(f"Node {self.node_id} is ready!")
        
    def add_peer(self, node_id: str, ip_address: str, port: int = 5001):
        """Add a peer node."""
        self.peers[node_id] = (ip_address, port)
        logger.info(f"Added peer {node_id} at {ip_address}:{port}")
        
    def send_packet(self, dest_node: str, data: str):
        """Send a packet to another node."""
        if dest_node not in self.peers:
            logger.warning(f"Unknown peer: {dest_node}")
            return
        
        with self._lock:
            self._seq += 1
            seq = self._seq

        packet = {
            'from': self.node_id,
            'to': dest_node,
            'data': data,
            'seq': seq,
            'timestamp': time.time()
        }
        
        try:
            ip, port = self.peers[dest_node]
            raw = json.dumps(packet).encode()
            self.sock.sendto(raw, (ip, port))
            with self._lock:
                self._pending_acks[seq] = time.time()
            self.packets_sent += 1
            logger.info(f"Sent packet to {dest_node}: {data[:50]}")
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")
            self.packets_lost += 1
    
    def _receive_loop(self):
        """Receive packets from other nodes."""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                packet = json.loads(data.decode())
                recv_time = time.time()

                # Handle ACK: measure round-trip latency
                if packet.get('type') == 'ACK':
                    seq = packet.get('seq')
                    with self._lock:
                        send_time = self._pending_acks.pop(seq, None)
                    if send_time:
                        rtt_ms = (recv_time - send_time) * 1000
                        with self._lock:
                            self._latency_samples.append(rtt_ms)
                            if len(self._latency_samples) > 50:
                                self._latency_samples.pop(0)
                    continue

                if packet['to'] == self.node_id:
                    raw_size = len(data)
                    self.packets_received += 1
                    self.bytes_received += raw_size
                    with self._lock:
                        self._bytes_in_window += raw_size
                    sender_id = packet['from']
                    logger.info(f"Received packet from {sender_id}: {packet['data'][:50]}")

                    # ACK with original seq so sender can measure RTT
                    ack = {
                        'from': self.node_id,
                        'to': sender_id,
                        'type': 'ACK',
                        'seq': packet.get('seq'),
                        'timestamp': recv_time
                    }
                    if sender_id in self.peers:
                        peer_ip, peer_port = self.peers[sender_id]
                        self.sock.sendto(json.dumps(ack).encode(), (peer_ip, peer_port))
                    else:
                        self.sock.sendto(json.dumps(ack).encode(), (addr[0], self.port))

            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
    
    def _send_loop(self):
        """Periodically send test packets."""
        while self.running:
            time.sleep(2)
            
            # Send to all peers
            for peer_id in self.peers:
                data = f"Hello from {self.node_id} at {datetime.now().isoformat()}"
                self.send_packet(peer_id, data)
    
    def _metrics_loop(self):
        """Report metrics to dashboard."""
        import requests
        while self.running:
            time.sleep(1)

            if self.dashboard_host:
                try:
                    now = time.time()

                    # Throughput: bytes received in last window
                    with self._lock:
                        elapsed = now - self._window_start
                        throughput_bps = (self._bytes_in_window * 8 / elapsed) if elapsed > 0 else 0.0
                        self._bytes_in_window = 0
                        self._window_start = now

                        # Latency mean + jitter
                        samples = list(self._latency_samples)

                    if samples:
                        latency_mean = sum(samples) / len(samples)
                        if len(samples) > 1:
                            diffs = [abs(samples[i] - samples[i-1]) for i in range(1, len(samples))]
                            jitter = sum(diffs) / len(diffs)
                        else:
                            jitter = 0.0
                        self._prev_latency = latency_mean
                    else:
                        latency_mean = self._prev_latency
                        jitter = 0.0

                    # Packet loss %
                    total = self.packets_sent + self.packets_lost
                    loss_pct = (self.packets_lost / total * 100) if total > 0 else 0.0

                    metrics = {
                        'node_id': self.node_id,
                        'packets_sent': self.packets_sent,
                        'packets_received': self.packets_received,
                        'packets_lost': self.packets_lost,
                        'throughput_bps': throughput_bps,
                        'latency_mean_ms': latency_mean,
                        'jitter_ms': jitter,
                        'loss_pct': loss_pct,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

                    requests.post(
                        f"http://{self.dashboard_host}:5000/api/node_metrics",
                        json=metrics,
                        timeout=1
                    )
                except Exception as e:
                    logger.debug(f"Failed to send metrics: {e}")
    
    def stop(self):
        """Stop the node."""
        self.running = False
        self.sock.close()
        logger.info(f"Node {self.node_id} stopped")


def main():
    parser = argparse.ArgumentParser(description='Distributed Network Node')
    parser.add_argument('--node', required=True, choices=['A', 'B', 'C', 'D'],
                       help='Node ID (A, B, C, or D)')
    parser.add_argument('--port', type=int, default=5001,
                       help='Port to listen on (default: 5001)')
    parser.add_argument('--peer', action='append',
                       help='Peer IP address (can specify multiple times)')
    parser.add_argument('--dashboard', action='store_true',
                       help='Run dashboard on this machine')
    parser.add_argument('--dashboard-host', type=str,
                       help='Dashboard host IP (for sending metrics)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"  DISTRIBUTED NETWORK NODE {args.node}")
    print("=" * 70)
    print()
    
    # If this machine hosts the dashboard, report metrics to localhost
    dashboard_host = args.dashboard_host
    if args.dashboard and not dashboard_host:
        dashboard_host = "127.0.0.1"

    # Create node
    node = DistributedNode(
        node_id=args.node,
        port=args.port,
        dashboard_host=dashboard_host
    )
    
    # Add peers
    if args.peer:
        peer_ids = ['A', 'B', 'C', 'D']
        peer_ids.remove(args.node)  # Remove self
        
        for i, peer_ip in enumerate(args.peer):
            if i < len(peer_ids):
                node.add_peer(peer_ids[i], peer_ip, args.port)
    
    # Start dashboard if requested
    if args.dashboard:
        print("Starting dashboard...")
        from src.dashboard_enhanced import EnhancedDashboard as Dashboard
        dashboard = Dashboard(host="0.0.0.0", port=5000)
        dashboard.start(threaded=True)
        print(f"✓ Dashboard started at http://0.0.0.0:5000")
        print()
    
    # Start node
    node.start()
    
    print()
    print(f"Node {args.node} Configuration:")
    print(f"  - Listening on: 0.0.0.0:{args.port}")
    print(f"  - Peers: {list(node.peers.keys())}")
    if args.dashboard:
        print(f"  - Dashboard: http://0.0.0.0:5000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping node...")
        node.stop()
        print("✓ Node stopped")


if __name__ == "__main__":
    main()
