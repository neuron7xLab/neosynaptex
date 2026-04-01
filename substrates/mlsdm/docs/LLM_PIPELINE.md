# LLM Pipeline Specification

**Document Version:** 1.0.0
**Project Version:** 1.2.0
**Last Updated:** November 2025
**Status:** Production

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Stage Flow](#stage-flow)
- [Components](#components)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Neuro-Principles](#neuro-principles)
- [Testing](#testing)
- [Integration Guide](#integration-guide)

---

## Overview

The LLM Pipeline (`LLMPipeline`) is a unified orchestration layer that integrates:

1. **Pre-flight checks** - Moral filter, threat assessment
2. **LLM generation** - Core language model call
3. **Post-flight processing** - Aphasia detection/repair, content filtering
4. **Telemetry hooks** - Observability and monitoring

### Key Properties

| Property | Description |
|----------|-------------|
| **Thread-safe** | Concurrent request handling |
| **Fault-tolerant** | Graceful degradation on filter errors |
| **Observable** | Stage-level timing and telemetry |
| **Configurable** | Enable/disable individual stages |
| **Extensible** | Protocol-based filter interfaces |

### Location

```
src/mlsdm/core/llm_pipeline.py
```

---

## Architecture

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       LLM Pipeline                          │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐│
│  │ PRE-FILTERS  │ → │   LLM CALL   │ → │   POST-FILTERS   ││
│  │              │   │              │   │                  ││
│  │ • Moral      │   │ • Generate   │   │ • Aphasia        ││
│  │ • Threat     │   │   response   │   │ • Content        ││
│  │              │   │              │   │                  ││
│  └──────────────┘   └──────────────┘   └──────────────────┘│
│         │                  │                   │            │
│         ▼                  ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 TELEMETRY HOOKS                       │  │
│  │   Stage timing, Decision logging, Metrics export      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Output: PipelineResult                                     │
│   • response (final text)                                   │
│   • accepted (bool)                                         │
│   • stages (list of stage results)                          │
│   • total_duration_ms                                       │
└─────────────────────────────────────────────────────────────┘
```

### Class Hierarchy

```python
# Core classes
LLMPipeline          # Main orchestrator
PipelineConfig       # Configuration dataclass
PipelineResult       # Output dataclass
PipelineStageResult  # Per-stage result

# Filter interfaces (Protocols)
PreFilter            # Pre-flight filter protocol
PostFilter           # Post-flight filter protocol

# Filter implementations
MoralPreFilter       # Moral evaluation pre-filter
ThreatPreFilter      # Threat assessment pre-filter
AphasiaPostFilter    # Aphasia detection post-filter

# Result types
FilterDecision       # Enum: ALLOW, BLOCK, MODIFY
FilterResult         # Filter evaluation result
```

---

## Stage Flow

### Stage Execution Order

1. **Pre-filters** (sequential, first block wins)
   - Moral filter evaluates `moral_value`
   - Threat filter evaluates prompt content
   - Any BLOCK decision stops pipeline

2. **LLM generation**
   - Calls configured LLM function
   - Handles timeout and errors
   - Captures response

3. **Post-filters** (sequential, all run)
   - Aphasia detection and optional repair
   - Content filtering (future)
   - MODIFY decisions transform response

4. **Telemetry emission**
   - Calls registered callbacks
   - Records final result

### Filter Decision Flow

```
Pre-filter evaluation:
  ALLOW  → Continue to next stage
  BLOCK  → Stop pipeline, return rejection
  MODIFY → Continue with modified input (future)

Post-filter evaluation:
  ALLOW  → Continue with original response
  BLOCK  → Return empty response (future)
  MODIFY → Continue with modified response
```

---

## Components

### MoralPreFilter

**Purpose:** Evaluate moral acceptability before LLM generation.

**Neuro-principle:** Prefrontal cortex inhibition - prevents harmful outputs.

```python
from mlsdm.core.llm_pipeline import MoralPreFilter, FilterDecision

filter = MoralPreFilter(initial_threshold=0.5)

result = filter.evaluate(
    prompt="user input",
    context={"moral_value": 0.8}
)

if result.decision == FilterDecision.ALLOW:
    print("Request accepted")
else:
    print(f"Request blocked: {result.reason}")
```

**Properties:**
- Uses `MoralFilterV2` internally
- Adaptive threshold (0.30-0.90 bounds)
- EMA-based threshold adjustment

### ThreatPreFilter

**Purpose:** Detect potential threats in prompts.

**Neuro-principle:** Amygdala threat response - rapid threat detection.

```python
from mlsdm.core.llm_pipeline import ThreatPreFilter

filter = ThreatPreFilter(sensitivity=0.5)

result = filter.evaluate(
    prompt="normal user question",
    context={}
)

print(f"Threat score: {result.metadata['threat_score']}")
```

**Properties:**
- Keyword-based detection (placeholder)
- Configurable sensitivity (0.0-1.0)
- Extensible for ML-based detection

### AphasiaPostFilter

**Purpose:** Detect and repair telegraphic speech patterns.

**Neuro-principle:** Executive monitoring - error correction.

```python
from mlsdm.core.llm_pipeline import AphasiaPostFilter

filter = AphasiaPostFilter(
    repair_enabled=True,
    severity_threshold=0.3,
    llm_repair_fn=my_llm_function
)

result = filter.evaluate(
    response="LLM generated text",
    context={"prompt": "original prompt", "max_tokens": 512}
)

if result.decision == FilterDecision.MODIFY:
    final_text = result.modified_content
else:
    final_text = "LLM generated text"
```

**Properties:**
- Uses `AphasiaBrocaDetector` internally
- Optional automatic repair via LLM
- Configurable severity threshold

---

## Configuration

### PipelineConfig

```python
from mlsdm.core.llm_pipeline import PipelineConfig

config = PipelineConfig(
    # Moral filter
    moral_filter_enabled=True,      # Enable/disable moral pre-filter
    moral_threshold=0.50,           # Initial moral threshold (0.0-1.0)

    # Aphasia filter
    aphasia_detection_enabled=True, # Enable/disable aphasia detection
    aphasia_repair_enabled=True,    # Enable/disable automatic repair
    aphasia_severity_threshold=0.3, # Minimum severity for repair

    # Threat filter
    threat_assessment_enabled=False, # Enable/disable threat pre-filter

    # General
    max_tokens_default=512,         # Default max tokens
    telemetry_enabled=True,         # Enable/disable telemetry hooks
)
```

### Configuration Profiles

| Profile | Moral | Aphasia | Threat | Use Case |
|---------|-------|---------|--------|----------|
| **Standard** | ✅ | ✅ | ❌ | General production |
| **Strict** | ✅ | ✅ | ✅ | High-security environments |
| **Minimal** | ❌ | ❌ | ❌ | Testing, benchmarks |
| **Content-Safe** | ✅ | ✅ | ✅ | User-facing applications |

---

## Usage Examples

### Basic Usage

```python
from mlsdm.core.llm_pipeline import LLMPipeline, PipelineConfig

# Define LLM function
def my_llm(prompt: str, max_tokens: int) -> str:
    # Your LLM implementation
    return "Generated response..."

# Create pipeline
pipeline = LLMPipeline(
    llm_generate_fn=my_llm,
    config=PipelineConfig(
        moral_filter_enabled=True,
        aphasia_detection_enabled=True,
    ),
)

# Process request
result = pipeline.process(
    prompt="Explain quantum computing",
    moral_value=0.8,
    max_tokens=512,
)

if result.accepted:
    print(result.response)
else:
    print(f"Blocked at {result.blocked_at}: {result.block_reason}")
```

### With Telemetry

```python
from mlsdm.core.llm_pipeline import LLMPipeline, PipelineResult

def log_telemetry(result: PipelineResult):
    print(f"Total time: {result.total_duration_ms:.2f}ms")
    for stage in result.stages:
        print(f"  {stage.stage_name}: {stage.duration_ms:.2f}ms")

pipeline = LLMPipeline(llm_generate_fn=my_llm)
pipeline.register_telemetry_callback(log_telemetry)

result = pipeline.process(prompt="Hello", moral_value=0.8)
```

### Inspecting Results

```python
result = pipeline.process(prompt="Test", moral_value=0.8)

# Check stages
for stage in result.stages:
    print(f"{stage.stage_name}: success={stage.success}, time={stage.duration_ms}ms")

    # Access filter-specific metadata
    if hasattr(stage.result, 'metadata'):
        print(f"  Metadata: {stage.result.metadata}")

# Get pipeline stats
stats = pipeline.get_stats()
print(f"Pre-filters: {stats['pre_filters']}")
print(f"Post-filters: {stats['post_filters']}")

# Get moral filter state
moral_state = pipeline.get_moral_filter_state()
if moral_state:
    print(f"Moral threshold: {moral_state['threshold']}")
```

---

## Neuro-Principles

The LLM Pipeline implements several neurobiological principles:

### 1. Prefrontal Cortex Inhibition (Pre-filters)

**Biological basis:** The prefrontal cortex inhibits inappropriate responses before they are executed.

**Implementation:** Moral and threat pre-filters evaluate requests before LLM generation, blocking harmful or inappropriate content.

### 2. Amygdala Threat Response (Threat Filter)

**Biological basis:** The amygdala provides rapid threat detection, triggering defensive responses.

**Implementation:** ThreatPreFilter performs quick pattern-based threat detection, blocking suspicious requests before expensive LLM calls.

### 3. Executive Monitoring (Post-filters)

**Biological basis:** Executive functions monitor and correct speech production errors.

**Implementation:** AphasiaPostFilter detects speech pathologies analogous to Broca's aphasia and triggers correction.

### 4. Adaptive Thresholds (Moral Filter)

**Biological basis:** Neural thresholds adapt based on experience and context.

**Implementation:** MoralPreFilter uses EMA-based threshold adaptation, responding to patterns of accepted/rejected content.

---

## Testing

### Unit Tests

```bash
# Run all pipeline tests
pytest tests/unit/test_llm_pipeline.py -v

# Run specific test class
pytest tests/unit/test_llm_pipeline.py::TestMoralPreFilter -v

# Run with coverage
pytest tests/unit/test_llm_pipeline.py --cov=mlsdm.core.llm_pipeline
```

### Test Coverage

| Test Class | Coverage |
|------------|----------|
| `TestLLMPipelineBasic` | Pipeline creation, process flow |
| `TestMoralPreFilter` | Moral evaluation, adaptation |
| `TestThreatPreFilter` | Threat detection, sensitivity |
| `TestAphasiaPostFilter` | Aphasia detection, repair |
| `TestPipelineErrorHandling` | Error recovery, graceful degradation |
| `TestPipelineTelemetry` | Telemetry callbacks, disabling |
| `TestPipelineEdgeCases` | Empty prompts, unicode, special chars |

---

## Integration Guide

### With LLMWrapper

The LLMPipeline can be used alongside or as a replacement for the existing LLMWrapper:

```python
from mlsdm.core.llm_pipeline import LLMPipeline, PipelineConfig
from mlsdm.adapters import build_local_stub_llm_adapter

# Create adapter
llm_fn = build_local_stub_llm_adapter()

# Create pipeline
pipeline = LLMPipeline(
    llm_generate_fn=llm_fn,
    config=PipelineConfig(
        moral_filter_enabled=True,
        aphasia_detection_enabled=True,
    ),
)

# Use pipeline
result = pipeline.process(prompt="Hello", moral_value=0.8)
```

### With NeuroCognitiveEngine

```python
from mlsdm.engine import NeuroCognitiveEngine
from mlsdm.core.llm_pipeline import LLMPipeline

# Create engine
engine = NeuroCognitiveEngine(...)

# Create pipeline wrapping engine's LLM function
pipeline = LLMPipeline(
    llm_generate_fn=lambda p, t: engine.generate(p, max_tokens=t)["response"],
)
```

### Adding Custom Filters

```python
from mlsdm.core.llm_pipeline import FilterResult, FilterDecision

class CustomPreFilter:
    """Custom pre-filter implementation."""

    def evaluate(self, prompt: str, context: dict) -> FilterResult:
        # Custom logic
        if "forbidden" in prompt.lower():
            return FilterResult(
                decision=FilterDecision.BLOCK,
                reason="forbidden_content",
                metadata={"matched": "forbidden"},
            )
        return FilterResult(
            decision=FilterDecision.ALLOW,
            reason="allowed",
        )

# Add to pipeline
pipeline._pre_filters.append(("custom_filter", CustomPreFilter()))
```

---

## References

- [MORAL_FILTER_SPEC.md](../MORAL_FILTER_SPEC.md) - Moral filter specification
- [APHASIA_SPEC.md](../APHASIA_SPEC.md) - Aphasia detection specification
- [LLM_ADAPTERS_AND_FACTORY.md](./LLM_ADAPTERS_AND_FACTORY.md) - LLM adapter documentation
- [API_REFERENCE.md](../API_REFERENCE.md) - Complete API reference

---

**Document Status:** Production
**Review Cycle:** Per major version
**Last Reviewed:** November 2025
**Next Review:** v2.0.0 release
