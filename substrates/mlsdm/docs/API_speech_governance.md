# Speech Governance API Contract

**Document Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Stable

This document defines the contract for the Speech Governance system, including aphasia detection and repair functionality exposed through the `/infer` endpoint.

---

## Table of Contents

- [Overview](#overview)
- [Target Contract](#target-contract)
- [Input: InferRequest](#input-inferrequest)
- [Output: AphasiaMetadata](#output-aphasiametadata)
- [Internal Models](#internal-models)
  - [AphasiaReport](#aphasiareport)
  - [PipelineStepResult](#pipelinestepresult)
  - [PipelineMetadata](#pipelinemetadata)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Test Commands](#test-commands)

---

## Overview

The Speech Governance system provides:
- **Aphasia detection**: Identifies telegraphic/fragmented speech patterns in LLM outputs
- **Speech repair**: Optionally repairs detected patterns to improve output quality
- **Pipeline composition**: Multiple governors can be chained for flexible processing

---

## Target Contract

**Endpoint:** `POST /infer`
**Feature:** `aphasia_mode` parameter
**Response Field:** `aphasia_metadata`

When `aphasia_mode=true` is set in the request, the response includes structured metadata about aphasia detection and repair in the `aphasia_metadata` field.

---

## Input: InferRequest

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | str | Yes | - | Input text prompt (min 1 char) |
| `aphasia_mode` | bool | No | false | Enable aphasia detection and repair |
| `moral_value` | float | No | 0.5 | Moral threshold (0.0-1.0) |
| `secure_mode` | bool | No | false | Enable enhanced security filtering |
| `rag_enabled` | bool | No | true | Enable RAG context retrieval |

---

## Output: AphasiaMetadata

When `aphasia_mode=true`, the `aphasia_metadata` field in the response contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | bool | Yes | Whether aphasia mode was enabled for this request |
| `detected` | bool | Yes | Whether aphasic patterns were detected |
| `severity` | float | Yes | Severity score (0.0 = none, 1.0 = severe) |
| `repaired` | bool | Yes | Whether repairs were applied |
| `note` | str \| null | No | Optional note about the processing |

### Severity Scale

| Score | Level | Description |
|-------|-------|-------------|
| 0.0 | None | No telegraphic speech detected |
| 0.1-0.3 | Mild | Minor omissions (articles, conjunctions) |
| 0.4-0.6 | Moderate | Multiple function words missing |
| 0.7-0.9 | Severe | Heavily telegraphic, needs repair |
| 1.0 | Critical | Almost all function words missing |

---

## Internal Models

### AphasiaReport

Internal model for detailed aphasia detection results.

| Field | Type | Description |
|-------|------|-------------|
| `is_aphasic` | bool | Whether telegraphic speech detected |
| `severity` | float | Severity score (0.0-1.0) |
| `patterns_detected` | list[str] | Specific patterns detected |
| `repaired` | bool | Whether repairs were applied |
| `repair_notes` | str \| null | Details about repairs |

**Pattern Types:**
- `missing_articles` - Missing "a", "an", "the"
- `omitted_function_words` - Missing "is", "are", "to", etc.
- `fragmented_syntax` - Incomplete sentence structures
- `missing_conjunctions` - Missing "and", "but", "or", etc.

### PipelineStepResult

Result of a single step in the speech governance pipeline.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Governor name/identifier |
| `status` | "ok" \| "error" | Step execution status |
| `raw_text` | str \| null | Input text (if success) |
| `final_text` | str \| null | Output text (if success) |
| `metadata` | dict \| null | Governor-specific metadata |
| `error_type` | str \| null | Exception type (if error) |
| `error_message` | str \| null | Exception message (if error) |

### PipelineMetadata

Aggregated metadata for the entire pipeline execution.

| Field | Type | Description |
|-------|------|-------------|
| `pipeline` | list[PipelineStepResult] | Step results in order |
| `aphasia_report` | AphasiaReport \| null | Aggregated aphasia report |
| `total_steps` | int | Total number of steps |
| `successful_steps` | int | Steps that succeeded |
| `failed_steps` | int | Steps that failed |

---

## Error Handling

### When Speech Governor Not Configured

If `aphasia_mode=true` but no speech governor is configured, the response includes:

```json
{
  "aphasia_metadata": {
    "enabled": true,
    "detected": false,
    "severity": 0.0,
    "repaired": false,
    "note": "aphasia_mode enabled but no speech governor configured"
  }
}
```

### Pipeline Failure Isolation

The `PipelineSpeechGovernor` isolates failures:
- If one governor fails, the pipeline continues with others
- Failed steps are logged and recorded in metadata
- The final text is the last successful transformation

---

## Examples

### Request with Aphasia Mode Enabled

```json
{
  "prompt": "Explain quantum computing",
  "aphasia_mode": true,
  "moral_value": 0.5
}
```

### Response with Aphasia Detected and Repaired

```json
{
  "response": "Quantum computing uses qubits instead of classical bits...",
  "accepted": true,
  "phase": "wake",
  "aphasia_metadata": {
    "enabled": true,
    "detected": true,
    "severity": 0.4,
    "repaired": true,
    "note": null
  }
}
```

### Response with No Aphasia Detected

```json
{
  "response": "The answer to your question is...",
  "accepted": true,
  "phase": "wake",
  "aphasia_metadata": {
    "enabled": true,
    "detected": false,
    "severity": 0.0,
    "repaired": false,
    "note": null
  }
}
```

### Response with Aphasia Mode Disabled

When `aphasia_mode=false` (default), `aphasia_metadata` is `null`:

```json
{
  "response": "Generated response...",
  "accepted": true,
  "phase": "wake",
  "aphasia_metadata": null
}
```

---

## Test Commands

```bash
# Run speech governance contract tests
pytest tests/contracts/test_speech_contracts.py -v

# Run infer endpoint tests (includes aphasia_mode tests)
pytest tests/api/test_infer_contract.py -v

# Run all contract tests
pytest tests/contracts/ tests/api/test_infer_contract.py -v
```

---

## Related Documentation

- [API Contract](API_CONTRACT.md) - Main HTTP API contract
- [Engine Contract](API_engine_contract.md) - NeuroCognitiveEngine contract
- [APHASIA_SPEC.md](../APHASIA_SPEC.md) - Aphasia detection specification

---

## Document Maintenance

This contract should be updated when:
1. New aphasia detection patterns are added
2. AphasiaMetadata schema changes
3. Pipeline behavior is modified
4. New speech governors are added

**Owner:** Principal API & I/O Contract Engineer
