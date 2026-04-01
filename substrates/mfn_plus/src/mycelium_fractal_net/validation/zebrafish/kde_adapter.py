"""KDE Density Field Adapter for McGuirl 2020 zebrafish cell coordinates.

Converts cell point coordinates -> smooth density field [0,1].
Density field then goes directly into compute_tda() �� no additional processing.

Pipeline:
  cell_coords (N x 2) -> KDE -> density_field (grid x grid) -> compute_tda -> TopologicalSignature

Why KDE, not binarization:
  Binarization loses topological information about component sizes (lifetimes).
  KDE preserves continuous landscape -> persistent homology correctly computes beta_0, pe_0.

# APPROXIMATION: bandwidth chosen via Silverman rule (Silverman 1986).
# Bandwidth calibration on real McGuirl data — TODO(nfi-v2).
# Ref: McGuirl et al. (2020) PNAS 117:5217. DOI: 10.1073/pnas.1917763117
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

__all__ = ["CellDensityAdapter", "KDEConfig"]


@dataclass(frozen=True)
class KDEConfig:
    grid_size: int = 128
    bandwidth: float | None = None  # None -> Silverman rule
    normalize: bool = True
    clip_percentile: float = 99.0


class CellDensityAdapter:
    """Convert McGuirl cell coordinates or images to density field for TDA.

    Two input formats:
      FORMAT_A: np.ndarray shape (N, 2) — cell coordinates (x, y) in pixels
      FORMAT_B: np.ndarray shape (H, W) — intensity image (already a field)

    compute_density_field() auto-detects format by shape.
    """

    def __init__(self, config: KDEConfig | None = None) -> None:
        self.config = config or KDEConfig()

    def compute_density_field(self, data: np.ndarray) -> np.ndarray:
        """Return np.ndarray shape (grid_size, grid_size) in [0, 1]."""
        data = np.asarray(data, dtype=np.float64)

        if data.ndim == 2 and data.shape[1] == 2 and data.shape[0] > 2:
            return self._kde_from_coordinates(data)
        elif data.ndim == 2:
            return self._normalize_image(data)
        elif data.ndim == 3:
            return self._normalize_image(data.mean(axis=-1))
        else:
            raise ValueError(f"Unexpected data shape: {data.shape}")

    def _kde_from_coordinates(self, coords: np.ndarray) -> np.ndarray:
        """Gaussian KDE on grid_size x grid_size grid.

        Bandwidth: Silverman rule h = 1.06 * sigma * N^(-1/5)
        # APPROXIMATION: isotropic bandwidth — real pigmentation is anisotropic.
        """
        N = len(coords)
        G = self.config.grid_size

        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        x_range = max(x_max - x_min, 1e-6)
        y_range = max(y_max - y_min, 1e-6)

        x_norm = (coords[:, 0] - x_min) / x_range * (G - 1)
        y_norm = (coords[:, 1] - y_min) / y_range * (G - 1)

        if self.config.bandwidth is not None:
            bw = self.config.bandwidth
        else:
            sigma = (np.std(x_norm) + np.std(y_norm)) / 2 + 1e-6
            bw = 1.06 * sigma * (N ** (-0.2))
            bw = np.clip(bw, 1.0, G / 4)

        gx, gy = np.meshgrid(np.arange(G), np.arange(G), indexing="ij")
        density = np.zeros((G, G))
        chunk = 500
        for i in range(0, N, chunk):
            xc = x_norm[i : i + chunk]
            yc = y_norm[i : i + chunk]
            dx = gx[np.newaxis, :, :] - xc[:, np.newaxis, np.newaxis]
            dy = gy[np.newaxis, :, :] - yc[:, np.newaxis, np.newaxis]
            density += np.exp(-0.5 * (dx**2 + dy**2) / (bw**2)).sum(axis=0)

        return self._normalize_image(density)

    def _normalize_image(self, arr: np.ndarray) -> np.ndarray:
        """Clip outliers, resize if needed, normalize to [0, 1]."""
        G = self.config.grid_size
        if arr.shape[0] != G or arr.shape[1] != G:
            from scipy.ndimage import zoom

            arr = zoom(arr, (G / arr.shape[0], G / arr.shape[1]), order=1)

        if not self.config.normalize:
            return arr.copy()

        p_hi = np.percentile(arr, self.config.clip_percentile)
        arr = np.clip(arr, 0.0, p_hi)
        lo, hi = arr.min(), arr.max()
        if hi > lo:
            return (arr - lo) / (hi - lo)
        warnings.warn("Constant density field after normalization.", stacklevel=2)
        return np.zeros_like(arr)
