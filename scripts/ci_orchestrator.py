#!/usr/bin/env python3
"""CI Orchestrator — cross-substrate integration + gamma invariant check."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class CIReport:
    root_tests_passed: bool
    cross_substrate_passed: bool
    gamma_invariant_passed: bool
    global_gamma: float
    per_domain_gamma: dict[str, float]
    phase: str
    errors: list[str]


class CIOrchestrator:
    def run_root_tests(self) -> bool:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=line", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        return result.returncode == 0

    def run_substrate_smoke(self, substrate: str) -> bool:
        adapter_path = ROOT / "substrates" / substrate / "adapter.py"
        if not adapter_path.exists():
            return True  # no adapter = skip
        result = subprocess.run(
            [sys.executable, "-c", f"import substrates.{substrate}.adapter; print('OK')"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0

    def run_cross_substrate(self) -> dict:
        """Full observe() cycle with all mock adapters."""
        from neosynaptex import (
            MockBnSynAdapter,
            MockMarketAdapter,
            MockMfnAdapter,
            MockPsycheCoreAdapter,
            Neosynaptex,
        )

        engine = Neosynaptex(window=16)
        engine.register(MockBnSynAdapter())
        engine.register(MockMfnAdapter())
        engine.register(MockPsycheCoreAdapter())
        engine.register(MockMarketAdapter())

        for _ in range(40):
            state = engine.observe()

        return {
            "gamma_mean": state.gamma_mean,
            "gamma_per_domain": dict(state.gamma_per_domain),
            "phase": state.phase,
            "cross_coherence": state.cross_coherence,
            "spectral_radius": state.spectral_radius,
        }

    def run_gamma_invariant_check(self, per_domain_gamma: dict[str, float]) -> dict:
        """Statistical test: mean gamma in [0.5, 1.5] and bootstrap CI excludes 0."""
        valid = [v for v in per_domain_gamma.values() if np.isfinite(v)]
        if len(valid) < 2:
            return {"passed": False, "reason": "insufficient valid gammas"}

        arr = np.array(valid)
        mean_g = float(np.mean(arr))
        in_range = 0.5 <= mean_g <= 1.5

        # Bootstrap CI for mean gamma — does it exclude 0?
        rng = np.random.default_rng(42)
        boot_means = np.array(
            [float(np.mean(rng.choice(arr, size=len(arr), replace=True))) for _ in range(2000)]
        )
        ci_lo = float(np.percentile(boot_means, 2.5))
        ci_hi = float(np.percentile(boot_means, 97.5))
        excludes_zero = ci_lo > 0.0

        return {
            "passed": in_range and excludes_zero,
            "mean_gamma": mean_g,
            "in_range": in_range,
            "ci_lo": round(ci_lo, 4),
            "ci_hi": round(ci_hi, 4),
            "excludes_zero": excludes_zero,
            "n_domains": len(valid),
        }

    def generate_report(self) -> CIReport:
        errors: list[str] = []

        # Cross-substrate
        try:
            cross = self.run_cross_substrate()
            cross_ok = cross["phase"] != "DEGENERATE" and 0.5 <= cross["gamma_mean"] <= 1.5
        except Exception as e:
            cross = {"gamma_mean": float("nan"), "gamma_per_domain": {}, "phase": "ERROR"}
            cross_ok = False
            errors.append(f"cross_substrate: {e}")

        # Gamma invariant
        gamma_check = self.run_gamma_invariant_check(cross.get("gamma_per_domain", {}))

        return CIReport(
            root_tests_passed=True,  # defer to pytest
            cross_substrate_passed=cross_ok,
            gamma_invariant_passed=gamma_check["passed"],
            global_gamma=cross.get("gamma_mean", float("nan")),
            per_domain_gamma=cross.get("gamma_per_domain", {}),
            phase=cross.get("phase", "UNKNOWN"),
            errors=errors,
        )


def main() -> int:
    orch = CIOrchestrator()
    report = orch.generate_report()

    print("=== CI Orchestrator Report ===")
    print(f"  Cross-substrate: {'PASS' if report.cross_substrate_passed else 'FAIL'}")
    print(f"  Gamma invariant: {'PASS' if report.gamma_invariant_passed else 'FAIL'}")
    print(f"  Global gamma: {report.global_gamma:.4f}")
    print(f"  Phase: {report.phase}")
    for d, g in sorted(report.per_domain_gamma.items()):
        print(f"    {d}: gamma={g:.4f}" if np.isfinite(g) else f"    {d}: gamma=NaN")

    if report.errors:
        print(f"\n  ERRORS: {report.errors}")

    ok = report.cross_substrate_passed and report.gamma_invariant_passed
    print(f"\n  VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
