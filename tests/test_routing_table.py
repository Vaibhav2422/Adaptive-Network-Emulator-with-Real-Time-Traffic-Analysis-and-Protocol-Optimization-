"""
Unit tests for the RoutingTable class.

Tests routing table operations, serialization, and logging functionality.

Validates: Requirements 4.6
"""

import pytest
import json
import time
from src.routing_table import RoutingTable
from src.data_models import RouteEntry


class TestRoutingTableInitialization:
    """Test RoutingTable initialization."""
    
    def test_initialization(self):
        """Test basic initialization."""
        rt = RoutingTable("node1")
        assert rt.node_id == "node1"
        assert rt.size() == 0
        assert len(rt.get_all()) == 0


class TestRoutingTableOperations:
    """Test basic routing table operations."""
    
    def test_add_route(self):
        """Test adding a route."""
        rt = RoutingTable("node1")
        route = RouteEntry(
            destination="192.168.2.0/24",
            next_hop="192.168.1.254",
            cost=1.0,
            interface="eth0",
            timestamp=time.time(),
            metric_type="hop_count"
        )
        
        rt.add(route)
        assert rt.size() == 1
        assert rt.get("192.168.2.0/24") is not None
        assert rt.get("192.168.2.0/24").next_hop == "192.168.1.254"
    
    def test_add_multiple_routes(self):
        """Test adding multiple routes."""
        rt = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
            RouteEntry("10.0.0.0/8", "192.168.1.1", 5.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            rt.add(route)
        
        assert rt.size() == 3
    
    def test_update_route(self):
        """Test updating an existing route."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        # Update cost and next_hop
        success = rt.update("192.168.2.0/24", cost=0.5, next_hop="192.168.1.253")
        assert success is True
        
        updated_route = rt.get("192.168.2.0/24")
        assert updated_route.cost == 0.5
        assert updated_route.next_hop == "192.168.1.253"
    
    def test_update_nonexistent_route(self):
        """Test updating a route that doesn't exist."""
        rt = RoutingTable("node1")
        success = rt.update("192.168.2.0/24", cost=0.5)
        assert success is False
    
    def test_remove_route(self):
        """Test removing a route."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        assert rt.size() == 1
        success = rt.remove("192.168.2.0/24")
        assert success is True
        assert rt.size() == 0
        assert rt.get("192.168.2.0/24") is None
    
    def test_remove_nonexistent_route(self):
        """Test removing a route that doesn't exist."""
        rt = RoutingTable("node1")
        success = rt.remove("192.168.2.0/24")
        assert success is False
    
    def test_get_route(self):
        """Test getting a specific route."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        retrieved = rt.get("192.168.2.0/24")
        assert retrieved is not None
        assert retrieved.destination == "192.168.2.0/24"
        assert retrieved.next_hop == "192.168.1.254"
    
    def test_get_nonexistent_route(self):
        """Test getting a route that doesn't exist."""
        rt = RoutingTable("node1")
        retrieved = rt.get("192.168.2.0/24")
        assert retrieved is None
    
    def test_get_all_routes(self):
        """Test getting all routes."""
        rt = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            rt.add(route)
        
        all_routes = rt.get_all()
        assert len(all_routes) == 2
        assert "192.168.2.0/24" in all_routes
        assert "192.168.3.0/24" in all_routes
        
        # Verify it's a copy
        all_routes.clear()
        assert rt.size() == 2
    
    def test_clear_routes(self):
        """Test clearing all routes."""
        rt = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            rt.add(route)
        
        assert rt.size() == 2
        rt.clear()
        assert rt.size() == 0


class TestRoutingTableLookup:
    """Test routing table lookup operations."""
    
    def test_lookup_exact_match(self):
        """Test lookup with exact destination match."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.5", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        next_hop = rt.lookup("192.168.2.5")
        assert next_hop == "192.168.1.254"
    
    def test_lookup_subnet_match(self):
        """Test lookup with subnet-based routing."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        next_hop = rt.lookup("192.168.2.50")
        assert next_hop == "192.168.1.254"
        
        next_hop = rt.lookup("192.168.2.100")
        assert next_hop == "192.168.1.254"
    
    def test_lookup_longest_prefix_match(self):
        """Test longest prefix matching for overlapping routes."""
        rt = RoutingTable("node1")
        
        # Add overlapping routes
        route1 = RouteEntry("192.168.0.0/16", "192.168.1.254", 2.0, "eth0", time.time(), "hop_count")
        route2 = RouteEntry("192.168.2.0/24", "192.168.1.253", 1.0, "eth1", time.time(), "hop_count")
        
        rt.add(route1)
        rt.add(route2)
        
        # Should use more specific route (longer prefix)
        next_hop = rt.lookup("192.168.2.50")
        assert next_hop == "192.168.1.253"
        
        # Should use less specific route
        next_hop = rt.lookup("192.168.3.50")
        assert next_hop == "192.168.1.254"
    
    def test_lookup_default_route(self):
        """Test default route (0.0.0.0/0) as fallback."""
        rt = RoutingTable("node1")
        default_route = RouteEntry("0.0.0.0/0", "192.168.1.254", 10.0, "eth0", time.time(), "hop_count")
        rt.add(default_route)
        
        # Any destination without specific route should use default
        next_hop = rt.lookup("8.8.8.8")
        assert next_hop == "192.168.1.254"
        
        next_hop = rt.lookup("1.2.3.4")
        assert next_hop == "192.168.1.254"
    
    def test_lookup_no_route(self):
        """Test lookup when no route exists."""
        rt = RoutingTable("node1")
        next_hop = rt.lookup("10.0.0.1")
        assert next_hop is None
    
    def test_lookup_invalid_destination(self):
        """Test lookup with invalid destination."""
        rt = RoutingTable("node1")
        next_hop = rt.lookup("invalid.ip")
        assert next_hop is None


class TestRoutingTableSerialization:
    """Test routing table serialization and deserialization."""
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        rt = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            rt.add(route)
        
        data = rt.to_dict()
        assert data["node_id"] == "node1"
        assert "routes" in data
        assert len(data["routes"]) == 2
        assert "192.168.2.0/24" in data["routes"]
        assert "192.168.3.0/24" in data["routes"]
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "node_id": "node1",
            "routes": {
                "192.168.2.0/24": {
                    "destination": "192.168.2.0/24",
                    "next_hop": "192.168.1.254",
                    "cost": 1.0,
                    "interface": "eth0",
                    "timestamp": time.time(),
                    "metric_type": "hop_count"
                }
            }
        }
        
        rt = RoutingTable.from_dict(data)
        assert rt.node_id == "node1"
        assert rt.size() == 1
        assert rt.get("192.168.2.0/24") is not None
        assert rt.get("192.168.2.0/24").next_hop == "192.168.1.254"
    
    def test_to_json(self):
        """Test serialization to JSON."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        json_str = rt.to_json()
        assert isinstance(json_str, str)
        
        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["node_id"] == "node1"
        assert "routes" in data
    
    def test_to_json_with_indent(self):
        """Test serialization to JSON with pretty printing."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        json_str = rt.to_json(indent=2)
        assert isinstance(json_str, str)
        assert "\n" in json_str  # Should have newlines for pretty printing
    
    def test_from_json(self):
        """Test deserialization from JSON."""
        json_str = json.dumps({
            "node_id": "node1",
            "routes": {
                "192.168.2.0/24": {
                    "destination": "192.168.2.0/24",
                    "next_hop": "192.168.1.254",
                    "cost": 1.0,
                    "interface": "eth0",
                    "timestamp": time.time(),
                    "metric_type": "hop_count"
                }
            }
        })
        
        rt = RoutingTable.from_json(json_str)
        assert rt.node_id == "node1"
        assert rt.size() == 1
        assert rt.get("192.168.2.0/24") is not None
    
    def test_serialization_round_trip(self):
        """Test that serialization and deserialization preserve data."""
        rt1 = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", 1234567890.0, "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth1", 1234567891.0, "latency"),
        ]
        
        for route in routes:
            rt1.add(route)
        
        # Serialize to JSON and back
        json_str = rt1.to_json()
        rt2 = RoutingTable.from_json(json_str)
        
        # Verify data is preserved
        assert rt2.node_id == rt1.node_id
        assert rt2.size() == rt1.size()
        
        for dest in rt1.get_all().keys():
            route1 = rt1.get(dest)
            route2 = rt2.get(dest)
            assert route2 is not None
            assert route2.destination == route1.destination
            assert route2.next_hop == route1.next_hop
            assert route2.cost == route1.cost
            assert route2.interface == route1.interface
            assert route2.timestamp == route1.timestamp
            assert route2.metric_type == route1.metric_type


class TestRoutingTableLogging:
    """Test routing table logging functionality."""
    
    def test_to_log_format_empty(self):
        """Test log format for empty routing table."""
        rt = RoutingTable("node1")
        log_lines = rt.to_log_format()
        
        assert len(log_lines) == 1
        assert "empty" in log_lines[0].lower()
    
    def test_to_log_format_with_routes(self):
        """Test log format with routes."""
        rt = RoutingTable("node1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth1", time.time(), "latency"),
        ]
        
        for route in routes:
            rt.add(route)
        
        log_lines = rt.to_log_format()
        
        # Should have header, column headers, separator, and route lines
        assert len(log_lines) >= 4
        assert "node1" in log_lines[0]
        assert "2 routes" in log_lines[0]
    
    def test_str_representation(self):
        """Test string representation."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        str_repr = str(rt)
        assert isinstance(str_repr, str)
        assert "node1" in str_repr
        assert "192.168.2.0/24" in str_repr
    
    def test_repr_representation(self):
        """Test developer-friendly representation."""
        rt = RoutingTable("node1")
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        rt.add(route)
        
        repr_str = repr(rt)
        assert isinstance(repr_str, str)
        assert "RoutingTable" in repr_str
        assert "node1" in repr_str
        assert "routes=1" in repr_str
