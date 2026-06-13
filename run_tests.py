#!/usr/bin/env python3
"""
Master test runner for Task 27.1 — Complete test suite with coverage.

Usage:
    python run_tests.py              # run everything
    python run_tests.py --unit       # unit tests only
    python run_tests.py --property   # property tests only
    python run_tests.py --integration# integration tests only
    python run_tests.py --e2e        # end-to-end tests only
    python run_tests.py --fast       # skip slow hypothesis tests

Outputs:
    - Console summary with pass/fail per category
    - htmlcov/index.html  (coverage HTML report)
    - coverage.xml        (for CI tools)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


# ── Test groups ──────────────────────────────────────────────

UNIT_TESTS = [
    "tests/test_data_models.py",
    "tests/test_data_link_layer.py",
    "tests/test_physical_layer.py",
    "tests/test_network_layer.py",
    "tests/test_mac_layer.py",
    "tests/test_dijkstra_router.py",
    "tests/test_distance_vector_router.py",
    "tests/test_icmp_simulator.py",
    "tests/test_application_layer.py",
    "tests/test_utils.py",
    "tests/test_routing_table.py",
    "tests/test_routing_verification.py",
    "tests/test_infrastructure.py",
]

PROPERTY_TESTS = [
    "tests/test_properties_gbn.py",
    "tests/test_properties_sr.py",
    "tests/test_properties_sliding_window.py",
    "tests/test_properties_mac_layer.py",
    "tests/test_properties_data_link.py",
    "tests/test_properties_network_layer.py",
    "tests/test_properties_distance_vector.py",
    "tests/test_properties_data_serialization.py",
    "tests/test_properties_application.py",
    "tests/test_properties_congestion.py",
    "tests/test_properties_layer_integration.py",
    "tests/test_properties_dashboard.py",
    "tests/test_properties_metrics.py",
    "tests/test_properties_stats_logging.py",
    "tests/test_properties_optimization.py",
    "tests/test_properties_simulation.py",
    "tests/test_properties_logging_reporting.py",
    "tests/test_properties_config_validation.py",
]

INTEGRATION_TESTS = [
    "tests/test_transport_protocol_behavior.py",
    "tests/test_transport_reliable_delivery.py",
    "tests/test_integration_frame_transmission.py",
    "tests/test_integration_layer_communication.py",
    "tests/test_packet_forwarding_integration.py",
    "tests/test_packet_forwarding_simple.py",
    "tests/test_error_handling_mechanisms.py",
]

E2E_TESTS = [
    "tests/test_e2e_system.py",
]


def _existing(files):
    return [f for f in files if Path(f).exists()]


def run_group(label: str, files: list, extra_args: list, coverage: bool, cov_append: bool) -> dict:
    existing = _existing(files)
    missing  = [f for f in files if f not in existing]

    if not existing:
        print(f"\n{'─'*55}")
        print(f"  {label}: NO FILES FOUND — skipped")
        return {"label": label, "passed": 0, "failed": 0, "errors": 0,
                "skipped": len(files), "missing_files": missing, "ran": False}

    print(f"\n{'─'*55}")
    print(f"  Running {label} ({len(existing)}/{len(files)} files found)...")
    if missing:
        print(f"  ⚠️  Missing: {', '.join(missing)}")
    print(f"{'─'*55}")

    cmd = [sys.executable, "-m", "pytest"] + existing + ["-v", "--tb=short"] + extra_args

    if coverage:
        flag = "--cov-append" if cov_append else "--cov=src"
        cmd += [flag, "--cov-report=", f"--cov=src"]

    t0     = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0

    # Parse basic counts from return code (full parsing needs pytest-json-report)
    passed = result.returncode == 0
    print(f"\n  ⏱  {elapsed:.1f}s  |  {'✅ PASSED' if passed else '❌ FAILED'}")

    return {
        "label":         label,
        "returncode":    result.returncode,
        "elapsed_s":     round(elapsed, 1),
        "files_found":   len(existing),
        "files_missing": len(missing),
        "missing_files": missing,
        "ran":           True,
        "ok":            passed,
    }


def main():
    parser = argparse.ArgumentParser(description="Task 27.1 — Full test suite runner")
    parser.add_argument("--unit",        action="store_true", help="Unit tests only")
    parser.add_argument("--property",    action="store_true", help="Property tests only")
    parser.add_argument("--integration", action="store_true", help="Integration tests only")
    parser.add_argument("--e2e",         action="store_true", help="E2E tests only")
    parser.add_argument("--fast",        action="store_true",
                        help="Reduce Hypothesis to 10 examples for speed")
    parser.add_argument("--no-cov",      action="store_true", help="Skip coverage collection")
    parser.add_argument("-x",            action="store_true", help="Stop on first failure")
    args = parser.parse_args()

    run_all = not any([args.unit, args.property, args.integration, args.e2e])

    extra = []
    if args.fast:
        extra += ["--hypothesis-seed=0", "-p", "no:hypothesis"]
        # Actually reduce via settings — simplest way: set env
        import os
        os.environ["HYPOTHESIS_MAX_EXAMPLES"] = "10"
    if args.x:
        extra += ["-x"]

    coverage = not args.no_cov

    print("=" * 55)
    print("  TASK 27.1 — COMPLETE TEST SUITE")
    print("=" * 55)
    if coverage:
        print("  Coverage collection: ON  (htmlcov/index.html)")
    print()

    results = []
    first   = True

    def run(label, files):
        nonlocal first
        r = run_group(label, files, extra, coverage, cov_append=not first)
        results.append(r)
        first = False

    if run_all or args.unit:
        run("UNIT TESTS", UNIT_TESTS)
    if run_all or args.property:
        run("PROPERTY TESTS", PROPERTY_TESTS)
    if run_all or args.integration:
        run("INTEGRATION TESTS", INTEGRATION_TESTS)
    if run_all or args.e2e:
        run("END-TO-END TESTS", E2E_TESTS)

    # Coverage HTML + XML
    if coverage and any(r["ran"] for r in results):
        print(f"\n{'─'*55}")
        print("  Generating coverage reports...")
        subprocess.run([
            sys.executable, "-m", "pytest",
            "--cov=src", "--cov-append",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--collect-only", "-q",   # don't re-run tests
        ], capture_output=False)

    # Final summary
    print(f"\n{'='*55}")
    print("  FINAL SUMMARY")
    print(f"{'='*55}")

    all_ok   = True
    total_elapsed = 0.0
    for r in results:
        if not r["ran"]:
            icon = "⏭ "
        elif r.get("ok"):
            icon = "✅"
        else:
            icon = "❌"
            all_ok = False
        elapsed = f"{r.get('elapsed_s', 0):.1f}s" if r["ran"] else "skipped"
        found   = f"{r.get('files_found',0)}/{r.get('files_found',0)+r.get('files_missing',0)} files"
        print(f"  {icon} {r['label']:30s}  {found}  {elapsed}")
        if r.get("missing_files"):
            for mf in r["missing_files"]:
                print(f"       ↳ missing: {mf}")
        total_elapsed += r.get("elapsed_s", 0)

    print(f"{'─'*55}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Result: {'✅ ALL PASSED' if all_ok else '❌ SOME FAILED'}")
    if coverage:
        print(f"  Coverage HTML: htmlcov/index.html")
        print(f"  Coverage XML:  coverage.xml")
    print(f"{'='*55}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
