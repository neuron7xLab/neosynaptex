"""Multi-scale criticality analysis via renormalization group coarse-graining.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests scale-invariance of criticality metrics by coarse-graining neuronal
spike trains at progressively larger spatial scales.

References
----------
docs/SPEC.md#P0-4
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from .analysis import fit_power_law_mle, mr_branching_ratio

BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class RenormalizationParams:
    """Parameters for multi-scale renormalization analysis.

    Parameters
    ----------
    grouping_factor : int
        Spatial coarse-graining factor per scale level.
    n_scales : int
        Number of coarse-graining scales to compute.
    analysis_window : int
        Number of timesteps to buffer before analysis.
    update_interval : int
        Minimum steps between successive compute() calls.
    """

    grouping_factor: int = 4
    n_scales: int = 4
    analysis_window: int = 1000
    update_interval: int = 500


@dataclass(frozen=True)
class ScaleMetrics:
    """Criticality metrics at a single coarse-graining scale.

    Parameters
    ----------
    scale : int
        Scale index (0 = individual neurons).
    n_groups : int
        Number of groups at this scale.
    sigma : float
        Branching ratio estimate.
    avalanche_exponent : float or None
        Power-law exponent of avalanche size distribution, or None if
        insufficient avalanches for a fit.
    entropy_rate : float
        Normalized entropy of the activity distribution.
    """

    scale: int
    n_groups: int
    sigma: float
    avalanche_exponent: float | None
    entropy_rate: float


@dataclass(frozen=True)
class RenormalizationResult:
    """Aggregate result of multi-scale renormalization analysis.

    Parameters
    ----------
    scales : list[ScaleMetrics]
        Per-scale metrics.
    sigma_cv : float
        Coefficient of variation of sigma across scales.
    tau_cv : float or None
        Coefficient of variation of avalanche exponents (None if fewer
        than 2 scales have valid exponents).
    entropy_cv : float
        Coefficient of variation of entropy rates across scales.
    scale_invariant : bool
        True if sigma_cv < 0.1, indicating scale-invariant criticality.
    flow_trajectory : list[tuple[float, float, float]]
        (sigma, avalanche_exponent_or_0, entropy_rate) per scale.
    timestamp_step : int
        Simulation step at which this result was computed.
    """

    scales: list[ScaleMetrics]
    sigma_cv: float
    tau_cv: float | None
    entropy_cv: float
    scale_invariant: bool
    flow_trajectory: list[tuple[float, float, float]]
    timestamp_step: int


@dataclass
class RenormalizationEngine:
    """Engine for multi-scale criticality analysis via coarse-graining.

    Parameters
    ----------
    N : int
        Total number of neurons.
    nE : int
        Number of excitatory neurons (reserved for future use).
    params : RenormalizationParams
        Renormalization configuration.

    Notes
    -----
    Maintains a ring buffer of spike vectors and performs coarse-grained
    branching ratio, avalanche, and entropy analysis on demand.
    """

    N: int
    nE: int
    params: RenormalizationParams
    _buffer: NDArray[np.bool_] = field(init=False, repr=False)
    _write_idx: int = field(init=False, default=0)
    _total_observed: int = field(init=False, default=0)
    _last_compute_step: int = field(init=False, default=-1)

    def __post_init__(self) -> None:
        self._buffer = np.zeros(
            (self.params.analysis_window, self.N), dtype=np.bool_
        )
        self._write_idx = 0
        self._total_observed = 0
        self._last_compute_step = -1

    def observe(self, spiked: BoolArray, step: int) -> None:
        """Record a spike vector into the ring buffer.

        Parameters
        ----------
        spiked : BoolArray
            Boolean spike vector of length N.
        step : int
            Current simulation step.
        """
        self._buffer[self._write_idx] = spiked[: self.N]
        self._write_idx = (self._write_idx + 1) % self.params.analysis_window
        self._total_observed += 1
        self._last_observe_step = step

    def compute(self) -> RenormalizationResult | None:
        """Run multi-scale analysis on the buffered spike data.

        Returns
        -------
        RenormalizationResult or None
            Analysis result, or None if insufficient data has been observed.
        """
        if self._total_observed < self.params.analysis_window:
            return None

        step = getattr(self, "_last_observe_step", self._total_observed)

        # Unroll ring buffer into contiguous time-ordered array
        if self._total_observed >= self.params.analysis_window:
            # Buffer is full; read from write_idx onward (oldest first)
            data = np.concatenate(
                [
                    self._buffer[self._write_idx :],
                    self._buffer[: self._write_idx],
                ],
                axis=0,
            )
        else:
            data = self._buffer[: self._total_observed]

        T = data.shape[0]
        scale_metrics: list[ScaleMetrics] = []

        for k in range(self.params.n_scales):
            group_size = self.params.grouping_factor ** k
            n_groups = self.N // group_size
            if n_groups < 1:
                # Can't coarse-grain further; repeat last valid scale
                n_groups = 1
                group_size = self.N

            # Coarse-grain: sum spikes within each group per timestep
            usable = n_groups * group_size
            reshaped = data[:, :usable].reshape(T, n_groups, group_size)
            group_activity = reshaped.sum(axis=2).astype(np.float64)
            # group_activity shape: (T, n_groups)

            # --- Branching ratio ---
            sigma = self._compute_sigma(group_activity, n_groups, k)

            # --- Avalanche exponent ---
            tau = self._compute_avalanche_exponent(group_activity)

            # --- Entropy rate ---
            h = self._compute_entropy_rate(group_activity)

            scale_metrics.append(
                ScaleMetrics(
                    scale=k,
                    n_groups=n_groups,
                    sigma=sigma,
                    avalanche_exponent=tau,
                    entropy_rate=h,
                )
            )

        # Aggregate statistics across scales
        sigmas = np.array([s.sigma for s in scale_metrics])
        sigma_cv = float(np.std(sigmas) / max(np.mean(sigmas), 1e-12))

        taus = [s.avalanche_exponent for s in scale_metrics if s.avalanche_exponent is not None]
        if len(taus) >= 2:
            tau_arr = np.array(taus)
            tau_cv: float | None = float(np.std(tau_arr) / max(np.mean(tau_arr), 1e-12))
        else:
            tau_cv = None

        entropies = np.array([s.entropy_rate for s in scale_metrics])
        entropy_cv = float(np.std(entropies) / max(np.mean(entropies), 1e-12))

        flow_trajectory = [
            (s.sigma, s.avalanche_exponent if s.avalanche_exponent is not None else 0.0, s.entropy_rate)
            for s in scale_metrics
        ]

        return RenormalizationResult(
            scales=scale_metrics,
            sigma_cv=sigma_cv,
            tau_cv=tau_cv,
            entropy_cv=entropy_cv,
            scale_invariant=sigma_cv < 0.1,
            flow_trajectory=flow_trajectory,
            timestamp_step=step,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sigma(
        group_activity: NDArray[np.float64], n_groups: int, scale: int
    ) -> float:
        """Compute branching ratio for a given scale.

        At scale 0 (individual neurons), uses total population activity.
        At higher scales, averages per-group branching ratios for groups
        with sufficient activity.
        """
        if scale == 0:
            pop_activity = group_activity.sum(axis=1)
            try:
                return mr_branching_ratio(pop_activity)
            except ValueError:
                return 1.0

        # Higher scales: per-group branching ratio, averaged
        ratios: list[float] = []
        for g in range(n_groups):
            ts = group_activity[:, g]
            if ts.sum() < 5:
                continue
            try:
                ratios.append(mr_branching_ratio(ts))
            except ValueError:
                continue

        if not ratios:
            # Fallback to population-level
            pop_activity = group_activity.sum(axis=1)
            try:
                return mr_branching_ratio(pop_activity)
            except ValueError:
                return 1.0

        return float(np.mean(ratios))

    @staticmethod
    def _compute_avalanche_exponent(
        group_activity: NDArray[np.float64],
    ) -> float | None:
        """Compute avalanche size distribution exponent.

        Avalanches are defined as consecutive timesteps where total
        population activity exceeds the mean. Size = sum of excess.
        """
        pop = group_activity.sum(axis=1)
        threshold = pop.mean()
        above = pop > threshold

        # Extract avalanche sizes
        sizes: list[float] = []
        current_size = 0.0
        in_avalanche = False
        for t in range(len(pop)):
            if above[t]:
                current_size += pop[t] - threshold
                in_avalanche = True
            else:
                if in_avalanche and current_size > 0:
                    sizes.append(current_size)
                current_size = 0.0
                in_avalanche = False
        # Handle avalanche at end of window
        if in_avalanche and current_size > 0:
            sizes.append(current_size)

        if len(sizes) < 10:
            return None

        sizes_arr = np.array(sizes)
        xmin = float(np.min(sizes_arr[sizes_arr > 0]))
        valid = sizes_arr[sizes_arr >= xmin]
        if len(valid) < 10:
            return None

        try:
            fit = fit_power_law_mle(valid, xmin)
            return fit.alpha
        except ValueError:
            return None

    @staticmethod
    def _compute_entropy_rate(
        group_activity: NDArray[np.float64],
    ) -> float:
        """Compute normalized entropy of group activity distribution.

        Returns
        -------
        float
            Normalized entropy in [0, 1].
        """
        pop = group_activity.sum(axis=1).astype(int)
        max_val = int(pop.max())
        if max_val <= 0:
            return 0.0

        counts = np.bincount(pop, minlength=max_val + 1).astype(np.float64)
        probs = counts / counts.sum()
        probs = probs[probs > 0]
        entropy = -float(np.sum(probs * np.log2(probs)))
        max_entropy = np.log2(max_val + 1)
        if max_entropy <= 0:
            return 0.0
        return float(np.clip(entropy / max_entropy, 0.0, 1.0))
