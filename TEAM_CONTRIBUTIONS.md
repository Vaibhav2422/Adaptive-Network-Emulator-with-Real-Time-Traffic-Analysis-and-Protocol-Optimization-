# Team Contributions — Adaptive Network Emulator
### Course Project | End Semester Review

---

## Team Structure

| Role | Name |
|------|------|
| Group Leader | Vaibhav Hade |
| Assistant Group Leader | Omkar Ghanure |
| Member | Satyajeet Ghadge |
| Member | Aaryan Giri |
| Member | Onkar Gawde |

---

## 1. Vaibhav Hade — Group Leader

**Responsibilities:** Project leadership, research, architecture, and documentation

- Defined the overall system architecture and 7-layer protocol stack design
- Conducted literature review of base papers (Kurose & Ross, Tanenbaum, Dijkstra, Jacobson, Claessen & Hughes, RFCs 793/5681)
- Filed patent disclosure covering 4 novel innovations and 12 claims
- Authored and formatted the research paper and technical report
- Designed the adaptive congestion control algorithm (window adjustment + traffic-aware routing)
- Wrote the requirements specification and design document
- Coordinated task distribution and tracked project milestones
- Prepared executive summary and all project deliverables documentation
- Led end-semester review preparation and PPT content planning

---

## 2. Omkar Ghanure — Assistant Group Leader

**Responsibilities:** Core protocol implementation and testing coordination

- Implemented the Transport Layer — Go-Back-N (GBN) and Selective Repeat (SR) protocols
- Built the sliding window mechanism with flow control and congestion detection
- Assisted group leader in coordinating tasks across team members
- Integrated transport layer with network and application layers
- Wrote unit tests for transport layer (`test_transport_layer.py`, `test_transport_reliable_delivery.py`)
- Wrote property-based tests for GBN and SR (`test_properties_gbn.py`, `test_properties_sr.py`)
- Validated sliding window constraint and sequence number properties
- Supported debugging of integration issues across layers
- Reviewed and verified test results for the full test suite

---

## 3. Satyajeet Ghadge — Member

**Responsibilities:** Network layer, routing algorithms, and optimization module

- Implemented the Network Layer — IP addressing, packet forwarding, routing table management
- Built Dijkstra link-state routing algorithm (`dijkstra_router.py`)
- Built Distance Vector routing algorithm using Bellman-Ford (`distance_vector_router.py`)
- Implemented traffic-aware dynamic route optimization (multi-factor cost adjustment)
- Built the ICMP simulator for network diagnostics (`icmp_simulator.py`)
- Wrote unit and property-based tests for network layer and routing (`test_network_layer.py`, `test_properties_network_layer.py`, `test_properties_distance_vector.py`)
- Verified routing correctness properties (shortest path optimality, convergence)
- Contributed to integration tests for packet forwarding (`test_packet_forwarding_integration.py`)

---

## 4. Aaryan Giri — Member

**Responsibilities:** Lower layers (Physical, MAC, Data Link) and error handling

- Implemented the Physical Layer — transmission delay, propagation delay, packet loss, jitter simulation (`physical_layer.py`)
- Implemented the MAC Layer — CSMA/CD simulation, collision detection, exponential backoff (`mac_layer.py`)
- Implemented the Data Link Layer — frame encapsulation, CRC-32 error detection, Hamming code error correction (`data_link_layer.py`)
- Built error injection mechanism for testing error handling scenarios
- Wrote unit and property-based tests for all three layers (`test_physical_layer.py`, `test_mac_layer.py`, `test_data_link_layer.py`, `test_properties_mac_layer.py`, `test_properties_data_link.py`)
- Validated CRC round-trip, Hamming single-bit correction, and collision detection properties
- Contributed to frame transmission integration tests (`test_integration_frame_transmission.py`)

---

## 5. Onkar Gawde — Member

**Responsibilities:** Application layer, dashboard, demo, and configuration

- Implemented the Application Layer — HTTP, DNS, FTP protocols, file transfer service, message transmission (`application_layer.py`, `file_transfer_service.py`)
- Built the real-time web dashboard using Flask and Chart.js (`dashboard.py`, `dashboard_enhanced.py`)
- Implemented Server-Sent Events (SSE) for live metric push updates
- Built the MetricsAPI with in-memory circular buffer (500 snapshots), alert system, and topology data
- Created the live demo scripts (`live_demo.py`, `live_demo_loop.py`, `simple_demo.py`)
- Wrote the demo explanation and visual demo guide
- Managed configuration files (YAML — default, dev, prod, test) and logging setup
- Wrote application layer tests (`test_application_layer.py`, `test_properties_application.py`)
- Set up pytest configuration, coverage reporting, and the `run_tests.py` script

---

## Contribution Summary

| Member | Primary Area | Key Deliverable |
|--------|-------------|----------------|
| Vaibhav Hade | Architecture, Research, Documentation | Patent filing, Literature review, Research paper, System design |
| Omkar Ghanure | Transport Layer, Testing | GBN/SR protocols, Sliding window, Test coordination |
| Satyajeet Ghadge | Network Layer, Routing | Dijkstra, Distance Vector, Traffic-aware optimization |
| Aaryan Giri | Physical/MAC/Data Link Layers | CRC, Hamming code, CSMA/CD, Error handling |
| Onkar Gawde | Application Layer, Dashboard, Demo | Flask dashboard, SSE, Live demo, Configuration |

---

*All members contributed to integration testing, code review, and final presentation preparation.*
