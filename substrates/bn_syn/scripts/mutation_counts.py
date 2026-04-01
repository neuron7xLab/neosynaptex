#!/usr/bin/env python3
"""Canonical mutation metrics model and extraction for CI and gates."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Final


GITHUB_OUTPUT_KEYS: Final[tuple[str, ...]] = (
    "baseline_score",
    "tolerance",
    "min_acceptable",
    "score",
    "total",
    "killed",
)


@dataclass(frozen=True)
class MutationCounts:
    """Normalized mutmut result counts for scoring."""

    killed: int
    survived: int
    timeout: int
    suspicious: int
    skipped: int
    untested: int

    @property
    def total_scored(self) -> int:
        """Total mutants included in score denominator."""
        return self.killed + self.survived + self.timeout + self.suspicious

    @property
    def killed_equivalent(self) -> int:
        """Mutants counted as killed for score numerator."""
        return self.killed + self.timeout


@dataclass(frozen=True)
class MutationBaseline:
    """Mutation score baseline contract loaded from quality artifacts."""

    baseline_score: float
    tolerance_delta: float
    status: str
    total_mutants: int

    @property
    def min_acceptable(self) -> float:
        """Minimum score accepted by CI gate."""
        return self.baseline_score - self.tolerance_delta


@dataclass(frozen=True)
class MutationAssessment:
    """Derived CI mutation metrics for output/reporting."""

    counts: MutationCounts
    baseline: MutationBaseline
    score: float

    @property
    def gate_passes(self) -> bool:
        return self.score >= self.baseline.min_acceptable

    @property
    def delta_vs_baseline(self) -> float:
        return round(self.score - self.baseline.baseline_score, 2)

    @property
    def gap_vs_minimum(self) -> float:
        return round(self.score - self.baseline.min_acceptable, 2)


def _count_ids_for_status(status: str) -> int:
    """Count mutmut IDs for a given status using machine-stable result-ids output."""
    result = subprocess.run(
        ["mutmut", "result-ids", status],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip()
    if not output:
        return 0
    return len(output.split())


def read_mutation_counts() -> MutationCounts:
    """Read canonical mutation counts from mutmut result IDs."""
    return MutationCounts(
        killed=_count_ids_for_status("killed"),
        survived=_count_ids_for_status("survived"),
        timeout=_count_ids_for_status("timeout"),
        suspicious=_count_ids_for_status("suspicious"),
        skipped=_count_ids_for_status("skipped"),
        untested=_count_ids_for_status("untested"),
    )


def calculate_score(counts: MutationCounts) -> float:
    """Calculate mutation score as percentage."""
    if counts.total_scored == 0:
        return 0.0
    return round(100.0 * counts.killed_equivalent / counts.total_scored, 2)


def load_mutation_baseline(path: Path = Path("quality/mutation_baseline.json")) -> MutationBaseline:
    """Load and normalize mutation baseline config."""
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    return MutationBaseline(
        baseline_score=float(payload["baseline_score"]),
        tolerance_delta=float(payload["tolerance_delta"]),
        status=str(payload.get("status", "")),
        total_mutants=int(payload.get("metrics", {}).get("total_mutants", 0)),
    )


def assess_mutation_gate(
    counts: MutationCounts,
    baseline: MutationBaseline,
) -> MutationAssessment:
    """Build immutable mutation assessment from canonical source data."""
    return MutationAssessment(counts=counts, baseline=baseline, score=calculate_score(counts))


def render_ci_summary_markdown(assessment: MutationAssessment) -> str:
    """Render deterministic, data-dense markdown for GitHub Actions summary."""
    status = "✅ PASS" if assessment.gate_passes else "❌ FAIL"
    lines = [
        "## Mutation Testing Results",
        "",
        f"**Gate Status:** {status}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Mutation score | {assessment.score:.2f}% |",
        f"| Baseline score | {assessment.baseline.baseline_score:.2f}% |",
        f"| Tolerance delta | ±{assessment.baseline.tolerance_delta:.2f}% |",
        f"| Minimum acceptable | {assessment.baseline.min_acceptable:.2f}% |",
        f"| Delta vs baseline | {assessment.delta_vs_baseline:+.2f}% |",
        f"| Gap vs minimum acceptable | {assessment.gap_vs_minimum:+.2f}% |",
        f"| Killed (incl. timeout) | {assessment.counts.killed_equivalent} |",
        f"| Survived | {assessment.counts.survived} |",
        f"| Timeout | {assessment.counts.timeout} |",
        f"| Suspicious | {assessment.counts.suspicious} |",
        f"| Scored denominator | {assessment.counts.total_scored} |",
        f"| Skipped | {assessment.counts.skipped} |",
        f"| Untested | {assessment.counts.untested} |",
        "",
    ]
    return "\n".join(lines)


def render_github_output_lines(assessment: MutationAssessment) -> str:
    """Render deterministic GitHub output entries from canonical assessment."""
    output_map = {
        "baseline_score": f"{assessment.baseline.baseline_score:.2f}",
        "tolerance": f"{assessment.baseline.tolerance_delta:.2f}",
        "min_acceptable": f"{assessment.baseline.min_acceptable:.2f}",
        "score": f"{assessment.score:.2f}",
        "total": str(assessment.counts.total_scored),
        "killed": str(assessment.counts.killed_equivalent),
    }
    lines = [f"{key}={output_map[key]}" for key in GITHUB_OUTPUT_KEYS]
    return "\n".join(lines) + "\n"
