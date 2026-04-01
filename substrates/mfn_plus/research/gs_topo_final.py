#!/usr/bin/env python3
"""GS Topological Verification — N=256, T=25000, multifocal init."""

import json
import multiprocessing
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace
from scipy.stats import spearmanr

try:
    import gudhi
    def betti(field):
        t = np.median(field)
        cc = gudhi.CubicalComplex(
            dimensions=list(field.shape),
            top_dimensional_cells=(field > t).astype(float).ravel())
        cc.compute_persistence()
        p = cc.persistence()
        return sum(1 for d, _ in p if d == 0), sum(1 for d, _ in p if d == 1)
    TDA = "gudhi"
except ImportError:
    from scipy.ndimage import label
    def betti(field):
        b = field > np.median(field)
        _, b0 = label(b)
        p = b.astype(int)
        chi = (p.sum() - (p[:, :-1]*p[:, 1:]).sum() - (p[:-1, :]*p[1:, :]).sum()
               + (p[:-1,:-1]*p[:-1,1:]*p[1:,:-1]*p[1:,1:]).sum())
        return b0, max(0, b0 - chi)
    TDA = "simple"


def simple_CE(field):
    N = field.shape[0]
    macro = np.array([
        field[:N//2, :N//2].mean(), field[:N//2, N//2:].mean(),
        field[N//2:, :N//2].mean(), field[N//2:, N//2:].mean(),
    ])
    return float(macro.var() / (field.var() + 1e-10))


def simulate_gs(F, k, N=256, T=25000, dt=0.5, seed=42):
    rng = np.random.default_rng(seed)
    Du, Dv = 0.16, 0.08
    U = np.ones((N, N), dtype=np.float64)
    V = np.zeros((N, N), dtype=np.float64)

    # 20 multifocal perturbations
    coords = rng.integers(10, N - 10, size=(20, 2))
    for cx, cy in coords:
        U[cx:cx+5, cy:cy+5] = 0.50
        V[cx:cx+5, cy:cy+5] = 0.25

    V += np.abs(rng.normal(0, 0.01, (N, N)))

    history = []
    for t in range(1, T + 1):
        lapU = laplace(U, mode="wrap")
        lapV = laplace(V, mode="wrap")
        uvv = U * V * V
        U += dt * (Du * lapU - uvv + F * (1 - U))
        V += dt * (Dv * lapV + uvv - (F + k) * V)
        U = np.clip(U, 0, 1)
        V = np.clip(V, 0, 1)
        if t % 2500 == 0:
            history.append((t, V.copy()))

    return history


def run_config(F, k):
    t0 = time.perf_counter()
    history = simulate_gs(F, k)
    elapsed = time.perf_counter() - t0
    records = []
    for t, field in history:
        b0, b1 = betti(field)
        bt = b0 + b1
        CE = simple_CE(field)
        records.append({
            "t": t, "F": F, "k": k,
            "b0": b0, "b1": b1, "bt": bt, "CE": round(CE, 6),
        })
    bt_final = records[-1]["bt"] if records else 0
    print(f"  F={F:.3f} k={k:.3f}: β_final={bt_final:>5} ({elapsed:.0f}s)")
    return records


if __name__ == "__main__":
    t0_total = time.perf_counter()

    F_vals = [0.014, 0.018, 0.022, 0.026, 0.030, 0.035, 0.040]
    k_vals = [0.049, 0.053, 0.057, 0.061, 0.065]
    configs = [(F, k) for F in F_vals for k in k_vals]

    print("=" * 60)
    print(f"  GS FINAL: {len(configs)} configs, N=256, T=25000")
    print(f"  TDA: {TDA}, CPUs: {multiprocessing.cpu_count()}")
    print("=" * 60)

    all_results = Parallel(n_jobs=multiprocessing.cpu_count())(
        delayed(run_config)(F, k) for F, k in configs
    )

    all_records = [r for batch in all_results for r in batch]
    # Filter: only records with bt >= 5
    valid = [r for r in all_records if r["bt"] >= 5]
    print(f"\n  Total records: {len(all_records)}, valid (β≥5): {len(valid)}")

    if not valid:
        print("  NO VALID DATA")
    else:
        bt = np.array([r["bt"] for r in valid], dtype=float)
        ce = np.array([r["CE"] for r in valid], dtype=float)

        print(f"  β range: [{int(bt.min())}..{int(bt.max())}]")
        print(f"  β > 100: {'YES' if bt.max() > 100 else 'NO'}")
        print(f"  CE range: [{ce.min():.4f}..{ce.max():.4f}]")

        # Unique topo levels
        unique_bt = sorted(set(int(b) for b in bt))
        print(f"  Unique β levels: {len(unique_bt)}")

        if len(unique_bt) >= 3:
            rho, p = spearmanr(bt, ce)
            print(f"\n  CE vs β_total: Spearman ρ = {rho:+.4f}  p = {p:.6f}")

            # Show data
            print(f"\n  {'β':>6} {'CE':>10} {'F':>6} {'k':>6} {'t':>6}")
            for r in sorted(valid, key=lambda x: x["bt"]):
                print(f"  {r['bt']:>6} {r['CE']:>10.6f} {r['F']:>6.3f} {r['k']:>6.3f} {r['t']:>6}")

            print()
            if rho > 0.70 and p < 0.01:
                verdict = "CONFIRMED"
                print(f"  >>> CONFIRMED: ρ={rho:.3f}, p={p:.6f}")
            elif rho > 0.40 and p < 0.05:
                verdict = "PARTIAL"
                print(f"  >>> PARTIAL: ρ={rho:.3f}")
            else:
                verdict = "REJECTED"
                print(f"  >>> REJECTED: ρ={rho:.3f}")
        else:
            rho, p = 0, 1
            verdict = "INSUFFICIENT"
            print("  >>> INSUFFICIENT topo variation")

        summary = {
            "rho": round(float(rho), 4), "p": round(float(p), 6),
            "bt_min": int(bt.min()), "bt_max": int(bt.max()),
            "n_valid": len(valid), "n_unique_bt": len(unique_bt),
            "verdict": verdict,
        }
        with open("results/gs_topo_final.json", "w") as f:
            json.dump({"summary": summary, "records": valid}, f, indent=2)

        elapsed = time.perf_counter() - t0_total
        print(f"\n  {elapsed:.0f}s total")
        print(f"  Saved: results/gs_topo_final.json")
    print("=" * 60)
