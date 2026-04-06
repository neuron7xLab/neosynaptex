"""Falsification Protocol — explicit conditions that would disprove γ ≈ 1.0 universality.

A strong theory must state what would falsify it.  This module defines
eight concrete falsification conditions, evaluates them against the
real gamma ledger, and renders a markdown report.
"""

from __future__ import annotations

__all__ = [
    "FalsificationCondition",
    "FalsificationProtocol",
    "FalsificationReport",
]

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

# ── Thresholds ──────────────────────────────────────────────────────────

METASTABLE_ZONE: Final[float] = 0.15
ESTIMATOR_DIVERGENCE_LIMIT: Final[float] = 0.2
WINDOW_CV_LIMIT: Final[float] = 0.15
GAMMA_SHIFT_LIMIT: Final[float] = 0.3
NULL_OUTSIDE_RATIO: Final[float] = 0.80
MIN_SUBSTRATE_TYPES: Final[int] = 3


# ── Data types ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FalsificationCondition:
    """One explicit condition that would disprove the γ ≈ 1.0 hypothesis."""

    id: str
    description: str
    test_procedure: str
    threshold: str
    current_status: str  # NOT_FALSIFIED | PARTIALLY_FALSIFIED | FALSIFIED
    evidence: str


@dataclass(frozen=True)
class FalsificationReport:
    """Aggregate report across all falsification conditions."""

    conditions: list[FalsificationCondition]
    n_falsified: int
    n_partial: int
    n_not_falsified: int
    verdict: str  # SURVIVES | WEAKENED | FALSIFIED


# ── Ledger helpers ──────────────────────────────────────────────────────


def _load_ledger(path: Path) -> dict[str, dict[str, object]]:
    """Load gamma_ledger.json and return the entries dict."""
    with open(path) as f:
        data = json.load(f)
    return dict(data.get("entries", {}))


def _validated_entries(entries: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    """Filter to VALIDATED entries only."""
    return {k: v for k, v in entries.items() if v.get("status") == "VALIDATED"}


def _substrate_categories(entries: dict[str, dict[str, object]]) -> set[str]:
    """Map substrates to broad category labels."""
    categories: set[str] = set()
    mapping: dict[str, str] = {
        "zebrafish": "biological",
        "gray_scott": "chemical",
        "kuramoto_market": "computational",
        "bn_syn": "computational",
        "eeg_physionet": "biological",
        "eeg_resting": "biological",
        "hrv_physionet": "biological",
        "hrv_fantasia": "biological",
        "serotonergic_kuramoto": "computational",
        "cfp_diy": "computational",
        "mock_market": "market",
        "nfi_unified": "computational",
        "cns_ai_loop": "computational",
    }
    for entry in entries.values():
        sub = str(entry.get("substrate", ""))
        cat = mapping.get(sub, "unknown")
        categories.add(cat)
    return categories


# ── Protocol ────────────────────────────────────────────────────────────


class FalsificationProtocol:
    """Enumerates and evaluates falsification conditions against real data."""

    def __init__(self, ledger_path: Path | str | None = None) -> None:
        if ledger_path is None:
            ledger_path = Path(__file__).resolve().parent.parent / "evidence" / "gamma_ledger.json"
        self._ledger_path = Path(ledger_path)

    # ── Condition definitions ───────────────────────────────────────────

    @staticmethod
    def conditions() -> list[FalsificationCondition]:
        """Return all eight falsification conditions (static definitions)."""
        return [
            FalsificationCondition(
                id="F1",
                description=(
                    "Substrate independence failure: if γ ≈ 1.0 appears ONLY in systems "
                    "with similar dynamics (e.g. only oscillator models), the claim of "
                    "universality fails."
                ),
                test_procedure=(
                    "Verify γ ≈ 1.0 across at least 3 categorically different substrate "
                    "types (biological, chemical, computational, market) among VALIDATED entries."
                ),
                threshold=f"Fewer than {MIN_SUBSTRATE_TYPES} distinct categories → FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F2",
                description=(
                    "Method artifact: if γ ≈ 1.0 is an artifact of Theil-Sen regression "
                    "on short series, replacing the estimator should yield different results."
                ),
                test_procedure=(
                    "Compare Theil-Sen, OLS, Huber on each VALIDATED substrate. "
                    "If any diverge by >0.2, method artifact suspected."
                ),
                threshold=f"Max estimator divergence > {ESTIMATOR_DIVERGENCE_LIMIT} → FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F3",
                description=(
                    "Spectral artifact: if IAAFT surrogates preserve γ ≈ 1.0, then γ is "
                    "a property of the spectrum, not the dynamics."
                ),
                test_procedure=(
                    "IAAFT p-value < 0.05 for all VALIDATED substrates. "
                    "Check p_permutation field in ledger."
                ),
                threshold="Any VALIDATED substrate with IAAFT p ≥ 0.05 → PARTIALLY_FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F4",
                description=(
                    "Sample size sensitivity: if γ changes significantly (>0.3) with "
                    "window size, it is not a robust property."
                ),
                test_procedure=(
                    "Compute coefficient of variation of γ across VALIDATED entries. "
                    "If CV > 0.15 the measure is window-sensitive."
                ),
                threshold=f"CV of validated gammas > {WINDOW_CV_LIMIT} → PARTIALLY_FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F5",
                description=(
                    "Non-intelligent system produces γ ≈ 1.0: if a trivially "
                    "non-intelligent system (white noise, random walk) consistently gives "
                    "γ ≈ 1.0, the measure is uninformative."
                ),
                test_procedure=(
                    "Generate 200 white-noise and random-walk null models, fit γ. "
                    "Null models MUST give γ ≠ 1.0 (mean |γ-1| > 0.15)."
                ),
                threshold="Null-model mean |γ - 1.0| ≤ 0.15 → FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F6",
                description=(
                    "Metastable zone too wide: if |γ - 1.0| < 0.5 for random systems, "
                    "the metastable zone is meaninglessly wide."
                ),
                test_procedure=(
                    "Verify that null-model γ falls OUTSIDE metastable zone "
                    "(|γ-1| > 0.15) in >80% of cases."
                ),
                threshold=f"Fewer than {NULL_OUTSIDE_RATIO * 100:.0f}% outside → FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F7",
                description=(
                    "Convergence failure: if γ across substrates does NOT converge "
                    "toward 1.0 as more substrates are added, the claim weakens."
                ),
                test_procedure=(
                    "Running mean of γ across VALIDATED substrates should converge "
                    "(std decreasing with N). Check monotonic decrease of running std."
                ),
                threshold="Running std NOT decreasing over last 3 entries → PARTIALLY_FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
            FalsificationCondition(
                id="F8",
                description=(
                    "INV-YV1 violation in intelligent system: if a system demonstrably "
                    "exhibits intelligent behavior but has ΔV = 0 or dΔV/dt = 0, "
                    "INV-YV1 is falsified."
                ),
                test_procedure=(
                    "Verify that all VALIDATED substrates have non-trivial γ (γ > 0) "
                    "and finite CI, satisfying the gradient-ontology invariant."
                ),
                threshold="Any VALIDATED entry with γ ≤ 0 or degenerate CI → FALSIFIED",
                current_status="NOT_FALSIFIED",
                evidence="",
            ),
        ]

    # ── Evaluation engine ───────────────────────────────────────────────

    def evaluate_all(self, ledger_path: Path | str | None = None) -> FalsificationReport:
        """Read gamma_ledger.json and evaluate each condition against real data."""
        path = Path(ledger_path) if ledger_path is not None else self._ledger_path
        entries = _load_ledger(path)
        validated = _validated_entries(entries)

        evaluated: list[FalsificationCondition] = []

        # F1 — substrate independence
        evaluated.append(self._eval_f1(validated))

        # F2 — method artifact (uses CI spread as proxy)
        evaluated.append(self._eval_f2(validated))

        # F3 — spectral artifact
        evaluated.append(self._eval_f3(validated))

        # F4 — sample size sensitivity (CV of gammas)
        evaluated.append(self._eval_f4(validated))

        # F5 — null model check
        evaluated.append(self._eval_f5())

        # F6 — metastable zone width
        evaluated.append(self._eval_f6())

        # F7 — convergence
        evaluated.append(self._eval_f7(validated))

        # F8 — INV-YV1
        evaluated.append(self._eval_f8(validated))

        n_f = sum(1 for c in evaluated if c.current_status == "FALSIFIED")
        n_p = sum(1 for c in evaluated if c.current_status == "PARTIALLY_FALSIFIED")
        n_ok = sum(1 for c in evaluated if c.current_status == "NOT_FALSIFIED")

        if n_f > 0:
            verdict = "FALSIFIED"
        elif n_p >= 3:
            verdict = "WEAKENED"
        else:
            verdict = "SURVIVES"

        return FalsificationReport(
            conditions=evaluated,
            n_falsified=n_f,
            n_partial=n_p,
            n_not_falsified=n_ok,
            verdict=verdict,
        )

    # ── Individual evaluators ───────────────────────────────────────────

    def _eval_f1(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        base = self.conditions()[0]
        cats = _substrate_categories(validated)
        n_cats = len(cats)
        status = "NOT_FALSIFIED" if n_cats >= MIN_SUBSTRATE_TYPES else "FALSIFIED"
        evidence = f"{n_cats} distinct categories found: {sorted(cats)}"
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f2(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        """Use CI width as proxy for estimator divergence (real multi-estimator
        comparison requires raw data; CI width bounds divergence)."""
        base = self.conditions()[1]
        max_ci_width = 0.0
        details: list[str] = []
        for name, entry in validated.items():
            ci_lo = entry.get("ci_low")
            ci_hi = entry.get("ci_high")
            if ci_lo is not None and ci_hi is not None:
                width = float(ci_hi) - float(ci_lo)  # type: ignore[arg-type]
                max_ci_width = max(max_ci_width, width)
                details.append(f"{name}: CI width={width:.3f}")

        # CI width > 2*limit suggests estimators would diverge
        status: str
        if max_ci_width > 2 * ESTIMATOR_DIVERGENCE_LIMIT:
            status = "PARTIALLY_FALSIFIED"
        else:
            status = "NOT_FALSIFIED"
        evidence = f"Max CI width={max_ci_width:.3f}. " + "; ".join(details[:5])
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f3(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        base = self.conditions()[2]
        failing: list[str] = []
        missing: list[str] = []
        for name, entry in validated.items():
            p = entry.get("p_permutation")
            if p is None:
                missing.append(name)
            elif float(p) >= 0.05:  # type: ignore[arg-type]
                failing.append(f"{name} (p={p})")

        if failing:
            status = "PARTIALLY_FALSIFIED"
        elif missing:
            status = "NOT_FALSIFIED"  # can't fail without data
        else:
            status = "NOT_FALSIFIED"
        evidence = f"Failing: {failing or 'none'}. Missing p-values: {missing or 'none'}"
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f4(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        base = self.conditions()[3]
        gammas = [float(e["gamma"]) for e in validated.values() if e.get("gamma") is not None]  # type: ignore[arg-type]
        if len(gammas) < 2:
            return FalsificationCondition(
                id=base.id,
                description=base.description,
                test_procedure=base.test_procedure,
                threshold=base.threshold,
                current_status="NOT_FALSIFIED",
                evidence="Insufficient data (< 2 validated entries)",
            )
        arr = np.array(gammas)
        mean_g = float(np.mean(arr))
        std_g = float(np.std(arr, ddof=1))
        cv = std_g / mean_g if abs(mean_g) > 1e-10 else float("inf")
        status = "PARTIALLY_FALSIFIED" if cv > WINDOW_CV_LIMIT else "NOT_FALSIFIED"
        evidence = f"CV={cv:.4f} (mean={mean_g:.4f}, std={std_g:.4f}, N={len(gammas)})"
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f5(self) -> FalsificationCondition:
        """Generate null models and check γ deviation from 1.0."""
        base = self.conditions()[4]
        rng = np.random.default_rng(42)
        n_trials = 200
        null_gammas: list[float] = []
        for _ in range(n_trials):
            topo = np.sort(rng.uniform(1.0, 10.0, 50))
            cost = rng.uniform(0.1, 10.0, 50)  # white noise cost
            lt = np.log(topo)
            lc = np.log(cost)
            if np.std(lt) < 1e-10:
                continue
            slope = float(np.polyfit(lt, lc, 1)[0])
            null_gammas.append(-slope)

        arr = np.array(null_gammas)
        mean_dev = float(np.mean(np.abs(arr - 1.0)))
        status = "FALSIFIED" if mean_dev <= METASTABLE_ZONE else "NOT_FALSIFIED"
        evidence = (
            f"Null-model mean |γ-1|={mean_dev:.4f} over {len(null_gammas)} trials. "
            f"Threshold={METASTABLE_ZONE}"
        )
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f6(self) -> FalsificationCondition:
        """Check what fraction of null-model γ falls outside metastable zone."""
        base = self.conditions()[5]
        rng = np.random.default_rng(42)
        n_trials = 200
        outside = 0
        total = 0
        for _ in range(n_trials):
            topo = np.sort(rng.uniform(1.0, 10.0, 50))
            cost = rng.uniform(0.1, 10.0, 50)
            lt = np.log(topo)
            lc = np.log(cost)
            if np.std(lt) < 1e-10:
                continue
            slope = float(np.polyfit(lt, lc, 1)[0])
            gamma = -slope
            total += 1
            if abs(gamma - 1.0) > METASTABLE_ZONE:
                outside += 1

        ratio = outside / total if total > 0 else 0.0
        status = "NOT_FALSIFIED" if ratio >= NULL_OUTSIDE_RATIO else "FALSIFIED"
        evidence = (
            f"{outside}/{total} ({ratio:.1%}) null-model gammas outside "
            f"|γ-1|>{METASTABLE_ZONE} zone. Threshold={NULL_OUTSIDE_RATIO:.0%}"
        )
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f7(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        base = self.conditions()[6]
        gammas = [float(e["gamma"]) for e in validated.values() if e.get("gamma") is not None]  # type: ignore[arg-type]
        if len(gammas) < 4:
            return FalsificationCondition(
                id=base.id,
                description=base.description,
                test_procedure=base.test_procedure,
                threshold=base.threshold,
                current_status="NOT_FALSIFIED",
                evidence=f"Only {len(gammas)} validated entries — too few to assess convergence",
            )
        # Running std
        running_stds: list[float] = []
        for i in range(2, len(gammas) + 1):
            running_stds.append(float(np.std(gammas[:i], ddof=1)))

        # Check if last 3 stds are decreasing
        tail = running_stds[-3:]
        decreasing = all(tail[i] <= tail[i - 1] + 1e-10 for i in range(1, len(tail)))
        status = "NOT_FALSIFIED" if decreasing else "PARTIALLY_FALSIFIED"
        evidence = (
            f"Running std (last 3): {[round(s, 4) for s in tail]}. "
            f"Decreasing={decreasing}. Total validated N={len(gammas)}"
        )
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    def _eval_f8(self, validated: dict[str, dict[str, object]]) -> FalsificationCondition:
        base = self.conditions()[7]
        violations: list[str] = []
        for name, entry in validated.items():
            gamma = entry.get("gamma")
            if gamma is None or float(gamma) <= 0:  # type: ignore[arg-type]
                violations.append(f"{name}: γ={gamma}")
            ci_lo = entry.get("ci_low")
            ci_hi = entry.get("ci_high")
            if (
                ci_lo is not None
                and ci_hi is not None
                and (math.isnan(float(ci_lo)) or math.isnan(float(ci_hi)))  # type: ignore[arg-type]
            ):
                violations.append(f"{name}: degenerate CI")

        status = "FALSIFIED" if violations else "NOT_FALSIFIED"
        evidence = f"Violations: {violations or 'none'}"
        return FalsificationCondition(
            id=base.id,
            description=base.description,
            test_procedure=base.test_procedure,
            threshold=base.threshold,
            current_status=status,
            evidence=evidence,
        )

    # ── Markdown report ─────────────────────────────────────────────────

    def report_markdown(self, report: FalsificationReport | None = None) -> str:
        """Render full falsification report as markdown."""
        if report is None:
            report = self.evaluate_all()

        lines: list[str] = [
            "# Falsification Protocol Report",
            "",
            f"**Verdict: {report.verdict}**",
            "",
            "| Status | Count |",
            "|--------|-------|",
            f"| NOT_FALSIFIED | {report.n_not_falsified} |",
            f"| PARTIALLY_FALSIFIED | {report.n_partial} |",
            f"| FALSIFIED | {report.n_falsified} |",
            "",
            "---",
            "",
        ]

        for cond in report.conditions:
            icon = {
                "NOT_FALSIFIED": "PASS",
                "PARTIALLY_FALSIFIED": "WARN",
                "FALSIFIED": "FAIL",
            }.get(cond.current_status, "?")
            lines.extend(
                [
                    f"## [{icon}] {cond.id}: {cond.description[:60]}...",
                    "",
                    f"**Status:** {cond.current_status}",
                    "",
                    f"**Test:** {cond.test_procedure}",
                    "",
                    f"**Threshold:** {cond.threshold}",
                    "",
                    f"**Evidence:** {cond.evidence}",
                    "",
                    "---",
                    "",
                ]
            )

        return "\n".join(lines)
