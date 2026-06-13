"""
Property-based tests for Simulation Control and Experiment Management (Task 23).

Properties tested:
  - Property 33: Traffic generation parameter accuracy  (Requirement 10.2)
  - Property 36: Experiment reproducibility             (Requirement 10.7)

100 examples per property.
"""

import random
import tempfile
import time
from typing import Any, Dict, List, Optional

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.traffic_generator import (
    TrafficGenerator, FlowConfig, TrafficPattern, CongestionLevel,
)
from src.experiment_manager import ExperimentManager, ExperimentConfig
from src.simulation_controller import (
    SimulationController, SimulationConfig, SimulationState, SpeedMode,
)


# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

def _make_flow(
    flow_id: str,
    pattern: str,
    rate_bps: float,
    packet_size: int = 1024,
    burst_prob: float = 0.3,
    burst_mult: float = 5.0,
    period_s: float = 10.0,
    congestion: str = "none",
    seed: int = 42,
) -> FlowConfig:
    return FlowConfig(
        flow_id=flow_id,
        source="10.0.0.1",
        destination="10.0.0.2",
        pattern=pattern,
        rate_bps=rate_bps,
        packet_size_bytes=packet_size,
        burst_prob=burst_prob,
        burst_mult=burst_mult,
        period_s=period_s,
        protocol="TCP",
        congestion_level=congestion,
        random_seed=seed,
    )


def _simple_experiment_fn(
    config: ExperimentConfig, rng: random.Random
) -> Dict[str, Any]:
    """Deterministic experiment: same seed → same results."""
    n_packets = config.parameters.get("n_packets", 100)
    loss_pct  = config.parameters.get("loss_pct",  0.0)
    results   = [rng.gauss(50.0, 10.0) for _ in range(n_packets)]
    mean_lat  = sum(results) / len(results)
    lost      = sum(1 for _ in range(n_packets) if rng.random() < loss_pct / 100.0)
    return {
        "mean_latency_ms": round(mean_lat, 6),
        "packets_sent":    n_packets,
        "packets_lost":    lost,
        "loss_pct":        round(lost / n_packets * 100, 6),
        "throughput_bps":  round(rng.uniform(1e5, 1e6), 6),
    }


# ─────────────────────────────────────────────
# Property 33: Traffic generation accuracy
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    rate_bps=st.floats(min_value=8.0, max_value=1e8,
                       allow_nan=False, allow_infinity=False),
    packet_size=st.integers(min_value=64, max_value=9000),
    n_ticks=st.integers(min_value=1, max_value=50),
)
def test_property_33_constant_traffic_rate_accuracy(rate_bps, packet_size, n_ticks):
    """
    Property 33: Traffic generation parameter accuracy.
    Validates: Requirement 10.2

    For CONSTANT pattern, packets per tick = rate_bps / (packet_size * 8).
    """
    gen  = TrafficGenerator()
    flow = _make_flow("f1", TrafficPattern.CONSTANT.value,
                      rate_bps, packet_size, seed=42)
    gen.add_flow(flow)

    expected_per_tick = max(1, int(rate_bps / (packet_size * 8)))

    for tick in range(n_ticks):
        pkts = gen.generate_flow_tick("f1", tick, float(tick))
        assert len(pkts) == expected_per_tick, (
            f"Tick {tick}: expected {expected_per_tick} packets, "
            f"got {len(pkts)} (rate={rate_bps:.0f}bps, size={packet_size}B)"
        )
        for p in pkts:
            assert p.size_bytes == packet_size
            assert p.source      == flow.source
            assert p.destination == flow.destination
            assert p.protocol    == flow.protocol


@settings(max_examples=100, deadline=None)
@given(
    burst_prob=st.floats(min_value=0.1, max_value=0.4,
                         allow_nan=False, allow_infinity=False),
    n_ticks=st.integers(min_value=50, max_value=200),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_33_bursty_traffic_has_silence_gaps(burst_prob, n_ticks, seed):
    """
    Property 33 (variant): BURSTY pattern with burst_prob <= 0.4 must have
    silent ticks (zero packets) between bursts.
    With burst_prob<=0.4 and n_ticks>=50 we expect at least 40% silence.
    """
    assume(burst_prob <= 0.4)

    gen  = TrafficGenerator()
    flow = _make_flow("f1", TrafficPattern.BURSTY.value,
                      rate_bps=1_000_000.0,
                      burst_prob=burst_prob,
                      burst_mult=3.0,
                      seed=seed)
    gen.add_flow(flow)

    tick_counts = [
        len(gen.generate_flow_tick("f1", t, float(t)))
        for t in range(n_ticks)
    ]
    silent_ticks = sum(1 for c in tick_counts if c == 0)
    silent_ratio = silent_ticks / n_ticks

    # With burst_prob<=0.4 and n_ticks>=50, silence ratio must be >=0.4
    assert silent_ratio >= 0.4, (
        f"BURSTY burst_prob={burst_prob:.2f} over {n_ticks} ticks "
        f"should have >=40% silent, got {silent_ratio:.2%} ({silent_ticks}/{n_ticks})"
    )


@settings(max_examples=100, deadline=None)
@given(
    rate_bps=st.floats(min_value=8000.0, max_value=1e7,
                       allow_nan=False, allow_infinity=False),
    congestion=st.sampled_from(["none", "low", "medium", "high"]),
    n_ticks=st.integers(min_value=20, max_value=100),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_33_congestion_loss_rate_approximate(rate_bps, congestion, n_ticks, seed):
    """
    Property 33 (variant): Congestion must not increase packet count vs no congestion.
    """
    gen_clean = TrafficGenerator()
    gen_clean.add_flow(_make_flow("f1", TrafficPattern.CONSTANT.value,
                                  rate_bps, congestion="none", seed=seed))
    clean_count = sum(
        len(gen_clean.generate_flow_tick("f1", t, float(t)))
        for t in range(n_ticks)
    )

    gen_cong = TrafficGenerator()
    gen_cong.add_flow(_make_flow("f1", TrafficPattern.CONSTANT.value,
                                 rate_bps, congestion=congestion, seed=seed))
    cong_count = sum(
        len(gen_cong.generate_flow_tick("f1", t, float(t)))
        for t in range(n_ticks)
    )

    assert cong_count <= clean_count, (
        f"Congestion='{congestion}' must not increase packets: "
        f"clean={clean_count}, congested={cong_count}"
    )


@settings(max_examples=100, deadline=None)
@given(
    n_flows=st.integers(min_value=1, max_value=5),
    rate_bps=st.floats(min_value=8000.0, max_value=1e6,
                       allow_nan=False, allow_infinity=False),
)
def test_property_33_multiple_flows_generated_independently(n_flows, rate_bps):
    """
    Property 33 (variant): generate_tick() total must equal sum of per-flow totals.
    """
    gen = TrafficGenerator()
    for i in range(n_flows):
        gen.add_flow(_make_flow(f"flow_{i}", TrafficPattern.CONSTANT.value,
                                rate_bps, seed=i * 100))

    total_all      = len(gen.generate_tick(0, 0.0))
    per_flow_total = 0
    for i in range(n_flows):
        g2 = TrafficGenerator()
        g2.add_flow(_make_flow(f"flow_{i}", TrafficPattern.CONSTANT.value,
                               rate_bps, seed=i * 100))
        per_flow_total += len(g2.generate_flow_tick(f"flow_{i}", 0, 0.0))

    assert total_all == per_flow_total, (
        f"Total packets ({total_all}) must equal sum of per-flow ({per_flow_total})"
    )


# ─────────────────────────────────────────────
# Property 36: Experiment reproducibility
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1),
    n_packets=st.integers(min_value=10, max_value=200),
    loss_pct=st.floats(min_value=0.0, max_value=50.0,
                       allow_nan=False, allow_infinity=False),
)
def test_property_36_same_seed_produces_identical_results(seed, n_packets, loss_pct):
    """
    Property 36: Experiment reproducibility.
    Validates: Requirement 10.7

    Two runs with the same seed must produce identical metrics.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ExperimentManager(results_dir=tmpdir)
        config  = ExperimentConfig(
            experiment_id="repro_test",
            parameters={"n_packets": n_packets, "loss_pct": loss_pct},
            random_seed=seed,
        )
        r1 = manager.run_experiment(config, _simple_experiment_fn)
        r2 = manager.run_experiment(config, _simple_experiment_fn)

        assert r1.success and r2.success
        for key in r1.metrics:
            assert r1.metrics[key] == r2.metrics[key], (
                f"Metric '{key}' differs with seed={seed}"
            )


@settings(max_examples=100, deadline=None)
@given(
    seed1=st.integers(min_value=0, max_value=2**31 - 1),
    seed2=st.integers(min_value=0, max_value=2**31 - 1),
    n_packets=st.integers(min_value=50, max_value=200),
)
def test_property_36_different_seeds_may_differ(seed1, seed2, n_packets):
    """Each seed must produce internally consistent results."""
    assume(seed1 != seed2)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ExperimentManager(results_dir=tmpdir)
        c1 = ExperimentConfig("s1", {"n_packets": n_packets, "loss_pct": 10.0}, seed1)
        c2 = ExperimentConfig("s2", {"n_packets": n_packets, "loss_pct": 10.0}, seed2)

        r1a = manager.run_experiment(c1, _simple_experiment_fn)
        r1b = manager.run_experiment(c1, _simple_experiment_fn)
        r2a = manager.run_experiment(c2, _simple_experiment_fn)
        r2b = manager.run_experiment(c2, _simple_experiment_fn)

        assert r1a.metrics == r1b.metrics, "Same seed must give same result"
        assert r2a.metrics == r2b.metrics, "Same seed must give same result"


@settings(max_examples=100, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1),
    n_packets=st.integers(min_value=10, max_value=200),
)
def test_property_36_n_runs_all_identical_with_same_seed(seed, n_packets):
    """check_reproducibility() must return True for any fixed seed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ExperimentManager(results_dir=tmpdir)
        config  = ExperimentConfig(
            "repro_verify",
            {"n_packets": n_packets, "loss_pct": 5.0},
            seed,
        )
        assert manager.check_reproducibility(config, _simple_experiment_fn, n_runs=3)


@settings(max_examples=100, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1),
    sweep_values=st.lists(
        st.floats(min_value=0.0, max_value=50.0,
                  allow_nan=False, allow_infinity=False),
        min_size=2, max_size=4, unique=True,
    ),
)
def test_property_36_parameter_sweep_reproducible(seed, sweep_values):
    """Same sweep with same seed must yield identical results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = ExperimentConfig("base", {"n_packets": 50}, seed)

        m1     = ExperimentManager(results_dir=tmpdir)
        batch1 = m1.parameter_sweep(base, {"loss_pct": sweep_values}, _simple_experiment_fn)

        m2     = ExperimentManager(results_dir=tmpdir)
        batch2 = m2.parameter_sweep(base, {"loss_pct": sweep_values}, _simple_experiment_fn)

        assert batch1.total_experiments == batch2.total_experiments
        for r1, r2 in zip(batch1.results, batch2.results):
            assert r1.metrics == r2.metrics, (
                f"Sweep mismatch for params={r1.parameters}"
            )


# ─────────────────────────────────────────────
# SimulationController tests
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    multiplier=st.floats(min_value=0.1, max_value=100.0,
                         allow_nan=False, allow_infinity=False),
)
def test_simulation_controller_speed_control(multiplier):
    """Speed setting must be stored correctly."""
    ctrl = SimulationController()
    ctrl.set_fast_forward(multiplier)
    assert ctrl.config.speed_mode       == SpeedMode.FAST_FORWARD.value
    assert abs(ctrl.config.speed_multiplier - max(0.01, multiplier)) < 1e-9


@settings(max_examples=100, deadline=None)
@given(n_steps=st.integers(min_value=1, max_value=20))
def test_simulation_controller_step_count(n_steps):
    """Step mode must advance exactly one tick per step() call."""
    ctrl = SimulationController()
    ctrl._state      = SimulationState.PAUSED
    ctrl._start_time = time.time()

    for i in range(n_steps):
        assert ctrl.step() is True

    assert ctrl.get_tick_count() == n_steps, (
        f"After {n_steps} steps, tick_count={ctrl.get_tick_count()} (expected {n_steps})"
    )


@settings(max_examples=100, deadline=None)
@given(
    tick_count=st.integers(min_value=0, max_value=10000),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_simulation_checkpoint_roundtrip(tick_count, seed):
    """Checkpoint save/load must preserve tick count and seed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctrl = SimulationController(
            SimulationConfig(seed=seed),
            checkpoint_dir=tmpdir,
        )
        ctrl._tick_count = tick_count
        ctrl._start_time = time.time()

        ckpt = ctrl.save_checkpoint(checkpoint_id="test_ckpt")
        assert ckpt.tick_count == tick_count

        ctrl2  = SimulationController(checkpoint_dir=tmpdir)
        loaded = ctrl2.load_checkpoint("test_ckpt")

        assert loaded is not None
        assert loaded.tick_count     == tick_count
        assert ctrl2.get_tick_count() == tick_count
        assert ctrl2.config.seed     == seed
