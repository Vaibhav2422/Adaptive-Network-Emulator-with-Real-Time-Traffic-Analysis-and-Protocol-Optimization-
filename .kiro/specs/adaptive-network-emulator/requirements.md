# Requirements Document

## Introduction

The Adaptive Network Emulator is a software-based network simulation system that demonstrates end-to-end communication across multiple layers of the TCP/IP and OSI models. The system integrates protocol implementation, real-time traffic analysis, and adaptive optimization to provide an educational platform for understanding network behavior under various conditions. The emulator operates entirely in software on a local system, focusing on correct protocol behavior, metrics accuracy, and explainability.

## Glossary

- **Emulator**: The complete network simulation system
- **Application_Layer**: The topmost layer handling user-facing protocols (TCP/UDP sockets)
- **Transport_Layer**: Layer responsible for reliable data transfer (GBN, SR protocols)
- **Network_Layer**: Layer handling routing and IP addressing
- **Data_Link_Layer**: Layer responsible for framing, error detection, and correction
- **MAC_Layer**: Media Access Control layer handling channel access
- **Physical_Layer**: Abstracted layer representing physical transmission
- **Traffic_Analyzer**: Component that captures and analyzes network packets
- **Optimization_Module**: Component that adapts network parameters based on conditions
- **Dashboard**: Web-based interface for monitoring network metrics
- **GBN**: Go-Back-N reliable data transfer protocol
- **SR**: Selective Repeat reliable data transfer protocol
- **CRC**: Cyclic Redundancy Check for error detection
- **Hamming_Code**: Error correction code implementation
- **CSMA_CD**: Carrier Sense Multiple Access with Collision Detection
- **Routing_Algorithm**: Algorithm for determining packet paths (Dijkstra or Distance Vector)
- **Flow_Control**: Mechanism to manage data transmission rate
- **Congestion_Control**: Mechanism to adapt to network congestion
- **Packet**: Unit of data transmitted through the network
- **Frame**: Data unit at the Data Link Layer
- **Node**: A simulated network device in the emulator
- **Throughput**: Rate of successful data transmission
- **Latency**: Time delay in packet transmission
- **Packet_Loss**: Percentage of packets that fail to reach destination
- **Retransmission**: Re-sending of lost or corrupted packets

## Requirements

### Requirement 1: Layered Architecture

**User Story:** As a network engineer, I want a modular layered architecture, so that I can understand and modify individual protocol layers independently.

#### Acceptance Criteria

1. THE Emulator SHALL implement separate modules for Application_Layer, Transport_Layer, Network_Layer, Data_Link_Layer, MAC_Layer, and Physical_Layer
2. WHEN data flows between layers, THE Emulator SHALL pass data through well-defined interfaces with clear encapsulation and decapsulation
3. THE Emulator SHALL document the data flow path from Application_Layer to Physical_Layer and back
4. WHEN a layer processes data, THE Emulator SHALL add appropriate headers without modifying data from upper layers
5. THE Emulator SHALL maintain clear separation of concerns where each layer only interacts with adjacent layers

### Requirement 2: Application Layer Communication

**User Story:** As a user, I want to send text messages and transfer files using TCP and UDP protocols, so that I can test different application-level communication patterns.

#### Acceptance Criteria

1. WHEN using TCP sockets, THE Application_Layer SHALL support reliable text message transmission between client and server
2. WHEN using TCP sockets, THE Application_Layer SHALL support reliable file transfer with integrity verification
3. WHEN using UDP sockets, THE Application_Layer SHALL support file transfer without reliability guarantees
4. THE Application_Layer SHALL support both client-server and peer-to-peer communication modes
5. WHEN a file transfer completes, THE Application_Layer SHALL verify file integrity at the destination
6. WHEN establishing a connection, THE Application_Layer SHALL handle connection setup and teardown properly

### Requirement 3: Transport Layer Reliability

**User Story:** As a network researcher, I want to implement and compare Go-Back-N and Selective Repeat protocols, so that I can understand different reliability mechanisms.

#### Acceptance Criteria

1. THE Transport_Layer SHALL implement the Go-Back-N protocol with configurable window size
2. THE Transport_Layer SHALL implement the Selective Repeat protocol with configurable window size
3. WHEN a packet is lost, THE GBN protocol SHALL retransmit all packets from the lost packet onward
4. WHEN a packet is lost, THE SR protocol SHALL retransmit only the specific lost packet
5. THE Transport_Layer SHALL implement sliding window flow control for both GBN and SR
6. WHEN packet loss or delay is detected, THE Transport_Layer SHALL adapt transmission parameters
7. THE Transport_Layer SHALL maintain sequence numbers for packet ordering
8. WHEN receiving acknowledgments, THE Transport_Layer SHALL advance the window appropriately

### Requirement 4: Network Layer Routing

**User Story:** As a network administrator, I want dynamic routing with multiple algorithms, so that I can compare routing strategies under different network conditions.

#### Acceptance Criteria

1. THE Network_Layer SHALL implement IP addressing with subnet support
2. THE Network_Layer SHALL implement Dijkstra link-state routing algorithm
3. THE Network_Layer SHALL implement Distance Vector routing algorithm
4. WHEN network conditions change, THE Network_Layer SHALL dynamically update routing tables
5. WHEN selecting a route, THE Network_Layer SHALL choose paths based on current traffic conditions
6. THE Network_Layer SHALL maintain routing tables with next-hop information
7. THE Network_Layer SHALL support logical ICMP-like behavior for network diagnostics
8. WHEN a routing algorithm runs, THE Network_Layer SHALL compute shortest paths based on link costs

### Requirement 5: Data Link Layer Error Handling

**User Story:** As a protocol developer, I want error detection and correction mechanisms, so that I can simulate realistic data link behavior.

#### Acceptance Criteria

1. THE Data_Link_Layer SHALL implement frame construction with header and trailer
2. THE Data_Link_Layer SHALL implement CRC for error detection
3. THE Data_Link_Layer SHALL implement Hamming Code for error correction
4. WHEN creating a frame, THE Data_Link_Layer SHALL compute and append CRC checksum
5. WHEN receiving a frame, THE Data_Link_Layer SHALL verify CRC and detect errors
6. WHEN errors are detected, THE Data_Link_Layer SHALL attempt correction using Hamming Code
7. THE Data_Link_Layer SHALL support error injection for testing purposes
8. WHEN error correction succeeds, THE Data_Link_Layer SHALL deliver corrected data to Network_Layer
9. WHEN error correction fails, THE Data_Link_Layer SHALL discard the frame and signal packet loss

### Requirement 6: MAC and Physical Layer Abstraction

**User Story:** As a system designer, I want abstracted MAC and Physical layers, so that I can focus on higher-layer protocols while maintaining conceptual completeness.

#### Acceptance Criteria

1. THE MAC_Layer SHALL implement logical CSMA_CD channel access simulation
2. WHEN multiple nodes attempt transmission, THE MAC_Layer SHALL simulate collision detection
3. WHEN a collision occurs, THE MAC_Layer SHALL implement exponential backoff
4. THE Physical_Layer SHALL provide abstract transmission with configurable delay and loss parameters
5. THE Emulator SHALL document Physical_Layer assumptions and limitations
6. THE MAC_Layer SHALL simulate carrier sensing before transmission

### Requirement 7: Real-Time Traffic Analysis

**User Story:** As a network analyst, I want to capture and analyze live network traffic, so that I can measure performance metrics accurately.

#### Acceptance Criteria

1. THE Traffic_Analyzer SHALL capture packets using PyShark or Wireshark integration
2. WHEN packets are transmitted, THE Traffic_Analyzer SHALL measure throughput in real-time
3. WHEN packets are transmitted, THE Traffic_Analyzer SHALL measure end-to-end latency
4. THE Traffic_Analyzer SHALL calculate packet loss percentage
5. THE Traffic_Analyzer SHALL count retransmissions for reliability protocols
6. THE Traffic_Analyzer SHALL log all metrics with timestamps
7. THE Traffic_Analyzer SHALL support comparison of metrics before and after optimization
8. WHEN analyzing traffic, THE Traffic_Analyzer SHALL categorize packets by protocol and layer

### Requirement 8: Adaptive Optimization

**User Story:** As a network optimizer, I want automatic adaptation to network conditions, so that the system can improve performance dynamically.

#### Acceptance Criteria

1. THE Optimization_Module SHALL monitor network conditions continuously
2. WHEN congestion is detected, THE Optimization_Module SHALL adjust routing paths
3. WHEN packet loss exceeds a threshold, THE Optimization_Module SHALL modify flow control parameters
4. WHEN latency increases, THE Optimization_Module SHALL select alternative routes
5. THE Optimization_Module SHALL log all optimization decisions with justifications
6. THE Optimization_Module SHALL use measured metrics to trigger adaptations
7. WHEN optimization occurs, THE Optimization_Module SHALL measure performance improvement
8. THE Optimization_Module SHALL support enabling and disabling adaptive behavior for comparison

### Requirement 9: Monitoring Dashboard

**User Story:** As a system operator, I want a visual dashboard, so that I can monitor network state and metrics in real-time.

#### Acceptance Criteria

1. THE Dashboard SHALL display real-time throughput, latency, and packet loss metrics
2. THE Dashboard SHALL visualize active protocols and their states
3. THE Dashboard SHALL display current routing paths and topology
4. WHEN network conditions change, THE Dashboard SHALL update visualizations within 2 seconds
5. THE Dashboard SHALL provide a lightweight web interface using Flask or similar framework
6. THE Dashboard SHALL display historical metric trends over time
7. THE Dashboard SHALL highlight active optimizations and their effects

### Requirement 10: Evaluation and Testing

**User Story:** As a researcher, I want controlled traffic scenarios and performance logging, so that I can evaluate protocol behavior scientifically.

#### Acceptance Criteria

1. THE Emulator SHALL support generation of controlled traffic patterns with configurable parameters
2. WHEN generating traffic, THE Emulator SHALL simulate various congestion levels
3. THE Emulator SHALL log protocol behavior under different network conditions
4. THE Emulator SHALL support comparison between static and adaptive configurations
5. THE Emulator SHALL export performance logs in structured format for analysis
6. THE Emulator SHALL capture Wireshark packet traces for detailed inspection
7. WHEN running experiments, THE Emulator SHALL produce reproducible results with fixed random seeds
8. THE Emulator SHALL generate summary reports comparing protocol performance

### Requirement 11: System Configuration and Constraints

**User Story:** As a system administrator, I want clear configuration options and documented constraints, so that I can set up and operate the emulator correctly.

#### Acceptance Criteria

1. THE Emulator SHALL operate entirely on a local system without cloud dependencies
2. THE Emulator SHALL support configuration of network topology with limited number of nodes
3. THE Emulator SHALL provide configuration files for protocol parameters
4. THE Emulator SHALL document all Physical_Layer abstractions and limitations
5. WHEN starting, THE Emulator SHALL validate configuration and report errors clearly
6. THE Emulator SHALL support Python 3.8 or higher as the implementation language
7. THE Emulator SHALL provide clear error messages for configuration issues
