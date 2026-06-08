#!/usr/bin/env python3
"""
Dashboard Startup Script

Launches the Adaptive Network Emulator monitoring dashboard.
Access at: http://127.0.0.1:5000
"""

import time
import logging
from src.dashboard import Dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Start the dashboard server."""
    print("=" * 60)
    print("  Adaptive Network Emulator - Monitoring Dashboard")
    print("=" * 60)
    print()
    
    # Create dashboard instance
    dashboard = Dashboard(host="127.0.0.1", port=5000)
    
    # Start the server
    print("Starting dashboard server...")
    dashboard.start(threaded=True)
    
    print()
    print("✓ Dashboard is running!")
    print()
    print("  URL: http://127.0.0.1:5000")
    print()
    print("  Available endpoints:")
    print("    GET  /                      - Dashboard UI")
    print("    GET  /api/metrics           - Current metrics")
    print("    GET  /api/metrics/history   - Historical data")
    print("    GET  /api/topology          - Network topology")
    print("    GET  /api/alerts            - Alert list")
    print("    GET  /api/protocols         - Protocol states")
    print("    GET  /api/events            - SSE real-time stream")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Generate some sample data for demonstration
    print("Generating sample data...")
    dashboard.api.update_metrics_raw(
        throughput_bps=50_000_000,  # 50 Mbps
        latency_mean_ms=15.5,
        latency_p95_ms=23.2,
        loss_pct=0.5,
        jitter_mean_ms=2.3,
        retransmissions=5,
        active_connections=3
    )
    
    # Add sample topology
    dashboard.api.update_topology_raw(
        nodes=[
            {"node_id": "A", "ip_address": "10.0.0.1", "x": 0.2, "y": 0.5, "status": "active"},
            {"node_id": "B", "ip_address": "10.0.0.2", "x": 0.5, "y": 0.2, "status": "active"},
            {"node_id": "C", "ip_address": "10.0.0.3", "x": 0.8, "y": 0.5, "status": "active"},
            {"node_id": "D", "ip_address": "10.0.0.4", "x": 0.5, "y": 0.8, "status": "active"},
        ],
        links=[
            {"source": "A", "target": "B", "cost": 1.0, "utilization": 0.3, "has_packet_flow": True},
            {"source": "B", "target": "C", "cost": 1.0, "utilization": 0.5, "has_packet_flow": True},
            {"source": "C", "target": "D", "cost": 1.0, "utilization": 0.2, "has_packet_flow": False},
            {"source": "D", "target": "A", "cost": 1.0, "utilization": 0.4, "has_packet_flow": True},
        ]
    )
    
    # Add sample alert
    dashboard.api.add_alert(
        "Dashboard started successfully",
        severity="info"
    )
    
    print("✓ Sample data loaded")
    print()
    
    # Keep the server running
    try:
        while dashboard.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down dashboard...")
        dashboard.stop()
        print("✓ Dashboard stopped")


if __name__ == "__main__":
    main()
