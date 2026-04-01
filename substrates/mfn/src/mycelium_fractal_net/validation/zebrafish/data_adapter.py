"""Adapter: external data (image/numpy/.mat) -> FieldSequence.

Three modes:
  1. SYNTHETIC: list[np.ndarray] -> list[FieldSequence]
  2. REAL .mat: McGuirl 2020 agent-based cell coordinates -> density field
     Format: cellsM (melanophores), cellsId/Il (iridophores), numMel, etc.
     Ref: github.com/sandstede-lab/Quantifying_Zebrafish_Patterns
  3. REAL .npz: image arrays (future)

# ASSUMPTION: external fields have shape (H, W) with values in [0, 1].
# If not [0, 1] — automatic normalisation with warning.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec

__all__ = ["AdapterConfig", "ZebrafishFieldAdapter"]


@dataclass(frozen=True)
class AdapterConfig:
    target_grid_size: int = 128
    normalize: bool = True
    label: str = "external"


class ZebrafishFieldAdapter:
    """Convert zebrafish pigmentation data to FieldSequence.

    Supports McGuirl 2020 .mat files (cell coordinates -> density field via KDE)
    and raw numpy arrays.
    Ref: github.com/sandstede-lab/Quantifying_Zebrafish_Patterns
    """

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self.config = config or AdapterConfig()

    def from_arrays(
        self,
        arrays: list[np.ndarray],
        phenotype: str = "unknown",
        seed: int = 0,
    ) -> list[FieldSequence]:
        """Convert list of 2D arrays to list of FieldSequence."""
        sequences: list[FieldSequence] = []
        for i, arr in enumerate(arrays):
            processed = self._process_field(arr, i)

            if i == 0:
                history = processed[np.newaxis, :, :]
            else:
                prev = sequences[-1].history
                history = np.concatenate(
                    [prev, processed[np.newaxis, :, :]], axis=0
                )

            spec = SimulationSpec(
                grid_size=processed.shape[0],
                steps=i + 1,
                seed=seed,
            )

            seq = FieldSequence(
                field=processed,
                history=history,
                spec=spec,
                metadata={
                    "source": "zebrafish_synthetic_proxy",
                    "phenotype": phenotype,
                    "timepoint": i,
                    "label_real": False,  # SYNTHETIC_PROXY
                    "ref": "McGuirl et al. (2020) PNAS 10.1073/pnas.1917038117",
                },
            )
            sequences.append(seq)

        return sequences

    def from_npz(
        self, path: Path, phenotype: str = "wild_type"
    ) -> list[FieldSequence]:
        """Load real McGuirl 2020 data from NPZ file.

        # TODO(nfi-v2): activate after download from Zenodo 3569843.
        """
        if not path.exists():
            raise FileNotFoundError(
                f"McGuirl 2020 data not found at {path}.\n"
                "Download from: https://zenodo.org/record/3569843\n"
                "Set MCGUIRL_DATA_PATH env variable or pass path explicitly.\n"
                "# TODO(nfi-v2): implement auto-download."
            )

        data = np.load(path, allow_pickle=True)
        if "images" in data:
            arrays = [data["images"][i] for i in range(len(data["images"]))]
        elif "image" in data:
            arrays = [data["image"]]
        else:
            raise KeyError(
                f"Expected 'images' or 'image' key in {path}. "
                f"Found: {list(data.keys())}"
            )

        return self.from_arrays(arrays, phenotype=phenotype)

    def from_mat(
        self,
        path: Path,
        phenotype: str = "wild_type",
        cell_key: str = "cellsM",
        num_key: str = "numMel",
        timepoints: list[int] | None = None,
        kde_sigma: float = 2.0,
    ) -> list[FieldSequence]:
        """Load McGuirl 2020 .mat file: cell coordinates -> density field.

        The .mat files contain agent-based simulation output:
          cellsM[i, :, t] = (x, y) of melanophore i at timepoint t
          numMel[t] = number of active melanophores at timepoint t

        We convert cell coordinates to a 2D density field via:
          1. histogram2d on (x, y) coordinates
          2. Gaussian smoothing (sigma=kde_sigma)
          3. Normalize to [0, 1]

        Args:
            path: path to .mat file
            phenotype: "wild_type", "mutant", etc.
            cell_key: key for cell coordinate array (cellsM, cellsId, etc.)
            num_key: key for active cell count (numMel, numIrid, etc.)
            timepoints: which timepoints to extract (default: 10 evenly spaced)
            kde_sigma: Gaussian smoothing sigma for density estimation

        Ref: github.com/sandstede-lab/Quantifying_Zebrafish_Patterns
        """
        import scipy.io as sio
        from scipy.ndimage import gaussian_filter

        if not path.exists():
            raise FileNotFoundError(
                f"McGuirl 2020 .mat file not found at {path}.\n"
                "Download from: github.com/sandstede-lab/"
                "Quantifying_Zebrafish_Patterns/data/sample_inputs/"
            )

        mat = sio.loadmat(str(path))
        cells = mat[cell_key]   # (max_cells, 2, n_timepoints)
        nums = mat[num_key].flatten()  # (n_timepoints,)
        n_total = cells.shape[2]

        if timepoints is None:
            # Take 20 evenly spaced timepoints from the second half
            # (early timepoints have few cells, not informative)
            start = n_total // 2
            indices = np.linspace(start, n_total - 1, 20, dtype=int)
            timepoints = indices.tolist()

        grid = self.config.target_grid_size
        arrays: list[np.ndarray] = []

        for t in timepoints:
            n = int(nums[t])
            if n < 3:
                arrays.append(np.zeros((grid, grid), dtype=np.float64))
                continue

            coords = cells[:n, :, t]  # (n, 2)
            x, y = coords[:, 0], coords[:, 1]

            # Build density field via histogram2d + Gaussian smoothing
            xedge = np.linspace(x.min() - 50, x.max() + 50, grid + 1)
            yedge = np.linspace(y.min() - 50, y.max() + 50, grid + 1)
            H, _, _ = np.histogram2d(x, y, bins=[xedge, yedge])
            H = gaussian_filter(H, sigma=kde_sigma)
            mx = H.max()
            if mx > 0:
                H = H / mx
            arrays.append(H)

        # Use from_arrays but override metadata for real data
        sequences = self.from_arrays(arrays, phenotype=phenotype, seed=0)
        # Patch metadata to mark as real
        patched: list[FieldSequence] = []
        for i, seq in enumerate(sequences):
            meta = dict(seq.metadata) if seq.metadata else {}
            meta["source"] = "mcguirl2020_mat"
            meta["label_real"] = True
            meta["mat_file"] = str(path.name)
            meta["cell_key"] = cell_key
            meta["timepoint_index"] = timepoints[i]
            meta["ref"] = (
                "McGuirl et al. (2020) PNAS 117(10):5217-5224. "
                "DOI: 10.1073/pnas.1917763117"
            )
            patched.append(FieldSequence(
                field=seq.field,
                history=seq.history,
                spec=seq.spec,
                metadata=meta,
            ))
        return patched

    def from_mat_composite(
        self,
        path: Path,
        phenotype: str = "wild_type",
        cell_keys: list[str] | None = None,
        num_keys: list[str] | None = None,
        timepoints: list[int] | None = None,
        kde_sigma: float = 4.0,
    ) -> list[FieldSequence]:
        """Load McGuirl 2020 .mat: composite multi-cell-type density field.

        Combines multiple cell types (melanophores + iridophores by default)
        into a single density field for richer topological signature.
        Uses FULL temporal range for maximum variation.

        Ref: github.com/sandstede-lab/Quantifying_Zebrafish_Patterns
        """
        import scipy.io as sio
        from scipy.ndimage import gaussian_filter

        if not path.exists():
            raise FileNotFoundError(f"Not found: {path}")

        mat = sio.loadmat(str(path))

        if cell_keys is None:
            cell_keys = ["cellsM", "cellsId"]
        if num_keys is None:
            num_keys = ["numMel", "numIrid"]

        # Filter to keys actually present in this file with nonzero cells
        valid_pairs = []
        for ck, nk in zip(cell_keys, num_keys):
            if ck in mat and nk in mat:
                nums = mat[nk].flatten()
                if nums.max() > 0:
                    valid_pairs.append((ck, nk))

        if not valid_pairs:
            raise ValueError(
                f"No valid cell types in {path.name}. "
                f"Tried: {list(zip(cell_keys, num_keys))}"
            )

        n_total = mat[valid_pairs[0][1]].flatten().shape[0]

        if timepoints is None:
            # Full range, every 2nd timepoint
            timepoints = list(range(0, n_total, 2))

        grid = self.config.target_grid_size
        arrays: list[np.ndarray] = []

        for t in timepoints:
            all_coords: list[np.ndarray] = []
            for ck, nk in valid_pairs:
                n = int(mat[nk].flatten()[t])
                if n > 0:
                    all_coords.append(mat[ck][:n, :, t])

            if not all_coords or sum(len(c) for c in all_coords) < 3:
                arrays.append(np.zeros((grid, grid), dtype=np.float64))
                continue

            coords = np.vstack(all_coords)
            x, y = coords[:, 0], coords[:, 1]
            xedge = np.linspace(x.min() - 50, x.max() + 50, grid + 1)
            yedge = np.linspace(y.min() - 50, y.max() + 50, grid + 1)
            H, _, _ = np.histogram2d(x, y, bins=[xedge, yedge])
            H = gaussian_filter(H, sigma=kde_sigma)
            mx = H.max()
            if mx > 0:
                H = H / mx
            arrays.append(H)

        sequences = self.from_arrays(arrays, phenotype=phenotype, seed=0)
        patched: list[FieldSequence] = []
        for i, seq in enumerate(sequences):
            meta = dict(seq.metadata) if seq.metadata else {}
            meta["source"] = "mcguirl2020_mat_composite"
            meta["label_real"] = True
            meta["mat_file"] = str(path.name)
            meta["cell_keys"] = [ck for ck, _ in valid_pairs]
            meta["timepoint_index"] = timepoints[i]
            meta["ref"] = (
                "McGuirl et al. (2020) PNAS 117(10):5217-5224. "
                "DOI: 10.1073/pnas.1917763117"
            )
            patched.append(
                FieldSequence(
                    field=seq.field,
                    history=seq.history,
                    spec=seq.spec,
                    metadata=meta,
                )
            )
        return patched

    def _process_field(self, arr: np.ndarray, idx: int) -> np.ndarray:
        """Normalize, resize if needed, validate shape."""
        arr = np.asarray(arr, dtype=np.float64)

        # Flatten multichannel (RGB -> grayscale mean)
        if arr.ndim == 3:
            arr = arr.mean(axis=-1)

        if arr.ndim != 2:
            raise ValueError(
                f"Expected 2D field at timepoint {idx}, got shape {arr.shape}"
            )

        target = self.config.target_grid_size
        if arr.shape[0] != target or arr.shape[1] != target:
            arr = self._resize(arr, target)

        if self.config.normalize:
            lo, hi = arr.min(), arr.max()
            if hi > lo:
                arr = (arr - lo) / (hi - lo)
            elif arr.max() > 1.0 or arr.min() < 0.0:
                warnings.warn(
                    f"Field at timepoint {idx} outside [0,1] and constant — clipping.",
                    stacklevel=2,
                )
                arr = np.clip(arr, 0.0, 1.0)

        return arr

    def _resize(self, arr: np.ndarray, target: int) -> np.ndarray:
        """Resize via scipy zoom (no PIL dependency).

        # APPROXIMATION: bilinear interpolation via scipy.ndimage.zoom.
        """
        from scipy.ndimage import zoom

        h, w = arr.shape
        return zoom(arr, (target / h, target / w), order=1)
