"""
BNSynGammaProbe — measures γ-scaling on DNCA internal state trajectories.

Hypothesis (Vasylenko-Levin-Tononi):
  γ is a substrate-specific candidate marker of organized systems
  (see docs/CLAIM_BOUNDARY.md §2; substrate-independence was
  empirically contradicted by the HRV n=5 pilot, γ mean 0.50 ± 0.44).
  γ_WT = +1.043 was measured on McGuirl 2020 zebrafish pigmentation
  density fields using cubical persistent homology.

Method:
  1. Collect DNCA internal state trajectory (1000 steps)
  2. Convert to 2D density snapshots via sliding window
  3. Compute H0 persistent entropy (pe₀) and Betti number (β₀) per snapshot
  4. Compute Δpe₀, Δβ₀ between consecutive windows
  5. Fit log(Δpe₀) vs log(Δβ₀) via Theil-Sen regression → γ
  6. Bootstrap 95% CI

Two measurement approaches:
  A: NMO activity field — shape [window, 6] per snapshot
  B: Prediction error field — shape [window, spatial] per snapshot

Control: shuffled trajectory should give γ ≈ 0.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch


@dataclass
class GammaReport:
    """Result of γ-scaling measurement."""
    approach: str
    gamma: float
    r2: float
    ci_low: float
    ci_high: float
    n_pairs: int
    gamma_wt: float = 1.043

    @property
    def verdict(self) -> str:
        if self.n_pairs < 20:
            return "INSUFFICIENT DATA"
        if self.r2 < 0.1:
            return "INCONCLUSIVE (low R²)"
        if 0.8 < self.gamma < 1.3:
            return "CONSISTENT WITH γ_WT"
        if self.gamma > 0:
            return "ORGANIZED (γ > 0, different scale)"
        if self.gamma < 0:
            return "ANTI-ORGANIZED (γ < 0)"
        return "RANDOM (γ ≈ 0)"

    def summary(self) -> str:
        return (
            f"BNSynGammaProbe — {self.approach}\n"
            f"  γ_DNCA  = {self.gamma:+.3f} "
            f"CI=[{self.ci_low:+.3f}, {self.ci_high:+.3f}]\n"
            f"  γ_WT    = {self.gamma_wt:+.3f} (McGuirl 2020 zebrafish)\n"
            f"  R²      = {self.r2:.3f}\n"
            f"  n_pairs = {self.n_pairs}\n"
            f"  verdict = {self.verdict}\n"
        )


def _cubical_tda(image_2d: np.ndarray) -> Tuple[float, int]:
    """
    Compute H0 persistent homology via cubical complex.

    Returns: (pe0, beta0)
      pe0  = H0 persistent entropy = -Σ(l_i/L) log(l_i/L)
      beta0 = number of H0 features
    """
    try:
        import gudhi
        cc = gudhi.CubicalComplex(
            dimensions=list(image_2d.shape),
            top_dimensional_cells=image_2d.flatten().tolist(),
        )
        cc.compute_persistence()
        pairs = cc.persistence()
        h0 = [(b, d) for dim, (b, d) in pairs if dim == 0 and d != float("inf")]
    except ImportError:
        # Fallback: approximate TDA via connected components at multiple thresholds
        h0 = _approximate_h0(image_2d)

    if not h0:
        return 0.0, 0

    lifetimes = [max(1e-12, d - b) for b, d in h0]
    L = sum(lifetimes)
    if L < 1e-10:
        return 0.0, len(h0)

    pe0 = -sum((l / L) * math.log(l / L + 1e-12) for l in lifetimes)
    beta0 = len(h0)
    return pe0, beta0


def _approximate_h0(image_2d: np.ndarray, n_thresholds: int = 30) -> List[Tuple[float, float]]:
    """
    Approximate H0 persistent homology without gudhi.

    Uses threshold-based connected component counting:
    at each threshold t, count connected components in (image > t).
    Birth = threshold where component appears, death = threshold where it merges.
    """
    flat = image_2d.flatten()
    vmin, vmax = float(flat.min()), float(flat.max())
    if vmax - vmin < 1e-10:
        return []

    thresholds = np.linspace(vmin, vmax, n_thresholds)
    prev_count = 0
    births: List[float] = []
    features: List[Tuple[float, float]] = []

    for t in thresholds:
        binary = (image_2d > t).astype(np.int32)
        count = _count_components(binary)

        # New components born
        if count > prev_count:
            for _ in range(count - prev_count):
                births.append(float(t))
        # Components merged (died)
        elif count < prev_count:
            for _ in range(prev_count - count):
                if births:
                    b = births.pop(0)
                    features.append((b, float(t)))
        prev_count = count

    # Remaining births die at max threshold
    for b in births:
        features.append((b, float(vmax)))

    return features


def _count_components(binary: np.ndarray) -> int:
    """Count connected components in a 2D binary array (4-connected)."""
    if binary.sum() == 0:
        return 0

    labeled = np.zeros_like(binary, dtype=int)
    label = 0
    rows, cols = binary.shape

    for r in range(rows):
        for c in range(cols):
            if binary[r, c] > 0 and labeled[r, c] == 0:
                label += 1
                # BFS flood fill
                stack = [(r, c)]
                while stack:
                    cr, cc_ = stack.pop()
                    if 0 <= cr < rows and 0 <= cc_ < cols and binary[cr, cc_] > 0 and labeled[cr, cc_] == 0:
                        labeled[cr, cc_] = label
                        for nr, nc in ((cr - 1, cc_), (cr + 1, cc_), (cr, cc_ - 1), (cr, cc_ + 1)):
                            if 0 <= nr < rows and 0 <= nc < cols and labeled[nr, nc] == 0:
                                stack.append((nr, nc))

    return label


def _theil_sen(x: np.ndarray, y: np.ndarray) -> float:
    """Theil-Sen slope estimator (median of pairwise slopes)."""
    n = len(x)
    if n < 2:
        return 0.0
    slopes = []
    # Sample pairwise slopes (cap at 5000 pairs for speed)
    if n > 100:
        indices = np.random.choice(n, min(n, 200), replace=False)
    else:
        indices = np.arange(n)
    for i in indices:
        for j in indices:
            if i < j and abs(x[j] - x[i]) > 1e-12:
                slopes.append((y[j] - y[i]) / (x[j] - x[i]))
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
    return float(r ** 2)


class BNSynGammaProbe:
    """
    Measures γ-scaling on DNCA internal trajectories.

    Hypothesis: γ is a substrate-specific candidate marker of organized systems.
    Reference: γ_WT = +1.043 (McGuirl et al. 2020 PNAS, zebrafish pigmentation)
    Method: TDA-calibrated space log(Δpe₀) vs log(Δβ₀), Theil-Sen regression
    """

    def __init__(self, window_size: int = 50, n_bootstrap: int = 500, seed: int = 42):
        self.window_size = window_size
        self.n_bootstrap = n_bootstrap
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def collect_trajectory(
        self,
        dnca: Any,
        n_steps: int = 1000,
        noise_level: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """Run DNCA and collect internal state trajectory."""
        state_dim = dnca.state_dim
        pattern = torch.sin(torch.arange(state_dim, dtype=torch.float32) * 0.3) * 0.5

        trajectory: List[Dict[str, Any]] = []
        for step in range(n_steps):
            obs = pattern + torch.randn(state_dim) * noise_level
            # Vary input regime periodically to create richer dynamics
            if step % 200 < 30:
                obs = obs * 2.0 + torch.randn(state_dim) * 0.3
            out = dnca.step(obs, reward=0.01 * math.sin(step * 0.05))

            trajectory.append({
                "step": step,
                "nmo_activities": np.array([out.all_activities[k] for k in sorted(out.all_activities.keys())]),
                "r_order": out.r_order,
                "mismatch": out.mismatch,
                "dominant_nmo": out.dominant_nmo,
                "prediction_error": dnca.sps.prediction_error.detach().cpu().numpy().copy(),
            })

        return trajectory

    def trajectory_to_images_nmo(self, trajectory: List[Dict]) -> np.ndarray:
        """
        Convert trajectory to NMO activity density images.
        Shape: [n_windows, window_size, n_nmo]
        """
        W = self.window_size
        n = len(trajectory)
        if n < W + 1:
            return np.empty((0, W, 6))

        n_windows = n - W
        activities = np.array([t["nmo_activities"] for t in trajectory])

        # Normalize to [0, 1]
        amin = activities.min(axis=0, keepdims=True)
        amax = activities.max(axis=0, keepdims=True)
        rng = amax - amin
        rng[rng < 1e-10] = 1.0
        activities = (activities - amin) / rng

        images = np.zeros((n_windows, W, activities.shape[1]))
        for i in range(n_windows):
            images[i] = activities[i:i + W]

        return images

    def trajectory_to_images_prediction_error(
        self, trajectory: List[Dict], spatial_size: int = 50,
    ) -> np.ndarray:
        """
        Convert trajectory to prediction error density images.
        Shape: [n_windows, window_size, spatial_size]
        """
        W = self.window_size
        n = len(trajectory)
        if n < W + 1:
            return np.empty((0, W, spatial_size))

        n_windows = n - W
        raw_pe = np.array([t["prediction_error"] for t in trajectory])
        state_dim = raw_pe.shape[1]

        # Subsample or pad to spatial_size
        if state_dim >= spatial_size:
            indices = np.linspace(0, state_dim - 1, spatial_size, dtype=int)
            pe = raw_pe[:, indices]
        else:
            pe = np.zeros((n, spatial_size))
            pe[:, :state_dim] = raw_pe

        # Normalize to [0, 1]
        pmin = pe.min()
        pmax = pe.max()
        rng = pmax - pmin
        if rng < 1e-10:
            rng = 1.0
        pe = (pe - pmin) / rng

        images = np.zeros((n_windows, W, spatial_size))
        for i in range(n_windows):
            images[i] = pe[i:i + W]

        return images

    def compute_tda_series(self, images: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute H0 persistent entropy and Betti-0 for each image."""
        n = images.shape[0]
        pe0_series = np.zeros(n)
        beta0_series = np.zeros(n, dtype=int)

        for i in range(n):
            pe0, beta0 = _cubical_tda(images[i])
            pe0_series[i] = pe0
            beta0_series[i] = beta0

        return pe0_series, beta0_series

    def compute_gamma(
        self,
        pe0_series: np.ndarray,
        beta0_series: np.ndarray,
        approach: str = "nmo_activity",
    ) -> GammaReport:
        """Compute γ from TDA series via Theil-Sen on log-deltas."""
        n = len(pe0_series)
        if n < 2:
            return GammaReport(approach=approach, gamma=0.0, r2=0.0, ci_low=0.0, ci_high=0.0, n_pairs=0)

        # Compute deltas between consecutive windows
        delta_pe0 = np.abs(np.diff(pe0_series))
        delta_beta0 = np.abs(np.diff(beta0_series.astype(float))) + 1.0  # +1 to avoid log(0)

        # Filter: keep only meaningful deltas
        mask = (delta_pe0 > 1e-6) & (delta_beta0 > 1e-6)
        delta_pe0 = delta_pe0[mask]
        delta_beta0 = delta_beta0[mask]

        if len(delta_pe0) < 5:
            return GammaReport(approach=approach, gamma=0.0, r2=0.0, ci_low=0.0, ci_high=0.0, n_pairs=len(delta_pe0))

        log_dpe0 = np.log(delta_pe0)
        log_dbeta0 = np.log(delta_beta0)

        # Theil-Sen regression
        gamma = _theil_sen(log_dbeta0, log_dpe0)
        r2 = _pearson_r2(log_dbeta0, log_dpe0)

        # Bootstrap CI
        n_pts = len(log_dpe0)
        gammas_boot = []
        for _ in range(self.n_bootstrap):
            idx = np.random.choice(n_pts, n_pts, replace=True)
            g = _theil_sen(log_dbeta0[idx], log_dpe0[idx])
            gammas_boot.append(g)

        ci_low = float(np.percentile(gammas_boot, 2.5))
        ci_high = float(np.percentile(gammas_boot, 97.5))

        return GammaReport(
            approach=approach,
            gamma=gamma,
            r2=r2,
            ci_low=ci_low,
            ci_high=ci_high,
            n_pairs=n_pts,
        )

    def compute_gamma_random_baseline(self, trajectory: List[Dict]) -> GammaReport:
        """
        Null model: compute TDA on original images, then shuffle the pe0
        and beta0 series *independently* before computing γ.

        Shuffling the trajectory alone preserves per-window structure and
        global normalization, so sliding-window correlations survive and
        γ stays far from 0.  Independently permuting the two TDA series
        destroys the pe0-β0 coupling, which is the actual source of γ.
        """
        images = self.trajectory_to_images_nmo(trajectory)
        if images.shape[0] == 0:
            return GammaReport(approach="random_baseline", gamma=0.0, r2=0.0, ci_low=0.0, ci_high=0.0, n_pairs=0)
        pe0, beta0 = self.compute_tda_series(images)
        # Independently shuffle each series to destroy coupling
        rng = np.random.default_rng(42)
        pe0 = rng.permutation(pe0)
        beta0 = rng.permutation(beta0)
        return self.compute_gamma(pe0, beta0, approach="random_baseline")

    def run(self, dnca: Any, n_steps: int = 1000) -> Tuple[GammaReport, GammaReport, GammaReport]:
        """
        Run full γ-scaling probe.
        Returns: (nmo_report, pe_report, random_baseline_report)
        """
        trajectory = self.collect_trajectory(dnca, n_steps=n_steps)

        # Approach A: NMO activity field
        images_nmo = self.trajectory_to_images_nmo(trajectory)
        pe0_nmo, beta0_nmo = self.compute_tda_series(images_nmo)
        nmo_report = self.compute_gamma(pe0_nmo, beta0_nmo, approach="nmo_activity")

        # Approach B: Prediction error field
        images_pe = self.trajectory_to_images_prediction_error(trajectory)
        pe0_pe, beta0_pe = self.compute_tda_series(images_pe)
        pe_report = self.compute_gamma(pe0_pe, beta0_pe, approach="prediction_error")

        # Control: random baseline
        random_report = self.compute_gamma_random_baseline(trajectory)

        return nmo_report, pe_report, random_report
