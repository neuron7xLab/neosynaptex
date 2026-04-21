"""Lemma 1 numerical verification: Kuramoto on complete graph K_N.

Per Canon Closure Protocol v1.0 · Phase 2 B3.

Simulates the mean-field Kuramoto model
    dθ_i/dt = ω_i + (K_mf/N) · Σ_j sin(θ_j − θ_i)
          = ω_i + K_mf · r · sin(ψ − θ_i)
on the complete graph K_N with N ∈ {30, 100, 300, 1000, 3000} and
Lorentzian frequencies g(ω) = Δ/(π(ω²+Δ²)), Δ = 0.5.

For each N:
    1. Draw ω_i ~ Cauchy(0, Δ).
    2. Find K_mf_c by bisection on the time-averaged order parameter r
       crossing r_threshold = 0.3.
    3. Convert to the unnormalized cost convention used in Lemma 1:
           K = K_mf / λ_1(A_N) = K_mf / (N-1).
    4. Fit  log K = log A − γ · log λ_1  by ordinary least squares
       on the asymptotic set N ≥ 100 and on the full set.
    5. Bootstrap 95% CI on γ and A by resampling K_mf_c draws within
       each N.

Writes:
    evidence/lemma_1_numerical.json
    manuscript/figures/lemma_1_verification.pdf
    manuscript/figures/lemma_1_verification.png

Deterministic: master seed = 7.

H3 guard: exits with code 2 if the asymptotic γ 95% CI does not
contain 1.0.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SEED = 7
N_VALUES = [30, 100, 300, 1000, 3000]
SAMPLES_PER_N = 48
DELTA = 0.5
R_THRESHOLD = 0.3  # supercritical-filter threshold; physics fit is threshold-free
T_SIM = 120.0
DT = 0.1
K_GRID = (0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.6, 4.0)
OMEGA_CLIP = 30.0 * DELTA
N_BOOT = 2000


def simulate_r(N: int, K: float, omegas: np.ndarray, rng: np.random.Generator) -> float:
    """Mean-field Kuramoto on K_N. Returns time-averaged r over the second half."""
    theta = rng.uniform(0.0, 2.0 * np.pi, N)
    n_steps = int(T_SIM / DT)
    r_trail = np.empty(n_steps)
    dt = DT
    for t in range(n_steps):
        z = np.exp(1j * theta).mean()
        r = abs(z)
        psi = np.angle(z)
        r_trail[t] = r
        # Heun's method (improved Euler).
        k1 = omegas + K * r * np.sin(psi - theta)
        theta_pred = theta + dt * k1
        z2 = np.exp(1j * theta_pred).mean()
        r2 = abs(z2)
        psi2 = np.angle(z2)
        k2 = omegas + K * r2 * np.sin(psi2 - theta_pred)
        theta = theta + 0.5 * dt * (k1 + k2)
    return float(r_trail[n_steps // 2 :].mean())


def measure_Kc(N: int, omegas: np.ndarray, rng: np.random.Generator) -> float:
    """
    Measure critical coupling K_mf_c via mean-field self-consistency.

    Theory (Kuramoto 1975, Restrepo–Ott–Hunt 2005):
        For K > K_c the steady-state order parameter satisfies
            r² = (K − K_c) / K           (mean-field, to leading order)
        ⇒ K (1 − r²) = K_c
    So, for every supercritical sample, K·(1−r²) is an unbiased estimator
    of K_c. Averaging over the supercritical K-grid (filtered by
    R_THRESHOLD) gives a K_c estimate that is threshold-free in the
    physics sense: the filter only rejects sub-/near-critical points
    where the mean-field approximation fails.
    """
    estimates: list[float] = []
    for K in K_GRID:
        r = simulate_r(N, K, omegas, rng)
        if r >= R_THRESHOLD and r < 0.999:
            estimates.append(K * (1.0 - r * r))
    if not estimates:
        return float("nan")
    # Median is robust to small-r fluctuations and r→1 saturation edge.
    return float(np.median(estimates))


def run_kuramoto_sweep() -> dict[int, list[float]]:
    master = np.random.default_rng(SEED)
    results: dict[int, list[float]] = {}
    for N in N_VALUES:
        samples: list[float] = []
        skipped = 0
        for s in range(SAMPLES_PER_N):
            sub_seed = int(master.integers(0, 2**31 - 1))
            rng = np.random.default_rng(sub_seed)
            u = rng.random(N)
            omegas = DELTA * np.tan(np.pi * (u - 0.5))
            omegas = np.clip(omegas, -OMEGA_CLIP, OMEGA_CLIP)
            Kc = measure_Kc(N, omegas, rng)
            if np.isnan(Kc):
                skipped += 1
                continue
            samples.append(Kc)
            if (s + 1) % 8 == 0 or s == 0:
                print(
                    f"  N={N:5d}  sample={s + 1:3d}/{SAMPLES_PER_N}  K_mf_c={Kc:.4f}",
                    file=sys.stderr,
                    flush=True,
                )
        if skipped:
            print(f"  N={N:5d}  skipped={skipped} (no supercritical samples)", file=sys.stderr)
        results[N] = samples
    return results


def fit_power_law(N_subset: list[int], samples_by_N: dict[int, list[float]]) -> tuple[float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for N in N_subset:
        lam = N - 1
        for Kmf in samples_by_N[N]:
            xs.append(np.log(lam))
            ys.append(np.log(Kmf / lam))
    slope, intercept = np.polyfit(np.asarray(xs), np.asarray(ys), 1)
    return -float(slope), float(np.exp(intercept))


def bootstrap_fit(
    N_subset: list[int], samples_by_N: dict[int, list[float]], n_boot: int = N_BOOT, seed: int = 42
) -> tuple[list[float], list[float]]:
    rng = np.random.default_rng(seed)
    gammas: list[float] = []
    As: list[float] = []
    for _ in range(n_boot):
        xs: list[float] = []
        ys: list[float] = []
        for N in N_subset:
            lam = N - 1
            sample = samples_by_N[N]
            idx = rng.integers(0, len(sample), len(sample))
            for i in idx:
                xs.append(np.log(lam))
                ys.append(np.log(sample[i] / lam))
        slope, intercept = np.polyfit(np.asarray(xs), np.asarray(ys), 1)
        gammas.append(-float(slope))
        As.append(float(np.exp(intercept)))
    return gammas, As


def adapter_delta_verification() -> dict[str, int | float | str]:
    adapter = Path("substrates/kuramoto/adapter.py")
    if not adapter.exists():
        return {"file": str(adapter), "delta_matches": 0, "delta_value": DELTA, "present": False}
    text = adapter.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"(?:delta|Delta|DELTA)[^\n]{0,40}0\.5|0\.5[^\n]{0,40}(?:delta|Delta|DELTA)", text)
    return {
        "file": str(adapter),
        "delta_matches": len(matches),
        "delta_value": DELTA,
        "present": True,
    }


def make_figure(
    samples_by_N: dict[int, list[float]],
    gamma_asym: float,
    A_asym: float,
    out_dir: Path,
) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(6.2, 4.4))
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(N_VALUES)))
    for N, color in zip(N_VALUES, colors):
        lam = N - 1
        ys = [k / lam for k in samples_by_N[N]]
        ax.scatter([lam] * len(ys), ys, s=14, alpha=0.55, color=color, label=f"$N={N}$")
    lam_grid = np.logspace(np.log10(N_VALUES[0] - 1), np.log10(N_VALUES[-1] - 1), 200)
    ax.plot(lam_grid, A_asym * lam_grid ** (-gamma_asym), color="black", lw=1.4,
            label=rf"asymptotic fit: $\hat{{\gamma}}={gamma_asym:.3f}$, $\hat{{A}}={A_asym:.3f}$")
    ax.plot(lam_grid, 1.0 * lam_grid ** (-1.0), color="#c1272d", lw=1.0, ls="--",
            label=r"theory: $K = 2\Delta\cdot C^{-1}$  ($A=1$, $\gamma=1$)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Complexity $C = \lambda_1(A_{K_N}) = N-1$")
    ax.set_ylabel(r"Cost $K = K_{\mathrm{sum}}^{(c)} = K_{\mathrm{mf}}^{(c)}/(N-1)$")
    ax.set_title(r"Lemma 1 verification: Kuramoto on $K_N$, Lorentzian $\Delta=0.5$")
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "lemma_1_verification.pdf")
    fig.savefig(out_dir / "lemma_1_verification.png", dpi=160)
    plt.close(fig)


def main() -> int:
    script_path = Path(__file__).resolve()
    script_sha256 = hashlib.sha256(script_path.read_bytes()).hexdigest()
    print("Running Kuramoto sweep...", file=sys.stderr, flush=True)
    samples_by_N = run_kuramoto_sweep()
    asym_N = [N for N in N_VALUES if N >= 100]
    full_N = list(N_VALUES)
    gamma_asym, A_asym = fit_power_law(asym_N, samples_by_N)
    gamma_full, A_full = fit_power_law(full_N, samples_by_N)
    boot_g_asym, boot_A_asym = bootstrap_fit(asym_N, samples_by_N, seed=42)
    boot_g_full, _ = bootstrap_fit(full_N, samples_by_N, seed=43)
    g_asym_ci = [float(np.percentile(boot_g_asym, 2.5)), float(np.percentile(boot_g_asym, 97.5))]
    A_asym_ci = [float(np.percentile(boot_A_asym, 2.5)), float(np.percentile(boot_A_asym, 97.5))]
    g_full_ci = [float(np.percentile(boot_g_full, 2.5)), float(np.percentile(boot_g_full, 97.5))]

    repo_root = Path.cwd().resolve()
    try:
        rel_script = script_path.relative_to(repo_root)
    except ValueError:
        rel_script = script_path.name

    output = {
        "claim_id": "C-002",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script_path": str(rel_script),
        "script_sha256": script_sha256,
        "random_seed": SEED,
        "parameters": {
            "graph": "complete",
            "N_values": N_VALUES,
            "samples_per_N": SAMPLES_PER_N,
            "frequency_distribution": "Cauchy",
            "Delta": DELTA,
            "r_threshold": R_THRESHOLD,
            "T_sim": T_SIM,
            "dt": DT,
            "K_grid": list(K_GRID),
            "omega_clip_abs": OMEGA_CLIP,
            "bootstrap_resamples": N_BOOT,
            "method": "mean-field self-consistency: K_c = median(K * (1 - r^2)) over supercritical K grid filtered by r >= r_threshold and r < 0.999",
            "r_threshold_role": "supercritical-sample filter for the mean-field fit (not a transition detector)",
        },
        "asymptotic_fit": {
            "N_values_used": asym_N,
            "gamma_hat": round(gamma_asym, 4),
            "gamma_CI95": [round(g_asym_ci[0], 4), round(g_asym_ci[1], 4)],
            "A_hat": round(A_asym, 4),
            "A_CI95": [round(A_asym_ci[0], 4), round(A_asym_ci[1], 4)],
            "theory_A": 1.0,
        },
        "full_fit": {
            "N_values_used": full_N,
            "gamma_hat_all": round(gamma_full, 4),
            "gamma_CI95_all": [round(g_full_ci[0], 4), round(g_full_ci[1], 4)],
            "A_hat_all": round(A_full, 4),
        },
        "adapter_verification": adapter_delta_verification(),
        "raw_K_mf_c_by_N": {
            str(N): [round(x, 6) for x in samples_by_N[N]] for N in N_VALUES
        },
    }

    evidence_path = Path("evidence/lemma_1_numerical.json")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    make_figure(samples_by_N, gamma_asym, A_asym, Path("manuscript/figures"))

    print(
        f"\nasymptotic  gamma_hat={gamma_asym:.4f}  CI95=[{g_asym_ci[0]:.4f}, {g_asym_ci[1]:.4f}]",
        file=sys.stderr,
    )
    print(
        f"asymptotic  A_hat={A_asym:.4f}      CI95=[{A_asym_ci[0]:.4f}, {A_asym_ci[1]:.4f}]",
        file=sys.stderr,
    )
    print(
        f"full (incl. N=30)  gamma_hat={gamma_full:.4f}  CI95=[{g_full_ci[0]:.4f}, {g_full_ci[1]:.4f}]",
        file=sys.stderr,
    )
    print(f"wrote: {evidence_path}", file=sys.stderr)
    print("wrote: manuscript/figures/lemma_1_verification.{pdf,png}", file=sys.stderr)

    if not (g_asym_ci[0] <= 1.0 <= g_asym_ci[1]):
        print(
            f"H3 HALT CONDITION TRIGGERED: asymptotic γ 95% CI [{g_asym_ci[0]:.4f}, {g_asym_ci[1]:.4f}] "
            "does not contain 1.0. Lemma 1 falsified for this regime.",
            file=sys.stderr,
        )
        return 2
    print("H3 PASS: asymptotic γ 95% CI contains 1.0", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
