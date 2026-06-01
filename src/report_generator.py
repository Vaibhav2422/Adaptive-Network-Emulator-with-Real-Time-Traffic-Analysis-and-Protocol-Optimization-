"""
Report Generator for the Adaptive Network Emulator.

Generates summary reports comparing protocol performance,
static vs adaptive configurations, and optimization effectiveness.

Validates: Requirement 10.8
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class MetricSummary:
    """Summary statistics for a single metric across a set of results."""
    metric_name: str
    mean:   float
    min:    float
    max:    float
    std:    float
    count:  int


@dataclass
class ProtocolComparison:
    """Side-by-side comparison of two protocols or configurations."""
    label_a:      str
    label_b:      str
    metric_name:  str
    value_a:      float
    value_b:      float
    diff_pct:     float          # ((b - a) / |a|) * 100
    winner:       str            # label of better performer


@dataclass
class PerformanceReport:
    """
    Full performance comparison report.

    Validates: Requirement 10.8
    """
    report_id:    str
    title:        str
    timestamp:    str
    description:  str

    # Experiment results included
    experiments:  List[Dict] = field(default_factory=list)

    # Per-metric summaries for each group
    summaries:    Dict[str, List[MetricSummary]] = field(default_factory=dict)

    # Head-to-head comparisons
    comparisons:  List[ProtocolComparison] = field(default_factory=list)

    # Static vs adaptive
    static_metrics:   Dict[str, float] = field(default_factory=dict)
    adaptive_metrics: Dict[str, float] = field(default_factory=dict)
    adaptive_improvement_pct: Dict[str, float] = field(default_factory=dict)

    # Narrative sections
    findings:     List[str] = field(default_factory=list)
    methodology:  str = ""
    conclusion:   str = ""


# ─────────────────────────────────────────────
# ReportGenerator  (task 24.5)
# ─────────────────────────────────────────────

class ReportGenerator:
    """
    Generates summary performance and protocol comparison reports.

    Features:
    - Compute per-metric statistics (mean, min, max, std)
    - Compare protocols / configurations head-to-head
    - Compare static vs adaptive performance
    - Export reports as JSON and human-readable text
    - Embed ASCII charts for terminal display

    Validates: Requirement 10.8
    """

    def __init__(self, reports_dir: str = "reports"):
        self._reports_dir = Path(reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._report_counter = 0

    # ── Main report builder ───────────────────────────────────────────────

    def generate_report(
        self,
        title: str,
        groups: Dict[str, List[Dict[str, Any]]],
        description: str = "",
        lower_is_better: Optional[List[str]] = None,
    ) -> PerformanceReport:
        """
        Generate a full performance comparison report.

        Args:
            title:           Report title.
            groups:          Dict of group_label → list of metric dicts.
                             Each metric dict maps metric_name → float value.
            description:     Optional report description.
            lower_is_better: Metric names where lower = better
                             (e.g. latency, loss). Default: all lower=better.

        Returns:
            PerformanceReport with summaries, comparisons, and findings.

        Validates: Requirement 10.8
        """
        self._report_counter += 1
        report_id = f"report_{self._report_counter}_{int(time.time())}"
        lib       = set(lower_is_better or [])

        # Summaries per group
        summaries: Dict[str, List[MetricSummary]] = {}
        for group_label, results in groups.items():
            summaries[group_label] = self._compute_summaries(results)

        # Head-to-head comparisons (all group pairs)
        comparisons: List[ProtocolComparison] = []
        group_labels = list(groups.keys())
        for i in range(len(group_labels)):
            for j in range(i + 1, len(group_labels)):
                la, lb = group_labels[i], group_labels[j]
                comps  = self._compare_groups(
                    la, summaries[la],
                    lb, summaries[lb],
                    lib,
                )
                comparisons.extend(comps)

        # Findings
        findings = self._generate_findings(summaries, comparisons, lib)

        report = PerformanceReport(
            report_id=report_id,
            title=title,
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description,
            experiments=[
                {"group": g, "count": len(r)}
                for g, r in groups.items()
            ],
            summaries=summaries,
            comparisons=comparisons,
            findings=findings,
            methodology=(
                "Metrics collected over multiple experiment runs. "
                "Statistics computed across all runs per group."
            ),
            conclusion=self._generate_conclusion(comparisons, lib),
        )
        return report

    def generate_static_vs_adaptive_report(
        self,
        static_results:   List[Dict[str, Any]],
        adaptive_results: List[Dict[str, Any]],
        title: str = "Static vs Adaptive Configuration Comparison",
        lower_is_better: Optional[List[str]] = None,
    ) -> PerformanceReport:
        """
        Compare static and adaptive configurations directly.

        Validates: Requirement 10.8
        """
        lib = set(lower_is_better or ["loss_pct", "latency_mean_ms",
                                       "latency_ms", "jitter_ms",
                                       "retransmissions"])

        report = self.generate_report(
            title=title,
            groups={"static": static_results, "adaptive": adaptive_results},
            description="Comparison of static vs adaptive network configuration.",
            lower_is_better=list(lib),
        )

        # Compute mean per metric for each group
        static_means  = self._group_means(static_results)
        adaptive_means = self._group_means(adaptive_results)

        improvement: Dict[str, float] = {}
        for metric in static_means:
            if metric in adaptive_means:
                s = static_means[metric]
                a = adaptive_means[metric]
                if s != 0:
                    raw_diff = ((a - s) / abs(s)) * 100.0
                    # For lower-is-better: negative diff = improvement
                    improvement[metric] = -raw_diff if metric in lib else raw_diff

        report.static_metrics           = static_means
        report.adaptive_metrics         = adaptive_means
        report.adaptive_improvement_pct = improvement
        return report

    # ── Export ────────────────────────────────────────────────────────────

    def save_json(
        self, report: PerformanceReport, filename: Optional[str] = None
    ) -> Path:
        """Save report as JSON. Validates: Requirement 10.8"""
        fname = filename or f"{report.report_id}.json"
        path  = self._reports_dir / fname
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._report_to_dict(report), fh, indent=2)
        logger.info("Report saved: %s", path)
        return path

    def save_text(
        self, report: PerformanceReport, filename: Optional[str] = None
    ) -> Path:
        """Save report as human-readable text. Validates: Requirement 10.8"""
        fname = filename or f"{report.report_id}.txt"
        path  = self._reports_dir / fname
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render_text(report))
        logger.info("Text report saved: %s", path)
        return path

    def render_text(self, report: PerformanceReport) -> str:
        """Render report as a human-readable string with ASCII charts."""
        lines = [
            "=" * 70,
            f"  {report.title}",
            "=" * 70,
            f"  Report ID : {report.report_id}",
            f"  Generated : {report.timestamp}",
            f"  {report.description}",
            "",
        ]

        # Per-group summaries
        for group, summaries in report.summaries.items():
            lines.append(f"── {group.upper()} ──")
            for s in summaries:
                lines.append(
                    f"  {s.metric_name:<28} "
                    f"mean={s.mean:>10.3f}  "
                    f"min={s.min:>10.3f}  "
                    f"max={s.max:>10.3f}  "
                    f"std={s.std:>8.3f}  n={s.count}"
                )
            lines.append("")

        # Comparisons
        if report.comparisons:
            lines.append("── COMPARISONS ──")
            for c in report.comparisons:
                sign  = "▲" if c.diff_pct > 0 else "▼"
                lines.append(
                    f"  {c.metric_name:<28} "
                    f"{c.label_a}={c.value_a:.3f}  "
                    f"{c.label_b}={c.value_b:.3f}  "
                    f"diff={sign}{abs(c.diff_pct):.1f}%  "
                    f"winner={c.winner}"
                )
            lines.append("")

        # Static vs adaptive improvement
        if report.adaptive_improvement_pct:
            lines.append("── ADAPTIVE IMPROVEMENT ──")
            for metric, pct in report.adaptive_improvement_pct.items():
                bar   = self._ascii_bar(pct, width=20)
                lines.append(f"  {metric:<28} {bar} {pct:+.1f}%")
            lines.append("")

        # Findings
        if report.findings:
            lines.append("── FINDINGS ──")
            for f in report.findings:
                lines.append(f"  • {f}")
            lines.append("")

        # Conclusion
        if report.conclusion:
            lines.append("── CONCLUSION ──")
            lines.append(f"  {report.conclusion}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _compute_summaries(results: List[Dict[str, Any]]) -> List[MetricSummary]:
        if not results:
            return []
        metrics: Dict[str, List[float]] = {}
        for r in results:
            for k, v in r.items():
                if isinstance(v, (int, float)):
                    metrics.setdefault(k, []).append(float(v))

        summaries = []
        for name, vals in metrics.items():
            n    = len(vals)
            mean = sum(vals) / n
            mn   = min(vals)
            mx   = max(vals)
            std  = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5 if n > 1 else 0.0
            summaries.append(MetricSummary(
                metric_name=name, mean=mean, min=mn, max=mx, std=std, count=n
            ))
        return summaries

    @staticmethod
    def _compare_groups(
        la: str, sums_a: List[MetricSummary],
        lb: str, sums_b: List[MetricSummary],
        lower_is_better: set,
    ) -> List[ProtocolComparison]:
        map_a = {s.metric_name: s for s in sums_a}
        map_b = {s.metric_name: s for s in sums_b}
        comparisons = []
        for name in map_a:
            if name not in map_b:
                continue
            va = map_a[name].mean
            vb = map_b[name].mean
            diff_pct = ((vb - va) / abs(va)) * 100.0 if va != 0 else 0.0
            if name in lower_is_better:
                winner = la if va <= vb else lb
            else:
                winner = la if va >= vb else lb
            comparisons.append(ProtocolComparison(
                label_a=la, label_b=lb,
                metric_name=name,
                value_a=va, value_b=vb,
                diff_pct=diff_pct,
                winner=winner,
            ))
        return comparisons

    @staticmethod
    def _group_means(results: List[Dict[str, Any]]) -> Dict[str, float]:
        if not results:
            return {}
        totals: Dict[str, float] = {}
        counts: Dict[str, int]   = {}
        for r in results:
            for k, v in r.items():
                if isinstance(v, (int, float)):
                    totals[k] = totals.get(k, 0.0) + float(v)
                    counts[k] = counts.get(k, 0) + 1
        return {k: totals[k] / counts[k] for k in totals}

    @staticmethod
    def _generate_findings(
        summaries: Dict[str, List[MetricSummary]],
        comparisons: List[ProtocolComparison],
        lower_is_better: set,
    ) -> List[str]:
        findings = []
        win_count: Dict[str, int] = {}
        for c in comparisons:
            win_count[c.winner] = win_count.get(c.winner, 0) + 1

        for group, count in sorted(win_count.items(), key=lambda x: -x[1]):
            findings.append(
                f"'{group}' outperformed in {count} metric(s)."
            )

        for c in comparisons:
            if abs(c.diff_pct) >= 20:
                direction = "lower" if c.diff_pct < 0 else "higher"
                findings.append(
                    f"Significant difference in '{c.metric_name}': "
                    f"{c.label_b} is {abs(c.diff_pct):.1f}% {direction} than {c.label_a}."
                )
        return findings

    @staticmethod
    def _generate_conclusion(
        comparisons: List[ProtocolComparison],
        lower_is_better: set,
    ) -> str:
        if not comparisons:
            return "Insufficient data for conclusion."
        win_count: Dict[str, int] = {}
        for c in comparisons:
            win_count[c.winner] = win_count.get(c.winner, 0) + 1
        if not win_count:
            return "No clear winner identified."
        best = max(win_count, key=lambda k: win_count[k])
        return (
            f"'{best}' demonstrated superior performance across "
            f"{win_count[best]} metric(s) compared to alternatives."
        )

    @staticmethod
    def _ascii_bar(value: float, width: int = 20) -> str:
        """Simple ASCII bar chart for a percentage value."""
        clamped = max(-100.0, min(100.0, value))
        filled  = int(abs(clamped) / 100.0 * width)
        char    = "█" if clamped >= 0 else "░"
        return f"[{char * filled}{' ' * (width - filled)}]"

    def _report_to_dict(self, report: PerformanceReport) -> Dict:
        """Convert report to a fully serializable dict."""
        d = asdict(report)
        # summaries is Dict[str, List[MetricSummary]] — already handled by asdict
        return d
