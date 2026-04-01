"""NFI — Neuromodulatory Field Intelligence.

Єдина когнітивна машина з формально визначеним інтерфейсом істини.
Чотири шари: ML-SDM, CA1-LAM, BN-Syn, MFN+.
gamma виникає як наслідок узгодженості, не як метрика.

Quick start:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.nfi import NFIAdaptiveLoop, GammaEmergenceProbe

    loop = NFIAdaptiveLoop(base_spec=mfn.SimulationSpec(grid_size=64, steps=100))
    result = loop.run(n_steps=30)

    probe = GammaEmergenceProbe()
    report = probe.analyze(result.contracts)
    print(report.label, report.mechanistic_source)

Ref: Vasylenko (2026)
"""

from .adaptive_loop import AdaptiveRunResult, NFIAdaptiveLoop
from .ca1_lam import CA1TemporalBuffer, TemporalSummary
from .closure import NFIClosureLoop
from .contract import NFIStateContract
from .emergent_validator import EmergentValidationSuite, ValidationReport
from .gamma_probe import GammaEmergenceProbe, GammaEmergenceReport
from .theta_adapter import ThetaMapping

__all__ = [
    "AdaptiveRunResult",
    "CA1TemporalBuffer",
    "EmergentValidationSuite",
    "GammaEmergenceProbe",
    "GammaEmergenceReport",
    "NFIAdaptiveLoop",
    "NFIClosureLoop",
    "NFIStateContract",
    "TemporalSummary",
    "ThetaMapping",
    "ValidationReport",
]
