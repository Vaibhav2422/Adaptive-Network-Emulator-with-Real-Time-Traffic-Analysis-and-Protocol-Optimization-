"""
Unit tests for the Network Layer implementation.

Tests IP address validation, subnet calculations, routing table operations,
and packet forwarding logic.

Validates: Requirements 4.1
"""

import pytest
import time
from src.network_layer import NetworkLayer
from src.data_models import Packet, RouteEntry


class TestNetworkLayerInitialization:
    """Test NetworkLayer initialization and IP address assignment."""
    
    def test_valid_initialization(self):
        """Test initialization with valid IP address and subnet mask."""
        nl = NetworkLayer("node1", "192.168.1.1", "255.255.255.0")
        assert nl.node_id == "node1"
        assert nl.ip_address == "192.168.1.1"
        assert nl.subnet_mask == "255.255.255.0"
        assert nl.routing_table.size() == 0
    
    def test_initialization_with_default_mask(self):
        """Test initialization with default subnet mask."""
        nl = NetworkLayer("node1", "10.0.0.1")
        assert nl.ip_address == "10.0.0.1"
        assert nl.subnet_mask == "255.255.255.0"
    
    def test_invalid_ip_address(self):
        """Test initialization with invalid IP address."""
        with pytest.raises(ValueError, match="Invalid IP address"):
            NetworkLayer("node1", "999.999.999.999")
        
        with pytest.raises(ValueError, match="Invalid IP address"):
            NetworkLayer("node1", "not.an.ip.address")
        
        with pytest.raises(ValueError, match="Invalid IP address"):
            NetworkLayer("node1", "192.168.1")
    
    def test_invalid_subnet_mask(self):
        """Test initialization with invalid subnet mask."""
        with pytest.raises(ValueError, match="Invalid subnet mask"):
            NetworkLayer("node1", "192.168.1.1", "999.999.999.999")
        
        with pytest.raises(ValueError, match="Invalid subnet mask"):
            NetworkLayer("node1", "192.168.1.1", "invalid.mask")


class TestIPAddressValidation:
    """Test IP address validation methods."""
    
    def test_validate_valid_addresses(self):
        """Test validation of valid IP addresses."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.validate_ip_address("192.168.1.1") is True
        assert nl.validate_ip_address("10.0.0.1") is True
        assert nl.validate_ip_address("172.16.0.1") is True
        assert nl.validate_ip_address("0.0.0.0") is True
        assert nl.validate_ip_address("255.255.255.255") is True
    
    def test_validate_invalid_addresses(self):
        """Test validation of invalid IP addresses."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.validate_ip_address("999.999.999.999") is False
        assert nl.validate_ip_address("not.an.ip") is False
        assert nl.validate_ip_address("192.168.1") is False
        assert nl.validate_ip_address("192.168.1.1.1") is False
        assert nl.validate_ip_address("") is False
    
    def test_assign_ip_address(self):
        """Test IP address assignment and update."""
        nl = NetworkLayer("node1", "192.168.1.1")
        assert nl.ip_address == "192.168.1.1"
        
        nl.assign_ip_address("10.0.0.1", "255.255.0.0")
        assert nl.ip_address == "10.0.0.1"
        assert nl.subnet_mask == "255.255.0.0"
    
    def test_assign_invalid_ip_address(self):
        """Test assigning invalid IP address."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        with pytest.raises(ValueError, match="Invalid IP address"):
            nl.assign_ip_address("999.999.999.999")


class TestSubnetCalculations:
    """Test subnet calculation methods."""
    
    def test_calculate_subnet_class_c(self):
        """Test subnet calculation for Class C network."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        network, broadcast, first_host, num_hosts = nl.calculate_subnet(
            "192.168.1.100", "255.255.255.0"
        )
        
        assert network == "192.168.1.0"
        assert broadcast == "192.168.1.255"
        assert first_host == "192.168.1.1"
        assert num_hosts == 254
    
    def test_calculate_subnet_class_b(self):
        """Test subnet calculation for Class B network."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        network, broadcast, first_host, num_hosts = nl.calculate_subnet(
            "172.16.50.100", "255.255.0.0"
        )
        
        assert network == "172.16.0.0"
        assert broadcast == "172.16.255.255"
        assert first_host == "172.16.0.1"
        assert num_hosts == 65534
    
    def test_calculate_subnet_class_a(self):
        """Test subnet calculation for Class A network."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        network, broadcast, first_host, num_hosts = nl.calculate_subnet(
            "10.50.100.200", "255.0.0.0"
        )
        
        assert network == "10.0.0.0"
        assert broadcast == "10.255.255.255"
        assert first_host == "10.0.0.1"
        assert num_hosts == 16777214
    
    def test_calculate_subnet_with_cidr(self):
        """Test subnet calculation with various CIDR notations."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        # /30 subnet (4 addresses, 2 usable hosts)
        network, broadcast, first_host, num_hosts = nl.calculate_subnet(
            "192.168.1.4", "255.255.255.252"
        )
        assert network == "192.168.1.4"
        assert broadcast == "192.168.1.7"
        assert num_hosts == 2
        
        # /29 subnet (8 addresses, 6 usable hosts)
        network, broadcast, first_host, num_hosts = nl.calculate_subnet(
            "192.168.1.8", "255.255.255.248"
        )
        assert network == "192.168.1.8"
        assert broadcast == "192.168.1.15"
        assert num_hosts == 6
    
    def test_calculate_subnet_invalid_input(self):
        """Test subnet calculation with invalid input."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        with pytest.raises(ValueError):
            nl.calculate_subnet("999.999.999.999", "255.255.255.0")
        
        with pytest.raises(ValueError):
            nl.calculate_subnet("192.168.1.1", "invalid.mask")


class TestSubnetMembership:
    """Test subnet membership checking methods."""
    
    def test_is_same_subnet_true(self):
        """Test checking if two IPs are in the same subnet (positive cases)."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.is_same_subnet(
            "192.168.1.10", "192.168.1.20", "255.255.255.0"
        ) is True
        
        assert nl.is_same_subnet(
            "10.0.0.1", "10.0.0.254", "255.255.255.0"
        ) is True
        
        assert nl.is_same_subnet(
            "172.16.1.1", "172.16.255.254", "255.255.0.0"
        ) is True
    
    def test_is_same_subnet_false(self):
        """Test checking if two IPs are in the same subnet (negative cases)."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.is_same_subnet(
            "192.168.1.10", "192.168.2.10", "255.255.255.0"
        ) is False
        
        assert nl.is_same_subnet(
            "10.0.0.1", "10.1.0.1", "255.255.0.0"
        ) is False
        
        assert nl.is_same_subnet(
            "172.16.1.1", "172.17.1.1", "255.255.0.0"
        ) is False
    
    def test_is_in_subnet(self):
        """Test checking if an IP is in this node's subnet."""
        nl = NetworkLayer("node1", "192.168.1.100", "255.255.255.0")
        
        # IPs in the same subnet
        assert nl.is_in_subnet("192.168.1.1") is True
        assert nl.is_in_subnet("192.168.1.100") is True
        assert nl.is_in_subnet("192.168.1.254") is True
        
        # IPs in different subnets
        assert nl.is_in_subnet("192.168.2.1") is False
        assert nl.is_in_subnet("10.0.0.1") is False
        assert nl.is_in_subnet("172.16.0.1") is False
    
    def test_is_in_subnet_invalid_ip(self):
        """Test subnet membership with invalid IP."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.is_in_subnet("invalid.ip") is False
        assert nl.is_in_subnet("999.999.999.999") is False


class TestRoutingTableOperations:
    """Test routing table management methods."""
    
    def test_add_route(self):
        """Test adding routes to the routing table."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry(
            destination="192.168.2.0/24",
            next_hop="192.168.1.254",
            cost=1.0,
            interface="eth0",
            timestamp=time.time(),
            metric_type="hop_count"
        )
        
        nl.add_route(route)
        assert nl.routing_table.get("192.168.2.0/24") is not None
        assert nl.routing_table.get("192.168.2.0/24").next_hop == "192.168.1.254"
    
    def test_add_multiple_routes(self):
        """Test adding multiple routes."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
            RouteEntry("10.0.0.0/8", "192.168.1.1", 5.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            nl.add_route(route)
        
        assert nl.routing_table.size() == 3
        assert nl.routing_table.get("192.168.2.0/24") is not None
        assert nl.routing_table.get("192.168.3.0/24") is not None
        assert nl.routing_table.get("10.0.0.0/8") is not None
    
    def test_update_existing_route(self):
        """Test updating an existing route."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route1 = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route1)
        
        # Update with better route
        route2 = RouteEntry("192.168.2.0/24", "192.168.1.253", 0.5, "eth1", time.time(), "latency")
        nl.add_route(route2)
        
        assert nl.routing_table.size() == 1
        assert nl.routing_table.get("192.168.2.0/24").next_hop == "192.168.1.253"
        assert nl.routing_table.get("192.168.2.0/24").cost == 0.5
    
    def test_remove_route(self):
        """Test removing a route from the routing table."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route)
        
        assert nl.remove_route("192.168.2.0/24") is True
        assert nl.routing_table.get("192.168.2.0/24") is None
    
    def test_remove_nonexistent_route(self):
        """Test removing a route that doesn't exist."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        assert nl.remove_route("192.168.2.0/24") is False
    
    def test_get_routing_table(self):
        """Test getting a copy of the routing table."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route)
        
        table_copy = nl.get_routing_table()
        assert len(table_copy) == 1
        assert "192.168.2.0/24" in table_copy
        
        # Verify it's a copy, not a reference
        table_copy.clear()
        assert nl.routing_table.size() == 1
    
    def test_clear_routing_table(self):
        """Test clearing the routing table."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        routes = [
            RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count"),
            RouteEntry("192.168.3.0/24", "192.168.1.253", 2.0, "eth0", time.time(), "hop_count"),
        ]
        
        for route in routes:
            nl.add_route(route)
        
        assert nl.routing_table.size() == 2
        
        nl.clear_routing_table()
        assert nl.routing_table.size() == 0


class TestNextHopLookup:
    """Test next hop lookup logic."""
    
    def test_get_next_hop_exact_match(self):
        """Test next hop lookup with exact destination match."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry("192.168.2.5", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route)
        
        next_hop = nl.get_next_hop("192.168.2.5")
        assert next_hop == "192.168.1.254"
    
    def test_get_next_hop_local_subnet(self):
        """Test next hop lookup for destination in local subnet."""
        nl = NetworkLayer("node1", "192.168.1.1", "255.255.255.0")
        
        # Destination in local subnet should return the destination itself
        next_hop = nl.get_next_hop("192.168.1.50")
        assert next_hop == "192.168.1.50"
    
    def test_get_next_hop_subnet_match(self):
        """Test next hop lookup with subnet-based routing."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route)
        
        # Any IP in 192.168.2.0/24 should route through 192.168.1.254
        next_hop = nl.get_next_hop("192.168.2.50")
        assert next_hop == "192.168.1.254"
        
        next_hop = nl.get_next_hop("192.168.2.100")
        assert next_hop == "192.168.1.254"
    
    def test_get_next_hop_longest_prefix_match(self):
        """Test longest prefix matching for overlapping routes."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        # Add overlapping routes
        route1 = RouteEntry("192.168.0.0/16", "192.168.1.254", 2.0, "eth0", time.time(), "hop_count")
        route2 = RouteEntry("192.168.2.0/24", "192.168.1.253", 1.0, "eth1", time.time(), "hop_count")
        
        nl.add_route(route1)
        nl.add_route(route2)
        
        # Should use more specific route (longer prefix)
        next_hop = nl.get_next_hop("192.168.2.50")
        assert next_hop == "192.168.1.253"
        
        # Should use less specific route
        next_hop = nl.get_next_hop("192.168.3.50")
        assert next_hop == "192.168.1.254"
    
    def test_get_next_hop_default_route(self):
        """Test default route (0.0.0.0/0) as fallback."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        default_route = RouteEntry("0.0.0.0/0", "192.168.1.254", 10.0, "eth0", time.time(), "hop_count")
        nl.add_route(default_route)
        
        # Any destination without specific route should use default
        next_hop = nl.get_next_hop("8.8.8.8")
        assert next_hop == "192.168.1.254"
        
        next_hop = nl.get_next_hop("1.2.3.4")
        assert next_hop == "192.168.1.254"
    
    def test_get_next_hop_no_route(self):
        """Test next hop lookup when no route exists."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        next_hop = nl.get_next_hop("10.0.0.1")
        assert next_hop is None
    
    def test_get_next_hop_invalid_destination(self):
        """Test next hop lookup with invalid destination."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        next_hop = nl.get_next_hop("invalid.ip")
        assert next_hop is None


class TestPacketForwarding:
    """Test packet forwarding logic."""
    
    def test_forward_packet_to_destination(self):
        """Test forwarding packet that has reached its destination."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        packet = Packet(
            packet_id="pkt1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="192.168.1.1",  # This node's IP
            protocol="TCP",
            payload=b"test data"
        )
        
        # Should return None when packet reaches destination
        next_hop = nl.forward_packet(packet)
        assert next_hop is None
    
    def test_forward_packet_with_route(self):
        """Test forwarding packet with available route."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        route = RouteEntry("192.168.2.0/24", "192.168.1.254", 1.0, "eth0", time.time(), "hop_count")
        nl.add_route(route)
        
        packet = Packet(
            packet_id="pkt1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="192.168.2.50",
            protocol="TCP",
            payload=b"test data"
        )
        
        next_hop = nl.forward_packet(packet)
        assert next_hop == "192.168.1.254"
    
    def test_forward_packet_no_route(self):
        """Test forwarding packet with no available route."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        packet = Packet(
            packet_id="pkt1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="10.0.0.1",
            protocol="TCP",
            payload=b"test data"
        )
        
        next_hop = nl.forward_packet(packet)
        assert next_hop is None
    
    def test_forward_packet_local_subnet(self):
        """Test forwarding packet to destination in local subnet."""
        nl = NetworkLayer("node1", "192.168.1.1", "255.255.255.0")
        
        packet = Packet(
            packet_id="pkt1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="192.168.1.50",
            protocol="TCP",
            payload=b"test data"
        )
        
        # Should forward directly to destination
        next_hop = nl.forward_packet(packet)
        assert next_hop == "192.168.1.50"
    
    def test_forward_packet_with_default_route(self):
        """Test forwarding packet using default route."""
        nl = NetworkLayer("node1", "192.168.1.1")
        
        default_route = RouteEntry("0.0.0.0/0", "192.168.1.254", 10.0, "eth0", time.time(), "hop_count")
        nl.add_route(default_route)
        
        packet = Packet(
            packet_id="pkt1",
            timestamp=time.time(),
            source_ip="192.168.1.2",
            dest_ip="8.8.8.8",
            protocol="TCP",
            payload=b"test data"
        )
        
        next_hop = nl.forward_packet(packet)
        assert next_hop == "192.168.1.254"
