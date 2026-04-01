"""NeuralExtension: high-level orchestrator for spiking neural substrate.

Follows BioExtension pattern: single entry point that runs a complete
neural simulation and produces MFN-compatible outputs.

Usage:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.neural import NeuralExtension, NeuralConfig

    # Standalone neural simulation
    ext = NeuralExtension(NeuralConfig(N=128, duration_ms=1000))
    report = ext.run()
    print(report.summary())

    # Bridge to MFN analytics
    seq = ext.to_field_sequence()
    diagnosis = mfn.diagnose(seq)

    # Or from existing R-D sequence: couple neural dynamics
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    ext = NeuralExtension.from_sequence(seq, NeuralConfig(N=128))
    report = ext.run()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from .converter import ConversionMode, SpikeFieldConverter, SpikeRaster
from .emergence import EmergenceDetector, EmergenceReport
from .network import NetworkParams, SpikeNetwork

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from .criticality import CriticalityReport

__all__ = ["NeuralConfig", "NeuralExtension", "NeuralReport"]


@dataclass(frozen=True)
class NeuralConfig:
    """Configuration for neural simulation."""

    N: int = 128
    duration_ms: float = 1000.0
    dt_ms: float = 0.5
    I_ext_pA: float = 410.0
    seed: int = 42
    frac_inhib: float = 0.2
    p_conn: float = 0.1
    enable_stdp: bool = True
    enable_emergence: bool = True
    grid_size: int = 16  # for field conversion

    @property
    def total_steps(self) -> int:
        return int(self.duration_ms / self.dt_ms)


@dataclass
class NeuralReport:
    """Complete neural simulation report."""

    criticality: CriticalityReport
    emergence: EmergenceReport | None
    duration_ms: float
    N: int
    total_spikes: int
    mean_rate_hz: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """One-line summary for display."""
        phase = self.emergence.phase.value if self.emergence else "n/a"
        sigma = self.criticality.sigma_mean
        n_aval = self.criticality.avalanche_stats.n_avalanches
        alpha = self.criticality.avalanche_stats.alpha_size
        return (
            f"[NEURAL N={self.N} T={self.duration_ms:.0f}ms] "
            f"sigma={sigma:.3f} rate={self.mean_rate_hz:.1f}Hz "
            f"avalanches={n_aval} alpha={alpha:.2f} "
            f"emergence={phase}"
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "N": self.N,
            "duration_ms": self.duration_ms,
            "total_spikes": self.total_spikes,
            "mean_rate_hz": round(self.mean_rate_hz, 2),
            "criticality": self.criticality.to_dict(),
        }
        if self.emergence:
            result["emergence"] = self.emergence.to_dict()
        return result


class NeuralExtension:
    """High-level neural substrate orchestrator.

    Parallel to BioExtension: provides a complete simulation
    with criticality tracking and emergence detection,
    then bridges output to MFN's analytics pipeline.
    """

    def __init__(
        self,
        config: NeuralConfig | None = None,
        coupling_field: NDArray[np.float64] | None = None,
    ) -> None:
        self.config = config or NeuralConfig()
        self._coupling_field = coupling_field

        net_params = NetworkParams(
            N=self.config.N,
            frac_inhib=self.config.frac_inhib,
            p_conn=self.config.p_conn,
            dt_ms=self.config.dt_ms,
            seed=self.config.seed,
            enable_stdp=self.config.enable_stdp,
        )
        self._network = SpikeNetwork(net_params)
        self._emergence = EmergenceDetector() if self.config.enable_emergence else None
        self._voltage_history: list[NDArray[np.float64]] = []
        self._ran = False

    @classmethod
    def from_sequence(cls, seq: Any, config: NeuralConfig | None = None) -> NeuralExtension:
        """Create from MFN FieldSequence: use final field as coupling input."""
        cfg = config or NeuralConfig()
        coupling = np.asarray(seq.field, dtype=np.float64)
        return cls(config=cfg, coupling_field=coupling)

    def run(self) -> NeuralReport:
        """Execute full simulation. Returns NeuralReport."""
        cfg = self.config
        total_steps = cfg.total_steps

        # Coupling modulation: if we have a field, use it to modulate I_ext
        I_base = cfg.I_ext_pA
        coupling_modulation = None
        if self._coupling_field is not None:
            # Flatten field, normalize to [0.8, 1.2], map to N neurons
            flat = self._coupling_field.ravel().astype(np.float64)
            if flat.max() - flat.min() > 1e-12:
                norm = (flat - flat.min()) / (flat.max() - flat.min())
            else:
                norm = np.ones_like(flat) * 0.5
            # Map to N neurons (tile/truncate)
            modulation = np.tile(norm, (cfg.N // len(norm) + 1))[: cfg.N]
            coupling_modulation = 0.8 + 0.4 * modulation  # [0.8, 1.2]

        for t in range(total_steps):
            I_ext = I_base
            if coupling_modulation is not None:
                # Spatially modulated external current
                I_ext = I_base * coupling_modulation[t % len(coupling_modulation)]
            else:
                I_ext = I_base

            self._network.step(I_ext_pA=I_ext)

            # Emergence tracking
            if self._emergence and t % 10 == 0:
                self._emergence.observe(self._network.voltage)

            # Record voltage history (subsampled)
            if t % 10 == 0:
                self._voltage_history.append(self._network.voltage.copy())

        self._ran = True

        # Build report
        crit_report = self._network.criticality.report()
        emerg_report = self._emergence.report() if self._emergence else None
        spike_times, _spike_neurons = self._network.spike_raster
        total_spikes = len(spike_times)
        mean_rate = total_spikes / cfg.N / (cfg.duration_ms / 1000.0) if cfg.N > 0 else 0.0

        return NeuralReport(
            criticality=crit_report,
            emergence=emerg_report,
            duration_ms=cfg.duration_ms,
            N=cfg.N,
            total_spikes=total_spikes,
            mean_rate_hz=mean_rate,
        )

    def to_field_sequence(self, mode: str = ConversionMode.RATE) -> Any:
        """Convert simulation output to MFN FieldSequence.

        Enables: mfn.diagnose(seq), mfn.extract(seq), mfn.detect(seq),
        and all analytics (TDA, causal emergence, Wasserstein, etc.)
        """
        if not self._ran:
            self.run()

        spike_times, spike_neurons = self._network.spike_raster
        voltages = (
            np.array(self._voltage_history, dtype=np.float64) if self._voltage_history else None
        )

        raster = SpikeRaster(
            spike_times=spike_times,
            spike_neurons=spike_neurons,
            N=self.config.N,
            T=self.config.total_steps,
            dt_ms=self.config.dt_ms,
            voltages=voltages,
        )

        converter = SpikeFieldConverter(
            grid_size=self.config.grid_size,
            bin_width_steps=max(1, self.config.total_steps // 40),
        )
        return converter.to_field_sequence(raster, mode=mode)
