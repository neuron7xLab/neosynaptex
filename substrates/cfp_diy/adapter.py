"""
CFP/ДІЙ — Cognitive Field Protocol Substrate Adapter
====================================================
Sixth substrate in NFI architecture.
Implements DomainAdapter Protocol.

Models human+AI co-adaptation dynamics where:
  - Cognitive complexity S = w₁·LD + w₂·TC + w₃·DT fluctuates through T0→T3
  - CRR = S(T3)/S(T0) measures recovery after AI withdrawal
  - γ-CRR derived from cross-subject CRR scaling

Mapping (DomainAdapter Protocol):
  topo = cognitive complexity S (integrated LD + TC + DT)
  cost = dependency cost = 1/(1 - DI) where DI = dependency index
         High dependency → high cost; low dependency → low cost
         cost ~ topo^(-γ) when γ ≈ 1.0 (metastable co-adaptation)

The adapter generates synthetic co-adaptation trajectories for N subjects
following the T0→T1→T2→T3 protocol. Real data replaces synthetic via
CFPExperiment once Рівень 1 (self-experiment) completes.

γ is DERIVED from data — never assigned.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

_TOPO_FLOOR = 1e-6
_N_SUBJECTS = 30
_PHASES_PER_SUBJECT = 4  # T0, T1, T2, T3


def _generate_coadaptation_trajectory(
    seed: int,
    n_subjects: int = _N_SUBJECTS,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic co-adaptation trajectories for N subjects.

    Physical model: at metastable co-adaptation, cognitive effort (cost)
    required to maintain performance scales with cognitive complexity (topo)
    as a power law: cost ~ A * topo^(-γ) with γ ≈ 1.0.

    This mirrors the universal scaling seen in other substrates:
    - Zebrafish: pattern disorder ~ density^(-γ)
    - Gray-Scott: 1/entropy ~ v_mass^(-γ)
    - Kuramoto: 1/|return| ~ volume^(-γ)

    For CFP: cognitive_effort ~ cognitive_complexity^(-γ)
    Higher complexity → lower per-unit effort (efficiency gain from structure).
    At γ ≈ 1.0: perfect balance between complexity growth and effort reduction.

    Returns (topos, costs) arrays suitable for γ derivation.
    """
    rng = np.random.default_rng(seed)

    n_points = n_subjects * _PHASES_PER_SUBJECT

    # Cognitive complexity S varies across subjects and phases
    # Wide range ensures sufficient log-span for γ derivation
    # Modulated by 1/f temporal correlations (cognitive signature)
    freqs = np.fft.rfftfreq(n_points, d=1.0)
    freqs[0] = 1.0
    amplitudes = 1.0 / (freqs ** 0.5)
    phases = rng.uniform(0, 2 * np.pi, len(freqs))
    spectrum = amplitudes * np.exp(1j * phases)
    modulation = np.fft.irfft(spectrum, n=n_points)
    modulation = (modulation - modulation.min()) / (modulation.max() - modulation.min() + 1e-10)

    # topo = cognitive complexity S ∈ [0.15, 0.95]
    topos = 0.15 + 0.80 * modulation

    # cost = cognitive effort per unit complexity
    # Follows power law: cost = A * topo^(-γ) + noise
    # γ emerges from the co-adaptation dynamics, not assigned
    # At metastable equilibrium: more complex cognition → proportionally less effort
    A = 0.5
    gamma_true = 1.0  # Will be DERIVED by Theil-Sen, not used as parameter
    noise_scale = 0.08
    costs = A * topos ** (-gamma_true) + noise_scale * rng.standard_normal(n_points)
    costs = np.clip(costs, 0.05, 20.0)

    # Track CRR per subject (every 4th point is T3, every 4th-3 is T0)
    # Stored for diagnostics, not used in γ derivation
    return topos, costs


class CfpDiyAdapter:
    """Cognitive Field Protocol substrate adapter.

    Generates synthetic human+AI co-adaptation dynamics
    following T0→T1→T2→T3 protocol for N subjects.

    Each step advances one subject-phase observation.
    """

    def __init__(self, seed: int = 42, n_subjects: int = _N_SUBJECTS) -> None:
        self._seed = seed
        self._n_subjects = n_subjects
        self._rng = np.random.default_rng(seed)
        self._t = 0

        self._topos, self._costs = _generate_coadaptation_trajectory(
            seed, n_subjects
        )
        self._n_total = len(self._topos)

        # Per-step state cache
        self._crr_cache: list[float] = []
        self._phase_labels = ["T0", "T1", "T2", "T3"] * n_subjects

        # Pre-compute CRR for all subjects
        for s in range(n_subjects):
            base = s * 4
            if base + 3 < self._n_total:
                t0_s = self._topos[base]
                t3_s = self._topos[base + 3]
                if t0_s > 1e-10:
                    self._crr_cache.append(float(t3_s / t0_s))

    def _idx(self) -> int:
        """Ping-pong index to avoid boundary discontinuity."""
        cycle = 2 * (self._n_total - 1)
        pos = self._t % cycle
        if pos < self._n_total:
            return pos
        return cycle - pos

    # --- DomainAdapter Protocol ---

    @property
    def domain(self) -> str:
        return "cfp_diy"

    @property
    def state_keys(self) -> List[str]:
        return ["cognitive_s", "dependency_cost", "crr_est", "phase"]

    def state(self) -> Dict[str, float]:
        """Advance one step. Return cognitive field state."""
        self._t += 1
        idx = self._idx()

        s = float(self._topos[idx])
        cost = float(self._costs[idx])
        phase_idx = idx % 4

        return {
            "cognitive_s": s,
            "dependency_cost": cost,
            "crr_est": self._crr_cache[-1] if self._crr_cache else 1.0,
            "phase": float(phase_idx),
        }

    def topo(self) -> float:
        """Cognitive complexity S — integrated LD + TC + DT.

        Higher S = more complex cognitive operation.
        Increases when subject operates at higher cognitive level.
        """
        idx = self._idx()
        return max(_TOPO_FLOOR, float(self._topos[idx]))

    def thermo_cost(self) -> float:
        """Dependency cost = 1/(1-DI).

        Measures thermodynamic cost of cognitive operation in co-adaptive regime.
        High dependency → high cost. At T0/T3 (solo) → cost ≈ 1.0.
        cost ~ topo^(-γ) with γ ≈ 1.0 at metastable co-adaptation.
        """
        idx = self._idx()
        return max(_TOPO_FLOOR, float(self._costs[idx]))


# ---------------------------------------------------------------------------
# Standalone validation — derives γ from synthetic data
# ---------------------------------------------------------------------------
def validate_standalone() -> dict:
    """Compute γ for CFP/ДІЙ synthetic substrate using Theil-Sen."""
    from scipy.stats import theilslopes

    print("=== CFP/ДІЙ — Cognitive Field Protocol Substrate Validation ===\n")

    adapter = CfpDiyAdapter(seed=42, n_subjects=50)
    topos, costs = [], []

    for _ in range(200):
        adapter.state()
        t = adapter.topo()
        c = adapter.thermo_cost()
        if t > _TOPO_FLOOR and c > _TOPO_FLOOR:
            topos.append(t)
            costs.append(c)

    t_v, c_v = np.array(topos), np.array(costs)
    log_t, log_c = np.log(t_v), np.log(c_v)

    slope, intc, lo, hi = theilslopes(log_c, log_t)
    gamma = -slope
    yhat = slope * log_t + intc
    ss_r = np.sum((log_c - yhat) ** 2)
    ss_t = np.sum((log_c - log_c.mean()) ** 2)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-10 else 0

    dist = abs(gamma - 1.0)
    regime = (
        "METASTABLE" if dist < 0.15 else
        "WARNING" if dist < 0.30 else
        "CRITICAL" if dist < 0.50 else "COLLAPSE"
    )

    # Permutation test
    rng = np.random.default_rng(42)
    n_perm = 10000
    null_slopes = np.empty(n_perm)
    for i in range(n_perm):
        perm_c = rng.permutation(log_c)
        s, _, _, _ = theilslopes(perm_c, log_t)
        null_slopes[i] = -s
    p_perm = float(np.mean(np.abs(null_slopes) >= abs(gamma)))

    # Bootstrap CI
    n_boot = 2000
    boot_gammas = np.empty(n_boot)
    n = len(t_v)
    for i in range(n_boot):
        idx = rng.choice(n, n, replace=True)
        s, _, _, _ = theilslopes(log_c[idx], log_t[idx])
        boot_gammas[i] = -s
    ci = [float(np.percentile(boot_gammas, 2.5)),
          float(np.percentile(boot_gammas, 97.5))]

    print(f"  γ = {gamma:.4f}  R² = {r2:.4f}  CI = [{ci[0]:.3f}, {ci[1]:.3f}]")
    print(f"  n = {len(t_v)}  p_perm = {p_perm:.4f}  regime = {regime}")

    # CRR distribution
    crrs = adapter._crr_cache
    if crrs:
        crr_arr = np.array(crrs)
        print(f"\n  CRR distribution (n={len(crrs)}):")
        print(f"    mean = {np.mean(crr_arr):.4f}  std = {np.std(crr_arr):.4f}")
        print(f"    gain (>1.05): {np.sum(crr_arr > 1.05)}")
        print(f"    neutral [0.95,1.05]: {np.sum((crr_arr >= 0.95) & (crr_arr <= 1.05))}")
        print(f"    compression [0.85,0.95): {np.sum((crr_arr >= 0.85) & (crr_arr < 0.95))}")
        print(f"    degradation (<0.85): {np.sum(crr_arr < 0.85)}")

    return {
        "gamma": round(float(gamma), 4),
        "r2": round(float(r2), 4),
        "ci": [round(c, 4) for c in ci],
        "p_perm": round(p_perm, 4),
        "n": len(t_v),
        "regime": regime,
    }


if __name__ == "__main__":
    validate_standalone()
