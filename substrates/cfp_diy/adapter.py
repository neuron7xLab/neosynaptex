"""
CFP/ДІЙ — Cognitive Field Protocol Substrate Adapter
====================================================
Sixth substrate in NFI architecture.
Implements DomainAdapter Protocol.

SIMULATION: Agent-Based Model of human+AI co-adaptation.
γ is EMERGENT from dynamics — never injected.

Model:
  N cognitive agents, each with:
    - ability a_i ∈ (0,1) — innate cognitive capacity
    - delegation d_i ∈ [0,1] — fraction of work offloaded to AI
    - skill s_i — accumulated competence, evolves via practice

  Dynamics per tick:
    1. Agent chooses task of complexity c ~ Beta(2,5) * (1 + depth_bonus)
    2. If AI available: agent delegates d_i fraction
       - Delegated work builds NO skill: ds/dt += 0
       - Own work builds skill: ds/dt += α * (c - s_i) * (1 - d_i)
    3. Error rate: e_i = max(0, c - s_i * (1-d_i) - ai_quality * d_i) + noise
    4. Cognitive output = completed complexity / error = throughput / cost

  Parameter sweep (like Gray-Scott F-sweep):
    Sweep AI_quality ∈ [0, 1] across 20 regimes.
    For each regime, run N agents for T ticks to equilibrium.
    Measure:
      topo = mean cognitive throughput (tasks * complexity completed)
      cost = mean error rate (mistakes per unit output)

  γ emerges from how error cost scales with throughput across AI quality regimes.
  NOT injected. NOT assumed. Derived from the simulation dynamics.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

import numpy as np

_TOPO_FLOOR = 1e-6
_N_AGENTS = 50
_T_EQUIL = 200
_N_REGIMES = 20
_SKILL_RATE = 0.05  # learning rate
_DELEGATION_ADAPT_RATE = 0.02  # how fast agents adjust delegation


def _run_regime(
    ai_quality: float,
    n_agents: int = _N_AGENTS,
    t_steps: int = _T_EQUIL,
    seed: int = 42,
) -> dict:
    """Run one ABM regime to equilibrium.

    ai_quality ∈ [0, 1]: quality of AI assistance.
      0 = no AI (solo cognition)
      1 = perfect AI (oracle)

    Returns equilibrium measurements: throughput, error_rate, etc.
    """
    rng = np.random.default_rng(seed)

    # Agent initial state
    ability = 0.2 + 0.6 * rng.beta(2, 3, n_agents)  # innate capacity
    skill = ability.copy()  # starts at innate level
    delegation = np.clip(ai_quality * 0.5 + rng.normal(0, 0.1, n_agents), 0, 0.95)

    throughput_history = []
    error_history = []

    for t in range(t_steps):
        # Task complexity drawn from environment (not controlled by agent)
        task_complexity = rng.beta(2, 5, n_agents) * 2.0 + 0.1  # ∈ [0.1, 2.1]

        # Effective work split
        own_effort = (1 - delegation) * skill
        ai_effort = delegation * ai_quality
        total_effort = own_effort + ai_effort

        # Error: gap between task demands and combined effort
        raw_error = task_complexity - total_effort
        noise = rng.normal(0, 0.05, n_agents)
        error = np.clip(raw_error + noise, 0.01, 5.0)

        # Throughput: what the agent+AI actually produces
        # Higher skill + better AI → more completed complexity
        throughput = np.clip(total_effort + rng.normal(0, 0.02, n_agents), 0.01, 5.0)

        # Skill evolution: ONLY from own practice
        # Key mechanism: delegation reduces skill growth
        skill_gap = task_complexity - skill
        skill += _SKILL_RATE * skill_gap * (1 - delegation)
        skill = np.clip(skill, 0.05, 3.0)

        # Delegation adaptation: agents adjust based on error feedback
        # High error → increase delegation; low error → decrease
        delegation += _DELEGATION_ADAPT_RATE * (error - 0.5) * 0.1
        delegation = np.clip(delegation, 0, 0.95)

        # Record last half (equilibrium region)
        if t >= t_steps // 2:
            throughput_history.append(float(np.mean(throughput)))
            error_history.append(float(np.mean(error)))

    # Equilibrium statistics
    eq_throughput = float(np.mean(throughput_history))
    eq_error = float(np.mean(error_history))
    eq_skill = float(np.mean(skill))
    eq_delegation = float(np.mean(delegation))

    return {
        "ai_quality": ai_quality,
        "throughput": eq_throughput,
        "error_rate": eq_error,
        "mean_skill": eq_skill,
        "mean_delegation": eq_delegation,
    }


class CfpDiyAdapter:
    """Cognitive Field Protocol substrate adapter — ABM simulation.

    Pre-computes equilibria across AI quality sweep (0→1).
    γ emerges from cross-regime scaling of throughput vs error.
    Analogous to Gray-Scott F-sweep producing different pattern regimes.
    """

    def __init__(self, seed: int = 42, n_regimes: int = _N_REGIMES) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0

        # Sweep AI quality parameter
        ai_qualities = np.linspace(0.0, 1.0, n_regimes)
        self._equilibria: list[dict] = []
        for i, aq in enumerate(ai_qualities):
            eq = _run_regime(aq, seed=seed + i * 7)
            # Only keep regimes with meaningful throughput
            if eq["throughput"] > 0.05 and eq["error_rate"] > 0.01:
                self._equilibria.append(eq)

        self._idx = 0

    # --- DomainAdapter Protocol ---

    @property
    def domain(self) -> str:
        return "cfp_diy"

    @property
    def state_keys(self) -> list[str]:
        return ["throughput", "error_rate", "skill", "delegation"]

    def state(self) -> dict[str, float]:
        """Advance one step. Random sample from equilibria."""
        self._t += 1
        self._idx = int(self._rng.integers(0, len(self._equilibria)))
        eq = self._equilibria[self._idx]
        noise = self._rng.normal(0, 0.001)
        return {
            "throughput": eq["throughput"] + noise,
            "error_rate": eq["error_rate"] + noise,
            "skill": eq["mean_skill"],
            "delegation": eq["mean_delegation"],
        }

    def topo(self) -> float:
        """Cognitive throughput — total productive output per unit time.

        Higher throughput = more cognitive work accomplished.
        Multiplicative noise for engine fit (γ-invariant under ×const).
        """
        eq = self._equilibria[self._idx]
        jitter = 1.0 + self._rng.normal(0, 0.02)
        return max(_TOPO_FLOOR, eq["throughput"] * jitter)

    def thermo_cost(self) -> float:
        """Cognitive error rate — mistakes per unit output.

        This is the thermodynamic cost of operating at given throughput.
        At optimal co-adaptation: cost scales as topo^(-γ).
        γ value is whatever the dynamics produce — NOT predetermined.
        """
        eq = self._equilibria[self._idx]
        jitter = 1.0 + self._rng.normal(0, 0.02)
        return max(_TOPO_FLOOR, eq["error_rate"] * jitter)


# ---------------------------------------------------------------------------
# Standalone validation — derives γ from ABM simulation
# ---------------------------------------------------------------------------
def validate_standalone() -> dict:
    """Compute γ for CFP/ДІЙ ABM substrate using Theil-Sen.

    γ is whatever comes out. It may or may not be near 1.0.
    That's the whole point — no circular guarantee.
    """
    from scipy.stats import theilslopes

    print("=== CFP/ДІЙ — Cognitive Field Protocol ABM Validation ===\n")
    print(f"Running ABM: {_N_REGIMES} AI-quality regimes × {_N_AGENTS} agents × {_T_EQUIL} ticks\n")

    adapter = CfpDiyAdapter(seed=42, n_regimes=25)

    # Collect equilibria
    topos, costs = [], []
    for _ in range(len(adapter._equilibria) * 5):
        adapter.state()
        t = adapter.topo()
        c = adapter.thermo_cost()
        if t > _TOPO_FLOOR and c > _TOPO_FLOOR:
            topos.append(t)
            costs.append(c)

    t_v, c_v = np.array(topos), np.array(costs)

    # Deduplicate equilibria (same regime cycled with noise)
    pairs = np.unique(np.round(np.column_stack([np.log(t_v), np.log(c_v)]), 4), axis=0)
    log_t, log_c = pairs[:, 0], pairs[:, 1]

    if len(log_t) < 5:
        print("  INSUFFICIENT DATA for γ derivation")
        return {"gamma": float("nan"), "r2": 0, "n": len(log_t), "regime": "INSUFFICIENT"}

    slope, intc, lo, hi = theilslopes(log_c, log_t)
    gamma = -slope
    yhat = slope * log_t + intc
    ss_r = np.sum((log_c - yhat) ** 2)
    ss_t = np.sum((log_c - log_c.mean()) ** 2)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-10 else 0

    dist = abs(gamma - 1.0)
    regime = (
        "METASTABLE"
        if dist < 0.15
        else "WARNING"
        if dist < 0.30
        else "CRITICAL"
        if dist < 0.50
        else "COLLAPSE"
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
    n = len(log_t)
    for i in range(n_boot):
        idx = rng.choice(n, n, replace=True)
        s, _, _, _ = theilslopes(log_c[idx], log_t[idx])
        boot_gammas[i] = -s
    ci = [float(np.percentile(boot_gammas, 2.5)), float(np.percentile(boot_gammas, 97.5))]

    print(f"  γ = {gamma:.4f}  R² = {r2:.4f}  CI = [{ci[0]:.3f}, {ci[1]:.3f}]")
    print(f"  n = {n} unique equilibria  p_perm = {p_perm:.4f}  regime = {regime}")

    # Show equilibria
    print(f"\n  Equilibria ({len(adapter._equilibria)} regimes):")
    for eq in adapter._equilibria:
        print(
            f"    AI={eq['ai_quality']:.2f}  throughput={eq['throughput']:.3f}  "
            f"error={eq['error_rate']:.3f}  skill={eq['mean_skill']:.3f}  "
            f"deleg={eq['mean_delegation']:.3f}"
        )

    return {
        "gamma": round(float(gamma), 4),
        "r2": round(float(r2), 4),
        "ci": [round(c, 4) for c in ci],
        "p_perm": round(p_perm, 4),
        "n": n,
        "regime": regime,
    }


if __name__ == "__main__":
    validate_standalone()
