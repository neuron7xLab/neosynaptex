#!/usr/bin/env python3
"""Derive gamma from real CNS-AI session data.

Uses latency CV as topo proxy, 1/accuracy as cost proxy.
Consistent with manuscript Section 2.3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import theilslopes

SESSIONS_DIR = Path(__file__).resolve().parent / "evidence" / "sessions"
EVIDENCE_DIR = Path(__file__).resolve().parent.parent.parent / "evidence"


def load_sessions() -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    productive: list[tuple[float, float]] = []
    non_productive: list[tuple[float, float]] = []
    if not SESSIONS_DIR.exists():
        return productive, non_productive

    for session_dir in sorted(SESSIONS_DIR.glob("session_*")):
        analysis_file = session_dir / "analysis.json"
        if not analysis_file.exists():
            continue
        with open(analysis_file) as f:
            data = json.load(f)

        stats = data.get("statistics", {})
        n = stats.get("n_tasks", 0)
        accuracy = stats.get("accuracy_pct", 0) / 100.0
        latency_cv = stats.get("latency_cv")

        if n < 20 or latency_cv is None or accuracy == 0:
            continue

        topo = latency_cv * n
        cost = max(1.0 - accuracy, 0.01)

        if accuracy >= 0.75:
            productive.append((topo, cost))
        else:
            non_productive.append((topo, cost))

    return productive, non_productive


def compute_gamma(points: list[tuple[float, float]], label: str) -> dict | None:
    if len(points) < 5:
        print(f"  {label}: INSUFFICIENT DATA (n={len(points)}, need >= 5)")
        return None

    topos = np.array([p[0] for p in points])
    costs = np.array([p[1] for p in points])

    mask = (topos > 0) & (costs > 0)
    topos, costs = topos[mask], costs[mask]
    if len(topos) < 5:
        print(f"  {label}: INSUFFICIENT POSITIVE DATA (n={len(topos)})")
        return None

    log_t = np.log(topos)
    log_c = np.log(costs)

    if np.ptp(log_t) < 0.5:
        print(f"  {label}: RANGE_GATE FAILED (ptp={np.ptp(log_t):.3f} < 0.5)")
        return None

    slope, intercept, lo, hi = theilslopes(log_c, log_t)
    gamma = -slope

    yhat = slope * log_t + intercept
    ss_r = float(np.sum((log_c - yhat) ** 2))
    ss_t = float(np.sum((log_c - log_c.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 1e-10 else 0.0

    if r2 < 0.5:
        print(f"  {label}: R2_GATE FAILED (r2={r2:.3f} < 0.5)")
        return None

    print(f"  {label}: g={gamma:.4f} CI=[{-hi:.3f},{-lo:.3f}] R2={r2:.3f} n={len(topos)}")
    return {
        "gamma": round(float(gamma), 4),
        "ci_lo": round(float(-hi), 4),
        "ci_hi": round(float(-lo), 4),
        "r2": round(float(r2), 3),
        "n": int(len(topos)),
    }


def main() -> int:
    print("=== CNS-AI Real Gamma Derivation ===\n")
    productive, non_productive = load_sessions()
    print(f"Sessions: {len(productive)} productive, {len(non_productive)} non-productive\n")

    all_points = productive + non_productive
    g_all = compute_gamma(all_points, "ALL sessions")
    g_prod = compute_gamma(productive, "PRODUCTIVE (acc >= 75%)")
    g_non = compute_gamma(non_productive, "NON-PRODUCTIVE (acc < 75%)")

    if g_all:
        result = {
            "substrate": "cns_ai_real",
            "gamma": g_all["gamma"],
            "ci": [g_all["ci_lo"], g_all["ci_hi"]],
            "r2": g_all["r2"],
            "n": g_all["n"],
            "productive_gamma": g_prod["gamma"] if g_prod else None,
            "non_productive_gamma": g_non["gamma"] if g_non else None,
            "status": "DERIVED_REAL",
        }
        out = EVIDENCE_DIR / "cns_ai_real_gamma.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"\n  Saved: {out}")
        return 0

    print("\n  NO REAL DATA AVAILABLE.")
    print("  Run: python substrates/cns_ai_loop/collector.py --duration 30")
    print("  Then: python substrates/cns_ai_loop/analyze.py")
    print("  Minimum: 20 sessions with >= 20 tasks each")
    return 1


if __name__ == "__main__":
    sys.exit(main())
