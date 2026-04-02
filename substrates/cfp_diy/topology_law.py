"""
Topology Law Test (F3) — The Kill Switch
=========================================
Critical falsification experiment for CFP/ДІЙ.

Uses the SAME ABM simulation engine with two conditions:
  D_structured: tasks have dependency DAG (later tasks require prior skills)
  D_shuffled:   same tasks, random order (no dependency structure)

This is NOT a synthetic test designed to pass.
The ABM runs the full simulation in both conditions.
γ and CRR emerge from dynamics — the test reports whatever comes out.

If CRR(D_structured) = CRR(D_shuffled) → topology doesn't matter → F3 kills the hypothesis.
If CRR(D_structured) ≠ CRR(D_shuffled) → topology law has evidence.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import mannwhitneyu


@dataclass
class TopologyTestResult:
    """Result of F3 topology law test."""

    crr_structured_mean: float
    crr_structured_std: float
    crr_shuffled_mean: float
    crr_shuffled_std: float
    u_statistic: float
    p_value: float
    effect_size: float  # Cohen's d
    verdict: str  # "TOPOLOGY_LAW" / "SCALING_LAW" / "INCONCLUSIVE"
    n_structured: int
    n_shuffled: int


@dataclass
class M4Result:
    """Result of M4 (minimal dataset) test."""

    crr_full_mean: float
    crr_reduced_mean: float
    difference: float
    p_value: float
    verdict: str  # "TOPOLOGY_SUFFICIENT" / "VOLUME_REQUIRED"


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for two independent samples."""
    n1, n2 = len(a), len(b)
    var1, var2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std < 1e-10:
        return 0.0
    return float(abs(np.mean(a) - np.mean(b)) / pooled_std)


def _run_coadaptation_abm(
    n_agents: int,
    n_tasks: int,
    task_order: np.ndarray,
    task_complexities: np.ndarray,
    task_prerequisites: list[list[int]],
    ai_quality: float,
    seed: int,
) -> np.ndarray:
    """Run co-adaptation ABM and return CRR for each agent.

    Phase structure:
      Tasks 0..n/3:     T0 (no AI, baseline)
      Tasks n/3..2n/3:  T1+T2 (with AI)
      Tasks 2n/3..n:    T3 (no AI, recovery)

    CRR = mean_performance(T3) / mean_performance(T0)

    task_order: the sequence in which tasks are presented
    task_prerequisites: for each task, which tasks must be completed first
                       (skills from prerequisites transfer)
    """
    rng = np.random.default_rng(seed)

    # Agent state
    skill = 0.2 + 0.3 * rng.beta(2, 3, n_agents)
    completed_tasks: list[set[int]] = [set() for _ in range(n_agents)]

    t0_end = n_tasks // 3
    t2_end = 2 * n_tasks // 3

    t0_perf = np.zeros(n_agents)
    t0_count = np.zeros(n_agents)
    t3_perf = np.zeros(n_agents)
    t3_count = np.zeros(n_agents)

    for step, task_id in enumerate(task_order):
        c = task_complexities[task_id]
        prereqs = task_prerequisites[task_id]

        # Prerequisite bonus: if agent completed prerequisites,
        # they have relevant prior knowledge (structural advantage)
        for agent_i in range(n_agents):
            prereq_bonus = 0.0
            if prereqs:
                completed_prereqs = sum(1 for p in prereqs if p in completed_tasks[agent_i])
                prereq_bonus = 0.15 * (completed_prereqs / len(prereqs))

            effective_skill = skill[agent_i] + prereq_bonus

            # AI assistance only in T1+T2 phase
            use_ai = t0_end <= step < t2_end
            ai_boost = ai_quality * 0.3 if use_ai else 0.0

            # Performance = how well agent handles task
            perf = min(1.0, (effective_skill + ai_boost) / max(c, 0.1))
            perf += rng.normal(0, 0.05)
            perf = np.clip(perf, 0, 1)

            # Skill update: practice effect (only from own work)
            own_fraction = 1.0 - (0.4 if use_ai else 0.0)
            skill[agent_i] += 0.02 * (c - skill[agent_i]) * own_fraction
            skill[agent_i] = np.clip(skill[agent_i], 0.05, 2.0)

            completed_tasks[agent_i].add(task_id)

            # Record phase performance
            if step < t0_end:
                t0_perf[agent_i] += perf
                t0_count[agent_i] += 1
            elif step >= t2_end:
                t3_perf[agent_i] += perf
                t3_count[agent_i] += 1

    # CRR per agent
    t0_mean = np.where(t0_count > 0, t0_perf / t0_count, 0.5)
    t3_mean = np.where(t3_count > 0, t3_perf / t3_count, 0.5)
    crr = t3_mean / np.clip(t0_mean, 0.01, None)

    return crr


def _build_task_graph(n_tasks: int, seed: int) -> tuple[np.ndarray, list[list[int]]]:
    """Build a DAG of task dependencies.

    Returns (task_complexities, prerequisites_per_task).
    Complexity increases with DAG depth.
    """
    rng = np.random.default_rng(seed)

    # Build DAG: each task can depend on 0-2 earlier tasks
    prerequisites: list[list[int]] = [[] for _ in range(n_tasks)]
    for i in range(1, n_tasks):
        n_deps = rng.integers(0, min(3, i))
        if n_deps > 0:
            deps = rng.choice(i, n_deps, replace=False).tolist()
            prerequisites[i] = deps

    # Compute depth
    depth = np.zeros(n_tasks)
    for i in range(n_tasks):
        if prerequisites[i]:
            depth[i] = max(depth[p] for p in prerequisites[i]) + 1

    # Complexity scales with depth (structured curriculum)
    base = 0.3 + 0.1 * depth + rng.normal(0, 0.05, n_tasks)
    complexities = np.clip(base, 0.1, 3.0)

    return complexities, prerequisites


def f3_test(
    n_agents: int = 40,
    n_tasks: int = 30,
    seed: int = 42,
) -> TopologyTestResult:
    """F3 — The Kill Switch.

    Condition A (structured): tasks presented in topological order (prerequisites first)
    Condition B (shuffled): same tasks, random order (prerequisites broken)

    Both conditions use IDENTICAL tasks, complexities, and AI quality.
    The ONLY difference is task ORDER (topology preserved vs destroyed).
    """
    complexities, prerequisites = _build_task_graph(n_tasks, seed)

    # Topological order (structured)
    topo_order = np.argsort(
        -np.array(
            [max((0,) + tuple(len(prerequisites[j]) for j in range(i))) for i in range(n_tasks)]
        )
    )
    # Simple: sort by depth (prerequisites come first)
    depths = np.zeros(n_tasks)
    for i in range(n_tasks):
        if prerequisites[i]:
            depths[i] = max(depths[p] for p in prerequisites[i]) + 1
    structured_order = np.argsort(depths)

    # Shuffled order (random)
    rng = np.random.default_rng(seed + 1000)
    shuffled_order = rng.permutation(n_tasks)

    # Run both conditions
    crr_structured = _run_coadaptation_abm(
        n_agents,
        n_tasks,
        structured_order,
        complexities,
        prerequisites,
        ai_quality=0.6,
        seed=seed,
    )
    crr_shuffled = _run_coadaptation_abm(
        n_agents,
        n_tasks,
        shuffled_order,
        complexities,
        prerequisites,
        ai_quality=0.6,
        seed=seed,
    )

    # Statistical test
    u_stat, p_val = mannwhitneyu(crr_structured, crr_shuffled, alternative="two-sided")
    d = _cohens_d(crr_structured, crr_shuffled)

    if p_val < 0.01 and d > 0.5:
        verdict = "TOPOLOGY_LAW"
    elif p_val >= 0.05:
        verdict = "SCALING_LAW"
    else:
        verdict = "INCONCLUSIVE"

    return TopologyTestResult(
        crr_structured_mean=round(float(np.mean(crr_structured)), 4),
        crr_structured_std=round(float(np.std(crr_structured)), 4),
        crr_shuffled_mean=round(float(np.mean(crr_shuffled)), 4),
        crr_shuffled_std=round(float(np.std(crr_shuffled)), 4),
        u_statistic=round(float(u_stat), 2),
        p_value=round(float(p_val), 6),
        effect_size=round(d, 4),
        verdict=verdict,
        n_structured=n_agents,
        n_shuffled=n_agents,
    )


def m4_test(
    n_agents: int = 40,
    n_tasks_full: int = 30,
    seed: int = 42,
) -> M4Result:
    """M4 — Minimal Dataset with Preserved Topology.

    Condition A: Full task set (30 tasks), structured order
    Condition B: 30% of tasks, but preserving prerequisite chains

    If CRR(30%) ≈ CRR(100%) → structure matters more than volume.
    """
    complexities, prerequisites = _build_task_graph(n_tasks_full, seed)

    # Full set: topological order
    depths = np.zeros(n_tasks_full)
    for i in range(n_tasks_full):
        if prerequisites[i]:
            depths[i] = max(depths[p] for p in prerequisites[i]) + 1
    structured_order = np.argsort(depths)

    # Reduced set: keep 30% of tasks, preserving dependency chains
    n_reduced = max(6, n_tasks_full * 3 // 10)
    # Select tasks with highest depth (they carry the most structure)
    selected = np.argsort(depths)[-n_reduced:]
    # Add their prerequisites
    selected_set = set(selected.tolist())
    for task_id in list(selected_set):
        for prereq in prerequisites[task_id]:
            selected_set.add(prereq)
    selected_sorted = sorted(selected_set)

    # Remap
    reduced_complexities = complexities[selected_sorted]
    remap = {old: new for new, old in enumerate(selected_sorted)}
    reduced_prereqs: list[list[int]] = []
    for old_id in selected_sorted:
        reduced_prereqs.append([remap[p] for p in prerequisites[old_id] if p in remap])
    n_reduced_actual = len(selected_sorted)

    # Reduced depths and order
    reduced_depths = np.zeros(n_reduced_actual)
    for i in range(n_reduced_actual):
        if reduced_prereqs[i]:
            reduced_depths[i] = max(reduced_depths[p] for p in reduced_prereqs[i]) + 1
    reduced_order = np.argsort(reduced_depths)

    crr_full = _run_coadaptation_abm(
        n_agents,
        n_tasks_full,
        structured_order,
        complexities,
        prerequisites,
        ai_quality=0.6,
        seed=seed,
    )
    crr_reduced = _run_coadaptation_abm(
        n_agents,
        n_reduced_actual,
        reduced_order,
        reduced_complexities,
        reduced_prereqs,
        ai_quality=0.6,
        seed=seed,
    )

    diff = abs(float(np.mean(crr_full)) - float(np.mean(crr_reduced)))
    _, p_val = mannwhitneyu(crr_full, crr_reduced, alternative="two-sided")

    verdict = "TOPOLOGY_SUFFICIENT" if p_val > 0.05 else "VOLUME_REQUIRED"

    return M4Result(
        crr_full_mean=round(float(np.mean(crr_full)), 4),
        crr_reduced_mean=round(float(np.mean(crr_reduced)), 4),
        difference=round(diff, 4),
        p_value=round(float(p_val), 6),
        verdict=verdict,
    )


def validate_standalone() -> dict:
    """Run F3 and M4 tests. Report whatever comes out."""
    print("=== CFP/ДІЙ — Topology Law Validation (ABM-based) ===\n")

    print("--- F3: Structured vs Shuffled (Kill Switch) ---")
    f3 = f3_test(n_agents=50, n_tasks=30, seed=42)
    print(f"  Structured: CRR = {f3.crr_structured_mean:.4f} ± {f3.crr_structured_std:.4f}")
    print(f"  Shuffled:   CRR = {f3.crr_shuffled_mean:.4f} ± {f3.crr_shuffled_std:.4f}")
    print(f"  U = {f3.u_statistic}  p = {f3.p_value:.6f}  Cohen's d = {f3.effect_size:.4f}")
    print(f"  VERDICT: {f3.verdict}\n")

    print("--- M4: 30% Dataset with Preserved Topology ---")
    m4 = m4_test(n_agents=50, n_tasks_full=30, seed=42)
    print(f"  Full (100%): CRR = {m4.crr_full_mean:.4f}")
    print(f"  Reduced (30%+deps): CRR = {m4.crr_reduced_mean:.4f}")
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
            "crr_reduced": m4.crr_reduced_mean,
            "p_value": m4.p_value,
            "verdict": m4.verdict,
        },
    }


if __name__ == "__main__":
    validate_standalone()
