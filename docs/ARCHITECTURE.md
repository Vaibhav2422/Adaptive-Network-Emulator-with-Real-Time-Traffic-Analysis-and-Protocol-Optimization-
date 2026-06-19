# Network Protocol Emulator — Architecture Documentation

> **Requirements 1.3, 11.4** | Task 26.3

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Layer Interactions](#2-layer-interactions)
3. [Data Flow](#3-data-flow)
4. [Extension Points](#4-extension-points)
5. [Physical Layer Abstractions and Limitations](#5-physical-layer-abstractions-and-limitations)

---

## 1. System Architecture Overview

The emulator follows a **layered architecture** that mirrors the OSI model. Each layer is an independent Python module with a clearly defined interface to its neighbours. The system is event-driven: a central `SimulationController` runs a discrete-event loop, and components communicate by posting events onto a shared `EventQueue`.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER / CONFIG                            │
│          YAML File  ──►  ConfigLoader  ──►  EmulatorConfig      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SIMULATION CONTROLLER                         │
│   EventQueue  ◄──►  SimulationController  ──►  ExperimentMgr   │
└──┬─────────────────┬──────────────────┬──────────────────┬──────┘
   │                 │                  │                  │
   ▼                 ▼                  ▼                  ▼
┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐
│ APPLICA- │  │ TRANSPORT │  │   NETWORK    │  │   DATA LINK      │
│ TION     │  │ LAYER     │  │   LAYER      │  │   LAYER          │
│ LAYER    │  │ GBN/SR/   │  │ Dijkstra /   │  │ MAC / Frame /    │
│ FileXfer │  │ ADAPTIVE  │  │ Dist.Vector  │  │ Error Detection  │
└──────────┘  └───────────┘  └──────────────┘  └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │  PHYSICAL LAYER  │
                                               │  (Abstracted)    │
                                               │  Delay / Loss /  │
                                               │  Bandwidth Model │
                                               └──────────────────┘
                                                         │
                    ┌────────────────────────────────────┤
                    │                                    │
                    ▼                                    ▼
          ┌──────────────────┐               ┌──────────────────────┐
          │  LOGGING &       │               │  REPORTING &         │
          │  EXPORT          │               │  DASHBOARD           │
          │  ProtocolLogger  │               │  ReportGenerator     │
          │  DataExporter    │               │  Dashboard           │
          └──────────────────┘               └──────────────────────┘
```

### Key Components

| Component | Module | Responsibility |
|-----------|--------|----------------|
| Config Loader | `src/config_loader.py` | Parse, validate, and build typed config |
| Simulation Controller | `src/simulation_controller.py` | Drive the discrete-event loop |
| Experiment Manager | `src/experiment_manager.py` | Orchestrate multi-run experiments |
| Application Layer | `src/application_layer.py` | File transfer service, traffic generation |
| Transport Layer | `src/gbn_protocol.py`, `src/sr_protocol.py` | Reliable delivery, windowing, ARQ |
| Network Layer | `src/network_layer.py`, `src/dijkstra_router.py` | Routing, forwarding |
| Data Link Layer | `src/data_link_layer.py`, `src/mac_layer.py` | Framing, MAC, error detection |
| Physical Layer | `src/physical_layer.py` | Propagation delay, loss, bandwidth model |
| Protocol Logger | `src/protocol_logger.py` | Structured event logging |
| Data Exporter | `src/data_exporter.py` | JSON, CSV, JSONL, pcap-like export |
| Report Generator | `src/report_generator.py` | Statistical comparison reports |
| Dashboard | `src/dashboard.py` | Real-time metrics visualisation |

---

## 2. Layer Interactions

Each layer communicates with adjacent layers through well-defined **send/receive interfaces**. Layers never bypass each other — data always travels through the full stack.

```
Application Layer
      │  send_file(data)  /  on_file_received(data)
      ▼
Transport Layer  ◄──────────────────────────────────────────────────────┐
      │  send_segment(segment)                  ACK / NACK feedback     │
      │  on_ack(ack_num)                                                │
      ▼                                                                 │
Network Layer                                                           │
      │  route(packet)  →  forwarding_table lookup                     │
      │  on_packet(packet)                                              │
      ▼                                                                 │
Data Link Layer                                                         │
      │  send_frame(frame)  /  on_frame(frame)                         │
      │  CRC check, MAC arbitration, collision handling                 │
      ▼                                                                 │
Physical Layer                                                          │
      │  transmit(bits, link)                                           │
      │  Models: propagation delay + bandwidth delay + loss drop        │
      ▼                                                                 │
[Link traversed — arrives at next node's Physical Layer]               │
      │                                                                 │
      └── Data Link → Network → Transport → Application ───────────────┘
```

### Interaction Details

**Application → Transport**
- Application calls `transport.send(data, destination)` to request delivery.
- Transport segments data into packets and manages reliable delivery via ARQ (GBN / SR / ADAPTIVE).
- On receipt, transport reassembles and calls `application.on_data_received(data)`.

**Transport → Network**
- Transport hands a segment (with destination address) to `network.forward(packet)`.
- Network looks up the next hop in its routing table and calls `data_link.send_frame(frame, next_hop)`.

**Network → Data Link**
- Network passes a packet to the data link layer for framing.
- Data link adds a header (source MAC, destination MAC), computes CRC, and queues the frame for transmission.
- On receive, data link strips the frame header, verifies CRC, and passes the payload up to network.

**Data Link → Physical**
- Data link calls `physical.transmit(frame_bits, link)`.
- Physical models bandwidth delay (`frame_size / bandwidth`), propagation delay, and probabilistic packet loss.
- On the receive side, physical delivers bits to the remote node's data link layer.

---

## 3. Data Flow

### 3.1 Packet send path (top-down)

```
Application
  │  1. FileTransferService.send_file(bytes)
  │     → segments data into chunks of packet_size_bytes
  ▼
Transport (GBN example)
  │  2. GBNProtocol.send(segment, seq_num)
  │     → places packet in send window
  │     → starts retransmission timer
  ▼
Network
  │  3. NetworkLayer.forward(packet)
  │     → DijkstraRouter.next_hop(src, dst)
  │     → adds IP-like header
  ▼
Data Link
  │  4. DataLinkLayer.send_frame(frame)
  │     → MACLayer.arbitrate()  (CSMA/CD if shared medium)
  │     → appends CRC-32 checksum
  ▼
Physical
     5. PhysicalLayer.transmit(bits, link)
        → EventQueue.schedule(arrival_event,
            time = now + bandwidth_delay + propagation_delay)
        → with probability loss_pct/100: drop event instead
```

### 3.2 Packet receive path (bottom-up)

```
Physical
  │  6. on_arrival_event fired by EventQueue
  │     → delivers bits to remote node's data link
  ▼
Data Link
  │  7. DataLinkLayer.on_frame(frame)
  │     → verifies CRC → if error: sends NACK / drops
  │     → strips frame header
  ▼
Network
  │  8. NetworkLayer.on_packet(packet)
  │     → checks destination: is this node the target?
  │        YES → pass to transport
  │        NO  → forward to next hop (re-enter send path at step 3)
  ▼
Transport
  │  9. GBNProtocol.on_packet(segment)
  │     → sends cumulative ACK
  │     → delivers in-order segments to application
  ▼
Application
    10. FileTransferService.on_data_received(chunk)
        → reassembles file
        → signals transfer complete when all chunks received
```

### 3.3 Logging data flow

Every layer emits structured log entries via `ProtocolLogger`:

```
Any Layer
  │  ProtocolLogger.log(layer, node_id, event_type, message, condition)
  ▼
ProtocolLogger
  │  → assigns entry_id + timestamp
  │  → stores in in-memory list + optional file sink
  ▼
DataExporter                    ReportGenerator
  │  export_json()                generate_report()
  │  export_csv()                 render_text()
  │  export_jsonl()               save_json()
  │  capture_packet_trace()
  ▼
output/  (JSON, CSV, JSONL, pcap-like files)
```

---

## 4. Extension Points

The emulator is designed to be extended without modifying core modules.

### 4.1 Adding a new transport protocol

1. Create `src/my_protocol.py` and extend `BaseProtocol` (from `gbn_protocol.py`).
2. Override: `on_packet_sent`, `on_ack_received`, `on_timeout`, `on_nack_received`.
3. Pass your class to `SimulationController`:

```python
from src.my_protocol import MyProtocol
controller = SimulationController(config, protocol_class=MyProtocol)
```

No changes to any other module are needed.

### 4.2 Adding a new routing algorithm

1. Create `src/my_router.py` implementing the `BaseRouter` interface:
   - `shortest_path(src, dst) → list[str]`
   - `path_cost(path) → float`
2. Pass it to `NetworkLayer`:

```python
from src.my_router import MyRouter
network = NetworkLayer(topology, router_class=MyRouter)
```

### 4.3 Adding a new traffic pattern

1. Create `src/my_traffic.py` implementing `BaseTrafficGenerator`:
   - `next_packet_time() → float`  (returns inter-arrival time)
   - `packet_size() → int`
2. Register it in `TrafficGenerator` by adding to the pattern dispatch dict:

```python
# In src/traffic_generator.py
from src.my_traffic import MyTrafficGenerator
_PATTERNS["my_pattern"] = MyTrafficGenerator
```

3. Use it in config:

```yaml
experiment:
  traffic_pattern: my_pattern
```

### 4.4 Adding a new export format

Subclass `DataExporter` and add a method:

```python
class ExtendedExporter(DataExporter):
    def export_parquet(self, records, label):
        import pandas as pd
        df   = pd.DataFrame(records)
        path = self.export_dir / f"{label}.parquet"
        df.to_parquet(path)
        return path
```

### 4.5 Adding a new metric

1. Add the metric field to `SimulationResult` in `src/data_models.py`.
2. Compute it in `MetricsCalculator.compute(events)`.
3. It will automatically appear in exports, reports, and dashboard — no other changes needed.

---

## 5. Physical Layer Abstractions and Limitations

### 5.1 What the Physical Layer models

The `PhysicalLayer` is a **software abstraction** of a real physical medium. It does not simulate actual radio waves, electrical signals, or optical pulses. Instead it models the *observable effects* of the physical medium:

| Effect | Model | Config parameter |
|--------|-------|-----------------|
| Transmission delay | `frame_bits / bandwidth_bps` | `bandwidth_mbps` |
| Propagation delay | Fixed per-link constant | `delay_ms` |
| Packet loss | Independent Bernoulli trial | `loss_pct` |
| Jitter | Uniform noise added to delay | (internal, derived from `loss_pct`) |

### 5.2 How the Physical Layer schedules delivery

```
transmit(frame, link) called at time T
  │
  ├── transmission_delay = frame.size_bits / link.bandwidth_bps
  ├── propagation_delay  = link.delay_ms / 1000.0
  ├── total_delay        = transmission_delay + propagation_delay
  │
  ├── if random() < link.loss_pct / 100:
  │       EventQueue.schedule(DROP_EVENT, time=T + total_delay)
  │       # frame is silently discarded — sender detects via timeout
  │
  └── else:
          EventQueue.schedule(ARRIVAL_EVENT, time=T + total_delay)
          # frame appears at remote data link layer
```

### 5.3 Known limitations

| Limitation | Description | Impact |
|------------|-------------|--------|
| **No bit-level errors** | Loss is all-or-nothing (frame drop). Individual bit flips are not modelled. CRC checks in the data link layer will therefore never fire unless you inject errors manually. | Conservative: real links also have bit errors at high BER. |
| **No congestion on shared links** | Each link is modelled independently. Two simultaneous transmissions on the same link do not interfere (no queuing model). | Throughput may be overestimated on high-load shared media. |
| **No propagation variation** | Delay is fixed per link; no multipath, Doppler, or weather effects. | Latency distributions will be narrower than real wireless links. |
| **No link-layer collision model** | The MAC layer implements CSMA/CD conceptually, but the physical layer does not simulate collision energy or jamming signals. | Collision rate may be underestimated on busy shared Ethernet segments. |
| **Memoryless loss** | Each packet is independently dropped with probability `loss_pct/100`. Burst errors (Gilbert-Elliott model) are not supported. | Loss bursts typical of real wireless channels are not reproduced. |
| **No buffer modelling** | The physical layer does not model finite TX/RX buffers. Packets are never dropped due to buffer overflow. | Tail-drop and RED behaviour cannot be studied with the current model. |

### 5.4 When these limitations matter

These limitations are acceptable for the primary use cases of this emulator — comparing sliding window protocols and routing algorithms under controlled conditions. They become significant if you need to:

- Study **burst-loss recovery** (use a Gilbert-Elliott loss model extension)
- Study **congestion control** (add a queuing discipline such as FIFO or WFQ)
- Study **wireless channel effects** (add a path-loss and fading model)
- Reproduce **real-world packet captures** (use a live traffic replay instead)

### 5.5 How to extend the Physical Layer

To add a more realistic loss model, subclass `PhysicalLayer`:

```python
from src.physical_layer import PhysicalLayer
import random

class GilbertElliottPhysicalLayer(PhysicalLayer):
    """Two-state Markov burst-loss model."""

    def __init__(self, config, p_good_to_bad=0.01, p_bad_to_good=0.1):
        super().__init__(config)
        self.state = "good"                  # or "bad"
        self.p_gb  = p_good_to_bad
        self.p_bg  = p_bad_to_good
        self.loss_in_bad  = 0.5             # 50% loss in bad state
        self.loss_in_good = 0.0             # 0%  loss in good state

    def _transition(self):
        if self.state == "good":
            if random.random() < self.p_gb:
                self.state = "bad"
        else:
            if random.random() < self.p_bg:
                self.state = "good"

    def _should_drop(self, link):
        self._transition()
        loss = self.loss_in_bad if self.state == "bad" else self.loss_in_good
        return random.random() < loss
```

Pass it to `SimulationController(config, physical_layer_class=GilbertElliottPhysicalLayer)`.
