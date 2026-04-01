#!/usr/bin/env python3
"""Universal Cost of Complexity: ΔH / (β₀ + β₁) = C?"""

import json
import multiprocessing
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace, label

N_JOBS = min(multiprocessing.cpu_count(), 8)

try:
    import gudhi
    def compute_betti(field):
        f = np.asarray(field, dtype=np.float64)
        f_range = f.max() - f.min()
        if f_range < 1e-12:
            return 0, 0
        f_sup = f.max() - f
        f_norm = f_sup / (f_sup.max() + 1e-12)
        cc = gudhi.CubicalComplex(top_dimensional_cells=f_norm)
        cc.compute_persistence()
        pairs = cc.persistence()
        min_pers = 0.01
        b0 = sum(1 for d, (b, de) in pairs if d == 0 and de != float('inf') and (de - b) > min_pers)
        b1 = sum(1 for d, (b, de) in pairs if d == 1 and de != float('inf') and (de - b) > min_pers)
        return b0, b1
    print("TDA: GUDHI")
except ImportError:
    def compute_betti(field):
        thr = np.median(field)
        binary = field > thr
        labeled_arr, b0 = label(binary)
        p = binary.astype(int)
        V = p.sum()
        E_h = (p[:, :-1] * p[:, 1:]).sum()
        E_v = (p[:-1, :] * p[1:, :]).sum()
        F = (p[:-1,:-1] * p[:-1,1:] * p[1:,:-1] * p[1:,1:]).sum()
        euler = V - E_h - E_v + F
        b1 = max(0, b0 - euler)
        return b0, b1
    print("TDA: simple (install gudhi for better results)")


def to_prob(f):
    a = np.abs(f).ravel().astype(np.float64) + 1e-12
    return a / a.sum()


def entropy_kl(field, ref):
    p = to_prob(field)
    q = to_prob(ref)
    return max(0.0, float(np.sum(p * np.log(p / (q + 1e-12)))))


def sim_gs(F, k, N=64, T=300, dt=0.5, seed=42):
    rng = np.random.default_rng(seed)
    U = np.ones((N, N)); V = np.zeros((N, N))
    r = N // 4; cx, cy = N // 2, N // 2
    U[cx-r:cx+r, cy-r:cy+r] = 0.5
    V[cx-r:cx+r, cy-r:cy+r] = 0.25 + 0.1 * rng.random((2*r, 2*r))
    Du, Dv = 0.16, 0.08
    for _ in range(T):
        lU = laplace(U, mode='wrap'); lV = laplace(V, mode='wrap')
        uvv = U * V * V
        U += dt * (Du * lU - uvv + F * (1 - U))
        V += dt * (Dv * lV + uvv - (F + k) * V)
    return V, rng.uniform(0, 0.1, (N, N))  # final field, initial proxy


def sim_fhn(I_ext, eps, N=64, T=300, dt=0.01, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.uniform(-0.5, 0.5, (N, N))
    w = rng.uniform(-0.5, 0.5, (N, N))
    v_init = v.copy()
    for _ in range(T):
        lv = laplace(v, mode='wrap'); lw = laplace(w, mode='wrap')
        dv = v - v**3/3 - w + I_ext + 1.0 * lv
        dw = eps * (v + 0.7 - 0.8 * w) + 0.5 * lw
        v += dt * dv; w += dt * dw
    return v, v_init


GS_PARAMS = [
    (0.020, 0.055), (0.025, 0.058), (0.030, 0.060),
    (0.035, 0.060), (0.040, 0.060), (0.045, 0.061),
    (0.050, 0.062), (0.055, 0.062), (0.060, 0.062),
    (0.065, 0.063), (0.035, 0.065), (0.040, 0.065),
    (0.045, 0.063), (0.050, 0.064), (0.030, 0.057),
]

FHN_PARAMS = [
    (0.2, 0.04), (0.3, 0.05), (0.4, 0.06),
    (0.5, 0.07), (0.5, 0.08), (0.6, 0.08),
    (0.7, 0.09), (0.8, 0.10), (0.9, 0.11),
    (1.0, 0.12), (0.6, 0.06), (0.7, 0.07),
    (0.8, 0.08), (0.4, 0.10), (0.3, 0.12),
]


def measure_gs(args):
    F, k, seed = args
    try:
        final, init = sim_gs(F, k, seed=seed)
        dH = entropy_kl(init, final)
        b0, b1 = compute_betti(final)
        topo = b0 + b1
        return {"F": F, "k": k, "seed": seed, "dH": round(dH, 6),
                "b0": b0, "b1": b1, "topo": topo,
                "cost": round(dH / (topo + 1e-6), 6), "valid": topo > 0}
    except Exception:
        return {"valid": False}


def measure_fhn(args):
    I_ext, eps, seed = args
    try:
        final, init = sim_fhn(I_ext, eps, seed=seed)
        dH = entropy_kl(init, final)
        b0, b1 = compute_betti(final)
        topo = b0 + b1
        return {"I_ext": I_ext, "eps": eps, "seed": seed, "dH": round(dH, 6),
                "b0": b0, "b1": b1, "topo": topo,
                "cost": round(dH / (topo + 1e-6), 6), "valid": topo > 0}
    except Exception:
        return {"valid": False}


if __name__ == "__main__":
    print("=" * 60)
    print("  UNIVERSAL COST OF COMPLEXITY: ΔH / (β₀+β₁) = C?")
    print(f"  CPUs: {N_JOBS}")
    print("=" * 60)

    # Multi-seed for each parameter
    gs_jobs = [(F, k, s) for F, k in GS_PARAMS for s in range(3)]
    fhn_jobs = [(I, e, s) for I, e in FHN_PARAMS for s in range(3)]

    print(f"\n  Gray-Scott: {len(gs_jobs)} runs ({len(GS_PARAMS)} params × 3 seeds)")
    gs_all = Parallel(n_jobs=N_JOBS)(delayed(measure_gs)(j) for j in gs_jobs)
    gs_valid = [r for r in gs_all if r.get("valid")]

    print(f"  FHN: {len(fhn_jobs)} runs ({len(FHN_PARAMS)} params × 3 seeds)")
    fhn_all = Parallel(n_jobs=N_JOBS)(delayed(measure_fhn)(j) for j in fhn_jobs)
    fhn_valid = [r for r in fhn_all if r.get("valid")]

    print(f"\n  Valid: GS={len(gs_valid)} FHN={len(fhn_valid)}")

    # Results table
    print(f"\n{'=' * 60}")
    print("  GRAY-SCOTT:")
    print(f"  {'F':>6} {'k':>6} {'β₀':>4} {'β₁':>4} {'topo':>5} {'ΔH':>8} {'C':>8}")
    for r in sorted(gs_valid, key=lambda x: x["topo"]):
        print(f"  {r['F']:6.3f} {r['k']:6.3f} {r['b0']:4d} {r['b1']:4d} "
              f"{r['topo']:5d} {r['dH']:8.4f} {r['cost']:8.4f}")

    print(f"\n  FITZHUGH-NAGUMO:")
    print(f"  {'I':>6} {'ε':>6} {'β₀':>4} {'β₁':>4} {'topo':>5} {'ΔH':>8} {'C':>8}")
    for r in sorted(fhn_valid, key=lambda x: x["topo"]):
        print(f"  {r['I_ext']:6.2f} {r['eps']:6.3f} {r['b0']:4d} {r['b1']:4d} "
              f"{r['topo']:5d} {r['dH']:8.4f} {r['cost']:8.4f}")

    # Verdict
    print(f"\n{'=' * 60}")
    if gs_valid and fhn_valid:
        gs_costs = np.array([r["cost"] for r in gs_valid])
        fhn_costs = np.array([r["cost"] for r in fhn_valid])

        gs_mean = float(gs_costs.mean())
        fhn_mean = float(fhn_costs.mean())
        gs_med = float(np.median(gs_costs))
        fhn_med = float(np.median(fhn_costs))

        ratio_mean = min(gs_mean, fhn_mean) / max(gs_mean, fhn_mean)
        ratio_med = min(gs_med, fhn_med) / max(gs_med, fhn_med)

        print(f"  GS  C_mean={gs_mean:.4f}  C_median={gs_med:.4f}  "
              f"CV={gs_costs.std()/gs_mean*100:.0f}%")
        print(f"  FHN C_mean={fhn_mean:.4f}  C_median={fhn_med:.4f}  "
              f"CV={fhn_costs.std()/fhn_mean*100:.0f}%")
        print(f"  Ratio (mean): {ratio_mean:.3f}")
        print(f"  Ratio (median): {ratio_med:.3f}")

        # Correlation: does ΔH scale with topo?
        gs_topo = np.array([r["topo"] for r in gs_valid])
        gs_dH = np.array([r["dH"] for r in gs_valid])
        fhn_topo = np.array([r["topo"] for r in fhn_valid])
        fhn_dH = np.array([r["dH"] for r in fhn_valid])

        if len(gs_topo) > 3 and gs_topo.std() > 0:
            corr_gs = float(np.corrcoef(gs_topo, gs_dH)[0, 1])
        else:
            corr_gs = 0.0
        if len(fhn_topo) > 3 and fhn_topo.std() > 0:
            corr_fhn = float(np.corrcoef(fhn_topo, fhn_dH)[0, 1])
        else:
            corr_fhn = 0.0

        print(f"\n  Correlation ΔH vs topo:")
        print(f"    GS:  r={corr_gs:.3f}")
        print(f"    FHN: r={corr_fhn:.3f}")

        print()
        if ratio_mean > 0.5:
            print("  >>> COST IS SIMILAR BETWEEN SUBSTRATES")
            avg = (gs_mean + fhn_mean) / 2
            print(f"  >>> C ≈ {avg:.4f} per topological feature")
        elif ratio_mean > 0.2:
            print("  >>> SAME ORDER OF MAGNITUDE")
        else:
            print("  >>> COSTS DIFFER SUBSTANTIALLY")

        os.makedirs("results", exist_ok=True)
        with open("results/topological_cost.json", "w") as f:
            json.dump({
                "gs": gs_valid, "fhn": fhn_valid,
                "summary": {
                    "gs_mean": round(gs_mean, 6), "fhn_mean": round(fhn_mean, 6),
                    "gs_median": round(gs_med, 6), "fhn_median": round(fhn_med, 6),
                    "ratio_mean": round(ratio_mean, 4), "ratio_median": round(ratio_med, 4),
                    "corr_gs": round(corr_gs, 4), "corr_fhn": round(corr_fhn, 4),
                }
            }, f, indent=2)
        print(f"\n  Saved: results/topological_cost.json")
    print("=" * 60)
