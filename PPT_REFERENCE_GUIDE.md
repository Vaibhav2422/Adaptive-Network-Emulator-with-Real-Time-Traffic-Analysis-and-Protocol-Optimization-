# PPT Reference Guide — Adaptive Network Emulator
### End Semester Review Presentation

---

## WHAT IS THIS PROJECT?

The **Adaptive Network Emulator** is a software-based network simulation system built entirely in Python. It simulates how data travels across a network — from the physical transmission of bits all the way up to application-level communication — using the full 7-layer OSI / TCP-IP model.
The key innovation is **adaptive optimization**: the system monitors real-time network conditions (congestion, packet loss, latency) and automatically adjusts its behavior to maintain performance. It also includes a **live web dashboard** for real-time visualization and a **property-based testing framework** for formal correctness validation.

Think of it like a smart highway system — it detects traffic jams and automatically adjusts speed limits to keep everything flowing.

---

## WHY WAS THIS BUILT? (Problem Statement)

Network protocol development has real challenges:
- Manual testing is slow and misses edge cases
- Protocol bugs are hard to reproduce
- Performance tuning requires endless experimentation
- Integration issues between layers are common
- No easy way to formally prove a protocol is correct

This project solves all of that in one place — a complete, testable, adaptive, and visual network simulation.

---

## PROJECT GOALS / OBJECTIVES

1. Implement a complete network protocol stack (Physical → Application, all 7 layers)
2. Validate protocol correctness using property-based testing (formal proofs)
3. Enable adaptive optimization based on live network conditions
4. Provide a reproducible experimentation framework
5. Support multiple transport protocols (Go-Back-N, Selective Repeat) and routing algorithms (Dijkstra, Distance Vector)
6. Build a real-time monitoring dashboard

---

## KEY ACHIEVEMENTS (Numbers to Quote in PPT)

| What | Target | Achieved |
|------|--------|----------|
| Requirements Coverage | 90% | 91.1% |
| Test Pass Rate | 95% | 99.5% (730/734 tests) |
| Code Coverage | 80% | >80% |
| Correctness Properties | 30+ | 38 properties |
| Throughput Improvement | 10% | 18.3% average |
| Total Lines of Code | — | ~14,680 (6,180 production + 8,500 test) |
| Development Time | — | 12 weeks |

---

## SYSTEM ARCHITECTURE (For Architecture Slide)

The system has 4 main layers stacked on top of each other:

```
[ Web Dashboard (Flask + Chart.js) ]
           ↕ HTTP / SSE
[ Monitoring & Metrics API ]
           ↕
[ Network Protocol Stack — 7 Layers ]
           ↕
[ Simulated Network Nodes A, B, C, D ]
```

### The 7-Layer Protocol Stack (Bottom to Top)

| Layer | Name | What It Does |
|-------|------|--------------|
| Layer 1 | Physical Layer | Simulates bit transmission, latency (5–50ms), packet loss (0–15%), jitter |
| Layer 2 | Data Link Layer | Frame encapsulation, CRC-32 error detection, Hamming code error correction |
| Layer 2 | MAC Layer | CSMA/CD simulation, collision detection, exponential backoff |
| Layer 3 | Network Layer | IP routing, Dijkstra & Distance Vector algorithms, packet forwarding |
| Layer 4 | Transport Layer | Adaptive TCP — Go-Back-N, Selective Repeat, sliding window (8–48 packets) |
| Layer 7 | Application Layer | HTTP, DNS, FTP protocols, file transfer, message transmission |

### Supporting Components
- **MetricsAPI** — collects, stores (500 snapshots), and broadcasts metrics via SSE
- **Optimization Module** — monitors conditions and triggers adaptive changes
- **Web Dashboard** — Flask backend + Chart.js frontend, real-time updates <2 seconds

---

## THE CORE INNOVATION — ADAPTIVE CONGESTION CONTROL

This is the most important technical contribution of the project.

### The Problem with Normal TCP
Standard TCP uses fixed algorithms (AIMD — Additive Increase, Multiplicative Decrease). It reacts slowly and doesn't use real-time metrics intelligently.

### Our Adaptive Algorithm

**Window Size Adjustment:**
```
if packet_loss > threshold:
    window_size = max(8, window_size / 2)   ← reduce aggressively
elif latency < target:
    window_size = min(48, window_size + 1)  ← increase gradually
```

**Route Cost Adjustment:**
```
adjusted_cost = base_cost × (1 + 2×utilization + 1.5×latency_factor + 3×loss_factor)
```

### What This Achieves
- Under 1% loss: +5.4% throughput improvement
- Under 5% loss: +30.6% throughput improvement
- Under 10% loss: +78.8% throughput improvement
- Average across all conditions: **+18.3% throughput**
- Retransmissions reduced by **31.4%**

### Protocol State Machine
```
IDLE → SENDING → CONGESTED → WAITING → RECOVERY → SENDING
```

---

## TRANSPORT LAYER — GBN vs SR vs ADAPTIVE

| Condition | Go-Back-N | Selective Repeat | Adaptive |
|-----------|-----------|-----------------|---------|
| 0% loss | 95.2 Mbps | 95.3 Mbps | 95.3 Mbps |
| 1% loss | 87.4 Mbps | 91.2 Mbps | 92.1 Mbps |
| 5% loss | 62.3 Mbps | 78.9 Mbps | 81.4 Mbps |
| 10% loss | 38.2 Mbps | 61.7 Mbps | 68.3 Mbps |
| 20% loss | 15.6 Mbps | 38.4 Mbps | 45.2 Mbps |

**Key point:** SR outperforms GBN by 14–40% under packet loss. Adaptive beats both.

**Go-Back-N:** On any packet loss, retransmits that packet AND all packets after it. Simple but wasteful.

**Selective Repeat:** Only retransmits the specific lost packet. More efficient, more complex.

**Adaptive:** Dynamically adjusts window size based on real-time conditions. Best of both worlds.

---

## ROUTING ALGORITHMS

### Dijkstra (Link-State Routing)
- Each node knows the complete network topology
- Computes shortest path to every destination
- Time complexity: O(E log V)
- Fast convergence, higher memory use
- Used in real-world OSPF protocol

### Distance Vector (Bellman-Ford)
- Each node only knows distances to neighbors
- Exchanges info with neighbors iteratively
- Time complexity: O(V²)
- Simpler but slower convergence (2–6 iterations)

### Performance Comparison

| Nodes | Dijkstra Time | Distance Vector Time |
|-------|--------------|---------------------|
| 3 | 0.12ms | 0.18ms |
| 5 | 0.24ms | 0.45ms |
| 10 | 0.68ms | 1.82ms |

Dijkstra is 2–3× faster than Distance Vector.

### Traffic-Aware Routing (Innovation)
Routes are dynamically recomputed based on live utilization, latency, and loss — not just static link costs. This gives 15–25% throughput improvement in congested networks.

---

## ERROR DETECTION & CORRECTION

### CRC-32 (Cyclic Redundancy Check)
- Detects all single-bit errors
- Detects all double-bit errors
- Detects burst errors up to 32 bits
- Applied to every frame

### Hamming Code
- Corrects single-bit errors
- Detects two-bit errors
- Applied to critical header fields
- Payload uses CRC only (detection without correction, due to overhead)

---

## PROPERTY-BASED TESTING (Formal Validation)

This is what makes this project academically significant.

### What is Property-Based Testing?
Instead of writing "test case: input X gives output Y", you write a **universal property** — a rule that must hold for ALL possible inputs. The testing framework (Hypothesis) automatically generates hundreds of random inputs to try to break the property.

### Example Properties
- "For any data passed through all 7 layers, the received data must be byte-for-byte identical to the sent data"
- "For any network topology, Dijkstra must always find the shortest path"
- "For any packet loss event in GBN, all packets from the lost one onward must be retransmitted"
- "For any frame with a single bit flip, Hamming code must correct it and deliver original data"

### Results
- **38 correctness properties** defined
- **100+ test iterations per property** (Hypothesis generates random inputs)
- **100% of properties passing**
- Discovered **12 bugs** during development that manual testing missed

### Test Pyramid

```
        [ Property-Based Tests: 38 ]   ← formal correctness proofs
       [ Integration Tests: 50+ ]      ← cross-layer interactions
      [ Unit Tests: 640+ ]             ← individual components
```

Total: **734 tests, 99.5% pass rate**

---

## LIVE DASHBOARD

### Technology Stack
- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript
- Charts: Chart.js
- Real-time updates: Server-Sent Events (SSE) — no polling needed
- Port: 5000 (localhost)

### What the Dashboard Shows
1. **Live Metrics** — Throughput (bps), Latency (ms), Packet Loss (%), Jitter (ms)
2. **Real-time Charts** — Throughput history, Latency history, Packet Loss history
3. **Network Topology** — Animated nodes (A, B, C, D) with live link status
   - Green node = healthy, Yellow = congested, Red = failed
4. **Protocol State** — Current window size, unacked packets, retransmissions, state badge
5. **Alerts Panel** — Info / Warning / Critical notifications
6. **Historical Data Table** — Detailed metrics log

### Dashboard Update Speed
- Updates within **<2 seconds** of any network condition change
- Validated by property-based test (Property 32)

---

## DEMO PHASES (For Live Demo Slide)

The demo runs through 5 phases (~85 seconds total):

| Phase | Duration | What Happens | What to Watch |
|-------|----------|-------------|---------------|
| 1 — Normal | 20s | Light traffic, stable metrics | Smooth charts, green nodes, window=32 |
| 2 — Traffic Burst | 15s | Sudden traffic increase | Throughput spike, window grows to 48 |
| 3 — Congestion | 20s | Network overloaded | Nodes turn yellow, window drops 48→8, loss spikes |
| 4 — Node Failure | 15s | Node C fails, traffic reroutes | Node C turns red, alternate paths activate |
| 5 — Recovery | 15s | Node C recovers, stabilizes | Node C turns green, window grows 16→32 |

**Phase 3 is the most important** — it shows the adaptive algorithm in action. Window size automatically drops from 48 to 8 to prevent network collapse.

---

## COMPARISON WITH EXISTING TOOLS

| Feature | NS-3 | OMNeT++ | Mininet | This Project |
|---------|------|---------|---------|-------------|
| Full Protocol Stack | ✅ | ✅ | ❌ | ✅ |
| Property-Based Testing | ❌ | ❌ | ❌ | ✅ |
| Adaptive Optimization | ❌ | ❌ | ❌ | ✅ |
| Traffic-Aware Routing | ⚠️ | ⚠️ | ❌ | ✅ |
| Python API | ✅ | ❌ | ✅ | ✅ |
| Reproducibility | ⚠️ | ⚠️ | ❌ | ✅ |
| Learning Curve | High | High | Medium | Low |
| Simulation Speed (10 nodes) | ~45s | ~38s | — | ~12s |

**This project is 3–4× faster than NS-3 and is the only one with property-based testing and built-in adaptive optimization.**

---

## SCALABILITY

| Nodes | Simulation Time | Memory | CPU |
|-------|----------------|--------|-----|
| 2 | 1.2s | 45 MB | 12% |
| 5 | 3.8s | 78 MB | 28% |
| 10 | 12.4s | 156 MB | 54% |
| 20 | 48.7s | 312 MB | 89% |

Scales linearly up to 10 nodes. Practical limit is 10–15 nodes on standard hardware.

---

## PROJECT STRUCTURE (For Code Slide)

```
src/
├── physical_layer.py       ← Layer 1
├── mac_layer.py            ← Layer 2 (MAC)
├── data_link_layer.py      ← Layer 2 (Data Link)
├── network_layer.py        ← Layer 3
├── transport_layer.py      ← Layer 4 (Adaptive TCP)
├── application_layer.py    ← Layer 7
├── network_node.py         ← Node integration
├── dashboard.py            ← Web dashboard
└── data_models.py          ← Shared data structures

tests/
├── test_properties_*.py    ← 38 property-based tests
├── test_*_layer.py         ← Unit tests per layer
└── test_*_integration.py   ← Integration tests

live_demo.py                ← Run the live demo
start_dashboard.py          ← Dashboard only
```

---

## TECHNICAL SPECS

- Language: Python 3.8+
- Key Libraries: Flask, Hypothesis, pytest, PyYAML, NumPy
- Architecture: Event-driven, multi-threaded
- Storage: In-memory circular buffer (500 snapshots)
- Threading: Main thread + Flask server thread + Simulation thread + Monitoring thread
- Config: YAML files (default, dev, prod, test)

---

## LATENCY OVERHEAD

| Network Delay | Measured Latency | Protocol Overhead |
|--------------|-----------------|------------------|
| 10ms | 10.2ms | 2% |
| 50ms | 50.8ms | 1.6% |
| 100ms | 101.3ms | 1.3% |
| 200ms | 202.1ms | 1.05% |

Protocol overhead is less than 2% — negligible.

---

## APPLICATIONS / USE CASES

1. **Education** — Students can visualize how each network layer works, run experiments without hardware
2. **Research** — Reproducible experiments, formal correctness validation, platform for new protocol development
3. **Development** — Protocol validation before deployment, performance testing
4. **Teaching Tool** — Professors can demonstrate congestion, routing, error correction live

---

## FUTURE WORK

Short-term:
- Fix 4 remaining integration test failures (node ID ↔ IP mapping issue)
- PyShark integration for real packet capture
- Full web dashboard with topology editor

Medium-term:
- TCP variants: Reno, Cubic, BBR
- OSPF and BGP routing protocols
- Parallel simulation execution

Long-term:
- Machine learning for congestion prediction
- Distributed simulation (100+ nodes)
- Hardware-in-the-loop testing

---

## KEY REFERENCES (For Literature Slide)

1. Kurose & Ross — *Computer Networking: A Top-Down Approach* (8th ed., 2021)
2. Tanenbaum & Wetherall — *Computer Networks* (5th ed., 2011)
3. Dijkstra (1959) — Original shortest path algorithm paper
4. Jacobson (1988) — *Congestion Avoidance and Control* (foundational TCP paper)
5. Claessen & Hughes (2000) — *QuickCheck* (original property-based testing paper)
6. MacIver (2019) — *Hypothesis: A New Approach to Property-Based Testing*
7. RFC 793 — TCP specification
8. RFC 5681 — TCP Congestion Control
9. NS-3, OMNeT++, Mininet — compared tools

---

## SUGGESTED PPT SLIDE STRUCTURE

1. Title Slide — Project name, team, date
2. Problem Statement — Why this project matters
3. Objectives — What we set out to build
4. System Architecture — The 4-layer diagram + 7-layer protocol stack
5. Layer-by-Layer Walkthrough — Brief explanation of each layer
6. Core Innovation: Adaptive Congestion Control — Algorithm + results table
7. Transport Protocols: GBN vs SR vs Adaptive — Throughput comparison table
8. Routing Algorithms — Dijkstra vs Distance Vector
9. Error Detection & Correction — CRC + Hamming
10. Property-Based Testing — What it is, 38 properties, 12 bugs found
11. Test Results — 734 tests, 99.5% pass rate, test pyramid
12. Live Dashboard — Screenshot + what each panel shows
13. Demo Phases — Table of 5 phases
14. Comparison with Existing Tools — Feature comparison table
15. Performance & Scalability — Numbers
16. Applications / Use Cases
17. Future Work
18. Conclusion — Key numbers, what was achieved
19. References
20. Q&A

---

## ONE-LINER SUMMARY FOR INTRODUCTION

> "We built a complete 7-layer network protocol emulator in Python that simulates real network behavior, automatically adapts to congestion using a novel algorithm, formally validates correctness with 38 property-based tests, and visualizes everything on a live web dashboard — achieving 18.3% throughput improvement and 99.5% test pass rate."

---

## ANSWERS TO LIKELY QUESTIONS FROM MAM

**Q: Is the demo live or pre-recorded?**
A: It's live. Each run has random variations because packet loss uses random number generation. The code is in `live_demo.py`.

**Q: How is this different from regular TCP?**
A: Standard TCP uses fixed AIMD algorithms. Our system uses real-time metrics (loss rate, latency) to make smarter, faster decisions. The window size adapts more precisely.

**Q: What is property-based testing and why is it important?**
A: Instead of testing specific cases, we define universal rules (properties) that must hold for ALL inputs. The Hypothesis library generates 100+ random test cases per property automatically. This found 12 bugs that manual testing missed.

**Q: What are the 4 nodes in the topology?**
A: Nodes A, B, C, D — each with IP addresses 10.0.0.1 through 10.0.0.4. Each node has a complete protocol stack. They communicate through simulated network links.

**Q: What happens when a node fails?**
A: Traffic automatically reroutes through alternate paths. The routing table updates dynamically. The network keeps running — this is fault tolerance.

**Q: What are the limitations?**
A: Practical limit of 10–15 nodes on standard hardware. No real packet capture yet (PyShark integration planned). 4 integration tests still failing due to a node ID ↔ IP mapping issue.

**Q: What is the real-world application?**
A: Data centers, ISPs, IoT networks, satellite communications — anywhere network congestion is a problem. Also excellent as an educational tool for networking courses.
