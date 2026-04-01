# MLSDM LLM API Specification

**Version:** 1.2.0
**Last Updated:** November 2025

Complete specification for MLSDM's LLM integration APIs.

## Overview

MLSDM provides three levels of LLM integration:

1. **HTTP API** - RESTful endpoints for service integration
2. **Python API** - Direct library integration
3. **CLI** - Command-line interface for testing and operations

---

## HTTP API

### Base URL

```
http://localhost:8000
```

### Authentication

Optional API key authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/infer
```

Set `API_KEY` environment variable to enable.

---

### POST /infer

**Primary endpoint for governed text generation.**

#### Request

```http
POST /infer HTTP/1.1
Content-Type: application/json

{
  "prompt": "string (required, min 1 char)",
  "moral_value": 0.5,       // float 0.0-1.0, default 0.5
  "max_tokens": 512,        // int 1-4096, optional
  "secure_mode": false,     // bool, default false
  "aphasia_mode": false,    // bool, default false
  "rag_enabled": true,      // bool, default true
  "context_top_k": 5,       // int 1-100, default 5
  "user_intent": null       // string, optional
}
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | Input text to process (min 1 char) |
| `moral_value` | float | 0.5 | Moral threshold (0.0=reject all, 1.0=accept all) |
| `max_tokens` | int | 512 | Maximum tokens to generate (1-4096) |
| `secure_mode` | bool | false | Boost moral threshold by +0.2 for security |
| `aphasia_mode` | bool | false | Enable telegraphic speech detection/repair |
| `rag_enabled` | bool | true | Enable RAG context retrieval from memory |
| `context_top_k` | int | 5 | Number of memory items to retrieve (1-100) |
| `user_intent` | string | null | Intent category (e.g., "conversational") |

#### Response (200 OK)

```json
{
  "response": "Generated text...",
  "accepted": true,
  "phase": "wake",
  "moral_metadata": {
    "threshold": 0.5,
    "secure_mode": false,
    "applied_moral_value": 0.8
  },
  "rag_metadata": {
    "enabled": true,
    "context_items_retrieved": 3,
    "top_k": 5
  },
  "aphasia_metadata": {
    "enabled": true,
    "detected": false,
    "severity": 0.0,
    "repaired": false
  },
  "timing": {
    "total": 15.2,
    "generation": 12.1,
    "moral_precheck": 0.5
  },
  "governance": null
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Generated text (empty if rejected) |
| `accepted` | bool | Whether request was accepted |
| `phase` | string | Current phase: "wake" or "sleep" |
| `moral_metadata` | object | Moral filtering details |
| `rag_metadata` | object | RAG retrieval details |
| `aphasia_metadata` | object | Aphasia detection (if enabled) |
| `timing` | object | Performance timing in milliseconds |
| `governance` | object | FSLGS governance state (if enabled) |

#### Error Responses

**400 Bad Request - Validation Error**
```json
{
  "error": {
    "error_type": "validation_error",
    "message": "Prompt cannot be empty",
    "details": {"field": "prompt"}
  }
}
```

**422 Unprocessable Entity - Schema Validation**
```json
{
  "detail": [
    {"loc": ["body", "moral_value"], "msg": "ensure this value is <= 1.0", "type": "value_error"}
  ]
}
```

**429 Too Many Requests - Rate Limit**
```json
{
  "error": {
    "error_type": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Maximum 5 requests per second.",
    "details": null
  }
}
```

**500 Internal Server Error**
```json
{
  "error": {
    "error_type": "internal_error",
    "message": "An internal error occurred. Please try again later.",
    "details": null
  }
}
```

---

### POST /generate

**Simplified generation endpoint.**

#### Request

```json
{
  "prompt": "string (required)",
  "max_tokens": 512,
  "moral_value": 0.5
}
```

#### Response

```json
{
  "response": "Generated text...",
  "phase": "wake",
  "accepted": true,
  "metrics": {"timing": {"total": 15.2}},
  "safety_flags": {
    "validation_steps": [...],
    "rejected_at": null
  },
  "memory_stats": {
    "step": 1,
    "moral_threshold": 0.5,
    "context_items": 3
  }
}
```

---

### GET /health

**Basic health check.**

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

---

### GET /status

**Extended status with system information.**

```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "status": "ok",
  "version": "1.2.0",
  "backend": "local_stub",
  "system": {
    "memory_mb": 125.4,
    "cpu_percent": 12.5
  },
  "config": {
    "dimension": 384,
    "rate_limiting_enabled": true
  }
}
```

---

### GET /metrics

**Prometheus metrics endpoint.**

```bash
curl http://localhost:8000/metrics
```

Returns Prometheus-formatted text:
```
# HELP neuro_requests_total Total number of requests
# TYPE neuro_requests_total counter
neuro_requests_total 42
```

---

## Python API

### Quick Start

```python
from mlsdm import create_neuro_engine

engine = create_neuro_engine()
result = engine.generate("Hello, world!")
print(result["response"])
```

### Public Imports

```python
from mlsdm import (
    # Core classes
    LLMWrapper,
    NeuroCognitiveEngine,
    NeuroEngineConfig,
    NeuroCognitiveClient,

    # Speech governance
    SpeechGovernor,
    SpeechGovernanceResult,
    PipelineSpeechGovernor,

    # Factory functions
    create_llm_wrapper,
    create_neuro_engine,
    build_neuro_engine_from_env,
    build_stub_embedding_fn,

    # Version
    __version__,
)
```

### Factory Functions

#### create_neuro_engine()

```python
def create_neuro_engine(
    config: NeuroEngineConfig | None = None,
    llm_generate_fn: Callable[[str, int], str] | None = None,
    embedding_fn: Callable[[str], np.ndarray] | None = None,
) -> NeuroCognitiveEngine:
```

Creates a NeuroCognitiveEngine with sensible defaults.

#### create_llm_wrapper()

```python
def create_llm_wrapper(
    llm_generate_fn: Callable | None = None,
    embedding_fn: Callable | None = None,
    dim: int = 384,
    capacity: int = 20_000,
    wake_duration: int = 8,
    sleep_duration: int = 3,
    initial_moral_threshold: float = 0.50,
    speech_governor: SpeechGovernor | None = None,
) -> LLMWrapper:
```

Creates an LLMWrapper with cognitive governance.

### NeuroCognitiveEngine.generate()

```python
def generate(
    prompt: str,
    *,
    max_tokens: int = 512,
    user_intent: str | None = None,
    cognitive_load: float | None = None,
    moral_value: float | None = None,
    context_top_k: int | None = None,
    enable_diagnostics: bool = True,
) -> dict[str, Any]:
```

**Returns:**
```python
{
    "response": str,          # Generated text
    "governance": dict,       # FSLGS state
    "mlsdm": dict,           # MLSDM state
    "timing": dict,          # Timing metrics
    "validation_steps": list, # Validation history
    "error": dict | None,    # Error info
    "rejected_at": str | None # Rejection stage
}
```

### LLMWrapper.generate()

```python
def generate(
    prompt: str,
    moral_value: float,
    max_tokens: int | None = None,
    context_top_k: int | None = None,
) -> dict[str, Any]:
```

**Returns:**
```python
{
    "response": str,
    "accepted": bool,
    "phase": str,
    "step": int,
    "note": str,
    "moral_threshold": float,
    "context_items": int,
    "max_tokens_used": int,
    "speech_governance": dict | None
}
```

### LLMWrapper.get_state()

```python
def get_state() -> dict[str, Any]:
```

**Returns:**
```python
{
    "step": int,
    "phase": str,
    "phase_counter": int,
    "moral_threshold": float,
    "moral_ema": float,
    "accepted_count": int,
    "rejected_count": int,
    "synaptic_norms": {"L1": float, "L2": float, "L3": float},
    "pelm_stats": {"capacity": int, "used": int, "memory_mb": float},
    "consolidation_buffer_size": int,
    "reliability": {
        "stateless_mode": bool,
        "circuit_breaker_state": str,
        "pelm_failure_count": int,
        "embedding_failure_count": int,
        "llm_failure_count": int
    }
}
```

---

## CLI API

### Usage

```bash
mlsdm [command] [options]
```

### Commands

#### mlsdm demo

Interactive demo mode:

```bash
# Interactive chat
mlsdm demo --interactive

# Single prompt
mlsdm demo -p "Hello, world!"

# With options
mlsdm demo -p "Test" -m 0.9 --moral-threshold 0.5 --verbose
```

Options:
- `-i, --interactive` - Interactive mode
- `-p, --prompt TEXT` - Single prompt
- `-m, --moral-value FLOAT` - Moral value (default: 0.8)
- `--moral-threshold FLOAT` - Initial threshold (default: 0.5)
- `--wake-duration INT` - Wake steps (default: 8)
- `--sleep-duration INT` - Sleep steps (default: 3)
- `-v, --verbose` - Verbose output

#### mlsdm serve

Start HTTP server:

```bash
mlsdm serve --port 8000 --host 0.0.0.0
```

Options:
- `--host TEXT` - Host (default: 0.0.0.0)
- `--port INT` - Port (default: 8000)
- `--config PATH` - Config file path
- `--backend [local_stub|openai]` - LLM backend
- `--log-level [debug|info|warning|error]`
- `--reload` - Auto-reload (dev mode)
- `--disable-rate-limit` - Disable rate limiting

#### mlsdm check

Environment check:

```bash
mlsdm check
mlsdm check --verbose
```

Options:
- `-v, --verbose` - Show full status JSON

---

## Modes and Features

### Secure Mode

In `/infer`, `secure_mode=true` increases the effective moral threshold by 0.2:

```
effective_threshold = min(1.0, moral_value + 0.2)
```

### Aphasia Mode

When `aphasia_mode=true`, the system detects and repairs telegraphic speech patterns (Broca's aphasia indicators):
- Short sentences
- Missing function words
- Sentence fragments

### RAG Mode

When `rag_enabled=true` (default):
- Retrieves `context_top_k` related items from memory
- Enhances prompts with retrieved context
- Records retrieval metrics

Set `rag_enabled=false` to disable context retrieval.

### Cognitive Phases

- **Wake Phase**: Normal processing, accepts requests
- **Sleep Phase**: Rejects new requests, consolidates memory

The system cycles between phases automatically based on `wake_duration` and `sleep_duration`.

---

## Error Codes

| Code | Type | Description |
|------|------|-------------|
| 400 | validation_error | Invalid input format |
| 422 | unprocessable | Schema validation failed |
| 429 | rate_limit_exceeded | Too many requests |
| 500 | internal_error | Server error |

---

## Rate Limiting

Default: 5 requests per second per client.

Disable for testing:
```bash
export DISABLE_RATE_LIMIT=1
```

---

## Version History

- **1.2.0** - Added /infer endpoint, CLI, public API facade
- **1.1.0** - Added speech governance, metrics
- **1.0.0** - Initial release

---

**See Also:**
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
