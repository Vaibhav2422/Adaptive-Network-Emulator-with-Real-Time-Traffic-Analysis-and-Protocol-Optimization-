"""
Property-based tests for Logging, Reporting, and Data Export (Task 24).

Properties tested:
  - Property 34: Protocol behavior logging completeness  (Requirement 10.3)
  - Property 35: Log export format validity              (Requirement 10.5)
  - Property 37: Performance comparison report generation (Requirement 10.8)

100 examples per property.
"""

import json
import random
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, assume, strategies as st

from src.protocol_logger import (
    ProtocolLogger, NetworkLayer, NetworkCondition, LogLevel,
)
from src.data_exporter import DataExporter
from src.report_generator import ReportGenerator


# ─────────────────────────────────────────────
# Shared strategies
# ─────────────────────────────────────────────

layer_st     = st.sampled_from([l.value for l in NetworkLayer])
condition_st = st.sampled_from([c.value for c in NetworkCondition])
level_st     = st.sampled_from([l.value for l in LogLevel])
node_id_st   = st.text(min_size=1, max_size=10,
                        alphabet=st.characters(min_codepoint=97, max_codepoint=122))
event_st     = st.sampled_from([
    "packet_sent", "packet_received", "ack_received",
    "retransmission", "window_update", "route_change",
    "frame_error", "collision", "backoff",
])
message_st   = st.text(min_size=1, max_size=100,
                        alphabet=st.characters(min_codepoint=32, max_codepoint=126))


def _make_metric_dict(rng_seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(rng_seed)
    return {
        "throughput_bps":  rng.uniform(1e4, 1e8),
        "latency_mean_ms": rng.uniform(1.0, 300.0),
        "loss_pct":        rng.uniform(0.0, 30.0),
        "retransmissions": rng.randint(0, 100),
        "jitter_ms":       rng.uniform(0.0, 50.0),
    }


# ─────────────────────────────────────────────
# Property 34: Protocol behavior logging completeness
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    layer=layer_st,
    node_id=node_id_st,
    event_type=event_st,
    condition=condition_st,
    message=message_st,
)
def test_property_34_every_event_is_logged(layer, node_id, event_type, condition, message):
    """
    Property 34: Protocol behavior logging completeness.
    Validates: Requirement 10.3

    For any network condition and event, every log() call must produce
    a retrievable entry with all fields intact.
    """
    assume(message.strip())

    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = ProtocolLogger(log_dir=tmpdir)
        entry   = plogger.log(
            layer=layer,
            node_id=node_id,
            event_type=event_type,
            message=message.strip(),
            condition=condition,
        )

        # Entry must be stored
        assert entry is not None
        assert entry.entry_id
        assert entry.timestamp

        # Fields must match what was passed
        assert entry.layer      == layer
        assert entry.node_id    == node_id
        assert entry.event_type == event_type
        assert entry.condition  == condition
        assert entry.message    == message.strip()

        # Must be retrievable via query
        all_entries = plogger.get_all_entries()
        assert len(all_entries) == 1
        assert all_entries[0].entry_id == entry.entry_id
        plogger.close()


@settings(max_examples=100, deadline=None)
@given(
    layer=layer_st,
    condition=condition_st,
    n_events=st.integers(min_value=1, max_value=20),
)
def test_property_34_all_conditions_logged_and_filterable(layer, condition, n_events):
    """
    Property 34 (variant): Log entries must be filterable by condition.
    Every entry logged under a condition must appear in filtered results.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = ProtocolLogger(log_dir=tmpdir)

        for i in range(n_events):
            plogger.log(
                layer=layer,
                node_id=f"node_{i}",
                event_type="packet_sent",
                message=f"Event {i}",
                condition=condition,
            )

        filtered = plogger.get_entries(layer=layer, condition=condition)
        assert len(filtered) == n_events, (
            f"Expected {n_events} filtered entries, got {len(filtered)}"
        )
        for e in filtered:
            assert e.condition == condition
            assert e.layer     == layer
        plogger.close()


@settings(max_examples=100, deadline=None)
@given(
    layers=st.lists(layer_st, min_size=1, max_size=6, unique=True),
    n_per_layer=st.integers(min_value=1, max_value=10),
)
def test_property_34_per_layer_entries_correctly_separated(layers, n_per_layer):
    """
    Property 34 (variant): Each layer must have exactly n_per_layer entries
    when n_per_layer events are logged per layer.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = ProtocolLogger(log_dir=tmpdir)

        for layer in layers:
            for i in range(n_per_layer):
                plogger.log(
                    layer=layer,
                    node_id="node_0",
                    event_type="packet_sent",
                    message=f"msg {i}",
                )

        for layer in layers:
            entries = plogger.get_entries(layer=layer)
            assert len(entries) == n_per_layer, (
                f"Layer '{layer}': expected {n_per_layer}, got {len(entries)}"
            )
        plogger.close()


@settings(max_examples=100, deadline=None)
@given(
    node_id=node_id_st,
    n_events=st.integers(min_value=1, max_value=15),
    loss_pct=st.floats(min_value=0.0, max_value=100.0,
                       allow_nan=False, allow_infinity=False),
    latency_ms=st.floats(min_value=0.0, max_value=500.0,
                         allow_nan=False, allow_infinity=False),
)
def test_property_34_metric_values_preserved_in_log(node_id, n_events, loss_pct, latency_ms):
    """
    Property 34 (variant): Numeric metric values must be preserved exactly in log entries.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        plogger = ProtocolLogger(log_dir=tmpdir)

        for i in range(n_events):
            entry = plogger.log_transport(
                node_id=node_id,
                event_type="packet_sent",
                message=f"pkt {i}",
                loss_pct=loss_pct,
                latency_ms=latency_ms,
                sequence_num=i,
            )
            assert abs(entry.loss_pct   - loss_pct)   < 1e-9
            assert abs(entry.latency_ms - latency_ms) < 1e-9
            assert entry.sequence_num == i
        plogger.close()


# ─────────────────────────────────────────────
# Property 35: Log export format validity
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    n_records=st.integers(min_value=1, max_value=50),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_35_json_export_is_valid_and_parseable(n_records, seed):
    """
    Property 35: Log export format validity.
    Validates: Requirement 10.5

    Any JSON export must be valid, parseable, and contain all records.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=tmpdir)
        records  = [_make_metric_dict(seed + i) for i in range(n_records)]

        path = exporter.export_json(records, label="metrics")

        assert path.exists(), "Export file must be created"
        assert exporter.validate_json(path), "Exported JSON must be valid"

        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)

        assert len(loaded) == n_records, (
            f"Expected {n_records} records, got {len(loaded)}"
        )
        # All keys from original must be present
        for orig, loaded_r in zip(records, loaded):
            for key in orig:
                assert key in loaded_r, f"Key '{key}' missing from exported record"


@settings(max_examples=100, deadline=None)
@given(
    n_records=st.integers(min_value=1, max_value=50),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_35_csv_export_is_valid_and_parseable(n_records, seed):
    """
    Property 35 (variant): Any CSV export must have correct headers and rows.
    Validates: Requirement 10.5
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=tmpdir)
        records  = [_make_metric_dict(seed + i) for i in range(n_records)]

        path = exporter.export_csv(records, label="metrics")

        assert path.exists()
        assert exporter.validate_csv(path), "Exported CSV must be valid"

        import csv
        with open(path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows   = list(reader)

        assert len(rows) == n_records, (
            f"CSV must have {n_records} data rows, got {len(rows)}"
        )
        for key in records[0]:
            assert key in reader.fieldnames, f"Column '{key}' missing from CSV"


@settings(max_examples=100, deadline=None)
@given(
    n_packets=st.integers(min_value=1, max_value=50),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_35_packet_trace_is_valid_wireshark_format(n_packets, seed):
    """
    Property 35 (variant): Packet trace must be valid Wireshark-compatible JSON.
    Validates: Requirement 10.6
    """
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=tmpdir)
        packets  = [
            {
                "packet_id":   f"pkt_{i}",
                "source":      f"10.0.0.{rng.randint(1, 254)}",
                "destination": f"10.0.0.{rng.randint(1, 254)}",
                "protocol":    rng.choice(["TCP", "UDP", "ICMP"]),
                "size_bytes":  rng.randint(64, 1500),
                "layer":       rng.choice(["transport", "network"]),
                "sequence_num": i,
                "timestamp":   1700000000.0 + i,
            }
            for i in range(n_packets)
        ]

        path = exporter.capture_packet_trace(packets)

        assert path.exists()
        assert exporter.validate_packet_trace(path), (
            "Packet trace must be valid Wireshark-compatible JSON"
        )

        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)

        assert len(loaded) == n_packets
        for pkt in loaded:
            assert "_source" in pkt
            assert "layers"  in pkt["_source"]
            assert "frame"   in pkt["_source"]["layers"]
            assert "ip"      in pkt["_source"]["layers"]


@settings(max_examples=100, deadline=None)
@given(
    n_records=st.integers(min_value=1, max_value=30),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_35_jsonl_export_every_line_valid(n_records, seed):
    """
    Property 35 (variant): Every line in a JSONL export must be valid JSON.
    Validates: Requirement 10.5
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=tmpdir)
        records  = [_make_metric_dict(seed + i) for i in range(n_records)]

        path = exporter.export_jsonl(records, label="metrics")

        assert path.exists()
        assert exporter.validate_jsonl(path)

        with open(path, "r", encoding="utf-8") as fh:
            lines = [l.strip() for l in fh if l.strip()]

        assert len(lines) == n_records
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)


# ─────────────────────────────────────────────
# Property 37: Performance comparison report generation
# ─────────────────────────────────────────────

@settings(max_examples=100, deadline=None)
@given(
    n_results=st.integers(min_value=2, max_value=20),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_37_report_generated_for_any_experiment(n_results, seed):
    """
    Property 37: Performance comparison report generation.
    Validates: Requirement 10.8

    For any set of experiment results, a summary report must be generated
    with at least one finding and a non-empty conclusion.
    """
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as tmpdir:
        gen      = ReportGenerator(reports_dir=tmpdir)
        group_a  = [_make_metric_dict(seed + i)       for i in range(n_results)]
        group_b  = [_make_metric_dict(seed + 1000 + i) for i in range(n_results)]

        report = gen.generate_report(
            title="Protocol Comparison",
            groups={"protocol_a": group_a, "protocol_b": group_b},
            lower_is_better=["loss_pct", "latency_mean_ms", "jitter_ms"],
        )

        assert report.report_id,   "Report must have an ID"
        assert report.timestamp,   "Report must have a timestamp"
        assert report.summaries,   "Report must have summaries"
        assert report.comparisons, "Report must have comparisons"
        assert report.conclusion,  "Report must have a conclusion"

        # Summaries must cover both groups
        assert "protocol_a" in report.summaries
        assert "protocol_b" in report.summaries

        # Each summary must have entries
        assert len(report.summaries["protocol_a"]) > 0
        assert len(report.summaries["protocol_b"]) > 0


@settings(max_examples=100, deadline=None)
@given(
    n_static=st.integers(min_value=2, max_value=15),
    n_adaptive=st.integers(min_value=2, max_value=15),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_37_static_vs_adaptive_report_has_improvement(n_static, n_adaptive, seed):
    """
    Property 37 (variant): Static vs adaptive report must compute improvement percentages.
    Validates: Requirement 10.8
    """
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as tmpdir:
        gen      = ReportGenerator(reports_dir=tmpdir)
        static   = [_make_metric_dict(seed + i)      for i in range(n_static)]
        adaptive = [_make_metric_dict(seed + 500 + i) for i in range(n_adaptive)]

        report = gen.generate_static_vs_adaptive_report(static, adaptive)

        assert report.static_metrics,           "Must have static metrics"
        assert report.adaptive_metrics,         "Must have adaptive metrics"
        assert report.adaptive_improvement_pct is not None, \
            "Must have improvement percentages"

        # Improvement pct must be numeric
        for metric, pct in report.adaptive_improvement_pct.items():
            assert isinstance(pct, float), f"Improvement for '{metric}' must be float"


@settings(max_examples=100, deadline=None)
@given(
    n_results=st.integers(min_value=2, max_value=15),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_37_report_saves_to_json_and_is_valid(n_results, seed):
    """
    Property 37 (variant): Saved JSON report must be valid and contain all sections.
    Validates: Requirement 10.8
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        gen     = ReportGenerator(reports_dir=tmpdir)
        group_a = [_make_metric_dict(seed + i)      for i in range(n_results)]
        group_b = [_make_metric_dict(seed + 100 + i) for i in range(n_results)]

        report = gen.generate_report(
            title="Test Report",
            groups={"gbn": group_a, "sr": group_b},
        )
        path = gen.save_json(report)

        assert path.exists()
        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)

        required_keys = ["report_id", "title", "timestamp", "summaries",
                         "comparisons", "findings", "conclusion"]
        for key in required_keys:
            assert key in loaded, f"Key '{key}' missing from saved report"


@settings(max_examples=100, deadline=None)
@given(
    n_groups=st.integers(min_value=2, max_value=4),
    n_results=st.integers(min_value=2, max_value=10),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_37_report_comparisons_cover_all_group_pairs(n_groups, n_results, seed):
    """
    Property 37 (variant): Report must produce comparisons for every group pair.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        gen    = ReportGenerator(reports_dir=tmpdir)
        groups = {
            f"group_{i}": [_make_metric_dict(seed + i * 100 + j) for j in range(n_results)]
            for i in range(n_groups)
        }

        report = gen.generate_report(title="Multi-group", groups=groups)

        # Number of unique pairs = n*(n-1)/2
        expected_pairs = n_groups * (n_groups - 1) // 2
        labels_in_comparisons = set()
        for c in report.comparisons:
            labels_in_comparisons.add((c.label_a, c.label_b))

        assert len(labels_in_comparisons) == expected_pairs, (
            f"Expected {expected_pairs} group pairs in comparisons, "
            f"got {len(labels_in_comparisons)}"
        )


@settings(max_examples=100, deadline=None)
@given(
    n_results=st.integers(min_value=2, max_value=15),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_property_37_text_report_renders_non_empty(n_results, seed):
    """
    Property 37 (variant): Text report rendering must produce non-empty output
    with all required sections.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        gen     = ReportGenerator(reports_dir=tmpdir)
        group_a = [_make_metric_dict(seed + i) for i in range(n_results)]
        group_b = [_make_metric_dict(seed + 200 + i) for i in range(n_results)]

        report = gen.generate_report(
            title="Text Render Test",
            groups={"gbn": group_a, "sr": group_b},
        )
        text = gen.render_text(report)

        assert len(text) > 100, "Text report must be non-trivial"
        assert "Text Render Test" in text
        assert "GBN" in text.upper() or "gbn" in text.lower()
        assert "CONCLUSION" in text.upper()
