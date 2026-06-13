"""
Property-based tests for MetricsCalculator (Task 20.3).

Properties tested:
  - Property 22: Throughput calculation accuracy  (Requirement 7.2)
  - Property 23: Latency measurement accuracy     (Requirement 7.3)
  - Property 24: Packet loss calculation accuracy (Requirement 7.4)
  - Property 25: Retransmission counting accuracy (Requirement 7.5)

Each property uses at least 100 hypothesis examples for statistical confidence.
"""

import time
import math
from typing import List, Optional

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.traffic_analyzer import CapturedPacket
from src.metrics_calculator import MetricsCalculator

# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

calculator = MetricsCalculator()


def _make_packet(
    packet_id: str,
    send_time: float,
    recv_time: Optional[float],
    size_bytes: int,
    is_retransmission: bool = False,
    source: str = "192.168.1.1",
    destination: str = "192.168.1.2",
    protocol: str = "TCP",
) -> CapturedPacket:
    """Helper to build a CapturedPacket for tests."""
    return CapturedPacket(
        packet_id=packet_id,
        send_time=send_time,
        recv_time=recv_time,
        size_bytes=size_bytes,
        source=source,
        destination=destination,
        protocol=protocol,
        layer="Transport",
        is_retransmission=is_retransmission,
    )


# ─────────────────────────────────────────────
# Property 22: Throughput = bytes / time
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    sizes=st.lists(st.integers(min_value=1, max_value=65535), min_size=1, max_size=50),
    interval=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_22_throughput_calculation_accuracy(sizes, interval):
    """
    Property 22: Throughput calculation accuracy.
    Validates: Requirement 7.2

    For any set of delivered packets and a given time interval,
    throughput_bps must equal (total_bytes_delivered × 8) / interval.
    """
    assume(interval > 0)

    base_time = 1_000_000.0  # arbitrary epoch anchor
    packets: List[CapturedPacket] = []
    for i, size in enumerate(sizes):
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time,
            recv_time=base_time + interval * 0.5,  # all delivered within interval
            size_bytes=size,
        ))

    result = calculator.calculate_throughput(packets, time_interval_s=interval)

    expected_bytes = sum(sizes)
    expected_bps = (expected_bytes * 8) / interval
    expected_Bps = expected_bytes / interval

    # Throughput formula correctness
    assert result.bytes_delivered == expected_bytes, (
        f"bytes_delivered mismatch: expected {expected_bytes}, got {result.bytes_delivered}"
    )
    assert abs(result.throughput_bps - expected_bps) < 1e-6, (
        f"throughput_bps mismatch: expected {expected_bps:.6f}, got {result.throughput_bps:.6f}"
    )
    assert abs(result.throughput_Bps - expected_Bps) < 1e-6, (
        f"throughput_Bps mismatch: expected {expected_Bps:.6f}, got {result.throughput_Bps:.6f}"
    )

    # Consistency: bps = Bps × 8
    assert abs(result.throughput_bps - result.throughput_Bps * 8) < 1e-9, (
        "throughput_bps must equal throughput_Bps × 8"
    )


@settings(max_examples=100, deadline=None)
@given(
    sizes=st.lists(st.integers(min_value=1, max_value=65535), min_size=1, max_size=30),
    interval=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
    lost_count=st.integers(min_value=0, max_value=10),
)
def test_property_22_throughput_excludes_lost_packets(sizes, interval, lost_count):
    """
    Property 22 (variant): Throughput must only count DELIVERED bytes.
    Lost packets (recv_time=None) must not inflate throughput.
    """
    assume(interval > 0)
    assume(lost_count <= len(sizes))

    base_time = 1_000_000.0
    packets: List[CapturedPacket] = []
    for i, size in enumerate(sizes):
        lost = i < lost_count
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time,
            recv_time=None if lost else base_time + interval * 0.5,
            size_bytes=size,
        ))

    result = calculator.calculate_throughput(packets, time_interval_s=interval)

    delivered_bytes = sum(sizes[lost_count:])
    assert result.bytes_delivered == delivered_bytes, (
        f"Throughput must exclude lost packets: "
        f"expected {delivered_bytes} bytes, got {result.bytes_delivered}"
    )


@settings(max_examples=100, deadline=None)
@given(
    interval=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_22_throughput_empty_session(interval):
    """
    Property 22 (edge): Empty packet list → zero throughput regardless of interval.
    """
    result = calculator.calculate_throughput([], time_interval_s=interval)
    assert result.bytes_delivered == 0
    assert result.throughput_bps == 0.0
    assert result.throughput_Bps == 0.0


# ─────────────────────────────────────────────
# Property 23: Latency = recv_time − send_time
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    delays_ms=st.lists(
        st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=50,
    )
)
def test_property_23_latency_measurement_accuracy(delays_ms):
    """
    Property 23: Latency measurement accuracy.
    Validates: Requirement 7.3

    For any packet, measured latency must equal (recv_time - send_time) in ms.
    """
    assume(all(d >= 0 for d in delays_ms))

    base_send = 1_000_000.0
    packets: List[CapturedPacket] = []
    for i, delay_ms in enumerate(delays_ms):
        send = base_send + i * 0.001
        recv = send + delay_ms / 1000.0
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=send,
            recv_time=recv,
            size_bytes=100,
        ))

    result = calculator.calculate_latency(packets)

    assert len(result.per_packet_ms) == len(delays_ms), (
        "per_packet_ms length must match number of delivered packets"
    )

    for i, (measured, expected) in enumerate(zip(result.per_packet_ms, delays_ms)):
        assert abs(measured - expected) < 1e-6, (
            f"Packet {i}: latency mismatch — expected {expected:.6f} ms, got {measured:.6f} ms"
        )

    # Aggregate correctness
    if delays_ms:
        import statistics as _stats
        assert abs(result.mean_ms - _stats.mean(delays_ms)) < 1e-6, "mean_ms incorrect"
        assert abs(result.min_ms - min(delays_ms)) < 1e-6, "min_ms incorrect"
        assert abs(result.max_ms - max(delays_ms)) < 1e-6, "max_ms incorrect"


@settings(max_examples=100, deadline=None)
@given(
    delays_ms=st.lists(
        st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=30,
    ),
    lost_count=st.integers(min_value=0, max_value=5),
)
def test_property_23_latency_excludes_lost_packets(delays_ms, lost_count):
    """
    Property 23 (variant): Lost packets (recv_time=None) must not appear in latency results.
    """
    assume(lost_count <= len(delays_ms))

    base_send = 1_000_000.0
    packets: List[CapturedPacket] = []
    for i, delay_ms in enumerate(delays_ms):
        send = base_send + i * 0.001
        lost = i < lost_count
        recv = None if lost else send + delay_ms / 1000.0
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=send,
            recv_time=recv,
            size_bytes=100,
        ))

    result = calculator.calculate_latency(packets)

    expected_count = len(delays_ms) - lost_count
    assert len(result.per_packet_ms) == expected_count, (
        f"Latency list should contain only delivered-packet latencies: "
        f"expected {expected_count}, got {len(result.per_packet_ms)}"
    )


@settings(max_examples=100, deadline=None)
@given(st.just([]))  # Edge-case fixture
def test_property_23_latency_empty_session(_):
    """Property 23 (edge): Empty packet list → all latency values zero."""
    result = calculator.calculate_latency([])
    assert result.per_packet_ms == []
    assert result.mean_ms == 0.0
    assert result.min_ms == 0.0
    assert result.max_ms == 0.0


# ─────────────────────────────────────────────
# Property 24: Packet loss = (lost / sent) × 100
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    total=st.integers(min_value=1, max_value=200),
    lost=st.integers(min_value=0, max_value=200),
)
def test_property_24_packet_loss_calculation_accuracy(total, lost):
    """
    Property 24: Packet loss calculation accuracy.
    Validates: Requirement 7.4

    For any session, loss_percentage = (packets_lost / packets_sent) × 100.
    """
    assume(lost <= total)

    base_time = 1_000_000.0
    packets: List[CapturedPacket] = []
    for i in range(total):
        is_lost = i < lost
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=None if is_lost else base_time + i * 0.001 + 0.01,
            size_bytes=100,
        ))

    result = calculator.calculate_packet_loss(packets)

    expected_pct = (lost / total) * 100.0

    assert result.packets_sent == total, (
        f"packets_sent mismatch: expected {total}, got {result.packets_sent}"
    )
    assert result.packets_lost == lost, (
        f"packets_lost mismatch: expected {lost}, got {result.packets_lost}"
    )
    assert abs(result.loss_percentage - expected_pct) < 1e-9, (
        f"loss_percentage mismatch: expected {expected_pct:.9f}%, "
        f"got {result.loss_percentage:.9f}%"
    )


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=1, max_value=100))
def test_property_24_zero_loss_when_all_received(total):
    """Property 24 (variant): When all packets are received, loss must be exactly 0%."""
    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=base_time + i * 0.001 + 0.01,
            size_bytes=100,
        )
        for i in range(total)
    ]
    result = calculator.calculate_packet_loss(packets)
    assert result.loss_percentage == 0.0, "No loss when all packets received"


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=1, max_value=100))
def test_property_24_100_percent_loss_when_all_dropped(total):
    """Property 24 (variant): When all packets are lost, loss must be exactly 100%."""
    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=None,
            size_bytes=100,
        )
        for i in range(total)
    ]
    result = calculator.calculate_packet_loss(packets)
    assert result.loss_percentage == 100.0, "100% loss when all packets dropped"


@settings(max_examples=100, deadline=None)
@given(st.just(0))
def test_property_24_empty_session_no_division_by_zero(_):
    """Property 24 (edge): Empty session → 0% loss, no ZeroDivisionError."""
    result = calculator.calculate_packet_loss([])
    assert result.packets_sent == 0
    assert result.packets_lost == 0
    assert result.loss_percentage == 0.0


# ─────────────────────────────────────────────
# Property 25: Retransmission count = actual retransmissions
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    total=st.integers(min_value=1, max_value=200),
    retransmit_count=st.integers(min_value=0, max_value=200),
)
def test_property_25_retransmission_counting_accuracy(total, retransmit_count):
    """
    Property 25: Retransmission counting accuracy.
    Validates: Requirement 7.5

    For any session, the reported retransmission_count must equal the actual
    number of packets with is_retransmission=True.
    """
    assume(retransmit_count <= total)

    base_time = 1_000_000.0
    packets: List[CapturedPacket] = []
    for i in range(total):
        is_retx = i < retransmit_count
        packets.append(_make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=base_time + i * 0.001 + 0.01,
            size_bytes=100,
            is_retransmission=is_retx,
        ))

    result = calculator.calculate_retransmissions(packets)

    assert result.total_packets == total, (
        f"total_packets mismatch: expected {total}, got {result.total_packets}"
    )
    assert result.retransmission_count == retransmit_count, (
        f"retransmission_count mismatch: expected {retransmit_count}, "
        f"got {result.retransmission_count}"
    )

    expected_rate = retransmit_count / total
    assert abs(result.retransmission_rate - expected_rate) < 1e-9, (
        f"retransmission_rate mismatch: expected {expected_rate:.9f}, "
        f"got {result.retransmission_rate:.9f}"
    )


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=1, max_value=100))
def test_property_25_no_retransmissions_when_none_flagged(total):
    """Property 25 (variant): retransmission_count = 0 when no packet is flagged."""
    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=base_time + i * 0.001 + 0.01,
            size_bytes=100,
            is_retransmission=False,
        )
        for i in range(total)
    ]
    result = calculator.calculate_retransmissions(packets)
    assert result.retransmission_count == 0
    assert result.retransmission_rate == 0.0


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=1, max_value=100))
def test_property_25_all_retransmissions_when_all_flagged(total):
    """Property 25 (variant): retransmission_count = total when all packets are flagged."""
    base_time = 1_000_000.0
    packets = [
        _make_packet(
            packet_id=f"pkt_{i}",
            send_time=base_time + i * 0.001,
            recv_time=base_time + i * 0.001 + 0.01,
            size_bytes=100,
            is_retransmission=True,
        )
        for i in range(total)
    ]
    result = calculator.calculate_retransmissions(packets)
    assert result.retransmission_count == total
    assert abs(result.retransmission_rate - 1.0) < 1e-9


@settings(max_examples=100, deadline=None)
@given(st.just(0))
def test_property_25_empty_session(_):
    """Property 25 (edge): Empty session → retransmission_count = 0."""
    result = calculator.calculate_retransmissions([])
    assert result.total_packets == 0
    assert result.retransmission_count == 0
    assert result.retransmission_rate == 0.0
