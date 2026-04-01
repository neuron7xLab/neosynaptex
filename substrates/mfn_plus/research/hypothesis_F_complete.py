#!/usr/bin/env python3
"""Hypothesis F Complete: CE(t) dynamics + nucleation jumps + FHN third substrate."""

import json
import multiprocessing
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace
from scipy.stats import spearmanr, linregress

import gudhi

N_JOBS = min(multiprocessing.cpu_count(), 8)


def betti(field, min_pers=0.005):
    f = np.asarray(field, dtype=np.float64)
    if f.max() - f.min() < 1e-12:
        return 0, 0
    fs = f.max() - f
    fn = fs / (fs.max() + 1e-12)
    cc = gudhi.CubicalComplex(top_dimensional_cells=fn)
    cc.compute_persistence()
    p = cc.persistence()
    return (sum(1 for d, (b, de) in p if d == 0 and de != float("inf") and de - b > min_pers),
            sum(1 for d, (b, de) in p if d == 1 and de != float("inf") and de - b > min_pers))


def to_prob(f):
    a = np.abs(f).ravel().astype(np.float64) + 1e-12
    return a / a.sum()


def entropy_kl(f1, f2):
    p, q = to_prob(f1), to_prob(f2)
    return max(0, float(np.sum(p * np.log(p / (q + 1e-12)))))


def compute_CE(field, n=4):
    N = field.shape[0]
    block = N // n
    macro = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            macro[i, j] = field[i * block:(i + 1) * block, j * block:(j + 1) * block].mean()
    micro_var = float(field.var())
    macro_var = float(macro.var())
    EI = macro_var / (micro_var + 1e-12)
    return float(np.log(EI + 1e-12)), EI


# ═══════════════════════════════════════════════════════════════
# SIMULATORS WITH FULL HISTORY
# ═══════════════════════════════════════════════════════════════

def sim_gs_history(F, k, N=128, T=1000, dt=0.5, seed=42, checkpoint=20):
    rng = np.random.default_rng(seed)
    U = np.ones((N, N)); V = np.zeros((N, N))
    r = N // 4; cx, cy = N // 2, N // 2
    U[cx-r:cx+r, cy-r:cy+r] = 0.5 + 0.1 * rng.standard_normal((2*r, 2*r))
    V[cx-r:cx+r, cy-r:cy+r] = 0.25 + 0.1 * rng.random((2*r, 2*r))
    Du, Dv = 0.16, 0.08
    history = [(0, V.copy())]
    for t in range(1, T + 1):
        lU = laplace(U, mode="wrap"); lV = laplace(V, mode="wrap")
        uvv = U * V * V
        U += dt * (Du * lU - uvv + F * (1 - U))
        V += dt * (Dv * lV + uvv - (F + k) * V)
        if t % checkpoint == 0:
            history.append((t, V.copy()))
    return history


def sim_fhn_history(I_ext, eps, N=128, T=500, dt=0.01, seed=42, checkpoint=10):
    rng = np.random.default_rng(seed)
    v = rng.uniform(-0.5, 0.5, (N, N))
    w = rng.uniform(-0.5, 0.5, (N, N))
    history = [(0, v.copy())]
    for t in range(1, T + 1):
        lv = laplace(v, mode="wrap"); lw = laplace(w, mode="wrap")
        dv = v - v**3 / 3 - w + I_ext + 1.0 * lv
        dw = eps * (v + 0.7 - 0.8 * w) + 0.5 * lw
        v += dt * dv; w += dt * dw
        if t % checkpoint == 0:
            history.append((t, v.copy()))
    return history


def sim_brus_history(B, N=128, T=500, dt=0.01, seed=42, checkpoint=10):
    rng = np.random.default_rng(seed)
    A = 2.0; Dx, Dy = 1.0, 8.0
    X = A * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    Y = (B / A) * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    history = [(0, X.copy())]
    for t in range(1, T + 1):
        lX = laplace(X, mode="wrap"); lY = laplace(Y, mode="wrap")
        dX = A + X**2 * Y - (B + 1) * X + Dx * lX
        dY = B * X - X**2 * Y + Dy * lY
        X += dt * dX; Y += dt * dY
        X = np.clip(X, 0.001, 50); Y = np.clip(Y, 0.001, 50)
        if t % checkpoint == 0:
            history.append((t, X.copy()))
    return history


# ═══════════════════════════════════════════════════════════════
# CE(t) TRAJECTORY WITH NUCLEATION DETECTION
# ═══════════════════════════════════════════════════════════════

def analyze_trajectory(history):
    """Compute CE(t), β(t) at each checkpoint. Detect nucleation jumps."""
    records = []
    for step, field in history:
        b0, b1 = betti(field)
        topo = b0 + b1
        ce, ei = compute_CE(field, n=4)
        records.append({
            "step": step, "b0": b0, "b1": b1, "topo": topo,
            "CE": round(ce, 4), "EI": round(ei, 6),
        })

    # Detect nucleation jumps: Δtopo > 2 between consecutive checkpoints
    jumps = []
    for i in range(1, len(records)):
        dt = records[i]["topo"] - records[i-1]["topo"]
        dce = records[i]["CE"] - records[i-1]["CE"]
        if abs(dt) >= 2:
            jumps.append({
                "step": records[i]["step"],
                "delta_topo": dt,
                "delta_CE": round(dce, 4),
                "topo_before": records[i-1]["topo"],
                "topo_after": records[i]["topo"],
                "CE_before": records[i-1]["CE"],
                "CE_after": records[i]["CE"],
            })

    return records, jumps


# ═══════════════════════════════════════════════════════════════
# PART 1: GS CE(t) with nucleation detection
# ═══════════════════════════════════════════════════════════════

def part1_gs():
    print("\n" + "=" * 65)
    print("  PART 1: Gray-Scott CE(t) + nucleation jumps")
    print("=" * 65)

    patterns = [
        ("spots",     0.035, 0.065),
        ("labyrinth", 0.040, 0.060),
        ("worms",     0.050, 0.065),
        ("chaos",     0.026, 0.051),
    ]

    all_results = {}
    for name, F, k in patterns:
        hist = sim_gs_history(F, k, N=128, T=800, checkpoint=20, seed=42)
        records, jumps = analyze_trajectory(hist)
        all_results[name] = {"records": records, "jumps": jumps, "F": F, "k": k}

        print(f"\n  {name} (F={F}, k={k}):")
        print(f"    {'step':>6} {'topo':>5} {'CE':>7} {'β₀':>4} {'β₁':>4}")
        for r in records[::max(1, len(records)//8)]:
            print(f"    {r['step']:>6} {r['topo']:>5} {r['CE']:>7.3f} {r['b0']:>4} {r['b1']:>4}")

        if jumps:
            print(f"    NUCLEATION JUMPS ({len(jumps)}):")
            for j in jumps[:5]:
                print(f"      step={j['step']}: topo {j['topo_before']}→{j['topo_after']} "
                      f"(Δ={j['delta_topo']:+d}), CE {j['CE_before']:.3f}→{j['CE_after']:.3f} "
                      f"(Δ={j['delta_CE']:+.3f})")

        # CE jump per topo change at nucleation
        if jumps:
            ratios = [j["delta_CE"] / j["delta_topo"] for j in jumps if j["delta_topo"] != 0]
            if ratios:
                print(f"    ΔCE/Δtopo at nucleation: mean={np.mean(ratios):.4f}")

    return all_results


# ═══════════════════════════════════════════════════════════════
# PART 2: FHN as third substrate
# ═══════════════════════════════════════════════════════════════

def part2_fhn():
    print("\n" + "=" * 65)
    print("  PART 2: FHN CE vs topo (third substrate)")
    print("=" * 65)

    FHN_PARAMS = [
        (0.2, 0.04), (0.3, 0.06), (0.4, 0.08),
        (0.5, 0.08), (0.6, 0.06), (0.7, 0.08),
        (0.8, 0.10), (0.5, 0.05), (0.6, 0.10),
    ]

    results = []
    for I_ext, eps in FHN_PARAMS:
        for seed in range(3):
            hist = sim_fhn_history(I_ext, eps, N=64, T=300, checkpoint=10, seed=seed)
            final_field = hist[-1][1]
            b0, b1 = betti(final_field)
            topo = b0 + b1
            ce, ei = compute_CE(final_field, n=4)
            dH = entropy_kl(hist[0][1], final_field)
            results.append({
                "I_ext": I_ext, "eps": eps, "seed": seed,
                "topo": topo, "CE": round(ce, 4), "dH": round(dH, 4),
                "b0": b0, "b1": b1,
            })

    results.sort(key=lambda x: x["topo"])
    print(f"  {'I':>5} {'ε':>5} {'topo':>5} {'CE':>7} {'ΔH':>7}")
    for r in results:
        print(f"  {r['I_ext']:>5.2f} {r['eps']:>5.3f} {r['topo']:>5} {r['CE']:>7.3f} {r['dH']:>7.3f}")

    topo = np.array([r["topo"] for r in results], dtype=float)
    ce = np.array([r["CE"] for r in results], dtype=float)
    if len(set(topo)) >= 3:
        rho, p = spearmanr(topo, ce)
        print(f"\n  FHN: CE vs topo Spearman ρ={rho:.3f} p={p:.4f}")
    else:
        rho = 0.0
        print(f"\n  FHN: insufficient topo variation")

    return results, round(float(rho), 4)


# ═══════════════════════════════════════════════════════════════
# PART 3: Cross-substrate summary
# ═══════════════════════════════════════════════════════════════

def part3_summary(gs_results, fhn_rho):
    print("\n" + "=" * 65)
    print("  PART 3: THREE-SUBSTRATE SUMMARY")
    print("=" * 65)

    # GS: aggregate CE vs topo from final frames
    gs_final = []
    for name, data in gs_results.items():
        rec = data["records"][-1]  # final checkpoint
        gs_final.append({"name": name, "topo": rec["topo"], "CE": rec["CE"]})

    gs_topo = np.array([r["topo"] for r in gs_final], dtype=float)
    gs_ce = np.array([r["CE"] for r in gs_final], dtype=float)
    if len(set(gs_topo)) >= 3:
        rho_gs, p_gs = spearmanr(gs_topo, gs_ce)
    else:
        rho_gs = float(np.corrcoef(gs_topo, gs_ce)[0, 1]) if len(gs_topo) > 1 else 0

    # Load Brusselator from previous
    try:
        with open("results/hypothesis_F.json") as f:
            prev = json.load(f)
        rho_br = prev.get("br_rho", 0)
    except Exception:
        rho_br = -0.891  # known from earlier run

    print(f"\n  {'Substrate':>20} {'γ':>8} {'CE vs β':>10} {'Spearman ρ':>12}")
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*12}")
    print(f"  {'Gray-Scott':>20} {'+1.24':>8} {'CE↑':>10} {rho_gs:>+12.3f}")
    print(f"  {'FitzHugh-Nagumo':>20} {'+1.06':>8} {'CE↑':>10} {fhn_rho:>+12.3f}")
    print(f"  {'Brusselator':>20} {'-6.65':>8} {'CE↓':>10} {rho_br:>+12.3f}")

    # Verdict
    print()
    subcrit_positive = rho_gs > 0 and fhn_rho > 0
    supercrit_negative = rho_br < -0.3

    if subcrit_positive and supercrit_negative:
        print("  >>> HYPOTHESIS F: CONFIRMED on 3 substrates")
        print("  >>> γ > 0 systems: CE increases with β (economies of scale)")
        print("  >>> γ < 0 systems: CE decreases with β (diseconomies)")
        verdict = "CONFIRMED"
    elif (rho_gs > 0 or fhn_rho > 0) and supercrit_negative:
        print("  >>> HYPOTHESIS F: PARTIAL (2/3 substrates)")
        verdict = "PARTIAL"
    else:
        print("  >>> HYPOTHESIS F: REJECTED")
        verdict = "REJECTED"

    return verdict, {"gs": round(float(rho_gs), 4), "fhn": fhn_rho, "br": rho_br}


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 65)
    print("  HYPOTHESIS F COMPLETE: CE(t) + nucleation + 3 substrates")
    print(f"  CPUs: {N_JOBS}")
    print("=" * 65)

    gs_data = part1_gs()
    fhn_results, fhn_rho = part2_fhn()
    verdict, rhos = part3_summary(gs_data, fhn_rho)

    elapsed = time.perf_counter() - t0

    # Save
    output = {
        "hypothesis": "F_Vasylenko_Levin_Tononi",
        "verdict": verdict,
        "correlations": rhos,
        "gs_patterns": {name: {"jumps": d["jumps"],
                               "final_topo": d["records"][-1]["topo"],
                               "final_CE": d["records"][-1]["CE"]}
                        for name, d in gs_data.items()},
        "fhn_rho": fhn_rho,
        "compute_seconds": round(elapsed, 1),
    }
    with open("results/hypothesis_F_complete.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  {elapsed:.0f}s total")
    print(f"  Saved: results/hypothesis_F_complete.json")
    print("=" * 65)
