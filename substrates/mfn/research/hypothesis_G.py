#!/usr/bin/env python3
"""Hypothesis G: Two mechanisms of economies of scale.

Class I  (Causal):   γ>0, CE↑, ξ↑ → GS-type (solitons)
Class II (Coherent): γ>0, CE↓, ξ↑ → FHN-type (waves)
Class III (Neither): γ<0, CE↓, ξ↓ → Brusselator-type
"""

import json
import multiprocessing
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage import laplace
from scipy.signal import correlate2d
from scipy.stats import spearmanr

import gudhi

N_JOBS = min(multiprocessing.cpu_count(), 8)


# ═══════════════════════════════════════════════════════════════
# MEASUREMENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def betti(field, min_pers=0.005):
    f = np.asarray(field, dtype=np.float64)
    if f.max() - f.min() < 1e-12:
        return 0, 0
    fs = f.max() - f; fn = fs / (fs.max() + 1e-12)
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
    N = field.shape[0]; block = N // n
    macro = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            macro[i, j] = field[i*block:(i+1)*block, j*block:(j+1)*block].mean()
    micro_var = float(field.var()); macro_var = float(macro.var())
    EI = macro_var / (micro_var + 1e-12)
    return float(np.log(EI + 1e-12))


def compute_correlation_length(field):
    """Spatial correlation length ξ via radial autocorrelation."""
    f = field - field.mean()
    if f.std() < 1e-10:
        return 0.0

    N = field.shape[0]
    # Use FFT for fast autocorrelation
    F = np.fft.fft2(f)
    psd = np.abs(F) ** 2
    C = np.real(np.fft.ifft2(psd)) / (f.std() ** 2 * N * N)

    # Radial average
    center_y, center_x = N // 2, N // 2
    C_shifted = np.fft.fftshift(C)
    y, x = np.ogrid[:C_shifted.shape[0], :C_shifted.shape[1]]
    r = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2).astype(int)
    r_max = N // 2

    C_radial = np.zeros(r_max)
    for ri in range(r_max):
        mask = r == ri
        if mask.any():
            C_radial[ri] = C_shifted[mask].mean()

    # Normalize so C(0) = 1
    if C_radial[0] > 1e-12:
        C_radial /= C_radial[0]

    # ξ = first zero crossing (where C drops to 0)
    zero_crossings = np.where(np.diff(np.sign(C_radial)))[0]
    if len(zero_crossings) > 0:
        return float(zero_crossings[0])

    # Fallback: e-folding length
    below_e = np.where(C_radial < 1.0 / np.e)[0]
    if len(below_e) > 0:
        return float(below_e[0])

    return float(r_max)


# ═══════════════════════════════════════════════════════════════
# SIMULATORS
# ═══════════════════════════════════════════════════════════════

def sim_gs(F, k, N=128, T=800, dt=0.5, seed=42):
    rng = np.random.default_rng(seed)
    U = np.ones((N, N)); V = np.zeros((N, N))
    r = N // 4; cx, cy = N // 2, N // 2
    U[cx-r:cx+r, cy-r:cy+r] = 0.5 + 0.1 * rng.standard_normal((2*r, 2*r))
    V[cx-r:cx+r, cy-r:cy+r] = 0.25 + 0.1 * rng.random((2*r, 2*r))
    for _ in range(T):
        lU = laplace(U, mode='wrap'); lV = laplace(V, mode='wrap')
        uvv = U * V * V
        U += dt * (0.16 * lU - uvv + F * (1 - U))
        V += dt * (0.08 * lV + uvv - (F + k) * V)
    return V, rng.uniform(0, 0.1, (N, N))


def sim_fhn(I_ext, eps, N=128, T=500, dt=0.01, seed=42):
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


def sim_brus(B, N=128, T=500, dt=0.01, seed=42):
    rng = np.random.default_rng(seed)
    A = 2.0; Dx, Dy = 1.0, 8.0
    X = A * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    Y = (B / A) * np.ones((N, N)) + 0.1 * rng.standard_normal((N, N))
    init = X.copy()
    for _ in range(T):
        lX = laplace(X, mode='wrap'); lY = laplace(Y, mode='wrap')
        X += dt * (A + X**2 * Y - (B+1) * X + Dx * lX)
        Y += dt * (B * X - X**2 * Y + Dy * lY)
        X = np.clip(X, 0.001, 50); Y = np.clip(Y, 0.001, 50)
    return X, init


# ═══════════════════════════════════════════════════════════════
# PARAMETER SETS
# ═══════════════════════════════════════════════════════════════

GS_PARAMS = [
    (0.018, 0.051), (0.026, 0.051), (0.030, 0.057), (0.030, 0.060),
    (0.035, 0.060), (0.035, 0.065), (0.040, 0.060), (0.040, 0.065),
    (0.045, 0.063), (0.050, 0.062), (0.050, 0.065), (0.055, 0.062),
    (0.060, 0.062), (0.065, 0.063),
]

FHN_PARAMS = [
    (0.2, 0.04), (0.3, 0.05), (0.4, 0.06), (0.5, 0.07),
    (0.5, 0.08), (0.6, 0.06), (0.6, 0.08), (0.7, 0.08),
    (0.8, 0.10), (0.6, 0.10), (0.5, 0.05), (0.7, 0.09),
]

BRUS_PARAMS = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]


# ═══════════════════════════════════════════════════════════════
# MEASURE ALL THREE
# ═══════════════════════════════════════════════════════════════

def measure(sim_fn, args, name):
    try:
        final, init = sim_fn(*args)
        b0, b1 = betti(final)
        topo = b0 + b1
        ce = compute_CE(final, n=4)
        xi = compute_correlation_length(final)
        dH = entropy_kl(init, final)
        return {"name": name, "topo": topo, "CE": round(ce, 4),
                "xi": round(xi, 2), "dH": round(dH, 4),
                "b0": b0, "b1": b1, "valid": topo > 0}
    except Exception:
        return {"valid": False}


if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 65)
    print("  HYPOTHESIS G: Two mechanisms of economies of scale")
    print(f"  CPUs: {N_JOBS}")
    print("=" * 65)

    # GS
    print("\n  Gray-Scott...")
    gs_jobs = [(sim_gs, (F, k), "GS") for F, k in GS_PARAMS for _ in range(2)]
    gs_raw = Parallel(n_jobs=N_JOBS)(delayed(measure)(*j) for j in gs_jobs)
    gs = [r for r in gs_raw if r.get("valid")]

    # FHN
    print("  FitzHugh-Nagumo...")
    fhn_jobs = [(sim_fhn, (I, e), "FHN") for I, e in FHN_PARAMS for _ in range(2)]
    fhn_raw = Parallel(n_jobs=N_JOBS)(delayed(measure)(*j) for j in fhn_jobs)
    fhn = [r for r in fhn_raw if r.get("valid")]

    # Brusselator
    print("  Brusselator...")
    br_jobs = [(sim_brus, (B,), "BR") for B in BRUS_PARAMS for _ in range(2)]
    br_raw = Parallel(n_jobs=N_JOBS)(delayed(measure)(*j) for j in br_jobs)
    br = [r for r in br_raw if r.get("valid")]

    print(f"  Valid: GS={len(gs)} FHN={len(fhn)} BR={len(br)}")

    # ═══════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════

    def analyze(data, label):
        topo = np.array([r["topo"] for r in data], dtype=float)
        ce = np.array([r["CE"] for r in data], dtype=float)
        xi = np.array([r["xi"] for r in data], dtype=float)

        rho_ce, p_ce = spearmanr(topo, ce) if len(set(topo)) >= 3 else (0, 1)
        rho_xi, p_xi = spearmanr(topo, xi) if len(set(topo)) >= 3 else (0, 1)

        print(f"\n  {label}:")
        print(f"    topo range: [{int(topo.min())}..{int(topo.max())}]")
        print(f"    CE  vs topo: ρ={rho_ce:+.3f}  p={p_ce:.4f}")
        print(f"    ξ   vs topo: ρ={rho_xi:+.3f}  p={p_xi:.4f}")

        # Classification
        ce_up = rho_ce > 0.2 and p_ce < 0.1
        xi_up = rho_xi > 0.2 and p_xi < 0.1
        if ce_up and xi_up:
            cls = "Class I (Causal + Coherent)"
        elif xi_up:
            cls = "Class II (Coherent only)"
        elif ce_up:
            cls = "Class I (Causal only)"
        else:
            cls = "Class III (Neither)"
        print(f"    → {cls}")

        return {"rho_ce": round(float(rho_ce), 4), "p_ce": round(float(p_ce), 4),
                "rho_xi": round(float(rho_xi), 4), "p_xi": round(float(p_xi), 4),
                "class": cls}

    print(f"\n{'=' * 65}")
    print("  RESULTS")
    print(f"{'=' * 65}")

    r_gs = analyze(gs, "Gray-Scott (γ=+1.24)")
    r_fhn = analyze(fhn, "FHN (γ=+1.06)")
    r_br = analyze(br, "Brusselator (γ=-6.65)")

    # Show data points
    for label, data in [("GS", gs), ("FHN", fhn), ("BR", br)]:
        print(f"\n  {label} data:")
        print(f"  {'topo':>5} {'CE':>7} {'ξ':>6} {'ΔH':>7}")
        for r in sorted(data, key=lambda x: x["topo"])[:12]:
            print(f"  {r['topo']:>5} {r['CE']:>7.3f} {r['xi']:>6.1f} {r['dH']:>7.3f}")

    # ═══════════════════════════════════════════════════════════
    # FINAL TABLE
    # ═══════════════════════════════════════════════════════════

    elapsed = time.perf_counter() - t0

    print(f"\n{'=' * 65}")
    print("  TAXONOMY OF PATTERN-FORMING SYSTEMS")
    print(f"{'=' * 65}")
    print(f"  {'System':>15} {'γ':>6} {'CE vs β':>9} {'ξ vs β':>9} {'Class'}")
    print(f"  {'-'*15} {'-'*6} {'-'*9} {'-'*9} {'-'*30}")
    print(f"  {'Gray-Scott':>15} {'+1.24':>6} {r_gs['rho_ce']:>+9.3f} {r_gs['rho_xi']:>+9.3f} {r_gs['class']}")
    print(f"  {'FHN':>15} {'+1.06':>6} {r_fhn['rho_ce']:>+9.3f} {r_fhn['rho_xi']:>+9.3f} {r_fhn['class']}")
    print(f"  {'Brusselator':>15} {'-6.65':>6} {r_br['rho_ce']:>+9.3f} {r_br['rho_xi']:>+9.3f} {r_br['class']}")

    # Verdict
    print()
    gs_ok = "I" in r_gs["class"]
    fhn_ok = "II" in r_fhn["class"]
    br_ok = "III" in r_br["class"]

    if gs_ok and fhn_ok and br_ok:
        print("  >>> HYPOTHESIS G: CONFIRMED")
        print("  >>> Three classes of scaling mechanism identified")
        verdict = "CONFIRMED"
    elif (gs_ok or fhn_ok) and br_ok:
        print("  >>> HYPOTHESIS G: PARTIAL")
        verdict = "PARTIAL"
    else:
        print("  >>> HYPOTHESIS G: REJECTED")
        verdict = "REJECTED"

    # Save
    output = {
        "hypothesis": "G_two_mechanisms",
        "verdict": verdict,
        "gs": r_gs, "fhn": r_fhn, "br": r_br,
        "compute_seconds": round(elapsed, 1),
    }
    with open("results/hypothesis_G.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  {elapsed:.0f}s total")
    print(f"  Saved: results/hypothesis_G.json")
    print("=" * 65)
