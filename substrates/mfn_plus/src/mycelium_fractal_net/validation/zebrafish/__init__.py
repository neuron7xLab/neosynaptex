"""Zebrafish gamma-scaling validation pipeline.

# SYNTHETIC_PROXY: real McGuirl 2020 data not loaded.
# Ref: McGuirl et al. (2020) PNAS 117(10):5217-5224. DOI: 10.1073/pnas.1917038117
"""

from .data_adapter import AdapterConfig, ZebrafishFieldAdapter
from .gamma_validator import (
    GammaValidationResult,
    ZebrafishGammaValidator,
    ZebrafishValidationReport,
)
from .kde_adapter import CellDensityAdapter, KDEConfig
from .report import ZebrafishReportExporter
from .synthetic_proxy import (
    SyntheticZebrafishConfig,
    SyntheticZebrafishGenerator,
    ZebrafishPhenotype,
)
from .rips_h1_validator import (
    H1ControlGenerator,
    H1Result,
    H1ValidationReport,
    RipsH1Computer,
    RipsH1Validator,
)
from .rips_validator import (
    RipsControlGenerator,
    RipsMHLComputer,
    RipsResult,
    RipsValidationReport,
    RipsValidator,
)
from .multiscale_gamma import (
    MultiScaleGammaComputer,
    MultiScaleResult,
    MultiScaleValidationReport,
    MultiScaleValidator,
    RandomControlGenerator,
)
from .tda_calibrated import (
    CalibratedGammaComputer,
    CalibratedGammaResult,
    TDACalibratedValidator,
    TDAFrame,
    TDAFrameExtractor,
    TDAValidationReport,
)

__all__ = [
    "AdapterConfig",
    "CalibratedGammaComputer",
    "CalibratedGammaResult",
    "CellDensityAdapter",
    "GammaValidationResult",
    "KDEConfig",
    "MultiScaleGammaComputer",
    "MultiScaleResult",
    "MultiScaleValidationReport",
    "MultiScaleValidator",
    "RandomControlGenerator",
    "RipsControlGenerator",
    "RipsMHLComputer",
    "RipsResult",
    "RipsValidationReport",
    "RipsValidator",
    "SyntheticZebrafishConfig",
    "SyntheticZebrafishGenerator",
    "TDACalibratedValidator",
    "TDAFrame",
    "TDAFrameExtractor",
    "TDAValidationReport",
    "ZebrafishFieldAdapter",
    "ZebrafishGammaValidator",
    "ZebrafishPhenotype",
    "ZebrafishReportExporter",
    "ZebrafishValidationReport",
]
