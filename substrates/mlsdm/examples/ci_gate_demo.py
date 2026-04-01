#!/usr/bin/env python3
"""
Demo script showing CI Performance & Resilience Gate in action.

This script demonstrates the gate's capabilities without requiring actual PR data.
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from ci_perf_resilience_gate import (  # noqa: E402
    ChangeClass,
    CIPerfResilienceGate,
    FileChange,
    JobResult,
    JobStatus,
)


def demo_documentation_pr():
    """Demonstrate analysis of a documentation-only PR."""
    print("=" * 80)
    print("DEMO 1: Documentation-Only PR")
    print("=" * 80)
    print()

    gate = CIPerfResilienceGate()

    # Simulate a doc-only PR
    changes = [
        FileChange("README.md", ChangeClass.DOC_ONLY, "Documentation file"),
        FileChange("docs/guide.md", ChangeClass.DOC_ONLY, "Documentation file"),
        FileChange("CHANGELOG.md", ChangeClass.DOC_ONLY, "Documentation file"),
    ]

    job_results = [
        JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed | Duration: 2m15s"),
        JobResult("Security Vulnerability Scan", JobStatus.SUCCESS, "Passed | Duration: 1m30s"),
        JobResult("Unit and Integration Tests", JobStatus.SUCCESS, "Passed | Duration: 5m20s"),
    ]

    mode, mode_reasons = gate.risk_classifier.classify(changes, job_results, [])
    verdict, actions, reasons = gate.merge_verdictor.determine_verdict(mode, job_results)

    print(f"Mode: {mode.value}")
    print(f"Reasoning: {', '.join(mode_reasons)}")
    print()
    print(f"Verdict: {verdict}")
    print(f"Reasons: {', '.join(reasons)}")
    print()


def demo_critical_path_pr():
    """Demonstrate analysis of a PR with critical changes."""
    print("=" * 80)
    print("DEMO 2: Critical Path PR (Missing Performance Tests)")
    print("=" * 80)
    print()

    gate = CIPerfResilienceGate()

    # Simulate a PR touching critical paths
    changes = [
        FileChange(
            "src/mlsdm/neuro_engine/core.py",
            ChangeClass.CORE_CRITICAL,
            "File in critical path: src/mlsdm/neuro_engine",
        ),
        FileChange(
            "src/mlsdm/circuit_breaker/breaker.py",
            ChangeClass.CORE_CRITICAL,
            "File in critical path: src/mlsdm/circuit_breaker",
        ),
        FileChange(
            "tests/test_neuro_engine.py",
            ChangeClass.NON_CORE_CODE,
            "Utility or non-critical code change",
        ),
    ]

    job_results = [
        JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed | Duration: 2m15s"),
        JobResult("Security Vulnerability Scan", JobStatus.SUCCESS, "Passed | Duration: 1m30s"),
        JobResult("Unit and Integration Tests", JobStatus.SUCCESS, "Passed | Duration: 5m20s"),
        JobResult(
            "Performance & Resilience Validation / Fast Resilience Tests",
            JobStatus.SKIPPED,
            "Skipped (conditions not met)",
        ),
        JobResult(
            "Performance & Resilience Validation / Performance & SLO Validation",
            JobStatus.SKIPPED,
            "Skipped (conditions not met)",
        ),
    ]

    mode, mode_reasons = gate.risk_classifier.classify(changes, job_results, [])
    verdict, actions, reasons = gate.merge_verdictor.determine_verdict(mode, job_results)

    print(f"Mode: {mode.value}")
    print(f"Reasoning: {', '.join(mode_reasons)}")
    print()
    print(f"Verdict: {verdict}")
    if actions:
        print("Required Actions:")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action}")
    print()


def demo_release_pr():
    """Demonstrate analysis of a release PR."""
    print("=" * 80)
    print("DEMO 3: Release PR (All Tests Required)")
    print("=" * 80)
    print()

    gate = CIPerfResilienceGate()

    # Simulate a release PR
    changes = [
        FileChange(
            "src/mlsdm/neuro_engine/core.py",
            ChangeClass.CORE_CRITICAL,
            "File in critical path: src/mlsdm/neuro_engine",
        ),
        FileChange(
            "config/production.yaml",
            ChangeClass.CORE_CRITICAL,
            "File in critical path: config/",
        ),
        FileChange("CHANGELOG.md", ChangeClass.DOC_ONLY, "Documentation file"),
    ]

    job_results = [
        JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed | Duration: 2m15s"),
        JobResult("Security Vulnerability Scan", JobStatus.SUCCESS, "Passed | Duration: 1m30s"),
        JobResult("Unit and Integration Tests", JobStatus.SUCCESS, "Passed | Duration: 5m20s"),
        JobResult(
            "Performance & Resilience Validation / Fast Resilience Tests",
            JobStatus.SUCCESS,
            "Passed | Duration: 3m45s",
        ),
        JobResult(
            "Performance & Resilience Validation / Performance & SLO Validation",
            JobStatus.SUCCESS,
            "Passed | Duration: 5m10s",
        ),
        JobResult(
            "Performance & Resilience Validation / Comprehensive Resilience Tests",
            JobStatus.SUCCESS,
            "Passed | Duration: 12m30s",
        ),
    ]

    mode, mode_reasons = gate.risk_classifier.classify(changes, job_results, ["release", "v1.2.0"])
    verdict, actions, reasons = gate.merge_verdictor.determine_verdict(mode, job_results)

    print(f"Mode: {mode.value}")
    print(f"Reasoning: {', '.join(mode_reasons)}")
    print()
    print(f"Verdict: {verdict}")
    print("Reasons:")
    for reason in reasons:
        print(f"  - {reason}")
    print()


def demo_failed_tests():
    """Demonstrate analysis of a PR with failed tests."""
    print("=" * 80)
    print("DEMO 4: PR with Failed Tests")
    print("=" * 80)
    print()

    gate = CIPerfResilienceGate()

    changes = [
        FileChange(
            "src/mlsdm/rate_limiter.py",
            ChangeClass.CORE_CRITICAL,
            "Contains critical patterns: timeout, rate_limit",
        ),
    ]

    job_results = [
        JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed | Duration: 2m15s"),
        JobResult(
            "Security Vulnerability Scan",
            JobStatus.FAILURE,
            "Failed | Failed steps: Run pip-audit",
        ),
        JobResult("Unit and Integration Tests", JobStatus.SUCCESS, "Passed | Duration: 5m20s"),
        JobResult(
            "Performance & Resilience Validation / Fast Resilience Tests",
            JobStatus.SUCCESS,
            "Passed | Duration: 3m45s",
        ),
        JobResult(
            "Performance & Resilience Validation / Performance & SLO Validation",
            JobStatus.FAILURE,
            "Failed | Failed steps: Run SLO validation",
        ),
    ]

    mode, mode_reasons = gate.risk_classifier.classify(changes, job_results, [])
    verdict, actions, reasons = gate.merge_verdictor.determine_verdict(mode, job_results)

    print(f"Mode: {mode.value}")
    print(f"Reasoning: {', '.join(mode_reasons)}")
    print()
    print(f"Verdict: {verdict}")
    if actions:
        print("Required Actions:")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action}")
    print(f"Reasons: {', '.join(reasons)}")
    print()


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("CI PERFORMANCE & RESILIENCE GATE DEMONSTRATION")
    print("=" * 80)
    print()
    print("This demo shows how the gate analyzes different types of PRs.")
    print()

    demo_documentation_pr()
    demo_critical_path_pr()
    demo_release_pr()
    demo_failed_tests()

    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print()
    print("To analyze a real PR, use:")
    print("  python scripts/ci_perf_resilience_gate.py --pr-url <github_pr_url>")
    print()


if __name__ == "__main__":
    main()
