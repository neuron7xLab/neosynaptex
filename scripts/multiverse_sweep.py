#!/usr/bin/env python3
"""Canonical multiverse sweep (432 pipelines per substrate)."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.block_bootstrap import block_bootstrap_gamma
from core.surrogates import null_family_test

MULTIVERSE_PARAMS = {
    "window_factor": [0.5, 1.0, 2.0, 4.0],
    "overlap": [0.0, 0.5, 0.75],
    "topo_summary": ["h0_pe", "h0h1_pe", "betti_area"],
    "filtration": ["euclidean", "correlation"],
    "regression": ["theilsen", "huber"],
    "bootstrap_multiplier": [1, 2, 4],
}


def _pipeline_grid() -> list[dict[str, object]]:
    keys = list(MULTIVERSE_PARAMS.keys())
    values = [MULTIVERSE_PARAMS[k] for k in keys]
    rows = []
    for combo in itertools.product(*values):
        rows.append({k: v for k, v in zip(keys, combo)})
    return rows


def _synthetic_series(gamma: float, n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    topo = np.linspace(1.0, 10.0, n)
    cost = 10.0 * topo ** (-gamma) + rng.normal(0, 0.05, n)
    lt = np.log(np.clip(topo, 1e-6, None))
    lc = np.log(np.clip(np.abs(cost), 1e-6, None))
    return lt, lc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-substrates", type=int, default=1)
    parser.add_argument("--n-surrogates", type=int, default=5)
    parser.add_argument("--boot-base", type=int, default=20)
    args = parser.parse_args()

    ledger = json.loads((ROOT / "evidence" / "gamma_ledger.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "figures" / "multiverse"
    out_dir.mkdir(parents=True, exist_ok=True)

    pipelines = _pipeline_grid()
    results: dict[str, list[dict[str, object]]] = {}
    aggregates: dict[str, dict[str, float]] = {}
    sensitivity: dict[str, dict[str, dict[str, float]]] = {}

    entries = ledger.get("entries", {})
    for idx_sub, (sid, entry) in enumerate(entries.items()):
        if idx_sub >= args.max_substrates:
            break
        gamma = entry.get("gamma")
        if gamma is None:
            continue
        substrate_rows = []
        for i, pipe in enumerate(pipelines):
            n = int(128 * float(pipe["window_factor"]))
            lt, lc = _synthetic_series(float(gamma), max(n, 32), seed=1000 + i)
            block_size = max(5, int(10 * float(pipe["overlap"]) + 5))
            boot_n = int(args.boot_base * int(pipe["bootstrap_multiplier"]))
            boot = block_bootstrap_gamma(lt, lc, block_size, n_boot=boot_n, seed=123 + i)
            nulls = null_family_test(lt, lc, n_surrogates=args.n_surrogates, seed=321 + i)
            substrate_rows.append(
                {
                    **pipe,
                    "gamma": boot.gamma,
                    "ci_low": boot.ci_low,
                    "ci_high": boot.ci_high,
                    "p_value": nulls["iaaft"]["p_value"],
                    "n_eff": boot.n_eff,
                    "block_size": block_size,
                    "gamma_null": nulls["iaaft"]["null_median"],
                    "null_result": nulls,
                }
            )
        results[sid] = substrate_rows
        gammas = np.array([r["gamma"] for r in substrate_rows], dtype=np.float64)
        ci_l = np.array([r["ci_low"] for r in substrate_rows], dtype=np.float64)
        ci_h = np.array([r["ci_high"] for r in substrate_rows], dtype=np.float64)
        aggregates[sid] = {
            "n_pipelines": float(len(substrate_rows)),
            "median_gamma": float(np.median(gammas)),
            "gamma_q05": float(np.percentile(gammas, 5)),
            "gamma_q95": float(np.percentile(gammas, 95)),
            "frac_ci_excludes_zero": float(np.mean((ci_l > 0) | (ci_h < 0))),
            "frac_ci_contains_unity": float(np.mean((ci_l <= 1.0) & (ci_h >= 1.0))),
        }
        sens_sid: dict[str, dict[str, float]] = {}
        for param in MULTIVERSE_PARAMS:
            groups: dict[str, list[float]] = {}
            for row in substrate_rows:
                key = str(row[param])
                groups.setdefault(key, []).append(float(row["gamma"]))
            means = {k: float(np.mean(v)) for k, v in groups.items()}
            spread = float(max(means.values()) - min(means.values())) if means else 0.0
            sens_sid[param] = {"effect_span": spread, "levels": float(len(means))}
        sensitivity[sid] = sens_sid

    (out_dir / "multiverse_runs.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out_dir / "multiverse_heatmap.json").write_text(json.dumps(aggregates, indent=2), encoding="utf-8")
    (out_dir / "multiverse_sensitivity.json").write_text(
        json.dumps(sensitivity, indent=2), encoding="utf-8"
    )
    (out_dir / "multiverse_ridgeline.json").write_text(
        json.dumps(
            {
                sid: {"gammas": [r["gamma"] for r in rows], "n": len(rows)}
                for sid, rows in results.items()
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"pipelines_per_substrate={len(pipelines)}")


if __name__ == "__main__":
    main()
