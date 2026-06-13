"""
Property-based tests for the Optimization Module (Task 21).

Properties tested:
  - Property 28: Optimization triggers on congestion    (Requirements 8.2, 8.3, 8.4)
  - Property 29: Optimization decision logging          (Requirement 8.5)
  - Property 30: Metric-driven optimization             (Requirement 8.6)
  - Property 31: Performance measurement around optimization (Requirement 8.7)

Each property uses at least 100 hypothesis examples.
"""

import tempfile
import time
from typing import List

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.optimization_module import (
    NetworkMetrics,
    NetworkCondition,
    OptimizationAction,
    ConditionMonitor,
    FlowOptimizer,
    RouteOptimizer,
    OptimizationModule,
)
from src.decision_logger import DecisionLogger


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _metrics(
    loss_pct: float = 0.0,
    latency_ms: float = 10.0,
    throughput_bps: float = 1_000_000.0,
    retransmissions: int = 0,
    jitter_ms: float = 1.0,
) -> NetworkMetrics:
    return NetworkMetrics(
        loss_pct=loss_pct,
        latency_mean_ms=latency_ms,
        latency_p95_ms=latency_ms * 1.5,
        throughput_bps=throughput_bps,
        retransmissions=retransmissions,
        jitter_mean_ms=jitter_ms,
        timestamp=time.time(),
    )


# ─────────────────────────────────────────────
# Property 30: Metric-driven optimization
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    latency_ms=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
)
def test_property_30_metric_driven_optimization_triggers_only_on_threshold(
    loss_pct, latency_ms
):
    """
    Property 30: Metric-driven optimization.
    Validates: Requirement 8.6

    Optimization must trigger if and only if actual metric values exceed
    configured thresholds. It must NOT trigger on normal conditions.
    """
    monitor = ConditionMonitor(
        congestion_loss_pct=5.0,
        high_loss_pct=10.0,
        high_latency_ms=200.0,
        congestion_latency_ms=100.0,
    )
    metrics = _metrics(loss_pct=loss_pct, latency_ms=latency_ms)
    result  = monitor.check(metrics)

    should_trigger = (
        loss_pct >= 5.0 or latency_ms >= 100.0
    )

    assert result.triggered == should_trigger, (
        f"triggered={result.triggered} but should_trigger={should_trigger} "
        f"for loss={loss_pct:.2f}%, latency={latency_ms:.2f}ms"
    )

    # When not triggered → condition must be NORMAL
    if not result.triggered:
        assert result.condition == NetworkCondition.NORMAL, (
            f"Condition should be NORMAL when not triggered, got {result.condition}"
        )

    # When triggered → condition must NOT be NORMAL
    if result.triggered:
        assert result.condition != NetworkCondition.NORMAL, (
            "Condition must not be NORMAL when triggered"
        )


@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_30_optimization_module_acts_only_when_enabled(loss_pct):
    """
    Property 30 (variant): When disabled, module detects conditions but takes NO action.
    Validates: Requirements 8.6, 8.8
    """
    # Disabled module
    module_disabled = OptimizationModule(enabled=False)
    decision = module_disabled.evaluate(_metrics(loss_pct=loss_pct))
    assert decision is None, (
        "Disabled module must not make decisions even on bad metrics"
    )

    # Enabled module — same metrics should trigger
    module_enabled = OptimizationModule(enabled=True)
    decision = module_enabled.evaluate(_metrics(loss_pct=loss_pct))
    assert decision is not None, (
        f"Enabled module must act on loss={loss_pct:.2f}% (>= 5%)"
    )


@settings(max_examples=100, deadline=None)
@given(
    latency_ms=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_30_normal_conditions_never_trigger(latency_ms):
    """
    Property 30 (variant): Normal metric values must never trigger optimization.
    """
    assume(latency_ms < 100.0)  # Below congestion threshold

    module = OptimizationModule(enabled=True)
    decision = module.evaluate(_metrics(loss_pct=0.0, latency_ms=latency_ms))
    assert decision is None, (
        f"Normal metrics (loss=0%, latency={latency_ms:.2f}ms) must not trigger"
    )


# ─────────────────────────────────────────────
# Property 28: Optimization triggers on congestion
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_28_congestion_triggers_window_reduction(loss_pct):
    """
    Property 28: Optimization triggers on congestion.
    Validates: Requirements 8.2, 8.3, 8.4

    When loss >= congestion threshold, optimization must reduce the window size.
    """
    flow = FlowOptimizer(initial_window=16, min_window=1, max_window=64)
    initial_window = flow.get_window_size()

    new_window = flow.optimize_for_loss(loss_pct)

    assert new_window < initial_window or new_window == flow.min_window, (
        f"Window must be reduced on loss={loss_pct:.2f}%: "
        f"initial={initial_window}, new={new_window}"
    )
    assert new_window >= flow.min_window, (
        f"Window must never go below min_window={flow.min_window}"
    )


@settings(max_examples=100, deadline=None)
@given(
    latency_ms=st.floats(min_value=200.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    multiplier=st.floats(min_value=1.5, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_property_28_high_latency_adjusts_timeout(latency_ms, multiplier):
    """
    Property 28 (variant): High latency must trigger timeout adjustment.
    Validates: Requirement 8.4
    """
    flow = FlowOptimizer()
    timeout_ms = flow.adjust_timeout(latency_ms, multiplier)

    expected_min = latency_ms * multiplier
    assert timeout_ms >= expected_min or timeout_ms >= 100.0, (
        f"Timeout must be >= latency*multiplier or >= 100ms: "
        f"latency={latency_ms:.1f}ms, multiplier={multiplier:.2f}, "
        f"timeout={timeout_ms:.1f}ms"
    )
    assert timeout_ms >= 100.0, "Timeout must be at least 100ms"


@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    n_routes=st.integers(min_value=2, max_value=5),
)
def test_property_28_congestion_triggers_route_change(loss_pct, n_routes):
    """
    Property 28 (variant): Congestion with multiple routes must trigger route change.
    Validates: Requirement 8.2
    """
    route_opt = RouteOptimizer()
    routes = [
        (f"hop_{i}", float(i + 1), float(i * 10 + 10))
        for i in range(n_routes)
    ]
    route_opt.register_routes("dest_1", routes)
    initial_route = route_opt.get_active_route("dest_1")

    new_route = route_opt.optimize_for_congestion("dest_1")

    assert new_route is not None, "Should find an alternate route"
    assert new_route != initial_route, (
        "Route must change on congestion when alternatives exist"
    )


@settings(max_examples=100, deadline=None)
@given(
    latency_values=st.lists(
        st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        min_size=2, max_size=5,
    )
)
def test_property_28_latency_optimization_picks_lowest(latency_values):
    """
    Property 28 (variant): Latency optimization must select the lowest-latency route.
    Validates: Requirement 8.4
    """
    route_opt = RouteOptimizer()
    routes = [
        (f"hop_{i}", 1.0, lat)
        for i, lat in enumerate(latency_values)
    ]
    route_opt.register_routes("dest_1", routes)

    selected = route_opt.optimize_for_latency("dest_1")
    min_latency_hop = min(routes, key=lambda r: r[2])[0]

    assert selected == min_latency_hop, (
        f"Should select lowest-latency hop '{min_latency_hop}', got '{selected}'"
    )


# ─────────────────────────────────────────────
# Property 29: Optimization decision logging
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    latency_ms=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_every_decision_is_logged(loss_pct, latency_ms):
    """
    Property 29: Optimization decision logging.
    Validates: Requirement 8.5

    Every optimization decision must be logged with condition, metrics, and action.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        module = OptimizationModule(enabled=True)
        dlogger = DecisionLogger(log_dir=tmpdir)

        decision = module.evaluate(_metrics(loss_pct=loss_pct, latency_ms=latency_ms))

        if decision is not None:
            entry = dlogger.log_decision(decision)
            dlogger.close()

            # Every field must be populated
            assert entry.decision_id == decision.decision_id
            assert entry.condition   == decision.condition.value
            assert entry.action      == decision.action.value
            assert entry.timestamp,  "Log entry must have a timestamp"
            assert entry.trigger_metrics, "Trigger metrics must be logged"

            # Metrics must match what triggered the decision
            logged_loss = entry.trigger_metrics.get("loss_pct")
            assert logged_loss is not None, "loss_pct must appear in trigger_metrics"
            assert abs(logged_loss - loss_pct) < 1e-9, (
                f"Logged loss {logged_loss} must match trigger loss {loss_pct}"
            )


@settings(max_examples=100, deadline=None)
@given(
    n_triggers=st.integers(min_value=1, max_value=10),
    loss_pct=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_log_count_matches_decisions(n_triggers, loss_pct):
    """
    Property 29 (variant): Number of log entries must equal number of decisions made.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        module  = OptimizationModule(enabled=True)
        dlogger = DecisionLogger(log_dir=tmpdir)

        decisions_made = 0
        for _ in range(n_triggers):
            decision = module.evaluate(_metrics(loss_pct=loss_pct))
            if decision:
                dlogger.log_decision(decision)
                decisions_made += 1

        dlogger.close()
        entries = dlogger.get_decision_entries()

        assert len(entries) == decisions_made, (
            f"Log entry count {len(entries)} must equal decisions made {decisions_made}"
        )


@settings(max_examples=100, deadline=None)
@given(
    loss_pct=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_log_file_contains_all_decisions(loss_pct):
    """
    Property 29 (variant): Every decision must appear in the persisted log file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        module  = OptimizationModule(enabled=True)
        dlogger = DecisionLogger(log_dir=tmpdir)

        decision = module.evaluate(_metrics(loss_pct=loss_pct))
        if decision:
            dlogger.log_decision(decision)

        log_records = dlogger.read_log_file()
        dlogger.close()

        decision_records = [r for r in log_records if r.get("type") == "decision"]

        if decision:
            assert len(decision_records) >= 1, "Decision must appear in log file"
            record = decision_records[0]
            assert "condition" in record,        "Log record must contain condition"
            assert "action" in record,           "Log record must contain action"
            assert "trigger_metrics" in record,  "Log record must contain trigger_metrics"
            assert "timestamp" in record,        "Log record must contain timestamp"


# ─────────────────────────────────────────────
# Property 31: Performance measurement around optimization
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    before_loss=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    after_loss=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_31_before_after_measurement_recorded(before_loss, after_loss):
    """
    Property 31: Performance measurement around optimization.
    Validates: Requirement 8.7

    For any optimization decision, before and after metrics must be recorded
    and improvement percentages correctly calculated.
    """
    module = OptimizationModule(enabled=True)

    before_metrics = _metrics(loss_pct=before_loss, latency_ms=10.0)
    decision = module.evaluate(before_metrics)
    assume(decision is not None)

    module.record_before(decision.decision_id, before_metrics)

    after_metrics = _metrics(loss_pct=after_loss, latency_ms=10.0)
    module.record_after(decision.decision_id, after_metrics)

    measurements = module.get_measurements()
    assert len(measurements) == 1

    m = measurements[0]
    assert m.decision_id == decision.decision_id
    assert m.before is not None
    assert m.after  is not None

    # Improvement % for loss: positive means loss went down (better)
    loss_improvement = m.improvement_pct.get("loss_pct", 0.0)

    if after_loss < before_loss:
        assert loss_improvement > 0, (
            f"Loss improved ({before_loss:.2f}% → {after_loss:.2f}%) "
            f"so improvement_pct should be positive, got {loss_improvement:.4f}"
        )
    elif after_loss > before_loss:
        assert loss_improvement < 0, (
            f"Loss degraded ({before_loss:.2f}% → {after_loss:.2f}%) "
            f"so improvement_pct should be negative, got {loss_improvement:.4f}"
        )


@settings(max_examples=100, deadline=None)
@given(
    before_loss=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    after_loss=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_property_31_effectiveness_report_generated(before_loss, after_loss):
    """
    Property 31 (variant): Effectiveness report must be generated after measurements.
    Validates: Requirement 8.7
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        module  = OptimizationModule(enabled=True)
        dlogger = DecisionLogger(log_dir=tmpdir)

        before  = _metrics(loss_pct=before_loss)
        decision = module.evaluate(before)
        assume(decision is not None)

        module.record_before(decision.decision_id, before)
        module.record_after(decision.decision_id, _metrics(loss_pct=after_loss))

        # Log the measurement
        for m in module.get_measurements():
            dlogger.log_effectiveness(m)

        report = dlogger.generate_report()
        dlogger.close()

        assert report.total_measured >= 1, "Report must count measured decisions"
        assert report.timestamp,           "Report must have a timestamp"
        assert report.summary,             "Report must have a summary"

        # Since loss improved, avg loss improvement should be positive
        assert report.avg_loss_improvement_pct > 0, (
            f"Loss improved so report avg should be positive, "
            f"got {report.avg_loss_improvement_pct:.4f}"
        )


@settings(max_examples=100, deadline=None)
@given(
    n_decisions=st.integers(min_value=1, max_value=10),
    loss_pct=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
)
def test_property_31_report_decision_count_matches(n_decisions, loss_pct):
    """
    Property 31 (variant): Report total_decisions must match actual logged decisions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dlogger = DecisionLogger(log_dir=tmpdir)
        module  = OptimizationModule(enabled=True)

        logged = 0
        for _ in range(n_decisions):
            d = module.evaluate(_metrics(loss_pct=loss_pct))
            if d:
                dlogger.log_decision(d)
                logged += 1

        report = dlogger.generate_report()
        dlogger.close()

        assert report.total_decisions == logged, (
            f"Report total_decisions={report.total_decisions} "
            f"must equal logged decisions={logged}"
        )
