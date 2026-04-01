"""
γ-Dynamics Analysis — how γ evolves with learning, transitions, and noise.

Three analyses:
  A1: γ(t) timeline — does γ grow with training?
  A2: γ_stable vs γ_transition — does coherence drop during transitions?
  A3: γ(noise) — does γ peak at intermediate noise (metastability)?
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe, GammaReport


@dataclass
class GammaTimelinePoint:
    t_start: int
    gamma: float
    r2: float
    ci_low: float
    ci_high: float


@dataclass
class GammaDynamicsReport:
    timeline: List[GammaTimelinePoint]
    gamma_stable: Optional[GammaReport]
    gamma_transition: Optional[GammaReport]
    noise_curve: List[Tuple[float, GammaReport]]

    def timeline_summary(self, n: int = 10) -> str:
        lines = ["γ-Timeline (γ vs training time)"]
        lines.append(f"  {'t_start':>7s}  {'γ':>7s}  {'R²':>5s}  {'CI_low':>7s}  {'CI_high':>7s}")
        for pt in self.timeline[:n]:
            lines.append(f"  {pt.t_start:7d}  {pt.gamma:+7.3f}  {pt.r2:5.3f}  {pt.ci_low:+7.3f}  {pt.ci_high:+7.3f}")
        if len(self.timeline) > n:
            lines.append(f"  ... ({len(self.timeline)} total windows)")
            last = self.timeline[-1]
            lines.append(f"  {last.t_start:7d}  {last.gamma:+7.3f}  {last.r2:5.3f}  {last.ci_low:+7.3f}  {last.ci_high:+7.3f}")

        # Trend
        if len(self.timeline) > 5:
            first5 = np.mean([p.gamma for p in self.timeline[:5]])
            last5 = np.mean([p.gamma for p in self.timeline[-5:]])
            trend = "GROWING" if last5 > first5 + 0.1 else ("STABLE" if abs(last5 - first5) < 0.2 else "DECLINING")
            lines.append(f"  Trend: first5_mean={first5:+.3f} last5_mean={last5:+.3f} → {trend}")
        return "\n".join(lines)

    def transition_summary(self) -> str:
        lines = ["γ-Transition Analysis"]
        if self.gamma_stable and self.gamma_transition:
            lines.append(f"  γ_stable     = {self.gamma_stable.gamma:+.3f} (R²={self.gamma_stable.r2:.3f}, n={self.gamma_stable.n_pairs})")
            lines.append(f"  γ_transition = {self.gamma_transition.gamma:+.3f} (R²={self.gamma_transition.r2:.3f}, n={self.gamma_transition.n_pairs})")
            diff = self.gamma_stable.gamma - self.gamma_transition.gamma
            lines.append(f"  Δγ = {diff:+.3f} {'(stable > transition ✓)' if diff > 0 else '(unexpected)'}")
        else:
            lines.append("  Insufficient transition data")
        return "\n".join(lines)

    def noise_summary(self) -> str:
        lines = ["γ vs Noise Level"]
        lines.append(f"  {'noise':>7s}  {'γ':>7s}  {'R²':>5s}  {'n':>5s}  verdict")
        peak_gamma = -999.0
        peak_noise = 0.0
        for noise, report in self.noise_curve:
            lines.append(f"  {noise:7.3f}  {report.gamma:+7.3f}  {report.r2:5.3f}  {report.n_pairs:5d}  {report.verdict}")
            if report.gamma > peak_gamma:
                peak_gamma = report.gamma
                peak_noise = noise
        if self.noise_curve:
            lines.append(f"  Peak: γ={peak_gamma:+.3f} at noise={peak_noise:.3f}")
            # Check inverted-U
            gammas = [r.gamma for _, r in self.noise_curve]
            if len(gammas) >= 3:
                mid = len(gammas) // 2
                is_inverted_u = gammas[mid] > gammas[0] and gammas[mid] > gammas[-1]
                lines.append(f"  Inverted-U pattern: {'YES ✓' if is_inverted_u else 'NO'}")
        return "\n".join(lines)

    def full_summary(self) -> str:
        return "\n\n".join([
            "=" * 60,
            "γ-DYNAMICS REPORT — DNCA v1.4",
            "=" * 60,
            self.timeline_summary(),
            self.transition_summary(),
            self.noise_summary(),
            "=" * 60,
        ])


def analyze_gamma_dynamics(
    dnca: Any,
    probe: Optional[BNSynGammaProbe] = None,
    n_steps: int = 2000,
    window_size: int = 200,
    step_size: int = 50,
    noise_levels: Optional[List[float]] = None,
) -> GammaDynamicsReport:
    """
    Full γ-dynamics analysis.

    A1: γ(t) timeline over training
    A2: γ_stable vs γ_transition
    A3: γ vs noise level
    """
    if probe is None:
        probe = BNSynGammaProbe(window_size=50, n_bootstrap=200)
    if noise_levels is None:
        noise_levels = [0.0, 0.05, 0.1, 0.2, 0.5]

    # === A1: γ timeline ===
    trajectory = probe.collect_trajectory(dnca, n_steps=n_steps, noise_level=0.1)

    timeline: List[GammaTimelinePoint] = []
    for t_start in range(0, len(trajectory) - window_size, step_size):
        window = trajectory[t_start:t_start + window_size]
        images = probe.trajectory_to_images_nmo(window)
        if images.shape[0] < 10:
            continue
        pe0, beta0 = probe.compute_tda_series(images)
        report = probe.compute_gamma(pe0, beta0, approach=f"t={t_start}")
        timeline.append(GammaTimelinePoint(
            t_start=t_start, gamma=report.gamma,
            r2=report.r2, ci_low=report.ci_low, ci_high=report.ci_high,
        ))

    # === A2: γ_stable vs γ_transition ===
    # Find transition steps
    transition_steps = set()
    for t in trajectory:
        step = t["step"]
        # Detect dominant changes
        if step > 0:
            prev = trajectory[step - 1] if step < len(trajectory) else None
            if prev and t["dominant_nmo"] != prev["dominant_nmo"]:
                for s in range(max(0, step - 10), min(len(trajectory), step + 10)):
                    transition_steps.add(s)

    stable_indices = [i for i in range(len(trajectory)) if i not in transition_steps and i > 20]
    trans_indices = sorted(transition_steps)

    gamma_stable = None
    gamma_transition = None

    if len(stable_indices) > 100:
        stable_traj = [trajectory[i] for i in stable_indices[:500]]
        images_s = probe.trajectory_to_images_nmo(stable_traj)
        if images_s.shape[0] > 10:
            pe0_s, b0_s = probe.compute_tda_series(images_s)
            gamma_stable = probe.compute_gamma(pe0_s, b0_s, "stable_regimes")

    if len(trans_indices) > 50:
        trans_traj = [trajectory[i] for i in trans_indices[:300]]
        images_t = probe.trajectory_to_images_nmo(trans_traj)
        if images_t.shape[0] > 10:
            pe0_t, b0_t = probe.compute_tda_series(images_t)
            gamma_transition = probe.compute_gamma(pe0_t, b0_t, "transition_regimes")

    # === A3: γ vs noise level ===
    noise_curve: List[Tuple[float, GammaReport]] = []
    for noise in noise_levels:
        dnca.reset()
        traj_noise = probe.collect_trajectory(dnca, n_steps=1000, noise_level=noise)
        images_n = probe.trajectory_to_images_nmo(traj_noise)
        if images_n.shape[0] > 10:
            pe0_n, b0_n = probe.compute_tda_series(images_n)
            report_n = probe.compute_gamma(pe0_n, b0_n, f"noise={noise:.2f}")
            noise_curve.append((noise, report_n))

    return GammaDynamicsReport(
        timeline=timeline,
        gamma_stable=gamma_stable,
        gamma_transition=gamma_transition,
        noise_curve=noise_curve,
    )
