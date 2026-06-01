"""
Monitoring Dashboard for the Adaptive Network Emulator.

Provides a Flask web server with REST API, SSE real-time updates,
alert management, and historical data storage.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""

import json
import logging
import queue
import time
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Flask import with graceful fallback
try:
    from flask import Flask, jsonify, request, Response, render_template_string
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not available. Dashboard will run in mock mode.")


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class MetricSnapshot:
    """A timestamped snapshot of network metrics."""
    timestamp: str
    throughput_bps: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p95_ms: float = 0.0
    loss_pct: float = 0.0
    retransmissions: int = 0
    jitter_mean_ms: float = 0.0
    active_connections: int = 0


@dataclass
class TopologyNode:
    """Node data for topology rendering."""
    node_id: str
    ip_address: str
    x: float = 0.0
    y: float = 0.0
    status: str = "active"   # active | congested | failed


@dataclass
class TopologyLink:
    """Link data for topology rendering."""
    source: str
    target: str
    cost: float = 1.0
    utilization: float = 0.0
    has_packet_flow: bool = False


@dataclass
class TopologyData:
    """Complete topology snapshot for frontend rendering."""
    nodes: List[TopologyNode] = field(default_factory=list)
    links: List[TopologyLink] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Alert:
    """A dashboard alert."""
    alert_id: str
    timestamp: str
    severity: str          # info | warning | critical
    message: str
    metric_name: str = ""
    metric_value: float = 0.0
    acknowledged: bool = False


@dataclass
class ProtocolState:
    """Protocol state for display."""
    protocol: str
    window_size: int = 0
    unacked_packets: int = 0
    retransmission_count: int = 0
    state: str = "idle"    # idle | sending | waiting | congested


# ─────────────────────────────────────────────
# MetricsAPI  (task 22.2)
# ─────────────────────────────────────────────

class MetricsAPI:
    """
    Backend logic for serving metrics, topology, alerts, and history.

    Validates: Requirements 9.1, 9.2, 9.3, 9.6, 9.7
    """

    MAX_HISTORY = 500   # maximum historical snapshots kept

    def __init__(self):
        self._current_metrics = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._topology  = TopologyData()
        self._alerts: List[Alert] = []
        self._protocol_states: Dict[str, ProtocolState] = {}
        self._alert_counter = 0

        # SSE event queue (one per connected client)
        self._sse_queues: List[queue.Queue] = []
        self._lock = threading.Lock()

        # Thresholds for auto-alerts
        self._alert_thresholds = {
            "loss_pct":        10.0,
            "latency_mean_ms": 200.0,
            "throughput_bps":  10_000.0,   # minimum expected
        }

    # ── Metric ingestion ──────────────────────────────────────────────────

    def update_metrics(self, metrics: MetricSnapshot) -> None:
        """
        Push a new metrics snapshot.

        Stores in history, checks alert thresholds, and broadcasts via SSE.

        Validates: Requirements 9.1, 9.6
        """
        with self._lock:
            self._current_metrics = metrics
            self._history.append(metrics)

        # Auto-generate alerts on threshold breaches
        self._check_alert_thresholds(metrics)

        # Broadcast to all SSE clients
        self._broadcast_event("metrics", asdict(metrics))

    def update_metrics_raw(
        self,
        throughput_bps: float = 0.0,
        latency_mean_ms: float = 0.0,
        latency_p95_ms: float = 0.0,
        loss_pct: float = 0.0,
        retransmissions: int = 0,
        jitter_mean_ms: float = 0.0,
        active_connections: int = 0,
    ) -> MetricSnapshot:
        """Convenience method — build and push a snapshot from raw values."""
        snap = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            throughput_bps=throughput_bps,
            latency_mean_ms=latency_mean_ms,
            latency_p95_ms=latency_p95_ms,
            loss_pct=loss_pct,
            retransmissions=retransmissions,
            jitter_mean_ms=jitter_mean_ms,
            active_connections=active_connections,
        )
        self.update_metrics(snap)
        return snap

    # ── Topology ──────────────────────────────────────────────────────────

    def update_topology(self, topology: TopologyData) -> None:
        """
        Update topology data for rendering.

        Validates: Requirement 9.2
        """
        with self._lock:
            self._topology = topology
        self._broadcast_event("topology", self._topology_to_dict())

    def update_topology_raw(
        self,
        nodes: List[Dict],
        links: List[Dict],
    ) -> TopologyData:
        """Convenience method — build topology from raw dicts."""
        topo_nodes = [TopologyNode(**n) for n in nodes]
        topo_links = [TopologyLink(**lnk) for lnk in links]
        topo = TopologyData(nodes=topo_nodes, links=topo_links)
        self.update_topology(topo)
        return topo

    def get_topology(self) -> Dict:
        """Return current topology as a dict."""
        with self._lock:
            return self._topology_to_dict()

    def _topology_to_dict(self) -> Dict:
        return {
            "nodes": [asdict(n) for n in self._topology.nodes],
            "links": [asdict(lnk) for lnk in self._topology.links],
            "timestamp": self._topology.timestamp,
        }

    # ── Alerts ────────────────────────────────────────────────────────────

    def add_alert(
        self,
        message: str,
        severity: str = "warning",
        metric_name: str = "",
        metric_value: float = 0.0,
    ) -> Alert:
        """
        Add a manual alert.

        Validates: Requirement 9.3
        """
        self._alert_counter += 1
        alert = Alert(
            alert_id=f"alert_{self._alert_counter}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            message=message,
            metric_name=metric_name,
            metric_value=metric_value,
        )
        with self._lock:
            self._alerts.append(alert)
        self._broadcast_event("alert", asdict(alert))
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert by ID."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def get_alerts(self, unacknowledged_only: bool = False) -> List[Dict]:
        """Return alerts as a list of dicts."""
        with self._lock:
            alerts = list(self._alerts)
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return [asdict(a) for a in alerts]

    def _check_alert_thresholds(self, metrics: MetricSnapshot) -> None:
        """Auto-generate alerts when metrics exceed thresholds."""
        if metrics.loss_pct >= self._alert_thresholds["loss_pct"]:
            self.add_alert(
                f"High packet loss: {metrics.loss_pct:.1f}%",
                severity="critical",
                metric_name="loss_pct",
                metric_value=metrics.loss_pct,
            )
        if metrics.latency_mean_ms >= self._alert_thresholds["latency_mean_ms"]:
            self.add_alert(
                f"High latency: {metrics.latency_mean_ms:.1f}ms",
                severity="warning",
                metric_name="latency_mean_ms",
                metric_value=metrics.latency_mean_ms,
            )

    # ── Protocol state ────────────────────────────────────────────────────

    def update_protocol_state(self, state: ProtocolState) -> None:
        """Update protocol state for a specific protocol."""
        with self._lock:
            self._protocol_states[state.protocol] = state
        self._broadcast_event("protocol_state", asdict(state))

    def get_protocol_states(self) -> List[Dict]:
        with self._lock:
            return [asdict(s) for s in self._protocol_states.values()]

    # ── Historical data ───────────────────────────────────────────────────

    def get_current_metrics(self) -> Dict:
        """Return the most recent metrics snapshot."""
        with self._lock:
            return asdict(self._current_metrics)

    def get_history(self, limit: int = 100) -> List[Dict]:
        """
        Return recent metrics history.

        Validates: Requirement 9.7
        """
        with self._lock:
            items = list(self._history)
        return [asdict(m) for m in items[-limit:]]

    def get_history_count(self) -> int:
        """Return number of stored historical snapshots."""
        with self._lock:
            return len(self._history)

    # ── SSE broadcasting ──────────────────────────────────────────────────

    def register_sse_client(self) -> "queue.Queue":
        """Register a new SSE client and return its event queue."""
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._sse_queues.append(q)
        return q

    def unregister_sse_client(self, q: "queue.Queue") -> None:
        """Remove an SSE client queue."""
        with self._lock:
            try:
                self._sse_queues.remove(q)
            except ValueError:
                pass

    def _broadcast_event(self, event_type: str, data: Dict) -> None:
        """Send an SSE event to all connected clients."""
        payload = json.dumps({"type": event_type, "data": data,
                              "timestamp": datetime.now(timezone.utc).isoformat()})
        dead: List[queue.Queue] = []
        with self._lock:
            queues = list(self._sse_queues)
        for q in queues:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            self.unregister_sse_client(q)

    def get_last_update_time(self) -> float:
        """Return epoch time of the most recent metrics update."""
        with self._lock:
            snap = self._current_metrics
        try:
            dt = datetime.fromisoformat(snap.timestamp)
            return dt.timestamp()
        except Exception:
            return 0.0


# ─────────────────────────────────────────────
# Dashboard  (task 22.1)
# ─────────────────────────────────────────────

class Dashboard:
    """
    Flask-based monitoring dashboard.

    REST endpoints:
      GET  /api/metrics           → current metrics
      GET  /api/metrics/history   → historical metrics
      GET  /api/topology          → topology data
      GET  /api/alerts            → alerts list
      POST /api/alerts/<id>/ack   → acknowledge alert
      GET  /api/protocols         → protocol states
      POST /api/control/start     → start emulator
      POST /api/control/stop      → stop emulator
      GET  /api/events            → SSE stream (real-time)
      GET  /                      → dashboard HTML

    Validates: Requirements 9.1–9.7
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.api  = MetricsAPI()
        self._app: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        if FLASK_AVAILABLE:
            self._build_app()

    def _build_app(self) -> None:
        """Build the Flask app with all routes."""
        app = Flask(__name__)
        CORS(app)   # Enable CORS for development

        api = self.api

        # ── REST API routes ───────────────────────────────────────────────

        @app.route("/api/metrics")
        def get_metrics():
            return jsonify(api.get_current_metrics())

        @app.route("/api/metrics/history")
        def get_history():
            limit = request.args.get("limit", 100, type=int)
            return jsonify(api.get_history(limit=limit))

        @app.route("/api/topology")
        def get_topology():
            return jsonify(api.get_topology())

        @app.route("/api/alerts")
        def get_alerts():
            unacked = request.args.get("unacknowledged", "false").lower() == "true"
            return jsonify(api.get_alerts(unacknowledged_only=unacked))

        @app.route("/api/alerts/<alert_id>/ack", methods=["POST"])
        def ack_alert(alert_id):
            success = api.acknowledge_alert(alert_id)
            return jsonify({"success": success})

        @app.route("/api/protocols")
        def get_protocols():
            return jsonify(api.get_protocol_states())

        @app.route("/api/control/start", methods=["POST"])
        def control_start():
            return jsonify({"status": "started",
                            "timestamp": datetime.now(timezone.utc).isoformat()})

        @app.route("/api/control/stop", methods=["POST"])
        def control_stop():
            return jsonify({"status": "stopped",
                            "timestamp": datetime.now(timezone.utc).isoformat()})

        # ── SSE stream ────────────────────────────────────────────────────

        @app.route("/api/events")
        def sse_stream():
            """
            Server-Sent Events endpoint for real-time updates.
            Validates: Requirement 9.4 (updates within 2 seconds)
            """
            q = api.register_sse_client()

            def generate():
                try:
                    # Send initial data on connect
                    yield f"data: {json.dumps({'type': 'connected'})}\n\n"
                    while True:
                        try:
                            payload = q.get(timeout=30)
                            yield f"data: {payload}\n\n"
                        except queue.Empty:
                            yield ": heartbeat\n\n"
                except GeneratorExit:
                    api.unregister_sse_client(q)

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        # ── Frontend ──────────────────────────────────────────────────────

        @app.route("/")
        def index():
            return render_template_string(_DASHBOARD_HTML)

        self._app = app

    # ── Server lifecycle ──────────────────────────────────────────────────

    def start(self, threaded: bool = True) -> None:
        """Start the dashboard server."""
        if not FLASK_AVAILABLE:
            logger.warning("Flask not available — dashboard running in mock mode.")
            self._running = True
            return

        self._running = True
        if threaded:
            self._thread = threading.Thread(
                target=lambda: self._app.run(
                    host=self.host, port=self.port,
                    debug=False, use_reloader=False
                ),
                daemon=True,
            )
            self._thread.start()
            logger.info("Dashboard started at http://%s:%d", self.host, self.port)
        else:
            self._app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self) -> None:
        """Stop the dashboard server."""
        self._running = False
        logger.info("Dashboard stopped.")

    def is_running(self) -> bool:
        return self._running


# ─────────────────────────────────────────────
# Dashboard HTML/CSS/JS  (task 22.3)
# ─────────────────────────────────────────────

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Adaptive Network Emulator — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --border:   #2a2d3e;
    --accent:   #4f8ef7;
    --green:    #22c55e;
    --yellow:   #eab308;
    --red:      #ef4444;
    --text:     #e2e8f0;
    --muted:    #64748b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; }

  /* ── Header ── */
  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 24px; background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  header h1 { font-size: 1.1rem; font-weight: 600; color: var(--accent); letter-spacing: .5px; }
  #conn-status { font-size: .78rem; padding: 3px 10px; border-radius: 99px; font-weight: 600; }
  .connected    { background: #166534; color: var(--green); }
  .disconnected { background: #7f1d1d; color: var(--red); }

  /* ── Layout ── */
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px; padding: 20px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px;
  }
  .card h2 { font-size: .78rem; text-transform: uppercase; letter-spacing: 1px;
             color: var(--muted); margin-bottom: 12px; }

  /* ── KPI tiles ── */
  .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .kpi { background: var(--bg); border-radius: 8px; padding: 12px; text-align: center; }
  .kpi .val { font-size: 1.6rem; font-weight: 700; }
  .kpi .lbl { font-size: .72rem; color: var(--muted); margin-top: 4px; }
  .kpi.good .val  { color: var(--green); }
  .kpi.warn .val  { color: var(--yellow); }
  .kpi.bad  .val  { color: var(--red); }

  /* ── Charts ── */
  .chart-wrap { position: relative; height: 180px; }

  /* ── Topology ── */
  #topology-canvas { width: 100%; height: 220px; border-radius: 8px; background: var(--bg); }

  /* ── Protocol state ── */
  .proto-row { display: flex; justify-content: space-between; align-items: center;
               padding: 8px 0; border-bottom: 1px solid var(--border); font-size: .85rem; }
  .proto-row:last-child { border-bottom: none; }
  .badge { padding: 2px 8px; border-radius: 99px; font-size: .72rem; font-weight: 600; }
  .badge.idle      { background: #1e3a5f; color: var(--accent); }
  .badge.sending   { background: #14532d; color: var(--green); }
  .badge.congested { background: #7f1d1d; color: var(--red); }
  .badge.waiting   { background: #713f12; color: var(--yellow); }

  /* ── Alerts ── */
  .alert-item { padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;
                font-size: .82rem; display: flex; justify-content: space-between; }
  .alert-item.critical { background: #450a0a; border-left: 3px solid var(--red); }
  .alert-item.warning  { background: #422006; border-left: 3px solid var(--yellow); }
  .alert-item.info     { background: #0c1a3a; border-left: 3px solid var(--accent); }
  .ack-btn { cursor: pointer; background: none; border: 1px solid var(--border);
             color: var(--muted); border-radius: 4px; padding: 2px 8px; font-size: .72rem; }
  .ack-btn:hover { color: var(--text); border-color: var(--text); }
  #alerts-list { max-height: 200px; overflow-y: auto; }

  /* ── Optimization events ── */
  .opt-event { padding: 6px 10px; border-radius: 6px; margin-bottom: 5px;
               font-size: .80rem; background: #1a1040; border-left: 3px solid #a78bfa; }
  #opt-list { max-height: 150px; overflow-y: auto; }

  /* ── History table ── */
  .history-table { width: 100%; border-collapse: collapse; font-size: .78rem; }
  .history-table th { color: var(--muted); font-weight: 500; padding: 4px 8px;
                       text-align: right; border-bottom: 1px solid var(--border); }
  .history-table th:first-child { text-align: left; }
  .history-table td { padding: 4px 8px; text-align: right; border-bottom: 1px solid #1e2231; }
  .history-table td:first-child { text-align: left; color: var(--muted); }
  #history-body tr:hover td { background: #1e2231; }
  .history-wrap { max-height: 200px; overflow-y: auto; }
</style>
</head>
<body>

<header>
  <h1>&#127760; Adaptive Network Emulator</h1>
  <span id="conn-status" class="disconnected">● Disconnected</span>
</header>

<div class="grid">

  <!-- KPI Metrics -->
  <div class="card">
    <h2>Live Metrics</h2>
    <div class="kpi-grid">
      <div class="kpi good" id="kpi-throughput">
        <div class="val" id="val-throughput">—</div>
        <div class="lbl">Throughput</div>
      </div>
      <div class="kpi good" id="kpi-latency">
        <div class="val" id="val-latency">—</div>
        <div class="lbl">Latency (mean)</div>
      </div>
      <div class="kpi good" id="kpi-loss">
        <div class="val" id="val-loss">—</div>
        <div class="lbl">Packet Loss</div>
      </div>
      <div class="kpi good" id="kpi-jitter">
        <div class="val" id="val-jitter">—</div>
        <div class="lbl">Jitter</div>
      </div>
    </div>
  </div>

  <!-- Throughput Chart -->
  <div class="card">
    <h2>Throughput History</h2>
    <div class="chart-wrap">
      <canvas id="chart-throughput"></canvas>
    </div>
  </div>

  <!-- Latency Chart -->
  <div class="card">
    <h2>Latency History</h2>
    <div class="chart-wrap">
      <canvas id="chart-latency"></canvas>
    </div>
  </div>

  <!-- Loss Chart -->
  <div class="card">
    <h2>Packet Loss History</h2>
    <div class="chart-wrap">
      <canvas id="chart-loss"></canvas>
    </div>
  </div>

  <!-- Topology -->
  <div class="card" style="grid-column: span 2;">
    <h2>Network Topology</h2>
    <canvas id="topology-canvas"></canvas>
  </div>

  <!-- Protocol State -->
  <div class="card">
    <h2>Protocol State</h2>
    <div id="proto-list">
      <div class="proto-row" style="color:var(--muted); font-size:.82rem;">
        No protocol data yet…
      </div>
    </div>
  </div>

  <!-- Alerts -->
  <div class="card">
    <h2>Alerts</h2>
    <div id="alerts-list">
      <div style="color:var(--muted); font-size:.82rem;">No alerts.</div>
    </div>
  </div>

  <!-- Optimization Events -->
  <div class="card">
    <h2>&#9889; Optimization Events</h2>
    <div id="opt-list">
      <div style="color:var(--muted); font-size:.82rem;">No optimization events yet.</div>
    </div>
  </div>

  <!-- Historical Trends -->
  <div class="card" style="grid-column: span 2;">
    <h2>Historical Data</h2>
    <div class="history-wrap">
      <table class="history-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Throughput</th>
            <th>Latency ms</th>
            <th>Loss %</th>
            <th>Retransmissions</th>
            <th>Jitter ms</th>
          </tr>
        </thead>
        <tbody id="history-body">
          <tr><td colspan="6" style="text-align:center;color:var(--muted);">No data yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>

</div><!-- /grid -->

<script>
// ── Chart setup ─────────────────────────────────────────────────────────
const MAX_POINTS = 60;
const chartDefaults = {
  responsive: true, maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: { legend: { display: false } },
  scales: {
    x: { display: false },
    y: { grid: { color: '#2a2d3e' }, ticks: { color: '#64748b', font: { size: 10 } } }
  }
};

function makeChart(id, color, label) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label, data: [],
        borderColor: color, backgroundColor: color + '22',
        borderWidth: 2, fill: true,
        tension: 0.3, pointRadius: 0,
      }]
    },
    options: { ...chartDefaults }
  });
}

const charts = {
  throughput: makeChart('chart-throughput', '#4f8ef7', 'Throughput bps'),
  latency:    makeChart('chart-latency',    '#22c55e', 'Latency ms'),
  loss:       makeChart('chart-loss',       '#ef4444', 'Loss %'),
};

function pushChart(chart, label, value) {
  chart.data.labels.push(label);
  chart.data.datasets[0].data.push(value);
  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}

// ── KPI helpers ─────────────────────────────────────────────────────────
function setKPI(id, value, unit, thresholds) {
  const el   = document.getElementById('kpi-' + id);
  const valEl = document.getElementById('val-' + id);
  valEl.textContent = value + unit;
  el.className = 'kpi ' + (value >= thresholds.bad ? 'bad' : value >= thresholds.warn ? 'warn' : 'good');
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso; }
}

function fmtBps(bps) {
  if (bps >= 1e9) return (bps/1e9).toFixed(2) + ' Gbps';
  if (bps >= 1e6) return (bps/1e6).toFixed(2) + ' Mbps';
  if (bps >= 1e3) return (bps/1e3).toFixed(1) + ' Kbps';
  return bps.toFixed(0) + ' bps';
}

// ── Metrics update ───────────────────────────────────────────────────────
function onMetrics(m) {
  const t = fmtTime(m.timestamp);
  setKPI('throughput', fmtBps(m.throughput_bps), '', { warn: Infinity, bad: Infinity });
  document.getElementById('val-throughput').textContent = fmtBps(m.throughput_bps);

  setKPI('latency', m.latency_mean_ms.toFixed(1), ' ms', { warn: 100, bad: 200 });
  setKPI('loss',    m.loss_pct.toFixed(2),         ' %',  { warn: 5,   bad: 10  });
  setKPI('jitter',  m.jitter_mean_ms.toFixed(2),   ' ms', { warn: 20,  bad: 50  });

  pushChart(charts.throughput, t, m.throughput_bps);
  pushChart(charts.latency,    t, m.latency_mean_ms);
  pushChart(charts.loss,       t, m.loss_pct);
}

// ── Topology canvas ──────────────────────────────────────────────────────
let topoData = { nodes: [], links: [] };

function drawTopology() {
  const canvas = document.getElementById('topology-canvas');
  const ctx    = canvas.getContext('2d');
  canvas.width  = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight || 220;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const W = canvas.width, H = canvas.height;
  const nodes = topoData.nodes || [];
  const links = topoData.links || [];

  // Auto-layout nodes in a circle if no positions set
  nodes.forEach((n, i) => {
    if (!n.x || !n.y) {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
      n._x = W/2 + Math.cos(angle) * (Math.min(W, H) * 0.35);
      n._y = H/2 + Math.sin(angle) * (Math.min(W, H) * 0.35);
    } else {
      n._x = n.x * W; n._y = n.y * H;
    }
  });

  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.node_id] = n; });

  // Draw links
  links.forEach(lnk => {
    const src = nodeMap[lnk.source];
    const tgt = nodeMap[lnk.target];
    if (!src || !tgt) return;

    ctx.beginPath();
    ctx.moveTo(src._x, src._y);
    ctx.lineTo(tgt._x, tgt._y);
    ctx.strokeStyle = lnk.has_packet_flow ? '#4f8ef7' : '#2a2d3e';
    ctx.lineWidth   = lnk.has_packet_flow ? 2 : 1;
    ctx.stroke();

    // Animated packet dot on active links
    if (lnk.has_packet_flow) {
      const t = (Date.now() % 1500) / 1500;
      const px = src._x + (tgt._x - src._x) * t;
      const py = src._y + (tgt._y - src._y) * t;
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI*2);
      ctx.fillStyle = '#4f8ef7';
      ctx.fill();
    }
  });

  // Draw nodes
  nodes.forEach(n => {
    const color = n.status === 'failed'    ? '#ef4444' :
                  n.status === 'congested' ? '#eab308' : '#22c55e';
    ctx.beginPath();
    ctx.arc(n._x, n._y, 16, 0, Math.PI*2);
    ctx.fillStyle = '#1a1d27';
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = '#e2e8f0';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(n.node_id, n._x, n._y);
  });
}

function onTopology(data) {
  topoData = data;
  drawTopology();
}

// Animate packet flows
setInterval(drawTopology, 50);

// ── Protocol state ────────────────────────────────────────────────────────
function onProtocolState(s) {
  const list = document.getElementById('proto-list');
  const id   = 'proto-' + s.protocol;
  let row = document.getElementById(id);
  if (!row) {
    row = document.createElement('div');
    row.id = id;
    row.className = 'proto-row';
    list.innerHTML = '';
    list.appendChild(row);
  }
  row.innerHTML = `
    <span>${s.protocol}</span>
    <span>W:${s.window_size} U:${s.unacked_packets} R:${s.retransmission_count}</span>
    <span class="badge ${s.state}">${s.state}</span>
  `;
}

// ── Alerts ────────────────────────────────────────────────────────────────
function onAlert(a) {
  const list = document.getElementById('alerts-list');
  // Remove placeholder
  const placeholder = list.querySelector('[data-placeholder]');
  if (placeholder) placeholder.remove();

  const div = document.createElement('div');
  div.className = `alert-item ${a.severity}`;
  div.id = 'alert-' + a.alert_id;
  div.innerHTML = `
    <span>${a.message}</span>
    <button class="ack-btn" onclick="ackAlert('${a.alert_id}')">ACK</button>
  `;
  list.prepend(div);
}

async function ackAlert(id) {
  await fetch('/api/alerts/' + id + '/ack', { method: 'POST' });
  const el = document.getElementById('alert-' + id);
  if (el) el.style.opacity = '0.4';
}

// ── Optimization events ───────────────────────────────────────────────────
function addOptEvent(msg) {
  const list = document.getElementById('opt-list');
  const placeholder = list.querySelector('[data-placeholder]');
  if (placeholder) placeholder.remove();

  const div = document.createElement('div');
  div.className = 'opt-event';
  div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  list.prepend(div);
  if (list.children.length > 20) list.lastChild.remove();
}

// ── History table ─────────────────────────────────────────────────────────
const historyRows = [];
function addHistoryRow(m) {
  historyRows.unshift(m);
  if (historyRows.length > 100) historyRows.pop();
  const tbody = document.getElementById('history-body');
  tbody.innerHTML = historyRows.slice(0, 20).map(r => `
    <tr>
      <td>${fmtTime(r.timestamp)}</td>
      <td>${fmtBps(r.throughput_bps)}</td>
      <td>${r.latency_mean_ms.toFixed(2)}</td>
      <td>${r.loss_pct.toFixed(2)}</td>
      <td>${r.retransmissions}</td>
      <td>${r.jitter_mean_ms.toFixed(2)}</td>
    </tr>
  `).join('');
}

// ── SSE connection ────────────────────────────────────────────────────────
function connectSSE() {
  const statusEl = document.getElementById('conn-status');
  const es = new EventSource('/api/events');

  es.onopen = () => {
    statusEl.textContent = '● Connected';
    statusEl.className   = 'connected';
  };

  es.onerror = () => {
    statusEl.textContent = '● Disconnected';
    statusEl.className   = 'disconnected';
    setTimeout(connectSSE, 3000);
  };

  es.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'metrics') {
        onMetrics(msg.data);
        addHistoryRow(msg.data);
      } else if (msg.type === 'topology') {
        onTopology(msg.data);
      } else if (msg.type === 'alert') {
        onAlert(msg.data);
      } else if (msg.type === 'protocol_state') {
        onProtocolState(msg.data);
      } else if (msg.type === 'optimization') {
        addOptEvent(msg.data.action + ' — ' + msg.data.condition);
      }
    } catch(e) { console.error('SSE parse error', e); }
  };
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
(async function init() {
  // Load initial data via REST
  try {
    const [metricsRes, topoRes, alertsRes, historyRes] = await Promise.all([
      fetch('/api/metrics'),
      fetch('/api/topology'),
      fetch('/api/alerts'),
      fetch('/api/metrics/history?limit=20'),
    ]);

    const m = await metricsRes.json();
    onMetrics(m);

    const topo = await topoRes.json();
    onTopology(topo);

    const alerts = await alertsRes.json();
    alerts.forEach(a => onAlert(a));

    const hist = await historyRes.json();
    hist.reverse().forEach(h => addHistoryRow(h));

  } catch(e) { console.warn('Could not load initial data:', e); }

  connectSSE();
})();
</script>
</body>
</html>
"""
