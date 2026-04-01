#!/usr/bin/env python3
"""HK-Invariant: dH/dt = -α·I_W - β·I_FR (Hellinger-Kantorovich decomposition).

Three-layer verification:
  L1: Global OLS regression for α, β
  L2: Phase-specific (pre/during/post bifurcation)
  L3: Cross-substrate comparison (GS vs FHN vs CH control)
"""

import json
import multiprocessing
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace

N_JOBS = min(multiprocessing.cpu_count(), 8)


def to_prob(f):
    a = np.abs(f).ravel().astype(np.float64) + 1e-12
    return a / a.sum()


def compute_HK(field_t, field_t1, field_ref, dt):
    p_t = to_prob(field_t)
    p_t1 = to_prob(field_t1)
    p_ref = to_prob(field_ref)

    H_t = float(np.sum(p_t * np.log(p_t / (p_ref + 1e-12))))
    H_t1 = float(np.sum(p_t1 * np.log(p_t1 / (p_ref + 1e-12))))
    dH_dt = (H_t1 - H_t) / dt

    I_W = float(np.sum((p_t - p_ref) ** 2 / (p_ref + 1e-12)))

    log_ratio = np.log(p_t / (p_ref + 1e-12))
    I_FR = float(np.sum(p_t * log_ratio ** 2))

    return {
        "dH_dt": dH_dt, "I_W": I_W, "I_FR": I_FR,
        "valid": dH_dt < 0 and I_W > 1e-8 and I_FR > 1e-8,
    }


def fit_OLS(records):
    valid = [r for r in records if r["valid"]]
    if len(valid) < 10:
        return None
    y = np.array([-r["dH_dt"] for r in valid])
    X = np.column_stack([
        [r["I_W"] for r in valid],
        [r["I_FR"] for r in valid],
    ])
    try:
        coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
        alpha, beta = float(coeffs[0]), float(coeffs[1])
        y_pred = X @ coeffs
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"alpha": round(alpha, 6), "beta": round(beta, 6),
                "R2": round(r2, 4), "n": len(valid)}
    except Exception:
        return None


def detect_phases(traj):
    v = np.array([float(np.var(f)) for f in traj])
    dv = np.diff(v)
    if len(dv) == 0:
        return ["post"] * len(traj)
    thr = np.mean(dv) + 2 * np.std(dv)
    bif = np.where(dv > thr)[0]
    if len(bif) == 0:
        return ["post"] * len(traj)
    onset = int(bif[0])
    end = min(int(bif[-1]) + 5, len(traj) - 1)
    return ["pre" if i < onset else "during" if i <= end else "post"
            for i in range(len(traj))]


# ═══════════════════════════════════════════════════════════════
# SIMULATORS
# ═══════════════════════════════════════════════════════════════

def sim_gs(N=64, T=300, dt=0.5, seed=42):
    rng = np.random.default_rng(seed)
    U = np.ones((N, N)); V = np.zeros((N, N))
    r = N // 4; cx, cy = N // 2, N // 2
    U[cx-r:cx+r, cy-r:cy+r] = 0.5
    V[cx-r:cx+r, cy-r:cy+r] = 0.25 + 0.1 * rng.random((2*r, 2*r))
    F, k, Du, Dv = 0.055, 0.062, 0.16, 0.08
    hist = [V.copy()]
    for _ in range(T):
        lU = laplace(U, mode="wrap"); lV = laplace(V, mode="wrap")
        uvv = U * V * V
        U += dt * (Du * lU - uvv + F * (1 - U))
        V += dt * (Dv * lV + uvv - (F + k) * V)
        if _ % 5 == 0:
            hist.append(V.copy())
    return np.array(hist)


def sim_fhn(N=64, T=300, dt=0.01, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.uniform(-0.5, 0.5, (N, N))
    w = rng.uniform(-0.5, 0.5, (N, N))
    hist = [v.copy()]
    for _ in range(T):
        lv = laplace(v, mode="wrap"); lw = laplace(w, mode="wrap")
        dv = v - v**3/3 - w + 0.5 + 1.0 * lv
        dw = 0.08 * (v + 0.7 - 0.8 * w) + 0.5 * lw
        v += dt * dv; w += dt * dw
        if _ % 5 == 0:
            hist.append(v.copy())
    return np.array(hist)


def sim_ch(N=64, T=300, dt=0.1, seed=42):
    rng = np.random.default_rng(seed)
    phi = rng.uniform(-0.1, 0.1, (N, N))
    gamma = 0.01
    def lap(f):
        return np.roll(f,1,0)+np.roll(f,-1,0)+np.roll(f,1,1)+np.roll(f,-1,1)-4*f
    hist = [phi.copy()]
    for _ in range(T):
        mu = phi**3 - phi - gamma * lap(phi)
        phi += dt * lap(mu)
        phi = np.clip(phi, -5, 5)
        if _ % 5 == 0:
            hist.append(phi.copy())
    return np.array(hist)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_substrate(name, sim_fn, dt, n_seeds=30):
    print(f"\n{'=' * 55}")
    print(f"  {name}")
    print(f"{'=' * 55}")

    def one_seed(seed):
        traj = sim_fn(seed=seed)
        ref = traj[-1]
        phases = detect_phases(traj)
        recs = {"all": [], "pre": [], "during": [], "post": []}
        for i in range(len(traj) - 1):
            r = compute_HK(traj[i], traj[i+1], ref, dt)
            if r["valid"]:
                recs["all"].append(r)
                recs[phases[i]].append(r)
        return recs

    all_recs = Parallel(n_jobs=N_JOBS)(delayed(one_seed)(s) for s in range(n_seeds))

    merged = {"all": [], "pre": [], "during": [], "post": []}
    for rec in all_recs:
        for phase in merged:
            merged[phase].extend(rec[phase])

    results = {}

    # L1: Global
    fit = fit_OLS(merged["all"])
    if fit:
        print(f"\n  L1 Global: dH/dt = -{fit['alpha']:.4f}·I_W - {fit['beta']:.4f}·I_FR")
        print(f"     R² = {fit['R2']:.4f}  n = {fit['n']}")
        results["global"] = fit

    # L2: Phase
    print(f"\n  L2 Phase:")
    for phase in ["pre", "during", "post"]:
        pf = fit_OLS(merged[phase])
        if pf:
            ba = pf["beta"] / (pf["alpha"] + 1e-10)
            print(f"     {phase:8s}: α={pf['alpha']:.4f}  β={pf['beta']:.4f}  "
                  f"β/α={ba:.3f}  R²={pf['R2']:.3f}  n={pf['n']}")
            results[f"phase_{phase}"] = pf

    # HK Consistency
    if fit:
        recs = merged["all"]
        y = np.array([-r["dH_dt"] for r in recs])
        pred = np.array([fit["alpha"] * r["I_W"] + fit["beta"] * r["I_FR"] for r in recs])
        ci = float(1 - np.mean(np.abs(y - pred)) / (np.mean(np.abs(y)) + 1e-10))
        print(f"\n  HK Consistency Index: {ci:.4f}")
        results["hk_ci"] = round(ci, 4)

    return results


if __name__ == "__main__":
    print("=" * 55)
    print("  HK-INVARIANT: dH/dt = -α·I_W - β·I_FR")
    print(f"  CPUs: {N_JOBS}")
    print("=" * 55)

    subs = {
        "Gray-Scott": (sim_gs, 0.5),
        "FitzHugh-Nagumo": (sim_fhn, 0.05),
        "Cahn-Hilliard": (sim_ch, 0.5),
    }

    all_res = {}
    for name, (fn, dt) in subs.items():
        all_res[name] = run_substrate(name, fn, dt, n_seeds=30)

    # CROSS-SUBSTRATE
    print("\n" + "=" * 55)
    print("  CROSS-SUBSTRATE COMPARISON")
    print("=" * 55)
    print(f"  {'Substrate':20} {'α':>8} {'β':>8} {'β/α':>8} {'R²':>8} {'HK-CI':>8}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for name, res in all_res.items():
        g = res.get("global")
        if g:
            ba = g["beta"] / (g["alpha"] + 1e-10)
            ci = res.get("hk_ci", 0)
            print(f"  {name:20} {g['alpha']:8.4f} {g['beta']:8.4f} "
                  f"{ba:8.3f} {g['R2']:8.4f} {ci:8.4f}")

    # VERDICT
    gs = all_res.get("Gray-Scott", {}).get("global")
    fhn = all_res.get("FitzHugh-Nagumo", {}).get("global")
    ch = all_res.get("Cahn-Hilliard", {}).get("global")

    print()
    if gs and fhn:
        a_diff = abs(gs["alpha"] - fhn["alpha"]) / (abs(gs["alpha"]) + 1e-10)
        b_diff = abs(gs["beta"] - fhn["beta"]) / (abs(gs["beta"]) + 1e-10)
        ba_gs = gs["beta"] / (gs["alpha"] + 1e-10)
        ba_fhn = fhn["beta"] / (fhn["alpha"] + 1e-10)
        ba_diff = abs(ba_gs - ba_fhn) / (abs(ba_gs) + 1e-10)

        print(f"  α difference (GS vs FHN): {a_diff:.1%}")
        print(f"  β difference (GS vs FHN): {b_diff:.1%}")
        print(f"  β/α ratio GS={ba_gs:.3f} FHN={ba_fhn:.3f} diff={ba_diff:.1%}")

        if a_diff < 0.3 and b_diff < 0.3:
            print("\n  >>> α, β INVARIANT across RD substrates")
        elif ba_diff < 0.3:
            print("\n  >>> β/α RATIO invariant (reaction/diffusion balance conserved)")
        elif gs["R2"] > 0.8 and fhn["R2"] > 0.8:
            print("\n  >>> HK decomposition VALID (R²>0.8) but coefficients substrate-specific")
        else:
            print("\n  >>> HK decomposition does NOT fit the data well")

    os.makedirs("results", exist_ok=True)
    with open("results/hk_invariant.json", "w") as f:
        json.dump(all_res, f, indent=2, default=str)
    print(f"\n  Saved: results/hk_invariant.json")
    print("=" * 55)
