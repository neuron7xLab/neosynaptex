# NeuroCognitiveEngine Contract

**Document Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Stable

This document defines the internal contract for the `NeuroCognitiveEngine.generate()` method output.

---

## Overview

The `NeuroCognitiveEngine` is the high-level orchestration layer for MLSDM + FSLGS. It provides a single entry point that composes:

- **MLSDM LLMWrapper**: Memory, rhythm, moral governance, reliability
- **FSLGSWrapper** (optional): Dual-stream language, anti-schizophrenia, UG constraints

The `generate()` method returns an `EngineResult` model that provides a strongly-typed contract for the engine output.

---

## Target Contract

**Function:** `NeuroCognitiveEngine.generate()`
**Input:** prompt (str), optional parameters
**Output:** `EngineResult` (see below)

---

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | str | Yes | - | Input text prompt to process |
| `max_tokens` | int | No | 512 | Maximum tokens to generate (1-4096) |
| `user_intent` | str | No | "conversational" | User intent category |
| `cognitive_load` | float | No | 0.5 | Cognitive load value (0.0-1.0) |
| `moral_value` | float | No | 0.5 | Moral threshold (0.0-1.0) |
| `context_top_k` | int | No | 5 | RAG context items to retrieve |
| `enable_diagnostics` | bool | No | True | Include diagnostics in output |

---

## Output: EngineResult

The `EngineResult` model provides a strongly-typed output contract.

### Contract Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `response` | str | Yes | Generated response text (empty if rejected) |
| `governance` | dict \| None | Yes | FSLGS governance result (None if disabled) |
| `mlsdm` | dict | Yes | MLSDM internal state snapshot |
| `timing` | EngineTiming | Yes | Pipeline timing metrics |
| `validation_steps` | list[EngineValidationStep] | Yes | Validation steps executed |
| `error` | EngineErrorInfo \| None | Yes | Error info (None if success) |
| `rejected_at` | Literal["pre_flight", "generation", "pre_moral"] \| None | Yes | Rejection stage |
| `meta` | EngineResultMeta | Yes | Execution metadata |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_success` | bool | True if no error and not rejected |
| `is_rejected` | bool | True if rejected_at is set |

---

## Timing: EngineTiming

| Field | Type | Description |
|-------|------|-------------|
| `total` | float | Total pipeline time (ms) |
| `moral_precheck` | float \| None | Pre-flight moral check time (ms) |
| `grammar_precheck` | float \| None | Pre-flight grammar check time (ms) |
| `generation` | float \| None | LLM/FSLGS generation time (ms) |
| `post_moral_check` | float \| None | Post-generation moral check time (ms) |

---

## Validation Step: EngineValidationStep

| Field | Type | Description |
|-------|------|-------------|
| `step` | str | Step name (e.g., "moral_precheck") |
| `passed` | bool | Whether validation passed |
| `skipped` | bool | Whether step was skipped |
| `score` | float \| None | Validation score |
| `threshold` | float \| None | Validation threshold |
| `reason` | str \| None | Reason for skip/failure |

---

## Error Info: EngineErrorInfo

| Field | Type | Description |
|-------|------|-------------|
| `type` | str | Error type code |
| `message` | str \| None | Human-readable message |
| `score` | float \| None | Moral score (for rejections) |
| `threshold` | float \| None | Moral threshold (for rejections) |
| `traceback` | str \| None | Stack trace (debug only) |

**Error Types:**
- `moral_precheck` - Pre-flight moral check failed
- `grammar_precheck` - Pre-flight grammar check failed
- `mlsdm_rejection` - MLSDM rejected request
- `empty_response` - LLM returned empty response
- `bulkhead_full` - System at capacity
- `internal_error` - Unexpected error

---

## Metadata: EngineResultMeta

| Field | Type | Description |
|-------|------|-------------|
| `backend_id` | str \| None | LLM provider ID (multi-LLM routing) |
| `variant` | str \| None | A/B test variant |

---

## Examples

### Success Response

```python
from mlsdm.contracts import EngineResult

result = engine.generate("Hello, world!")

# Check success
if result.is_success:
    print(result.response)
    print(f"Phase: {result.mlsdm.get('phase')}")
    print(f"Total time: {result.timing.total}ms")
```

```json
{
  "response": "NEURO-RESPONSE: Hello, world!...",
  "governance": null,
  "mlsdm": {
    "phase": "wake",
    "step": 42,
    "moral_threshold": 0.5
  },
  "timing": {
    "total": 15.5,
    "moral_precheck": 1.0,
    "generation": 12.5,
    "post_moral_check": 2.0
  },
  "validation_steps": [
    {"step": "moral_precheck", "passed": true, "score": 0.8, "threshold": 0.5},
    {"step": "post_moral_check", "passed": true, "score": 0.85, "threshold": 0.5}
  ],
  "error": null,
  "rejected_at": null,
  "meta": {"backend_id": "local_stub", "variant": null}
}
```

### Rejection Response

```python
result = engine.generate("Harmful prompt")

if result.is_rejected:
    print(f"Rejected at: {result.rejected_at}")
    print(f"Error: {result.error.type}")
    print(f"Score: {result.error.score}, Threshold: {result.error.threshold}")
```

```json
{
  "response": "",
  "governance": null,
  "mlsdm": {},
  "timing": {
    "total": 2.0,
    "moral_precheck": 2.0
  },
  "validation_steps": [
    {"step": "moral_precheck", "passed": false, "score": 0.2, "threshold": 0.5}
  ],
  "error": {
    "type": "moral_precheck",
    "score": 0.2,
    "threshold": 0.5
  },
  "rejected_at": "pre_flight",
  "meta": {}
}
```

---

## ApiError Format

All API errors should use the standardized `ApiError` model:

```python
from mlsdm.contracts import ApiError

# Create validation error
error = ApiError.validation_error(
    message="Prompt cannot be empty",
    field="prompt"
)

# Create moral rejection
error = ApiError.moral_rejection(
    score=0.3,
    threshold=0.5,
    stage="pre_flight"
)

# Serialize for response
{"error": error.model_dump()}
```

**ApiError Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | str | Yes | Machine-readable error code |
| `message` | str | Yes | Human-readable message |
| `details` | dict \| None | No | Additional context |

---

## Pipeline Stages

The engine follows this pipeline:

1. **PRE-FLIGHT** (rejection stage: `pre_flight`)
   - Moral pre-check (MLSDM.moral)
   - Grammar pre-check (FSLGS.grammar, if enabled)

2. **GENERATION** (rejection stage: `generation`)
   - FSLGS (if enabled): режими, dual-stream, UG-constraints
   - MLSDM: moral/rhythm/memory + LLM

3. **POST-VALIDATION** (rejection stage: `pre_moral`)
   - FSLGS coherence, binding, grammar post-check
   - Moral check on response

4. **RESPONSE**
   - Return EngineResult with timing, validation_steps, error info

---

## Migration Guide

### Converting from dict to EngineResult

```python
# Before (dict[str, Any])
result = engine.generate("Hello")
if result.get("error") is None:
    print(result["response"])

# After (EngineResult)
result = engine.generate("Hello")
if result.is_success:
    print(result.response)

# Or use from_dict for legacy code
from mlsdm.contracts import EngineResult
raw_dict = engine.generate("Hello")  # If still returning dict
result = EngineResult.from_dict(raw_dict)
```

### Converting EngineResult back to dict

```python
# For backwards compatibility
result = EngineResult(response="Hello")
as_dict = result.to_dict()  # Returns dict matching legacy format
```

---

## Contract Stability

These models are part of the stable internal API contract:

- **Do not** remove fields without a major version bump
- **Do not** change field types without a major version bump
- **Fields can be added** in minor versions (with defaults)
- All changes should update the contract tests

**Test file:** `tests/contracts/test_engine_contracts.py`

```bash
pytest tests/contracts/test_engine_contracts.py -v
```

---

## Related Documentation

- [API Contract](API_CONTRACT.md) - HTTP endpoint contracts
- [NEURO_COG_ENGINE_SPEC](NEURO_COG_ENGINE_SPEC.md) - Engine specification
- [LLM Pipeline](LLM_PIPELINE.md) - LLM integration details
