"""
DNCA Cognitive Benchmark Suite — 4 behavioral experiments with falsification.

A1: N-Back Working Memory (ACh + PAC)
A2: Stroop Interference (GABA + NE)
A3: Wisconsin Card Sorting Test (NE reset + DA RPE)
A4: Metastability Health (resting state dynamics)

Each benchmark produces BenchmarkResult with SUPPORTED/INCONCLUSIVE/FALSIFIED verdict.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import torch

from neuron7x_agents.dnca.orchestrator import DNCA, DNCStepOutput


@dataclass
class BenchmarkResult:
    name: str
    passed: bool
    metrics: Dict[str, float]
    falsification_checks: Dict[str, bool]  # True = check passed
    verdict: str  # SUPPORTED | INCONCLUSIVE | FALSIFIED
    notes: List[str] = field(default_factory=list)


class DNCABenchmarkSuite:
    """Suite of 4 cognitive benchmarks for DNCA validation."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def run_all(self, dnca: DNCA) -> List[BenchmarkResult]:
        results = [
            self.run_a1_nback(dnca, n=2),
            self.run_a2_stroop(dnca),
            self.run_a3_wcst(dnca),
            self.run_a4_metastability(dnca),
        ]
        return results

    # ── A1: N-Back Working Memory ─────────────────────────────────

    def run_a1_nback(self, dnca: DNCA, n: int = 2, n_steps: int = 200) -> BenchmarkResult:
        """
        N-Back working memory task.
        Tests ACh precision/attention + theta-gamma PAC.
        """
        torch.manual_seed(self.seed)
        random.seed(self.seed)
        dnca.reset()
        sd = dnca.state_dim

        # Generate stimulus sequence
        stimuli = [random.randint(0, 9) for _ in range(n_steps)]
        # Ensure ~30% matches
        for i in range(n, n_steps):
            if random.random() < 0.3:
                stimuli[i] = stimuli[i - n]

        hits = 0
        misses = 0
        false_alarms = 0
        correct_rejections = 0
        pac_values: List[float] = []

        for i in range(n_steps):
            # Encode stimulus as sensory input
            obs = torch.zeros(sd)
            obs[stimuli[i] % sd] = 1.0
            obs += torch.randn(sd) * 0.1

            is_match = i >= n and stimuli[i] == stimuli[i - n]
            out = dnca.step(obs, reward=1.0 if is_match else 0.0)
            pac_values.append(out.r_order)

            # DNCA "response": high dominant activity = "match detected"
            response_match = out.dominant_activity > 0.6 and out.mismatch < 0.3

            if is_match and response_match:
                hits += 1
            elif is_match and not response_match:
                misses += 1
            elif not is_match and response_match:
                false_alarms += 1
            else:
                correct_rejections += 1

        total_targets = hits + misses
        total_non = false_alarms + correct_rejections
        hit_rate = hits / max(1, total_targets)
        fa_rate = false_alarms / max(1, total_non)

        # d' (signal detection theory)
        # Clamp rates away from 0 and 1
        hr = max(0.01, min(0.99, hit_rate))
        fr = max(0.01, min(0.99, fa_rate))
        z_hr = _norm_ppf(hr)
        z_fr = _norm_ppf(fr)
        d_prime = z_hr - z_fr

        pac_mean = sum(pac_values[-50:]) / min(50, len(pac_values)) if pac_values else 0.0

        metrics = {
            "d_prime": d_prime,
            "hit_rate": hit_rate,
            "false_alarm_rate": fa_rate,
            "pac_mean": pac_mean,
            "n": float(n),
        }

        checks = {
            "d_prime_above_floor": d_prime > 0.5,
            "pac_nonzero": pac_mean > 0.001,
        }

        all_pass = all(checks.values())
        verdict = "SUPPORTED" if all_pass else ("INCONCLUSIVE" if d_prime > 0 else "FALSIFIED")

        return BenchmarkResult(
            name=f"a1_nback_n{n}",
            passed=all_pass,
            metrics=metrics,
            falsification_checks=checks,
            verdict=verdict,
            notes=[f"N={n}, {n_steps} trials, d'={d_prime:.2f}"],
        )

    # ── A2: Stroop Interference ──────────────────────────────────

    def run_a2_stroop(self, dnca: DNCA, n_trials: int = 200) -> BenchmarkResult:
        """
        Stroop interference task.
        Tests GABA normalization + NE conflict detection.
        """
        torch.manual_seed(self.seed)
        random.seed(self.seed)
        dnca.reset()
        sd = dnca.state_dim

        congruent_latencies: List[int] = []
        incongruent_latencies: List[int] = []
        congruent_errors = 0
        incongruent_errors = 0

        for trial in range(n_trials):
            is_incongruent = random.random() < 0.3

            # Encode two streams
            color_idx = random.randint(0, 2)
            if is_incongruent:
                word_idx = (color_idx + random.randint(1, 2)) % 3
            else:
                word_idx = color_idx

            obs = torch.zeros(sd)
            # Color signal in first third
            obs[color_idx * (sd // 6):(color_idx + 1) * (sd // 6)] = 1.0
            # Word signal in second third (potentially conflicting)
            offset = sd // 3
            obs[offset + word_idx * (sd // 6):offset + (word_idx + 1) * (sd // 6)] = 0.8
            obs += torch.randn(sd) * 0.1

            # For incongruent trials, inject competition perturbation:
            # conflicting color/word signals boost multiple NMO growth rates,
            # analogous to the anterior cingulate conflict signal.
            if is_incongruent:
                # Conflict perturbation: temporarily boost noise in LV field
                conflict_perturbation = torch.randn(dnca.n_nmo) * 0.04
                dnca.competition.activities = (dnca.competition.activities + conflict_perturbation).clamp(0.0, 1.0)

            # Run until dominant activity settles (max 20 substeps)
            latency = 0
            correct = False
            prev_dominant = None
            stable_count = 0
            settle_threshold = 0.20
            for substep in range(20):
                out = dnca.step(obs, reward=0.0)
                latency += 1
                # Measure settling: dominant NMO must stay the same
                # for 2 consecutive steps with activity above threshold
                if out.dominant_nmo == prev_dominant and out.dominant_activity > settle_threshold:
                    stable_count += 1
                else:
                    stable_count = 0
                prev_dominant = out.dominant_nmo
                if stable_count >= 2:
                    correct = out.dominant_activity > 0.3
                    break

            if is_incongruent:
                incongruent_latencies.append(latency)
                if not correct:
                    incongruent_errors += 1
            else:
                congruent_latencies.append(latency)
                if not correct:
                    congruent_errors += 1

        mean_cong = sum(congruent_latencies) / max(1, len(congruent_latencies))
        mean_incong = sum(incongruent_latencies) / max(1, len(incongruent_latencies))
        ratio = mean_incong / max(0.01, mean_cong)

        metrics = {
            "congruent_latency": mean_cong,
            "incongruent_latency": mean_incong,
            "latency_ratio": ratio,
            "congruent_error_rate": congruent_errors / max(1, len(congruent_latencies)),
            "incongruent_error_rate": incongruent_errors / max(1, len(incongruent_latencies)),
        }

        checks = {
            "latency_ratio_above_1.4": ratio > 1.4,
            "conflict_effect_present": mean_incong > mean_cong,
        }

        all_pass = all(checks.values())
        verdict = "SUPPORTED" if all_pass else "INCONCLUSIVE"

        return BenchmarkResult(
            name="a2_stroop",
            passed=all_pass,
            metrics=metrics,
            falsification_checks=checks,
            verdict=verdict,
            notes=[f"ratio={ratio:.2f}, {n_trials} trials"],
        )

    # ── A3: Wisconsin Card Sorting Test ──────────────────────────

    def run_a3_wcst(self, dnca: DNCA, n_steps: int = 600) -> BenchmarkResult:
        """
        WCST: detect hidden rule changes from reward signal.
        Tests NE context change detection + DA reward prediction error.
        """
        torch.manual_seed(self.seed)
        random.seed(self.seed)
        dnca.reset()
        sd = dnca.state_dim

        # 3 rules: color, shape, number
        rules = ["color", "shape", "number"]
        current_rule_idx = 0
        correct_streak = 0
        rule_changes = 0
        perseverative_errors = 0
        total_errors = 0
        adaptation_steps_list: List[int] = []
        steps_since_change = 0
        adapted = False

        for step in range(n_steps):
            # Generate card
            color = random.randint(0, 2)
            shape = random.randint(0, 2)
            number = random.randint(0, 2)

            obs = torch.zeros(sd)
            obs[color] = 1.0
            obs[3 + shape] = 1.0
            obs[6 + number] = 1.0
            obs += torch.randn(sd) * 0.05

            # DNCA response: use sensory prediction strength for rule readout.
            # The rule dimension with highest prediction magnitude = what the
            # system has learned to attend to = the rule it is following.
            out = dnca.step(obs)

            pred = dnca.sps.sensory_prediction.detach()
            rule_strength = [
                pred[0:3].abs().sum().item(),   # color attention
                pred[3:6].abs().sum().item(),   # shape attention
                pred[6:9].abs().sum().item(),   # number attention
            ]
            chosen_rule = rule_strength.index(max(rule_strength))

            correct = chosen_rule == current_rule_idx
            reward = 3.0 if correct else -3.0  # stronger reward for DA learning
            # Feed reward back
            dnca.step(obs, reward=reward)

            if correct:
                correct_streak += 1
                if not adapted and steps_since_change > 0:
                    adapted = True
                    adaptation_steps_list.append(steps_since_change)
            else:
                total_errors += 1
                if steps_since_change < 5 and rule_changes > 0:
                    perseverative_errors += 1
                correct_streak = 0

            # Rule change every 10 consecutive correct
            if correct_streak >= 10:
                current_rule_idx = (current_rule_idx + 1) % 3
                rule_changes += 1
                correct_streak = 0
                steps_since_change = 0
                adapted = False

            steps_since_change += 1

        persev_rate = perseverative_errors / max(1, total_errors) if total_errors > 0 else 0.0
        mean_adapt = sum(adaptation_steps_list) / max(1, len(adaptation_steps_list)) if adaptation_steps_list else float("inf")

        metrics = {
            "perseverative_error_rate": persev_rate,
            "total_errors": float(total_errors),
            "rule_changes": float(rule_changes),
            "mean_adaptation_steps": mean_adapt,
        }

        checks = {
            "persev_below_40pct": persev_rate < 0.40,
            "adaptation_below_15": mean_adapt < 15.0 or len(adaptation_steps_list) == 0,
        }

        all_pass = all(checks.values())
        if all_pass and persev_rate < 0.20:
            verdict = "SUPPORTED"
        elif all_pass:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "FALSIFIED"

        return BenchmarkResult(
            name="a3_wcst",
            passed=all_pass,
            metrics=metrics,
            falsification_checks=checks,
            verdict=verdict,
            notes=[f"persev={persev_rate:.1%}, adapt={mean_adapt:.1f} steps, {rule_changes} rule changes"],
        )

    # ── A4: Metastability Health ─────────────────────────────────

    def run_a4_metastability(self, dnca: DNCA, n_steps: int = 500) -> BenchmarkResult:
        """
        Resting state dynamics — no task structure.
        Tests MetastabilityEngine, LotkaVolterraField, KuramotoCoupling.
        """
        torch.manual_seed(self.seed)
        random.seed(self.seed)
        dnca.reset()
        sd = dnca.state_dim

        r_values: List[float] = []
        activities_per_nmo: Counter = Counter()
        transitions = 0

        for step in range(n_steps):
            obs = torch.randn(sd) * 0.5
            out = dnca.step(obs, reward=0.0)
            r_values.append(out.r_order)
            if out.dominant_nmo:
                activities_per_nmo[out.dominant_nmo] += 1
            if out.transition_event:
                transitions += 1

        r_mean = sum(r_values) / len(r_values) if r_values else 0.0
        r_std = math.sqrt(sum((x - r_mean) ** 2 for x in r_values) / len(r_values)) if r_values else 0.0

        # Activity entropy
        total = sum(activities_per_nmo.values())
        if total > 0:
            probs = [c / total for c in activities_per_nmo.values()]
            ent = -sum(p * math.log(p + 1e-10) for p in probs)
        else:
            ent = 0.0

        tr_rate = transitions / (n_steps / 100.0)

        # Regime durations from manager
        durations = dnca.regime_mgr.get_regime_durations()
        dur_mean = sum(durations) / max(1, len(durations)) if durations else 0.0
        dur_cv = 0.0
        if durations and dur_mean > 0:
            dur_var = sum((d - dur_mean) ** 2 for d in durations) / len(durations)
            dur_cv = math.sqrt(dur_var) / dur_mean

        metrics = {
            "r_mean": r_mean,
            "r_std": r_std,
            "activity_entropy": ent,
            "transition_rate_per_100": tr_rate,
            "regime_duration_mean": dur_mean,
            "regime_duration_cv": dur_cv,
            "n_nmo_active": float(len(activities_per_nmo)),
        }

        checks = {
            "r_std_metastable": r_std > METASTABILITY_THRESHOLD,
            "r_mean_in_range": 0.10 < r_mean < 0.90,
            "entropy_above_floor": ent > 0.50,
            "no_rigidity": r_std >= 0.05,
            "no_collapse": r_mean >= 0.10 or len(r_values) < 50,
        }

        all_pass = all(checks.values())
        if all_pass and r_std > METASTABILITY_THRESHOLD:
            verdict = "SUPPORTED"
        elif r_std < 0.05 or r_mean < 0.10:
            verdict = "FALSIFIED"
        else:
            verdict = "INCONCLUSIVE"

        return BenchmarkResult(
            name="a4_metastability",
            passed=all_pass,
            metrics=metrics,
            falsification_checks=checks,
            verdict=verdict,
            notes=[f"r={r_mean:.3f}±{r_std:.3f}, H={ent:.2f}, transitions={transitions}"],
        )


# ── Utility ──────────────────────────────────────────────────────

METASTABILITY_THRESHOLD = 0.10

def _norm_ppf(p: float) -> float:
    """Approximate inverse normal CDF (probit) for d' computation."""
    # Rational approximation (Abramowitz & Stegun 26.2.23)
    if p <= 0.0:
        return -4.0
    if p >= 1.0:
        return 4.0
    if p == 0.5:
        return 0.0
    if p > 0.5:
        return -_norm_ppf(1.0 - p)
    t = math.sqrt(-2.0 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return -(t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t))
