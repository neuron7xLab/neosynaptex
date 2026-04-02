#!/usr/bin/env python3
"""Reproducibility machine — one command, all substrates, all γ, all statistical tests.

Usage: python scripts/reproduce.py
Output: evidence/reproduction_bundle.json + stdout summary

This is the script a reviewer runs after: git clone + pip install -e . + python scripts/reproduce.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.falsification import bias_probe, estimate_gamma_multi, null_ensemble_test
from neosynaptex import (
    MockBnSynAdapter,
    MockMarketAdapter,
    MockMfnAdapter,
    MockPsycheCoreAdapter,
    Neosynaptex,
    _per_domain_gamma,
)
from substrates.hrv.adapter import HrvAdapter
from substrates.lotka_volterra.adapter import LotkaVolterraAdapter


@dataclass
class SubstrateGammaResult:
    name: str
    gamma: float
    ci_low: float
    ci_high: float
    r2: float
    n_pairs: int
    p_shuffle: float
    p_iaaft: float
    estimator_spread: float


def _derive_gamma_from_adapter(
    adapter: object, n_ticks: int = 100, seed: int = 42
) -> SubstrateGammaResult:
    """Run adapter for n_ticks, collect topo/cost, derive γ with full falsification."""
    name = getattr(adapter, "domain", "unknown")
    topos, costs = [], []

    for _ in range(n_ticks):
        adapter.state()  # type: ignore[union-attr]
        t = adapter.topo()  # type: ignore[union-attr]
        c = adapter.thermo_cost()  # type: ignore[union-attr]
        if np.isfinite(t) and np.isfinite(c) and t > 0 and c > 0:
            topos.append(t)
            costs.append(c)

    if len(topos) < 10:
        return SubstrateGammaResult(
            name=name,
            gamma=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            r2=0.0,
            n_pairs=len(topos),
            p_shuffle=1.0,
            p_iaaft=1.0,
            estimator_spread=float("nan"),
        )

    t_arr = np.array(topos)
    c_arr = np.array(costs)
    lt = np.log(t_arr)
    lc = np.log(c_arr)

    gamma, r2, ci_lo, ci_hi = _per_domain_gamma(t_arr, c_arr, seed=seed)

    # Null ensemble
    if np.isfinite(gamma) and np.ptp(lt) >= 0.5:
        null = null_ensemble_test(lt, lc, n_surrogates=99, seed=seed)
        p_shuf = null.p_shuffle
        p_iaaft = null.p_iaaft
    else:
        p_shuf = 1.0
        p_iaaft = 1.0

    # Estimator sensitivity
    if np.isfinite(gamma) and np.ptp(lt) >= 0.5:
        est = estimate_gamma_multi(lt, lc, n_boot=200, seed=seed)
        gammas = [e.gamma for e in est]
        spread = max(gammas) - min(gammas) if len(gammas) >= 2 else 0.0
    else:
        spread = float("nan")

    return SubstrateGammaResult(
        name=name,
        gamma=float(gamma) if np.isfinite(gamma) else float("nan"),
        ci_low=float(ci_lo) if np.isfinite(ci_lo) else float("nan"),
        ci_high=float(ci_hi) if np.isfinite(ci_hi) else float("nan"),
        r2=float(r2) if np.isfinite(r2) else 0.0,
        n_pairs=len(topos),
        p_shuffle=p_shuf,
        p_iaaft=p_iaaft,
        estimator_spread=spread,
    )


def main() -> int:
    print("=" * 60)
    print("  NFI REPRODUCIBILITY REPORT")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    t0 = time.perf_counter()

    # All adapters (mock + real substrates)
    adapters = [
        MockBnSynAdapter(seed=42),
        MockMfnAdapter(seed=43),
        MockPsycheCoreAdapter(seed=44),
        MockMarketAdapter(seed=45),
        HrvAdapter(seed=77),
        LotkaVolterraAdapter(seed=88),
    ]

    results: list[SubstrateGammaResult] = []
    print("\n--- Per-Substrate γ Derivation ---\n")

    for adapter in adapters:
        r = _derive_gamma_from_adapter(adapter, n_ticks=100)
        results.append(r)
        gamma_str = f"{r.gamma:.4f}" if np.isfinite(r.gamma) else "NaN"
        ci_str = f"[{r.ci_low:.3f},{r.ci_high:.3f}]" if np.isfinite(r.ci_low) else "[NaN]"
        print(
            f"  {r.name:20s}  γ={gamma_str:>8s}  CI={ci_str:>16s}  "
            f"R²={r.r2:.3f}  n={r.n_pairs:>3d}  "
            f"p_shuf={r.p_shuffle:.3f}  p_iaaft={r.p_iaaft:.3f}  "
            f"spread={r.estimator_spread:.4f}"
            if np.isfinite(r.estimator_spread)
            else f"  {r.name:20s}  γ={gamma_str:>8s}  CI={ci_str:>16s}  "
            f"R²={r.r2:.3f}  n={r.n_pairs:>3d}  INSUFFICIENT DATA"
        )

    # Cross-substrate integration
    print("\n--- Cross-Substrate Integration ---\n")
    engine = Neosynaptex(window=16)
    engine.register(MockBnSynAdapter(seed=42))
    engine.register(MockMfnAdapter(seed=43))
    engine.register(MockPsycheCoreAdapter(seed=44))
    engine.register(MockMarketAdapter(seed=45))

    for _ in range(40):
        state = engine.observe()

    print(f"  Phase: {state.phase}")
    print(f"  γ mean: {state.gamma_mean:.4f}")
    print(f"  Cross-coherence: {state.cross_coherence:.4f}")
    print(f"  Spectral radius: {state.spectral_radius:.4f}")

    # Bias probe
    print("\n--- Method Bias Probe ---\n")
    bias = bias_probe(gamma_values=[0.5, 0.85, 1.0, 1.15, 1.5], n_trials=30)
    for b in bias:
        print(
            f"  γ_true={b.gamma_true:.2f}  "
            f"TS={b.gamma_theilsen:.4f}(Δ={b.bias_theilsen:+.4f})  "
            f"OLS={b.gamma_ols:.4f}(Δ={b.bias_ols:+.4f})  "
            f"Huber={b.gamma_huber:.4f}(Δ={b.bias_huber:+.4f})"
        )

    # Summary statistics
    valid_gammas = [r.gamma for r in results if np.isfinite(r.gamma)]
    mean_g = float(np.mean(valid_gammas)) if valid_gammas else float("nan")
    std_g = float(np.std(valid_gammas)) if valid_gammas else float("nan")
    all_sig = all(r.p_shuffle < 0.05 for r in results if np.isfinite(r.gamma))

    elapsed = time.perf_counter() - t0

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print(f"  Substrates: {len(results)} ({len(valid_gammas)} with valid γ)")
    print(f"  Mean γ: {mean_g:.4f} ± {std_g:.4f}")
    print(f"  All shuffle nulls significant: {all_sig}")
    spreads = [r.estimator_spread for r in results if np.isfinite(r.estimator_spread)]
    max_spread = max(spreads, default=0.0)
    print(f"  Max estimator spread: {max_spread:.4f}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("=" * 60)

    # Git SHA
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=ROOT,
        ).stdout.strip()
    except Exception:
        sha = "unknown"

    # Save bundle
    bundle = {
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "n_substrates": len(results),
        "mean_gamma": mean_g,
        "std_gamma": std_g,
        "all_nulls_significant": all_sig,
        "elapsed_seconds": round(elapsed, 1),
        "substrates": [
            {
                k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                for k, v in asdict(r).items()
            }
            for r in results
        ],
        "cross_substrate": {
            "phase": state.phase,
            "gamma_mean": round(state.gamma_mean, 4) if np.isfinite(state.gamma_mean) else None,
            "cross_coherence": round(state.cross_coherence, 4)
            if np.isfinite(state.cross_coherence)
            else None,
        },
        "bias_probe": [asdict(b) for b in bias],
    }

    out_path = ROOT / "evidence" / "reproduction_bundle.json"
    out_path.write_text(json.dumps(bundle, indent=2, default=str))
    print(f"\n  Bundle: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
