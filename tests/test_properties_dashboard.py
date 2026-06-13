"""
Property-based tests for the Monitoring Dashboard (Task 22.4).

Properties tested:
  - Property 32: Dashboard update responsiveness (Requirement 9.4)
    For any network change, dashboard should update within 2 seconds.

Each property uses at least 100 hypothesis examples.
"""

import queue
import time
from typing import List

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.dashboard import MetricsAPI, MetricSnapshot, TopologyData, TopologyNode, TopologyLink


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

UPDATE_DEADLINE_S = 2.0   # Requirement 9.4: updates within 2 seconds


def _make_snapshot(
    throughput_bps: float = 1_000_000.0,
    latency_ms: float = 10.0,
    loss_pct: float = 0.0,
    jitter_ms: float = 1.0,
    retransmissions: int = 0,
) -> MetricSnapshot:
    from datetime import datetime, timezone
    return MetricSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        throughput_bps=throughput_bps,
        latency_mean_ms=latency_ms,
        latency_p95_ms=latency_ms * 1.5,
        loss_pct=loss_pct,
        retransmissions=retransmissions,
        jitter_mean_ms=jitter_ms,
    )


# ─────────────────────────────────────────────
# Property 32: Dashboard update responsiveness
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    throughput=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    latency_ms=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    loss_pct=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_32_metrics_update_within_2_seconds(throughput, latency_ms, loss_pct):
    """
    Property 32: Dashboard update responsiveness.
    Validates: Requirement 9.4

    For any network metric change, the dashboard SSE clients must receive
    the update within 2 seconds of it being pushed.
    """
    api = MetricsAPI()
    client_q = api.register_sse_client()

    snap = _make_snapshot(
        throughput_bps=throughput,
        latency_ms=latency_ms,
        loss_pct=loss_pct,
    )

    import json

    t_start = time.perf_counter()
    api.update_metrics(snap)

    # Drain events until we find the 'metrics' one.
    # High-loss snapshots also auto-generate an 'alert' event which
    # may arrive before the 'metrics' event in the queue.
    metrics_found = False
    deadline = time.perf_counter() + UPDATE_DEADLINE_S
    while time.perf_counter() < deadline:
        remaining = deadline - time.perf_counter()
        try:
            payload = client_q.get(timeout=max(remaining, 0.01))
        except queue.Empty:
            break
        data = json.loads(payload)
        if data["type"] == "metrics":
            metrics_found = True
            break

    elapsed = time.perf_counter() - t_start

    assert metrics_found, (
        f"Dashboard did not receive a 'metrics' event within {UPDATE_DEADLINE_S}s "
        f"(elapsed={elapsed:.4f}s)"
    )
    assert elapsed < UPDATE_DEADLINE_S, (
        f"Metrics event took {elapsed:.4f}s — exceeds {UPDATE_DEADLINE_S}s deadline"
    )


@settings(max_examples=100, deadline=None)
@given(
    n_clients=st.integers(min_value=1, max_value=10),
    loss_pct=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_32_all_clients_receive_update_within_deadline(n_clients, loss_pct):
    """
    Property 32 (variant): ALL connected SSE clients must receive the update
    within 2 seconds — not just the first one.
    """
    api = MetricsAPI()
    client_queues = [api.register_sse_client() for _ in range(n_clients)]

    snap = _make_snapshot(loss_pct=loss_pct)

    t_start = time.perf_counter()
    api.update_metrics(snap)
    t_sent = time.perf_counter()

    for i, q in enumerate(client_queues):
        try:
            payload = q.get(timeout=UPDATE_DEADLINE_S)
            elapsed = time.perf_counter() - t_start
            assert elapsed < UPDATE_DEADLINE_S, (
                f"Client {i} received update after {elapsed:.4f}s "
                f"(deadline={UPDATE_DEADLINE_S}s)"
            )
        except queue.Empty:
            pytest.fail(
                f"Client {i}/{n_clients} did not receive update within "
                f"{UPDATE_DEADLINE_S}s"
            )


@settings(max_examples=100, deadline=None)
@given(
    n_updates=st.integers(min_value=1, max_value=20),
    base_loss=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_32_consecutive_updates_all_within_deadline(n_updates, base_loss):
    """
    Property 32 (variant): Each consecutive metric update must arrive
    within the 2-second deadline.
    """
    api = MetricsAPI()
    client_q = api.register_sse_client()

    for i in range(n_updates):
        snap = _make_snapshot(loss_pct=base_loss + i * 0.1)

        t_start = time.perf_counter()
        api.update_metrics(snap)

        try:
            client_q.get(timeout=UPDATE_DEADLINE_S)
            elapsed = time.perf_counter() - t_start
        except queue.Empty:
            pytest.fail(
                f"Update {i+1}/{n_updates} not received within {UPDATE_DEADLINE_S}s"
            )

        assert elapsed < UPDATE_DEADLINE_S, (
            f"Update {i+1} took {elapsed:.4f}s — exceeds deadline"
        )


@settings(max_examples=100, deadline=None)
@given(
    n_nodes=st.integers(min_value=1, max_value=8),
    n_links=st.integers(min_value=0, max_value=10),
)
def test_property_32_topology_update_within_deadline(n_nodes, n_links):
    """
    Property 32 (variant): Topology changes must also reach SSE clients
    within the 2-second deadline.
    """
    api = MetricsAPI()
    client_q = api.register_sse_client()

    nodes = [TopologyNode(node_id=f"N{i}", ip_address=f"10.0.0.{i+1}") for i in range(n_nodes)]

    actual_links = min(n_links, n_nodes - 1) if n_nodes > 1 else 0
    links = [
        TopologyLink(source=f"N{i}", target=f"N{i+1}")
        for i in range(actual_links)
    ]
    topo = TopologyData(nodes=nodes, links=links)

    t_start = time.perf_counter()
    api.update_topology(topo)

    try:
        payload = client_q.get(timeout=UPDATE_DEADLINE_S)
        elapsed = time.perf_counter() - t_start
    except queue.Empty:
        pytest.fail(
            f"Topology update not received within {UPDATE_DEADLINE_S}s"
        )

    assert elapsed < UPDATE_DEADLINE_S, (
        f"Topology update took {elapsed:.4f}s — exceeds deadline"
    )

    import json
    data = json.loads(payload)
    assert data["type"] == "topology", f"Expected type='topology', got '{data['type']}'"


@settings(max_examples=100, deadline=None)
@given(
    message=st.text(min_size=1, max_size=100,
                    alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    severity=st.sampled_from(["info", "warning", "critical"]),
)
def test_property_32_alert_broadcast_within_deadline(message, severity):
    """
    Property 32 (variant): Alerts must be broadcast to SSE clients
    within the 2-second deadline.
    """
    assume(message.strip())

    api = MetricsAPI()
    client_q = api.register_sse_client()

    t_start = time.perf_counter()
    api.add_alert(message.strip(), severity=severity)

    try:
        payload = client_q.get(timeout=UPDATE_DEADLINE_S)
        elapsed = time.perf_counter() - t_start
    except queue.Empty:
        pytest.fail(
            f"Alert not broadcast within {UPDATE_DEADLINE_S}s"
        )

    assert elapsed < UPDATE_DEADLINE_S, (
        f"Alert broadcast took {elapsed:.4f}s — exceeds deadline"
    )

    import json
    data = json.loads(payload)
    assert data["type"] == "alert"
    assert data["data"]["severity"] == severity
    assert data["data"]["message"]  == message.strip()


@settings(max_examples=100, deadline=None)
@given(
    throughput=st.floats(min_value=1000.0, max_value=1e9,
                         allow_nan=False, allow_infinity=False),
)
def test_property_32_metrics_stored_in_history_immediately(throughput):
    """
    Property 32 (variant): After update_metrics(), the new snapshot must
    appear in history immediately (not delayed).
    """
    api = MetricsAPI()
    before_count = api.get_history_count()

    api.update_metrics(_make_snapshot(throughput_bps=throughput))

    after_count = api.get_history_count()
    assert after_count == before_count + 1, (
        f"History must grow by 1 after update: before={before_count}, after={after_count}"
    )

    history = api.get_history(limit=1)
    assert len(history) == 1
    assert abs(history[-1]["throughput_bps"] - throughput) < 1e-6, (
        f"Latest history entry must match the pushed throughput"
    )


@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=10.0, max_value=100.0,
                       allow_nan=False, allow_infinity=False),
)
def test_property_32_high_loss_auto_alert_within_deadline(loss_pct):
    """
    Property 32 (variant): Auto-generated alerts (on threshold breach) must
    also arrive within 2 seconds.
    """
    api = MetricsAPI()
    client_q = api.register_sse_client()

    # Flush the initial metrics event first
    api.update_metrics(_make_snapshot(loss_pct=loss_pct))

    # Drain all events that arrived — collect within deadline
    received_types = []
    deadline = time.perf_counter() + UPDATE_DEADLINE_S
    while time.perf_counter() < deadline:
        try:
            payload = client_q.get(timeout=0.1)
            import json
            received_types.append(json.loads(payload)["type"])
        except queue.Empty:
            break

    # We expect at least a "metrics" event and an "alert" event
    assert "metrics" in received_types, "Metrics event must be broadcast"
    assert "alert" in received_types, (
        f"Auto-alert for loss={loss_pct:.1f}% must be broadcast within {UPDATE_DEADLINE_S}s"
    )
