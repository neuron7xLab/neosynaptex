#!/usr/bin/env python3
"""M-invariant on neural substrate: IF + STD (Levina 2007).

Tests whether dM/dt < 0 holds during self-organization to criticality.
Three regimes: subcritical, critical, supercritical — controlled by tau_rec.

Ref: Levina, Herrmann & Geisel (2007) Nature Physics 3:857
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

os.environ["MKL_NUM_THREADS"] = "1"
warnings.filterwarnings("ignore")

import numpy as np
import ot


def compute_M(v1: np.ndarray, v2: np.ndarray) -> float:
    """HWI saturation ratio — identical formula for all substrates."""
    a = np.abs(v1).ravel().astype(np.float64) + 1e-12
    a /= a.sum()
    b = np.abs(v2).ravel().astype(np.float64) + 1e-12
    b /= b.sum()

    H = max(0.0, float(np.sum(a * np.log(a / (b + 1e-12)))))

    n = len(a)
    idx = np.arange(n, dtype=np.float64).reshape(-1, 1)
    M_cost = (idx - idx.T) ** 2
    # Normalize cost matrix
    M_cost /= M_cost.max() + 1e-12

    try:
        w2_sq = ot.sinkhorn2(a, b, M_cost, reg=0.05, numItermax=300)
        W2 = float(np.sqrt(max(float(w2_sq), 0)))
    except Exception:
        W2 = 0.0

    # Jensen-Shannon divergence (stable Fisher proxy)
    m_dist = 0.5 * (a + b)
    I = float(0.5 * np.sum(a * np.log(a / (m_dist + 1e-12)))
              + 0.5 * np.sum(b * np.log(b / (m_dist + 1e-12))))

    rhs = W2 * np.sqrt(max(I, 1e-12))
    return float(H / (rhs + 1e-10)) if rhs > 1e-6 else 0.0


def run_neural_sim(N: int = 200, T_ms: int = 3000, tau_rec_ms: float = 800.0,
                   seed: int = 42) -> dict:
    """Run IF + STD network simulation using Brian2."""
    from brian2 import (
        NeuronGroup, Synapses, SpikeMonitor, StateMonitor,
        ms, mV, Hz, defaultclock, start_scope,
        network_operation, Network,
    )

    start_scope()
    defaultclock.dt = 0.1 * ms
    np.random.seed(seed)

    tau = 10 * ms
    V_rest = -70 * mV
    V_thresh = -50 * mV
    V_reset = -65 * mV
    U_se = 0.5

    neuron_eqs = '''
    dv/dt = (V_rest - v) / tau : volt
    '''

    synapse_eqs = f'''
    dx_syn/dt = (1 - x_syn) / ({tau_rec_ms}*ms) : 1 (clock-driven)
    w : volt
    '''
    on_pre = '''
    v_post += {U_se} * x_syn * w
    x_syn -= {U_se} * x_syn
    '''.format(U_se=U_se)

    G = NeuronGroup(N, neuron_eqs,
                    threshold='v > V_thresh',
                    reset='v = V_reset',
                    method='euler')
    G.v = 'V_rest + randn()*2*mV'

    S = Synapses(G, G, synapse_eqs, on_pre=on_pre)
    S.connect(p=0.1)
    # Strong recurrent: each spike can push neighbors over threshold
    S.w = '(V_thresh - V_rest) / (N * 0.1 * U_se) + 0.1*mV*randn()'
    S.x_syn = 1.0

    spike_mon = SpikeMonitor(G)
    state_mon = StateMonitor(G, 'v', record=True, dt=5 * ms)

    # External Poisson noise
    noise_eqs = 'rates : Hz'
    noise_group = NeuronGroup(N, noise_eqs, threshold='rand() < rates * dt')
    # Weak external drive: rare seeds that trigger avalanches
    noise_group.rates = 10 * Hz
    noise_syn = Synapses(noise_group, G, on_pre='v_post += (V_thresh - V_rest) * 1.1')
    noise_syn.connect('i == j')

    net = Network(G, S, spike_mon, state_mon, noise_group, noise_syn)
    net.run(T_ms * ms)

    v_data = np.array(state_mon.v / mV)  # (N, T) in mV
    spike_times = np.array(spike_mon.t / ms)

    return {
        "v_data": v_data.T,  # (T, N)
        "spike_times": spike_times,
        "N": N,
        "T_ms": T_ms,
        "tau_rec_ms": tau_rec_ms,
    }


def compute_branching_ratio(spike_times: np.ndarray, T_ms: int) -> float:
    """Compute branching ratio σ using mrestimator."""
    try:
        import mrestimator as mre
        # Bin spikes into 1ms bins
        sc = np.array([
            np.sum((spike_times >= t) & (spike_times < t + 1))
            for t in range(T_ms)
        ], dtype=float)

        if sc.sum() < 10:
            return 0.0

        rk = mre.coefficients(sc, dt=1, dtunit='ms')
        fit = mre.fit(rk)
        return float(fit.mre)
    except Exception:
        # Fallback: naive A_{t+1}/A_t
        sc = np.array([
            np.sum((spike_times >= t) & (spike_times < t + 1))
            for t in range(T_ms)
        ], dtype=float)
        ratios = []
        for t in range(len(sc) - 1):
            if sc[t] > 0:
                ratios.append(sc[t + 1] / sc[t])
        return float(np.median(ratios)) if ratios else 0.0


def analyze_M_trajectory(v_data: np.ndarray) -> dict:
    """Compute M(t) trajectory and analyze monotonicity."""
    T = v_data.shape[0]
    ref_initial = v_data[0]
    ref_final = v_data[-1]

    stride = max(1, T // 30)
    Ms_from_initial = []
    Ms_from_final = []

    for t in range(0, T, stride):
        Ms_from_initial.append(compute_M(v_data[t], ref_initial))
        Ms_from_final.append(compute_M(v_data[t], ref_final))

    Ms_i = np.array(Ms_from_initial)
    Ms_f = np.array(Ms_from_final)

    # Monotone decreasing fraction (from initial)
    diffs_i = np.diff(Ms_i)
    dec_i = int(np.sum(diffs_i < 0))
    frac_i = dec_i / max(len(diffs_i), 1) * 100

    # Monotone decreasing fraction (from final = SOC)
    diffs_f = np.diff(Ms_f)
    dec_f = int(np.sum(diffs_f < 0))
    frac_f = dec_f / max(len(diffs_f), 1) * 100

    return {
        "M_from_initial": [round(float(m), 6) for m in Ms_i],
        "M_from_final": [round(float(m), 6) for m in Ms_f],
        "dM_dt_neg_initial_pct": round(frac_i, 1),
        "dM_dt_neg_final_pct": round(frac_f, 1),
        "M_initial_start": round(float(Ms_i[0]), 6),
        "M_initial_end": round(float(Ms_i[-1]), 6),
        "M_initial_mean": round(float(Ms_i.mean()), 6),
        "M_final_start": round(float(Ms_f[0]), 6),
        "M_final_end": round(float(Ms_f[-1]), 6),
        "M_final_mean": round(float(Ms_f.mean()), 6),
        "overall_descent": bool(Ms_i[-1] < Ms_i[0]),
    }


if __name__ == "__main__":
    t0_total = time.perf_counter()

    print("=" * 65)
    print("  M-INVARIANT: Neural Substrate (IF + STD, Levina 2007)")
    print("=" * 65)
    print()

    configs = [
        ("Subcritical",    2000.0),
        ("Critical",        800.0),
        ("Supercritical",   200.0),
    ]

    results = {}

    for name, tau_rec in configs:
        print(f"--- {name} (tau_rec={tau_rec}ms) ---")
        t1 = time.perf_counter()

        sim = run_neural_sim(N=200, T_ms=3000, tau_rec_ms=tau_rec, seed=42)
        sim_time = time.perf_counter() - t1
        print(f"  Simulation: {sim_time:.1f}s, {len(sim['spike_times'])} spikes")

        sigma = compute_branching_ratio(sim["spike_times"], sim["T_ms"])
        print(f"  Branching ratio σ = {sigma:.4f}")

        t1 = time.perf_counter()
        m_traj = analyze_M_trajectory(sim["v_data"])
        m_time = time.perf_counter() - t1
        print(f"  M analysis: {m_time:.1f}s")
        print(f"  dM/dt < 0 (from initial): {m_traj['dM_dt_neg_initial_pct']:.0f}%")
        print(f"  M: {m_traj['M_initial_start']:.4f} → {m_traj['M_initial_end']:.4f} "
              f"({'descent' if m_traj['overall_descent'] else 'NO descent'})")
        print(f"  M mean = {m_traj['M_initial_mean']:.4f}")
        print()

        results[name] = {
            "tau_rec_ms": tau_rec,
            "sigma": round(sigma, 4),
            "n_spikes": len(sim["spike_times"]),
            "sim_seconds": round(sim_time, 1),
            **m_traj,
        }

    elapsed = time.perf_counter() - t0_total

    # Save
    output = {
        "results": results,
        "compute_seconds": round(elapsed, 1),
    }
    os.makedirs("results", exist_ok=True)
    with open("results/neural_M_invariant.json", "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 65)
    print("  COMPARISON")
    print("=" * 65)
    print(f"  {'Regime':<15} {'σ':>6} {'dM/dt<0':>8} {'M_start':>8} {'M_end':>8} {'Descent':>8}")
    print(f"  {'-'*15} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for name in ["Subcritical", "Critical", "Supercritical"]:
        r = results[name]
        desc = "YES" if r["overall_descent"] else "no"
        print(f"  {name:<15} {r['sigma']:>6.3f} {r['dM_dt_neg_initial_pct']:>7.0f}% "
              f"{r['M_initial_start']:>8.4f} {r['M_initial_end']:>8.4f} {desc:>8}")

    # Verdict
    crit = results["Critical"]
    best_dec = max(results.values(), key=lambda r: r["dM_dt_neg_initial_pct"])

    print()
    if crit["dM_dt_neg_initial_pct"] >= 60 and crit["overall_descent"]:
        print("  >>> INVARIANT CONFIRMED on neural substrate")
        print(f"  >>> Critical regime: dM/dt < 0 = {crit['dM_dt_neg_initial_pct']:.0f}%")
    elif crit["dM_dt_neg_initial_pct"] > 40:
        print("  >>> PARTIAL: tendency but not strong monotonicity")
    else:
        print("  >>> NOT CONFIRMED: dM/dt not predominantly negative")

    print(f"\n  {elapsed:.0f}s total")
    print(f"  Saved: results/neural_M_invariant.json")
    print("=" * 65)
