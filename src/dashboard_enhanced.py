"""
Enhanced Dashboard with Clickable Chart Modals

This extends the base dashboard with modal popups for charts.
When you click on any chart, it opens in a larger modal view.
"""

from src.dashboard import Dashboard, MetricsAPI, ProtocolState
import logging

logger = logging.getLogger(__name__)

# Enhanced HTML with modal functionality
_ENHANCED_DASHBOARD_HTML = """<!DOCTYPE html>
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
  .chart-wrap { 
    position: relative; 
    height: 180px; 
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .chart-wrap:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(79, 142, 247, 0.3);
  }
  .chart-wrap::after {
    content: '🔍 Click to enlarge';
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0,0,0,0.7);
    color: var(--accent);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
  }
  .chart-wrap:hover::after {
    opacity: 1;
  }

  /* ── Modal ── */
  .modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(4px);
  }
  .modal.active {
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s;
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .modal-content {
    background: var(--surface);
    border: 2px solid var(--accent);
    border-radius: 12px;
    padding: 24px;
    width: 90%;
    max-width: 1200px;
    height: 80vh;
    position: relative;
    animation: slideIn 0.3s;
  }
  @keyframes slideIn {
    from { transform: translateY(-50px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
  }
  .modal-title {
    font-size: 1.4rem;
    color: var(--accent);
    font-weight: 600;
  }
  .modal-close {
    background: none;
    border: 2px solid var(--border);
    color: var(--text);
    font-size: 1.5rem;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s;
  }
  .modal-close:hover {
    background: var(--red);
    border-color: var(--red);
    transform: rotate(90deg);
  }
  .modal-chart-container {
    height: calc(100% - 80px);
    position: relative;
  }

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
    <div class="chart-wrap" onclick="openChartModal('throughput', 'Throughput History')">
      <canvas id="chart-throughput"></canvas>
    </div>
  </div>

  <!-- Latency Chart -->
  <div class="card">
    <h2>Latency History</h2>
    <div class="chart-wrap" onclick="openChartModal('latency', 'Latency History')">
      <canvas id="chart-latency"></canvas>
    </div>
  </div>

  <!-- Loss Chart -->
  <div class="card">
    <h2>Packet Loss History</h2>
    <div class="chart-wrap" onclick="openChartModal('loss', 'Packet Loss History')">
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

<!-- Modal for enlarged charts -->
<div id="chart-modal" class="modal" onclick="closeModal(event)">
  <div class="modal-content" onclick="event.stopPropagation()">
    <div class="modal-header">
      <h2 class="modal-title" id="modal-title">Chart</h2>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-chart-container">
      <canvas id="modal-chart"></canvas>
    </div>
  </div>
</div>

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

const modalChartDefaults = {
  responsive: true, maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: { 
    legend: { display: true, labels: { color: '#e2e8f0', font: { size: 14 } } }
  },
  scales: {
    x: { 
      display: true,
      grid: { color: '#2a2d3e' },
      ticks: { color: '#64748b', font: { size: 12 } }
    },
    y: { 
      grid: { color: '#2a2d3e' }, 
      ticks: { color: '#64748b', font: { size: 12 } } 
    }
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

let modalChart = null;

function pushChart(chart, label, value) {
  chart.data.labels.push(label);
  chart.data.datasets[0].data.push(value);
  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}

// ── Modal functions ──────────────────────────────────────────────────────
function openChartModal(chartType, title) {
  const modal = document.getElementById('chart-modal');
  const modalTitle = document.getElementById('modal-title');
  const modalCanvas = document.getElementById('modal-chart');
  
  modalTitle.textContent = title;
  modal.classList.add('active');
  
  // Destroy existing modal chart if any
  if (modalChart) {
    modalChart.destroy();
  }
  
  // Get data from the small chart
  const sourceChart = charts[chartType];
  const color = sourceChart.data.datasets[0].borderColor;
  const label = sourceChart.data.datasets[0].label;
  
  // Create enlarged chart
  const ctx = modalCanvas.getContext('2d');
  modalChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [...sourceChart.data.labels],
      datasets: [{
        label: label,
        data: [...sourceChart.data.datasets[0].data],
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 3,
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
      }]
    },
    options: { ...modalChartDefaults }
  });
  
  // Update modal chart when source chart updates
  window.activeModalChart = chartType;
}

function closeModal(event) {
  if (event && event.target.id !== 'chart-modal' && event.target.className !== 'modal-close') {
    return;
  }
  const modal = document.getElementById('chart-modal');
  modal.classList.remove('active');
  window.activeModalChart = null;
  if (modalChart) {
    modalChart.destroy();
    modalChart = null;
  }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

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
  
  // Add to history table
  addToHistory(m);
  
  // Update modal chart if open
  if (window.activeModalChart && modalChart) {
    const sourceChart = charts[window.activeModalChart];
    modalChart.data.labels = [...sourceChart.data.labels];
    modalChart.data.datasets[0].data = [...sourceChart.data.datasets[0].data];
    modalChart.update('none');
  }
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
  await fetch(`/api/alerts/${id}/ack`, { method: 'POST' });
  const el = document.getElementById('alert-' + id);
  if (el) el.style.opacity = '0.5';
}

// ── SSE connection ────────────────────────────────────────────────────────
const evtSource = new EventSource('/api/events');
const connStatus = document.getElementById('conn-status');

evtSource.onopen = () => {
  connStatus.textContent = '● Connected';
  connStatus.className = 'connected';
};

evtSource.onerror = () => {
  connStatus.textContent = '● Disconnected';
  connStatus.className = 'disconnected';
};

evtSource.onmessage = (event) => {
  try {
    const msg = JSON.parse(event.data);
    if (msg.type === 'metrics') onMetrics(msg.data);
    else if (msg.type === 'topology') onTopology(msg.data);
    else if (msg.type === 'alert') onAlert(msg.data);
    else if (msg.type === 'protocol_state') onProtocolState(msg.data);
  } catch (e) {
    console.error('SSE parse error:', e);
  }
};

// ── Historical Data ──────────────────────────────────────────────────────
let historyData = [];

function updateHistoryTable() {
  const tbody = document.getElementById('history-body');
  
  if (historyData.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);">No data yet.</td></tr>';
    return;
  }
  
  // Show last 10 entries
  const recent = historyData.slice(-10).reverse();
  tbody.innerHTML = recent.map(h => `
    <tr>
      <td>${fmtTime(h.timestamp)}</td>
      <td>${fmtBps(h.throughput_bps)}</td>
      <td>${h.latency_mean_ms.toFixed(1)}</td>
      <td>${h.loss_pct.toFixed(2)}</td>
      <td>${h.retransmissions}</td>
      <td>${h.jitter_mean_ms.toFixed(2)}</td>
    </tr>
  `).join('');
}

function addToHistory(metrics) {
  historyData.push(metrics);
  // Keep last 100 entries
  if (historyData.length > 100) {
    historyData.shift();
  }
  updateHistoryTable();
}

// ── Initial data load ─────────────────────────────────────────────────────
async function loadInitialData() {
  try {
    const [metrics, topology, alerts, history] = await Promise.all([
      fetch('/api/metrics').then(r => r.json()),
      fetch('/api/topology').then(r => r.json()),
      fetch('/api/alerts').then(r => r.json()),
      fetch('/api/metrics/history').then(r => r.json()),
    ]);
    if (metrics.timestamp) onMetrics(metrics);
    if (topology.nodes) onTopology(topology);
    alerts.forEach(onAlert);
    
    // Load historical data
    if (history && history.length > 0) {
      historyData = history;
      updateHistoryTable();
    }
  } catch (e) {
    console.error('Initial load error:', e);
  }
}

loadInitialData();
</script>
</body>
</html>
"""


class EnhancedDashboard(Dashboard):
    """Dashboard with clickable chart modals."""
    
    def _build_app(self) -> None:
        """Build Flask app with enhanced HTML."""
        try:
            from flask import Flask, jsonify, request, Response, render_template_string
            from flask_cors import CORS
        except ImportError:
            return
            
        app = Flask(__name__)
        CORS(app)
        
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
            from datetime import datetime, timezone
            return jsonify({"status": "started",
                            "timestamp": datetime.now(timezone.utc).isoformat()})

        @app.route("/api/control/stop", methods=["POST"])
        def control_stop():
            from datetime import datetime, timezone
            return jsonify({"status": "stopped",
                            "timestamp": datetime.now(timezone.utc).isoformat()})

        # Storage for distributed node metrics
        _node_metrics: dict = {}

        @app.route("/api/node_metrics", methods=["POST"])
        def receive_node_metrics():
            from datetime import datetime, timezone
            data = request.get_json(silent=True) or {}
            node_id = data.get("node_id", "unknown")
            _node_metrics[node_id] = {**data, "received_at": datetime.now(timezone.utc).isoformat()}

            # Aggregate all node metrics and push into the dashboard charts
            nodes_with_data = list(_node_metrics.values())
            active = len(nodes_with_data)

            total_sent = sum(v.get("packets_sent", 0) for v in nodes_with_data)
            total_lost = sum(v.get("packets_lost", 0) for v in nodes_with_data)
            total_pkts = total_sent + total_lost
            loss_pct = (total_lost / total_pkts * 100) if total_pkts > 0 else 0.0

            throughput = sum(v.get("throughput_bps", 0.0) for v in nodes_with_data)
            latency_vals = [v["latency_mean_ms"] for v in nodes_with_data if v.get("latency_mean_ms", 0) > 0]
            latency_mean = sum(latency_vals) / len(latency_vals) if latency_vals else 0.0
            jitter_vals = [v["jitter_ms"] for v in nodes_with_data if v.get("jitter_ms", 0) > 0]
            jitter_mean = sum(jitter_vals) / len(jitter_vals) if jitter_vals else 0.0

            api.update_metrics_raw(
                throughput_bps=float(throughput),
                latency_mean_ms=latency_mean,
                loss_pct=loss_pct,
                jitter_mean_ms=jitter_mean,
                active_connections=active,
            )

            # Update topology to show connected nodes
            nodes = []
            positions = {"A": (0.2, 0.5), "B": (0.8, 0.5), "C": (0.5, 0.2), "D": (0.5, 0.8)}
            for nid, ndata in _node_metrics.items():
                x, y = positions.get(nid, (0.5, 0.5))
                nodes.append({"node_id": nid, "ip_address": nid, "x": x, "y": y, "status": "active"})
            links = []
            node_ids = list(_node_metrics.keys())
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    links.append({"source": node_ids[i], "target": node_ids[j],
                                  "cost": 1.0, "utilization": 0.5, "has_packet_flow": True})
            if nodes:
                api.update_topology_raw(nodes=nodes, links=links)

            return jsonify({"status": "ok", "node": node_id})

        @app.route("/api/node_metrics", methods=["GET"])
        def get_node_metrics():
            return jsonify(_node_metrics)

        # ── SSE stream ────────────────────────────────────────────────────

        @app.route("/api/events")
        def sse_stream():
            import json
            import queue
            q = api.register_sse_client()

            def generate():
                try:
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

        # ── Frontend with enhanced HTML ───────────────────────────────────

        @app.route("/")
        def index():
            return render_template_string(_ENHANCED_DASHBOARD_HTML)

        self._app = app
