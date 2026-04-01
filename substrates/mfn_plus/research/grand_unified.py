#!/usr/bin/env python3
"""Grand Unified Experiment — Vasylenko Thermodynamic Topology Framework.

All metrics, all substrates, one sweep.
"""

import json
import multiprocessing
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace, label
from scipy.signal import correlate2d
from scipy.stats import spearmanr, linregress

N_JOBS = min(multiprocessing.cpu_count(), 12)


def betti(field):
    t = np.median(field)
    b = field > t
    _, b0 = label(b)
    p = b.astype(int)
    V = p.sum()
    Eh = (p[:, :-1] * p[:, 1:]).sum()
    Ev = (p[:-1, :] * p[1:, :]).sum()
    F = (p[:-1, :-1] * p[:-1, 1:] * p[1:, :-1] * p[1:, 1:]).sum()
    return int(b0), int(max(0, b0 - (V - Eh - Ev + F)))


def entropy(f1, f2):
    p = np.abs(f1).ravel() + 1e-12; p /= p.sum()
    q = np.abs(f2).ravel() + 1e-12; q /= q.sum()
    return max(0, float(np.sum(p * np.log(p / q))))


def CE(field):
    N = field.shape[0]
    macro = np.array([field[:N//2, :N//2].mean(), field[:N//2, N//2:].mean(),
                      field[N//2:, :N//2].mean(), field[N//2:, N//2:].mean()])
    return float(macro.var() / (field.var() + 1e-12))


def xi(field):
    f = field - field.mean()
    if f.std() < 1e-10: return 0.0
    N = field.shape[0]
    F_hat = np.fft.fft2(f)
    C = np.real(np.fft.ifft2(np.abs(F_hat)**2)) / (f.std()**2 * N * N + 1e-12)
    C_s = np.fft.fftshift(C)
    cy, cx = N // 2, N // 2
    y, x = np.ogrid[:C_s.shape[0], :C_s.shape[1]]
    r = np.sqrt((x - cx)**2 + (y - cy)**2).astype(int)
    C_rad = np.zeros(N // 2)
    for ri in range(N // 2):
        m = r == ri
        if m.any(): C_rad[ri] = C_s[m].mean()
    if C_rad[0] > 1e-12: C_rad /= C_rad[0]
    zc = np.where(np.diff(np.sign(C_rad)))[0]
    if len(zc): return float(zc[0])
    be = np.where(C_rad < 1 / np.e)[0]
    return float(be[0]) if len(be) else float(N // 2)


def sigma_ex(traj):
    eps = []
    for i in range(max(0, len(traj) - 5), len(traj) - 1):
        d = traj[i + 1] - traj[i]
        total = float(np.sum(d**2))
        g = np.gradient(traj[i])
        hk = float(np.sum(g[0]**2 + g[1]**2)) * 0.01
        eps.append(max(0, total - hk))
    return float(np.mean(eps)) if eps else 0.0


# ═══════════════════════════════════════════════════════
# SIMULATORS
# ═══════════════════════════════════════════════════════

def sim_gs(F, k, N=128, T=500, dt=0.5, seed=42):
    rng = np.random.default_rng(seed)
    U = np.ones((N, N)); V = np.zeros((N, N))
    coords = rng.integers(5, N - 5, size=(20, 2))
    for cx, cy in coords:
        U[cx:cx+4, cy:cy+4] = 0.5; V[cx:cx+4, cy:cy+4] = 0.25
    V += np.abs(rng.normal(0, 0.01, (N, N)))
    hist = [V.copy()]
    for _ in range(T):
        lU = laplace(U, mode='wrap'); lV = laplace(V, mode='wrap')
        uvv = U * V * V
        U += dt * (0.16 * lU - uvv + F * (1 - U))
        V += dt * (0.08 * lV + uvv - (F + k) * V)
        U = np.clip(U, 0, 1); V = np.clip(V, 0, 1)
        if _ % 25 == 0: hist.append(V.copy())
    return np.array(hist)


def sim_fhn(I_ext, eps, N=128, T=500, dt=0.01, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.uniform(-0.5, 0.5, (N, N))
    w = rng.uniform(-0.5, 0.5, (N, N))
    hist = [v.copy()]
    for _ in range(T):
        lv = laplace(v, mode='wrap'); lw = laplace(w, mode='wrap')
        v += dt * (v - v**3/3 - w + I_ext + 1.0 * lv)
        w += dt * (eps * (v + 0.7 - 0.8 * w) + 0.5 * lw)
        if _ % 25 == 0: hist.append(v.copy())
    return np.array(hist)


def sim_br(B, N=128, T=500, dt=0.01, seed=42):
    rng = np.random.default_rng(seed)
    A = 2.0
    X = A * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    Y = (B / A) * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    hist = [X.copy()]
    for _ in range(T):
        lX = laplace(X, mode='wrap'); lY = laplace(Y, mode='wrap')
        X += dt * (A + X**2 * Y - (B + 1) * X + 1.0 * lX)
        Y += dt * (B * X - X**2 * Y + 8.0 * lY)
        X = np.clip(X, 0.001, 50); Y = np.clip(Y, 0.001, 50)
        if _ % 25 == 0: hist.append(X.copy())
    return np.array(hist)


# ═══════════════════════════════════════════════════════
# MEASURE
# ═══════════════════════════════════════════════════════

def measure(name, sim_fn, params, L_sign, seed=42):
    try:
        traj = sim_fn(*params, seed=seed)
        final = traj[-1]; ref = traj[0]
        b0, b1 = betti(final)
        topo = b0 + b1
        if topo < 3: return None
        dH = entropy(ref, final)
        cost = dH / (topo + 1e-10)

        # Nucleation: first topo jump
        nuc = None
        tp, cp = 0, CE(traj[0])
        for frame in traj[1:]:
            b0f, b1f = betti(frame)
            tf = b0f + b1f; cf = CE(frame)
            if tf > tp + 2 and tp < 10 and tf - tp > 0:
                nuc = (cf - cp) / (tf - tp)
                break
            tp, cp = tf, cf

        return {"sub": name, "params": [float(p) for p in params], "seed": seed,
                "b0": b0, "b1": b1, "topo": topo,
                "dH": round(dH, 4), "cost": round(cost, 6),
                "CE": round(CE(final), 6), "xi": round(xi(final), 1),
                "sigma_ex": round(sigma_ex(traj), 6),
                "L": L_sign, "nuc": round(nuc, 6) if nuc else None}
    except Exception:
        return None


GS = [((F, k), +1) for F, k in [
    (0.020, 0.055), (0.025, 0.058), (0.030, 0.060), (0.035, 0.060),
    (0.040, 0.060), (0.045, 0.061), (0.050, 0.062), (0.055, 0.062),
    (0.014, 0.053), (0.018, 0.057), (0.026, 0.051), (0.030, 0.065),
    (0.035, 0.065), (0.040, 0.065),
]]
FHN = [((I, e), +1) for I, e in [
    (0.3, 0.05), (0.4, 0.06), (0.5, 0.07), (0.6, 0.08),
    (0.7, 0.09), (0.8, 0.10), (0.5, 0.05), (0.6, 0.06),
]]
BR = [((B,), -1) for B in [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]]

if __name__ == "__main__":
    t0 = time.perf_counter()
    print("=" * 65)
    print("  GRAND UNIFIED EXPERIMENT")
    print("  Vasylenko Thermodynamic Topology Framework")
    print(f"  CPUs: {N_JOBS}")
    print("=" * 65)

    jobs = []
    for (p, L) in GS:
        for s in range(2): jobs.append(("GS", sim_gs, p, L, s))
    for (p, L) in FHN:
        for s in range(2): jobs.append(("FHN", sim_fhn, p, L, s))
    for (p, L) in BR:
        for s in range(2): jobs.append(("BR", sim_br, p, L, s))

    print(f"\n  {len(jobs)} runs across 3 substrates...")
    raw = Parallel(n_jobs=N_JOBS)(
        delayed(measure)(n, f, p, L, s) for n, f, p, L, s in jobs
    )
    valid = [r for r in raw if r is not None]
    print(f"  Valid: {len(valid)}/{len(jobs)}")

    # Group
    by_sub = {}
    for r in valid:
        by_sub.setdefault(r["sub"], []).append(r)

    analyses = {}
    for name, recs in by_sub.items():
        topo = np.array([r["topo"] for r in recs], dtype=float)
        cost = np.array([r["cost"] for r in recs])
        ce = np.array([r["CE"] for r in recs])
        xi_arr = np.array([r["xi"] for r in recs])

        # γ
        mask = (topo > 0) & (cost > 0)
        if mask.sum() > 3:
            sl, _, rv, pv, _ = linregress(np.log(topo[mask]), np.log(cost[mask]))
            gamma, R2 = -sl, rv**2
        else:
            gamma, R2 = 0, 0

        rho_ce, p_ce = spearmanr(topo, ce) if len(set(topo)) >= 3 else (0, 1)
        rho_xi, p_xi = spearmanr(topo, xi_arr) if len(set(topo)) >= 3 and np.std(xi_arr) > 0 else (0, 1)

        nucs = [r["nuc"] for r in recs if r["nuc"] is not None]
        L = recs[0]["L"]

        if L > 0 and rho_ce > 0.3 and rho_xi > 0.3:
            cls = "Class I (Causal+Coherent)"
        elif L > 0 and rho_xi > 0.3:
            cls = "Class II (Coherent)"
        elif L > 0 and rho_ce > 0.3:
            cls = "Class I (Causal)"
        elif L < 0:
            cls = "Class III (Neither)"
        else:
            cls = "Undefined"

        analyses[name] = {
            "n": len(recs), "gamma": round(gamma, 3), "R2": round(R2, 3),
            "rho_CE": round(float(rho_ce), 3), "p_CE": round(float(p_ce), 4),
            "rho_xi": round(float(rho_xi), 3), "p_xi": round(float(p_xi), 4),
            "nuc_mean": round(float(np.mean(nucs)), 4) if nucs else None,
            "L": L, "class": cls,
            "topo_range": [int(topo.min()), int(topo.max())],
            "cost_mean": round(float(cost.mean()), 4),
            "sigma_ex_mean": round(float(np.mean([r["sigma_ex"] for r in recs])), 6),
        }

    # Print
    print(f"\n{'=' * 70}")
    print("  PUBLICATION TABLE")
    print(f"{'=' * 70}")
    print(f"  {'Sub':>12} {'γ':>7} {'R²':>6} {'ρ_CE':>7} {'ρ_ξ':>7} {'L':>3} {'σ_ex':>10} {'Class'}")
    print(f"  {'-'*12} {'-'*7} {'-'*6} {'-'*7} {'-'*7} {'-'*3} {'-'*10} {'-'*25}")
    for name in ["GS", "FHN", "BR"]:
        a = analyses.get(name)
        if a:
            print(f"  {name:>12} {a['gamma']:>+7.3f} {a['R2']:>6.3f} "
                  f"{a['rho_CE']:>+7.3f} {a['rho_xi']:>+7.3f} {a['L']:>+3d} "
                  f"{a['sigma_ex_mean']:>10.6f} {a['class']}")

    # Hypothesis F
    print(f"\n  HYPOTHESIS F (sign(γ) = sign(ρ_CE)):")
    confirmed = 0
    for name, a in analyses.items():
        match = np.sign(a["gamma"]) == np.sign(a["rho_CE"])
        confirmed += int(match)
        print(f"    {name:>8}: γ={a['gamma']:+.3f} ρ_CE={a['rho_CE']:+.3f} {'✓' if match else '✗'}")
    print(f"    Confirmed: {confirmed}/{len(analyses)}")

    # Nucleation
    print(f"\n  NUCLEATION INVARIANT:")
    for name, a in analyses.items():
        if a["nuc_mean"]: print(f"    {name:>8}: ΔCE/Δtopo = {a['nuc_mean']:.4f}")

    elapsed = time.perf_counter() - t0

    with open("results/grand_unified.json", "w") as f:
        json.dump({"analyses": analyses, "raw": valid,
                   "compute_seconds": round(elapsed, 1)}, f, indent=2, default=str)

    print(f"\n  {elapsed:.0f}s | Saved: results/grand_unified.json")
    print("=" * 70)
