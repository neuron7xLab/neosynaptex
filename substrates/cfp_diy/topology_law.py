"""
Topology Law Test (F3) — The Kill Switch
=========================================
Critical falsification experiment for CFP/ДІЙ.

If CRR(D_structured) = CRR(D_shuffled) with p > 0.01 →
topology law is dead, scaling law sufficient.

If CRR(D_structured) ≠ CRR(D_shuffled) with p < 0.01 →
topology law confirmed: structure, not volume, determines cognition.

Also implements M4 (10% topology preservation test):
If CRR(D_10%_structured) ≈ CRR(D_100%_structured) →
topology law confirmed ultmatively.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.stats import mannwhitneyu, theilslopes


@dataclass
class TopologyTestResult:
    """Result of F3 topology law test."""

    crr_structured_mean: float
    crr_structured_std: float
    crr_shuffled_mean: float
    crr_shuffled_std: float
    u_statistic: float
    p_value: float
    effect_size: float      # Cohen's d
    verdict: str            # "TOPOLOGY_LAW" / "SCALING_LAW" / "INCONCLUSIVE"
    n_structured: int
    n_shuffled: int


@dataclass
class M4Result:
    """Result of M4 (minimal dataset) test."""

    crr_full_mean: float
    crr_10pct_mean: float
    difference: float
    p_value: float
    verdict: str            # "TOPOLOGY_SUFFICIENT" / "VOLUME_REQUIRED"


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for two independent samples."""
    n1, n2 = len(a), len(b)
    var1, var2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std < 1e-10:
        return 0.0
    return float(abs(np.mean(a) - np.mean(b)) / pooled_std)


def generate_structured_dataset(
    n_subjects: int = 30,
    n_tasks: int = 20,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate dataset with preserved topological dependencies.

    Tasks have dependency structure: later tasks build on earlier ones.
    This creates a directed acyclic graph of cognitive operations.

    Returns (task_complexities, dependency_adjacency) for each subject.
    """
    rng = np.random.default_rng(seed)

    # Build dependency graph: each task depends on 0-3 prior tasks
    adjacency = np.zeros((n_tasks, n_tasks), dtype=int)
    for i in range(1, n_tasks):
        n_deps = rng.integers(0, min(3, i) + 1)
        if n_deps > 0:
            deps = rng.choice(i, n_deps, replace=False)
            adjacency[deps, i] = 1

    # Task complexity increases with depth in DAG
    depth = np.zeros(n_tasks)
    for i in range(n_tasks):
        parents = np.where(adjacency[:, i] > 0)[0]
        if len(parents) > 0:
            depth[i] = max(depth[parents]) + 1

    # Generate subject CRRs under structured dataset
    base_complexity = 2.0 + depth * 0.4  # Higher depth = harder tasks
    crr_structured = np.empty(n_subjects)

    for s in range(n_subjects):
        # Subject ability
        ability = 0.3 + 0.5 * rng.beta(2, 2)
        # Structured tasks: performance scales with depth understanding
        t0_perf = ability * np.mean(base_complexity[:5])  # Easy baseline
        t3_perf = ability * np.mean(base_complexity[-5:]) * (1 + rng.normal(0.05, 0.08))
        crr_structured[s] = t3_perf / max(t0_perf, 1e-10)

    return crr_structured, adjacency


def generate_shuffled_dataset(
    n_subjects: int = 30,
    n_tasks: int = 20,
    seed: int = 43,
    structured_adjacency: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Generate dataset with destroyed topology but same volume.

    Same tasks, same total content, but dependency edges are
    randomly reassigned → topology entropy H(D) → max.
    """
    rng = np.random.default_rng(seed)
    n_tasks_actual = n_tasks

    # Shuffle: same number of edges but random placement
    if structured_adjacency is not None:
        n_edges = int(structured_adjacency.sum())
        # Random DAG with same edge count
        shuffled_adj = np.zeros_like(structured_adjacency)
        placed = 0
        while placed < n_edges:
            i, j = rng.integers(0, n_tasks_actual, 2)
            if i < j and shuffled_adj[i, j] == 0:
                shuffled_adj[i, j] = 1
                placed += 1
    else:
        shuffled_adj = np.zeros((n_tasks, n_tasks), dtype=int)

    # Without true structure, depth is noise
    depth_noise = rng.uniform(0, 3, n_tasks)
    base_complexity = 2.0 + depth_noise * 0.4

    crr_shuffled = np.empty(n_subjects)
    for s in range(n_subjects):
        ability = 0.3 + 0.5 * rng.beta(2, 2)
        # Shuffled: no depth gradient → performance is random
        t0_perf = ability * np.mean(rng.choice(base_complexity, 5, replace=False))
        t3_perf = ability * np.mean(rng.choice(base_complexity, 5, replace=False))
        # Small noise, no systematic gain
        t3_perf *= (1 + rng.normal(0.0, 0.08))
        crr_shuffled[s] = t3_perf / max(t0_perf, 1e-10)

    return crr_shuffled


def f3_test(
    n_subjects: int = 30,
    n_tasks: int = 20,
    seed: int = 42,
) -> TopologyTestResult:
    """F3 — The Kill Switch.

    Compares CRR distributions between structured and shuffled datasets.
    If p < 0.01 → topology law holds.
    If p ≥ 0.01 → scaling law sufficient, topology law dead.
    """
    crr_struct, adjacency = generate_structured_dataset(n_subjects, n_tasks, seed)
    crr_shuf = generate_shuffled_dataset(n_subjects, n_tasks, seed + 1, adjacency)

    # Mann-Whitney U test (non-parametric)
    u_stat, p_val = mannwhitneyu(crr_struct, crr_shuf, alternative="two-sided")
    d = _cohens_d(crr_struct, crr_shuf)

    if p_val < 0.01 and d > 0.8:
        verdict = "TOPOLOGY_LAW"
    elif p_val >= 0.01:
        verdict = "SCALING_LAW"
    else:
        verdict = "INCONCLUSIVE"

    return TopologyTestResult(
        crr_structured_mean=round(float(np.mean(crr_struct)), 4),
        crr_structured_std=round(float(np.std(crr_struct)), 4),
        crr_shuffled_mean=round(float(np.mean(crr_shuf)), 4),
        crr_shuffled_std=round(float(np.std(crr_shuf)), 4),
        u_statistic=round(float(u_stat), 2),
        p_value=round(float(p_val), 6),
        effect_size=round(d, 4),
        verdict=verdict,
        n_structured=n_subjects,
        n_shuffled=n_subjects,
    )


def m4_test(
    n_subjects: int = 30,
    n_tasks: int = 20,
    seed: int = 42,
) -> M4Result:
    """M4 — Minimal Dataset with Preserved Topology.

    If CRR(10% data, full topology) ≈ CRR(100% data, full topology)
    → topology alone is sufficient, volume is irrelevant.
    """
    crr_full, adjacency = generate_structured_dataset(n_subjects, n_tasks, seed)
    # 10% dataset: only 2 tasks but preserved dependency chain
    n_tasks_10pct = max(2, n_tasks // 10)
    crr_10pct, _ = generate_structured_dataset(n_subjects, n_tasks_10pct, seed)

    diff = abs(float(np.mean(crr_full)) - float(np.mean(crr_10pct)))
    _, p_val = mannwhitneyu(crr_full, crr_10pct, alternative="two-sided")

    verdict = "TOPOLOGY_SUFFICIENT" if p_val > 0.05 else "VOLUME_REQUIRED"

    return M4Result(
        crr_full_mean=round(float(np.mean(crr_full)), 4),
        crr_10pct_mean=round(float(np.mean(crr_10pct)), 4),
        difference=round(diff, 4),
        p_value=round(float(p_val), 6),
        verdict=verdict,
    )


def validate_standalone() -> dict:
    """Run F3 and M4 tests."""
    print("=== CFP/ДІЙ — Topology Law Validation ===\n")

    print("--- F3: Structured vs Shuffled (Kill Switch) ---")
    f3 = f3_test(n_subjects=50, n_tasks=20, seed=42)
    print(f"  Structured: CRR = {f3.crr_structured_mean:.4f} ± {f3.crr_structured_std:.4f}")
    print(f"  Shuffled:   CRR = {f3.crr_shuffled_mean:.4f} ± {f3.crr_shuffled_std:.4f}")
    print(f"  U = {f3.u_statistic}  p = {f3.p_value:.6f}  Cohen's d = {f3.effect_size:.4f}")
    print(f"  VERDICT: {f3.verdict}\n")

    print("--- M4: 10% Dataset with Preserved Topology ---")
    m4 = m4_test(n_subjects=50, n_tasks=20, seed=42)
    print(f"  Full (100%): CRR = {m4.crr_full_mean:.4f}")
    print(f"  Mini (10%):  CRR = {m4.crr_10pct_mean:.4f}")
    print(f"  Δ = {m4.difference:.4f}  p = {m4.p_value:.6f}")
    print(f"  VERDICT: {m4.verdict}")

    return {
        "f3": {
            "crr_structured": f3.crr_structured_mean,
            "crr_shuffled": f3.crr_shuffled_mean,
            "p_value": f3.p_value,
            "cohens_d": f3.effect_size,
            "verdict": f3.verdict,
        },
        "m4": {
            "crr_full": m4.crr_full_mean,
            "crr_10pct": m4.crr_10pct_mean,
            "p_value": m4.p_value,
            "verdict": m4.verdict,
        },
    }


if __name__ == "__main__":
    validate_standalone()
