"""
GammaFieldProbe — measures γ-scaling on 2D reaction-diffusion field trajectories.

Same methodology as BNSynGammaProbe (DNCA) to enable cross-substrate comparison:
  1. Take time series of 2D field snapshots
  2. Compute H0 persistent entropy (pe₀) and Betti number (β₀) per snapshot
  3. Compute Δpe₀, Δβ₀ between consecutive windows
  4. Fit log(Δβ₀) vs log(Δpe₀) via Theil-Sen regression → γ
  5. Bootstrap 95% CI
  6. Control: shuffled field should give γ ≈ 0

Reference: γ_WT = +1.043 (McGuirl et al. 2020 PNAS, zebrafish pigmentation)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class GammaFieldReport:
    """Result of γ-scaling measurement on a 2D field time series."""

    substrate: str          # "gray_scott_activator", "fhn_field", etc.
    gamma: float
    r2: float
    ci_low: float
    ci_high: float
    n_pairs: int
    gamma_wt: float = 1.043   # McGuirl 2020 zebrafish reference

    @property
    def verdict(self) -> str:
        if self.n_pairs < 20:
            return "INSUFFICIENT DATA"
        if self.r2 < 0.1:
            return "INCONCLUSIVE (low R²)"
        if 0.8 < self.gamma < 1.3:
            return "CONSISTENT WITH γ_WT"
        if self.gamma > 0:
            return "ORGANIZED (γ > 0)"
        if self.gamma < 0:
            return "ANTI-ORGANIZED (γ < 0)"
        return "RANDOM (γ ≈ 0)"

    def summary(self) -> str:
        return (
            f"GammaFieldProbe — {self.substrate}\n"
            f"  γ       = {self.gamma:+.3f} CI=[{self.ci_low:+.3f}, {self.ci_high:+.3f}]\n"
            f"  γ_WT    = {self.gamma_wt:+.3f} (McGuirl 2020 zebrafish)\n"
            f"  R²      = {self.r2:.3f}\n"
            f"  n_pairs = {self.n_pairs}\n"
            f"  verdict = {self.verdict}\n"
        )


# ---------------------------------------------------------------------------
#  Cubical TDA helpers (same algorithm as DNCA gamma probe)
# ---------------------------------------------------------------------------

def _count_components(binary: np.ndarray) -> int:
    """Count connected components in a 2D binary array (4-connected BFS)."""
    if binary.sum() == 0:
        return 0

    rows, cols = binary.shape
    labeled = np.zeros_like(binary, dtype=int)
    label = 0

    for r in range(rows):
        for c in range(cols):
            if binary[r, c] > 0 and labeled[r, c] == 0:
                label += 1
                stack = [(r, c)]
                while stack:
                    cr, cc = stack.pop()
                    if (
                        0 <= cr < rows
                        and 0 <= cc < cols
                        and binary[cr, cc] > 0
                        and labeled[cr, cc] == 0
                    ):
                        labeled[cr, cc] = label
                        for nr, nc in (
                            (cr - 1, cc),
                            (cr + 1, cc),
                            (cr, cc - 1),
                            (cr, cc + 1),
                        ):
                            if (
                                0 <= nr < rows
                                and 0 <= nc < cols
                                and labeled[nr, nc] == 0
                            ):
                                stack.append((nr, nc))
    return label


def _approximate_h0(
    image_2d: np.ndarray, n_thresholds: int = 30
) -> List[Tuple[float, float]]:
    """
    Approximate H0 persistent homology without gudhi.

    Uses threshold-based connected component counting:
    at each threshold t, count connected components in (image >= t).
    Birth = threshold where component appears, death = threshold where it merges.
    """
    flat = image_2d.flatten()
    vmin, vmax = float(flat.min()), float(flat.max())
    if vmax - vmin < 1e-10:
        return []

    thresholds = np.linspace(vmin, vmax, n_thresholds)
    prev_count = 0
    pairs: List[Tuple[float, float | None]] = []

    for thresh in thresholds:
        binary = (image_2d >= thresh).astype(np.int32)
        count = _count_components(binary)

        if count > prev_count:
            # New components born
            for _ in range(count - prev_count):
                pairs.append((float(thresh), None))
        elif count < prev_count:
            # Components merged/died — kill most recently born
            for _ in range(prev_count - count):
                for j in range(len(pairs) - 1, -1, -1):
                    if pairs[j][1] is None:
                        pairs[j] = (pairs[j][0], float(thresh))
                        break
        prev_count = count

    # Close remaining open pairs
    for j in range(len(pairs)):
        if pairs[j][1] is None:
            pairs[j] = (pairs[j][0], float(vmax))

    return [(b, d) for b, d in pairs if d is not None and d > b]


def _cubical_tda(image_2d: np.ndarray) -> Tuple[float, int]:
    """
    Compute H0 persistent homology via cubical complex.

    Returns: (pe0, beta0)
      pe0  = H0 persistent entropy = -Σ(l_i/L) log(l_i/L)
      beta0 = number of H0 features
    """
    try:
        import gudhi  # type: ignore[import-untyped]

        cc = gudhi.CubicalComplex(
            dimensions=list(image_2d.shape),
            top_dimensional_cells=image_2d.flatten().tolist(),
        )
        cc.compute_persistence()
        raw_pairs = cc.persistence()
        h0 = [
            (b, d)
            for dim, (b, d) in raw_pairs
            if dim == 0 and d != float("inf")
        ]
    except ImportError:
        h0 = _approximate_h0(image_2d)

    if not h0:
        return 0.0, 0

    lifetimes = [max(1e-12, d - b) for b, d in h0]
    total = sum(lifetimes)
    if total < 1e-10:
        return 0.0, len(h0)

    pe0 = -sum((l / total) * math.log(l / total + 1e-15) for l in lifetimes)
    beta0 = len(h0)
    return pe0, beta0


# ---------------------------------------------------------------------------
#  Regression helpers (identical to DNCA probe)
# ---------------------------------------------------------------------------

def _theil_sen(x: np.ndarray, y: np.ndarray) -> float:
    """Theil-Sen slope estimator (median of pairwise slopes)."""
    n = len(x)
    if n < 2:
        return 0.0

    if n > 100:
        rng = np.random.default_rng(0)
        indices = rng.choice(n, min(n, 200), replace=False)
    else:
        indices = np.arange(n)

    slopes: list[float] = []
    for i in indices:
        for j in indices:
            if i < j and abs(x[j] - x[i]) > 1e-12:
                slopes.append(float((y[j] - y[i]) / (x[j] - x[i])))

    if not slopes:
        return 0.0
    return float(np.median(slopes))


def _pearson_r2(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson R² between two arrays."""
    if len(x) < 3:
        return 0.0
    x_mean = x.mean()
    y_mean = y.mean()
    cov = ((x - x_mean) * (y - y_mean)).sum()
    sx = math.sqrt(max(1e-12, ((x - x_mean) ** 2).sum()))
    sy = math.sqrt(max(1e-12, ((y - y_mean) ** 2).sum()))
    r = cov / (sx * sy) if sx * sy > 1e-12 else 0.0
    return float(r**2)


# ---------------------------------------------------------------------------
#  GammaFieldProbe
# ---------------------------------------------------------------------------

class GammaFieldProbe:
    """Measure γ-scaling on 2D field time series via cubical TDA."""

    def __init__(self, n_bootstrap: int = 200, seed: int = 42):
        self.n_bootstrap = n_bootstrap
        self.seed = seed

    # -- public API ----------------------------------------------------------

    def measure(
        self, fields: NDArray, substrate: str = "field"
    ) -> GammaFieldReport:
        """
        Measure γ on a time series of 2D field snapshots.

        Parameters
        ----------
        fields : NDArray, shape (T, H, W)
            Time series of 2D field snapshots.
        substrate : str
            Label for the substrate.

        Returns
        -------
        GammaFieldReport
        """
        pe0_series, beta0_series = self._compute_tda_series(fields)
        return self._gamma_from_series(pe0_series, beta0_series, substrate)

    def measure_control(
        self, fields: NDArray, substrate: str = "shuffled"
    ) -> GammaFieldReport:
        """
        Measure γ on time-shuffled fields (null model).

        Independently shuffles pe0 and beta0 series to destroy coupling
        while preserving marginal distributions.
        """
        pe0_series, beta0_series = self._compute_tda_series(fields)
        rng = np.random.default_rng(self.seed + 999)
        pe0_series = rng.permutation(pe0_series)
        beta0_series = rng.permutation(beta0_series)
        return self._gamma_from_series(pe0_series, beta0_series, substrate)

    def run_on_engine(
        self,
        engine,  # ReactionDiffusionEngine
        steps: int = 300,
        substrate_label: str = "mfn_activator",
    ) -> tuple[GammaFieldReport, GammaFieldReport]:
        """
        Run complete γ measurement on an MFN+ engine.

        Returns (real_report, control_report).
        """
        engine.initialize_field()
        history, _metrics = engine.simulate(
            steps=steps, turing_enabled=True, return_history=True
        )
        # history shape: (steps, grid_size, grid_size)
        real = self.measure(history, substrate=substrate_label)
        control = self.measure_control(
            history, substrate=f"{substrate_label}_shuffled"
        )
        return real, control

    # -- internals -----------------------------------------------------------

    def _compute_tda_series(
        self, fields: NDArray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute pe0 and beta0 for each 2D snapshot in the time series."""
        n_frames = fields.shape[0]
        pe0_series = np.zeros(n_frames)
        beta0_series = np.zeros(n_frames, dtype=int)

        for i in range(n_frames):
            pe0, beta0 = _cubical_tda(fields[i])
            pe0_series[i] = pe0
            beta0_series[i] = beta0

        return pe0_series, beta0_series

    def _gamma_from_series(
        self,
        pe0_series: np.ndarray,
        beta0_series: np.ndarray,
        substrate: str,
    ) -> GammaFieldReport:
        """Compute γ from TDA series via Theil-Sen on log-deltas."""
        n = len(pe0_series)
        if n < 2:
            return GammaFieldReport(
                substrate=substrate,
                gamma=0.0,
                r2=0.0,
                ci_low=0.0,
                ci_high=0.0,
                n_pairs=0,
            )

        # Compute deltas between consecutive frames
        delta_pe0 = np.abs(np.diff(pe0_series))
        delta_beta0 = np.abs(np.diff(beta0_series.astype(float))) + 1.0

        # Filter: keep only meaningful deltas
        mask = (delta_pe0 > 1e-6) & (delta_beta0 > 1e-6)
        delta_pe0 = delta_pe0[mask]
        delta_beta0 = delta_beta0[mask]

        n_pairs = len(delta_pe0)
        if n_pairs < 5:
            return GammaFieldReport(
                substrate=substrate,
                gamma=0.0,
                r2=0.0,
                ci_low=0.0,
                ci_high=0.0,
                n_pairs=n_pairs,
            )

        log_dpe0 = np.log(delta_pe0)
        log_dbeta0 = np.log(delta_beta0)

        # Theil-Sen regression: log(Δpe0) vs log(Δβ0)
        gamma = _theil_sen(log_dbeta0, log_dpe0)
        r2 = _pearson_r2(log_dbeta0, log_dpe0)

        # Bootstrap CI
        rng = np.random.default_rng(self.seed)
        gammas_boot: list[float] = []
        for _ in range(self.n_bootstrap):
            idx = rng.choice(n_pairs, n_pairs, replace=True)
            g = _theil_sen(log_dbeta0[idx], log_dpe0[idx])
            gammas_boot.append(g)

        ci_low = float(np.percentile(gammas_boot, 2.5))
        ci_high = float(np.percentile(gammas_boot, 97.5))

        return GammaFieldReport(
            substrate=substrate,
            gamma=gamma,
            r2=r2,
            ci_low=ci_low,
            ci_high=ci_high,
            n_pairs=n_pairs,
        )
