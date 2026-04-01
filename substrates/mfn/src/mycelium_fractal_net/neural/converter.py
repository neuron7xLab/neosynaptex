"""Spike-to-field converter: bridge between neural substrate and MFN analytics.

Converts spiking network activity into MFN-native FieldSequence objects,
enabling the full analytics pipeline (TDA, causal emergence, Wasserstein,
Fisher information) to operate on neural data.

Three conversion modes:
  1. rate_field:   Spike rates binned onto a 2D grid (spatial activity map)
  2. voltage_field: Membrane voltages reshaped to 2D grid (instantaneous state)
  3. correlation_field: Pairwise spike correlations as 2D matrix (functional connectivity)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["ConversionMode", "SpikeFieldConverter", "SpikeRaster"]


@dataclass
class SpikeRaster:
    """Spike raster data from a neural simulation."""

    spike_times: NDArray[np.int64]  # step indices
    spike_neurons: NDArray[np.int64]  # neuron indices
    N: int  # total neuron count
    T: int  # total timestep count
    dt_ms: float = 0.5
    voltages: NDArray[np.float64] | None = None  # (T, N) optional

    @property
    def duration_ms(self) -> float:
        return self.T * self.dt_ms

    @property
    def mean_rate_hz(self) -> float:
        if self.T == 0 or self.N == 0:
            return 0.0
        return len(self.spike_times) / self.N / (self.duration_ms / 1000.0)


class ConversionMode:
    RATE = "rate_field"
    VOLTAGE = "voltage_field"
    CORRELATION = "correlation_field"


class SpikeFieldConverter:
    """Convert spike/voltage data into MFN FieldSequence objects.

    This is the critical bridge: it allows all MFN analytics
    (persistent homology, causal emergence, Wasserstein geometry, etc.)
    to operate on spiking neural network data.

    Usage:
        from mycelium_fractal_net.neural import SpikeFieldConverter, SpikeRaster
        import mycelium_fractal_net as mfn

        converter = SpikeFieldConverter(grid_size=16)
        raster = SpikeRaster(spike_times=..., spike_neurons=..., N=256, T=2000)
        seq = converter.to_field_sequence(raster, mode="rate_field")

        # Now use full MFN pipeline
        report = mfn.diagnose(seq)
    """

    def __init__(self, grid_size: int = 16, bin_width_steps: int = 50) -> None:
        """
        Args:
            grid_size: Side length of output 2D field (neurons mapped to grid_size x grid_size).
            bin_width_steps: Temporal binning width for rate computation.
        """
        if grid_size < 2:
            raise ValueError(f"grid_size must be >= 2, got {grid_size}")
        self.grid_size = grid_size
        self.bin_width = bin_width_steps

    def to_field_sequence(
        self,
        raster: SpikeRaster,
        mode: str = ConversionMode.RATE,
    ) -> Any:
        """Convert spike raster to MFN FieldSequence.

        Returns a FieldSequence object compatible with mfn.diagnose(),
        mfn.extract(), mfn.detect(), etc.
        """
        from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec

        if mode == ConversionMode.RATE:
            field, history = self._rate_field(raster)
        elif mode == ConversionMode.VOLTAGE:
            field, history = self._voltage_field(raster)
        elif mode == ConversionMode.CORRELATION:
            field, history = self._correlation_field(raster)
        else:
            raise ValueError(
                f"Unknown mode: {mode}. Use 'rate_field', 'voltage_field', or 'correlation_field'."
            )

        # Scale to MFN-native voltage range [-0.095, 0.020] V
        field = self._normalize_to_voltage(field)
        if history is not None:
            history = np.stack([self._normalize_to_voltage(h) for h in history])

        spec = SimulationSpec(
            grid_size=self.grid_size,
            steps=raster.T,
            seed=0,
        )

        return FieldSequence(
            field=field,
            history=history,
            spec=spec,
            neuromodulation_state=None,
            metadata={
                "source": "neural_substrate",
                "conversion_mode": mode,
                "N_neurons": raster.N,
                "T_steps": raster.T,
                "dt_ms": raster.dt_ms,
                "mean_rate_hz": raster.mean_rate_hz,
            },
        )

    def _rate_field(self, raster: SpikeRaster) -> tuple[NDArray, NDArray | None]:
        """Bin spikes into spatial rate field on grid."""
        G = self.grid_size
        N_grid = G * G

        # Map neurons to grid positions (wrapping if N != G*G)
        neuron_to_grid = np.arange(raster.N) % N_grid

        # Final frame: rate in last bin
        t_start = max(0, raster.T - self.bin_width)
        mask = raster.spike_times >= t_start
        final_spikes = neuron_to_grid[raster.spike_neurons[mask]]
        field = np.bincount(final_spikes, minlength=N_grid).reshape(G, G).astype(np.float64)

        # Temporal history
        n_bins = max(1, raster.T // self.bin_width)
        history_frames = []
        for b in range(n_bins):
            t0 = b * self.bin_width
            t1 = min((b + 1) * self.bin_width, raster.T)
            mask_b = (raster.spike_times >= t0) & (raster.spike_times < t1)
            bin_spikes = neuron_to_grid[raster.spike_neurons[mask_b]]
            frame = np.bincount(bin_spikes, minlength=N_grid).reshape(G, G).astype(np.float64)
            history_frames.append(frame)

        history = np.array(history_frames, dtype=np.float64) if len(history_frames) > 1 else None
        return field, history

    def _voltage_field(self, raster: SpikeRaster) -> tuple[NDArray, NDArray | None]:
        """Reshape voltage array to 2D grid at each timestep."""
        if raster.voltages is None:
            raise ValueError("Voltage data required for voltage_field mode. Set raster.voltages.")

        G = self.grid_size
        N_grid = G * G
        T = raster.voltages.shape[0]

        # Map neurons to grid (average if N > G*G, zero-pad if N < G*G)
        def _to_grid(v: NDArray) -> NDArray:
            grid = np.zeros(N_grid, dtype=np.float64)
            counts = np.zeros(N_grid, dtype=np.float64)
            idx = np.arange(len(v)) % N_grid
            np.add.at(grid, idx, v)
            np.add.at(counts, idx, 1.0)
            counts[counts == 0] = 1.0
            return (grid / counts).reshape(G, G)

        field = _to_grid(raster.voltages[-1])

        # Subsample history to max 64 frames
        stride = max(1, T // 64)
        history_frames = [_to_grid(raster.voltages[t]) for t in range(0, T, stride)]
        history = np.array(history_frames, dtype=np.float64) if len(history_frames) > 1 else None

        return field, history

    def _correlation_field(self, raster: SpikeRaster) -> tuple[NDArray, None]:
        """Pairwise spike correlation matrix (functional connectivity)."""
        G = self.grid_size
        N_use = min(raster.N, G * G)

        # Build spike count vectors per neuron
        spike_vectors = np.zeros((N_use, raster.T), dtype=np.float64)
        mask = raster.spike_neurons < N_use
        times = raster.spike_times[mask]
        neurons = raster.spike_neurons[mask]
        valid = times < raster.T
        spike_vectors[neurons[valid], times[valid]] = 1.0

        # Correlation matrix
        corr = np.corrcoef(spike_vectors)
        corr = np.nan_to_num(corr, nan=0.0)

        # Resize to grid
        if corr.shape[0] != G:
            from scipy.ndimage import zoom

            scale = G / corr.shape[0]
            corr = zoom(corr, scale, order=1)[:G, :G]

        return corr, None

    @staticmethod
    def _normalize_to_voltage(field: NDArray[np.float64]) -> NDArray[np.float64]:
        """Scale field to MFN-native voltage range [-0.095, 0.020] V."""
        fmin, fmax = field.min(), field.max()
        if fmax - fmin < 1e-12:
            return np.full_like(field, -0.060)  # resting potential
        normalized = (field - fmin) / (fmax - fmin)  # [0, 1]
        return normalized * 0.115 - 0.095  # [-0.095, 0.020] V
