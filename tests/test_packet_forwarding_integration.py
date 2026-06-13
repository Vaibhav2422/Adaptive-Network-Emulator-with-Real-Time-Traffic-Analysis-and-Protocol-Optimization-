"""
Integration tests for packet forwarding through multi-hop networks.

Tests packet forwarding through 3+ hops with various network topologies
to verify:
- Packets reach correct destinations
- Routing tables are used correctly
- Packet delivery rate >95% in stable network
"""

import pytest
import time
from src.network_layer import NetworkLayer
from src.dijkstra_router import DijkstraRouter
from src.distance_vector_router import DistanceVectorRouter
from src.data_models import Packet, NetworkTopology, Link, RouteEntry


# ─────────────────────────────────────────────────────────────
# Helper: forward_packet returns an IP address; convert it to
# a node_id using the ip→node reverse map so all assertions
# and dict lookups work with node IDs throughout.
# ─────────────────────────────────────────────────────────────

def _resolve(next_hop_ip, ip_to_node):
    """Convert a next-hop IP address to its node ID, or None."""
    if next_hop_ip is None:
        return None
    return ip_to_node.get(next_hop_ip, next_hop_ip)


def _install_routes(node_id, node, topology):
    """Compute Dijkstra routes for node_id and install them."""
    router = DijkstraRouter(node_id)
    router.update_topology(topology)
    routing_table = router.generate_routing_table()
    for dest, route in routing_table.get_all().items():
        node.add_route(route)


class TestMultiHopPacketForwarding:
    """Test packet forwarding through multi-hop networks."""

    def test_linear_topology_3_hops(self):
        """
        Test packet forwarding through linear topology with 3 hops:
        A --10-- B --15-- C --20-- D

        Test: Send packet from A to D (3 hops)
        Expected: Packet reaches D via B and C
        """
        node_a = NetworkLayer("node_a", "192.168.1.1")
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
        }

        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 20.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        for nid, node in [("node_a", node_a), ("node_b", node_b),
                           ("node_c", node_c), ("node_d", node_d)]:
            _install_routes(nid, node, topology)

        packet = Packet(
            packet_id="pkt_1", timestamp=time.time(),
            source_ip="192.168.1.1", dest_ip="192.168.1.4",
            protocol="TCP", payload=b"Test data from A to D",
        )

        nodes_map = {
            "node_a": node_a, "node_b": node_b,
            "node_c": node_c, "node_d": node_d,
        }

        # Hop 1: A -> B
        next_hop_1 = _resolve(node_a.forward_packet(packet), ip_to_node)
        assert next_hop_1 == "node_b", f"Expected next hop node_b, got {next_hop_1}"

        # Hop 2: B -> C
        next_hop_2 = _resolve(node_b.forward_packet(packet), ip_to_node)
        assert next_hop_2 == "node_c", f"Expected next hop node_c, got {next_hop_2}"

        # Hop 3: C -> D
        next_hop_3 = _resolve(node_c.forward_packet(packet), ip_to_node)
        assert next_hop_3 == "node_d", f"Expected next hop node_d, got {next_hop_3}"

        # Hop 4: D receives packet (destination reached)
        next_hop_4 = node_d.forward_packet(packet)
        assert next_hop_4 is None, "Packet should be delivered at destination"

    def test_mesh_topology_multiple_paths(self):
        """
        Test packet forwarding in mesh topology with multiple paths:
        A --5-- B --10-- D
        |       |        |
        15      8        5
        |       |        |
        C ------+--12--- E

        Test: Send packets from A to E
        Expected: Packets take shortest path A->B->D->E (cost 20)
        """
        node_a = NetworkLayer("node_a", "192.168.1.1")
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")
        node_e = NetworkLayer("node_e", "192.168.1.5")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
            "192.168.1.5": "node_e",
        }

        nodes = ["node_a", "node_b", "node_c", "node_d", "node_e"]
        links = [
            Link("node_a", "node_b",  5.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c",  8.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_e", 12.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_d", "node_e",  5.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        nodes_obj = {
            "node_a": node_a, "node_b": node_b, "node_c": node_c,
            "node_d": node_d, "node_e": node_e,
        }

        for nid, node in nodes_obj.items():
            _install_routes(nid, node, topology)

        packet = Packet(
            packet_id="pkt_mesh_1", timestamp=time.time(),
            source_ip="192.168.1.1", dest_ip="192.168.1.5",
            protocol="TCP", payload=b"Test data in mesh",
        )

        path = ["node_a"]
        current_node = node_a
        max_hops = 10
        hops = 0

        while hops < max_hops:
            next_hop_ip = current_node.forward_packet(packet)
            if next_hop_ip is None:
                break
            next_hop = _resolve(next_hop_ip, ip_to_node)
            path.append(next_hop)
            current_node = nodes_obj[next_hop]
            hops += 1

        assert hops < max_hops, "Packet did not reach destination (possible loop)"
        assert path[-1] == "node_e", f"Packet did not reach node_e, path: {path}"
        assert path == ["node_a", "node_b", "node_d", "node_e"], \
            f"Path not optimal, got: {path}"

    def test_star_topology(self):
        """
        Test packet forwarding in star topology:

            B
            |
        C - A - D
            |
            E

        All nodes connect through central node A.
        Test: Send packets from B to E (2 hops through A)
        """
        node_a = NetworkLayer("node_a", "192.168.1.1")  # Central node
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")
        node_e = NetworkLayer("node_e", "192.168.1.5")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
            "192.168.1.5": "node_e",
        }

        nodes = ["node_a", "node_b", "node_c", "node_d", "node_e"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_e", 10.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        for nid, node in [("node_a", node_a), ("node_b", node_b),
                           ("node_c", node_c), ("node_d", node_d),
                           ("node_e", node_e)]:
            _install_routes(nid, node, topology)

        packet = Packet(
            packet_id="pkt_star_1", timestamp=time.time(),
            source_ip="192.168.1.2", dest_ip="192.168.1.5",
            protocol="TCP", payload=b"Test data in star",
        )

        next_hop_1 = _resolve(node_b.forward_packet(packet), ip_to_node)
        assert next_hop_1 == "node_a", "First hop should be to central node"

        next_hop_2 = _resolve(node_a.forward_packet(packet), ip_to_node)
        assert next_hop_2 == "node_e", "Second hop should be to destination"

        next_hop_3 = node_e.forward_packet(packet)
        assert next_hop_3 is None, "Packet should be delivered"

    def test_ring_topology(self):
        """
        Test packet forwarding in ring topology:

        A --- B
        |     |
        D --- C

        Test: Send packet from A to C (shortest path A->B->C, 2 hops)
        """
        node_a = NetworkLayer("node_a", "192.168.1.1")
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
        }

        nodes = ["node_a", "node_b", "node_c", "node_d"]
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_d", "node_a", 10.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        nodes_obj = {
            "node_a": node_a, "node_b": node_b,
            "node_c": node_c, "node_d": node_d,
        }

        for nid, node in nodes_obj.items():
            _install_routes(nid, node, topology)

        packet = Packet(
            packet_id="pkt_ring_1", timestamp=time.time(),
            source_ip="192.168.1.1", dest_ip="192.168.1.3",
            protocol="TCP", payload=b"Test data in ring",
        )

        path = ["node_a"]
        current_node = node_a
        max_hops = 10
        hops = 0

        while hops < max_hops:
            next_hop_ip = current_node.forward_packet(packet)
            if next_hop_ip is None:
                break
            next_hop = _resolve(next_hop_ip, ip_to_node)
            path.append(next_hop)
            current_node = nodes_obj[next_hop]
            hops += 1

        assert hops < max_hops, "Packet did not reach destination"
        assert path[-1] == "node_c", f"Packet did not reach node_c, path: {path}"
        assert len(path) == 3, \
            f"Expected 3 nodes in path (A, B, C), got {len(path)}: {path}"


class TestPacketDeliveryRate:
    """Test packet delivery rate in stable network."""

    def _make_linear_network(self):
        """Create linear A-B-C-D topology and return nodes + ip_to_node."""
        node_a = NetworkLayer("node_a", "192.168.1.1")
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
        }
        nodes_map = {
            "node_a": node_a, "node_b": node_b,
            "node_c": node_c, "node_d": node_d,
        }

        nodes = list(nodes_map.keys())
        links = [
            Link("node_a", "node_b", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_d", 20.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        for nid, node in nodes_map.items():
            _install_routes(nid, node, topology)

        return node_a, nodes_map, ip_to_node

    def test_delivery_rate_linear_topology(self):
        """
        Test packet delivery rate in stable linear topology.
        Send 100 packets and verify >95% delivery rate.
        """
        node_a, nodes_map, ip_to_node = self._make_linear_network()

        num_packets = 100
        delivered = 0

        for i in range(num_packets):
            packet = Packet(
                packet_id=f"pkt_{i}", timestamp=time.time(),
                source_ip="192.168.1.1", dest_ip="192.168.1.4",
                protocol="TCP", payload=f"Packet {i}".encode(),
            )

            current_node = node_a
            max_hops = 10
            hops = 0
            reached_destination = False

            while hops < max_hops:
                next_hop_ip = current_node.forward_packet(packet)
                if next_hop_ip is None:
                    reached_destination = True
                    break
                next_hop = _resolve(next_hop_ip, ip_to_node)
                current_node = nodes_map.get(next_hop)
                if current_node is None:
                    break
                hops += 1

            if reached_destination:
                delivered += 1

        delivery_rate = (delivered / num_packets) * 100
        assert delivery_rate > 95.0, \
            f"Delivery rate {delivery_rate}% is below 95% threshold"
        print(f"Delivery rate: {delivery_rate}% ({delivered}/{num_packets} packets)")

    def test_delivery_rate_mesh_topology(self):
        """
        Test packet delivery rate in stable mesh topology.
        Send 100 packets and verify >95% delivery rate.
        """
        node_a = NetworkLayer("node_a", "192.168.1.1")
        node_b = NetworkLayer("node_b", "192.168.1.2")
        node_c = NetworkLayer("node_c", "192.168.1.3")
        node_d = NetworkLayer("node_d", "192.168.1.4")
        node_e = NetworkLayer("node_e", "192.168.1.5")

        ip_to_node = {
            "192.168.1.1": "node_a",
            "192.168.1.2": "node_b",
            "192.168.1.3": "node_c",
            "192.168.1.4": "node_d",
            "192.168.1.5": "node_e",
        }
        nodes_map = {
            "node_a": node_a, "node_b": node_b, "node_c": node_c,
            "node_d": node_d, "node_e": node_e,
        }

        nodes = list(nodes_map.keys())
        links = [
            Link("node_a", "node_b",  5.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_a", "node_c", 15.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_c",  8.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_b", "node_d", 10.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_c", "node_e", 12.0, 0.0, 0.0, 0.0, 0.0),
            Link("node_d", "node_e",  5.0, 0.0, 0.0, 0.0, 0.0),
        ]
        topology = NetworkTopology(nodes, links)

        for nid, node in nodes_map.items():
            _install_routes(nid, node, topology)

        num_packets = 100
        delivered = 0

        for i in range(num_packets):
            packet = Packet(
                packet_id=f"pkt_mesh_{i}", timestamp=time.time(),
                source_ip="192.168.1.1", dest_ip="192.168.1.5",
                protocol="TCP", payload=f"Mesh packet {i}".encode(),
            )

            current_node = node_a
            max_hops = 10
            hops = 0
            reached_destination = False

            while hops < max_hops:
                next_hop_ip = current_node.forward_packet(packet)
                if next_hop_ip is None:
                    reached_destination = True
                    break
                next_hop = _resolve(next_hop_ip, ip_to_node)
                current_node = nodes_map.get(next_hop)
                if current_node is None:
                    break
                hops += 1

            if reached_destination:
                delivered += 1

        delivery_rate = (delivered / num_packets) * 100
        assert delivery_rate > 95.0, \
            f"Delivery rate {delivery_rate}% is below 95% threshold"
        print(f"Mesh delivery rate: {delivery_rate}% ({delivered}/{num_packets} packets)")
