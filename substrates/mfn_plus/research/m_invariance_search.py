#!/usr/bin/env python3
"""
M-INVARIANCE SEARCH — Finding the right formulation | Vasylenko 2026

The naive M = H/(W₂√I) with reference=ρ_∞ and I=JSD gives CV=45%.
This script searches for the CORRECT formulation by testing:

  1. Different references: ρ_∞, ρ₀, uniform
  2. Different I: JSD, Fisher information, chi-squared
  3. Different combinations: M₁ = H/W₂², M₂ = H·W₂/I, etc.
  4. Power law fits: H ~ W₂^a · I^b → find (a,b) for invariance
  5. Integral invariant: ∫M(t)dt = const?
  6. Scaling: M · f(t) = const?
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec

EPS = 1e-12


def to_dist(field):
    w = np.abs(field).ravel().astype(np.float64) + EPS
    return w / w.sum()


def kl_div(a, b):
    return max(0.0, float(np.sum(a * np.log(a / (b + EPS)))))


def jsd(a, b):
    m = 0.5 * (a + b)
    return float(0.5 * np.sum(a * np.log(a / (m + EPS)))
                 + 0.5 * np.sum(b * np.log(b / (m + EPS))))


def fisher_info(field):
    """Spatial Fisher information: I = Σ (∇ρ)² / ρ."""
    rho = np.abs(field).astype(np.float64) + EPS
    rho = rho / rho.sum()
    # Gradient (periodic)
    dx = np.roll(rho, -1, axis=1) - np.roll(rho, 1, axis=1)
    dy = np.roll(rho, -1, axis=0) - np.roll(rho, 1, axis=0)
    grad_sq = dx**2 + dy**2
    return float(np.sum(grad_sq / rho))


def fisher_info_relative(field, ref):
    """Relative Fisher info: I(ρ‖π) = ∫|∇log(ρ/π)|² ρ dx."""
    rho = np.abs(field).astype(np.float64) + EPS
    rho = rho / rho.sum()
    pi = np.abs(ref).astype(np.float64) + EPS
    pi = pi / pi.sum()
    log_ratio = np.log(rho / pi)
    dx = np.roll(log_ratio, -1, axis=1) - np.roll(log_ratio, 1, axis=1)
    dy = np.roll(log_ratio, -1, axis=0) - np.roll(log_ratio, 1, axis=0)
    grad_sq = dx**2 + dy**2
    return float(np.sum(grad_sq * rho))


def shannon_entropy(field):
    """Shannon entropy H = -Σ p log p."""
    rho = np.abs(field).ravel().astype(np.float64) + EPS
    p = rho / rho.sum()
    return float(-np.sum(p * np.log(p)))


def w2_exact(field1, field2):
    import ot
    N = field1.shape[0]
    x = np.arange(N, dtype=np.float64)
    xx, yy = np.meshgrid(x, x)
    coords = np.stack([xx.ravel(), yy.ravel()], axis=1)
    a = to_dist(field1)
    b = to_dist(field2)
    if N <= 48:
        C = ot.dist(coords, coords)
        return float(np.sqrt(max(ot.emd2(a, b, C), 0)))
    return float(ot.sliced_wasserstein_distance(coords, coords, a, b, 200))


def simulate(seed=42, steps=60, N=32, alpha=0.18):
    spec = SimulationSpec(grid_size=N, steps=steps, seed=seed, alpha=alpha,
                          spike_probability=0.22)
    seq = simulate_history(spec)
    return seq.history


def cv(arr):
    a = np.array(arr)
    m = np.mean(a)
    return float(np.std(a) / (abs(m) + EPS)) if len(a) > 1 else 0.0


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 1: Reference choice
# ═══════════════════════════════════════════════════════════════

def exp1_reference_choice():
    print("=" * 60)
    print("  EXP 1: REFERENCE CHOICE")
    print("=" * 60)

    history = simulate(seed=42, steps=60)
    T = history.shape[0]
    N = history.shape[1]

    rho_0 = history[0]
    rho_inf = history[-1]
    rho_unif = np.ones((N, N), dtype=np.float64) / (N * N)

    refs = {"ρ_∞": rho_inf, "ρ₀": rho_0, "uniform": rho_unif}

    for ref_name, ref in refs.items():
        Ms = []
        print(f"\n  Reference: {ref_name}")
        print(f"  {'t':>4}  {'H':>10}  {'W2':>10}  {'I_jsd':>10}  {'M':>10}")
        for t in range(0, T, 5):
            a = to_dist(history[t])
            b = to_dist(ref)
            H = kl_div(a, b)
            W2 = w2_exact(history[t], ref)
            I = jsd(a, b)
            sqrt_I = np.sqrt(max(I, EPS))
            denom = W2 * sqrt_I
            M = H / (denom + EPS) if denom > 1e-8 else 0.0
            M = min(M, 5.0)  # don't clamp to 1 — let it show true scale
            Ms.append(M)
            print(f"  {t:>4}  {H:>10.6f}  {W2:>10.6f}  {I:>10.6f}  {M:>10.6f}")

        # Skip trivial endpoints
        inner = [m for m in Ms if m > 0.01]
        print(f"  CV = {cv(inner):.4f}  (n={len(inner)})")


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 2: Fisher info variants
# ═══════════════════════════════════════════════════════════════

def exp2_fisher_variants():
    print("\n" + "=" * 60)
    print("  EXP 2: INFORMATION MEASURE")
    print("=" * 60)

    history = simulate(seed=42, steps=60)
    T = history.shape[0]
    ref = history[-1]

    # Try different I measures
    measures = {
        "JSD": lambda t: jsd(to_dist(history[t]), to_dist(ref)),
        "Fisher_abs": lambda t: fisher_info(history[t]),
        "Fisher_rel": lambda t: fisher_info_relative(history[t], ref),
        "Shannon_H": lambda t: shannon_entropy(history[t]),
    }

    for i_name, i_fn in measures.items():
        Ms = []
        for t in range(0, T, 5):
            a = to_dist(history[t])
            b = to_dist(ref)
            H = kl_div(a, b)
            W2 = w2_exact(history[t], ref)
            I_val = i_fn(t)
            sqrt_I = np.sqrt(max(abs(I_val), EPS))
            denom = W2 * sqrt_I
            M = H / (denom + EPS) if denom > 1e-8 else 0.0
            Ms.append(M)

        inner = [m for m in Ms if m > 0.01]
        print(f"  {i_name:15s}: M_mean={np.mean(inner):.4f}  CV={cv(inner):.4f}")


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 3: Combinatorial search for invariant ratio
# ═══════════════════════════════════════════════════════════════

def exp3_ratio_search():
    print("\n" + "=" * 60)
    print("  EXP 3: RATIO SEARCH — H^a · W₂^b · I^c = const?")
    print("=" * 60)

    history = simulate(seed=42, steps=60)
    T = history.shape[0]
    ref = history[-1]

    Hs, W2s, Is_jsd, Is_fish = [], [], [], []
    for t in range(0, T, 2):
        a = to_dist(history[t])
        b = to_dist(ref)
        H = kl_div(a, b)
        W2 = w2_exact(history[t], ref)
        I_j = jsd(a, b)
        I_f = fisher_info(history[t])
        if H > 1e-8 and W2 > 1e-8 and I_j > 1e-10:
            Hs.append(H)
            W2s.append(W2)
            Is_jsd.append(I_j)
            Is_fish.append(I_f)

    Hs = np.array(Hs)
    W2s = np.array(W2s)
    Is_jsd = np.array(Is_jsd)
    Is_fish = np.array(Is_fish)

    logH = np.log(Hs)
    logW = np.log(W2s)
    logJ = np.log(Is_jsd)
    logF = np.log(Is_fish)

    # Fit: log H = a*log W₂ + b*log I + c
    # If H = const · W₂^a · I^b, then log H - a*logW - b*logI = const
    print("\n  Linear fit: log H = a·log W₂ + b·log I + c")

    for i_name, logI in [("JSD", logJ), ("Fisher", logF)]:
        X = np.column_stack([logW, logI, np.ones_like(logW)])
        coef, residuals, _, _ = np.linalg.lstsq(X, logH, rcond=None)
        a, b, c = coef
        predicted = a * logW + b * logI + c
        r2 = 1 - np.sum((logH - predicted)**2) / np.sum((logH - np.mean(logH))**2)

        # The invariant is: H / (W₂^a · I^b) = e^c
        ratio = Hs / (W2s**a * (np.array(Is_jsd if i_name == "JSD" else Is_fish))**b)
        print(f"\n  I={i_name}:")
        print(f"    H ∝ W₂^{a:.3f} · I^{b:.3f}")
        print(f"    R² = {r2:.6f}")
        print(f"    Invariant = H/(W₂^{a:.3f} · I^{b:.3f}) = {np.mean(ratio):.4f} ± {np.std(ratio):.4f}")
        print(f"    CV = {cv(ratio):.4f}")

    # Also try: direct power law H = K · W₂^a (ignoring I)
    print("\n  Direct: log H = a·log W₂ + c")
    sl, ic, r, p, se = stats.linregress(logW, logH)
    ratio_hw = Hs / W2s**sl
    print(f"    H ∝ W₂^{sl:.3f}  (R²={r**2:.6f})")
    print(f"    H/W₂^{sl:.3f} = {np.mean(ratio_hw):.6f}  CV={cv(ratio_hw):.4f}")

    # H = K · I^b (ignoring W₂)
    print("\n  Direct: log H = b·log I_JSD + c")
    sl2, ic2, r2, p2, se2 = stats.linregress(logJ, logH)
    ratio_hi = Hs / Is_jsd**sl2
    print(f"    H ∝ I^{sl2:.3f}  (R²={r2**2:.6f})")
    print(f"    H/I^{sl2:.3f} = {np.mean(ratio_hi):.6f}  CV={cv(ratio_hi):.4f}")

    # Try W₂ = K · I^d
    print("\n  W₂ vs I:")
    sl3, ic3, r3, p3, se3 = stats.linregress(logJ, logW)
    print(f"    W₂ ∝ I^{sl3:.3f}  (R²={r3**2:.6f})")


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 4: Integral invariant
# ═══════════════════════════════════════════════════════════════

def exp4_integral_invariant():
    print("\n" + "=" * 60)
    print("  EXP 4: INTEGRAL INVARIANT — ∫M(t)dt across seeds")
    print("=" * 60)

    integrals = {"M_orig": [], "H_total": [], "W2_total": [], "I_total": []}

    for seed in range(20):
        history = simulate(seed=seed, steps=60)
        ref = history[-1]
        Ms, Hs_sum, W2_sum, I_sum = [], 0.0, 0.0, 0.0

        for t in range(history.shape[0]):
            a = to_dist(history[t])
            b = to_dist(ref)
            H = kl_div(a, b)
            W2 = w2_exact(history[t], ref)
            I_val = jsd(a, b)
            sqrt_I = np.sqrt(max(I_val, EPS))
            denom = W2 * sqrt_I
            M = H / (denom + EPS) if denom > 1e-8 else 0.0
            Ms.append(M)
            Hs_sum += H
            W2_sum += W2
            I_sum += I_val

        integrals["M_orig"].append(np.trapezoid(Ms))
        integrals["H_total"].append(Hs_sum)
        integrals["W2_total"].append(W2_sum)
        integrals["I_total"].append(I_sum)

        if seed % 5 == 0:
            print(f"  seed={seed:>3}: ∫M={integrals['M_orig'][-1]:.4f}  "
                  f"ΣH={Hs_sum:.4f}  ΣW₂={W2_sum:.2f}  ΣI={I_sum:.6f}")

    print(f"\n  ∫M: mean={np.mean(integrals['M_orig']):.4f} "
          f"CV={cv(integrals['M_orig']):.4f}")
    print(f"  ΣH: mean={np.mean(integrals['H_total']):.4f} "
          f"CV={cv(integrals['H_total']):.4f}")
    print(f"  ΣW₂: mean={np.mean(integrals['W2_total']):.2f} "
          f"CV={cv(integrals['W2_total']):.4f}")
    print(f"  ΣI: mean={np.mean(integrals['I_total']):.6f} "
          f"CV={cv(integrals['I_total']):.4f}")

    # Try ratio of integrals
    ratio_int = [h / (w * np.sqrt(i) + EPS)
                 for h, w, i in zip(integrals['H_total'],
                                    integrals['W2_total'],
                                    integrals['I_total'])]
    print(f"\n  ΣH/(ΣW₂·√ΣI) = {np.mean(ratio_int):.6f}  CV={cv(ratio_int):.4f}")


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 5: Decay rates — are exponents related?
# ═══════════════════════════════════════════════════════════════

def exp5_decay_rates():
    print("\n" + "=" * 60)
    print("  EXP 5: DECAY RATE ANALYSIS")
    print("=" * 60)

    all_ratios = []
    for seed in range(10):
        history = simulate(seed=seed, steps=60)
        ref = history[-1]
        T = history.shape[0]

        logH, logW, logI, ts = [], [], [], []
        for t in range(0, T, 2):
            a = to_dist(history[t])
            b = to_dist(ref)
            H = kl_div(a, b)
            W2 = w2_exact(history[t], ref)
            I_val = jsd(a, b)
            if H > 1e-8 and W2 > 1e-8 and I_val > 1e-12:
                logH.append(np.log(H))
                logW.append(np.log(W2))
                logI.append(np.log(I_val))
                ts.append(t)

        if len(ts) < 5:
            continue

        ts = np.array(ts, dtype=float)
        logH = np.array(logH)
        logW = np.array(logW)
        logI = np.array(logI)

        # Fit exponential decay: log(X) = -λ·t + c  →  λ = -slope
        λ_H = -stats.linregress(ts, logH).slope
        λ_W = -stats.linregress(ts, logW).slope
        λ_I = -stats.linregress(ts, logI).slope

        # For M = H/(W₂√I) to be constant:
        # λ_H = λ_W + λ_I/2
        predicted = λ_W + λ_I / 2
        ratio = λ_H / (predicted + EPS) if predicted > 0 else 0

        all_ratios.append(ratio)

        if seed < 5:
            print(f"  seed={seed}: λ_H={λ_H:.4f}  λ_W={λ_W:.4f}  λ_I={λ_I:.4f}")
            print(f"           λ_W+λ_I/2={predicted:.4f}  ratio={ratio:.4f}")

    print(f"\n  λ_H / (λ_W + λ_I/2) across seeds:")
    print(f"    mean = {np.mean(all_ratios):.4f}  CV = {cv(all_ratios):.4f}")
    print(f"    If = 1.0 → M is constant. If ≠ 1.0 → M decays/grows.")


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 6: Rescaled M — M(t) · g(t)
# ═══════════════════════════════════════════════════════════════

def exp6_rescaled_M():
    print("\n" + "=" * 60)
    print("  EXP 6: RESCALED M — Can M(t)·g(t) = const?")
    print("=" * 60)

    history = simulate(seed=42, steps=60)
    ref = history[-1]
    T = history.shape[0]

    Ms, ts = [], []
    for t in range(T):
        a = to_dist(history[t])
        b = to_dist(ref)
        H = kl_div(a, b)
        W2 = w2_exact(history[t], ref)
        I_val = jsd(a, b)
        sqrt_I = np.sqrt(max(I_val, EPS))
        denom = W2 * sqrt_I
        M = H / (denom + EPS) if denom > 1e-8 else 0.0
        if M > 0.01:
            Ms.append(M)
            ts.append(t)

    Ms = np.array(Ms)
    ts = np.array(ts, dtype=float)

    if len(ts) < 5:
        print("  Not enough data points")
        return

    # Fit M(t) = A · (T-t)^β
    # log M = log A + β · log(T-t)
    remaining = np.maximum(T - ts, 1)
    sl, ic, r, p, se = stats.linregress(np.log(remaining), np.log(Ms))
    print(f"  M(t) ∝ (T-t)^{sl:.3f}  (R²={r**2:.4f})")

    # If M(t) = A·(T-t)^β, then M(t)·(T-t)^(-β) = A = const
    rescaled = Ms / remaining**sl
    print(f"  M/(T-t)^{sl:.3f} = {np.mean(rescaled):.6f}  CV={cv(rescaled):.4f}")

    # Try M(t) = A · e^(-λt)
    sl2, ic2, r2, p2, se2 = stats.linregress(ts, np.log(Ms))
    print(f"\n  M(t) ∝ e^({sl2:.4f}·t)  (R²={r2**2:.4f})")
    rescaled2 = Ms * np.exp(-sl2 * ts)
    print(f"  M·e^({-sl2:.4f}·t) = {np.mean(rescaled2):.6f}  CV={cv(rescaled2):.4f}")

    # Verify across seeds
    print(f"\n  Cross-seed verification (power law rescaling):")
    for seed in range(5):
        hist = simulate(seed=seed, steps=60)
        ref_s = hist[-1]
        Ms_s, ts_s = [], []
        for t in range(hist.shape[0]):
            a = to_dist(hist[t])
            b = to_dist(ref_s)
            H = kl_div(a, b)
            W2 = w2_exact(hist[t], ref_s)
            I_val = jsd(a, b)
            sqrt_I = np.sqrt(max(I_val, EPS))
            denom = W2 * sqrt_I
            M = H / (denom + EPS) if denom > 1e-8 else 0.0
            if M > 0.01:
                Ms_s.append(M)
                ts_s.append(t)
        Ms_s = np.array(Ms_s)
        ts_s = np.array(ts_s, dtype=float)
        remaining_s = np.maximum(T - ts_s, 1)
        rescaled_s = Ms_s / remaining_s**sl
        print(f"    seed={seed}: A={np.mean(rescaled_s):.6f}  CV={cv(rescaled_s):.4f}")


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  M-INVARIANCE SEARCH  |  6 Experiments  |  Vasylenko 2026 ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    t0 = time.perf_counter()

    exp1_reference_choice()
    exp2_fisher_variants()
    exp3_ratio_search()
    exp4_integral_invariant()
    exp5_decay_rates()
    exp6_rescaled_M()

    print(f"\n  Total time: {time.perf_counter() - t0:.1f}s")
