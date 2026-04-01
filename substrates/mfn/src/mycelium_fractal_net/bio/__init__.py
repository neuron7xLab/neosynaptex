"""Bio extension for MyceliumFractalNet.

Public surface (15 symbols, stable contract):
    BioExtension, BioConfig, BioReport
    MetaOptimizer, MetaOptimizerResult
    BioMemory, HDVEncoder
    MorphospaceBuilder, BasinStabilityAnalyzer
    GapJunctionDiffuser, HDVFieldEncoder
    FieldActiveInference, PersuadabilityAnalyzer
    LevinPipeline, ComputeBudget

Hard dependencies: numpy (always), scipy (Physarum + Levin), sklearn (morphospace)
Import budget: bio/ must not import from integration/, api/, cli/

Computational contracts (enforced by benchmark gates):
    PhysarumEngine.step() @ N=32: < 5ms
    BioMemory.query() @ 200 eps:  < 0.5ms
    BioExtension.step(1) @ N=16:  < 10ms
"""

from .anastomosis import AnastomosisConfig, AnastomosisEngine, AnastomosisState
from .chemotaxis import ChemotaxisConfig, ChemotaxisEngine, ChemotaxisState
from .compute_reserve import ComputeBudget, ComputeMode, GlycogenStore, ReserveConfig
from .dispersal import DispersalConfig, SporeDispersalEngine, SporeDispersalState
from .evolution import (
    PARAM_BOUNDS,
    PARAM_NAMES,
    BioEvolutionOptimizer,
    BioEvolutionResult,
    compute_fitness,
    params_to_bio_config,
)
from .extension import BioConfig, BioExtension, BioReport
from .fhn import FHNConfig, FHNEngine, FHNState
from .levin_pipeline import LevinPipeline, LevinPipelineConfig, LevinReport
from .memory import BioMemory, HDVEncoder, MemoryEntry
from .memory_anonymization import (
    AnonymizationConfig,
    AnonymizationMetrics,
    GapJunctionDiffuser,
    HDVFieldEncoder,
)
from .meta import MetaOptimizer, MetaOptimizerResult
from .morphospace import (
    BasinStabilityAnalyzer,
    BasinStabilityResult,
    MorphospaceBuilder,
    MorphospaceConfig,
    MorphospaceCoords,
)
from .persuasion import (
    FieldActiveInference,
    FreeEnergyResult,
    InterventionClassifier,
    InterventionLevel,
    PersuadabilityAnalyzer,
    PersuadabilityResult,
)
from .physarum import PhysarumConfig, PhysarumEngine, PhysarumState

# Public contract — stable across versions
__all__ = [
    "BasinStabilityAnalyzer",
    "BioConfig",
    "BioExtension",
    "BioMemory",
    "BioReport",
    "ComputeBudget",
    "FieldActiveInference",
    "GapJunctionDiffuser",
    "HDVEncoder",
    "HDVFieldEncoder",
    "LevinPipeline",
    "MetaOptimizer",
    "MetaOptimizerResult",
    "MorphospaceBuilder",
    "PersuadabilityAnalyzer",
]

# Internal — accessible via direct import but not part of the contract:
# AnastomosisEngine, PhysarumEngine, FHNEngine, etc.
# BioEvolutionOptimizer, PARAM_BOUNDS, PARAM_NAMES, etc.
# InterventionClassifier, InterventionLevel, etc.
