# Network Protocol Emulator — Example Workflows

> **Requirement 10.4** | Task 26.2

---

## Table of Contents

1. [Example 1: Basic File Transfer](#example-1-basic-file-transfer)
2. [Example 2: Comparing GBN vs SR](#example-2-comparing-gbn-vs-sr)
3. [Example 3: Testing Routing Algorithms](#example-3-testing-routing-algorithms)
4. [Example 4: Analyzing Optimization Effects](#example-4-analyzing-optimization-effects)
5. [Example 5: Custom Protocol Implementation](#example-5-custom-protocol-implementation)

---

## Example 1: Basic File Transfer

**Goal:** Simulate a reliable file transfer between two nodes over a lossy link and export the results.

### Config — `examples/example1_file_transfer.yaml`

```yaml
topology:
  nodes:
    - node_id: client
      node_type: sender
    - node_id: server
      node_type: receiver
  links:
    - source: client
      target: server
      bandwidth_mbps: 10.0
      delay_ms: 50.0
      loss_pct: 3.0

protocol:
  protocol: GBN
  window_size: 4
  timeout_ms: 300.0
  max_retransmissions: 8
  ack_mode: cumulative

experiment:
  name: basic_file_transfer
  duration_s: 60.0
  packet_size_bytes: 1460
  traffic_pattern: cbr
  repetitions: 3
  random_seed: 1
```

### Code

```python
from src.config_loader import ConfigLoader
from src.simulation_controller import SimulationController
from src.data_exporter import DataExporter

# Load config
config = ConfigLoader.from_file("examples/example1_file_transfer.yaml")

# Run simulation
controller = SimulationController(config)
results    = controller.run()

# Print summary
print(f"=== Basic File Transfer Results ===")
print(f"Throughput      : {results.throughput_bps / 1e6:.3f} Mbps")
print(f"Mean Latency    : {results.latency_mean_ms:.1f} ms")
print(f"Packet Loss     : {results.loss_pct:.2f}%")
print(f"Retransmissions : {results.retransmissions}")

# Export
exporter = DataExporter(export_dir="output/example1/")
exporter.export_json([results.__dict__], label="file_transfer")
exporter.export_csv( [results.__dict__], label="file_transfer")
```

### Expected Output

```
=== Basic File Transfer Results ===
Throughput      : 8.731 Mbps
Mean Latency    : 53.4 ms
Packet Loss     : 3.02%
Retransmissions : 47
```

---

## Example 2: Comparing GBN vs SR

**Goal:** Run the same experiment under both Go-Back-N and Selective Repeat, then generate a performance comparison report.

### Config — `examples/example2_gbn.yaml`

```yaml
topology:
  nodes:
    - node_id: tx
      node_type: sender
    - node_id: rx
      node_type: receiver
  links:
    - source: tx
      target: rx
      bandwidth_mbps: 50.0
      delay_ms: 30.0
      loss_pct: 5.0

protocol:
  protocol: GBN
  window_size: 16
  timeout_ms: 200.0
  max_retransmissions: 10
  ack_mode: cumulative

experiment:
  name: gbn_vs_sr_gbn
  duration_s: 90.0
  packet_size_bytes: 512
  traffic_pattern: bursty
  repetitions: 5
  random_seed: 42
```

### Config — `examples/example2_sr.yaml`

```yaml
topology:
  nodes:
    - node_id: tx
      node_type: sender
    - node_id: rx
      node_type: receiver
  links:
    - source: tx
      target: rx
      bandwidth_mbps: 50.0
      delay_ms: 30.0
      loss_pct: 5.0

protocol:
  protocol: SR
  window_size: 16
  timeout_ms: 200.0
  max_retransmissions: 10
  ack_mode: selective          # required for SR

experiment:
  name: gbn_vs_sr_sr
  duration_s: 90.0
  packet_size_bytes: 512
  traffic_pattern: bursty
  repetitions: 5
  random_seed: 42
```

### Code

```python
from src.config_loader import ConfigLoader
from src.simulation_controller import SimulationController
from src.report_generator import ReportGenerator

# Run GBN
cfg_gbn     = ConfigLoader.from_file("examples/example2_gbn.yaml")
results_gbn = SimulationController(cfg_gbn).run_all()   # returns list (repetitions)

# Run SR
cfg_sr     = ConfigLoader.from_file("examples/example2_sr.yaml")
results_sr = SimulationController(cfg_sr).run_all()

# Generate comparison report
gen    = ReportGenerator(reports_dir="output/example2/")
report = gen.generate_report(
    title="GBN vs SR — 5% Loss, 30ms Delay",
    groups={
        "GBN": [r.__dict__ for r in results_gbn],
        "SR":  [r.__dict__ for r in results_sr],
    },
    lower_is_better=["loss_pct", "latency_mean_ms", "jitter_ms", "retransmissions"],
)

# Print and save
print(gen.render_text(report))
gen.save_json(report)
```

### Expected Report Excerpt

```
=== GBN vs SR — 5% Loss, 30ms Delay ===

SUMMARIES
  GBN  throughput_bps=38.2M  latency_mean_ms=34.1  loss_pct=5.1  retransmissions=312
  SR   throughput_bps=43.7M  latency_mean_ms=31.8  loss_pct=5.0  retransmissions=187

COMPARISONS  GBN vs SR
  throughput_bps   : SR better by +14.4%
  retransmissions  : SR better by -40.1%

CONCLUSION
  SR outperforms GBN on 3 of 5 metrics under these conditions.
```

---

## Example 3: Testing Routing Algorithms

**Goal:** Build a multi-hop topology and compare Dijkstra vs Distance Vector routing by measuring end-to-end latency.

### Config — `examples/example3_routing.yaml`

```yaml
topology:
  nodes:
    - node_id: A
      node_type: sender
    - node_id: B
      node_type: router
    - node_id: C
      node_type: router
    - node_id: D
      node_type: receiver
  links:
    - source: A
      target: B
      bandwidth_mbps: 100.0
      delay_ms: 5.0
      loss_pct: 0.0
    - source: B
      target: C
      bandwidth_mbps: 100.0
      delay_ms: 15.0
      loss_pct: 1.0
    - source: B
      target: D
      bandwidth_mbps: 20.0
      delay_ms: 40.0
      loss_pct: 0.0
    - source: C
      target: D
      bandwidth_mbps: 100.0
      delay_ms: 5.0
      loss_pct: 0.0

protocol:
  protocol: GBN
  window_size: 8
  timeout_ms: 250.0
  max_retransmissions: 5
  ack_mode: cumulative

experiment:
  name: routing_comparison
  duration_s: 60.0
  packet_size_bytes: 256
  traffic_pattern: cbr
  repetitions: 3
  random_seed: 7
```

### Code

```python
from src.config_loader import ConfigLoader
from src.dijkstra_router import DijkstraRouter
from src.distance_vector_router import DistanceVectorRouter
from src.network_topology import NetworkTopology
from src.report_generator import ReportGenerator

config   = ConfigLoader.from_file("examples/example3_routing.yaml")
topology = NetworkTopology(config.topology)

# Dijkstra
dijkstra = DijkstraRouter(topology)
path_d   = dijkstra.shortest_path("A", "D")
cost_d   = dijkstra.path_cost(path_d)
print(f"Dijkstra  path: {' → '.join(path_d)}  cost: {cost_d:.1f} ms")

# Distance Vector
dv      = DistanceVectorRouter(topology)
dv.converge()
path_dv = dv.path("A", "D")
cost_dv = dv.path_cost(path_dv)
print(f"Dist.Vec  path: {' → '.join(path_dv)}  cost: {cost_dv:.1f} ms")

# Compare
gen    = ReportGenerator(reports_dir="output/example3/")
report = gen.generate_report(
    title="Dijkstra vs Distance Vector Routing",
    groups={
        "dijkstra":        [{"latency_mean_ms": cost_d,  "retransmissions": 0}],
        "distance_vector": [{"latency_mean_ms": cost_dv, "retransmissions": 0}],
    },
    lower_is_better=["latency_mean_ms"],
)
print(gen.render_text(report))
```

### Expected Output

```
Dijkstra  path: A → B → C → D  cost: 25.0 ms
Dist.Vec  path: A → B → C → D  cost: 25.0 ms
```

Both algorithms find the optimal A→B→C→D path (25ms) rather than the direct A→B→D path (45ms).

---

## Example 4: Analyzing Optimization Effects

**Goal:** Compare static GBN against the ADAPTIVE protocol across varying loss conditions and plot improvement percentages.

### Code

```python
from src.config_loader import ConfigLoader, ConfigValidationError
from src.simulation_controller import SimulationController
from src.report_generator import ReportGenerator

loss_conditions = [0.0, 1.0, 5.0, 10.0, 20.0]
static_results   = []
adaptive_results = []

base_cfg = {
    "topology": {
        "nodes": [
            {"node_id": "tx", "node_type": "sender"},
            {"node_id": "rx", "node_type": "receiver"},
        ],
        "links": [{"source": "tx", "target": "rx",
                   "bandwidth_mbps": 100.0, "delay_ms": 20.0, "loss_pct": 0.0}],
    },
    "experiment": {
        "name": "opt_test",
        "duration_s": 60.0,
        "packet_size_bytes": 1024,
        "traffic_pattern": "cbr",
        "repetitions": 3,
        "random_seed": 99,
    },
}

for loss in loss_conditions:
    base_cfg["topology"]["links"][0]["loss_pct"] = loss

    # Static GBN
    base_cfg["protocol"] = {
        "protocol": "GBN", "window_size": 8,
        "timeout_ms": 200.0, "max_retransmissions": 10,
        "ack_mode": "cumulative",
    }
    cfg_s   = ConfigLoader.from_dict(base_cfg)
    res_s   = SimulationController(cfg_s).run()
    static_results.append(res_s.__dict__)

    # Adaptive
    base_cfg["protocol"] = {
        "protocol": "ADAPTIVE", "window_size": 8,
        "timeout_ms": 200.0, "max_retransmissions": 10,
        "ack_mode": "cumulative", "adaptive_alpha": 0.125,
    }
    cfg_a   = ConfigLoader.from_dict(base_cfg)
    res_a   = SimulationController(cfg_a).run()
    adaptive_results.append(res_a.__dict__)

# Report
gen    = ReportGenerator(reports_dir="output/example4/")
report = gen.generate_static_vs_adaptive_report(static_results, adaptive_results)

print("=== Adaptive Improvement over Static GBN ===")
for metric, pct in report.adaptive_improvement_pct.items():
    direction = "better" if pct > 0 else "worse"
    print(f"  {metric:25s}: {pct:+.1f}% ({direction})")

gen.save_json(report)
```

### Expected Output

```
=== Adaptive Improvement over Static GBN ===
  throughput_bps           : +18.3% (better)
  latency_mean_ms          : -12.7% (better)
  loss_pct                 : -8.1%  (better)
  retransmissions          : -31.4% (better)
  jitter_ms                : -9.2%  (better)
```

---

## Example 5: Custom Protocol Implementation

**Goal:** Implement a custom Stop-and-Wait (SAW) protocol by extending the base protocol class and plug it into the emulator.

### Step 1 — Implement the protocol

Create `src/saw_protocol.py`:

```python
from src.gbn_protocol import BaseProtocol   # extend existing base

class StopAndWaitProtocol(BaseProtocol):
    """
    Stop-and-Wait: window_size is always 1.
    Sends one packet, waits for ACK, then sends next.
    """

    def __init__(self, config):
        super().__init__(config)
        self.window_size = 1      # force window to 1 regardless of config

    def on_packet_sent(self, packet):
        self.pending = packet
        self.start_timer(self.timeout_ms)

    def on_ack_received(self, ack_num):
        if ack_num == self.pending.sequence_num:
            self.stop_timer()
            self.pending = None
            self.send_next()

    def on_timeout(self):
        # Retransmit the single pending packet
        if self.retransmission_count < self.max_retransmissions:
            self.retransmit(self.pending)
            self.retransmission_count += 1
        else:
            self.drop(self.pending)
```

### Step 2 — Register and use it

```python
from src.config_loader import ConfigLoader
from src.saw_protocol   import StopAndWaitProtocol
from src.simulation_controller import SimulationController

raw_cfg = {
    "topology": {
        "nodes": [
            {"node_id": "s", "node_type": "sender"},
            {"node_id": "r", "node_type": "receiver"},
        ],
        "links": [{"source": "s", "target": "r",
                   "bandwidth_mbps": 10.0, "delay_ms": 20.0, "loss_pct": 1.0}],
    },
    "protocol": {
        "protocol": "GBN",       # closest base for validation
        "window_size": 1,        # SAW always uses 1
        "timeout_ms": 400.0,
        "max_retransmissions": 5,
        "ack_mode": "cumulative",
    },
    "experiment": {
        "name": "custom_saw",
        "duration_s": 30.0,
        "packet_size_bytes": 512,
        "traffic_pattern": "cbr",
    },
}

config     = ConfigLoader.from_dict(raw_cfg)
controller = SimulationController(config, protocol_class=StopAndWaitProtocol)
results    = controller.run()

print(f"SAW Throughput : {results.throughput_bps / 1e6:.3f} Mbps")
print(f"SAW Latency    : {results.latency_mean_ms:.1f} ms")
```

### Step 3 — Compare SAW vs GBN

```python
from src.report_generator import ReportGenerator

# (collect results_saw and results_gbn from separate runs)
gen    = ReportGenerator(reports_dir="output/example5/")
report = gen.generate_report(
    title="Stop-and-Wait vs GBN",
    groups={
        "SAW": [results_saw.__dict__],
        "GBN": [results_gbn.__dict__],
    },
    lower_is_better=["latency_mean_ms", "loss_pct"],
)
print(gen.render_text(report))
```

**Key insight:** SAW will show far lower throughput than GBN on high-latency links because it cannot pipeline packets. This example demonstrates both the extension mechanism and why window-based protocols outperform SAW as RTT grows.
