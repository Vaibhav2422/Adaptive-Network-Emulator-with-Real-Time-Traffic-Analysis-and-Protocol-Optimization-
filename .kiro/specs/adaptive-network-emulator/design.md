# Design Document: Adaptive Network Emulator

## Overview

The Adaptive Network Emulator is a modular, software-based network simulation system implemented in Python. It provides a complete protocol stack from Application to Physical layer, integrating real-time traffic analysis and adaptive optimization capabilities. The system uses an event-driven architecture with clear layer separation, enabling educational exploration of network protocols and performance optimization strategies.

The emulator operates on a local system, simulating multiple network nodes that communicate through software-defined channels. Each layer is implemented as a separate module with well-defined interfaces, allowing independent development and testing of protocol implementations.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Dashboard                      │
│                      (Flask Web UI)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Traffic Analyzer & Optimizer                │
│              (PyShark Integration + Metrics)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      Network Emulator Core                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Application Layer (TCP/UDP)               │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │       Transport Layer (GBN / SR Protocols)           │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │    Network Layer (IP + Routing: Dijkstra / DV)       │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │   Data Link Layer (Framing + CRC + Hamming)          │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │      MAC Layer (CSMA/CD Simulation)                  │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │    Physical Layer (Abstract Channel)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Event-Driven Architecture

The emulator uses an event-driven model where:
- Each layer processes events asynchronously
- Events include: packet arrival, timer expiration, acknowledgment receipt
- A central event queue manages scheduling and execution
- Layers communicate through message passing with clear interfaces

### Node Architecture

Each simulated node contains:
- Complete protocol stack (all layers)
- Local routing table
- Packet buffers at each layer
- Statistics collectors
- Configuration parameters

## Components and Interfaces

### 1. Application Layer

**Purpose:** Provides user-facing communication services using TCP and UDP sockets.

**Components:**
- `TCPSocketHandler`: Manages TCP connections for reliable communication
- `UDPSocketHandler`: Manages UDP communication for unreliable transfer
- `FileTransferService`: Handles file transfer operations with integrity checking
- `MessageService`: Handles text message transmission
- `ConnectionManager`: Manages client-server and peer-to-peer modes

**Interfaces:**
```python
class ApplicationLayer:
    def send_message(node_id: str, message: str, protocol: str) -> bool
    def send_file(node_id: str, file_path: str, protocol: str) -> bool
    def receive_data() -> tuple[str, bytes]
    def establish_connection(remote_node: str, mode: str) -> bool
    def close_connection(connection_id: str) -> None
```

**Data Flow:**
- Receives user data (messages/files)
- Segments data into chunks if needed
- Passes segments to Transport Layer with destination information
- Receives reassembled data from Transport Layer

### 2. Transport Layer

**Purpose:** Provides reliable data transfer using GBN or SR protocols with flow control.

**Components:**
- `GBNProtocol`: Go-Back-N implementation with sliding window
- `SRProtocol`: Selective Repeat implementation with selective acknowledgment
- `SlidingWindow`: Window management for both protocols
- `FlowController`: Manages transmission rate based on receiver capacity
- `CongestionDetector`: Monitors packet loss and delay for adaptation
- `SequenceManager`: Handles sequence number generation and validation
- `AcknowledgmentHandler`: Processes ACKs and updates window state

**Interfaces:**
```python
class TransportLayer:
    def send_segment(data: bytes, dest: str, protocol: str) -> None
    def receive_segment(segment: Segment) -> None
    def handle_acknowledgment(ack: Acknowledgment) -> None
    def set_window_size(size: int) -> None
    def get_statistics() -> TransportStats
```

**Protocol Behavior:**

*Go-Back-N:*
- Maintains send window of size N
- Sends packets sequentially within window
- On timeout or NAK, retransmits from lost packet onward
- Receiver only accepts in-order packets

*Selective Repeat:*
- Maintains send and receive windows
- Retransmits only specific lost packets
- Receiver buffers out-of-order packets
- More efficient but more complex

**Flow Control:**
- Sliding window limits outstanding packets
- Window size adjusted based on receiver feedback
- Prevents sender from overwhelming receiver

**Congestion Awareness:**
- Monitors packet loss rate
- Detects increasing latency
- Reduces window size when congestion detected
- Gradually increases window when conditions improve

### 3. Network Layer

**Purpose:** Handles IP addressing, routing, and packet forwarding.

**Components:**
- `IPAddressManager`: Manages IP address assignment and subnetting
- `DijkstraRouter`: Link-state routing using Dijkstra's algorithm
- `DistanceVectorRouter`: Distance vector routing implementation
- `RoutingTable`: Stores and manages routing information
- `RouteSelector`: Chooses routes based on current conditions
- `ICMPSimulator`: Provides logical ICMP-like diagnostics
- `PacketForwarder`: Forwards packets based on routing decisions

**Interfaces:**
```python
class NetworkLayer:
    def send_packet(data: bytes, dest_ip: str) -> None
    def receive_packet(packet: IPPacket) -> None
    def update_routing_table(topology: NetworkTopology) -> None
    def get_next_hop(dest_ip: str) -> str
    def compute_routes(algorithm: str) -> None
    def get_routing_table() -> dict
```

**Routing Algorithms:**

*Dijkstra (Link State):*
- Each node maintains complete topology
- Computes shortest paths to all destinations
- Updates when link costs change
- Converges quickly but requires more memory

*Distance Vector:*
- Each node maintains distance to all destinations
- Exchanges routing information with neighbors
- Uses Bellman-Ford algorithm
- Simpler but slower convergence

**Dynamic Route Selection:**
- Monitors link utilization and latency
- Adjusts link costs based on traffic conditions
- Recomputes routes when conditions change significantly
- Balances load across multiple paths when available

### 4. Data Link Layer

**Purpose:** Provides framing, error detection, and error correction.

**Components:**
- `FrameBuilder`: Constructs frames with headers and trailers
- `CRCCalculator`: Computes CRC checksums for error detection
- `HammingCodec`: Implements Hamming code for error correction
- `ErrorInjector`: Simulates bit errors for testing
- `FrameValidator`: Validates received frames

**Interfaces:**
```python
class DataLinkLayer:
    def send_frame(packet: bytes, dest_mac: str) -> None
    def receive_frame(frame: Frame) -> None
    def inject_error(frame: Frame, error_rate: float) -> Frame
    def detect_error(frame: Frame) -> bool
    def correct_error(frame: Frame) -> tuple[bool, bytes]
```

**Frame Structure:**
```
┌──────────┬──────────┬─────────┬──────────┬──────────┐
│ Preamble │  Header  │ Payload │  CRC     │  Trailer │
│ (8 bits) │ (varies) │ (data)  │ (32 bits)│ (8 bits) │
└──────────┴──────────┴─────────┴──────────┴──────────┘
```

**Error Detection (CRC):**
- Uses CRC-32 polynomial
- Computes checksum over header and payload
- Appends checksum to frame
- Receiver recomputes and compares
- Detects burst errors up to 32 bits

**Error Correction (Hamming Code):**
- Adds parity bits to data
- Can correct single-bit errors
- Can detect two-bit errors
- Applied to critical header fields
- Payload uses CRC only (detection without correction)

**Error Injection:**
- Configurable bit error rate
- Random bit flips in frames
- Used for testing error handling mechanisms

### 5. MAC Layer

**Purpose:** Simulates media access control with collision detection.

**Components:**
- `CSMAController`: Implements carrier sense logic
- `CollisionDetector`: Simulates collision detection
- `BackoffManager`: Implements exponential backoff algorithm
- `ChannelMonitor`: Tracks channel state (idle/busy)

**Interfaces:**
```python
class MACLayer:
    def request_transmission(frame: Frame) -> None
    def sense_channel() -> bool
    def handle_collision() -> int
    def transmit_frame(frame: Frame) -> bool
```

**CSMA/CD Simulation:**
1. Sense channel before transmission
2. If idle, begin transmission
3. If busy, wait and retry
4. Detect collisions during transmission
5. On collision, stop and execute backoff
6. Retry after backoff period

**Exponential Backoff:**
- After collision, wait random time in [0, 2^k - 1] slots
- k = min(attempt_count, 10)
- Maximum 16 attempts before giving up
- Slot time configurable (typically 51.2 μs for Ethernet)

### 6. Physical Layer

**Purpose:** Provides abstract transmission channel with configurable characteristics.

**Components:**
- `TransmissionChannel`: Simulates physical medium
- `DelaySimulator`: Adds propagation and transmission delays
- `LossSimulator`: Simulates packet loss
- `BitRateController`: Manages transmission bit rate

**Interfaces:**
```python
class PhysicalLayer:
    def transmit(bits: bytes, dest: str) -> None
    def receive() -> bytes
    def set_delay(delay_ms: float) -> None
    def set_loss_rate(rate: float) -> None
    def set_bit_rate(bps: int) -> None
```

**Abstraction Model:**
- Simulates propagation delay (distance-based)
- Simulates transmission delay (size/bitrate)
- Simulates random packet loss
- No actual physical signal modeling
- Assumes perfect synchronization
- No interference or noise modeling beyond loss

**Configurable Parameters:**
- Propagation delay: 1-100 ms
- Bit rate: 1 Mbps - 1 Gbps
- Loss rate: 0-50%
- Bit error rate: 0-10^-3

### 7. Traffic Analyzer

**Purpose:** Captures and analyzes network traffic in real-time.

**Components:**
- `PacketCapture`: Integrates with PyShark for packet capture
- `MetricsCalculator`: Computes performance metrics
- `StatisticsCollector`: Aggregates statistics over time
- `PerformanceLogger`: Logs metrics to files
- `ComparisonEngine`: Compares before/after optimization

**Interfaces:**
```python
class TrafficAnalyzer:
    def start_capture(interface: str) -> None
    def stop_capture() -> None
    def get_throughput() -> float
    def get_latency() -> float
    def get_packet_loss() -> float
    def get_retransmissions() -> int
    def export_metrics(file_path: str) -> None
    def compare_performance(baseline: Metrics, current: Metrics) -> dict
```

**Metrics Collected:**
- **Throughput:** Bytes successfully delivered per second
- **Latency:** End-to-end packet delay (mean, median, 95th percentile)
- **Packet Loss:** Percentage of packets not delivered
- **Retransmissions:** Count of retransmitted packets
- **Jitter:** Variation in packet delay
- **Protocol Distribution:** Breakdown by protocol type
- **Layer-specific metrics:** Per-layer processing time

**PyShark Integration:**
- Captures packets on loopback interface
- Filters by emulator-specific markers
- Parses packet headers at each layer
- Extracts timing information
- Correlates packets across layers

### 8. Optimization Module

**Purpose:** Monitors network conditions and adapts parameters dynamically.

**Components:**
- `ConditionMonitor`: Continuously monitors network state
- `OptimizationEngine`: Decides when and how to optimize
- `RouteOptimizer`: Adjusts routing paths
- `FlowOptimizer`: Adjusts flow control parameters
- `DecisionLogger`: Logs optimization decisions and rationale

**Interfaces:**
```python
class OptimizationModule:
    def monitor_conditions() -> NetworkConditions
    def optimize_routing(conditions: NetworkConditions) -> None
    def optimize_flow_control(conditions: NetworkConditions) -> None
    def enable_adaptation(enabled: bool) -> None
    def get_optimization_log() -> list[OptimizationEvent]
```

**Optimization Strategies:**

*Routing Optimization:*
- Monitors link utilization and latency
- Identifies congested paths
- Computes alternative routes
- Updates routing tables dynamically
- Balances load across available paths

*Flow Control Optimization:*
- Monitors packet loss rate
- Detects increasing queuing delay
- Adjusts window size (increase/decrease)
- Modifies timeout values
- Adapts retransmission strategy

**Triggering Conditions:**
- Packet loss > 5%: Reduce window size, find alternate route
- Latency increase > 50%: Check for congestion, reroute if possible
- Throughput drop > 30%: Investigate bottleneck, adjust parameters
- Retransmission rate > 10%: Increase timeout, reduce window

**Decision Justification:**
- Each optimization logged with timestamp
- Records triggering condition and metric values
- Documents action taken and expected effect
- Tracks actual performance change
- Enables post-analysis of optimization effectiveness

### 9. Monitoring Dashboard

**Purpose:** Provides real-time visualization of network state and metrics.

**Components:**
- `FlaskWebServer`: Serves web interface
- `MetricsAPI`: REST API for metrics data
- `VisualizationEngine`: Generates charts and graphs
- `TopologyRenderer`: Displays network topology
- `AlertManager`: Highlights anomalies and optimizations

**Interfaces:**
```python
class Dashboard:
    def start_server(port: int) -> None
    def update_metrics(metrics: dict) -> None
    def render_topology(topology: NetworkTopology) -> None
    def add_alert(message: str, severity: str) -> None
```

**Dashboard Views:**

*Metrics View:*
- Real-time line charts for throughput, latency, loss
- Current values with trend indicators
- Historical data over configurable time window
- Per-node and aggregate statistics

*Topology View:*
- Visual representation of network nodes and links
- Link thickness indicates utilization
- Color coding for link health (green/yellow/red)
- Active routes highlighted
- Animated packet flow

*Protocol View:*
- Active protocol states (GBN/SR window positions)
- Routing table contents
- Queue depths at each layer
- Protocol-specific statistics

*Optimization View:*
- Recent optimization events
- Performance before/after comparison
- Optimization effectiveness metrics
- Manual override controls

**Technology Stack:**
- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript
- Charts: Chart.js or Plotly
- Real-time updates: WebSocket or Server-Sent Events
- Lightweight design: No heavy frameworks

## Data Models

### Packet Structure

```python
@dataclass
class Packet:
    packet_id: str
    timestamp: float
    source_ip: str
    dest_ip: str
    protocol: str
    payload: bytes
    headers: dict[str, bytes]  # Layer-specific headers
    
@dataclass
class Segment:
    sequence_num: int
    ack_num: int
    window_size: int
    flags: set[str]  # SYN, ACK, FIN, etc.
    data: bytes
    checksum: int

@dataclass
class Frame:
    preamble: bytes
    dest_mac: str
    source_mac: str
    payload: bytes
    crc: int
    error_corrected: bool
```

### Routing Table Entry

```python
@dataclass
class RouteEntry:
    destination: str
    next_hop: str
    cost: float
    interface: str
    timestamp: float
    metric_type: str  # hop_count, latency, bandwidth
```

### Network Topology

```python
@dataclass
class Link:
    node_a: str
    node_b: str
    cost: float
    capacity: float
    utilization: float
    latency: float
    loss_rate: float

@dataclass
class NetworkTopology:
    nodes: list[str]
    links: list[Link]
    adjacency_matrix: np.ndarray
```

### Metrics Data

```python
@dataclass
class NetworkMetrics:
    timestamp: float
    throughput: float  # bytes/sec
    latency: float  # milliseconds
    packet_loss: float  # percentage
    retransmissions: int
    jitter: float  # milliseconds
    active_connections: int
    queue_depth: dict[str, int]  # per layer
```

### Configuration

```python
@dataclass
class EmulatorConfig:
    num_nodes: int
    topology_type: str  # mesh, star, ring, custom
    routing_algorithm: str  # dijkstra, distance_vector
    transport_protocol: str  # gbn, sr
    window_size: int
    timeout_ms: int
    error_rate: float
    loss_rate: float
    enable_optimization: bool
    capture_packets: bool
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, I've identified the following consolidations to eliminate redundancy:

**Consolidations:**
1. Properties 1.2 and 1.4 (layer encapsulation) can be combined into a single comprehensive property about data preservation through layers
2. Properties 3.7 and 3.8 (sequence numbers and window advancement) are related aspects of the same sliding window mechanism
3. Properties 4.2, 4.3, and 4.8 (routing algorithms) can be consolidated into properties about routing correctness
4. Properties 5.4 and 5.5 (CRC computation and verification) are two sides of the same round-trip property
5. Properties 7.2, 7.3, 7.4, 7.5 (various metrics) are all instances of "metrics should be calculated correctly"
6. Properties 8.2, 8.3, 8.4 (various optimization triggers) can be consolidated into a general property about optimization responses

**Retained Properties:**
- Each property provides unique validation value after consolidation
- Properties testing different protocols (GBN vs SR) are kept separate as they validate different behaviors
- Properties testing different layers are kept separate as they validate different components
- Round-trip properties (file transfer, CRC, frame correction) are essential and retained

### Correctness Properties

Property 1: Layer encapsulation preserves data integrity
*For any* data passed from an upper layer to a lower layer, the lower layer should add headers/trailers but preserve the original data unchanged, and when the data is decapsulated at the receiving end, it should match the original exactly.
**Validates: Requirements 1.2, 1.4**

Property 2: TCP file transfer round-trip
*For any* file transferred using TCP sockets, the received file should be byte-for-byte identical to the sent file.
**Validates: Requirements 2.2, 2.5**

Property 3: Connection lifecycle cleanup
*For any* connection established (client-server or peer-to-peer), performing setup followed by teardown should leave the system in a clean state with no resource leaks.
**Validates: Requirements 2.6**

Property 4: GBN retransmission behavior
*For any* sequence of packets transmitted using Go-Back-N where packet N is lost, all packets from N onward should be retransmitted, even if packets N+1, N+2, etc. were already sent.
**Validates: Requirements 3.3**

Property 5: SR selective retransmission
*For any* sequence of packets transmitted using Selective Repeat where packet N is lost, only packet N should be retransmitted, and other packets should not be resent.
**Validates: Requirements 3.4**

Property 6: Sliding window constraint
*For any* transport protocol (GBN or SR), the number of unacknowledged packets in flight should never exceed the configured window size.
**Validates: Requirements 3.5**

Property 7: Sequence number monotonicity
*For any* sequence of packets sent by the transport layer, the sequence numbers should be monotonically increasing (modulo sequence space wraparound).
**Validates: Requirements 3.7**

Property 8: Window advancement on ACK
*For any* acknowledgment received, if the ACK number is within the current window, the window should slide forward to exclude acknowledged packets.
**Validates: Requirements 3.8**

Property 9: Congestion adaptation
*For any* detection of packet loss or increased delay above threshold, the transport layer should adapt by reducing window size or adjusting timeout values.
**Validates: Requirements 3.6**

Property 10: Dijkstra shortest path correctness
*For any* network topology with weighted links, the Dijkstra algorithm should compute paths where the total cost from source to any destination is minimal among all possible paths.
**Validates: Requirements 4.2, 4.8**

Property 11: Distance Vector convergence
*For any* stable network topology, the Distance Vector algorithm should eventually converge such that all nodes have consistent routing information and packets reach their destinations via valid paths.
**Validates: Requirements 4.3**

Property 12: Dynamic routing update
*For any* change in network topology (link failure, cost change), the routing tables should be updated within a bounded time to reflect the new topology.
**Validates: Requirements 4.4**

Property 13: Route selection optimality
*For any* routing decision when multiple paths exist, the selected path should have better or equal metrics (latency, loss, utilization) compared to alternative paths.
**Validates: Requirements 4.5**

Property 14: Frame structure completeness
*For any* payload passed to the Data Link Layer, the resulting frame should contain a valid header, the payload, and a trailer with CRC.
**Validates: Requirements 5.1**

Property 15: CRC error detection round-trip
*For any* frame created with valid CRC, if no errors are introduced, CRC verification should pass; if bit errors are introduced, CRC verification should detect them with high probability.
**Validates: Requirements 5.4, 5.5**

Property 16: Hamming code single-bit correction
*For any* data encoded with Hamming code, if exactly one bit is flipped, the Hamming decoder should correct the error and recover the original data.
**Validates: Requirements 5.6**

Property 17: Error correction success delivers original data
*For any* frame with correctable errors, after error correction succeeds, the delivered data to the Network Layer should match the original data before error injection.
**Validates: Requirements 5.8**

Property 18: Uncorrectable error handling
*For any* frame with uncorrectable errors (multiple bit flips beyond Hamming capability), the Data Link Layer should discard the frame and signal packet loss rather than delivering corrupted data.
**Validates: Requirements 5.9**

Property 19: Collision detection on simultaneous transmission
*For any* scenario where two or more nodes attempt transmission simultaneously on the same channel, the MAC layer should detect a collision.
**Validates: Requirements 6.2**

Property 20: Exponential backoff after collision
*For any* collision detected, the backoff time should be randomly selected from [0, 2^min(k,10) - 1] slots where k is the collision attempt number.
**Validates: Requirements 6.3**

Property 21: Carrier sense before transmission
*For any* transmission attempt, the MAC layer should sense the channel first, and only transmit if the channel is idle.
**Validates: Requirements 6.6**

Property 22: Throughput calculation accuracy
*For any* sequence of packets transmitted over a time interval, the calculated throughput should equal (total bytes successfully delivered) / (time interval).
**Validates: Requirements 7.2**

Property 23: Latency measurement accuracy
*For any* packet transmitted, the measured latency should equal (receive timestamp - send timestamp).
**Validates: Requirements 7.3**

Property 24: Packet loss calculation accuracy
*For any* transmission session, the packet loss percentage should equal (packets lost / packets sent) × 100.
**Validates: Requirements 7.4**

Property 25: Retransmission counting accuracy
*For any* transmission session using a reliable protocol, the retransmission count should equal the actual number of packets retransmitted.
**Validates: Requirements 7.5**

Property 26: Metric timestamp association
*For any* metric recorded by the Traffic Analyzer, it should have an associated timestamp indicating when the measurement was taken.
**Validates: Requirements 7.6**

Property 27: Packet categorization correctness
*For any* captured packet, it should be correctly categorized by its protocol type (TCP/UDP/ICMP) and layer (Application/Transport/Network/Data Link).
**Validates: Requirements 7.8**

Property 28: Optimization triggers on congestion
*For any* detected congestion (packet loss > threshold OR latency increase > threshold), the Optimization Module should trigger an adaptation action (route change OR flow control adjustment).
**Validates: Requirements 8.2, 8.3, 8.4**

Property 29: Optimization decision logging
*For any* optimization action taken, there should be a log entry containing the timestamp, triggering condition, metric values, and action taken.
**Validates: Requirements 8.5**

Property 30: Metric-driven optimization
*For any* optimization triggered, the triggering condition should be based on actual measured metric values exceeding configured thresholds.
**Validates: Requirements 8.6**

Property 31: Performance measurement around optimization
*For any* optimization action, performance metrics should be captured both before and after the optimization to measure effectiveness.
**Validates: Requirements 8.7**

Property 32: Dashboard update responsiveness
*For any* change in network conditions (topology change, metric change > 10%), the dashboard should reflect the change within 2 seconds.
**Validates: Requirements 9.4**

Property 33: Traffic generation parameter accuracy
*For any* controlled traffic generation with specified parameters (rate, size, pattern), the actual generated traffic should match the specified parameters within 5% tolerance.
**Validates: Requirements 10.2**

Property 34: Protocol behavior logging completeness
*For any* network condition scenario, protocol behavior (state transitions, retransmissions, route changes) should be logged with sufficient detail for post-analysis.
**Validates: Requirements 10.3**

Property 35: Log export format validity
*For any* exported performance log, the format should be valid structured data (JSON/CSV) that can be parsed without errors.
**Validates: Requirements 10.5**

Property 36: Experiment reproducibility
*For any* experiment run with a fixed random seed and identical configuration, running the experiment again should produce identical results (same packet losses, same timings, same routes).
**Validates: Requirements 10.7**

Property 37: Performance comparison report generation
*For any* completed experiment, a summary report should be generated containing performance metrics for all tested configurations and their comparisons.
**Validates: Requirements 10.8**

Property 38: Configuration validation on startup
*For any* invalid configuration (missing required fields, out-of-range values, conflicting settings), the emulator should detect the error during startup and report a clear error message before attempting to run.
**Validates: Requirements 11.5, 11.7**

## Error Handling

### Layer-Specific Error Handling

**Application Layer:**
- Connection failures: Retry with exponential backoff, report to user after max attempts
- File not found: Return clear error message, do not attempt transfer
- Invalid destination: Validate before attempting connection, return error immediately
- Timeout on receive: Configurable timeout, clean up resources on expiration

**Transport Layer:**
- Packet loss: Detected via timeout, trigger retransmission per protocol (GBN/SR)
- Out-of-order packets: Buffer in SR, discard in GBN
- Duplicate ACKs: Interpret as potential loss signal, may trigger fast retransmit
- Window exhaustion: Block sender until ACKs received, prevent overflow
- Checksum mismatch: Discard packet, rely on timeout for retransmission

**Network Layer:**
- No route to destination: Return ICMP-like "destination unreachable" to sender
- Routing loop detection: TTL field decremented, packet dropped when TTL=0
- Invalid IP address: Validate format, return error before attempting routing
- Routing table inconsistency: Periodic refresh, use default route if specific route unavailable

**Data Link Layer:**
- CRC failure: Discard frame, signal loss to upper layer
- Uncorrectable error: Discard frame after Hamming correction fails
- Frame too large: Fragment or return error to Network Layer
- Buffer overflow: Drop incoming frames, signal congestion

**MAC Layer:**
- Collision: Abort transmission, execute exponential backoff, retry
- Max retries exceeded: Report failure to Data Link Layer
- Channel busy timeout: Wait with backoff, eventually report failure

**Physical Layer:**
- Transmission failure: Simulate loss, report to MAC Layer
- Configuration error: Validate parameters, return error on invalid values

### Error Recovery Strategies

**Timeout-based Recovery:**
- Each layer maintains appropriate timeouts
- Transport Layer: Retransmission timeout (RTO) calculated from RTT
- Application Layer: Connection timeout for setup/teardown
- Exponential backoff on repeated failures

**Redundancy-based Recovery:**
- Error correction codes (Hamming) for single-bit errors
- Retransmission for lost packets
- Alternative routes for failed links

**Graceful Degradation:**
- System continues operating with reduced functionality
- UDP continues even with high loss
- Routing adapts to link failures
- Dashboard shows degraded state

### Error Logging

All errors logged with:
- Timestamp
- Layer where error occurred
- Error type and description
- Context (packet ID, connection ID, etc.)
- Recovery action taken

Logs exported for analysis and debugging.

## Security Considerations

While this emulator is designed for educational purposes and local operation, basic security considerations are addressed:

**Scope of Security:**
- Focus on protocol behavior and performance analysis
- Security mechanisms kept minimal to avoid obscuring core networking concepts
- No production-grade security features (intentional design choice)

**Implemented Security Measures:**
- Input validation on all configuration parameters
- Bounds checking on buffer sizes to prevent overflow
- Sanitization of file paths to prevent directory traversal
- Rate limiting on packet generation to prevent resource exhaustion
- Isolation between simulated nodes (no cross-contamination of state)

**Excluded Security Features:**
- Encryption and authentication (not in scope)
- DDoS protection (educational context)
- Secure key management (not applicable)
- Network intrusion detection (beyond scope)

**Security Best Practices:**
- Run emulator with minimal privileges
- Validate all external inputs (configuration files, user commands)
- Log security-relevant events (invalid inputs, resource limits)
- Clear documentation of security limitations

## Scalability and Performance

**Current Limitations:**
- Designed for 2-20 nodes (educational scale)
- Single-machine execution (no distributed simulation)
- Python implementation (not optimized for high performance)
- Event-driven architecture has O(n log n) complexity for event queue

**Scalability Considerations:**
- Modular design allows future optimization of bottleneck components
- Clear interfaces enable replacement of components with faster implementations
- Configuration limits prevent resource exhaustion
- Graceful degradation under high load

**Performance Optimization Strategies:**
- Use efficient data structures (heaps for event queue, hash tables for routing)
- Minimize copying of packet data (use references where possible)
- Batch processing of events when appropriate
- Configurable simulation speed (faster than real-time for experiments)

**Resource Management:**
- Configurable buffer sizes at each layer
- Automatic cleanup of completed connections
- Memory limits on packet capture
- Disk space management for logs

## Extensibility and Modularity

**Design for Extension:**
- Plugin architecture for new protocols
- Abstract base classes for each layer
- Factory patterns for protocol selection
- Configuration-driven behavior

**Extension Points:**

*Adding New Transport Protocols:*
```python
class CustomProtocol(TransportProtocol):
    def send_segment(self, data: bytes, dest: str) -> None:
        # Custom implementation
        pass
    
    def handle_acknowledgment(self, ack: Acknowledgment) -> None:
        # Custom implementation
        pass
```

*Adding New Routing Algorithms:*
```python
class CustomRouter(RoutingAlgorithm):
    def compute_routes(self, topology: NetworkTopology) -> dict:
        # Custom implementation
        return routing_table
```

*Adding New Error Correction Codes:*
```python
class CustomECC(ErrorCorrectionCode):
    def encode(self, data: bytes) -> bytes:
        # Custom implementation
        pass
    
    def decode(self, data: bytes) -> tuple[bool, bytes]:
        # Custom implementation
        return (success, corrected_data)
```

**Modularity Benefits:**
- Independent development and testing of components
- Easy replacement of implementations
- Clear separation of concerns
- Reusable components across projects

**Future Extensions:**
- Additional transport protocols (QUIC, SCTP)
- More routing algorithms (OSPF, BGP simulation)
- Advanced error correction (Reed-Solomon, Turbo codes)
- Quality of Service (QoS) mechanisms
- IPv6 support
- Wireless channel simulation
- Mobile node support

## Logging and Debugging

**Logging Architecture:**
- Hierarchical logging (per-layer, per-node, system-wide)
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging with JSON format for machine parsing
- Separate log files for different components

**Log Categories:**

*Protocol Logs:*
- Packet send/receive events
- State transitions
- Retransmissions and timeouts
- Routing updates

*Performance Logs:*
- Throughput measurements
- Latency samples
- Packet loss events
- Queue depths

*Error Logs:*
- CRC failures
- Routing failures
- Configuration errors
- Resource exhaustion

*Optimization Logs:*
- Triggering conditions
- Actions taken
- Performance before/after
- Justifications

**Log Format:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "component": "transport_layer",
  "node": "node_1",
  "event": "packet_sent",
  "details": {
    "packet_id": "pkt_12345",
    "sequence": 42,
    "destination": "node_2",
    "size": 1500
  }
}
```

**Debugging Features:**
- Packet trace visualization
- State inspection at any simulation time
- Breakpoints on specific events
- Step-through simulation mode
- Replay capability from logs

**Debug Mode:**
- Verbose logging of all events
- Packet content dumps
- State snapshots at each step
- Performance profiling
- Memory usage tracking

## Simulation Controls

**Execution Modes:**

*Real-Time Mode:*
- Simulation runs at wall-clock speed
- Useful for live demonstration
- Dashboard updates in real-time

*Fast-Forward Mode:*
- Simulation runs faster than real-time
- Useful for long experiments
- Configurable speed multiplier (2x, 10x, 100x)

*Step Mode:*
- Manual advancement of simulation
- Process one event at a time
- Useful for debugging

*Batch Mode:*
- Non-interactive execution
- Run predefined experiments
- Generate reports automatically

**Simulation Control API:**
```python
class SimulationController:
    def start() -> None
    def pause() -> None
    def resume() -> None
    def stop() -> None
    def step() -> None  # Advance one event
    def set_speed(multiplier: float) -> None
    def seek(timestamp: float) -> None  # Jump to time
    def reset() -> None  # Reset to initial state
```

**Time Management:**
- Discrete event simulation (not continuous)
- Virtual time independent of wall-clock time
- Precise event ordering
- Configurable time resolution (microseconds)

**Experiment Management:**
- Save/load simulation state
- Checkpoint at intervals
- Reproducible experiments with seeds
- Batch experiment execution
- Parameter sweeps

## API and Integration

**REST API for External Integration:**

*Endpoints:*
```
GET  /api/status              # Simulation status
POST /api/start               # Start simulation
POST /api/stop                # Stop simulation
GET  /api/metrics             # Current metrics
GET  /api/topology            # Network topology
POST /api/topology            # Update topology
GET  /api/nodes/{id}          # Node details
POST /api/traffic             # Generate traffic
GET  /api/logs                # Retrieve logs
POST /api/config              # Update configuration
```

*Example Usage:*
```python
import requests

# Start simulation
response = requests.post('http://localhost:5000/api/start')

# Get current metrics
metrics = requests.get('http://localhost:5000/api/metrics').json()
print(f"Throughput: {metrics['throughput']} Mbps")

# Generate traffic
traffic_config = {
    "source": "node_1",
    "destination": "node_2",
    "rate": "10Mbps",
    "duration": 60
}
requests.post('http://localhost:5000/api/traffic', json=traffic_config)
```

**Python API for Programmatic Control:**
```python
from network_emulator import Emulator, Config

# Create emulator
config = Config.from_file('config.yaml')
emulator = Emulator(config)

# Set up topology
emulator.add_node('node_1', ip='192.168.1.1')
emulator.add_node('node_2', ip='192.168.1.2')
emulator.add_link('node_1', 'node_2', cost=10)

# Start simulation
emulator.start()

# Generate traffic
emulator.send_file('node_1', 'node_2', 'test.dat', protocol='tcp')

# Monitor metrics
metrics = emulator.get_metrics()
print(f"Latency: {metrics.latency} ms")

# Stop simulation
emulator.stop()
```

**Integration with External Tools:**
- Wireshark/PyShark for packet capture
- Matplotlib/Plotly for visualization
- Pandas for data analysis
- Jupyter notebooks for interactive exploration
- Export to CSV/JSON for external analysis

## User Guidance and Documentation

**Documentation Structure:**

*User Guide:*
- Installation instructions
- Quick start tutorial
- Configuration reference
- Common use cases
- Troubleshooting guide

*Developer Guide:*
- Architecture overview
- Component descriptions
- API reference
- Extension guide
- Contributing guidelines

*Tutorial Examples:*
- Basic file transfer
- Comparing GBN vs SR
- Testing routing algorithms
- Analyzing optimization effects
- Custom protocol implementation

**Configuration Guide:**

*Configuration File Format (YAML):*
```yaml
emulator:
  num_nodes: 5
  topology: mesh
  
network:
  routing_algorithm: dijkstra
  ip_subnet: 192.168.1.0/24
  
transport:
  protocol: gbn
  window_size: 8
  timeout_ms: 100
  
physical:
  bit_rate: 100Mbps
  propagation_delay: 10ms
  loss_rate: 0.01
  error_rate: 0.0001
  
optimization:
  enabled: true
  loss_threshold: 0.05
  latency_threshold: 100ms
  
monitoring:
  capture_packets: true
  dashboard_port: 5000
  log_level: INFO
  
experiments:
  random_seed: 42
  duration: 300s
```

**Example Workflows:**

*Workflow 1: Compare Transport Protocols*
1. Configure emulator with GBN protocol
2. Run file transfer experiment
3. Capture metrics
4. Reconfigure with SR protocol
5. Run same experiment
6. Compare results

*Workflow 2: Test Routing Under Failure*
1. Set up network topology
2. Start traffic generation
3. Monitor routing paths
4. Inject link failure
5. Observe rerouting
6. Analyze convergence time

*Workflow 3: Evaluate Optimization*
1. Run experiment with optimization disabled
2. Capture baseline metrics
3. Enable optimization
4. Run same experiment
5. Compare performance improvement
6. Analyze optimization decisions

**Error Messages and Troubleshooting:**
- Clear, actionable error messages
- Common error scenarios documented
- Diagnostic commands
- FAQ section
- Community support channels

## Non-Goals

To maintain focus and manage scope, the following are explicitly excluded:

**Not Implemented:**
- Hardware-level simulation (physical signal propagation, electromagnetic interference)
- Production-grade performance (optimized for clarity over speed)
- Large-scale Internet simulation (designed for 2-20 nodes)
- Real-time hardware interfacing (software-only simulation)
- Advanced security features (encryption, authentication, intrusion detection)
- Wireless-specific protocols (802.11 MAC, handoff, power management)
- Application-layer protocols beyond basic TCP/UDP (HTTP, FTP, SMTP)
- Network management protocols (SNMP, NetFlow)
- Quality of Service (QoS) mechanisms (traffic shaping, priority queuing)
- Distributed simulation across multiple machines

**Rationale:**
- Educational focus: Clarity and understandability over completeness
- Resource constraints: Limited development time and computational resources
- Scope management: Deep implementation of core concepts rather than shallow coverage of everything
- Maintainability: Simpler codebase is easier to understand and extend

**Future Considerations:**
- These features could be added as extensions
- Modular design allows incremental addition
- Community contributions welcome for specific features

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit testing and property-based testing as complementary approaches:

**Unit Tests:** Validate specific examples, edge cases, and error conditions
- Test specific protocol scenarios (e.g., "GBN with window size 4 and packet 2 lost")
- Test edge cases (e.g., "empty file transfer", "single-node network")
- Test error conditions (e.g., "invalid IP address format", "CRC with all bits flipped")
- Test integration points between layers
- Verify specific configuration scenarios

**Property-Based Tests:** Validate universal properties across all inputs
- Test properties that should hold for ANY valid input
- Use randomized input generation (random topologies, random packet sequences, random error patterns)
- Verify correctness properties defined in this document
- Each property test runs minimum 100 iterations
- Catch edge cases that humans might not think to test

**Together:** Provide comprehensive coverage where unit tests catch concrete bugs and property tests verify general correctness.

### Property-Based Testing Configuration

**Library Selection:** Use `hypothesis` for Python property-based testing
- Mature, well-documented library
- Excellent integration with pytest
- Powerful strategies for generating complex data structures
- Built-in shrinking to find minimal failing examples

**Test Configuration:**
- Minimum 100 iterations per property test (configurable via `@settings(max_examples=100)`)
- Each test tagged with comment referencing design property
- Tag format: `# Feature: adaptive-network-emulator, Property N: [property text]`
- Tests organized by layer/component

**Property Test Structure:**
```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    data=st.binary(min_size=1, max_size=1500),
    source=st.ip_addresses(v=4),
    dest=st.ip_addresses(v=4)
)
def test_layer_encapsulation_preserves_data(data, source, dest):
    """
    Feature: adaptive-network-emulator, Property 1: Layer encapsulation preserves data integrity
    
    For any data passed from an upper layer to a lower layer, the lower layer
    should add headers/trailers but preserve the original data unchanged.
    """
    # Test implementation
    pass
```

### Test Coverage by Component

**Application Layer Tests:**
- Unit: Specific file transfers, connection modes, error scenarios
- Property: File transfer round-trip (Property 2), connection lifecycle (Property 3)

**Transport Layer Tests:**
- Unit: Specific window sizes, specific loss patterns, timeout scenarios
- Property: GBN behavior (Property 4), SR behavior (Property 5), window constraint (Property 6), sequence numbers (Property 7), ACK handling (Property 8), congestion adaptation (Property 9)

**Network Layer Tests:**
- Unit: Specific topologies, specific routing scenarios
- Property: Dijkstra correctness (Property 10), DV convergence (Property 11), dynamic updates (Property 12), route selection (Property 13)

**Data Link Layer Tests:**
- Unit: Specific error patterns, specific frame sizes
- Property: Frame structure (Property 14), CRC round-trip (Property 15), Hamming correction (Property 16), error handling (Properties 17-18)

**MAC Layer Tests:**
- Unit: Specific collision scenarios, specific backoff values
- Property: Collision detection (Property 19), backoff algorithm (Property 20), carrier sense (Property 21)

**Traffic Analyzer Tests:**
- Unit: Specific packet sequences, specific time windows
- Property: Metric calculations (Properties 22-26), categorization (Property 27)

**Optimization Module Tests:**
- Unit: Specific congestion scenarios, specific threshold values
- Property: Optimization triggers (Property 28), logging (Property 29), metric-driven (Property 30), performance measurement (Property 31)

**Dashboard Tests:**
- Unit: Specific UI elements, specific data formats
- Property: Update responsiveness (Property 32)

**System Integration Tests:**
- Unit: Specific end-to-end scenarios, specific configurations
- Property: Traffic generation (Property 33), logging (Property 34), export format (Property 35), reproducibility (Property 36), reports (Property 37), configuration validation (Property 38)

### Test Data Generation Strategies

**Hypothesis Strategies:**
- `st.binary()`: Random byte sequences for payloads
- `st.integers()`: Sequence numbers, window sizes, port numbers
- `st.ip_addresses()`: IP addresses for routing tests
- `st.lists()`: Packet sequences, node lists
- `st.floats()`: Link costs, loss rates, delays
- Custom strategies: Network topologies, packet sequences with specific properties

**Example Custom Strategy:**
```python
@st.composite
def network_topology(draw):
    """Generate random network topology."""
    num_nodes = draw(st.integers(min_value=2, max_value=10))
    nodes = [f"node_{i}" for i in range(num_nodes)]
    
    # Generate random links
    links = []
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            if draw(st.booleans()):  # Random connectivity
                cost = draw(st.floats(min_value=1.0, max_value=100.0))
                links.append(Link(nodes[i], nodes[j], cost))
    
    return NetworkTopology(nodes, links)
```

### Integration Testing

**Layer Integration:**
- Test data flow through multiple layers
- Verify encapsulation/decapsulation at boundaries
- Test error propagation between layers

**End-to-End Testing:**
- Complete file transfer through all layers
- Routing with dynamic topology changes
- Optimization under various traffic patterns

**Performance Testing:**
- Measure throughput under various conditions
- Measure latency distribution
- Stress test with high packet rates
- Test with various error rates

### Test Execution

**Continuous Testing:**
- Run unit tests on every code change
- Run property tests before commits
- Full test suite in CI/CD pipeline

**Test Organization:**
```
tests/
├── unit/
│   ├── test_application_layer.py
│   ├── test_transport_layer.py
│   ├── test_network_layer.py
│   ├── test_data_link_layer.py
│   ├── test_mac_layer.py
│   └── test_physical_layer.py
├── property/
│   ├── test_properties_transport.py
│   ├── test_properties_network.py
│   ├── test_properties_data_link.py
│   └── test_properties_system.py
├── integration/
│   ├── test_layer_integration.py
│   └── test_end_to_end.py
└── conftest.py  # Shared fixtures and strategies
```

**Test Reporting:**
- Coverage reports (aim for >80% line coverage)
- Property test statistics (iterations, failures, shrinking)
- Performance benchmarks
- Failed test artifacts (packet captures, logs)

### Validation Against Requirements

Each correctness property explicitly references the requirements it validates, ensuring traceability from requirements through design to tests. This enables:
- Verification that all testable requirements have corresponding tests
- Impact analysis when requirements change
- Clear documentation of what each test validates
- Confidence that implementation meets specifications
