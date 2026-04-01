#!/usr/bin/env python3
"""Neural M-invariant v2: Mann-Kendall + sigma sweep + AdEx + N=500.

Four tasks to close the question:
  T1. Mann-Kendall on all 4 substrates (existing data + fresh neural)
  T2. Sigma sweep: does σ=1 give strongest trend?
  T3. AdEx with adaptation: cleaner descent?
  T4. N=500: do oscillations shrink with network size?
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

os.environ["MKL_NUM_THREADS"] = "1"
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pymannkendall as mk
from scipy.stats import kendalltau

from mycelium_fractal_net.analytics.unified_score import compute_hwi_components

# ═══════════════════════════════════════════════════════════════
# SHARED: compute_M + Mann-Kendall
# ═══════════════════════════════════════════════════════════════


def _to_2d(vec: np.ndarray) -> np.ndarray:
    """Reshape 1D neuron vector to nearest square 2D grid."""
    n = len(vec.ravel())
    side = int(np.floor(np.sqrt(n)))
    return vec.ravel()[: side * side].reshape(side, side).astype(np.float64)


def compute_M_traj(history: np.ndarray, ref: np.ndarray, stride: int = 1) -> np.ndarray:
    """Compute M(t) trajectory from history relative to reference."""
    ref_2d = _to_2d(ref) if ref.ndim == 1 else ref
    Ms = []
    for t in range(0, len(history), stride):
        frame = _to_2d(history[t]) if history[t].ndim == 1 else history[t]
        hwi = compute_hwi_components(frame, ref_2d)
        Ms.append(hwi.M)
    return np.array(Ms)


def mann_kendall(x: np.ndarray) -> dict:
    """Mann-Kendall trend test. Returns tau, p, trend label."""
    try:
        result = mk.original_test(x)
        return {
            "tau": round(float(result.Tau), 4),
            "p": round(float(result.p), 6),
            "trend": result.trend,
            "significant": float(result.p) < 0.05 and float(result.Tau) < -0.1,
        }
    except Exception:
        tau, p = kendalltau(np.arange(len(x)), x)
        return {
            "tau": round(float(tau), 4),
            "p": round(float(p), 6),
            "trend": "decreasing" if tau < 0 else "increasing",
            "significant": float(p) < 0.05 and float(tau) < -0.1,
        }


# ═══════════════════════════════════════════════════════════════
# NEURAL SIMULATION (IF + STD)
# ═══════════════════════════════════════════════════════════════


def run_if_std(
    N: int = 200, T_ms: int = 3000, tau_rec_ms: float = 800.0, seed: int = 42
) -> tuple[np.ndarray, float]:
    """Run IF+STD network simulation. Returns (v_data, sigma)."""
    from brian2 import (
        Hz,
        Network,
        NeuronGroup,
        SpikeMonitor,
        StateMonitor,
        Synapses,
        defaultclock,
        ms,
        mV,
        start_scope,
    )

    start_scope()
    defaultclock.dt = 0.1 * ms
    np.random.seed(seed)

    10 * ms
    -70 * mV
    -50 * mV
    -65 * mV
    U_se = 0.5

    G = NeuronGroup(
        N,
        "dv/dt = (V_rest - v) / tau : volt",
        threshold="v > V_thresh",
        reset="v = V_reset",
        method="euler",
    )
    G.v = "V_rest + randn()*2*mV"

    S = Synapses(
        G,
        G,
        f"dx_syn/dt = (1 - x_syn) / ({tau_rec_ms}*ms) : 1 (clock-driven)\nw : volt",
        on_pre=f"v_post += {U_se} * x_syn * w\nx_syn -= {U_se} * x_syn",
    )
    S.connect(p=0.1)
    S.w = "(V_thresh - V_rest) / (N * 0.1 * U_se) + 0.1*mV*randn()"
    S.x_syn = 1.0

    spike_mon = SpikeMonitor(G)
    state_mon = StateMonitor(G, "v", record=True, dt=10 * ms)

    noise = NeuronGroup(N, "rates : Hz", threshold="rand() < rates * dt")
    noise.rates = 10 * Hz
    ns = Synapses(noise, G, on_pre="v_post += (V_thresh - V_rest) * 1.1")
    ns.connect("i == j")

    net = Network(G, S, spike_mon, state_mon, noise, ns)
    net.run(T_ms * ms)

    v_data = np.array(state_mon.v / mV).T  # (T, N)
    spike_t = np.array(spike_mon.t / ms)

    # Branching ratio
    sc = np.array([np.sum((spike_t >= t) & (spike_t < t + 1)) for t in range(T_ms)], dtype=float)
    ratios = [sc[t + 1] / sc[t] for t in range(len(sc) - 1) if sc[t] > 0]
    sigma = float(np.median(ratios)) if ratios else 0.0

    return v_data, sigma, len(spike_t)


# ═══════════════════════════════════════════════════════════════
# TASK 1: Mann-Kendall on RD substrates + Neural
# ═══════════════════════════════════════════════════════════════


def task1_mann_kendall_all() -> dict:
    """Mann-Kendall test on all substrates."""
    print("TASK 1: Mann-Kendall trend test on all substrates")
    print("-" * 55)

    results = {}

    # Gray-Scott
    import mycelium_fractal_net as mfn

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    M_gs = compute_M_traj(seq.history, seq.field, stride=2)
    mk_gs = mann_kendall(M_gs)
    results["Gray-Scott"] = mk_gs
    print(f"  Gray-Scott:      tau={mk_gs['tau']:+.3f}  p={mk_gs['p']:.4f}  {mk_gs['trend']}")

    # FHN
    from scripts.m_invariant_three_substrates import substrate_fhn

    r_fhn = substrate_fhn(N=32, T=300, seed=42)
    mk_fhn = mann_kendall(np.array(r_fhn["M_trajectory"]))
    results["FitzHugh-Nagumo"] = mk_fhn
    print(f"  FitzHugh-Nagumo: tau={mk_fhn['tau']:+.3f}  p={mk_fhn['p']:.4f}  {mk_fhn['trend']}")

    # Cahn-Hilliard
    from scripts.m_invariant_three_substrates import substrate_cahn_hilliard

    r_ch = substrate_cahn_hilliard(N=32, T=300, seed=42)
    mk_ch = mann_kendall(np.array(r_ch["M_trajectory"]))
    results["Cahn-Hilliard"] = mk_ch
    print(f"  Cahn-Hilliard:   tau={mk_ch['tau']:+.3f}  p={mk_ch['p']:.4f}  {mk_ch['trend']}")

    # Neural IF+STD
    v_data, sigma, n_spikes = run_if_std(N=200, T_ms=3000, tau_rec_ms=800)
    M_neural = compute_M_traj(v_data, v_data[-1], stride=max(1, len(v_data) // 40))
    mk_neural = mann_kendall(M_neural)
    mk_neural["sigma"] = round(sigma, 4)
    mk_neural["n_spikes"] = n_spikes
    results["Neural IF+STD"] = mk_neural
    print(
        f"  Neural IF+STD:   tau={mk_neural['tau']:+.3f}  p={mk_neural['p']:.4f}  "
        f"{mk_neural['trend']}  σ={sigma:.3f}"
    )

    return results


# ═══════════════════════════════════════════════════════════════
# TASK 2: Sigma sweep
# ═══════════════════════════════════════════════════════════════


def task2_sigma_sweep() -> dict:
    """Does σ=1 give the strongest decreasing trend?"""
    print("\nTASK 2: Sigma sweep (tau_rec controls σ)")
    print("-" * 55)

    # tau_rec → σ mapping (from Levina 2007):
    # smaller tau_rec → faster recovery → stronger synapses → higher σ
    tau_recs = [3000, 1500, 800, 400, 150]
    results = {}

    for tau_rec in tau_recs:
        v_data, sigma, n_spikes = run_if_std(N=200, T_ms=2000, tau_rec_ms=float(tau_rec))
        if len(v_data) < 5:
            results[tau_rec] = {"sigma": 0, "tau_mk": 0, "p": 1, "n_spikes": 0}
            continue

        M_traj = compute_M_traj(v_data, v_data[-1], stride=max(1, len(v_data) // 30))
        mk_r = mann_kendall(M_traj)
        descent = float(M_traj[0] - M_traj[-1]) if len(M_traj) > 1 else 0

        results[tau_rec] = {
            "sigma": round(sigma, 4),
            "tau_mk": mk_r["tau"],
            "p": mk_r["p"],
            "descent": round(descent, 4),
            "n_spikes": n_spikes,
            "trend": mk_r["trend"],
        }
        print(
            f"  tau_rec={tau_rec:5d}ms  σ={sigma:.3f}  MK_tau={mk_r['tau']:+.3f}  "
            f"p={mk_r['p']:.4f}  descent={descent:+.4f}  spikes={n_spikes}"
        )

    return results


# ═══════════════════════════════════════════════════════════════
# TASK 3: N=500 — do oscillations shrink?
# ═══════════════════════════════════════════════════════════════


def task3_large_network() -> dict:
    """N=500 vs N=200: does averaging reduce oscillations?"""
    print("\nTASK 3: Network size effect (N=200 vs N=500)")
    print("-" * 55)

    results = {}
    for N in [200, 500]:
        t0 = time.perf_counter()
        v_data, sigma, n_spikes = run_if_std(N=N, T_ms=2000, tau_rec_ms=800)
        sim_t = time.perf_counter() - t0

        M_traj = compute_M_traj(v_data, v_data[-1], stride=max(1, len(v_data) // 30))
        mk_r = mann_kendall(M_traj)
        M_std = float(np.std(M_traj))

        results[N] = {
            "sigma": round(sigma, 4),
            "tau_mk": mk_r["tau"],
            "p": mk_r["p"],
            "M_std": round(M_std, 4),
            "n_spikes": n_spikes,
            "sim_seconds": round(sim_t, 1),
            "trend": mk_r["trend"],
        }
        print(
            f"  N={N:4d}  σ={sigma:.3f}  MK_tau={mk_r['tau']:+.3f}  "
            f"p={mk_r['p']:.4f}  M_std={M_std:.4f}  ({sim_t:.1f}s)"
        )

    return results


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 60)
    print("  NEURAL M-INVARIANT v2 — Mann-Kendall + Sigma + Size")
    print("=" * 60)
    print()

    r1 = task1_mann_kendall_all()
    r2 = task2_sigma_sweep()
    r3 = task3_large_network()

    elapsed = time.perf_counter() - t0

    output = {
        "task1_mann_kendall": r1,
        "task2_sigma_sweep": {str(k): v for k, v in r2.items()},
        "task3_network_size": {str(k): v for k, v in r3.items()},
        "compute_seconds": round(elapsed, 1),
    }

    os.makedirs("results", exist_ok=True)
    with open("results/neural_M_v2.json", "w") as f:
        json.dump(output, f, indent=2)

    print()
    print("=" * 60)
    print("  VERDICT")
    print("=" * 60)

    # All substrates with Mann-Kendall
    print(f"\n  {'Substrate':<20} {'MK tau':>8} {'p':>8} {'Trend':>12}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 8} {'-' * 12}")
    for name, r in r1.items():
        sig = "*" if r.get("significant") else ""
        print(f"  {name:<20} {r['tau']:>+8.3f} {r['p']:>8.4f} {r['trend']:>12}{sig}")

    # Sigma sweep
    best_tau_rec = min(r2, key=lambda k: r2[k].get("tau_mk", 0))
    best_r = r2[best_tau_rec]
    print(
        f"\n  Strongest trend at tau_rec={best_tau_rec}ms "
        f"(σ={best_r['sigma']:.3f}, MK_tau={best_r['tau_mk']:+.3f})"
    )

    # Network size
    if "200" in {str(k) for k in r3} and "500" in {str(k) for k in r3}:
        r200 = r3[200]
        r500 = r3[500]
        print(f"\n  N=200: M_std={r200['M_std']:.4f}  N=500: M_std={r500['M_std']:.4f}")
        if r500["M_std"] < r200["M_std"]:
            print("  → Oscillations DECREASE with network size")
        else:
            print("  → Oscillations persist regardless of size")

    # Final
    all_sig = all(r.get("significant", False) for r in r1.values())
    neural_sig = r1.get("Neural IF+STD", {}).get("significant", False)
    print()
    if all_sig:
        print("  >>> ALL SUBSTRATES: statistically significant decreasing trend")
    elif neural_sig:
        print("  >>> NEURAL: significant trend confirmed by Mann-Kendall")
    else:
        print("  >>> NEURAL: trend not statistically significant")

    print(f"\n  {elapsed:.0f}s total")
    print("  Saved: results/neural_M_v2.json")
    print("=" * 60)
