"""
Property-based tests for Application Layer.

Tests correctness properties related to connection lifecycle and data transfer.
"""
import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings
from src.application_layer import ApplicationLayer, ConnectionMode
from src.file_transfer_service import FileTransferService


# Feature: adaptive-network-emulator, Property 3: Connection lifecycle cleanup
@settings(max_examples=100)
@given(
    local_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    remote_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    mode=st.sampled_from([ConnectionMode.CLIENT_SERVER, ConnectionMode.PEER_TO_PEER])
)
def test_connection_lifecycle_cleanup(local_node, remote_node, mode):
    """
    Feature: adaptive-network-emulator, Property 3: Connection lifecycle cleanup
    
    For any connection, setup then teardown should leave clean state.
    
    Validates: Requirements 2.6
    """
    # Ensure nodes are different
    if local_node == remote_node:
        remote_node = remote_node + "_remote"
    
    # Create application layer
    app_layer = ApplicationLayer(node_id=local_node)
    
    # Record initial state
    initial_connection_count = app_layer.get_connection_count()
    initial_tcp_connections = len(app_layer.tcp_handler.connections)
    initial_tcp_buffers = len(app_layer.tcp_handler.receive_buffer)
    
    # Establish connection
    connection_id = app_layer.establish_connection(remote_node, mode)
    
    # Verify connection was established
    assert connection_id is not None, "Connection should be established"
    assert app_layer.get_connection_count() > initial_connection_count, \
        "Active connection count should increase"
    
    # Get connection details
    conn = app_layer.tcp_handler.get_connection(connection_id)
    assert conn is not None, "Connection should exist"
    assert conn.is_active(), "Connection should be active"
    assert conn.local_node == local_node, "Local node should match"
    assert conn.remote_node == remote_node, "Remote node should match"
    assert conn.mode == mode, "Connection mode should match"
    assert conn.protocol == "TCP", "Protocol should be TCP"
    
    # Close connection
    success = app_layer.close_connection(connection_id)
    assert success, "Connection should close successfully"
    
    # Verify clean state after teardown
    assert conn.is_closed(), "Connection should be closed"
    assert conn.closed_at is not None, "Closed timestamp should be set"
    
    # Verify receive buffer was cleaned up
    assert connection_id not in app_layer.tcp_handler.receive_buffer, \
        "Receive buffer should be cleaned up"
    
    # Verify no active connections remain
    assert app_layer.get_connection_count() == initial_connection_count, \
        "Active connection count should return to initial value"
    
    # Property: Setup then teardown leaves clean state
    # - No active connections
    # - No receive buffers
    # - Connection marked as closed
    assert len(app_layer.tcp_handler.get_active_connections()) == 0, \
        "No active connections should remain"


@settings(max_examples=100)
@given(
    local_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    remote_nodes=st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        min_size=1,
        max_size=5,
        unique=True
    )
)
def test_multiple_connections_cleanup(local_node, remote_nodes):
    """
    Feature: adaptive-network-emulator, Property 3: Connection lifecycle cleanup
    
    For any set of connections, establishing and closing all should leave clean state.
    
    Validates: Requirements 2.6
    """
    # Ensure remote nodes are different from local node
    remote_nodes = [node if node != local_node else node + "_remote" for node in remote_nodes]
    
    # Create application layer
    app_layer = ApplicationLayer(node_id=local_node)
    
    # Establish multiple connections
    connection_ids = []
    for remote_node in remote_nodes:
        connection_id = app_layer.establish_connection(remote_node, ConnectionMode.CLIENT_SERVER)
        assert connection_id is not None, f"Connection to {remote_node} should be established"
        connection_ids.append(connection_id)
    
    # Verify all connections are active
    assert app_layer.get_connection_count() == len(remote_nodes), \
        "All connections should be active"
    
    # Close all connections
    for connection_id in connection_ids:
        success = app_layer.close_connection(connection_id)
        assert success, f"Connection {connection_id} should close successfully"
    
    # Verify clean state
    assert app_layer.get_connection_count() == 0, \
        "No active connections should remain"
    assert len(app_layer.tcp_handler.get_active_connections()) == 0, \
        "No active TCP connections should remain"
    
    # Verify all receive buffers cleaned up
    for connection_id in connection_ids:
        assert connection_id not in app_layer.tcp_handler.receive_buffer, \
            f"Receive buffer for {connection_id} should be cleaned up"


@settings(max_examples=100)
@given(
    local_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    remote_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
)
def test_cleanup_all_connections(local_node, remote_node):
    """
    Feature: adaptive-network-emulator, Property 3: Connection lifecycle cleanup
    
    For any connections, cleanup_all_connections should leave clean state.
    
    Validates: Requirements 2.6
    """
    # Ensure nodes are different
    if local_node == remote_node:
        remote_node = remote_node + "_remote"
    
    # Create application layer
    app_layer = ApplicationLayer(node_id=local_node)
    
    # Establish some connections
    conn1 = app_layer.establish_connection(remote_node, ConnectionMode.CLIENT_SERVER)
    conn2 = app_layer.establish_connection(remote_node + "2", ConnectionMode.PEER_TO_PEER)
    
    assert conn1 is not None and conn2 is not None, "Connections should be established"
    assert app_layer.get_connection_count() > 0, "Should have active connections"
    
    # Send some UDP datagrams to create UDP state
    app_layer.udp_handler.send_datagram(remote_node, b"test data")
    
    # Clean up all connections
    app_layer.cleanup_all_connections()
    
    # Verify clean state
    assert app_layer.get_connection_count() == 0, \
        "No active TCP connections should remain"
    assert len(app_layer.tcp_handler.get_active_connections()) == 0, \
        "No active TCP connections should remain"
    assert len(app_layer.udp_handler.receive_buffer) == 0, \
        "UDP receive buffers should be cleared"
    assert len(app_layer.udp_handler.connections) == 0, \
        "UDP connections should be cleared"
    
    # Verify all TCP connections are closed
    for conn_id, conn in app_layer.tcp_handler.connections.items():
        assert conn.is_closed(), f"Connection {conn_id} should be closed"



# Feature: adaptive-network-emulator, Property 2: TCP file transfer round-trip
@settings(max_examples=100)
@given(
    file_data=st.binary(min_size=1, max_size=10000),
    local_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    remote_node=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
)
def test_tcp_file_transfer_round_trip(file_data, local_node, remote_node):
    """
    Feature: adaptive-network-emulator, Property 2: TCP file transfer round-trip
    
    For any file transferred via TCP, received file should match sent file exactly.
    
    Validates: Requirements 2.2, 2.5
    """
    # Ensure nodes are different
    if local_node == remote_node:
        remote_node = remote_node + "_remote"
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(file_data)
        temp_file_path = temp_file.name
    
    try:
        # Create file transfer service
        file_service = FileTransferService()
        
        # Track sent segments
        sent_segments = []
        
        def mock_send_callback(dest, data, protocol, file_id):
            """Mock callback to capture sent segments."""
            sent_segments.append(data)
        
        # Send file
        file_id = file_service.send_file(
            file_path=temp_file_path,
            dest_node=remote_node,
            protocol="TCP",
            send_callback=mock_send_callback
        )
        
        assert file_id is not None, "File transfer should be initiated"
        assert len(sent_segments) > 0, "Segments should be sent"
        
        # Simulate receiving segments
        receiver_service = FileTransferService()
        for segment_data in sent_segments:
            success = receiver_service.receive_segment(segment_data)
            assert success, "Segment should be received successfully"
        
        # Get received file
        received_data = receiver_service.get_received_file(file_id)
        
        # Property: Received file should match sent file exactly
        assert received_data is not None, "File should be received"
        assert received_data == file_data, \
            "Received file data should match original file data byte-for-byte"
        
        # Verify file integrity using checksum
        transfer_state = file_service.completed_transfers.get(file_id)
        assert transfer_state is not None, "Transfer state should exist"
        
        verified = receiver_service.verify_file_integrity(
            file_id, 
            transfer_state.file_checksum
        )
        assert verified, "File integrity should be verified"
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@settings(max_examples=100)
@given(
    file_data=st.binary(min_size=1, max_size=5000),
    segment_size=st.integers(min_value=100, max_value=2000)
)
def test_file_segmentation_and_reassembly(file_data, segment_size):
    """
    Feature: adaptive-network-emulator, Property 2: TCP file transfer round-trip
    
    For any file and segment size, segmentation and reassembly should preserve data.
    
    Validates: Requirements 2.2, 2.5
    """
    # Create file transfer service with custom segment size
    file_service = FileTransferService(segment_size=segment_size)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(file_data)
        temp_file_path = temp_file.name
    
    try:
        # Track sent segments
        sent_segments = []
        
        def mock_send_callback(dest, data, protocol, file_id):
            sent_segments.append(data)
        
        # Send file
        file_id = file_service.send_file(
            file_path=temp_file_path,
            dest_node="remote",
            protocol="TCP",
            send_callback=mock_send_callback
        )
        
        assert file_id is not None, "File transfer should be initiated"
        
        # Calculate expected number of segments
        expected_segments = (len(file_data) + segment_size - 1) // segment_size
        assert len(sent_segments) == expected_segments, \
            f"Should have {expected_segments} segments"
        
        # Receive segments in order
        receiver_service = FileTransferService()
        for segment_data in sent_segments:
            success = receiver_service.receive_segment(segment_data)
            assert success, "Segment should be received successfully"
        
        # Get received file
        received_data = receiver_service.get_received_file(file_id)
        
        # Property: Reassembled file should match original
        assert received_data == file_data, \
            "Reassembled file should match original file exactly"
        
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@settings(max_examples=100)
@given(
    file_data=st.binary(min_size=100, max_size=5000),
    segment_size=st.integers(min_value=100, max_value=1000)
)
def test_file_transfer_out_of_order_segments(file_data, segment_size):
    """
    Feature: adaptive-network-emulator, Property 2: TCP file transfer round-trip
    
    For any file, receiving segments out of order should still produce correct file.
    
    Validates: Requirements 2.2, 2.5
    """
    import random
    
    # Create file transfer service
    file_service = FileTransferService(segment_size=segment_size)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(file_data)
        temp_file_path = temp_file.name
    
    try:
        # Track sent segments
        sent_segments = []
        
        def mock_send_callback(dest, data, protocol, file_id):
            sent_segments.append(data)
        
        # Send file
        file_id = file_service.send_file(
            file_path=temp_file_path,
            dest_node="remote",
            protocol="TCP",
            send_callback=mock_send_callback
        )
        
        assert file_id is not None, "File transfer should be initiated"
        assert len(sent_segments) > 0, "Segments should be sent"
        
        # Shuffle segments to simulate out-of-order delivery
        shuffled_segments = sent_segments.copy()
        random.shuffle(shuffled_segments)
        
        # Receive segments out of order
        receiver_service = FileTransferService()
        for segment_data in shuffled_segments:
            success = receiver_service.receive_segment(segment_data)
            assert success, "Segment should be received successfully"
        
        # Get received file
        received_data = receiver_service.get_received_file(file_id)
        
        # Property: File should be correctly reassembled despite out-of-order delivery
        assert received_data == file_data, \
            "File should be correctly reassembled from out-of-order segments"
        
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@settings(max_examples=100)
@given(
    file_data=st.binary(min_size=1, max_size=5000)
)
def test_file_integrity_verification(file_data):
    """
    Feature: adaptive-network-emulator, Property 2: TCP file transfer round-trip
    
    For any file, integrity verification should detect corruption.
    
    Validates: Requirement 2.5
    """
    # Create file transfer service
    file_service = FileTransferService()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(file_data)
        temp_file_path = temp_file.name
    
    try:
        # Track sent segments
        sent_segments = []
        
        def mock_send_callback(dest, data, protocol, file_id):
            sent_segments.append(data)
        
        # Send file
        file_id = file_service.send_file(
            file_path=temp_file_path,
            dest_node="remote",
            protocol="TCP",
            send_callback=mock_send_callback
        )
        
        assert file_id is not None, "File transfer should be initiated"
        
        # Get original checksum
        transfer_state = file_service.completed_transfers.get(file_id)
        original_checksum = transfer_state.file_checksum
        
        # Receive all segments
        receiver_service = FileTransferService()
        for segment_data in sent_segments:
            receiver_service.receive_segment(segment_data)
        
        # Verify with correct checksum
        verified = receiver_service.verify_file_integrity(file_id, original_checksum)
        assert verified, "Integrity verification should pass with correct checksum"
        
        # Verify with incorrect checksum
        wrong_checksum = "0" * 64
        verified = receiver_service.verify_file_integrity(file_id, wrong_checksum)
        assert not verified, "Integrity verification should fail with incorrect checksum"
        
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
