"""BioExtension — unified multi-scale wrapper over FieldSequence.

Orchestrates 5 mechanisms in dependency order:
  Fast:     FHN electrical (substeps within each step)
  Medium:   Physarum conductivity + cytoplasmic streaming
  Slow:     Anastomosis + Chemotaxis
  Episodic: Spore dispersal
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from .anastomosis import AnastomosisConfig, AnastomosisEngine, AnastomosisState
from .chemotaxis import ChemotaxisConfig, ChemotaxisEngine, ChemotaxisState
from .dispersal import DispersalConfig, SporeDispersalEngine, SporeDispersalState
from .fhn import FHNConfig, FHNEngine, FHNState
from .physarum import PhysarumConfig, PhysarumEngine, PhysarumState

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["BioConfig", "BioExtension", "BioReport"]


@dataclass(frozen=True)
class BioConfig:
    """Unified configuration for all 5 bio mechanisms."""

    physarum: PhysarumConfig = field(default_factory=PhysarumConfig)
    anastomosis: AnastomosisConfig = field(default_factory=AnastomosisConfig)
    fhn: FHNConfig = field(default_factory=FHNConfig)
    dispersal: DispersalConfig = field(default_factory=DispersalConfig)
    chemotaxis: ChemotaxisConfig = field(default_factory=ChemotaxisConfig)
    source_threshold: float = 0.0
    sink_threshold: float = -0.05
    enable_physarum: bool = True
    enable_anastomosis: bool = True
    enable_fhn: bool = True
    enable_dispersal: bool = True
    enable_chemotaxis: bool = True
    seed: int = 42


@dataclass(frozen=True)
class BioReport:
    """Unified report from all bio mechanisms for one timestep."""

    physarum: dict[str, Any]
    anastomosis: dict[str, Any]
    fhn: dict[str, Any]
    dispersal: dict[str, Any]
    chemotaxis: dict[str, Any]
    step_count: int
    compute_time_ms: float
    field_shape: tuple[int, int]

    def summary(self) -> str:
        """Summary."""
        p = self.physarum
        a = self.anastomosis
        f = self.fhn
        return (
            f"[BIO step={self.step_count}] "
            f"physarum: D_max={p.get('conductivity_max', 0):.3f} "
            f"flux={p.get('flux_max', 0):.3f} | "
            f"anastomosis: tips={a.get('tip_density_mean', 0):.4f} "
            f"hyphae={a.get('hyphal_density_mean', 0):.4f} "
            f"kappa={a.get('connectivity_mean', 0):.4f} | "
            f"fhn: spiking={f.get('spiking_fraction', 0):.3f} "
            f"({self.compute_time_ms:.0f}ms)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "physarum": self.physarum,
            "anastomosis": self.anastomosis,
            "fhn": self.fhn,
            "dispersal": self.dispersal,
            "chemotaxis": self.chemotaxis,
            "step_count": self.step_count,
            "compute_time_ms": self.compute_time_ms,
            "field_shape": list(self.field_shape),
        }


class BioExtension:
    """Multi-scale biological extension over MFN FieldSequence.

    Usage::

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
        bio = BioExtension.from_sequence(seq)
        bio = bio.step(n=10)
        print(bio.report().summary())
    """

    def __init__(
        self,
        *,
        field: np.ndarray,
        N: int,
        config: BioConfig,
        physarum_state: PhysarumState,
        anastomosis_state: AnastomosisState,
        fhn_state: FHNState,
        dispersal_state: SporeDispersalState,
        chemotaxis_state: ChemotaxisState,
        rng: np.random.Generator,
        step_count: int = 0,
    ) -> None:
        self._field = field
        self.N = N
        self.config = config
        self.physarum_state = physarum_state
        self.anastomosis_state = anastomosis_state
        self.fhn_state = fhn_state
        self.dispersal_state = dispersal_state
        self.chemotaxis_state = chemotaxis_state
        self._rng = rng
        self.step_count = step_count
        self._p_engine = PhysarumEngine(N, config.physarum)
        self._a_engine = AnastomosisEngine(N, config.anastomosis)
        self._fhn_engine = FHNEngine(N, config.fhn)
        self._d_engine = SporeDispersalEngine(N, config.dispersal)
        self._c_engine = ChemotaxisEngine(N, config.chemotaxis)

    @classmethod
    def from_sequence(cls, seq: FieldSequence, config: BioConfig | None = None) -> BioExtension:
        """Construct BioExtension from a FieldSequence."""
        config = config or BioConfig()
        field = seq.field.astype(np.float64)
        N = field.shape[0]
        rng = np.random.default_rng(config.seed)

        source_mask = field > config.source_threshold
        sink_mask = field < config.sink_threshold

        p_state = PhysarumEngine(N, config.physarum).initialize(source_mask, sink_mask, rng=rng)

        norm_field = (field - field.min()) / (field.max() - field.min() + 1e-12)
        initial_tips = norm_field * 0.1
        a_state = AnastomosisEngine(N, config.anastomosis).initialize(initial_tips)

        hyphal_mask = (a_state.B > 0.0) | (norm_field > 0.1)
        fhn_state = FHNEngine(N, config.fhn).initialize(hyphal_mask, rng=rng)

        d_state = SporeDispersalEngine(N, config.dispersal).initialize()

        source_map = norm_field * config.chemotaxis.source_strength
        c_state = ChemotaxisEngine(N, config.chemotaxis).initialize(
            source_map, initial_rho=initial_tips
        )

        return cls(
            field=field,
            N=N,
            config=config,
            physarum_state=p_state,
            anastomosis_state=a_state,
            fhn_state=fhn_state,
            dispersal_state=d_state,
            chemotaxis_state=c_state,
            rng=rng,
        )

    def step(self, n: int = 1) -> BioExtension:
        """Advance one timestep."""
        ext = self
        for _ in range(n):
            ext = ext._single_step()
        return ext

    def _single_step(self) -> BioExtension:
        cfg = self.config
        field = self._field
        source_mask = field > cfg.source_threshold
        sink_mask = field < cfg.sink_threshold

        fhn_s = self.fhn_state
        if cfg.enable_fhn:
            hyphal_mask = self.anastomosis_state.B > 0.01
            fhn_s = self._fhn_engine.step(fhn_s, hyphal_mask)
            spike_perturb = (fhn_s.spike_map > 0).astype(np.float64) * 0.1
            sink_mask = sink_mask | (spike_perturb > 0.05)

        p_s = self.physarum_state
        if cfg.enable_physarum:
            # Feedback: where hyphae exist, new nutrient sources emerge.
            # Closes the biological loop: Physarum → growth → new sources → Physarum.
            if cfg.enable_anastomosis and np.any(self.anastomosis_state.B > 0.05):
                source_mask = source_mask | (self.anastomosis_state.B > 0.05)
            p_s = self._p_engine.step(p_s, source_mask, sink_mask)

        a_s = self.anastomosis_state
        if cfg.enable_anastomosis:
            if cfg.enable_chemotaxis:
                a_s.C[:] += 0.05 * self.chemotaxis_state.rho
            if cfg.enable_dispersal and np.any(self.dispersal_state.germination_sites):
                a_s.C[:] += self.dispersal_state.germination_sites.astype(float) * 0.05
            # Physarum conductivity → Anastomosis growth rate:
            # where transport is efficient, hyphae grow faster.
            # Convert edge conductivities to per-cell mean.
            cond_field = None
            if cfg.enable_physarum:
                N = self.N
                cond_cell = np.zeros((N, N), dtype=np.float64)
                count = np.zeros((N, N), dtype=np.float64)
                cond_cell[:, :-1] += p_s.D_h
                cond_cell[:, 1:] += p_s.D_h
                count[:, :-1] += 1
                count[:, 1:] += 1
                cond_cell[:-1, :] += p_s.D_v
                cond_cell[1:, :] += p_s.D_v
                count[:-1, :] += 1
                count[1:, :] += 1
                cond_field = cond_cell / np.maximum(count, 1)
            a_s = self._a_engine.step(a_s, conductivity_field=cond_field)

        c_s = self.chemotaxis_state
        if cfg.enable_chemotaxis:
            c_s = self._c_engine.step(c_s)

        d_s = self.dispersal_state
        if cfg.enable_dispersal:
            d_s = self._d_engine.step(d_s, a_s.B, self._rng)

        return BioExtension(
            field=field,
            N=self.N,
            config=cfg,
            physarum_state=p_s,
            anastomosis_state=a_s,
            fhn_state=fhn_s,
            dispersal_state=d_s,
            chemotaxis_state=c_s,
            rng=self._rng,
            step_count=self.step_count + 1,
        )

    def report(self) -> BioReport:
        """Generate unified report of current bio state."""
        t0 = time.perf_counter()
        return BioReport(
            physarum=self.physarum_state.to_dict(),
            anastomosis=self.anastomosis_state.to_dict(),
            fhn=self.fhn_state.to_dict(),
            dispersal=self.dispersal_state.to_dict(),
            chemotaxis=self.chemotaxis_state.to_dict(),
            step_count=self.step_count,
            compute_time_ms=(time.perf_counter() - t0) * 1000,
            field_shape=(self.N, self.N),
        )

    def effective_diffusion(self, base_D: float = 0.18) -> np.ndarray:
        """Compute effective diffusion coefficient from Physarum conductivity."""
        return base_D * (1.0 + 2.0 * self.anastomosis_state.kappa)

    def conductivity_map(self) -> np.ndarray:
        """Return the Physarum conductivity map for the current state."""
        return self.physarum_state.conductivity_map()
