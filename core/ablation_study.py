"""Ablation study — role-based vs energy-based vs hybrid control of coherence.

Task 6 deliverable.

Goal
----
Empirically test the thesis: *what matters is not the role scheme (fixed
personas/gain), but the energetics of objections (dynamic energy control +
FDT-derived γ)*. We compare three regimes:

1. **Roles-only**: fixed critic gain (E_obj constant), varied γ targets
   (simulating role diversity without energy control).
2. **Energy-only**: dynamic E_obj via PID-like gain scheduling, fixed γ target
   (energy control without role diversity).
3. **Hybrid**: dynamic E_obj + varied γ targets (full system).

Each regime is evaluated on:
- *Quality*: final coherence S and fraction of steps with ΔS > 0.
- *Robustness*: std of quality across seeds.
- *Compute cost*: total |E_obj| integrated over time (proxy for critic work).

The three metrics form a Pareto front that reveals which regime gives the
best quality/robustness per unit cost.

Design notes
------------
* numpy-only; no dependency on OEB controller (Task 3) or benchmark (Task 4).
  Uses ``CoherenceStateSpace`` directly.
* Frozen dataclasses for all result objects.
* Deterministic given seed.
* INV-1 compliant: γ is trajectory data, never cached state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
)

__all__ = [
    "AblationConfig",
    "AblationResult",
    "AblationSummary",
    "AblationStudy",
]

FloatArray = NDArray[np.float64]

# ── Regime names ────────────────────────────────────────────────────────

REGIME_ROLES_ONLY: Final[str] = "roles_only"
REGIME_ENERGY_ONLY: Final[str] = "energy_only"
REGIME_HYBRID: Final[str] = "hybrid"
ALL_REGIMES: Final[tuple[str, ...]] = (
    REGIME_ROLES_ONLY,
    REGIME_ENERGY_ONLY,
    REGIME_HYBRID,
)


# ── Config / result dataclasses ─────────────────────────────────────────


@dataclass(frozen=True)
class AblationConfig:
    """Configuration for a single ablation run.

    Attributes:
        regime: one of ``ALL_REGIMES``.
        n_steps: trajectory length.
        n_seeds: number of independent seeds (for robustness stats).
        base_seed: first seed; seeds are ``base_seed .. base_seed + n_seeds - 1``.
        initial_state: starting point.
        roles_gamma_targets: sequence of γ targets to cycle through in the
            roles-only and hybrid regimes.
        energy_gain_schedule: PID-like gain sequence for energy-only and
            hybrid regimes (length ``n_steps``). If *None*, a simple
            proportional controller is used internally.
    """

    regime: str
    n_steps: int = 200
    n_seeds: int = 10
    base_seed: int = 0
    initial_state: CoherenceState = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3)
    roles_gamma_targets: tuple[float, ...] = (0.8, 1.0, 1.2)
    energy_gain_schedule: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.regime not in ALL_REGIMES:
            raise ValueError(f"regime must be one of {ALL_REGIMES}, got {self.regime!r}")
        if self.n_steps < 1:
            raise ValueError("n_steps must be >= 1")
        if self.n_seeds < 1:
            raise ValueError("n_seeds must be >= 1")


@dataclass(frozen=True)
class AblationResult:
    """Result of a single ablation run (one seed)."""

    regime: str
    seed: int
    quality: float  # final coherence S
    delta_s_positive_frac: float  # fraction of steps where ΔS > 0
    compute_cost: float  # integral of |E_obj| over trajectory
    final_gamma: float
    trajectory: FloatArray  # (n_steps+1, 4) — full state trajectory


@dataclass(frozen=True)
class AblationSummary:
    """Aggregate statistics for one regime across all seeds."""

    regime: str
    quality_mean: float
    quality_std: float
    delta_s_frac_mean: float
    delta_s_frac_std: float
    cost_mean: float
    cost_std: float
    pareto_point: tuple[float, float, float]  # (quality, robustness, cost)
    n_runs: int


@dataclass(frozen=True)
class AblationReport:
    """Full ablation study report across all regimes."""

    summaries: tuple[AblationSummary, ...]
    all_results: tuple[AblationResult, ...]
    dominant_regime: str  # regime with best quality/cost ratio

    def summary_for(self, regime: str) -> AblationSummary:
        """Look up summary by regime name."""
        for s in self.summaries:
            if s.regime == regime:
                return s
        raise KeyError(f"no summary for regime {regime!r}")


# ── PID-like proportional gain controller (minimal, for energy regimes) ─


def _proportional_gain_schedule(
    n_steps: int,
    *,
    target_s: float = 0.5,
    kp: float = 0.3,
    base_gain: float = 0.05,
) -> FloatArray:
    """Generate a simple proportional gain schedule.

    At each step the gain is ``base_gain + kp * |S_t - target_s|``,
    but since we don't know S_t in advance we use a warm-up ramp that
    starts high and decays.  Good enough for ablation comparison.
    """
    t = np.arange(n_steps, dtype=np.float64)
    decay = np.exp(-0.01 * t)
    return np.asarray(base_gain + kp * decay, dtype=np.float64)


# ── Core study engine ───────────────────────────────────────────────────

_ROLE_CYCLE_PERIOD: Final[int] = 20  # switch γ target every N steps


class AblationStudy:
    """Run ablation experiments comparing role-based, energy-based, and hybrid.

    Usage::

        study = AblationStudy()
        report = study.run_all()
        print(report.dominant_regime)
    """

    def __init__(
        self,
        base_params: CoherenceStateSpaceParams | None = None,
    ) -> None:
        self.base_params: CoherenceStateSpaceParams = base_params or CoherenceStateSpaceParams()

    # ── Single run ──────────────────────────────────────────────────

    def run_single(
        self,
        config: AblationConfig,
        seed: int,
    ) -> AblationResult:
        """Execute one ablation run for *config* with a specific *seed*."""
        rng = np.random.default_rng(seed)
        n = config.n_steps

        # Build model with appropriate params per regime
        if config.regime == REGIME_ROLES_ONLY:
            traj = self._run_roles_only(config, n, rng)
        elif config.regime == REGIME_ENERGY_ONLY:
            traj = self._run_energy_only(config, n, rng)
        elif config.regime == REGIME_HYBRID:
            traj = self._run_hybrid(config, n, rng)
        else:  # pragma: no cover — validated in __post_init__
            raise ValueError(config.regime)

        # Compute metrics from trajectory
        s_traj = traj[:, 0]
        delta_s = np.diff(s_traj)
        quality = float(s_traj[-1])
        ds_frac = float(np.mean(delta_s > 0)) if len(delta_s) > 0 else 0.0
        cost = float(np.sum(np.abs(traj[:-1, 2])) * self.base_params.dt)
        final_gamma = float(traj[-1, 1])

        return AblationResult(
            regime=config.regime,
            seed=seed,
            quality=quality,
            delta_s_positive_frac=ds_frac,
            compute_cost=cost,
            final_gamma=final_gamma,
            trajectory=traj,
        )

    # ── Regime implementations ──────────────────────────────────────

    def _run_roles_only(
        self,
        config: AblationConfig,
        n_steps: int,
        rng: np.random.Generator,
    ) -> FloatArray:
        """Roles-only: cycle γ targets, fixed E_obj (no energy control)."""
        targets = config.roles_gamma_targets
        traj = np.empty((n_steps + 1, 4), dtype=np.float64)
        state = config.initial_state
        traj[0] = state.as_vector()

        for t in range(n_steps):
            # Cycle through γ targets (simulates role switching)
            g_target = targets[t // _ROLE_CYCLE_PERIOD % len(targets)]
            model = CoherenceStateSpace(
                CoherenceStateSpaceParams(
                    dt=self.base_params.dt,
                    alpha=self.base_params.alpha,
                    beta=self.base_params.beta,
                    kappa=self.base_params.kappa,
                    lam_g=self.base_params.lam_g,
                    mu_g=self.base_params.mu_g,
                    g_target=g_target,
                    lam_e=self.base_params.lam_e,
                    nu_e=self.base_params.nu_e,
                    rho=self.base_params.rho,
                    v_target=self.base_params.v_target,
                )
            )
            # Fixed E_obj input (no energy control)
            state = model.step(state, (0.0, 0.0), rng)
            traj[t + 1] = state.as_vector()

        return traj

    def _run_energy_only(
        self,
        config: AblationConfig,
        n_steps: int,
        rng: np.random.Generator,
    ) -> FloatArray:
        """Energy-only: dynamic E_obj via gain schedule, fixed γ target."""
        model = CoherenceStateSpace(self.base_params)

        if config.energy_gain_schedule is not None:
            gains = np.asarray(config.energy_gain_schedule, dtype=np.float64)
            if len(gains) < n_steps:
                gains = np.pad(gains, (0, n_steps - len(gains)), mode="edge")
        else:
            gains = _proportional_gain_schedule(n_steps)

        traj = np.empty((n_steps + 1, 4), dtype=np.float64)
        state = config.initial_state
        traj[0] = state.as_vector()

        for t in range(n_steps):
            # Dynamic energy injection: u_E = gain[t] * (1 - S)
            u_e = float(gains[t]) * (1.0 - state.S)
            state = model.step(state, (0.0, u_e), rng)
            traj[t + 1] = state.as_vector()

        return traj

    def _run_hybrid(
        self,
        config: AblationConfig,
        n_steps: int,
        rng: np.random.Generator,
    ) -> FloatArray:
        """Hybrid: dynamic E_obj + cycling γ targets."""
        targets = config.roles_gamma_targets

        if config.energy_gain_schedule is not None:
            gains = np.asarray(config.energy_gain_schedule, dtype=np.float64)
            if len(gains) < n_steps:
                gains = np.pad(gains, (0, n_steps - len(gains)), mode="edge")
        else:
            gains = _proportional_gain_schedule(n_steps)

        traj = np.empty((n_steps + 1, 4), dtype=np.float64)
        state = config.initial_state
        traj[0] = state.as_vector()

        for t in range(n_steps):
            g_target = targets[t // _ROLE_CYCLE_PERIOD % len(targets)]
            model = CoherenceStateSpace(
                CoherenceStateSpaceParams(
                    dt=self.base_params.dt,
                    alpha=self.base_params.alpha,
                    beta=self.base_params.beta,
                    kappa=self.base_params.kappa,
                    lam_g=self.base_params.lam_g,
                    mu_g=self.base_params.mu_g,
                    g_target=g_target,
                    lam_e=self.base_params.lam_e,
                    nu_e=self.base_params.nu_e,
                    rho=self.base_params.rho,
                    v_target=self.base_params.v_target,
                )
            )
            u_e = float(gains[t]) * (1.0 - state.S)
            state = model.step(state, (0.0, u_e), rng)
            traj[t + 1] = state.as_vector()

        return traj

    # ── Multi-seed aggregation ──────────────────────────────────────

    def run_config(self, config: AblationConfig) -> list[AblationResult]:
        """Run all seeds for a single config."""
        return [self.run_single(config, seed=config.base_seed + i) for i in range(config.n_seeds)]

    def summarize(self, results: list[AblationResult]) -> AblationSummary:
        """Aggregate results into a summary for one regime."""
        if not results:
            raise ValueError("empty results list")
        regime = results[0].regime
        qualities = np.array([r.quality for r in results], dtype=np.float64)
        ds_fracs = np.array([r.delta_s_positive_frac for r in results], dtype=np.float64)
        costs = np.array([r.compute_cost for r in results], dtype=np.float64)

        q_mean = float(np.mean(qualities))
        q_std = float(np.std(qualities, ddof=1)) if len(qualities) > 1 else 0.0
        ds_mean = float(np.mean(ds_fracs))
        ds_std = float(np.std(ds_fracs, ddof=1)) if len(ds_fracs) > 1 else 0.0
        c_mean = float(np.mean(costs))
        c_std = float(np.std(costs, ddof=1)) if len(costs) > 1 else 0.0

        # Robustness = 1 - normalised quality std (higher is better)
        robustness = 1.0 - min(q_std, 1.0)
        pareto = (q_mean, robustness, c_mean)

        return AblationSummary(
            regime=regime,
            quality_mean=q_mean,
            quality_std=q_std,
            delta_s_frac_mean=ds_mean,
            delta_s_frac_std=ds_std,
            cost_mean=c_mean,
            cost_std=c_std,
            pareto_point=pareto,
            n_runs=len(results),
        )

    # ── Full study ──────────────────────────────────────────────────

    def run_all(
        self,
        n_steps: int = 200,
        n_seeds: int = 10,
        base_seed: int = 0,
    ) -> AblationReport:
        """Run the complete ablation study across all three regimes.

        Returns an ``AblationReport`` with per-regime summaries and the
        dominant regime (best quality/cost ratio).
        """
        all_results: list[AblationResult] = []
        summaries: list[AblationSummary] = []

        for regime in ALL_REGIMES:
            config = AblationConfig(
                regime=regime,
                n_steps=n_steps,
                n_seeds=n_seeds,
                base_seed=base_seed,
            )
            results = self.run_config(config)
            all_results.extend(results)
            summaries.append(self.summarize(results))

        # Dominant = highest quality / cost ratio
        best_idx = int(np.argmax([s.quality_mean / max(s.cost_mean, 1e-12) for s in summaries]))
        dominant = summaries[best_idx].regime

        return AblationReport(
            summaries=tuple(summaries),
            all_results=tuple(all_results),
            dominant_regime=dominant,
        )
