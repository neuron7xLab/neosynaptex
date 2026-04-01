# SDK Usage Guide

**Document Version:** 1.2.0
**Last Updated:** December 2025
**Status:** Production

This guide provides practical usage examples for the MLSDM SDK client (`NeuroCognitiveClient`).

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Client Initialization](#client-initialization)
- [Generation Methods](#generation-methods)
- [Error Handling](#error-handling)
- [Response Structure](#response-structure)
- [Configuration](#configuration)

---

## Installation

```bash
pip install mlsdm-governed-cognitive-memory
```

---

## Quick Start

```python
from mlsdm.sdk import NeuroCognitiveClient

# Initialize with local stub backend (no API key required)
client = NeuroCognitiveClient(backend="local_stub")

# Generate a response
result = client.generate("What is consciousness?")
print(result["response"])
```

---

## Client Initialization

### Local Stub Backend (Default)

For testing and development without external API dependencies:

```python
from mlsdm.sdk import NeuroCognitiveClient

client = NeuroCognitiveClient(backend="local_stub")
```

### OpenAI Backend

For production use with OpenAI:

```python
from mlsdm.sdk import NeuroCognitiveClient

client = NeuroCognitiveClient(
    backend="openai",
    api_key="sk-...",  # Or set OPENAI_API_KEY environment variable
    model="gpt-4"      # Optional, defaults to "gpt-3.5-turbo"
)
```

### Custom Configuration

```python
from mlsdm.sdk import NeuroCognitiveClient
from mlsdm.engine import NeuroEngineConfig

config = NeuroEngineConfig(
    dim=512,
    enable_fslgs=False,
    initial_moral_threshold=0.6
)

client = NeuroCognitiveClient(backend="local_stub", config=config)
```

---

## Generation Methods

### Basic Generation (`generate`)

Returns a dictionary with full response data:

```python
result = client.generate(
    prompt="Explain quantum computing",
    max_tokens=256,
    moral_value=0.7,
    context_top_k=5
)

print(f"Response: {result['response']}")
print(f"Phase: {result['mlsdm']['phase']}")
print(f"Timing: {result['timing']}")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | Required | Input text prompt |
| `max_tokens` | int | None | Maximum tokens to generate |
| `moral_value` | float | None | Moral threshold (0.0-1.0) |
| `user_intent` | str | None | Intent category |
| `cognitive_load` | float | None | Cognitive load (0.0-1.0) |
| `context_top_k` | int | None | Context items to retrieve |

### Typed Generation (`generate_typed`)

Returns a strongly-typed `GenerateResponseDTO`:

```python
from mlsdm.sdk import NeuroCognitiveClient, GenerateResponseDTO

client = NeuroCognitiveClient()
result: GenerateResponseDTO = client.generate_typed(
    prompt="What is the meaning of life?",
    moral_value=0.8
)

# Access typed fields
print(f"Response: {result.response}")
print(f"Accepted: {result.accepted}")
print(f"Phase: {result.phase}")
print(f"Moral Score: {result.moral_score}")

# Access cognitive state
if result.cognitive_state:
    print(f"Stateless Mode: {result.cognitive_state.stateless_mode}")
    print(f"Emergency Shutdown: {result.cognitive_state.emergency_shutdown}")
```

---

## Error Handling

The SDK provides specific exception types for different error scenarios:

```python
from mlsdm.sdk import (
    NeuroCognitiveClient,
    MLSDMError,
    MLSDMClientError,
    MLSDMServerError,
    MLSDMTimeoutError,
)

client = NeuroCognitiveClient()

try:
    result = client.generate("Test prompt")
except MLSDMClientError as e:
    # Client-side errors (4xx equivalent)
    print(f"Client error: {e}")
    print(f"Error code: {e.error_code}")
except MLSDMServerError as e:
    # Server-side errors (5xx equivalent)
    print(f"Server error: {e}")
    print(f"Error code: {e.error_code}")
except MLSDMTimeoutError as e:
    # Timeout errors
    print(f"Timeout: {e}")
    print(f"Timeout seconds: {e.timeout_seconds}")
except MLSDMError as e:
    # Base exception for all SDK errors
    print(f"SDK error: {e}")
```

### Exception Hierarchy

```
MLSDMError (base)
├── MLSDMClientError  # Validation, bad input
├── MLSDMServerError  # Internal errors
└── MLSDMTimeoutError # Request timeouts
```

---

## Response Structure

### Dictionary Response (from `generate`)

```python
{
    "response": "Generated text...",
    "governance": {...},
    "mlsdm": {
        "phase": "wake",
        "step": 42,
        "moral_threshold": 0.5,
        "context_items": 3,
        ...
    },
    "timing": {
        "total": 15.2,
        "llm_call_ms": 10.5,
        ...
    },
    "validation_steps": ["moral_filter", ...],
    "error": null,
    "rejected_at": null
}
```

### GenerateResponseDTO (from `generate_typed`)

| Field | Type | Description |
|-------|------|-------------|
| `response` | str | Generated text |
| `accepted` | bool | Whether request was accepted |
| `phase` | str | Current cognitive phase |
| `moral_score` | float \| None | Moral score used |
| `aphasia_flags` | dict \| None | Aphasia detection |
| `emergency_shutdown` | bool | Emergency shutdown state |
| `cognitive_state` | CognitiveStateDTO \| None | Cognitive state snapshot |
| `metrics` | dict \| None | Performance metrics |
| `safety_flags` | dict \| None | Safety validation |
| `memory_stats` | dict \| None | Memory statistics |
| `governance` | dict \| None | Governance state |
| `timing` | dict \| None | Timing info |
| `validation_steps` | list | Validation steps |
| `error` | dict \| None | Error info |
| `rejected_at` | str \| None | Rejection stage |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BACKEND` | Backend type | "local_stub" |
| `OPENAI_API_KEY` | OpenAI API key | None |
| `OPENAI_MODEL` | OpenAI model | "gpt-3.5-turbo" |

### NeuroEngineConfig Options

```python
from mlsdm.engine import NeuroEngineConfig

config = NeuroEngineConfig(
    dim=384,                      # Embedding dimension
    enable_fslgs=False,           # FSLGS governance
    enable_metrics=True,          # Performance metrics
    initial_moral_threshold=0.5,  # Starting moral threshold
)
```

---

## Best Practices

1. **Use `generate_typed` for type safety** when building applications
2. **Handle exceptions** appropriately for production robustness
3. **Set `moral_value`** explicitly for consistent filtering behavior
4. **Monitor `phase`** to understand cognitive rhythm state

---

## See Also

- [API_CONTRACT.md](docs/API_CONTRACT.md) - HTTP API contract
- [API_REFERENCE.md](API_REFERENCE.md) - Full API reference
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Configuration options

---

**Version:** 1.0.0
**Last Updated:** November 2025
**Maintainer:** neuron7x
