"""
Traffic Analyzer implementation for the Adaptive Network Emulator.

Provides packet capture using PyShark and timing extraction for emulator traffic.
Falls back gracefully when PyShark/tshark is unavailable.

Validates: Requirements 7.1
"""

import logging
import time
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# PyShark import with graceful fallback
try:
    import pyshark
    PYSHARK_AVAILABLE = True
except ImportError:
    PYSHARK_AVAILABLE = False
    logger.warning("PyShark not available. Packet capture will use emulator-internal tracking.")


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class CapturedPacket:
    """
    Represents a single captured packet with timing and layer information.

    Attributes:
        packet_id:   Unique identifier for the packet
        send_time:   Timestamp when the packet was sent (epoch seconds)
        recv_time:   Timestamp when the packet was received (epoch seconds, None if lost)
        size_bytes:  Payload size in bytes
        source:      Source IP or node identifier
        destination: Destination IP or node identifier
        protocol:    Protocol name (TCP / UDP / ICMP / etc.)
        layer:       OSI layer at which the packet was captured
        is_retransmission: True if this packet is a retransmission
        headers:     Dict of layer-specific header fields
        emulator_marker: Custom marker injected by the emulator for filtering
    """
    packet_id: str
    send_time: float
    recv_time: Optional[float]
    size_bytes: int
    source: str
    destination: str
    protocol: str
    layer: str
    is_retransmission: bool = False
    headers: Dict = field(default_factory=dict)
    emulator_marker: str = "EMULATOR_PKT"


@dataclass
class LayerInfo:
    """Parsed header info for a single OSI layer."""
    layer_name: str
    fields: Dict[str, str] = field(default_factory=dict)
    processing_time_ms: float = 0.0


# ─────────────────────────────────────────────
# TrafficAnalyzer
# ─────────────────────────────────────────────

class TrafficAnalyzer:
    """
    Captures and analyses network traffic for the emulator.

    Supports two capture modes:
      1. PyShark mode  – live capture on the loopback interface, filtering for
                         packets that carry the emulator marker in their payload.
      2. Internal mode – purely in-process tracking via register_packet() /
                         register_packet_received(), used when PyShark / tshark
                         is unavailable or in unit-test environments.

    Usage::

        analyzer = TrafficAnalyzer()
        analyzer.start_capture()
        # ... run emulator ...
        packets = analyzer.stop_capture()

    Validates: Requirements 7.1
    """

    EMULATOR_MARKER = "EMULATOR_PKT"

    def __init__(
        self,
        interface: str = "lo",
        capture_filter: str = "",
        use_pyshark: bool = True,
    ):
        """
        Initialise the TrafficAnalyzer.

        Args:
            interface:     Network interface to capture on (default: loopback "lo").
            capture_filter: BPF filter string passed to PyShark (empty = capture all).
            use_pyshark:   Whether to attempt PyShark-based capture.
        """
        self.interface = interface
        self.capture_filter = capture_filter
        self._use_pyshark = use_pyshark and PYSHARK_AVAILABLE

        self._capturing: bool = False
        self._capture_start_time: Optional[float] = None
        self._capture_stop_time: Optional[float] = None

        # Internal packet store (used in both modes)
        self._packets: List[CapturedPacket] = []

        # PyShark capture object (live capture)
        self._pyshark_capture = None

        # Callbacks invoked for each new packet (optional)
        self._packet_callbacks: List[Callable[[CapturedPacket], None]] = []

        logger.info(
            "TrafficAnalyzer initialised: interface=%s, pyshark=%s",
            interface,
            self._use_pyshark,
        )

    # ── Public control API ────────────────────────────────────────────────

    def start_capture(self) -> bool:
        """
        Begin packet capture.

        Returns:
            True if capture started successfully, False otherwise.
        """
        if self._capturing:
            logger.warning("Capture already running.")
            return False

        self._packets.clear()
        self._capture_start_time = time.time()
        self._capturing = True

        if self._use_pyshark:
            return self._start_pyshark_capture()

        logger.info("TrafficAnalyzer: using internal (non-PyShark) capture mode.")
        return True

    def stop_capture(self) -> List[CapturedPacket]:
        """
        Stop packet capture and return all captured packets.

        Returns:
            List of CapturedPacket objects recorded during the session.
        """
        if not self._capturing:
            logger.warning("No active capture to stop.")
            return list(self._packets)

        self._capturing = False
        self._capture_stop_time = time.time()

        if self._use_pyshark and self._pyshark_capture is not None:
            self._stop_pyshark_capture()

        duration = (self._capture_stop_time or time.time()) - (self._capture_start_time or 0)
        logger.info(
            "Capture stopped: %d packets in %.3f s",
            len(self._packets),
            duration,
        )
        return list(self._packets)

    def is_capturing(self) -> bool:
        """Return True if a capture session is currently active."""
        return self._capturing

    def add_packet_callback(self, callback: Callable[[CapturedPacket], None]) -> None:
        """Register a callback invoked for every new captured packet."""
        self._packet_callbacks.append(callback)

    # ── Internal tracking API (used when PyShark is not available) ────────

    def register_packet_sent(
        self,
        packet_id: str,
        size_bytes: int,
        source: str,
        destination: str,
        protocol: str = "TCP",
        layer: str = "Transport",
        is_retransmission: bool = False,
        headers: Optional[Dict] = None,
    ) -> CapturedPacket:
        """
        Register a packet that has just been sent by the emulator.

        Call this from the emulator send path to track packets internally.

        Args:
            packet_id:        Unique packet identifier.
            size_bytes:       Payload size in bytes.
            source:           Source IP / node ID.
            destination:      Destination IP / node ID.
            protocol:         Protocol label.
            layer:            OSI layer name.
            is_retransmission: True for retransmitted packets.
            headers:          Optional dict of header fields.

        Returns:
            The created CapturedPacket (recv_time is None until received).
        """
        pkt = CapturedPacket(
            packet_id=packet_id,
            send_time=time.time(),
            recv_time=None,
            size_bytes=size_bytes,
            source=source,
            destination=destination,
            protocol=protocol,
            layer=layer,
            is_retransmission=is_retransmission,
            headers=headers or {},
            emulator_marker=self.EMULATOR_MARKER,
        )
        self._packets.append(pkt)
        self._invoke_callbacks(pkt)
        return pkt

    def register_packet_received(self, packet_id: str) -> bool:
        """
        Mark a previously registered packet as successfully received.

        Args:
            packet_id: The packet_id supplied to register_packet_sent().

        Returns:
            True if the packet was found and updated, False otherwise.
        """
        for pkt in self._packets:
            if pkt.packet_id == packet_id and pkt.recv_time is None:
                pkt.recv_time = time.time()
                return True
        logger.warning("register_packet_received: packet_id '%s' not found.", packet_id)
        return False

    # ── Query API ─────────────────────────────────────────────────────────

    def get_captured_packets(self) -> List[CapturedPacket]:
        """Return a copy of all packets captured so far."""
        return list(self._packets)

    def get_capture_duration(self) -> float:
        """
        Return the duration of the most recent (or ongoing) capture in seconds.
        """
        if self._capture_start_time is None:
            return 0.0
        end = self._capture_stop_time if self._capture_stop_time else time.time()
        return end - self._capture_start_time

    def get_statistics(self) -> Dict:
        """Return a summary dict of the current capture session."""
        total = len(self._packets)
        received = sum(1 for p in self._packets if p.recv_time is not None)
        lost = total - received
        retransmissions = sum(1 for p in self._packets if p.is_retransmission)
        return {
            "total_packets": total,
            "received_packets": received,
            "lost_packets": lost,
            "retransmissions": retransmissions,
            "capture_duration_s": self.get_capture_duration(),
        }

    # ── Layer header parsing ──────────────────────────────────────────────

    def parse_layer_headers(self, packet: CapturedPacket) -> List[LayerInfo]:
        """
        Extract per-layer header information from a CapturedPacket.

        For PyShark-captured packets this would read the real wire fields;
        for internally-tracked packets it reads the headers dict.

        Args:
            packet: CapturedPacket to parse.

        Returns:
            List of LayerInfo objects, one per layer present in headers.
        """
        layers: List[LayerInfo] = []

        # Walk through header keys like "physical", "data_link", "network", etc.
        layer_order = ["physical", "data_link", "mac", "network", "transport", "application"]
        for layer_name in layer_order:
            if layer_name in packet.headers:
                raw = packet.headers[layer_name]
                fields = raw if isinstance(raw, dict) else {"raw": str(raw)}
                layers.append(LayerInfo(layer_name=layer_name, fields=fields))

        # If nothing specific, create a single entry from the packet's own layer
        if not layers:
            layers.append(LayerInfo(
                layer_name=packet.layer,
                fields={
                    "source": packet.source,
                    "destination": packet.destination,
                    "protocol": packet.protocol,
                    "size_bytes": str(packet.size_bytes),
                },
            ))

        return layers

    def filter_emulator_packets(self, packets: List[CapturedPacket]) -> List[CapturedPacket]:
        """
        Filter a list of packets to only those originating from the emulator.

        Args:
            packets: List of CapturedPacket objects.

        Returns:
            Filtered list containing only emulator packets.
        """
        return [p for p in packets if p.emulator_marker == self.EMULATOR_MARKER]

    # ── PyShark internals ─────────────────────────────────────────────────

    def _start_pyshark_capture(self) -> bool:
        """Start a PyShark live capture on the configured interface."""
        try:
            self._pyshark_capture = pyshark.LiveCapture(
                interface=self.interface,
                bpf_filter=self.capture_filter or None,
            )
            logger.info("PyShark capture started on interface '%s'.", self.interface)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to start PyShark capture: %s", exc)
            # Fall back to internal mode
            self._use_pyshark = False
            self._pyshark_capture = None
            return True  # Still return True – internal mode will be used

    def _stop_pyshark_capture(self) -> None:
        """Stop the PyShark live capture and harvest packets."""
        if self._pyshark_capture is None:
            return
        try:
            self._pyshark_capture.close()
            # Harvest any packets that were sniffed
            for raw_pkt in self._pyshark_capture._packets:  # type: ignore[attr-defined]
                captured = self._parse_pyshark_packet(raw_pkt)
                if captured:
                    self._packets.append(captured)
                    self._invoke_callbacks(captured)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error stopping PyShark capture: %s", exc)
        finally:
            self._pyshark_capture = None

    def _parse_pyshark_packet(self, raw_pkt) -> Optional[CapturedPacket]:
        """
        Convert a raw PyShark packet object into a CapturedPacket.

        Only returns packets that carry the emulator marker in their payload.

        Args:
            raw_pkt: A pyshark packet object.

        Returns:
            CapturedPacket or None if the packet is not from the emulator.
        """
        try:
            # Check payload for emulator marker (data layer)
            payload_str = ""
            if hasattr(raw_pkt, "data"):
                payload_str = str(raw_pkt.data)
            if self.EMULATOR_MARKER not in payload_str:
                return None

            # Extract timing
            send_time = float(raw_pkt.sniff_timestamp)

            # Extract IP layer
            source = "unknown"
            destination = "unknown"
            protocol = "unknown"
            if hasattr(raw_pkt, "ip"):
                source = str(raw_pkt.ip.src)
                destination = str(raw_pkt.ip.dst)
                protocol = str(raw_pkt.ip.proto)

            # Packet size
            size_bytes = int(raw_pkt.length) if hasattr(raw_pkt, "length") else 0

            # Determine layer
            layer = "Network"
            if hasattr(raw_pkt, "tcp"):
                layer = "Transport"
                protocol = "TCP"
            elif hasattr(raw_pkt, "udp"):
                layer = "Transport"
                protocol = "UDP"

            pkt_id = f"pyshark_{source}_{destination}_{send_time}"

            return CapturedPacket(
                packet_id=pkt_id,
                send_time=send_time,
                recv_time=send_time,  # Live capture: recv ≈ sniff time
                size_bytes=size_bytes,
                source=source,
                destination=destination,
                protocol=protocol,
                layer=layer,
                emulator_marker=self.EMULATOR_MARKER,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not parse PyShark packet: %s", exc)
            return None

    # ── Helpers ───────────────────────────────────────────────────────────

    def _invoke_callbacks(self, packet: CapturedPacket) -> None:
        for cb in self._packet_callbacks:
            try:
                cb(packet)
            except Exception as exc:  # noqa: BLE001
                logger.error("Packet callback raised: %s", exc)
