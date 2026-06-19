# Network Protocol Emulator — User Documentation

> **Requirement 11.4** | Task 26.1

---

## Table of Contents

1. [Installation Guide](#1-installation-guide)
2. [Quick Start Tutorial](#2-quick-start-tutorial)
3. [Configuration Options](#3-configuration-options)
4. [Troubleshooting Guide](#4-troubleshooting-guide)
5. [API Reference](#5-api-reference)

---

## 1. Installation Guide

### Prerequisites

| Requirement | Minimum Version |
|-------------|----------------|
| Python      | 3.12+          |
| pip         | 23+            |
| OS          | Windows 10 / Ubuntu 20.04 / macOS 12+ |

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/network-protocol-emulator.git
cd network-protocol-emulator
```

### Step 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Verify installation

```bash
pytest tests/ -q
```

All tests should pass. If you see errors, see the [Troubleshooting Guide](#4-troubleshooting-guide).

---

## 2. Quick Start Tutorial

### Goal
Run a simple file transfer simulation over a two-node topology using the Go-Back-N (GBN) protocol and view the results.

### Step 1 — Create a configuration file

Create `my_experiment.yaml` in the project root:

```yaml
topology:
  nodes:
    - node_id: sender
      node_type: sender
    - node_id: receiver
      node_type: receiver
  links:
    - source: sender
      target: receiver
      bandwidth_mbps: 100.0
      delay_ms: 20.0
      loss_pct: 2.0

protocol:
  protocol: GBN
  window_size: 8
  timeout_ms: 200.0
  max_retransmissions: 5
  ack_mode: cumulative

experiment:
  name: quickstart_demo
  duration_s: 30.0
  packet_size_bytes: 1024
  traffic_pattern: cbr
  repetitions: 1
```

### Step 2 — Load and validate the config

```python
from src.config_loader import ConfigLoader

config = ConfigLoader.from_file("my_experiment.yaml")
print(f"Protocol : {config.protocol.protocol}")
print(f"Window   : {config.protocol.window_size}")
print(f"Duration : {config.experiment.duration_s}s")
```

### Step 3 — Run the simulation

```python
from src.simulation_controller import SimulationController

controller = SimulationController(config)
results = controller.run()
print(f"Throughput : {results.throughput_bps / 1e6:.2f} Mbps")
print(f"Loss       : {results.loss_pct:.2f}%")
print(f"Latency    : {results.latency_mean_ms:.1f} ms")
```

### Step 4 — Export results

```python
from src.data_exporter import DataExporter

exporter = DataExporter(export_dir="output/")
exporter.export_json([results.__dict__], label="quickstart")
exporter.export_csv([results.__dict__],  label="quickstart")
print("Results saved to output/")
```

---

## 3. Configuration Options

All configuration is written in YAML and loaded via `ConfigLoader`. The schema has three required top-level sections.

### 3.1 `topology`

Defines the network graph.

#### `topology.nodes` (required, list, ≥1 item)

| Field | Type | Required | Values | Description |
|-------|------|----------|--------|-------------|
| `node_id` | string | ✅ | any unique non-empty string | Unique identifier for the node |
| `node_type` | string | ✅ | `sender`, `receiver`, `router` | Role of the node in the topology |
| `position` | object | ❌ | `{x: float, y: float}` | Optional 2D position for visualization |

#### `topology.links` (optional, list)

| Field | Type | Required | Range | Description |
|-------|------|----------|-------|-------------|
| `source` | string | ✅ | any node_id | Source node of the link |
| `target` | string | ✅ | any node_id | Target node of the link |
| `bandwidth_mbps` | float | ✅ | > 0 | Link capacity in Megabits per second |
| `delay_ms` | float | ✅ | ≥ 0 | Propagation delay in milliseconds |
| `loss_pct` | float | ✅ | 0.0 – 100.0 | Packet loss percentage |

### 3.2 `protocol`

Defines protocol behavior.

| Field | Type | Required | Values / Range | Description |
|-------|------|----------|----------------|-------------|
| `protocol` | string | ✅ | `GBN`, `SR`, `ADAPTIVE` | Protocol to simulate |
| `window_size` | int | ✅ | 1 – 1024 | Sliding window size |
| `timeout_ms` | float | ✅ | > 0 | Retransmission timeout in ms |
| `max_retransmissions` | int | ✅ | ≥ 0 | Max retransmit attempts before drop |
| `ack_mode` | string | ❌ | `cumulative`, `selective` | ACK strategy (default: `cumulative`) |
| `adaptive_alpha` | float | ✅ if ADAPTIVE | (0.0, 1.0) | Learning rate for ADAPTIVE protocol |

**Conflict rules:**
- `SR` protocol **requires** `ack_mode: selective`
- `ADAPTIVE` protocol **requires** `adaptive_alpha`

### 3.3 `experiment`

Controls the simulation run.

| Field | Type | Required | Range | Description |
|-------|------|----------|-------|-------------|
| `name` | string | ✅ | non-empty | Human-readable experiment label |
| `duration_s` | float | ✅ | > 0 | Simulation duration in seconds |
| `packet_size_bytes` | int | ✅ | 64 – 65535 | Size of each packet in bytes |
| `traffic_pattern` | string | ✅ | `cbr`, `bursty`, `trace` | Traffic generation pattern |
| `repetitions` | int | ❌ | ≥ 1 | Number of runs to average (default: 1) |
| `random_seed` | int | ❌ | any int | Seed for reproducibility |

### 3.4 Full example config

```yaml
topology:
  nodes:
    - node_id: nodeA
      node_type: sender
    - node_id: nodeB
      node_type: router
    - node_id: nodeC
      node_type: receiver
  links:
    - source: nodeA
      target: nodeB
      bandwidth_mbps: 50.0
      delay_ms: 10.0
      loss_pct: 1.0
    - source: nodeB
      target: nodeC
      bandwidth_mbps: 50.0
      delay_ms: 10.0
      loss_pct: 0.5

protocol:
  protocol: ADAPTIVE
  window_size: 16
  timeout_ms: 150.0
  max_retransmissions: 10
  ack_mode: cumulative
  adaptive_alpha: 0.125

experiment:
  name: adaptive_3node_test
  duration_s: 120.0
  packet_size_bytes: 512
  traffic_pattern: bursty
  repetitions: 5
  random_seed: 42
```

---

## 4. Troubleshooting Guide

### `ConfigValidationError` on startup

The emulator validates config on load and reports all errors at once.

```
ConfigValidationError: Configuration validation failed:
  - [protocol.window_size] Must be integer in [1, 1024] (got: 0)
  - [experiment.traffic_pattern] Must be one of ['bursty', 'cbr', 'trace'] (got: 'random')
```

**Fix:** Read each `[field.name]` in the error, correct the value in your YAML, and re-run.

---

### `ModuleNotFoundError: No module named 'src'`

You are running pytest or Python from the wrong directory.

```bash
# Always run from the project root
cd path/to/PROJECT
pytest tests/
```

---

### `SR protocol requires ack_mode=selective`

```yaml
# ❌ Wrong
protocol:
  protocol: SR
  ack_mode: cumulative

# ✅ Correct
protocol:
  protocol: SR
  ack_mode: selective
```

---

### `ADAPTIVE protocol requires adaptive_alpha`

```yaml
# ❌ Wrong
protocol:
  protocol: ADAPTIVE

# ✅ Correct
protocol:
  protocol: ADAPTIVE
  adaptive_alpha: 0.125
```

---

### Tests collecting 0 items

Your test file is not in the `tests/` directory or doesn't match the `test_*.py` naming pattern.

```bash
# Check what pytest finds
pytest tests/ --collect-only
```

---

### Slow test runs

Hypothesis runs 100 examples per property test by default. To run a fast smoke-check during development:

```bash
pytest tests/ -x -q --hypothesis-seed=0
```

---

## 5. API Reference

### `src.config_loader.ConfigLoader`

Central class for loading and validating emulator configuration.

#### `ConfigLoader.from_file(path: str | Path) → EmulatorConfig`

Load config from a YAML file. Raises `FileNotFoundError` if path doesn't exist. Raises `ConfigValidationError` on any validation failure.

```python
config = ConfigLoader.from_file("experiment.yaml")
```

#### `ConfigLoader.from_yaml(yaml_text: str) → EmulatorConfig`

Load config from a YAML string. Useful for testing or programmatic config generation.

```python
config = ConfigLoader.from_yaml("""
topology:
  nodes:
    - node_id: n1
      node_type: sender
...
""")
```

#### `ConfigLoader.from_dict(raw: dict) → EmulatorConfig`

Load config from a Python dictionary. Raises `ConfigValidationError` on failure.

```python
config = ConfigLoader.from_dict({"topology": {...}, "protocol": {...}, "experiment": {...}})
```

#### `ConfigLoader.validate(raw: dict) → list[ConfigError]`

Validate without raising. Returns a (possibly empty) list of `ConfigError` objects. Useful for building validation UIs or pre-flight checks.

```python
errors = ConfigLoader.validate(raw_dict)
if errors:
    for e in errors:
        print(e.field, "→", e.message)
```

---

### `src.config_loader.ConfigValidationError`

Exception raised when one or more validation errors are found.

| Attribute | Type | Description |
|-----------|------|-------------|
| `errors` | `list[ConfigError]` | All errors found during validation |

```python
try:
    config = ConfigLoader.from_file("bad.yaml")
except ConfigValidationError as exc:
    for err in exc.errors:
        print(f"{err.field}: {err.message}")
```

---

### `src.config_loader.ConfigError`

Dataclass representing a single validation error.

| Field | Type | Description |
|-------|------|-------------|
| `field` | str | Dot-separated path to the invalid field (e.g. `protocol.window_size`) |
| `message` | str | Human-readable description of the problem |
| `value` | Any | The invalid value that was found (may be `None`) |

---

### `src.data_exporter.DataExporter`

Exports simulation results to various file formats.

| Method | Returns | Description |
|--------|---------|-------------|
| `export_json(records, label)` | `Path` | Export list of dicts as JSON array |
| `export_csv(records, label)` | `Path` | Export list of dicts as CSV |
| `export_jsonl(records, label)` | `Path` | Export as newline-delimited JSON |
| `capture_packet_trace(packets)` | `Path` | Export Wireshark-compatible JSON |
| `validate_json(path)` | `bool` | Check if JSON file is valid |
| `validate_csv(path)` | `bool` | Check if CSV file is valid |
| `validate_jsonl(path)` | `bool` | Check each line is valid JSON |
| `validate_packet_trace(path)` | `bool` | Check Wireshark format compliance |

---

### `src.protocol_logger.ProtocolLogger`

Logs network events across all layers.

| Method | Description |
|--------|-------------|
| `log(layer, node_id, event_type, message, condition)` | Log a generic network event |
| `log_transport(node_id, event_type, message, loss_pct, latency_ms, sequence_num)` | Log a transport-layer event with metrics |
| `get_all_entries()` | Return all log entries |
| `get_entries(layer, condition)` | Return filtered log entries |
| `close()` | Flush and close the log |

---

### `src.report_generator.ReportGenerator`

Generates performance comparison reports.

| Method | Description |
|--------|-------------|
| `generate_report(title, groups, lower_is_better)` | Generate a multi-group comparison report |
| `generate_static_vs_adaptive_report(static, adaptive)` | Specialized static vs adaptive report |
| `save_json(report)` | Persist report to JSON file |
| `render_text(report)` | Render report as a human-readable string |
