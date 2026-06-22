# Adaptive Network Emulator - Project Structure

## Complete Folder Structure

```
PROJECT/
├── .git/                           # Git repository
├── .hypothesis/                    # Hypothesis test data
├── .kiro/                          # Kiro specs
│   └── specs/
│       └── adaptive-network-emulator/
│           ├── .config.kiro
│           ├── requirements.md     # Requirements document
│           ├── design.md          # Design document
│           └── tasks.md           # Implementation tasks
├── .pytest_cache/                 # Pytest cache
├── config/                        # Configuration files
│   ├── default.yaml
│   ├── dev.yaml
│   ├── prod.yaml
│   └── test.yaml
├── docs/                          # Documentation
│   └── task1_completion.md
├── logs/                          # Log files (empty)
├── src/                           # Source code (see detailed list below)
├── tests/                         # Test files (see detailed list below)
├── .coverage                      # Coverage report
├── .gitignore                     # Git ignore file
├── pytest.ini                     # Pytest configuration
├── README.md                      # Project README
└── requirements.txt               # Python dependencies
```

## Source Files (src/)

### Core Layer Implementations
1. **`__init__.py`** - Package initialization
2. **`application_layer.py`** - Application Layer (TCP/UDP sockets, file transfer)
3. **`transport_layer.py`** - Transport Layer base (SlidingWindow)
4. **`gbn_protocol.py`** - Go-Back-N protocol implementation
5. **`sr_protocol.py`** - Selective Repeat protocol implementation
6. **`network_layer.py`** - Network Layer (IP addressing, routing)
7. **`data_link_layer.py`** - Data Link Layer (framing, CRC, Hamming)
8. **`mac_layer.py`** - MAC Layer (CSMA/CD simulation)
9. **`physical_layer.py`** - Physical Layer (abstract transmission)

### Supporting Components
10. **`node.py`** - Node class (complete protocol stack integration) ⭐ NEW
11. **`network_topology.py`** - Network topology management ⭐ NEW
12. **`data_models.py`** - Data structures (Packet, Segment, Frame, etc.)
13. **`routing_table.py`** - Routing table management
14. **`dijkstra_router.py`** - Dijkstra routing algorithm
15. **`distance_vector_router.py`** - Distance Vector routing algorithm
16. **`icmp_simulator.py`** - ICMP-like diagnostics
17. **`flow_controller.py`** - Flow control mechanism
18. **`congestion_detector.py`** - Congestion detection and adaptation
19. **`file_transfer_service.py`** - File transfer service
20. **`event_queue.py`** - Event queue for simulation
21. **`config.py`** - Configuration management
22. **`logging_config.py`** - Logging configuration
23. **`utils.py`** - Utility functions

## Test Files (tests/)

### Unit Tests
1. **`conftest.py`** - Pytest fixtures and configuration
2. **`test_infrastructure.py`** - Infrastructure tests
3. **`test_data_models.py`** - Data model tests
4. **`test_utils.py`** - Utility function tests
5. **`test_application_layer.py`** - Application layer tests
6. **`test_physical_layer.py`** - Physical layer tests
7. **`test_mac_layer.py`** - MAC layer tests
8. **`test_data_link_layer.py`** - Data link layer tests
9. **`test_network_layer.py`** - Network layer tests
10. **`test_routing_table.py`** - Routing table tests
11. **`test_dijkstra_router.py`** - Dijkstra router tests
12. **`test_distance_vector_router.py`** - Distance vector router tests
13. **`test_icmp_simulator.py`** - ICMP simulator tests

### Property-Based Tests (PBT)
14. **`test_properties_data_serialization.py`** - Data serialization properties
15. **`test_properties_application.py`** - Application layer properties
16. **`test_properties_sliding_window.py`** - Sliding window properties
17. **`test_properties_gbn.py`** - Go-Back-N properties
18. **`test_properties_sr.py`** - Selective Repeat properties
19. **`test_properties_congestion.py`** - Congestion control properties
20. **`test_properties_network_layer.py`** - Network layer properties
21. **`test_properties_distance_vector.py`** - Distance vector properties
22. **`test_properties_data_link.py`** - Data link layer properties
23. **`test_properties_mac_layer.py`** - MAC layer properties
24. **`test_properties_layer_integration.py`** - Layer integration properties ⭐ NEW

### Integration Tests
25. **`test_error_handling_mechanisms.py`** - Error handling integration
26. **`test_integration_frame_transmission.py`** - Frame transmission integration
27. **`test_packet_forwarding_simple.py`** - Simple packet forwarding
28. **`test_packet_forwarding_integration.py`** - Packet forwarding integration
29. **`test_routing_verification.py`** - Routing verification
30. **`test_transport_protocol_behavior.py`** - Transport protocol behavior
31. **`test_transport_reliable_delivery.py`** - Reliable delivery tests
32. **`test_integration_layer_communication.py`** - End-to-end communication ⭐ NEW

## Task 18 Completion Summary

### Files Created/Modified for Task 18:
1. **`src/node.py`** (NEW) - 600+ lines
   - Complete protocol stack integration
   - Encapsulation/decapsulation at each layer
   - Layer-to-layer communication interfaces
   - Node management and statistics

2. **`src/network_topology.py`** (NEW) - 400+ lines
   - Network topology management
   - Topology builders (mesh, star, ring)
   - Node and link management
   - Adjacency tracking

3. **`tests/test_properties_layer_integration.py`** (NEW) - 350+ lines
   - Property 1: Layer encapsulation preserves data integrity
   - 3 property-based tests with 100 examples each
   - Tests data preservation through all layers

4. **`tests/test_integration_layer_communication.py`** (NEW) - 500+ lines
   - 13 integration tests
   - End-to-end communication tests
   - Various network conditions (loss, errors)
   - All topology types

### Test Results:
- ✅ All 16 tests passing (3 PBT + 13 integration)
- ✅ Property tests: 100 examples each
- ✅ Integration tests: All scenarios covered

## Next Steps for Task 19

Task 19 is a checkpoint to ensure the complete protocol stack works:

### Task 19 Subtasks:
- **19.1** Run all integration tests
- **19.2** Verify end-to-end file transfer
- **19.3** Test with various network conditions
- **19.4** Verify layer interactions
- **19.5** Review and ask user

### Key Files to Focus On:
- `src/node.py` - Main integration point
- `src/network_topology.py` - Topology management
- All integration test files in `tests/`
- Property test files for validation

### Current Status:
- ✅ Tasks 1-18 completed
- ✅ All layers implemented and tested
- ✅ Layer integration complete
- ✅ End-to-end communication working
- 🔄 Ready for Task 19 checkpoint

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_integration_layer_communication.py -v

# Run property tests
python -m pytest tests/test_properties_layer_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Key Architecture Components

### Node Class (src/node.py)
- Integrates all 6 protocol layers
- Handles encapsulation (downward flow)
- Handles decapsulation (upward flow)
- Provides high-level send/receive interface

### NetworkTopology Class (src/network_topology.py)
- Manages multiple nodes
- Creates common topology patterns
- Handles node-to-node communication
- Tracks adjacency for routing

### Layer Flow
```
Application Layer
    ↓ (encapsulation)
Transport Layer (GBN/SR)
    ↓
Network Layer (IP + Routing)
    ↓
Data Link Layer (Framing + CRC + Hamming)
    ↓
MAC Layer (CSMA/CD)
    ↓
Physical Layer (Abstract transmission)
```

## Dependencies (requirements.txt)

```
pytest>=7.0
hypothesis>=6.0
Flask>=2.0
pyshark>=0.5
pyyaml>=6.0
numpy>=1.20
```

## Configuration Files

- `config/default.yaml` - Default configuration
- `config/dev.yaml` - Development configuration
- `config/prod.yaml` - Production configuration
- `config/test.yaml` - Test configuration
- `pytest.ini` - Pytest settings

## Documentation

- `README.md` - Project overview
- `docs/task1_completion.md` - Task 1 documentation
- `.kiro/specs/adaptive-network-emulator/requirements.md` - Requirements
- `.kiro/specs/adaptive-network-emulator/design.md` - Design document
- `.kiro/specs/adaptive-network-emulator/tasks.md` - Task list

---

**Last Updated**: Task 18 completed
**Next Task**: Task 19 - Checkpoint: Ensure complete protocol stack works
