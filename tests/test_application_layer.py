"""
Unit tests for Application Layer.

Tests specific functionality and integration of application layer components.
"""
import pytest
import tempfile
import os
from src.application_layer import ApplicationLayer, ConnectionMode


def test_tcp_connection_establishment():
    """Test TCP connection establishment."""
    app_layer = ApplicationLayer(node_id="node1")
    
    # Establish connection
    connection_id = app_layer.establish_connection("node2", ConnectionMode.CLIENT_SERVER)
    
    assert connection_id is not None
    assert app_layer.get_connection_count() == 1
    
    # Close connection
    success = app_layer.close_connection(connection_id)
    assert success
    assert app_layer.get_connection_count() == 0


def test_message_sending():
    """Test text message sending."""
    app_layer = ApplicationLayer(node_id="node1")
    
    # Send TCP message
    success = app_layer.send_message("node2", "Hello, World!", protocol="TCP")
    assert success
    
    # Send UDP message
    success = app_layer.send_message("node2", "Hello via UDP!", protocol="UDP")
    assert success


def test_file_transfer_basic():
    """Test basic file transfer functionality."""
    # Create a temporary file
    test_data = b"This is test file content for transfer."
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(test_data)
        temp_file_path = temp_file.name
    
    try:
        app_layer = ApplicationLayer(node_id="node1")
        
        # Track sent data
        sent_data = []
        
        def mock_callback(dest, data, protocol, connection_id):
            sent_data.append(data)
        
        app_layer.transport_send_callback = mock_callback
        app_layer.tcp_handler.send_callback = mock_callback
        
        # Send file
        file_id = app_layer.send_file("node2", temp_file_path, protocol="TCP")
        
        assert file_id is not None
        assert len(sent_data) > 0
        
        # Simulate receiving the file
        receiver = ApplicationLayer(node_id="node2")
        for segment_data in sent_data:
            receiver.receive_file_segment(segment_data)
        
        # Get received file
        received_data = receiver.get_received_file(file_id)
        
        assert received_data == test_data
        
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_connection_cleanup():
    """Test connection cleanup."""
    app_layer = ApplicationLayer(node_id="node1")
    
    # Create multiple connections
    conn1 = app_layer.establish_connection("node2", ConnectionMode.CLIENT_SERVER)
    conn2 = app_layer.establish_connection("node3", ConnectionMode.PEER_TO_PEER)
    
    assert app_layer.get_connection_count() == 2
    
    # Clean up all connections
    app_layer.cleanup_all_connections()
    
    assert app_layer.get_connection_count() == 0


def test_peer_to_peer_mode():
    """Test peer-to-peer connection mode."""
    app_layer = ApplicationLayer(node_id="node1")
    
    # Establish P2P connection
    connection_id = app_layer.establish_connection("node2", ConnectionMode.PEER_TO_PEER)
    
    assert connection_id is not None
    
    conn = app_layer.tcp_handler.get_connection(connection_id)
    assert conn.mode == ConnectionMode.PEER_TO_PEER
    
    app_layer.close_connection(connection_id)


def test_multiple_file_transfers():
    """Test multiple concurrent file transfers."""
    # Create multiple temporary files
    files = []
    for i in range(3):
        test_data = f"File {i} content".encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
            temp_file.write(test_data)
            files.append((temp_file.name, test_data))
    
    try:
        app_layer = ApplicationLayer(node_id="node1")
        
        sent_segments = {}
        
        def mock_callback(dest, data, protocol, connection_id):
            if dest not in sent_segments:
                sent_segments[dest] = []
            sent_segments[dest].append(data)
        
        app_layer.transport_send_callback = mock_callback
        app_layer.tcp_handler.send_callback = mock_callback
        
        # Send all files
        file_ids = []
        for i, (file_path, _) in enumerate(files):
            file_id = app_layer.send_file(f"node{i+2}", file_path, protocol="TCP")
            assert file_id is not None
            file_ids.append(file_id)
        
        # Verify all files were sent
        assert len(file_ids) == 3
        
    finally:
        for file_path, _ in files:
            if os.path.exists(file_path):
                os.unlink(file_path)
