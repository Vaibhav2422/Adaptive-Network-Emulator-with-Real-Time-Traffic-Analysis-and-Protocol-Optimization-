"""
Comparison Engine for the Adaptive Network Emulator.

Provides before/after performance analysis, baseline storage,
percentage improvement/degradation calculation, and comparison reports.

Validates: Requirements 7.7
"""

import json
import logging
import math
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.traffic_analyzer import CapturedPacket
from src.metrics_calculator import MetricsCalculator, SessionMetrics

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class BaselineSnapshot:
    """
    A stored baseline of session metrics.

    Attributes:
        baseline_id:     Unique identifier for this baseline.
        label:           Human-readable label.
        timestamp:       ISO 8601 creation timestamp.
        throughput_bps:  Baseline throughput.
        latency_mean_ms: Baseline mean latency.
        latency_p95_ms:  Baseline p95 latency.
        loss_pct:        Baseline packet loss percentage.
        retransmissions: Baseline retransmission count.
        jitter_mean_ms:  Baseline mean jitter.
        packet_count:    Total packets in the baseline session.
    """
    baseline_id: str
    label: str
    timestamp: str
    throughput_bps: float
    latency_mean_ms: float
    latency_p95_ms: float
    loss_pct: float
    retransmissions: int
    jitter_mean_ms: float
    packet_count: int


@dataclass
class MetricComparison:
    """
    Comparison result for a single metric.

    Attributes:
        metric_name:     Name of the metric.
        baseline_value:  Value in the baseline.
        current_value:   Value in the current session.
        change_pct:      Percentage change (positive = improvement for throughput,
                         negative = improvement for latency/loss).
        improved:        True when the change is beneficial.
        significant:     True when |change_pct| > significance_threshold.
    """
    metric_name: str
    baseline_value: float
    current_value: float
    change_pct: float
    improved: bool
    significant: bool


@dataclass
class ComparisonReport:
    """
    Full before/after comparison report.

    Attributes:
        report_id:       Unique report identifier.
        baseline_id:     ID of the baseline used.
        baseline_label:  Label of the baseline.
        timestamp:       ISO 8601 report generation timestamp.
        comparisons:     Per-metric comparison results.
        summary:         Plain-text summary of findings.
        overall_improved: True if the majority of key metrics improved.
    """
    report_id: str
    baseline_id: str
    baseline_label: str
    timestamp: str
    comparisons: List[MetricComparison]
    summary: str
    overall_improved: bool


# ─────────────────────────────────────────────
# ComparisonEngine
# ─────────────────────────────────────────────

# Metrics where *lower* is better (latency, loss, jitter, retransmissions)
_LOWER_IS_BETTER = {"latency_mean_ms", "latency_p95_ms", "loss_pct",
                    "retransmissions", "jitter_mean_ms"}

# Default significance threshold (%)
_DEFAULT_SIGNIFICANCE = 5.0


class ComparisonEngine:
    """
    Compares current session metrics against stored baselines.

    Supports:
    - Capturing and saving baseline snapshots to JSON files
    - Loading baselines from file
    - Percentage improvement / degradation calculation
    - Statistical significance testing (threshold-based)
    - Multi-baseline comparisons
    - Generating human-readable comparison reports

    Validates: Requirement 7.7
    """

    def __init__(
        self,
        baselines_dir: str = "logs/baselines",
        significance_threshold: float = _DEFAULT_SIGNIFICANCE,
    ):
        """
        Initialise the ComparisonEngine.

        Args:
            baselines_dir:         Directory to persist baseline files.
            significance_threshold: Minimum % change to flag as significant.
        """
        self._dir = Path(baselines_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._threshold = significance_threshold
        self._calculator = MetricsCalculator()
        self._baselines: Dict[str, BaselineSnapshot] = {}

        # Load any existing baselines from disk
        self._load_all_baselines()

    # ── Baseline management ───────────────────────────────────────────────

    def capture_baseline(
        self,
        packets: List[CapturedPacket],
        label: str = "",
        baseline_id: Optional[str] = None,
        time_interval_s: Optional[float] = None,
    ) -> BaselineSnapshot:
        """
        Capture a baseline snapshot from a packet list and save to disk.

        Args:
            packets:         Packets representing the baseline session.
            label:           Human-readable description.
            baseline_id:     Optional custom ID (auto-generated if None).
            time_interval_s: Optional explicit time window for throughput.

        Returns:
            BaselineSnapshot that was saved.
        """
        metrics = self._calculator.calculate_all(packets, time_interval_s)

        bid = baseline_id or f"baseline_{int(time.time() * 1000)}"
        snapshot = BaselineSnapshot(
            baseline_id=bid,
            label=label or bid,
            timestamp=datetime.now(timezone.utc).isoformat(),
            throughput_bps=metrics.throughput.throughput_bps,
            latency_mean_ms=metrics.latency.mean_ms,
            latency_p95_ms=metrics.latency.p95_ms,
            loss_pct=metrics.packet_loss.loss_percentage,
            retransmissions=metrics.retransmissions.retransmission_count,
            jitter_mean_ms=metrics.jitter.mean_jitter_ms,
            packet_count=len(packets),
        )

        self._baselines[bid] = snapshot
        self._save_baseline(snapshot)
        logger.info("Baseline captured: id=%s, label=%s", bid, label)
        return snapshot

    def load_baseline(self, baseline_id: str) -> Optional[BaselineSnapshot]:
        """
        Load a baseline by ID (from memory or disk).

        Args:
            baseline_id: Baseline identifier.

        Returns:
            BaselineSnapshot or None if not found.
        """
        if baseline_id in self._baselines:
            return self._baselines[baseline_id]
        # Try loading from disk
        path = self._dir / f"{baseline_id}.json"
        if path.exists():
            snapshot = self._load_baseline_file(path)
            if snapshot:
                self._baselines[baseline_id] = snapshot
            return snapshot
        return None

    def list_baselines(self) -> List[BaselineSnapshot]:
        """Return all available baselines (memory + disk)."""
        self._load_all_baselines()
        return list(self._baselines.values())

    def delete_baseline(self, baseline_id: str) -> bool:
        """Delete a baseline by ID."""
        self._baselines.pop(baseline_id, None)
        path = self._dir / f"{baseline_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # ── Comparison ────────────────────────────────────────────────────────

    def compare(
        self,
        current_packets: List[CapturedPacket],
        baseline_id: str,
        time_interval_s: Optional[float] = None,
    ) -> ComparisonReport:
        """
        Compare current session against a stored baseline.

        Args:
            current_packets: Packets from the current session.
            baseline_id:     ID of the baseline to compare against.
            time_interval_s: Optional time window for throughput.

        Returns:
            ComparisonReport with per-metric comparisons and summary.

        Raises:
            KeyError: If baseline_id is not found.
        """
        baseline = self.load_baseline(baseline_id)
        if baseline is None:
            raise KeyError(f"Baseline '{baseline_id}' not found.")

        metrics = self._calculator.calculate_all(current_packets, time_interval_s)
        current = self._metrics_to_dict(metrics, len(current_packets))
        base    = asdict(baseline)

        comparisons: List[MetricComparison] = []
        for key in ("throughput_bps", "latency_mean_ms", "latency_p95_ms",
                    "loss_pct", "retransmissions", "jitter_mean_ms"):
            baseline_val = float(base.get(key, 0.0))
            current_val  = float(current.get(key, 0.0))
            comp = self._compare_metric(key, baseline_val, current_val)
            comparisons.append(comp)

        improved_count = sum(1 for c in comparisons if c.improved)
        overall_improved = improved_count > len(comparisons) / 2

        summary = self._generate_summary(baseline, comparisons, overall_improved)

        report = ComparisonReport(
            report_id=f"report_{int(time.time() * 1000)}",
            baseline_id=baseline_id,
            baseline_label=baseline.label,
            timestamp=datetime.now(timezone.utc).isoformat(),
            comparisons=comparisons,
            summary=summary,
            overall_improved=overall_improved,
        )

        logger.info(
            "Comparison report generated: baseline=%s, overall_improved=%s",
            baseline_id, overall_improved,
        )
        return report

    def compare_multiple(
        self,
        current_packets: List[CapturedPacket],
        baseline_ids: List[str],
        time_interval_s: Optional[float] = None,
    ) -> List[ComparisonReport]:
        """
        Compare current session against multiple baselines.

        Args:
            current_packets: Packets from the current session.
            baseline_ids:    List of baseline IDs.
            time_interval_s: Optional time window for throughput.

        Returns:
            List of ComparisonReport objects.
        """
        reports = []
        for bid in baseline_ids:
            try:
                reports.append(self.compare(current_packets, bid, time_interval_s))
            except KeyError as exc:
                logger.warning("Skipping baseline: %s", exc)
        return reports

    def save_report(self, report: ComparisonReport, output_dir: str = "logs") -> Path:
        """
        Save a comparison report to a JSON file.

        Args:
            report:     ComparisonReport to save.
            output_dir: Directory to write the report.

        Returns:
            Path of the written file.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{report.report_id}.json"

        # Convert dataclasses to serialisable dicts
        data = {
            "report_id":       report.report_id,
            "baseline_id":     report.baseline_id,
            "baseline_label":  report.baseline_label,
            "timestamp":       report.timestamp,
            "overall_improved": report.overall_improved,
            "summary":         report.summary,
            "comparisons": [asdict(c) for c in report.comparisons],
        }

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

        logger.info("Comparison report saved: %s", path)
        return path

    # ── Internal helpers ──────────────────────────────────────────────────

    def _compare_metric(
        self, name: str, baseline: float, current: float
    ) -> MetricComparison:
        """Calculate percentage change and determine if it improved."""
        if baseline == 0:
            change_pct = 0.0 if current == 0 else 100.0
        else:
            change_pct = ((current - baseline) / abs(baseline)) * 100.0

        # For lower-is-better metrics, a negative change = improvement
        if name in _LOWER_IS_BETTER:
            improved = change_pct < 0
        else:
            improved = change_pct > 0

        significant = abs(change_pct) >= self._threshold

        return MetricComparison(
            metric_name=name,
            baseline_value=baseline,
            current_value=current,
            change_pct=change_pct,
            improved=improved,
            significant=significant,
        )

    def _metrics_to_dict(self, metrics: SessionMetrics, packet_count: int) -> Dict:
        return {
            "throughput_bps":  metrics.throughput.throughput_bps,
            "latency_mean_ms": metrics.latency.mean_ms,
            "latency_p95_ms":  metrics.latency.p95_ms,
            "loss_pct":        metrics.packet_loss.loss_percentage,
            "retransmissions": metrics.retransmissions.retransmission_count,
            "jitter_mean_ms":  metrics.jitter.mean_jitter_ms,
            "packet_count":    packet_count,
        }

    def _generate_summary(
        self,
        baseline: BaselineSnapshot,
        comparisons: List[MetricComparison],
        overall_improved: bool,
    ) -> str:
        lines = [
            f"Comparison vs baseline '{baseline.label}' ({baseline.timestamp})",
            f"Overall result: {'IMPROVED' if overall_improved else 'DEGRADED'}",
            "",
        ]
        for c in comparisons:
            arrow = "↑" if c.improved else "↓"
            sig   = " [significant]" if c.significant else ""
            lines.append(
                f"  {arrow} {c.metric_name}: {c.baseline_value:.4f} → "
                f"{c.current_value:.4f} ({c.change_pct:+.2f}%){sig}"
            )
        return "\n".join(lines)

    def _save_baseline(self, snapshot: BaselineSnapshot) -> None:
        path = self._dir / f"{snapshot.baseline_id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(snapshot), fh, indent=2)

    def _load_baseline_file(self, path: Path) -> Optional[BaselineSnapshot]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return BaselineSnapshot(**data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load baseline %s: %s", path, exc)
            return None

    def _load_all_baselines(self) -> None:
        for path in self._dir.glob("*.json"):
            bid = path.stem
            if bid not in self._baselines:
                snapshot = self._load_baseline_file(path)
                if snapshot:
                    self._baselines[bid] = snapshot
