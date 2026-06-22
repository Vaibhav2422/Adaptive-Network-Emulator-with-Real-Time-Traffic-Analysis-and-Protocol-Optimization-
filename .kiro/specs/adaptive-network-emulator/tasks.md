# Implementation Plan: Adaptive Network Emulator

## Overview

This implementation plan breaks down the Adaptive Network Emulator into discrete, incremental coding tasks. The approach follows a bottom-up strategy, implementing foundational layers first, then building upward through the protocol stack, and finally integrating monitoring and optimization capabilities. Each task builds on previous work, ensuring continuous integration and early validation of core functionality.

The implementation uses Python 3.8+ with standard libraries and well-established packages (hypothesis for property testing, Flask for the dashboard, PyShark for packet capture). Tasks are organized to enable parallel development where possible while maintaining clear dependencies.

### Implementation Strategy

**Bottom-Up Approach:** Physical → MAC → Data Link → Network → Transport → Application → Monitoring → Optimization

**Parallel Development Opportunities:**
- Tasks 1 (Infrastructure) and 2 (Data Models) can be done in parallel
- Tasks 3-5 (Lower layers) can proceed while Task 2 is being completed
- Dashboard frontend (22.3) can start once metrics API (22.2) provides minimal outputs
- Documentation (26) can be written incrementally alongside implementation

**Testing Philosophy:**
- Property-based tests use minimum 100 iterations for statistical confidence and reproducibility
- Each layer is tested independently before integration
- Integration tests validate end-to-end behavior
- Stress tests validate performance under high load

**Reproducibility:**
- All random operations use configurable seeds (specified in config)
- Experiments with identical seeds and configurations produce identical results
- Package versions pinned in requirements.txt for environment reproducibility

## Tasks

- [x] 1. Project setup and core infrastructure
  - [x] 1.1 Create project structure and environment
    - Create directory structure: src/, tests/, config/, logs/, docs/
    - Set up Python virtual environment (Python 3.8+)
    - Create requirements.txt with pinned versions: pytest>=7.0, hypothesis>=6.0, Flask>=2.0, pyshark>=0.5, pyyaml>=6.0, numpy>=1.20
    - Initialize git repository with .gitignore
    - _Requirements: 11.1, 11.6_
    - _Can be done in parallel with Task 2_

  - [x] 1.2 Configure testing framework
    - Install and configure pytest
    - Install and configure hypothesis plugin
    - Set hypothesis profile: 100 iterations minimum for property tests
    - Create pytest.ini with test discovery settings
    - _Requirements: 11.6_

  - [x] 1.3 Implement configuration system
    - Create YAML-based config loader with schema validation
    - Support environment-specific configs (dev, test, prod)
    - Implement config validation on load
    - Create default config template with all parameters documented
    - _Requirements: 11.2, 11.3_

  - [x] 1.4 Implement logging infrastructure
    - Set up structured JSON logging with rotation policy (max 100MB per file, keep 10 files)
    - Create hierarchical loggers: system, per-layer, per-node
    - Implement log level configuration (DEBUG, INFO, WARNING, ERROR)
    - Add timestamp, thread ID, and context to all log entries
    - _Requirements: 11.3_

  - [x] 1.5 Implement event queue system
    - Create discrete event simulation engine
    - Implement priority queue for event scheduling
    - Support event types: packet_arrival, timer_expiration, ack_receipt
    - Add event tracing for debugging
    - Implement simulation clock with configurable speed (real-time, fast-forward)
    - _Requirements: 11.1_

- [x] 2. Data models and common utilities
  - [x] 2.1 Define core data structures
    - Implement Packet, Segment, Frame dataclasses
    - Implement RouteEntry, Link, NetworkTopology dataclasses
    - Implement NetworkMetrics, EmulatorConfig dataclasses
    - Create serialization/deserialization methods for all data structures
    - _Requirements: 11.3_

  - [x] 2.2 Write property test for data serialization
    - **Property: Serialization round-trip**
    - **Validates: Requirements 11.3**
    - For any valid data structure, serializing then deserializing should produce an equivalent object

  - [x] 2.3 Implement utility functions
    - Checksum calculation utilities
    - Bit manipulation helpers
    - Time management for simulation
    - Random number generation with seed support
    - _Requirements: 10.7_

- [x] 3. Physical Layer implementation
  - [x] 3.1 Implement abstract transmission channel
    - Create PhysicalLayer class with configurable delay and loss
    - Implement transmission delay calculation (size / bit_rate)
    - Implement propagation delay simulation
    - Implement random packet loss based on configured rate
    - Create bit error injection mechanism
    - _Requirements: 6.4_

  - [x] 3.2 Write unit tests for Physical Layer
    - Test delay calculations
    - Test loss simulation with various rates
    - Test bit error injection
    - _Requirements: 6.4_

- [x] 4. MAC Layer implementation
  - [x] 4.1 Implement CSMA/CD simulation
    - Create MACLayer class with channel state management
    - Implement carrier sensing logic
    - Implement collision detection for simultaneous transmissions
    - Implement exponential backoff algorithm
    - Track transmission attempts and enforce max retry limit
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

  - [x] 4.2 Write property test for collision detection
    - **Property 19: Collision detection on simultaneous transmission**
    - **Validates: Requirements 6.2**
    - For any scenario where two or more nodes attempt transmission simultaneously, collision should be detected

  - [x] 4.3 Write property test for exponential backoff
    - **Property 20: Exponential backoff after collision**
    - **Validates: Requirements 6.3**
    - For any collision, backoff time should be in [0, 2^min(k,10) - 1] slots

  - [x] 4.4 Write property test for carrier sense
    - **Property 21: Carrier sense before transmission**
    - **Validates: Requirements 6.6**
    - For any transmission attempt, carrier sensing should occur first

- [x] 5. Data Link Layer implementation
  - [x] 5.1 Implement frame construction and CRC
    - Create DataLinkLayer class with frame builder
    - Implement frame structure (preamble, header, payload, CRC, trailer)
    - Implement CRC-32 calculation and verification
    - Create frame validation logic
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [x] 5.2 Write property test for frame structure
    - **Property 14: Frame structure completeness**
    - **Validates: Requirements 5.1**
    - For any payload, resulting frame should contain valid header, payload, and trailer with CRC

  - [x] 5.3 Write property test for CRC round-trip
    - **Property 15: CRC error detection round-trip**
    - **Validates: Requirements 5.4, 5.5**
    - For any frame with valid CRC, verification should pass; with errors, should detect

  - [x] 5.4 Implement Hamming Code error correction
    - Implement Hamming code encoder
    - Implement Hamming code decoder with single-bit correction
    - Integrate error correction into frame processing
    - Create error injection mechanism for testing
    - _Requirements: 5.3, 5.6, 5.7, 5.8, 5.9_

  - [x] 5.5 Write property test for Hamming correction
    - **Property 16: Hamming code single-bit correction**
    - **Validates: Requirements 5.6**
    - For any data with exactly one bit flipped, Hamming decoder should correct it

  - [x] 5.6 Write property test for error correction success
    - **Property 17: Error correction success delivers original data**
    - **Validates: Requirements 5.8**
    - For any frame with correctable errors, delivered data should match original

  - [x] 5.7 Write property test for uncorrectable error handling
    - **Property 18: Uncorrectable error handling**
    - **Validates: Requirements 5.9**
    - For any frame with uncorrectable errors, should discard and signal loss

- [x] 6. Checkpoint - Ensure lower layers work correctly
  - [x] 6.1 Run all lower layer tests
    - Execute all Physical Layer tests (pass rate: 100%)
    - Execute all MAC Layer tests (pass rate: 100%)
    - Execute all Data Link Layer tests (pass rate: 100%)
    - Verify test coverage >80% for these layers
    - _Expected: All unit and property tests passing_

  - [x] 6.2 Integration test: Frame transmission through layers
    - Test frame transmission: Application data → Physical Layer → back up
    - Verify headers added/removed correctly at each layer
    - Test with various payload sizes (1 byte, 1KB, 64KB)
    - _Expected: Data integrity preserved, headers correct_

  - [x] 6.3 Test error handling mechanisms
    - Test CRC detection with injected bit errors (detection rate >99%)
    - Test Hamming correction with single-bit errors (correction rate 100%)
    - Test collision detection with simultaneous transmissions
    - Test exponential backoff behavior
    - _Expected: Error detection/correction working as specified_

  - [x] 6.4 Review and ask user
    - Review test results and logs
    - Ask user if any questions or concerns before proceeding to Network Layer
    - _Milestone: Lower layers complete and validated_

- [x] 7. Network Layer - IP addressing and packet forwarding
  - [x] 7.1 Implement IP addressing and subnetting
    - Create NetworkLayer class with IP address management
    - Implement IP address assignment and validation
    - Implement subnet calculation and membership checking
    - Create packet forwarding logic
    - _Requirements: 4.1_

  - [x] 7.2 Implement routing table management
    - Create RoutingTable class with add/update/lookup operations
    - Implement next-hop lookup
    - Implement routing table serialization for logging
    - _Requirements: 4.6_

  - [x] 7.3 Write unit tests for IP addressing
    - Test IP address validation
    - Test subnet calculations
    - Test routing table operations
    - _Requirements: 4.1, 4.6_

- [x] 8. Network Layer - Dijkstra routing algorithm
  - [x] 8.1 Implement Dijkstra link-state routing
    - Create DijkstraRouter class
    - Implement shortest path computation using Dijkstra's algorithm
    - Implement link-state database management
    - Implement routing table generation from shortest paths
    - _Requirements: 4.2, 4.8_

  - [x] 8.2 Write property test for Dijkstra correctness
    - **Property 10: Dijkstra shortest path correctness**
    - **Validates: Requirements 4.2, 4.8**
    - For any topology, computed paths should have minimal total cost

- [x] 9. Network Layer - Distance Vector routing algorithm
  - [x] 9.1 Implement Distance Vector routing
    - Create DistanceVectorRouter class
    - Implement Bellman-Ford algorithm
    - Implement distance vector exchange with neighbors
    - Implement routing table updates based on received vectors
    - Handle routing loops with split horizon
    - _Requirements: 4.3_

  - [x] 9.2 Write property test for Distance Vector convergence
    - **Property 11: Distance Vector convergence**
    - **Validates: Requirements 4.3**
    - For any stable topology, DV should converge to consistent routing

- [x] 10. Network Layer - Dynamic routing and optimization
  - [x] 10.1 Implement dynamic routing updates
    - Create mechanism to detect topology changes
    - Implement routing table update triggers
    - Add timestamp tracking for routing entries
    - Implement route invalidation on link failure
    - _Requirements: 4.4_

  - [x] 10.2 Write property test for dynamic routing
    - **Property 12: Dynamic routing update**
    - **Validates: Requirements 4.4**
    - For any topology change, routing tables should update within bounded time

  - [x] 10.3 Implement traffic-aware route selection
    - Add link utilization and latency tracking
    - Implement route selection based on current conditions
    - Create mechanism to adjust link costs dynamically
    - _Requirements: 4.5_

  - [x] 10.4 Write property test for route selection
    - **Property 13: Route selection optimality**
    - **Validates: Requirements 4.5**
    - For any routing decision with multiple paths, selected path should have better metrics

  - [x] 10.5 Implement ICMP-like diagnostics
    - Create ICMPSimulator class
    - Implement echo request/reply (ping-like)
    - Implement destination unreachable messages
    - Implement TTL expiration handling
    - _Requirements: 4.7_

- [x] 11. Checkpoint - Ensure Network Layer works correctly
  - [x] 11.1 Run all Network Layer tests
    - Execute all IP addressing tests (pass rate: 100%)
    - Execute all routing algorithm tests (pass rate: 100%)
    - Execute all dynamic routing tests (pass rate: 100%)
    - Verify test coverage >80% for Network Layer
    - _Expected: All tests passing, routing tables correct_

  - [x] 11.2 Verify routing correctness
    - Test Dijkstra on sample topology: verify shortest paths computed
    - Test Distance Vector convergence: verify routing tables consistent
    - Test dynamic updates: verify routes update within 5 seconds of topology change
    - _Expected: Routing tables match expected values for test topologies_

  - [x] 11.3 Test packet forwarding
    - Test packet forwarding through multi-hop network (3+ hops)
    - Verify packets reach correct destinations
    - Test with various network topologies (mesh, star, ring)
    - _Expected: Packet delivery rate >95% in stable network_

  - [x] 11.4 Review and ask user
    - Review routing behavior and test results
    - Ask user if any questions or concerns before proceeding to Transport Layer
    - _Milestone: Network Layer complete with working routing_

- [x] 12. Transport Layer - Core sliding window mechanism
  - [x] 12.1 Implement sliding window foundation
    - Create SlidingWindow class with configurable size
    - Implement window state management (base, next_seq)
    - Implement sequence number generation and validation
    - Create acknowledgment tracking
    - _Requirements: 3.5, 3.7_

  - [x] 12.2 Write property test for window constraint
    - **Property 6: Sliding window constraint**
    - **Validates: Requirements 3.5**
    - For any protocol, unacknowledged packets should never exceed window size

  - [x] 12.3 Write property test for sequence number monotonicity
    - **Property 7: Sequence number monotonicity**
    - **Validates: Requirements 3.7**
    - For any packet sequence, sequence numbers should be monotonically increasing

- [x] 13. Transport Layer - Go-Back-N protocol
  - [x] 13.1 Implement GBN protocol
    - Create GBNProtocol class extending TransportProtocol base
    - Implement send logic with window management
    - Implement timeout and retransmission from lost packet onward
    - Implement cumulative acknowledgment handling
    - Implement receiver logic (accept only in-order packets)
    - _Requirements: 3.1, 3.3, 3.8_

  - [x] 13.2 Write property test for GBN retransmission
    - **Property 4: GBN retransmission behavior**
    - **Validates: Requirements 3.3**
    - For any sequence with packet N lost, all packets from N onward should be retransmitted

  - [x] 13.3 Write property test for window advancement
    - **Property 8: Window advancement on ACK**
    - **Validates: Requirements 3.8**
    - For any ACK received, window should slide forward appropriately

- [x] 14. Transport Layer - Selective Repeat protocol
  - [x] 14.1 Implement SR protocol
    - Create SRProtocol class extending TransportProtocol base
    - Implement send logic with individual packet tracking
    - Implement selective retransmission of lost packets only
    - Implement selective acknowledgment handling
    - Implement receiver buffering for out-of-order packets
    - _Requirements: 3.2, 3.4_

  - [x] 14.2 Write property test for SR selective retransmission
    - **Property 5: SR selective retransmission**
    - **Validates: Requirements 3.4**
    - For any sequence with packet N lost, only packet N should be retransmitted

- [x] 15. Transport Layer - Flow and congestion control
  - [x] 15.1 Implement flow control
    - Create FlowController class
    - Implement receiver window advertisement
    - Implement sender window adjustment based on receiver capacity
    - Add flow control to both GBN and SR
    - _Requirements: 3.5_

  - [x] 15.2 Implement congestion detection and adaptation
    - Create CongestionDetector class
    - Implement packet loss rate monitoring
    - Implement latency increase detection
    - Implement window size reduction on congestion
    - Implement gradual window increase on improvement
    - Implement timeout adjustment based on RTT
    - _Requirements: 3.6_

  - [x] 15.3 Write property test for congestion adaptation
    - **Property 9: Congestion adaptation**
    - **Validates: Requirements 3.6**
    - For any detection of loss or delay above threshold, transport should adapt parameters

- [x] 16. Checkpoint - Ensure Transport Layer works correctly
  - [x] 16.1 Run all Transport Layer tests
    - Execute all sliding window tests (pass rate: 100%)
    - Execute all GBN protocol tests (pass rate: 100%)
    - Execute all SR protocol tests (pass rate: 100%)
    - Execute all flow/congestion control tests (pass rate: 100%)
    - Verify test coverage >80% for Transport Layer
    - _Expected: All tests passing, protocols behaving correctly_

  - [x] 16.2 Verify protocol behavior
    - Test GBN retransmission: verify all packets from N onward retransmitted
    - Test SR selective retransmission: verify only lost packet retransmitted
    - Test window constraint: verify unacked packets never exceed window size
    - Test congestion adaptation: verify window reduces on packet loss
    - _Expected: Protocol behavior matches specification_

  - [x] 16.3 Test reliable delivery
    - Test reliable delivery with 10% packet loss (delivery rate: 100%)
    - Test reliable delivery with 50ms latency variation
    - Test with various window sizes (1, 4, 16, 64)
    - _Expected: All data delivered correctly despite network issues_

  - [x] 16.4 Review and ask user
    - Review transport protocol behavior and test results
    - Ask user if any questions or concerns before proceeding to Application Layer
    - _Milestone: Transport Layer complete with reliable delivery_

- [x] 17. Application Layer implementation
  - [x] 17.1 Implement socket handlers
    - Create ApplicationLayer class
    - Implement TCPSocketHandler for reliable communication
    - Implement UDPSocketHandler for unreliable communication
    - Implement connection establishment and teardown
    - Support both client-server and peer-to-peer modes
    - _Requirements: 2.1, 2.4, 2.6_

  - [x] 17.2 Write property test for connection lifecycle
    - **Property 3: Connection lifecycle cleanup**
    - **Validates: Requirements 2.6**
    - For any connection, setup then teardown should leave clean state

  - [x] 17.3 Implement message and file transfer services
    - Create MessageService for text message transmission
    - Create FileTransferService for file operations
    - Implement file segmentation for large files
    - Implement file integrity verification (checksums)
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

  - [x] 17.4 Write property test for TCP file transfer
    - **Property 2: TCP file transfer round-trip**
    - **Validates: Requirements 2.2, 2.5**
    - For any file transferred via TCP, received file should match sent file exactly

- [x] 18. Layer integration and end-to-end communication
  - [x] 18.1 Implement layer interfaces and data flow
    - Create clear interfaces between all layers
    - Implement encapsulation (adding headers) at each layer
    - Implement decapsulation (removing headers) at each layer
    - Wire all layers together in Node class
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [x] 18.2 Write property test for layer encapsulation
    - **Property 1: Layer encapsulation preserves data integrity**
    - **Validates: Requirements 1.2, 1.4**
    - For any data through layers, original data should be preserved unchanged

  - [x] 18.3 Create Node class and network topology
    - Implement Node class containing complete protocol stack
    - Create NetworkTopology class for managing nodes and links
    - Implement node-to-node communication
    - Create topology builder for common patterns (mesh, star, ring)
    - _Requirements: 1.1, 11.2_

  - [x] 18.4 Write integration tests for end-to-end communication
    - Test message transmission through all layers
    - Test file transfer through all layers
    - Test with various error rates and loss rates
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 19. Checkpoint - Ensure complete protocol stack works
  - [x] 19.1 Run all integration tests
    - Execute all end-to-end communication tests (pass rate: 100%)
    - Execute all layer integration tests (pass rate: 100%)
    - Verify complete test suite passes (unit + property + integration)
    - Verify overall test coverage >80%
    - _Expected: Full protocol stack working end-to-end_

  - [x] 19.2 Verify end-to-end file transfer
    - Test file transfer (1MB file) through all layers with 0% loss (success rate: 100%)
    - Test file transfer with 10% packet loss (success rate: 100%, retransmissions occur)
    - Test file transfer with 50ms latency (success, slower completion)
    - Verify file integrity: received file matches sent file byte-for-byte
    - _Expected: Files transferred correctly under various conditions_

  - [x] 19.3 Test with various network conditions
    - Test with high packet loss (20-30%): verify reliable delivery still works
    - Test with high latency (100-200ms): verify timeouts adjusted correctly
    - Test with bit errors: verify error correction/detection works
    - Test with network topology changes during transfer
    - _Expected: System adapts to conditions, maintains correctness_

  - [x] 19.4 Verify layer interactions
    - Verify data encapsulation/decapsulation at each layer
    - Verify headers added/removed correctly
    - Verify no data corruption through layers
    - Check for resource leaks (memory, file handles)
    - _Expected: Clean layer separation, no leaks_

  - [x] 19.5 Review and ask user
    - Review end-to-end behavior and test results
    - Ask user if any questions or concerns before proceeding to monitoring/optimization
    - _Milestone: Complete protocol stack validated and working_

- [ ] 20. Traffic Analyzer - Packet capture and basic metrics
  - [ ] 20.1 Implement packet capture with PyShark
    - Create TrafficAnalyzer class with start/stop capture methods
    - Integrate PyShark for packet capture on loopback interface
    - Implement packet filtering for emulator traffic (use custom markers in headers)
    - Parse packet headers at each layer (extract layer-specific info)
    - Extract timing information from packets (send time, receive time)
    - Handle PyShark exceptions and connection errors gracefully
    - _Requirements: 7.1_

  - [ ] 20.2 Implement core metrics calculation
    - Create MetricsCalculator class
    - Implement throughput calculation: (total bytes successfully delivered) / (time interval)
    - Implement latency measurement: (receive timestamp - send timestamp)
    - Implement packet loss calculation: (packets lost / packets sent) × 100
    - Implement retransmission counting: track and count retransmitted packets
    - Implement jitter calculation: variance in packet delay
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

  - [ ] 20.3 Write property tests for metrics calculations
    - **Property 22: Throughput calculation accuracy**
    - **Validates: Requirements 7.2**
    - For any sequence of packets, throughput = bytes / time
    - **Property 23: Latency measurement accuracy**
    - **Validates: Requirements 7.3**
    - For any packet, latency = receive_time - send_time
    - **Property 24: Packet loss calculation accuracy**
    - **Validates: Requirements 7.4**
    - For any session, loss = (lost / sent) × 100
    - **Property 25: Retransmission counting accuracy**
    - **Validates: Requirements 7.5**
    - For any session, retransmission count = actual retransmissions
    - _Note: 100 iterations per property for statistical confidence_
    done 
- [ ] 21. Traffic Analyzer - Statistics and logging
  - [ ] 21.1 Implement statistics collection
    - Create StatisticsCollector for aggregating metrics over time windows
    - Implement rolling window statistics (last 1s, 10s, 60s, 5min)
    - Calculate mean, median, 95th percentile for latency
    - Track protocol distribution (TCP/UDP/ICMP percentages)
    - Track per-layer processing times
    - _Requirements: 7.6, 7.8_

  - [ ] 21.2 Implement metric logging and categorization
    - Create PerformanceLogger for exporting metrics to files
    - Implement metric logging with timestamps (ISO 8601 format)
    - Implement packet categorization by protocol type (TCP/UDP/ICMP)
    - Implement packet categorization by layer (Application/Transport/Network/Data Link)
    - Create structured log format (JSON) for easy parsing
    - _Requirements: 7.6, 7.8_

  - [ ] 21.3 Write property tests for logging and categorization
    - **Property 26: Metric timestamp association**
    - **Validates: Requirements 7.6**
    - For any metric, it should have an associated timestamp
    - **Property 27: Packet categorization correctness**
    - **Validates: Requirements 7.8**
    - For any packet, it should be correctly categorized by protocol and layer

  - [ ] 21.4 Implement performance comparison engine
    - Create ComparisonEngine for before/after analysis
    - Implement baseline capture and storage (save to file)
    - Implement comparison metrics calculation (% improvement/degradation)
    - Generate comparison reports with statistical significance tests
    - Support multiple baseline comparisons
    - _Requirements: 7.7_
                                                                                done 
- [ ] 21. Optimization Module implementation
  - [ ] 21.1 Implement network condition monitoring
    - Create OptimizationModule class
    - Create ConditionMonitor for continuous monitoring
    - Implement metric threshold checking
    - Detect congestion, high loss, high latency
    - _Requirements: 8.1, 8.6_

  - [ ] 21.2 Write property test for metric-driven optimization
    - **Property 30: Metric-driven optimization**
    - **Validates: Requirements 8.6**
    - For any optimization, triggering should be based on actual metric values

  - [ ] 21.3 Implement optimization strategies

    - Create RouteOptimizer for adjusting routing paths
    - Create FlowOptimizer for adjusting flow control parameters
    - Implement congestion-triggered route changes
    - Implement loss-triggered window adjustments
    - Implement latency-triggered route selection
    - _Requirements: 8.2, 8.3, 8.4_

  - [ ] 21.4 Write property test for optimization triggers
    - **Property 28: Optimization triggers on congestion**
    - **Validates: Requirements 8.2, 8.3, 8.4**
    - For any detected congestion, optimization should trigger adaptation

  - [ ] 21.5 Implement optimization logging and measurement
    - Create DecisionLogger for logging optimization decisions
    - Log triggering conditions, metric values, and actions
    - Implement before/after performance measurement
    - Generate optimization effectiveness reports
    - _Requirements: 8.5, 8.7_

  - [ ] 21.6 Write property tests for optimization logging
    - **Property 29: Optimization decision logging**
    - **Validates: Requirements 8.5**
    - **Property 31: Performance measurement around optimization**
    - **Validates: Requirements 8.7**

  - [ ] 21.7 Implement adaptive behavior control
    - Add enable/disable flag for optimization
    - Support static vs adaptive mode comparison
    - _Requirements: 8.8_
                                                                                  DONE 
- [ ] 22. Monitoring Dashboard implementation
  - [ ] 22.1 Set up Flask web server and API
    - Create Dashboard class with Flask integration
    - Implement REST API endpoints for metrics, topology, control
    - Set up WebSocket or SSE for real-time updates
    - Implement CORS for development
    - _Requirements: 9.5_

  - [ ] 22.2 Implement dashboard backend logic
    - Create MetricsAPI for serving current metrics
    - Implement topology rendering data generation
    - Create alert management system
    - Implement historical data storage and retrieval
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7_

  - [ ] 22.3 Create dashboard frontend
    - Create HTML/CSS/JavaScript frontend
    - Implement real-time metric charts (Chart.js or Plotly)
    - Implement topology visualization with animated packet flow
    - Implement protocol state display
    - Implement optimization event highlighting
    - Display historical trends
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7_

  - [ ] 22.4 Write property test for dashboard responsiveness
    - **Property 32: Dashboard update responsiveness**
    - **Validates: Requirements 9.4**
    - For any network change, dashboard should update within 2 seconds
                                                                     ongoing  done
- [ ] 23. Simulation control and experiment management
  - [ ] 23.1 Implement simulation controller
    - Create SimulationController class
    - Implement start/pause/resume/stop controls
    - Implement step mode for debugging
    - Implement speed control (real-time, fast-forward)
    - Implement state save/load for checkpointing
    - _Requirements: 10.1, 10.7_

  - [ ] 23.2 Implement traffic generation
    - Create TrafficGenerator class
    - Implement configurable traffic patterns (constant, bursty, periodic)
    - Implement congestion level simulation
    - Support multiple simultaneous traffic flows
    - _Requirements: 10.1, 10.2_

  - [ ] 23.3 Write property test for traffic generation
    - **Property 33: Traffic generation parameter accuracy**
    - **Validates: Requirements 10.2**
    - For any traffic generation config, actual traffic should match parameters

  - [ ] 23.4 Implement experiment management
    - Create ExperimentManager class
    - Implement batch experiment execution
    - Implement parameter sweep support
    - Support reproducible experiments with random seeds
    - _Requirements: 10.4, 10.7_

  - [ ] 23.5 Write property test for reproducibility
    - **Property 36: Experiment reproducibility**
    - **Validates: Requirements 10.7**
    - For any experiment with fixed seed, results should be identical on re-run
                                                                                      DONE 
- [ ] 24. Logging, reporting, and data export
  - [ ] 24.1 Implement comprehensive logging system
    - Set up hierarchical logging (per-layer, per-node, system)
    - Implement structured JSON logging
    - Create separate log files for different components
    - Implement log level configuration
    - Log protocol behavior under various conditions
    - _Requirements: 10.3_

  - [ ] 24.2 Write property test for protocol behavior logging
    - **Property 34: Protocol behavior logging completeness**
    - **Validates: Requirements 10.3**
    - For any network condition, protocol behavior should be logged

  - [ ] 24.3 Implement data export functionality
    - Create export functions for CSV and JSON formats
    - Implement performance log export
    - Implement Wireshark packet trace capture
    - Validate export format correctness
    - _Requirements: 10.5, 10.6_

  - [ ] 24.4 Write property test for export format
    - **Property 35: Log export format validity**
    - **Validates: Requirements 10.5**
    - For any exported log, format should be valid and parseable

  - [ ] 24.5 Implement report generation
    - Create ReportGenerator class
    - Generate summary reports with performance comparisons
    - Include charts and visualizations in reports
    - Compare static vs adaptive performance
    - Generate protocol comparison reports
    - _Requirements: 10.8_

  - [ ] 24.6 Write property test for report generation
    - **Property 37: Performance comparison report generation**
    - **Validates: Requirements 10.8**
    - For any experiment, summary report should be generated with comparisons
                                                                                DONE 
- [ ] 25. Configuration and validation
  - [ ] 25.1 Implement configuration system
    - Create comprehensive YAML configuration schema
    - Implement configuration loader with validation
    - Support topology configuration
    - Support protocol parameter configuration
    - Support experiment configuration
    - _Requirements: 11.2, 11.3_

  - [ ] 25.2 Implement startup validation
    - Validate all configuration parameters on startup
    - Check for missing required fields
    - Check for out-of-range values
    - Check for conflicting settings
    - Report clear, actionable error messages
    - _Requirements: 11.5, 11.7_

  - [ ] 25.3 Write property test for configuration validation
    - **Property 38: Configuration validation on startup**
    - **Validates: Requirements 11.5, 11.7**
    - For any invalid config, emulator should detect and report clear error

- [ ] 26. Documentation and examples
  - [ ] 26.1 Write user documentation
    - Create installation guide
    - Write quick start tutorial
    - Document configuration options
    - Create troubleshooting guide
    - Document API reference
    - _Requirements: 11.4_

  - [ ] 26.2 Create example workflows
    - Example 1: Basic file transfer
    - Example 2: Comparing GBN vs SR
    - Example 3: Testing routing algorithms
    - Example 4: Analyzing optimization effects
    - Example 5: Custom protocol implementation
    - _Requirements: 10.4_

  - [ ] 26.3 Create architecture documentation
    - Document system architecture with diagrams
    - Document layer interactions
    - Document data flow
    - Document extension points
    - Document Physical Layer abstractions and limitations
    - _Requirements: 1.3, 11.4_
                                                                    DONE 
- [ ] 27. Final integration and system testing
  - [ ] 27.1 Run complete test suite
    - Execute all unit tests
    - Execute all property tests (minimum 100 iterations each)
    - Execute all integration tests
    - Verify test coverage (aim for >80%)
    - _Requirements: All_

  - [ ] 27.2 Perform end-to-end system testing
    - Test complete file transfer through all layers
    - Test routing algorithm comparison
    - Test optimization effectiveness
    - Test dashboard functionality
    - Test with various network conditions
    - _Requirements: All_

  - [ ] 27.3 Validate against requirements
    - Verify each requirement is implemented
    - Verify each correctness property is tested
    - Check requirements traceability
    - Generate requirements coverage report
    - _Requirements: All_
                                                          DONE 
- [x] 28. Final checkpoint - Project complete
  - All tests passing
  - Documentation complete
  - Examples working
  - Ready for demonstration and evaluation
  - Ask the user if questions arise

## Notes

- All tasks including property-based tests are required for complete implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties with minimum 100 iterations for statistical confidence
- Unit tests validate specific examples and edge cases
- The implementation follows a bottom-up approach: Physical → MAC → Data Link → Network → Transport → Application
- Monitoring and optimization are added after core protocol stack is complete
- Each layer is tested independently before integration
- Configuration and documentation are completed near the end but can be done in parallel
- Tasks 1 and 2 can be done in parallel for faster initial setup
- Dashboard frontend (22.3) can start once metrics API (22.2) provides minimal outputs
