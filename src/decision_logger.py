"""
Decision Logger for the Adaptive Network Emulator Optimization Module.

Logs optimization decisions with triggering conditions, metric values,
actions taken, and before/after performance measurements.

Validates: Requirements 8.5, 8.7
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.optimization_module import (
    OptimizationDecision,
    PerformanceMeasurement,
    NetworkMetrics,
    OptimizationModule,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class DecisionLogEntry:
    """
    A single logged optimization decision.

    Validates: Requirement 8.5 (log triggering conditions, metric values, actions)
    """
    log_id: str
    timestamp: str                   # ISO 8601
    decision_id: str
    condition: str                   # NetworkCondition value
    action: str                      # OptimizationAction value
    trigger_metrics: Dict            # Metric snapshot that caused trigger
    parameters: Dict                 # Action parameters
    enabled: bool


@dataclass
class EffectivenessEntry:
    """
    Before/after effectiveness record for a single optimization.

    Validates: Requirement 8.7
    """
    log_id: str
    timestamp: str
    decision_id: str
    before_metrics: Dict
    after_metrics: Optional[Dict]
    improvement_pct: Dict[str, float]
    overall_improved: bool


@dataclass
class OptimizationReport:
    """Summary report of optimization effectiveness over a session."""
    report_id: str
    timestamp: str
    total_decisions: int
    total_measured: int
    avg_loss_improvement_pct: float
    avg_latency_improvement_pct: float
    avg_throughput_improvement_pct: float
    decisions_that_improved: int
    summary: str


# ─────────────────────────────────────────────
# DecisionLogger
# ─────────────────────────────────────────────

class DecisionLogger:
    """
    Logs every optimization decision and its measured effectiveness.

    Features:
    - Logs decision trigger conditions, metric values, and action taken  Req 8.5
    - Records before/after metrics and computes improvement %            Req 8.7
    - Persists to JSON Lines file
    - Generates effectiveness reports

    Validates: Requirements 8.5, 8.7
    """

    def __init__(self, log_dir: str = "logs", filename_prefix: str = "optimization"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._log_path = self._log_dir / f"{filename_prefix}_{ts}.jsonl"
        self._log_file = open(self._log_path, "a", encoding="utf-8")

        self._decision_entries: List[DecisionLogEntry] = []
        self._effectiveness_entries: List[EffectivenessEntry] = []
        self._entry_counter = 0

        logger.info("DecisionLogger writing to %s", self._log_path)

    # ── Logging API ───────────────────────────────────────────────────────

    def log_decision(self, decision: OptimizationDecision) -> DecisionLogEntry:
        """
        Log a single optimization decision.

        Records: condition, trigger metrics, action, parameters.

        Validates: Requirement 8.5
        """
        self._entry_counter += 1
        entry = DecisionLogEntry(
            log_id=f"log_{self._entry_counter}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_id=decision.decision_id,
            condition=decision.condition.value,
            action=decision.action.value,
            trigger_metrics=self._metrics_to_dict(decision.trigger_metrics),
            parameters=decision.parameters,
            enabled=decision.enabled,
        )
        self._decision_entries.append(entry)
        self._write_json({"type": "decision", **asdict(entry)})
        return entry

    def log_effectiveness(
        self, measurement: PerformanceMeasurement
    ) -> EffectivenessEntry:
        """
        Log before/after performance measurement for an optimization.

        Validates: Requirement 8.7
        """
        self._entry_counter += 1

        after_dict = (
            self._metrics_to_dict(measurement.after)
            if measurement.after else None
        )

        # Determine overall improvement: majority of metrics improved
        impr = measurement.improvement_pct
        improved_count = sum(1 for v in impr.values() if v > 0)
        overall_improved = improved_count > len(impr) / 2 if impr else False

        entry = EffectivenessEntry(
            log_id=f"log_{self._entry_counter}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_id=measurement.decision_id,
            before_metrics=self._metrics_to_dict(measurement.before),
            after_metrics=after_dict,
            improvement_pct=measurement.improvement_pct,
            overall_improved=overall_improved,
        )
        self._effectiveness_entries.append(entry)
        self._write_json({"type": "effectiveness", **asdict(entry)})
        return entry

    def log_all_decisions(
        self, module: OptimizationModule
    ) -> List[DecisionLogEntry]:
        """Log all decisions from an OptimizationModule."""
        return [self.log_decision(d) for d in module.get_decisions()]

    def log_all_measurements(
        self, module: OptimizationModule
    ) -> List[EffectivenessEntry]:
        """Log all measurements from an OptimizationModule."""
        return [self.log_effectiveness(m) for m in module.get_measurements()]

    # ── Report generation ─────────────────────────────────────────────────

    def generate_report(self) -> OptimizationReport:
        """
        Generate a summary effectiveness report.

        Validates: Requirement 8.7
        """
        total_decisions = len(self._decision_entries)
        measured = [e for e in self._effectiveness_entries if e.after_metrics]
        total_measured = len(measured)

        def _avg(key: str) -> float:
            vals = [e.improvement_pct.get(key, 0.0) for e in measured]
            return sum(vals) / len(vals) if vals else 0.0

        avg_loss      = _avg("loss_pct")
        avg_latency   = _avg("latency_mean_ms")
        avg_throughput = _avg("throughput_bps")
        decisions_improved = sum(1 for e in measured if e.overall_improved)

        summary_lines = [
            f"Optimization Effectiveness Report",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Total decisions: {total_decisions}",
            f"Measured decisions: {total_measured}",
            f"Decisions that improved performance: {decisions_improved}/{total_measured}",
            f"Avg loss improvement:      {avg_loss:+.2f}%",
            f"Avg latency improvement:   {avg_latency:+.2f}%",
            f"Avg throughput improvement:{avg_throughput:+.2f}%",
        ]

        report = OptimizationReport(
            report_id=f"report_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_decisions=total_decisions,
            total_measured=total_measured,
            avg_loss_improvement_pct=avg_loss,
            avg_latency_improvement_pct=avg_latency,
            avg_throughput_improvement_pct=avg_throughput,
            decisions_that_improved=decisions_improved,
            summary="\n".join(summary_lines),
        )
        return report

    def save_report(self, report: OptimizationReport, output_dir: str = "logs") -> Path:
        """Save the effectiveness report to a JSON file."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{report.report_id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(report), fh, indent=2)
        logger.info("Optimization report saved: %s", path)
        return path

    # ── Queries ───────────────────────────────────────────────────────────

    def get_decision_entries(self) -> List[DecisionLogEntry]:
        return list(self._decision_entries)

    def get_effectiveness_entries(self) -> List[EffectivenessEntry]:
        return list(self._effectiveness_entries)

    def get_log_path(self) -> Path:
        return self._log_path

    def read_log_file(self) -> List[Dict]:
        """Read and parse the current log file."""
        self.flush()
        entries = []
        try:
            with open(self._log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Error reading log file: %s", exc)
        return entries

    # ── I/O ───────────────────────────────────────────────────────────────

    def flush(self) -> None:
        if not self._log_file.closed:
            self._log_file.flush()

    def close(self) -> None:
        self.flush()
        if not self._log_file.closed:
            self._log_file.close()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _metrics_to_dict(m: NetworkMetrics) -> Dict:
        return {
            "loss_pct":        m.loss_pct,
            "latency_mean_ms": m.latency_mean_ms,
            "latency_p95_ms":  m.latency_p95_ms,
            "throughput_bps":  m.throughput_bps,
            "retransmissions": m.retransmissions,
            "jitter_mean_ms":  m.jitter_mean_ms,
            "timestamp":       m.timestamp,
        }

    def _write_json(self, obj: Dict) -> None:
        try:
            self._log_file.write(json.dumps(obj) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write log entry: %s", exc)
