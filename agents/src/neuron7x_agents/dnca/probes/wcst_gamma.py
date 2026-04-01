"""
WCST γ-Probe — measures γ-scaling during Wisconsin Card Sorting Task.

First measurement of γ under real cognitive load.
At each rule change: compare γ_pre_change vs γ_post_adaptation.

Hypothesis: γ_post > γ_pre (successful adaptation increases coherence).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe, GammaReport


@dataclass
class WCSTGammaReport:
    pre_change_gammas: List[float]
    post_change_gammas: List[float]
    pre_change_reports: List[GammaReport]
    post_change_reports: List[GammaReport]
    n_rule_changes: int
    total_steps: int

    def summary(self) -> str:
        lines = [
            "=" * 55,
            "WCST γ-Probe Report",
            "=" * 55,
        ]
        if self.pre_change_gammas and self.post_change_gammas:
            pre_mean = np.mean(self.pre_change_gammas)
            pre_std = np.std(self.pre_change_gammas)
            post_mean = np.mean(self.post_change_gammas)
            post_std = np.std(self.post_change_gammas)
            lines.append(f"  Rule changes:    {self.n_rule_changes}")
            lines.append(f"  γ_pre_change:    {pre_mean:+.3f} ± {pre_std:.3f}")
            lines.append(f"  γ_post_adapt:    {post_mean:+.3f} ± {post_std:.3f}")
            diff = post_mean - pre_mean
            lines.append(f"  Δγ (post-pre):   {diff:+.3f}")
            lines.append(f"  Hypothesis (γ_post > γ_pre): {'SUPPORTED ✓' if diff > 0 else 'NOT SUPPORTED'}")
            lines.append("")
            lines.append("  Per rule-change:")
            for i in range(min(len(self.pre_change_gammas), len(self.post_change_gammas))):
                lines.append(f"    change {i+1}: pre={self.pre_change_gammas[i]:+.3f} → post={self.post_change_gammas[i]:+.3f}")
        else:
            lines.append("  Insufficient rule changes for analysis")
        lines.append("=" * 55)
        return "\n".join(lines)


class WCSTGammaProbe:
    """Measures γ-scaling during Wisconsin Card Sorting Task."""

    def __init__(self, probe: Optional[BNSynGammaProbe] = None):
        self.probe = probe or BNSynGammaProbe(window_size=30, n_bootstrap=200)

    def run(self, dnca: Any, n_steps: int = 600) -> WCSTGammaReport:
        """Run WCST with γ measurement at each rule change."""
        dnca.reset()
        sd = dnca.state_dim

        rules = ["color", "shape", "number"]
        current_rule_idx = 0
        correct_streak = 0
        rule_changes = 0

        trajectory: List[Dict] = []
        rule_change_steps: List[int] = []

        for step in range(n_steps):
            color = random.randint(0, 2)
            shape = random.randint(0, 2)
            number = random.randint(0, 2)

            obs = torch.zeros(sd)
            obs[color] = 1.0
            obs[3 + shape] = 1.0
            obs[6 + number] = 1.0
            obs += torch.randn(sd) * 0.05

            out = dnca.step(obs)

            # Determine correctness
            nmo_names = sorted(out.all_activities.keys())
            rule_scores = [0.0, 0.0, 0.0]
            for i, name in enumerate(nmo_names):
                rule_scores[i % 3] += out.all_activities[name]
            chosen = rule_scores.index(max(rule_scores))
            correct = chosen == current_rule_idx
            reward = 1.0 if correct else -1.0
            dnca.step(obs, reward=reward)

            trajectory.append({
                "step": step,
                "nmo_activities": np.array([out.all_activities[k] for k in sorted(out.all_activities.keys())]),
                "dominant_nmo": out.dominant_nmo,
                "mismatch": out.mismatch,
                "prediction_error": dnca.sps.prediction_error.detach().cpu().numpy().copy(),
            })

            if correct:
                correct_streak += 1
            else:
                correct_streak = 0

            if correct_streak >= 15:
                current_rule_idx = (current_rule_idx + 1) % 3
                rule_changes += 1
                rule_change_steps.append(step)
                correct_streak = 0

        # Compute γ around each rule change
        pre_reports: List[GammaReport] = []
        post_reports: List[GammaReport] = []
        pre_gammas: List[float] = []
        post_gammas: List[float] = []

        window = 100

        for change_step in rule_change_steps:
            # Pre-change: 100 steps before
            pre_start = max(0, change_step - window)
            pre_end = change_step
            if pre_end - pre_start < 50:
                continue

            pre_traj = trajectory[pre_start:pre_end]
            pre_images = self.probe.trajectory_to_images_nmo(pre_traj)
            if pre_images.shape[0] > 5:
                pe0, b0 = self.probe.compute_tda_series(pre_images)
                pre_r = self.probe.compute_gamma(pe0, b0, "pre_change")
                pre_reports.append(pre_r)
                pre_gammas.append(pre_r.gamma)

            # Post-change: 100 steps after
            post_start = change_step
            post_end = min(len(trajectory), change_step + window)
            if post_end - post_start < 50:
                continue

            post_traj = trajectory[post_start:post_end]
            post_images = self.probe.trajectory_to_images_nmo(post_traj)
            if post_images.shape[0] > 5:
                pe0, b0 = self.probe.compute_tda_series(post_images)
                post_r = self.probe.compute_gamma(pe0, b0, "post_change")
                post_reports.append(post_r)
                post_gammas.append(post_r.gamma)

        return WCSTGammaReport(
            pre_change_gammas=pre_gammas,
            post_change_gammas=post_gammas,
            pre_change_reports=pre_reports,
            post_change_reports=post_reports,
            n_rule_changes=rule_changes,
            total_steps=n_steps,
        )
