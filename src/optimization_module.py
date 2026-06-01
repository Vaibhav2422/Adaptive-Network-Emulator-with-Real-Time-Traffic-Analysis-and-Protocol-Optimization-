"""
Optimization Module for the Adaptive Network Emulator.

Provides network condition monitoring, optimization strategies (route + flow),
adaptive behavior control, and before/after performance measurement.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6, 8.8
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Enums and constants
# ─────────────────────────────────────────────

class NetworkCondition(Enum):
    NORMAL      = "normal"
    CONGESTION  = "congestion"
    HIGH_LOSS   = "high_loss"
    HIGH_LATENCY = "high_latency"
    DEGRADED    = "degraded"   # multiple issues at once


class OptimizationAction(Enum):
    NONE                  = "none"
    REDUCE_WINDOW         = "reduce_window"
    INCREASE_WINDOW       = "increase_window"
    CHANGE_ROUTE          = "change_route"
    ADJUST_TIMEOUT        = "adjust_timeout"
    SELECT_LOW_LATENCY_ROUTE = "select_low_latency_route"


# Default thresholds
DEFAULT_CONGESTION_LOSS_PCT   = 5.0    # % packet loss → congestion
DEFAULT_HIGH_LOSS_PCT         = 10.0   # % packet loss → high loss
DEFAULT_HIGH_LATENCY_MS       = 200.0  # ms mean latency → high latency
DEFAULT_CONGESTION_LATENCY_MS = 100.0  # ms mean latency → congestion


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class NetworkMetrics:
    """
    Snapshot of current network performance metrics.
    Used by ConditionMonitor to evaluate thresholds.
    """
    loss_pct: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p95_ms: float = 0.0
    throughput_bps: float = 0.0
    retransmissions: int = 0
    jitter_mean_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MonitorResult:
    """
    Result of a condition monitoring check.

    Attributes:
        condition:      Detected network condition.
        triggered:      True if any threshold was exceeded.
        metric_values:  Snapshot of the metrics that triggered detection.
        details:        Human-readable description.
    """
    condition: NetworkCondition
    triggered: bool
    metric_values: NetworkMetrics
    details: str


@dataclass
class OptimizationDecision:
    """
    A single optimization decision made by the module.

    Attributes:
        decision_id:      Unique identifier.
        timestamp:        When the decision was made (epoch seconds).
        condition:        The condition that triggered optimization.
        action:           The action taken.
        trigger_metrics:  Metric snapshot that caused the trigger.
        parameters:       Action-specific parameters (e.g. new window size).
        enabled:          Whether optimization was active when decision was made.
    """
    decision_id: str
    timestamp: float
    condition: NetworkCondition
    action: OptimizationAction
    trigger_metrics: NetworkMetrics
    parameters: Dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PerformanceMeasurement:
    """Before/after performance snapshot around an optimization event."""
    decision_id: str
    before: NetworkMetrics
    after: Optional[NetworkMetrics] = None
    improvement_pct: Dict[str, float] = field(default_factory=dict)


# ─────────────────────────────────────────────
# ConditionMonitor  (task 21.1)
# ─────────────────────────────────────────────

class ConditionMonitor:
    """
    Monitors network metrics against configurable thresholds.

    Detects: congestion, high packet loss, high latency.

    Validates: Requirements 8.1, 8.6
    """

    def __init__(
        self,
        congestion_loss_pct: float   = DEFAULT_CONGESTION_LOSS_PCT,
        high_loss_pct: float          = DEFAULT_HIGH_LOSS_PCT,
        high_latency_ms: float        = DEFAULT_HIGH_LATENCY_MS,
        congestion_latency_ms: float  = DEFAULT_CONGESTION_LATENCY_MS,
    ):
        self.congestion_loss_pct   = congestion_loss_pct
        self.high_loss_pct         = high_loss_pct
        self.high_latency_ms       = high_latency_ms
        self.congestion_latency_ms = congestion_latency_ms

    def check(self, metrics: NetworkMetrics) -> MonitorResult:
        """
        Evaluate metrics against all thresholds.

        Returns the most severe condition detected.

        Validates: Requirements 8.1, 8.6
        """
        has_congestion = (
            metrics.loss_pct >= self.congestion_loss_pct or
            metrics.latency_mean_ms >= self.congestion_latency_ms
        )
        has_high_loss    = metrics.loss_pct >= self.high_loss_pct
        has_high_latency = metrics.latency_mean_ms >= self.high_latency_ms

        # Determine most severe condition
        if has_high_loss and has_high_latency:
            condition = NetworkCondition.DEGRADED
            details = (
                f"Degraded: loss={metrics.loss_pct:.1f}% "
                f"(>={self.high_loss_pct}%), "
                f"latency={metrics.latency_mean_ms:.1f}ms "
                f"(>={self.high_latency_ms}ms)"
            )
        elif has_high_loss:
            condition = NetworkCondition.HIGH_LOSS
            details = (
                f"High loss: {metrics.loss_pct:.1f}% >= {self.high_loss_pct}%"
            )
        elif has_high_latency:
            condition = NetworkCondition.HIGH_LATENCY
            details = (
                f"High latency: {metrics.latency_mean_ms:.1f}ms "
                f">= {self.high_latency_ms}ms"
            )
        elif has_congestion:
            condition = NetworkCondition.CONGESTION
            details = (
                f"Congestion: loss={metrics.loss_pct:.1f}% or "
                f"latency={metrics.latency_mean_ms:.1f}ms"
            )
        else:
            condition = NetworkCondition.NORMAL
            details = "Network conditions normal"

        triggered = condition != NetworkCondition.NORMAL

        logger.debug("ConditionMonitor: %s — %s", condition.value, details)
        return MonitorResult(
            condition=condition,
            triggered=triggered,
            metric_values=metrics,
            details=details,
        )

    def is_congested(self, metrics: NetworkMetrics) -> bool:
        """Quick check: is the network congested?"""
        return self.check(metrics).condition in (
            NetworkCondition.CONGESTION,
            NetworkCondition.DEGRADED,
        )

    def is_high_loss(self, metrics: NetworkMetrics) -> bool:
        """Quick check: is packet loss above threshold?"""
        return metrics.loss_pct >= self.high_loss_pct

    def is_high_latency(self, metrics: NetworkMetrics) -> bool:
        """Quick check: is latency above threshold?"""
        return metrics.latency_mean_ms >= self.high_latency_ms


# ─────────────────────────────────────────────
# RouteOptimizer  (task 21.3)
# ─────────────────────────────────────────────

class RouteOptimizer:
    """
    Adjusts routing paths in response to network conditions.

    Strategies:
    - Congestion → switch to alternate route
    - High latency → select lowest-latency route

    Validates: Requirements 8.2, 8.4
    """

    def __init__(self):
        # route_table: dest → list of (next_hop, cost, latency_ms)
        self._routes: Dict[str, List[Tuple[str, float, float]]] = {}
        self._active_routes: Dict[str, str] = {}   # dest → current next_hop
        self.optimization_count = 0

    def register_routes(
        self,
        destination: str,
        routes: List[Tuple[str, float, float]],
    ) -> None:
        """
        Register available routes for a destination.

        Args:
            destination: Destination IP / node ID.
            routes:      List of (next_hop, cost, latency_ms) tuples.
        """
        self._routes[destination] = routes
        if routes:
            # Default: pick lowest cost
            best = min(routes, key=lambda r: r[1])
            self._active_routes[destination] = best[0]

    def optimize_for_congestion(self, destination: str) -> Optional[str]:
        """
        Switch to the next-best route to relieve congestion.

        Validates: Requirement 8.2
        """
        routes = self._routes.get(destination, [])
        if len(routes) < 2:
            return None

        current = self._active_routes.get(destination)
        # Pick cheapest route that isn't the current one
        alternatives = [r for r in routes if r[0] != current]
        if not alternatives:
            return None

        best_alt = min(alternatives, key=lambda r: r[1])
        self._active_routes[destination] = best_alt[0]
        self.optimization_count += 1

        logger.info(
            "RouteOptimizer: congestion → switching %s from %s to %s",
            destination, current, best_alt[0],
        )
        return best_alt[0]

    def optimize_for_latency(self, destination: str) -> Optional[str]:
        """
        Select the lowest-latency route.

        Validates: Requirement 8.4
        """
        routes = self._routes.get(destination, [])
        if not routes:
            return None

        best = min(routes, key=lambda r: r[2])   # sort by latency_ms
        self._active_routes[destination] = best[0]
        self.optimization_count += 1

        logger.info(
            "RouteOptimizer: high latency → selecting low-latency route %s for %s",
            best[0], destination,
        )
        return best[0]

    def get_active_route(self, destination: str) -> Optional[str]:
        return self._active_routes.get(destination)


# ─────────────────────────────────────────────
# FlowOptimizer  (task 21.3)
# ─────────────────────────────────────────────

class FlowOptimizer:
    """
    Adjusts flow control parameters in response to network conditions.

    Strategies:
    - High loss → reduce window size
    - Normal → gradually increase window size

    Validates: Requirements 8.3
    """

    def __init__(
        self,
        initial_window: int = 8,
        min_window: int = 1,
        max_window: int = 64,
        reduction_factor: float = 0.5,
        increase_step: int = 1,
    ):
        self.window_size      = initial_window
        self.min_window       = min_window
        self.max_window       = max_window
        self.reduction_factor = reduction_factor
        self.increase_step    = increase_step
        self.optimization_count = 0

    def optimize_for_loss(self, loss_pct: float) -> int:
        """
        Reduce window size on packet loss.

        Validates: Requirement 8.3
        """
        old_window = self.window_size
        new_window = max(
            self.min_window,
            int(self.window_size * self.reduction_factor),
        )
        self.window_size = new_window
        self.optimization_count += 1

        logger.info(
            "FlowOptimizer: loss=%.1f%% → window %d → %d",
            loss_pct, old_window, new_window,
        )
        return new_window

    def optimize_for_improvement(self) -> int:
        """
        Gradually increase window size when conditions improve.

        Validates: Requirement 8.3
        """
        old_window = self.window_size
        new_window = min(self.max_window, self.window_size + self.increase_step)
        self.window_size = new_window

        logger.info(
            "FlowOptimizer: improvement → window %d → %d",
            old_window, new_window,
        )
        return new_window

    def adjust_timeout(self, latency_mean_ms: float, multiplier: float = 3.0) -> float:
        """
        Adjust retransmission timeout based on current latency.

        Returns the recommended timeout in ms.
        """
        timeout_ms = max(100.0, latency_mean_ms * multiplier)
        logger.info("FlowOptimizer: timeout adjusted to %.1f ms", timeout_ms)
        return timeout_ms

    def get_window_size(self) -> int:
        return self.window_size


# ─────────────────────────────────────────────
# OptimizationModule  (tasks 21.1, 21.7)
# ─────────────────────────────────────────────

class OptimizationModule:
    """
    Central optimization module combining condition monitoring and strategies.

    Features:
    - Enable / disable optimization (static vs adaptive mode)   Req 8.8
    - Metric-driven trigger logic                               Req 8.6
    - Route and flow optimization strategies                    Req 8.2–8.4
    - Decision history for logging                              Req 8.5

    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6, 8.8
    """

    def __init__(
        self,
        enabled: bool = True,
        monitor: Optional[ConditionMonitor] = None,
        route_optimizer: Optional[RouteOptimizer] = None,
        flow_optimizer: Optional[FlowOptimizer] = None,
    ):
        self._enabled         = enabled
        self.monitor          = monitor or ConditionMonitor()
        self.route_optimizer  = route_optimizer or RouteOptimizer()
        self.flow_optimizer   = flow_optimizer or FlowOptimizer()

        self._decisions: List[OptimizationDecision] = []
        self._measurements: List[PerformanceMeasurement] = []
        self._decision_counter = 0

    # ── Enable / disable (task 21.7) ─────────────────────────────────────

    def enable(self) -> None:
        """Enable adaptive optimization mode."""
        self._enabled = True
        logger.info("OptimizationModule: ENABLED (adaptive mode)")

    def disable(self) -> None:
        """Disable optimization — static mode."""
        self._enabled = False
        logger.info("OptimizationModule: DISABLED (static mode)")

    def is_enabled(self) -> bool:
        return self._enabled

    # ── Core optimization loop (tasks 21.1, 21.3) ────────────────────────

    def evaluate(
        self,
        metrics: NetworkMetrics,
        destination: Optional[str] = None,
    ) -> Optional[OptimizationDecision]:
        """
        Evaluate current metrics and trigger optimization if needed.

        This is the main entry point. Call it periodically with fresh metrics.

        Args:
            metrics:     Current network metrics snapshot.
            destination: Optional route destination to optimise.

        Returns:
            OptimizationDecision if an action was taken, None otherwise.

        Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6
        """
        result = self.monitor.check(metrics)

        if not result.triggered:
            return None

        if not self._enabled:
            # Log that we detected a condition but took no action
            logger.debug(
                "OptimizationModule disabled — condition detected but no action: %s",
                result.condition.value,
            )
            return None

        # Choose action based on condition
        action, params = self._choose_action(result, destination)

        decision = self._record_decision(result, action, metrics, params)
        return decision

    def _choose_action(
        self,
        result: MonitorResult,
        destination: Optional[str],
    ) -> Tuple[OptimizationAction, Dict]:
        """Map a detected condition to the best optimization action."""
        condition = result.condition
        metrics   = result.metric_values
        params: Dict = {}

        if condition in (NetworkCondition.CONGESTION, NetworkCondition.DEGRADED):
            # Try route change first
            if destination:
                new_route = self.route_optimizer.optimize_for_congestion(destination)
                if new_route:
                    params["new_route"] = new_route
                    return OptimizationAction.CHANGE_ROUTE, params

            # Fall back to window reduction
            new_window = self.flow_optimizer.optimize_for_loss(metrics.loss_pct)
            params["new_window"] = new_window
            return OptimizationAction.REDUCE_WINDOW, params

        elif condition == NetworkCondition.HIGH_LOSS:
            new_window = self.flow_optimizer.optimize_for_loss(metrics.loss_pct)
            params["new_window"] = new_window
            return OptimizationAction.REDUCE_WINDOW, params

        elif condition == NetworkCondition.HIGH_LATENCY:
            if destination:
                new_route = self.route_optimizer.optimize_for_latency(destination)
                if new_route:
                    params["new_route"] = new_route
                    return OptimizationAction.SELECT_LOW_LATENCY_ROUTE, params

            new_timeout = self.flow_optimizer.adjust_timeout(metrics.latency_mean_ms)
            params["new_timeout_ms"] = new_timeout
            return OptimizationAction.ADJUST_TIMEOUT, params

        return OptimizationAction.NONE, params

    def _record_decision(
        self,
        result: MonitorResult,
        action: OptimizationAction,
        metrics: NetworkMetrics,
        params: Dict,
    ) -> OptimizationDecision:
        self._decision_counter += 1
        decision = OptimizationDecision(
            decision_id=f"decision_{self._decision_counter}",
            timestamp=time.time(),
            condition=result.condition,
            action=action,
            trigger_metrics=metrics,
            parameters=params,
            enabled=self._enabled,
        )
        self._decisions.append(decision)
        return decision

    # ── Before/after measurement (task 21.5) ─────────────────────────────

    def record_before(self, decision_id: str, metrics: NetworkMetrics) -> None:
        """Record the 'before' metrics snapshot for a decision."""
        self._measurements.append(
            PerformanceMeasurement(decision_id=decision_id, before=metrics)
        )

    def record_after(self, decision_id: str, metrics: NetworkMetrics) -> None:
        """
        Record the 'after' metrics and compute improvement percentages.

        Validates: Requirement 8.7
        """
        for m in self._measurements:
            if m.decision_id == decision_id and m.after is None:
                m.after = metrics
                m.improvement_pct = self._calc_improvement(m.before, metrics)
                return
        logger.warning("record_after: decision_id '%s' not found", decision_id)

    @staticmethod
    def _calc_improvement(before: NetworkMetrics, after: NetworkMetrics) -> Dict[str, float]:
        """Calculate % improvement for each metric (positive = better)."""
        result: Dict[str, float] = {}

        def _pct_change(b: float, a: float, lower_is_better: bool) -> float:
            if b == 0:
                return 0.0
            raw = ((a - b) / abs(b)) * 100.0
            return -raw if lower_is_better else raw

        result["loss_pct"]        = _pct_change(before.loss_pct,        after.loss_pct,        True)
        result["latency_mean_ms"] = _pct_change(before.latency_mean_ms, after.latency_mean_ms, True)
        result["latency_p95_ms"]  = _pct_change(before.latency_p95_ms,  after.latency_p95_ms,  True)
        result["throughput_bps"]  = _pct_change(before.throughput_bps,  after.throughput_bps,  False)
        result["jitter_mean_ms"]  = _pct_change(before.jitter_mean_ms,  after.jitter_mean_ms,  True)
        return result

    # ── Queries ───────────────────────────────────────────────────────────

    def get_decisions(self) -> List[OptimizationDecision]:
        return list(self._decisions)

    def get_measurements(self) -> List[PerformanceMeasurement]:
        return list(self._measurements)

    def get_statistics(self) -> Dict:
        total = len(self._decisions)
        by_condition: Dict[str, int] = {}
        by_action: Dict[str, int] = {}
        for d in self._decisions:
            by_condition[d.condition.value] = by_condition.get(d.condition.value, 0) + 1
            by_action[d.action.value]       = by_action.get(d.action.value, 0) + 1
        return {
            "enabled": self._enabled,
            "total_decisions": total,
            "by_condition": by_condition,
            "by_action": by_action,
            "route_optimizations": self.route_optimizer.optimization_count,
            "flow_optimizations":  self.flow_optimizer.optimization_count,
        }

    def reset(self) -> None:
        """Clear decision and measurement history."""
        self._decisions.clear()
        self._measurements.clear()
        self._decision_counter = 0
