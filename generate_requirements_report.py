"""
Requirements Traceability and Coverage Report Generator — Task 27.3

Run with:
    python generate_requirements_report.py

Outputs:
    docs/REQUIREMENTS_COVERAGE.md
    docs/REQUIREMENTS_COVERAGE.json
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Requirements registry
# All requirements from the project specification
# ─────────────────────────────────────────────────────────────

REQUIREMENTS: Dict[str, str] = {
    # Section 1 – System Overview
    "1.1":  "Emulate network stack with Physical, Data Link, Network, Transport, Application layers",
    "1.2":  "Support GBN and SR sliding window protocols",
    "1.3":  "Provide extensible architecture with documented extension points",
    "1.4":  "Run on standard Python 3.12+ without special hardware",

    # Section 2 – Physical Layer
    "2.1":  "Model propagation delay per link",
    "2.2":  "Model configurable packet loss rate",
    "2.3":  "Model bandwidth-limited transmission delay",
    "2.4":  "Support multiple simultaneous links",

    # Section 3 – Data Link Layer
    "3.1":  "Implement framing with header and CRC error detection",
    "3.2":  "Implement MAC layer with CSMA/CD",
    "3.3":  "Detect and handle frame collisions",
    "3.4":  "Support configurable frame size",

    # Section 4 – Network Layer
    "4.1":  "Implement Dijkstra shortest-path routing",
    "4.2":  "Implement Distance Vector routing",
    "4.3":  "Maintain and update routing tables",
    "4.4":  "Support multi-hop packet forwarding",

    # Section 5 – Transport Layer
    "5.1":  "Implement Go-Back-N (GBN) protocol",
    "5.2":  "Implement Selective Repeat (SR) protocol",
    "5.3":  "Support configurable window size (1–1024)",
    "5.4":  "Implement retransmission timeout and max retransmissions",
    "5.5":  "Support cumulative and selective acknowledgements",

    # Section 6 – Application Layer
    "6.1":  "Implement file transfer service",
    "6.2":  "Support CBR, bursty, and trace traffic patterns",
    "6.3":  "Reassemble received data correctly",

    # Section 7 – Adaptive Protocol
    "7.1":  "Implement ADAPTIVE protocol extending GBN/SR",
    "7.2":  "Dynamically adjust window size based on network conditions",
    "7.3":  "Use configurable learning rate (adaptive_alpha)",

    # Section 8 – Optimization
    "8.1":  "Implement congestion detection",
    "8.2":  "Implement flow control optimization",
    "8.3":  "Compare static vs adaptive protocol performance",

    # Section 9 – Simulation Control
    "9.1":  "Implement discrete-event simulation engine",
    "9.2":  "Support configurable experiment duration and repetitions",
    "9.3":  "Support reproducible runs via random seed",
    "9.4":  "Support multi-run experiment management",

    # Section 10 – Logging, Reporting, Export
    "10.3": "Log all protocol events with layer, node, condition, and message",
    "10.4": "Provide example workflows covering all major use cases",
    "10.5": "Export logs in JSON, CSV, and JSONL formats",
    "10.6": "Export packet traces in Wireshark-compatible JSON format",
    "10.7": "Validate all exported files for format correctness",
    "10.8": "Generate performance comparison reports with conclusions",

    # Section 11 – Configuration and Documentation
    "11.2": "Define comprehensive YAML configuration schema",
    "11.3": "Implement configuration loader with validation",
    "11.4": "Provide complete user and architecture documentation",
    "11.5": "Validate all config parameters on startup with clear errors",
    "11.7": "Report actionable error messages with field names and descriptions",
}

# ─────────────────────────────────────────────────────────────
# Property → Requirement mapping
# ─────────────────────────────────────────────────────────────

PROPERTIES: Dict[str, Dict] = {
    "Property 1":  {"desc": "GBN window constraint",             "requirements": ["5.1", "5.3"]},
    "Property 2":  {"desc": "GBN cumulative ACK ordering",       "requirements": ["5.1", "5.5"]},
    "Property 3":  {"desc": "GBN retransmission on timeout",     "requirements": ["5.1", "5.4"]},
    "Property 4":  {"desc": "SR window constraint",              "requirements": ["5.2", "5.3"]},
    "Property 5":  {"desc": "SR selective ACK correctness",      "requirements": ["5.2", "5.5"]},
    "Property 6":  {"desc": "SR out-of-order buffering",         "requirements": ["5.2"]},
    "Property 7":  {"desc": "Sliding window monotonicity",       "requirements": ["5.1", "5.2", "5.3"]},
    "Property 8":  {"desc": "MAC layer frame delivery",          "requirements": ["3.2"]},
    "Property 9":  {"desc": "CRC error detection",               "requirements": ["3.1"]},
    "Property 10": {"desc": "Physical layer loss model",         "requirements": ["2.2"]},
    "Property 11": {"desc": "Physical layer delay model",        "requirements": ["2.1"]},
    "Property 12": {"desc": "Network layer routing correctness", "requirements": ["4.1", "4.3"]},
    "Property 13": {"desc": "Dijkstra shortest path",           "requirements": ["4.1"]},
    "Property 14": {"desc": "Distance vector convergence",      "requirements": ["4.2"]},
    "Property 15": {"desc": "Data model serialization",         "requirements": ["10.5"]},
    "Property 16": {"desc": "Data model round-trip fidelity",   "requirements": ["10.5"]},
    "Property 17": {"desc": "Application layer traffic pattern","requirements": ["6.2"]},
    "Property 18": {"desc": "File transfer completeness",       "requirements": ["6.1", "6.3"]},
    "Property 19": {"desc": "Congestion detection accuracy",    "requirements": ["8.1"]},
    "Property 20": {"desc": "Flow controller stability",        "requirements": ["8.2"]},
    "Property 21": {"desc": "Layer integration data passing",   "requirements": ["1.1"]},
    "Property 22": {"desc": "Layer integration ordering",       "requirements": ["1.1"]},
    "Property 23": {"desc": "Dashboard metric tracking",        "requirements": ["10.8"]},
    "Property 24": {"desc": "Dashboard comparison view",        "requirements": ["10.8"]},
    "Property 25": {"desc": "Metrics calculator correctness",   "requirements": ["10.8"]},
    "Property 26": {"desc": "Statistics collector accuracy",    "requirements": ["10.8"]},
    "Property 27": {"desc": "Optimization module improvement",  "requirements": ["8.3"]},
    "Property 28": {"desc": "Simulation controller determinism","requirements": ["9.3"]},
    "Property 29": {"desc": "Simulation multi-run consistency", "requirements": ["9.4"]},
    "Property 30": {"desc": "DV routing metric optimality",     "requirements": ["4.2"]},
    "Property 31": {"desc": "GBN vs SR throughput comparison",  "requirements": ["5.1", "5.2", "8.3"]},
    "Property 32": {"desc": "Adaptive window adjustment",       "requirements": ["7.2", "7.3"]},
    "Property 33": {"desc": "Adaptive improvement over static", "requirements": ["7.1", "8.3"]},
    "Property 34": {"desc": "Protocol behavior logging completeness", "requirements": ["10.3"]},
    "Property 35": {"desc": "Log export format validity",       "requirements": ["10.5", "10.6", "10.7"]},
    "Property 37": {"desc": "Performance comparison report generation", "requirements": ["10.8"]},
    "Property 38": {"desc": "Configuration validation on startup", "requirements": ["11.5", "11.7"]},
}

# ─────────────────────────────────────────────────────────────
# Test file → task mapping
# ─────────────────────────────────────────────────────────────

TEST_FILES = {
    "tests/test_properties_gbn.py":             {"task": "Task 18", "type": "property"},
    "tests/test_properties_sr.py":              {"task": "Task 19", "type": "property"},
    "tests/test_properties_sliding_window.py":  {"task": "Task 20", "type": "property"},
    "tests/test_properties_mac_layer.py":       {"task": "Task 14", "type": "property"},
    "tests/test_properties_data_link.py":       {"task": "Task 13", "type": "property"},
    "tests/test_properties_network_layer.py":   {"task": "Task 16", "type": "property"},
    "tests/test_properties_distance_vector.py": {"task": "Task 17", "type": "property"},
    "tests/test_properties_data_serialization.py": {"task": "Task 12", "type": "property"},
    "tests/test_properties_application.py":     {"task": "Task 21", "type": "property"},
    "tests/test_properties_congestion.py":      {"task": "Task 22", "type": "property"},
    "tests/test_properties_layer_integration.py": {"task": "Task 23", "type": "property"},
    "tests/test_properties_dashboard.py":       {"task": "Task 23", "type": "property"},
    "tests/test_properties_metrics.py":         {"task": "Task 23", "type": "property"},
    "tests/test_properties_stats_logging.py":   {"task": "Task 23", "type": "property"},
    "tests/test_properties_optimization.py":    {"task": "Task 23", "type": "property"},
    "tests/test_properties_simulation.py":      {"task": "Task 23", "type": "property"},
    "tests/test_properties_logging_reporting.py": {"task": "Task 24", "type": "property"},
    "tests/test_properties_config_validation.py": {"task": "Task 25", "type": "property"},
    "tests/test_e2e_system.py":                 {"task": "Task 27", "type": "e2e"},
    "tests/test_data_models.py":                {"task": "Task 11", "type": "unit"},
    "tests/test_data_link_layer.py":            {"task": "Task 13", "type": "unit"},
    "tests/test_physical_layer.py":             {"task": "Task 12", "type": "unit"},
    "tests/test_network_layer.py":              {"task": "Task 16", "type": "unit"},
    "tests/test_mac_layer.py":                  {"task": "Task 14", "type": "unit"},
    "tests/test_dijkstra_router.py":            {"task": "Task 16", "type": "unit"},
    "tests/test_distance_vector_router.py":     {"task": "Task 17", "type": "unit"},
    "tests/test_icmp_simulator.py":             {"task": "Task 16", "type": "unit"},
    "tests/test_application_layer.py":          {"task": "Task 21", "type": "unit"},
    "tests/test_utils.py":                      {"task": "Task 11", "type": "unit"},
    "tests/test_routing_table.py":              {"task": "Task 16", "type": "unit"},
    "tests/test_routing_verification.py":       {"task": "Task 16", "type": "unit"},
    "tests/test_transport_protocol_behavior.py":{"task": "Task 18", "type": "integration"},
    "tests/test_transport_reliable_delivery.py":{"task": "Task 19", "type": "integration"},
    "tests/test_integration_frame_transmission.py": {"task": "Task 23", "type": "integration"},
    "tests/test_integration_layer_communication.py":{"task": "Task 23", "type": "integration"},
    "tests/test_packet_forwarding_integration.py":  {"task": "Task 16", "type": "integration"},
    "tests/test_packet_forwarding_simple.py":       {"task": "Task 16", "type": "integration"},
    "tests/test_error_handling_mechanisms.py":      {"task": "Task 23", "type": "integration"},
    "tests/test_infrastructure.py":                 {"task": "Task 11", "type": "unit"},
}

# ─────────────────────────────────────────────────────────────
# Source module → requirement mapping
# ─────────────────────────────────────────────────────────────

SOURCE_MODULES: Dict[str, List[str]] = {
    "src/physical_layer.py":         ["2.1", "2.2", "2.3", "2.4"],
    "src/data_link_layer.py":        ["3.1", "3.4"],
    "src/mac_layer.py":              ["3.2", "3.3"],
    "src/network_layer.py":          ["4.3", "4.4"],
    "src/dijkstra_router.py":        ["4.1"],
    "src/distance_vector_router.py": ["4.2"],
    "src/routing_table.py":          ["4.3"],
    "src/gbn_protocol.py":           ["5.1", "5.3", "5.4", "5.5"],
    "src/sr_protocol.py":            ["5.2", "5.3", "5.4", "5.5"],
    "src/transport_layer.py":        ["5.1", "5.2", "5.3", "5.4"],
    "src/application_layer.py":      ["6.1", "6.2", "6.3"],
    "src/file_transfer_service.py":  ["6.1", "6.3"],
    "src/traffic_generator.py":      ["6.2"],
    "src/congestion_detector.py":    ["8.1"],
    "src/flow_controller.py":        ["8.2"],
    "src/optimization_module.py":    ["7.1", "7.2", "7.3", "8.3"],
    "src/event_queue.py":            ["9.1"],
    "src/simulation_controller.py":  ["9.1", "9.2", "9.3"],
    "src/experiment_manager.py":     ["9.2", "9.4"],
    "src/protocol_logger.py":        ["10.3"],
    "src/data_exporter.py":          ["10.5", "10.6", "10.7"],
    "src/report_generator.py":       ["10.8"],
    "src/comparison_engine.py":      ["8.3", "10.8"],
    "src/metrics_calculator.py":     ["10.8"],
    "src/performance_logger.py":     ["10.3"],
    "src/decision_logger.py":        ["10.3"],
    "src/statistics_collector.py":   ["10.8"],
    "src/dashboard.py":              ["10.8"],
    "src/config_loader.py":          ["11.2", "11.3", "11.5", "11.7"],
    "src/config.py":                 ["11.2"],
    "src/data_models.py":            ["1.1"],
    "src/network_topology.py":       ["1.1", "4.3"],
    "src/node.py":                   ["1.1"],
    "src/utils.py":                  ["1.4"],
}

# ─────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────

@dataclass
class RequirementStatus:
    req_id:        str
    description:   str
    implemented_by: List[str] = field(default_factory=list)
    tested_by:      List[str] = field(default_factory=list)
    properties:     List[str] = field(default_factory=list)
    status:         str = "NOT_IMPLEMENTED"   # IMPLEMENTED | TESTED | NOT_IMPLEMENTED


def analyse() -> Dict[str, RequirementStatus]:
    statuses: Dict[str, RequirementStatus] = {
        rid: RequirementStatus(req_id=rid, description=desc)
        for rid, desc in REQUIREMENTS.items()
    }

    # Mark implementation
    for module, reqs in SOURCE_MODULES.items():
        for req in reqs:
            if req in statuses:
                statuses[req].implemented_by.append(module)

    # Mark property test coverage
    for prop_name, prop in PROPERTIES.items():
        for req in prop["requirements"]:
            if req in statuses:
                statuses[req].properties.append(prop_name)

    # Mark test file coverage (by requirement via property mapping)
    for test_file, meta in TEST_FILES.items():
        # All requirements covered by properties tested in this file
        # (simplified: credit all requirements for the task it covers)
        pass

    # Determine status
    for rid, s in statuses.items():
        if s.implemented_by and s.properties:
            s.status = "TESTED"
        elif s.implemented_by:
            s.status = "IMPLEMENTED"
        else:
            s.status = "NOT_IMPLEMENTED"

    return statuses


# ─────────────────────────────────────────────────────────────
# Scan test files for actual test counts
# ─────────────────────────────────────────────────────────────

def count_tests_in_file(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^\s*def test_", text, re.MULTILINE))


def scan_test_suite(project_root: Path) -> Dict[str, Dict]:
    results = {}
    total_unit        = 0
    total_property    = 0
    total_integration = 0
    total_e2e         = 0

    for rel_path, meta in TEST_FILES.items():
        abs_path = project_root / rel_path
        count    = count_tests_in_file(abs_path)
        exists   = abs_path.exists()
        results[rel_path] = {
            **meta,
            "exists": exists,
            "test_count": count,
        }
        if exists:
            t = meta["type"]
            if t == "unit":        total_unit        += count
            elif t == "property":  total_property    += count
            elif t == "integration": total_integration += count
            elif t == "e2e":       total_e2e         += count

    return {
        "files": results,
        "totals": {
            "unit":        total_unit,
            "property":    total_property,
            "integration": total_integration,
            "e2e":         total_e2e,
            "grand_total": total_unit + total_property + total_integration + total_e2e,
        },
    }


# ─────────────────────────────────────────────────────────────
# Report rendering
# ─────────────────────────────────────────────────────────────

def render_markdown(statuses: Dict[str, RequirementStatus],
                    suite_data: Dict,
                    project_root: Path) -> str:
    now     = datetime.now().strftime("%Y-%m-%d %H:%M")
    totals  = suite_data["totals"]
    files   = suite_data["files"]

    tested_count      = sum(1 for s in statuses.values() if s.status == "TESTED")
    implemented_count = sum(1 for s in statuses.values() if s.status == "IMPLEMENTED")
    missing_count     = sum(1 for s in statuses.values() if s.status == "NOT_IMPLEMENTED")
    total_reqs        = len(statuses)
    coverage_pct      = round((tested_count + implemented_count) / total_reqs * 100, 1)

    lines = [
        f"# Requirements Coverage Report",
        f"",
        f"> Generated: {now}  |  Task 27.3",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total requirements | {total_reqs} |",
        f"| ✅ Implemented + Tested | {tested_count} |",
        f"| 🟡 Implemented (no property test) | {implemented_count} |",
        f"| ❌ Not implemented | {missing_count} |",
        f"| **Overall coverage** | **{coverage_pct}%** |",
        f"",
        f"### Test Suite Breakdown",
        f"",
        f"| Type | Count |",
        f"|------|-------|",
        f"| Unit tests | {totals['unit']} |",
        f"| Property tests | {totals['property']} |",
        f"| Integration tests | {totals['integration']} |",
        f"| End-to-end tests | {totals['e2e']} |",
        f"| **Grand total** | **{totals['grand_total']}** |",
        f"",
        f"---",
        f"",
        f"## Requirements Traceability Matrix",
        f"",
        f"| Req | Description | Status | Implemented In | Tested By |",
        f"|-----|-------------|--------|----------------|-----------|",
    ]

    for rid, s in sorted(statuses.items(), key=lambda x: [int(p) for p in x[0].split(".")]):
        icon  = "✅" if s.status == "TESTED" else ("🟡" if s.status == "IMPLEMENTED" else "❌")
        impls = ", ".join(f"`{m.split('/')[-1]}`" for m in s.implemented_by) or "—"
        props = ", ".join(s.properties) or "—"
        lines.append(f"| {rid} | {s.description[:60]} | {icon} {s.status} | {impls} | {props} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Test File Inventory",
        f"",
        f"| File | Task | Type | Exists | Tests |",
        f"|------|------|------|--------|-------|",
    ]

    for fpath, meta in sorted(files.items()):
        exists = "✅" if meta["exists"] else "❌ MISSING"
        lines.append(
            f"| `{fpath}` | {meta['task']} | {meta['type']} | {exists} | {meta['test_count']} |"
        )

    missing_files = [f for f, m in files.items() if not m["exists"]]
    if missing_files:
        lines += [
            f"",
            f"---",
            f"",
            f"## ⚠️  Missing Test Files",
            f"",
            f"The following test files are tracked but not yet present:",
            f"",
        ]
        for f in missing_files:
            lines.append(f"- `{f}`")

    lines += [
        f"",
        f"---",
        f"",
        f"## Property → Requirement Mapping",
        f"",
        f"| Property | Description | Requirements Covered |",
        f"|----------|-------------|---------------------|",
    ]
    for prop_name, prop in sorted(PROPERTIES.items(), key=lambda x: int(x[0].split()[-1])):
        reqs = ", ".join(prop["requirements"])
        lines.append(f"| {prop_name} | {prop['desc']} | {reqs} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Source Module → Requirement Mapping",
        f"",
        f"| Module | Requirements |",
        f"|--------|-------------|",
    ]
    for mod, reqs in sorted(SOURCE_MODULES.items()):
        lines.append(f"| `{mod}` | {', '.join(reqs)} |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    # Locate project root (parent of this script's location)
    script_dir   = Path(__file__).parent
    project_root = script_dir

    # If running from PROJECT root, tests/ is a sibling
    if not (project_root / "tests").exists():
        project_root = script_dir.parent

    print(f"Project root: {project_root}")

    # Analyse requirements
    statuses   = analyse()
    suite_data = scan_test_suite(project_root)

    # Render markdown
    md   = render_markdown(statuses, suite_data, project_root)
    docs = project_root / "docs"
    docs.mkdir(exist_ok=True)

    md_path = docs / "REQUIREMENTS_COVERAGE.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"✅ Markdown report → {md_path}")

    # Render JSON
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_requirements": len(statuses),
            "tested":      sum(1 for s in statuses.values() if s.status == "TESTED"),
            "implemented": sum(1 for s in statuses.values() if s.status == "IMPLEMENTED"),
            "missing":     sum(1 for s in statuses.values() if s.status == "NOT_IMPLEMENTED"),
        },
        "test_counts": suite_data["totals"],
        "requirements": {rid: asdict(s) for rid, s in statuses.items()},
        "properties":   PROPERTIES,
        "test_files":   suite_data["files"],
    }
    json_path = docs / "REQUIREMENTS_COVERAGE.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"✅ JSON report    → {json_path}")

    # Print summary to stdout
    totals = suite_data["totals"]
    tested = report_data["summary"]["tested"]
    impl   = report_data["summary"]["implemented"]
    miss   = report_data["summary"]["missing"]
    total  = report_data["summary"]["total_requirements"]
    cov    = round((tested + impl) / total * 100, 1)

    print()
    print("=" * 55)
    print("  REQUIREMENTS COVERAGE SUMMARY")
    print("=" * 55)
    print(f"  Requirements:  {total}")
    print(f"  ✅ Tested:     {tested}")
    print(f"  🟡 Implemented:{impl}")
    print(f"  ❌ Missing:    {miss}")
    print(f"  Coverage:      {cov}%")
    print()
    print(f"  Unit tests:        {totals['unit']}")
    print(f"  Property tests:    {totals['property']}")
    print(f"  Integration tests: {totals['integration']}")
    print(f"  E2E tests:         {totals['e2e']}")
    print(f"  Grand total:       {totals['grand_total']}")
    print("=" * 55)

    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
