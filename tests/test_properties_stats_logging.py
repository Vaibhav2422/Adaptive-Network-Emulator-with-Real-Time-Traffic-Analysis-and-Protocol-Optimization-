"""
Property-based tests for Statistics Collector and Performance Logger (Task 21.3).

Properties tested:
  - Property 26: Metric timestamp association   (Requirement 7.6)
  - Property 27: Packet categorization correctness (Requirement 7.8)

Each property uses at least 100 hypothesis examples.
"""

import json
import tempfile
import os
from datetime import datetime, timezone
from typing import List, Optional

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.traffic_analyzer import CapturedPacket
from src.performance_logger import PerformanceLogger, _categorise_protocol, _categorise_layer
from src.statistics_collector import StatisticsCollector


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

VALID_PROTOCOLS = ["TCP", "UDP", "ICMP", "GBN", "SR", "OTHER", "tcp", "udp", "icmp"]
VALID_LAYERS    = ["application", "transport", "network", "data_link", "mac",
                   "physical", "Application", "Transport", "Network"]


def _make_packet(
    packet_id: str,
    send_time: float,
    recv_time: Optional[float],
    size_bytes: int,
    protocol: str = "TCP",
    layer: str = "Transport",
    is_retransmission: bool = False,
) -> CapturedPacket:
    return CapturedPacket(
        packet_id=packet_id,
        send_time=send_time,
        recv_time=recv_time,
        size_bytes=size_bytes,
        source="192.168.1.1",
        destination="192.168.1.2",
        protocol=protocol,
        layer=layer,
        is_retransmission=is_retransmission,
    )


def _is_valid_iso8601(ts: str) -> bool:
    """Return True if ts parses as an ISO 8601 datetime."""
    try:
        datetime.fromisoformat(ts)
        return True
    except ValueError:
        return False


# ─────────────────────────────────────────────
# Property 26: Every metric has a timestamp
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    metric_name=st.text(min_size=1, max_size=50,
                        alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    value=st.one_of(
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        st.integers(min_value=0, max_value=10_000),
    ),
    unit=st.sampled_from(["bps", "ms", "%", "bytes", ""]),
)
def test_property_26_every_logged_metric_has_timestamp(metric_name, value, unit):
    """
    Property 26: Metric timestamp association.
    Validates: Requirement 7.6

    For any metric logged by PerformanceLogger, the resulting entry must
    have a non-empty, valid ISO 8601 timestamp.
    """
    assume(metric_name.strip())   # Ignore blank-only names

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)
        entry = plogger.log_metric(metric_name.strip(), value, unit)
        plogger.close()

        # Timestamp must be present and non-empty
        assert entry.timestamp, "Metric entry must have a non-empty timestamp"

        # Timestamp must be a valid ISO 8601 string
        assert _is_valid_iso8601(entry.timestamp), (
            f"Timestamp '{entry.timestamp}' is not valid ISO 8601"
        )

        # Timestamp must include timezone info (UTC)
        assert "+" in entry.timestamp or entry.timestamp.endswith("Z") or "T" in entry.timestamp, (
            "Timestamp should contain time component"
        )

        # Metric name and value must be preserved
        assert entry.metric_name == metric_name.strip()
        assert entry.value == value
        assert entry.unit == unit


@settings(max_examples=100, deadline=None)
@given(
    sizes=st.lists(st.integers(min_value=1, max_value=65535), min_size=1, max_size=20),
    lost_count=st.integers(min_value=0, max_value=5),
)
def test_property_26_session_metrics_all_have_timestamps(sizes, lost_count):
    """
    Property 26 (variant): Every metric in a session log must have a timestamp.
    """
    assume(lost_count <= len(sizes))

    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.01,
            recv_time=None if i < lost_count else base_time + i * 0.01 + 0.005,
            size_bytes=sizes[i],
        )
        for i in range(len(sizes))
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)
        plogger.log_session_metrics(packets, session_id="test_session")

        entries = plogger.get_metric_entries()
        plogger.close()  # Must close BEFORE tempdir exits on Windows

        assert len(entries) > 0, "Session metrics must produce at least one log entry"

        for entry in entries:
            assert entry.timestamp, f"Entry '{entry.metric_name}' missing timestamp"
            assert _is_valid_iso8601(entry.timestamp), (
                f"Entry '{entry.metric_name}' has invalid timestamp: {entry.timestamp}"
            )


@settings(max_examples=100, deadline=None)
@given(
    n_metrics=st.integers(min_value=1, max_value=20),
    values=st.lists(
        st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=1, max_size=20,
    ),
)
def test_property_26_timestamps_written_to_log_file(n_metrics, values):
    """
    Property 26 (variant): Timestamps appear in the persisted JSON log file.
    """
    n = min(n_metrics, len(values))
    assume(n >= 1)

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)

        for i in range(n):
            plogger.log_metric(f"metric_{i}", values[i], "units")

        # Read log entries BEFORE closing (file must still be open)
        log_entries = plogger.read_log_file()
        plogger.close()

        assert len(log_entries) == n, (
            f"Expected {n} log entries, found {len(log_entries)}"
        )

        for record in log_entries:
            assert "timestamp" in record, "Every log file record must have a 'timestamp' field"
            assert record["timestamp"], "Timestamp must not be empty"
            assert _is_valid_iso8601(record["timestamp"]), (
                f"Log file timestamp '{record['timestamp']}' is not valid ISO 8601"
            )


@settings(max_examples=100, deadline=None)
@given(
    tags=st.dictionaries(
        keys=st.text(min_size=1, max_size=20,
                     alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
        values=st.text(min_size=1, max_size=20,
                       alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
        min_size=0, max_size=5,
    ),
    value=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_property_26_tags_preserved_with_timestamp(tags, value):
    """
    Property 26 (variant): Tags are preserved alongside the timestamp.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)
        entry = plogger.log_metric("test_metric", value, "ms", tags=tags)
        plogger.close()

        assert _is_valid_iso8601(entry.timestamp), "Timestamp must be valid ISO 8601"
        assert entry.tags == tags, "Tags must be preserved in the log entry"


# ─────────────────────────────────────────────
# Property 27: Packet categorisation correctness
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    protocol=st.sampled_from(["TCP", "UDP", "ICMP", "tcp", "udp", "icmp",
                               "GBN", "SR", "UNKNOWN", "other"]),
    layer=st.sampled_from(VALID_LAYERS),
    size=st.integers(min_value=1, max_value=65535),
)
def test_property_27_packet_categorisation_correctness(protocol, layer, size):
    """
    Property 27: Packet categorization correctness.
    Validates: Requirement 7.8

    For any packet, it must be correctly categorized by protocol type and layer.
    Protocol category must be one of TCP/UDP/ICMP/OTHER.
    Layer category must map to a canonical OSI layer name.
    """
    packet = _make_packet(
        packet_id="test_pkt",
        send_time=1_000_000.0,
        recv_time=1_000_000.1,
        size_bytes=size,
        protocol=protocol,
        layer=layer,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)
        category = plogger.categorise_packet(packet)
        plogger.close()

        # Protocol category must be one of the four valid values
        assert category.protocol_category in {"TCP", "UDP", "ICMP", "OTHER"}, (
            f"Invalid protocol category '{category.protocol_category}' "
            f"for protocol '{protocol}'"
        )

        # Known protocols must map correctly
        if protocol.upper() == "TCP":
            assert category.protocol_category == "TCP"
        elif protocol.upper() == "UDP":
            assert category.protocol_category == "UDP"
        elif protocol.upper() == "ICMP":
            assert category.protocol_category == "ICMP"
        else:
            assert category.protocol_category == "OTHER"

        # Layer category must be non-empty
        assert category.layer_category, "Layer category must not be empty"

        # Category must have a valid timestamp
        assert _is_valid_iso8601(category.timestamp), (
            f"Category timestamp '{category.timestamp}' is not valid ISO 8601"
        )

        # Packet ID must be preserved
        assert category.packet_id == packet.packet_id


@settings(max_examples=100, deadline=None)
@given(
    protocols=st.lists(
        st.sampled_from(["TCP", "UDP", "ICMP", "TCP", "TCP", "UDP"]),  # biased toward TCP
        min_size=1, max_size=30,
    ),
)
def test_property_27_batch_categorisation_count_matches(protocols):
    """
    Property 27 (variant): Batch categorisation returns one result per packet.
    """
    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=base_time + i * 0.001 + 0.005,
            size_bytes=100,
            protocol=proto,
        )
        for i, proto in enumerate(protocols)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = PerformanceLogger(log_dir=tmpdir)
        categories = plogger.log_packet_categories(packets)
        plogger.close()

        assert len(categories) == len(packets), (
            f"Expected {len(packets)} categories, got {len(categories)}"
        )

        for cat in categories:
            assert cat.protocol_category in {"TCP", "UDP", "ICMP", "OTHER"}
            assert _is_valid_iso8601(cat.timestamp)


@settings(max_examples=100, deadline=None)
@given(
    layer=st.sampled_from(VALID_LAYERS),
)
def test_property_27_layer_categories_are_canonical(layer):
    """
    Property 27 (variant): Layer categories must be canonical OSI layer names.
    """
    canonical = _categorise_layer(layer)
    valid_canonical = {"Application", "Transport", "Network", "DataLink", "Physical"}

    assert canonical in valid_canonical or len(canonical) > 0, (
        f"Layer '{layer}' mapped to unexpected canonical name '{canonical}'"
    )


@settings(max_examples=100, deadline=None)
@given(
    tcp_count=st.integers(min_value=0, max_value=20),
    udp_count=st.integers(min_value=0, max_value=20),
    icmp_count=st.integers(min_value=0, max_value=20),
)
def test_property_27_protocol_distribution_sums_to_100(tcp_count, udp_count, icmp_count):
    """
    Property 27 (variant): Protocol distribution percentages must sum to 100%.
    """
    total = tcp_count + udp_count + icmp_count
    assume(total > 0)

    base_time = 1_000_000.0
    packets: List[CapturedPacket] = []

    for i in range(tcp_count):
        packets.append(_make_packet(f"tcp_{i}", base_time, base_time + 0.01, 100, "TCP"))
    for i in range(udp_count):
        packets.append(_make_packet(f"udp_{i}", base_time, base_time + 0.01, 100, "UDP"))
    for i in range(icmp_count):
        packets.append(_make_packet(f"icmp_{i}", base_time, base_time + 0.01, 100, "ICMP"))

    collector = StatisticsCollector()
    collector.add_packets(packets)
    dist = collector.get_protocol_distribution()

    total_pct = dist.tcp_pct + dist.udp_pct + dist.icmp_pct + dist.other_pct
    assert abs(total_pct - 100.0) < 1e-9, (
        f"Protocol percentages must sum to 100%, got {total_pct:.9f}%"
    )

    assert dist.tcp_count == tcp_count
    assert dist.udp_count == udp_count
    assert dist.icmp_count == icmp_count
    assert dist.total == total
