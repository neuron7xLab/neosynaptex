"""Input adapter for external field data.

Converts raw arrays, .npy files, and .csv files into FieldSequence
objects that can be passed directly to the MFN pipeline.

Usage:
    from mycelium_fractal_net.adapters import FieldAdapter

    seq = FieldAdapter.load("data.npy")
    seq.detect()
    seq.explain()
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Union

import numpy as np

from mycelium_fractal_net.core.reaction_diffusion_config import FIELD_V_MAX, FIELD_V_MIN
from mycelium_fractal_net.types.field import FieldSequence

if TYPE_CHECKING:
    from numpy.typing import NDArray



__all__ = ['FieldAdapter']

class FieldAdapter:
    """Load and validate external data into FieldSequence.

    Accepts numpy arrays, .npy files, and .csv files.
    Validates finiteness, shape, dtype, and normalizes to
    biophysical range if needed.
    """

    @staticmethod
    def load(
        source: Union[np.ndarray, str, Path],
        *,
        normalize: bool = True,
    ) -> FieldSequence:
        """Load external data into a FieldSequence.

        Parameters
        ----------
        source : np.ndarray | str | Path
            - ndarray shape (H, W): single field frame
            - ndarray shape (T, H, W): field with history
            - str/Path to .npy file
            - str/Path to .csv file (loaded as 2D array)
        normalize : bool
            If True and data is outside [V_min, V_max], rescale
            to biophysical range. If False, reject out-of-range data.

        Returns
        -------
        FieldSequence
            Ready for pipeline: seq.detect(), seq.extract(), etc.

        Raises
        ------
        ValueError
            If data is not finite, wrong shape, or out of range
            (when normalize=False).
        FileNotFoundError
            If file path does not exist.
        """
        arr = FieldAdapter._to_array(source)
        arr = FieldAdapter._validate(arr)
        arr = FieldAdapter._normalize(arr, normalize)
        return FieldAdapter._to_sequence(arr)

    @staticmethod
    def _to_array(source: Union[np.ndarray, str, Path]) -> NDArray[np.float64]:
        if isinstance(source, np.ndarray):
            return source.astype(np.float64, copy=True)

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        if path.suffix == ".npy":
            arr: NDArray[np.float64] = np.load(path).astype(np.float64)
            return arr
        elif path.suffix == ".csv":
            arr = np.loadtxt(path, delimiter=",", dtype=np.float64)
            return np.asarray(arr, dtype=np.float64)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}. Use .npy or .csv")

    @staticmethod
    def _validate(arr: NDArray[np.float64]) -> NDArray[np.float64]:
        if arr.ndim < 2:
            raise ValueError(f"Data must be at least 2D, got {arr.ndim}D with shape {arr.shape}")
        if arr.ndim > 3:
            raise ValueError(f"Data must be 2D or 3D, got {arr.ndim}D with shape {arr.shape}")
        if not np.isfinite(arr).all():
            nan_count = int(np.sum(np.isnan(arr)))
            inf_count = int(np.sum(np.isinf(arr)))
            raise ValueError(
                f"Data contains non-finite values: {nan_count} NaN, {inf_count} Inf. "
                f"Clean the data before loading."
            )
        spatial = arr.shape[-2:]
        if spatial[0] < 2 or spatial[1] < 2:
            raise ValueError(f"Spatial dimensions must be >= 2x2, got {spatial}")
        return arr

    @staticmethod
    def _normalize(arr: NDArray[np.float64], normalize: bool) -> NDArray[np.float64]:
        dmin, dmax = float(arr.min()), float(arr.max())
        in_range = dmin >= FIELD_V_MIN and dmax <= FIELD_V_MAX

        if in_range:
            return arr

        if not normalize:
            raise ValueError(
                f"Data range [{dmin:.4f}, {dmax:.4f}] outside biophysical bounds "
                f"[{FIELD_V_MIN}, {FIELD_V_MAX}]. Set normalize=True to auto-rescale."
            )

        # Linear rescale to [V_min, V_max]
        data_range = dmax - dmin
        if data_range < 1e-12:
            return np.full_like(arr, (FIELD_V_MIN + FIELD_V_MAX) / 2)
        scaled = (arr - dmin) / data_range
        return FIELD_V_MIN + scaled * (FIELD_V_MAX - FIELD_V_MIN)

    @staticmethod
    def _to_sequence(arr: NDArray[np.float64]) -> FieldSequence:
        if arr.ndim == 2:
            return FieldSequence(
                field=arr,
                history=None,
                spec=None,
                metadata={"source": "external", "adapter": "FieldAdapter"},
            )
        # 3D: (T, H, W)
        return FieldSequence(
            field=arr[-1].copy(),
            history=arr,
            spec=None,
            metadata={"source": "external", "adapter": "FieldAdapter"},
        )
