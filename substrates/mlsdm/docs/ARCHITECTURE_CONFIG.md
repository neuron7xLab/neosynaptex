# Configuration Layer Architecture

**Document Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Stable

## Overview

The MLSDM Configuration Layer provides centralized management of all calibrated parameters, thresholds, and runtime settings. This document describes the architecture, public API, and usage patterns.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MLSDM Configuration Layer                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  mlsdm.config (Public API)                    │   │
│  │                                                               │   │
│  │  • CalibrationConfig      • get_calibration_config()         │   │
│  │  • MoralFilterCalibration • get_calibration_summary()        │   │
│  │  • AphasiaDetectorCalibration                                │   │
│  │  • PELMCalibration        • MORAL_FILTER_DEFAULTS            │   │
│  │  • SynapticMemoryCalibration                                 │   │
│  │  • CognitiveRhythmCalibration                                │   │
│  │  • ReliabilityCalibration                                    │   │
│  │  • CognitiveControllerCalibration                            │   │
│  │  • RateLimitCalibration                                      │   │
│  │  • SynergyExperienceCalibration                              │   │
│  │  • SecureModeCalibration                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              │ imports                               │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               mlsdm.config.calibration                        │   │
│  │                                                               │   │
│  │  Dataclass Definitions:                                       │   │
│  │  • @dataclass(frozen=True) MoralFilterCalibration            │   │
│  │  • @dataclass(frozen=True) AphasiaDetectorCalibration        │   │
│  │  • @dataclass(frozen=True) PELMCalibration                   │   │
│  │  • @dataclass(frozen=True) SynapticMemoryCalibration         │   │
│  │  • @dataclass(frozen=True) CognitiveRhythmCalibration        │   │
│  │  • @dataclass(frozen=True) ReliabilityCalibration            │   │
│  │  • @dataclass(frozen=True) CognitiveControllerCalibration    │   │
│  │  • @dataclass(frozen=True) RateLimitCalibration              │   │
│  │  • @dataclass(frozen=True) SynergyExperienceCalibration      │   │
│  │  • @dataclass(frozen=True) SecureModeCalibration             │   │
│  │  • @dataclass(frozen=True) CalibrationConfig                 │   │
│  │                                                               │   │
│  │  Default Instances:                                           │   │
│  │  • MORAL_FILTER_DEFAULTS = MoralFilterCalibration()          │   │
│  │  • APHASIA_DEFAULTS = AphasiaDetectorCalibration()           │   │
│  │  • (etc.)                                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   config/   │    │   MLSDM_*   │    │   Runtime   │
    │ *.yaml      │    │ Environment │    │   Override  │
    │ Files       │    │ Variables   │    │   (code)    │
    └─────────────┘    └─────────────┘    └─────────────┘
```

## Configuration Hierarchy

Configuration is resolved in the following priority order (highest first):

1. **Runtime Overrides**: Parameters passed directly to constructors
2. **Environment Variables**: `MLSDM_*` prefixed variables
3. **YAML Config Files**: `config/*.yaml`
4. **Hardcoded Defaults**: `mlsdm.config.calibration` dataclasses

## Public API

### Importing Configuration

```python
# Recommended: Import from mlsdm.config
from mlsdm.config import (
    get_calibration_config,
    MORAL_FILTER_DEFAULTS,
    MoralFilterCalibration,
)

# Get complete configuration
config = get_calibration_config()
print(config.moral_filter.threshold)  # 0.50

# Access individual defaults
print(MORAL_FILTER_DEFAULTS.threshold)  # 0.50
print(MORAL_FILTER_DEFAULTS.min_threshold)  # 0.30
```

### Calibration Dataclasses

Each calibration dataclass is frozen (immutable) and provides:
- Type-safe access to parameters
- IDE autocompletion
- Documentation via docstrings

#### MoralFilterCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `threshold` | float | 0.50 | Initial moral threshold |
| `adapt_rate` | float | 0.05 | Threshold adaptation rate |
| `min_threshold` | float | 0.30 | Minimum allowed threshold |
| `max_threshold` | float | 0.90 | Maximum allowed threshold |
| `dead_band` | float | 0.05 | EMA dead band for adaptation |
| `ema_alpha` | float | 0.1 | EMA smoothing factor |

#### AphasiaDetectorCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_sentence_len` | float | 6.0 | Minimum sentence length |
| `min_function_word_ratio` | float | 0.15 | Minimum function word ratio |
| `max_fragment_ratio` | float | 0.5 | Maximum fragment ratio |
| `fragment_length_threshold` | int | 4 | Fragment length threshold |
| `severity_threshold` | float | 0.3 | Repair trigger threshold |
| `detect_enabled` | bool | True | Detection enabled |
| `repair_enabled` | bool | True | Repair enabled |

#### PELMCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_capacity` | int | 20,000 | Default vector capacity |
| `max_capacity` | int | 1,000,000 | Maximum allowed capacity |
| `phase_tolerance` | float | 0.15 | Phase matching tolerance |
| `default_top_k` | int | 5 | Default retrieval count |
| `min_norm_threshold` | float | 1e-9 | Minimum norm threshold |
| `wake_phase` | float | 0.1 | Wake phase encoding |
| `sleep_phase` | float | 0.9 | Sleep phase encoding |

#### SynapticMemoryCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lambda_l1` | float | 0.50 | L1 decay rate |
| `lambda_l2` | float | 0.10 | L2 decay rate |
| `lambda_l3` | float | 0.01 | L3 decay rate |
| `theta_l1` | float | 1.2 | L1→L2 threshold |
| `theta_l2` | float | 2.5 | L2→L3 threshold |
| `gating12` | float | 0.45 | L1→L2 gating factor |
| `gating23` | float | 0.30 | L2→L3 gating factor |

#### CognitiveRhythmCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wake_duration` | int | 8 | Wake phase steps |
| `sleep_duration` | int | 3 | Sleep phase steps |
| `max_wake_tokens` | int | 2048 | Max tokens during wake |
| `max_sleep_tokens` | int | 150 | Max tokens during sleep |

#### ReliabilityCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `circuit_breaker_failure_threshold` | int | 5 | Failures before open |
| `circuit_breaker_recovery_timeout` | float | 60.0 | Recovery timeout (s) |
| `circuit_breaker_success_threshold` | int | 2 | Successes to close |
| `llm_timeout` | float | 30.0 | LLM call timeout (s) |
| `llm_retry_attempts` | int | 3 | LLM retry attempts |
| `pelm_failure_threshold` | int | 3 | PELM failures before degradation |

#### CognitiveControllerCalibration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory_threshold_mb` | float | 1024.0 | Memory threshold (MB) |
| `max_processing_time_ms` | float | 1000.0 | Max processing time (ms) |
| `max_memory_bytes` | int | 1.4 GB | Global memory bound |
| `recovery_cooldown_steps` | int | 10 | Recovery cooldown |
| `recovery_memory_safety_ratio` | float | 0.8 | Recovery safety ratio |
| `recovery_max_attempts` | int | 3 | Max recovery attempts |

## Environment Variables

All calibration parameters can be overridden via environment variables:

```bash
# Moral filter
export MLSDM_MORAL_THRESHOLD=0.60
export MLSDM_MORAL_MIN_THRESHOLD=0.35

# Aphasia detection
export MLSDM_APHASIA_MIN_SENTENCE_LEN=8.0
export MLSDM_APHASIA_REPAIR_ENABLED=false

# Memory bounds
export MLSDM_MAX_MEMORY_BYTES=2147483648  # 2 GB

# Secure mode (disables training in production)
export MLSDM_SECURE_MODE=1
```

## YAML Configuration Files

External YAML files in `config/` directory:

```yaml
# config/production.yaml
moral_filter:
  threshold: 0.60
  min_threshold: 0.40

aphasia:
  repair_enabled: false
  detect_enabled: true

cognitive_controller:
  memory_threshold_mb: 512.0
  max_processing_time_ms: 500.0
```

## Integration with Components

### LLMWrapper

```python
from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.config import COGNITIVE_RHYTHM_DEFAULTS

# Uses calibration defaults automatically
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embeddings,
    # wake_duration defaults to COGNITIVE_RHYTHM_DEFAULTS.wake_duration
    # sleep_duration defaults to COGNITIVE_RHYTHM_DEFAULTS.sleep_duration
)

# Override specific parameters
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embeddings,
    wake_duration=10,  # Override default
    sleep_duration=5,
)
```

### CognitiveController

```python
from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.config import get_synaptic_memory_config

# Load config from YAML
yaml_config = {'multi_level_memory': {'lambda_l1': 0.3}}
synaptic_config = get_synaptic_memory_config(yaml_config)

controller = CognitiveController(
    dim=384,
    synaptic_memory_config=synaptic_config,
)
```

### MoralFilterV2

```python
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.config import MORAL_FILTER_DEFAULTS

# Uses defaults from calibration
filter = MoralFilterV2()
print(filter.threshold)  # Uses MORAL_FILTER_DEFAULTS.threshold

# Override initial threshold
filter = MoralFilterV2(initial_threshold=0.65)
```

## Design Decisions

See [ADR-0005-configuration-layer.md](adr/0005-configuration-layer.md) for detailed rationale.

### Key Principles

1. **Frozen Dataclasses**: All calibration classes are immutable
2. **Fallback Pattern**: Components gracefully handle missing calibration
3. **Type Safety**: Strong typing for all parameters
4. **Separation**: Defaults vs loading logic vs validation

### Fallback Pattern

Components use try/except to handle missing calibration:

```python
try:
    from mlsdm.config import MORAL_FILTER_DEFAULTS
except ImportError:
    MORAL_FILTER_DEFAULTS = None

# Use fallback if calibration unavailable
threshold = (
    MORAL_FILTER_DEFAULTS.threshold
    if MORAL_FILTER_DEFAULTS
    else 0.50
)
```

## Related Documents

- [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) — User-facing configuration guide
- [ADR-0005-configuration-layer.md](adr/0005-configuration-layer.md) — Architecture decision record
- [ADR-0003-moral-filter.md](adr/0003-moral-filter.md) — Moral filter calibration
- [ADR-0004-memory-bounds.md](adr/0004-memory-bounds.md) — Memory bound calibration

---

**Document Status:** Stable
**Last Reviewed:** December 2025
**Next Review:** Version 1.3.0 release
