# ADR-0005: Configuration Layer Architecture (CONFIG-01)

**Status**: Accepted
**Date**: 2025-12-01
**Deciders**: MLSDM Core Team
**Categories**: Architecture, Configuration, Production Readiness

## Context

MLSDM requires centralized configuration management for:
- Calibrated thresholds (moral filter, aphasia detection, memory bounds)
- Runtime parameters (circuit breaker settings, rate limits)
- Environment-specific settings (dev/test/prod profiles)

Previously, configuration was split between two locations:
1. `config/calibration.py` (at repository root) — Calibrated dataclass defaults
2. `src/mlsdm/utils/config_loader.py` + `config_schema.py` — Schema and loading logic

This separation caused issues:
- `config/` directory was outside the Python package (`src/mlsdm/`)
- Imports relied on PYTHONPATH manipulation or editable installs
- No clear boundary between configuration definition and loading
- Difficult to distribute as a standalone package

### Key Forces

- **Package Integrity**: Configuration should be part of the installable package
- **Import Clarity**: Clean imports without PYTHONPATH hacks
- **Separation of Concerns**: Defaults vs loading logic vs validation
- **Backward Compatibility**: Existing code should work with minimal changes
- **Production Readiness**: Configuration must work in containerized deployments

## Decision

We will consolidate the configuration layer within the `mlsdm` package:

1. **Move calibration to package**: `config/calibration.py` → `src/mlsdm/config/calibration.py`
2. **Create config package**: `src/mlsdm/config/__init__.py` with clean public API
3. **Update imports**: Change `from config.calibration import X` → `from mlsdm.config import X`
4. **Keep external YAML files**: `config/*.yaml` remains at root for easy editing

### Configuration Layer Structure

```
src/mlsdm/
├── config/
│   ├── __init__.py          # Public API exports
│   └── calibration.py       # Calibrated dataclass defaults
└── utils/
    ├── config_loader.py     # YAML/INI loading logic
    ├── config_schema.py     # Pydantic schema validation
    └── config_validator.py  # Validation utilities

config/                       # External config files (not in package)
├── calibration.py           # DEPRECATED - keep for backward compatibility
├── default_config.yaml
├── production.yaml
└── production-ready.yaml
```

### Public API

```python
from mlsdm.config import (
    # Dataclasses
    CalibrationConfig,
    MoralFilterCalibration,
    AphasiaDetectorCalibration,
    PELMCalibration,
    SynapticMemoryCalibration,
    CognitiveRhythmCalibration,
    ReliabilityCalibration,
    CognitiveControllerCalibration,
    RateLimitCalibration,
    SynergyExperienceCalibration,
    SecureModeCalibration,

    # Default instances
    MORAL_FILTER_DEFAULTS,
    APHASIA_DEFAULTS,
    PELM_DEFAULTS,
    SYNAPTIC_MEMORY_DEFAULTS,
    COGNITIVE_RHYTHM_DEFAULTS,
    RELIABILITY_DEFAULTS,
    COGNITIVE_CONTROLLER_DEFAULTS,
    RATE_LIMIT_DEFAULTS,
    SYNERGY_EXPERIENCE_DEFAULTS,
    SECURE_MODE_DEFAULTS,

    # Functions
    get_calibration_config,
    get_calibration_summary,
    get_synaptic_memory_config,
)
```

### Configuration Hierarchy (unchanged)

1. **Hardcoded defaults** in `mlsdm/config/calibration.py`
2. **YAML file overrides** from `config/*.yaml`
3. **Environment variable overrides** with `MLSDM_*` prefix

## Consequences

### Positive

- **Package Integrity**: Configuration is now part of the installable package
- **Clean Imports**: `from mlsdm.config import X` works without PYTHONPATH
- **Docker-Ready**: No special setup needed in containers
- **Type Safety**: Dataclasses provide IDE autocompletion and type checking
- **Testable**: Configuration can be tested as part of package tests
- **Documented**: Public API is clearly defined in `__init__.py`

### Negative

- **Migration Required**: Existing code must update imports
- **Duplicate File**: Old `config/calibration.py` kept for backward compatibility
- **Two Locations**: YAML files remain at root, calibration in package

### Neutral

- YAML config files remain at repository root for easy editing
- External tools can still read `config/*.yaml` without Python imports
- Environment variable overrides unchanged

## Alternatives Considered

### Alternative 1: Keep Configuration at Root

- **Description**: Leave `config/` at repository root, add to package path
- **Pros**: No migration, minimal changes
- **Cons**: Fragile imports, breaks in containers, not proper package
- **Reason for rejection**: Does not meet production-readiness requirements

### Alternative 2: Move Everything to `src/mlsdm/config/`

- **Description**: Move YAML files into the package as well
- **Pros**: Single location for all configuration
- **Cons**: Harder to edit YAML in production, package bloat
- **Reason for rejection**: YAML files benefit from being easily editable externally

### Alternative 3: Use Environment Variables Only

- **Description**: Remove YAML/calibration files, use env vars exclusively
- **Pros**: Simple, 12-factor app compliant
- **Cons**: Many parameters, harder to manage complex configs
- **Reason for rejection**: Too many calibration parameters for pure env var approach

## Implementation

### Affected Components

- `src/mlsdm/config/` — New config package
- `src/mlsdm/core/llm_wrapper.py` — Updated imports
- `src/mlsdm/core/cognitive_controller.py` — Updated imports
- `src/mlsdm/cognition/moral_filter_v2.py` — Updated imports
- `src/mlsdm/extensions/neuro_lang_extension.py` — Updated imports
- `src/mlsdm/memory/multi_level_memory.py` — Updated imports
- `src/mlsdm/memory/phase_entangled_lattice_memory.py` — Updated imports
- `tests/unit/test_multi_level_memory_calibration.py` — Updated imports

### Migration Guide

Old:
```python
from config.calibration import MORAL_FILTER_DEFAULTS
```

New:
```python
from mlsdm.config import MORAL_FILTER_DEFAULTS
```

### Related Documents

- `CONFIGURATION_GUIDE.md` — User-facing configuration documentation
- `docs/FORMAL_INVARIANTS.md` — Invariants that depend on calibration
- `ADR-0003-moral-filter.md` — Moral filter calibration decisions
- `ADR-0004-memory-bounds.md` — Memory bound calibration decisions

## References

- [The Twelve-Factor App: Config](https://12factor.net/config)
- Python Packaging Authority: [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- MLSDM Internal: `CONFIGURATION_GUIDE.md`

---

*This ADR documents the rationale for CONFIG-01 configuration layer architecture*
