#!/usr/bin/env python3
"""
γ-Regime Phase Investigation — Falsification of H1 and H2.

Central question: what determines γ ≈ 1.0 vs γ ≈ 2.0?

H1: γ is determined by spatial geometry (diffusion → 1.0, no space → 2.0)
H2: γ is determined by competition strength (weak → 1.0, WTA → 2.0)

Task A: Sweep competition_strength in DNCA, measure γ
Task B: Create SpatialDNCA with local interactions, measure γ
Task C: Build phase diagram
Task D: Save results for manuscript

Author: Yaroslav Vasylenko / neuron7xLab
Date: 2026-03-30
Seed: 42 everywhere (INV-3)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neuron7x_agents.dnca.orchestrator import DNCA, DNCStepOutput
from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe
from neuron7x_agents.dnca.core.types import ACTIVITY_THRESHOLD


# =============================================================================
# FAST DNCA — disable inner SGD for measurement runs
# =============================================================================

def create_fast_dnca(state_dim: int = 64, seed: int = 42) -> DNCA:
    """
    Create DNCA with inner SGD disabled for fast trajectory collection.

    The γ probe measures competition dynamics (NMO activities, prediction errors).
    The inner SGD loop (20 iterations × 6 operators × backprop) takes ~44s/step.
    For γ measurement we need the competition dynamics, not converged forward models.

    Solution: patch step() to skip the forward model learning (step 8).
    This reduces step time from ~44s to ~0.01s while preserving all
    competition dynamics that determine γ.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    dnca = DNCA(state_dim=state_dim, hidden_dim=128, device="cpu", seed=seed)

    # Save original step
    original_step = dnca.step

    def fast_step(
        sensory_input: torch.Tensor,
        reward: float = 0.0,
        goal: Optional[torch.Tensor] = None,
    ) -> DNCStepOutput:
        """
        DNCA step with forward model learning disabled.
        All competition dynamics (LV, Kuramoto, metastability, regime) preserved.
        """
        from neuron7x_agents.dnca.core.types import RegimeTransitionEvent

        dnca._step_count += 1

        # === 1. Input validation + SPS receives input ===
        if sensory_input.dim() == 0 or sensory_input.shape[-1] == 0:
            raise ValueError(f"sensory_input must be non-empty, got shape {sensory_input.shape}")
        if not torch.isfinite(sensory_input).all():
            raise ValueError("sensory_input contains NaN or Inf")

        dnca.sps.receive_sensory(sensory_input)
        if goal is not None:
            dnca.sps.goal = goal.detach().clone()
        dnca.sps.reward_context = torch.tensor([reward]).expand(dnca.sps.dims["reward_dim"])

        # === 2. Active NMOs run DAC cycles (INV-2) ===
        dominant_idx = dnca.competition.get_dominant_index()
        dominant_name = dnca._op_names[dominant_idx]
        dominant_activity = float(dnca.competition.activities[dominant_idx].item())

        mismatch = 0.0
        satiation = 0.0
        with torch.no_grad():
            for i, (name, op) in enumerate(dnca.operators.items()):
                if dnca.competition.activities[i] > ACTIVITY_THRESHOLD:
                    motivation = 1.0 if name == dominant_name else 0.5
                    dac_out = op.step_dac(
                        sensory_input,
                        goal_hint=dnca.sps.goal if goal is not None else None,
                        motivation=motivation,
                    )
                    if name == dominant_name:
                        mismatch = dac_out.mismatch_normed
                        satiation = dac_out.satiation
                        dnca.sps.sensory_prediction = dac_out.prediction.detach().clone()
                        dnca.sps.prediction_error = (
                            sensory_input.detach() - dac_out.prediction.detach()
                        )

        # === 3. All NMOs compute modulations ===
        snapshot = dnca.sps.snapshot()
        modulations: Dict[str, Dict[str, torch.Tensor]] = {}
        growth_rates = torch.zeros(dnca.n_nmo)
        natural_freqs = torch.zeros(dnca.n_nmo)

        with torch.no_grad():
            for i, (name, op) in enumerate(dnca.operators.items()):
                modulations[name] = op.modulate(snapshot)
                growth_rates[i] = op.compute_growth_rate(snapshot)
                natural_freqs[i] = op.get_natural_frequency()

        if not torch.isfinite(growth_rates).all():
            growth_rates = torch.where(
                torch.isfinite(growth_rates), growth_rates, torch.zeros_like(growth_rates)
            )

        # === 4. Phase-locked write to SPS (INV-1) ===
        for name, fields in modulations.items():
            permitted = dnca._write_permissions.get(name, [])
            for field_name, value in fields.items():
                if field_name in permitted and hasattr(dnca.sps, field_name):
                    setattr(dnca.sps, field_name, value.detach().clone())

        # === 5. Competition field step ===
        activities = dnca.competition.step(growth_rates)
        dnca.sps.nmo_activities = activities.clone()
        for i, name in enumerate(dnca._op_names):
            dnca.operators[name].activity = float(activities[i].item())

        # === 6. Kuramoto coupling step ===
        r = dnca.kuramoto.step(activities, natural_freqs)
        dnca.sps.regime_coherence = torch.tensor([r])

        # === 7. MetastabilityEngine check (INV-5) ===
        dnca.metastability.check()

        # === 8. SKIPPED: Forward model learning ===
        # Not needed for γ measurement — preserves competition dynamics

        # === 9. Regime lifecycle check (INV-7) ===
        dominant_idx = dnca.competition.get_dominant_index()
        dominant_name = dnca._op_names[dominant_idx]
        dominant_activity = float(activities[dominant_idx].item())

        sorted_acts = activities.sort(descending=True)
        challenger_activity = float(sorted_acts.values[1].item()) if dnca.n_nmo > 1 else 0.0

        ne_op = dnca.operators.get("norepinephrine")
        ne_reset = hasattr(ne_op, 'reset_triggered') and ne_op.reset_triggered
        if ne_reset:
            dnca.competition.inject_reset(dominant_idx)

        transition = dnca.regime_mgr.update(
            dominant_nmo=dominant_name,
            dominant_activity=dominant_activity,
            dominant_satiation=satiation,
            dominant_mismatch=mismatch,
            coherence=r,
            ne_reset=ne_reset,
            challenger_activity=challenger_activity,
            goal=dnca.sps.goal,
        )

        # === 10. Phase advance ===
        dnca.sps.update_phase(dt=25.0)

        regime = dnca.regime_mgr.current
        regime_phase = regime.phase.name if regime else "NONE"
        regime_age = regime.age if regime else 0

        return DNCStepOutput(
            dominant_nmo=dominant_name,
            dominant_activity=dominant_activity,
            all_activities={name: float(activities[i].item()) for i, name in enumerate(dnca._op_names)},
            regime_phase=regime_phase,
            regime_age=regime_age,
            r_order=r,
            r_std=dnca.kuramoto.r_std,
            mismatch=mismatch,
            satiation=satiation,
            plasticity_gate=float(dnca.sps.plasticity_gate.item()),
            theta_phase=float(dnca.sps.theta_phase.item()),
            transition_event=transition,
            step=dnca._step_count,
        )

    dnca.step = fast_step
    return dnca


# =============================================================================
# TASK A — Competition Sweep
# =============================================================================

def patch_competition_strength(dnca: DNCA, strength: float) -> None:
    """
    Modulate competition strength in DNCA.

    competition_strength ∈ [0.0, 1.0]:
      0.0 = minimal competition (equal activities, soft normalization)
      1.0 = full winner-take-all (original or sharper)

    Three levers:
    1. Growth rate compression: 0.05 (flat) → 1.0 (full differences)
    2. Off-diagonal ρ scaling: 0.3 (weak inhibition) → 1.5 (strong)
    3. GABA exponent: 1.0 (linear) → 3.0 (sharp WTA)
    """
    lv = dnca.competition

    # --- Lever 1: Growth rate compression ---
    compression_factor = 0.05 + strength * 0.95  # [0.05, 1.0]

    def patched_step(
        self,
        growth_rates: torch.Tensor,
        external_perturbation: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        A = self.activities
        sigma = growth_rates.float()
        sigma_mean = sigma.mean()
        sigma = sigma_mean + (sigma - sigma_mean) * compression_factor

        inhibition = self.rho @ A
        dA = A * (sigma - inhibition) * self.dt
        noise = torch.randn(self.n) * self.noise_scale * self.dt

        dominant_idx = A.argmax()
        fatigue = torch.zeros(self.n)
        fatigue[dominant_idx] = -0.002 * A[dominant_idx]
        A = A + dA + noise + fatigue

        if external_perturbation is not None:
            A = A + external_perturbation

        self.activities = A.clamp(0.0, 1.0)
        return self.activities.clone()

    lv.step = types.MethodType(patched_step, lv)

    # --- Lever 2: ρ_ij off-diagonal scaling ---
    rho_scale = 0.3 + strength * 1.2  # [0.3, 1.5]
    n = lv.n
    GABA_IDX, GLU_IDX = 4, 5
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if j == GABA_IDX:
                base = 0.3
            elif j == GLU_IDX:
                base = 0.2
            elif i == GABA_IDX:
                base = 1.2
            elif i in (0, 1, 2, 3) and j in (0, 1, 2, 3):
                base = 0.9
            else:
                base = 0.8
            lv.rho[i, j] = base * rho_scale

    # --- Lever 3: GABA exponent ---
    gaba_exponent = 1.0 + strength * 2.0  # [1.0, 3.0]
    gaba_op = dnca.operators.get("gaba")
    if gaba_op is not None:
        gaba_op._exponent = gaba_exponent


def run_competition_sweep(
    n_levels: int = 5,
    n_steps: int = 500,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Task A: Sweep competition_strength from 0.0 to 1.0."""
    strengths = np.linspace(0.0, 1.0, n_levels).tolist()
    results = []

    for strength in strengths:
        torch.manual_seed(seed)
        np.random.seed(seed)

        dnca = create_fast_dnca(state_dim=64, seed=seed)
        patch_competition_strength(dnca, strength)

        probe = BNSynGammaProbe(window_size=50, n_bootstrap=300, seed=seed)
        nmo_report, pe_report, ctrl_report = probe.run(dnca, n_steps=n_steps)

        result = {
            "competition": round(strength, 2),
            "gamma_nmo": round(nmo_report.gamma, 4),
            "gamma_pe": round(pe_report.gamma, 4),
            "gamma_ctrl": round(ctrl_report.gamma, 4),
            "r2_nmo": round(nmo_report.r2, 4),
            "r2_pe": round(pe_report.r2, 4),
            "ci_low_nmo": round(nmo_report.ci_low, 4),
            "ci_high_nmo": round(nmo_report.ci_high, 4),
            "ci_low_pe": round(pe_report.ci_low, 4),
            "ci_high_pe": round(pe_report.ci_high, 4),
            "n_pairs_nmo": nmo_report.n_pairs,
            "n_pairs_pe": pe_report.n_pairs,
            "verdict_nmo": nmo_report.verdict,
            "verdict_pe": pe_report.verdict,
        }
        results.append(result)

        trend = "↓" if nmo_report.gamma < 1.5 else "↑"
        print(
            f"  competition={strength:.2f}  "
            f"γ_nmo={nmo_report.gamma:+.3f} [{nmo_report.ci_low:+.3f},{nmo_report.ci_high:+.3f}]  "
            f"γ_pe={pe_report.gamma:+.3f}  "
            f"γ_ctrl={ctrl_report.gamma:+.3f}  "
            f"R²={nmo_report.r2:.3f}  {trend}"
        )

    return results


# =============================================================================
# TASK B — Spatial DNCA
# =============================================================================

class SpatialLotkaVolterraField:
    """
    Lotka-Volterra with spatially local NMO interactions.

    Instead of global ρ_ij, operators influence only neighboring regions
    via 3×3 diffusion kernel. Converts global WTA into local competition.
    """

    def __init__(
        self,
        n_operators: int = 6,
        grid_size: int = 8,
        dt: float = 0.02,
        noise_scale: float = 0.02,
    ):
        self.n = n_operators
        self.grid_size = grid_size
        self.dt = dt
        self.noise_scale = noise_scale

        self.spatial_activities = torch.ones(n_operators, grid_size, grid_size) * 0.1
        self.activities = self.spatial_activities.mean(dim=(1, 2))

        # 3x3 diffusion kernel (normalized)
        self.kernel = torch.tensor([
            [0.05, 0.10, 0.05],
            [0.10, 0.40, 0.10],
            [0.05, 0.10, 0.05],
        ]).unsqueeze(0).unsqueeze(0)

        # Reduced mutual inhibition (local, not global)
        GABA_IDX, GLU_IDX = 4, 5
        self.rho = torch.zeros(n_operators, n_operators)
        for i in range(n_operators):
            for j in range(n_operators):
                if i == j:
                    self.rho[i, j] = 1.0
                elif j == GABA_IDX:
                    self.rho[i, j] = 0.15
                elif j == GLU_IDX:
                    self.rho[i, j] = 0.1
                elif i == GABA_IDX:
                    self.rho[i, j] = 0.6
                else:
                    self.rho[i, j] = 0.4

    def step(self, growth_rates, external_perturbation=None):
        sigma = growth_rates.float()
        sigma_mean = sigma.mean()
        sigma = sigma_mean + (sigma - sigma_mean) * 0.3

        SA = self.spatial_activities
        A_mean = SA.mean(dim=(1, 2))
        inhibition = self.rho @ A_mean

        for i in range(self.n):
            dA = SA[i] * (sigma[i] - inhibition[i]) * self.dt
            sa_padded = torch.nn.functional.pad(
                SA[i].unsqueeze(0).unsqueeze(0), (1, 1, 1, 1), mode='circular'
            )
            diffused = torch.nn.functional.conv2d(sa_padded, self.kernel).squeeze()
            SA[i] = 0.7 * diffused + 0.3 * SA[i] + dA

        SA = SA + torch.randn_like(SA) * self.noise_scale * self.dt
        A_mean = SA.mean(dim=(1, 2))
        dominant_idx = A_mean.argmax()
        SA[dominant_idx] -= 0.002 * SA[dominant_idx]

        if external_perturbation is not None:
            for i in range(self.n):
                SA[i] += external_perturbation[i]

        self.spatial_activities = SA.clamp(0.0, 1.0)
        self.activities = self.spatial_activities.mean(dim=(1, 2))
        return self.activities.clone()

    def get_dominant_index(self):
        return int(self.activities.argmax().item())

    def get_dominant_concentration(self):
        total = self.activities.sum().item()
        if total < 1e-8:
            return 0.0
        return float(self.activities.max().item() / total)

    def inject_reset(self, target_idx=None):
        if target_idx is not None:
            self.spatial_activities[target_idx] *= 0.1
        else:
            self.spatial_activities[self.get_dominant_index()] *= 0.1
        self.spatial_activities += torch.randn_like(self.spatial_activities) * 0.05
        self.activities = self.spatial_activities.mean(dim=(1, 2))

    def reset(self):
        self.spatial_activities = torch.ones(self.n, self.grid_size, self.grid_size) * 0.1
        self.activities = self.spatial_activities.mean(dim=(1, 2))


def run_spatial_experiment(n_steps: int = 500, seed: int = 42) -> Dict[str, Any]:
    """Task B: Run SpatialDNCA and measure γ."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    dnca = create_fast_dnca(state_dim=64, seed=seed)

    # Replace competition with spatial variant
    spatial_lv = SpatialLotkaVolterraField(n_operators=dnca.n_nmo, grid_size=8)
    dnca.competition = spatial_lv

    # Softer GABA (spatial = diffusive selection)
    gaba_op = dnca.operators.get("gaba")
    if gaba_op is not None:
        gaba_op._exponent = 1.5

    probe = BNSynGammaProbe(window_size=50, n_bootstrap=300, seed=seed)
    nmo_report, pe_report, ctrl_report = probe.run(dnca, n_steps=n_steps)

    result = {
        "substrate": "SpatialDNCA",
        "grid_size": 8,
        "spatial": True,
        "competition": 1.0,
        "gamma_nmo": round(nmo_report.gamma, 4),
        "gamma_pe": round(pe_report.gamma, 4),
        "gamma_ctrl": round(ctrl_report.gamma, 4),
        "r2_nmo": round(nmo_report.r2, 4),
        "r2_pe": round(pe_report.r2, 4),
        "ci_low_nmo": round(nmo_report.ci_low, 4),
        "ci_high_nmo": round(nmo_report.ci_high, 4),
        "ci_low_pe": round(pe_report.ci_low, 4),
        "ci_high_pe": round(pe_report.ci_high, 4),
        "n_pairs_nmo": nmo_report.n_pairs,
        "verdict_nmo": nmo_report.verdict,
    }

    print(
        f"  SpatialDNCA (8×8):  "
        f"γ_nmo={nmo_report.gamma:+.3f} [{nmo_report.ci_low:+.3f},{nmo_report.ci_high:+.3f}]  "
        f"γ_pe={pe_report.gamma:+.3f}  "
        f"γ_ctrl={ctrl_report.gamma:+.3f}  "
        f"R²={nmo_report.r2:.3f}"
    )

    return result


# =============================================================================
# TASK C — Phase Diagram
# =============================================================================

def build_phase_diagram(sweep_results, spatial_result, output_path):
    phase_data = {
        "metadata": {
            "author": "Yaroslav Vasylenko / neuron7xLab",
            "date": "2026-03-30",
            "seed": 42,
            "description": "γ as function of competition_strength and spatial_locality",
        },
        "axis_x": "competition_strength",
        "axis_y": "gamma (NMO activity field)",
        "sweep_points": sweep_results,
        "spatial_point": spatial_result,
        "reference_points": [
            {"substrate": "zebrafish", "gamma": 1.043, "spatial": True, "competition": 0.0,
             "source": "McGuirl et al. 2020 PNAS"},
            {"substrate": "MFN+", "gamma": 0.865, "spatial": True, "competition": 0.0,
             "source": "Vasylenko 2026, Gray-Scott R-D"},
            {"substrate": "market", "gamma": 1.081, "spatial": False, "competition": 0.3,
             "source": "mvstack Kuramoto synchronization"},
            {"substrate": "DNCA (original)", "gamma": 2.185, "spatial": False, "competition": 1.0,
             "source": "neuron7x-agents DNCA full validation"},
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(phase_data, f, indent=2, ensure_ascii=False)

    print(f"  Phase diagram saved to: {output_path}")
    return phase_data


# =============================================================================
# GATE CHECKS
# =============================================================================

def check_gates(sweep_results, spatial_result):
    gates = {}
    gamma_at_min = sweep_results[0]["gamma_nmo"]
    gamma_at_max = sweep_results[-1]["gamma_nmo"]
    gammas = [r["gamma_nmo"] for r in sweep_results]
    ctrls = [abs(r["gamma_ctrl"]) for r in sweep_results]

    gates["A-G1: comp=0.0 → γ<1.5"] = gamma_at_min < 1.5
    gates["A-G2: comp=1.0 → γ>1.5"] = gamma_at_max > 1.5

    diffs = [gammas[i + 1] - gammas[i] for i in range(len(gammas) - 1)]
    gates["A-G3: monotonic γ(competition)"] = all(d >= -0.15 for d in diffs)
    gates["A-G4: γ_ctrl < 0.3 at all levels"] = all(c < 0.3 for c in ctrls)
    gates["B-G1: SpatialDNCA γ measured"] = spatial_result["n_pairs_nmo"] >= 20

    return gates


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 65)
    print("  γ-REGIME PHASE INVESTIGATION")
    print("  neuron7xLab / Yaroslav Vasylenko")
    print("  seed=42 | INV-1 through INV-5 enforced")
    print("=" * 65)

    t0 = time.time()

    # === TASK A ===
    print("\n━━━ TASK A: Competition Sweep (H2 Falsification) ━━━")
    sweep_results = run_competition_sweep(n_levels=5, n_steps=500, seed=42)

    # === TASK B ===
    print("\n━━━ TASK B: Spatial DNCA (H1 Test) ━━━")
    spatial_result = run_spatial_experiment(n_steps=500, seed=42)

    # === TASK C ===
    print("\n━━━ TASK C: Phase Diagram ━━━")
    manuscript_dir = PROJECT_ROOT / "manuscript"
    phase_data = build_phase_diagram(
        sweep_results, spatial_result,
        manuscript_dir / "phase_diagram_data.json",
    )

    # === GATE CHECKS ===
    print("\n━━━ GATE CHECKS ━━━")
    gates = check_gates(sweep_results, spatial_result)
    n_passed = sum(gates.values())
    n_total = len(gates)
    for gate_name, passed in gates.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}]  {gate_name}")

    # === VERDICTS ===
    gamma_min = sweep_results[0]["gamma_nmo"]
    gamma_max = sweep_results[-1]["gamma_nmo"]
    gamma_spatial = spatial_result["gamma_nmo"]

    h2_confirmed = gates.get("A-G1: comp=0.0 → γ<1.5", False) and gates.get("A-G2: comp=1.0 → γ>1.5", False)
    h1_spatial_shift = gamma_spatial < gamma_max - 0.3

    gammas_sweep = [r["gamma_nmo"] for r in sweep_results]
    diffs = [gammas_sweep[i + 1] - gammas_sweep[i] for i in range(len(gammas_sweep) - 1)]
    trend = "MONOTONIC" if all(d >= -0.15 for d in diffs) else "NON-MONOTONIC"

    if h2_confirmed and h1_spatial_shift:
        mechanism = "BOTH (competition + spatial geometry)"
    elif h2_confirmed:
        mechanism = "COMPETITION"
    elif h1_spatial_shift:
        mechanism = "SPATIAL GEOMETRY"
    else:
        mechanism = "UNKNOWN — further investigation needed"

    elapsed = time.time() - t0

    # === FINAL REPORT ===
    print("\n" + "=" * 65)
    print("  PHASE INVESTIGATION — FINAL REPORT")
    print("=" * 65)

    print("\n  H2 Test (competition sweep):")
    for r in sweep_results:
        trend_arrow = "<" if r["gamma_nmo"] < 1.5 else ">"
        print(
            f"    competition={r['competition']:.2f} -> "
            f"gamma_nmo={r['gamma_nmo']:+.3f}  "
            f"gamma_ctrl={r['gamma_ctrl']:+.3f}  "
            f"R2={r['r2_nmo']:.3f}  {trend_arrow}"
        )
    print(f"    Trend: {trend}")
    print(f"    H2 verdict: {'CONFIRMED' if h2_confirmed else 'REJECTED'}")

    print(f"\n  H1 Test (Spatial DNCA):")
    print(
        f"    gamma_SpatialDNCA = {gamma_spatial:+.3f}  "
        f"CI=[{spatial_result['ci_low_nmo']:+.3f}, {spatial_result['ci_high_nmo']:+.3f}]"
    )
    print(f"    gamma shift from global DNCA: {gamma_spatial - gamma_max:+.3f}")
    print(f"    H1 verdict: {'CONFIRMED' if h1_spatial_shift else 'REJECTED'}")

    print(f"\n  Phase diagram: saved to manuscript/phase_diagram_data.json")
    print(f"\n  Mechanistic conclusion:")
    print(f"    gamma is determined by: {mechanism}")

    print(f"\n  Gates: {n_passed}/{n_total}")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 65)

    # Save raw results
    raw_output = {
        "sweep": sweep_results,
        "spatial": spatial_result,
        "gates": {k: v for k, v in gates.items()},
        "verdict_h1": "CONFIRMED" if h1_spatial_shift else "REJECTED",
        "verdict_h2": "CONFIRMED" if h2_confirmed else "REJECTED",
        "mechanism": mechanism,
        "trend": trend,
        "elapsed_seconds": round(elapsed, 1),
    }
    raw_path = manuscript_dir / "phase_investigation_raw.json"
    with open(raw_path, "w") as f:
        json.dump(raw_output, f, indent=2, ensure_ascii=False)
    print(f"\n  Raw data: {raw_path}")

    return raw_output


if __name__ == "__main__":
    main()
