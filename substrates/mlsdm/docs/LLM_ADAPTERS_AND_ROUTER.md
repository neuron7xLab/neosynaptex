# LLM Adapters and Router Configuration

This document describes the LLM backend system in MLSDM, including available adapters, routing strategies, and configuration options.

## Table of Contents

- [Overview](#overview)
- [Available Backends](#available-backends)
  - [Local Stub (Development)](#local-stub-development)
  - [OpenAI](#openai)
  - [Anthropic](#anthropic)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Multi-Provider Mode](#multi-provider-mode)
- [Routing Strategies](#routing-strategies)
  - [Single Provider](#single-provider)
  - [Rule-Based Router](#rule-based-router)
  - [A/B Test Router](#ab-test-router)
- [Error Handling](#error-handling)
- [Adding New Adapters](#adding-new-adapters)
- [Testing](#testing)

---

## Overview

MLSDM uses a pluggable adapter system for LLM backends, allowing you to:

1. **Switch backends** without code changes via environment variables
2. **Use multiple providers** with routing strategies (A/B testing, rule-based)
3. **Test locally** with the deterministic local_stub adapter
4. **Handle errors** consistently across all providers

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│  HTTP API       │────▶│  Router      │────▶│  LLM Provider  │
│  /generate      │     │  (optional)  │     │  - OpenAI      │
│                 │     │              │     │  - Anthropic   │
│                 │     │              │     │  - LocalStub   │
└─────────────────┘     └──────────────┘     └────────────────┘
```

---

## Available Backends

### Local Stub (Development)

The local stub adapter provides deterministic responses for testing and development without external API calls.

**When to use:**
- Local development
- CI/CD pipelines
- Unit/integration testing
- Demos and presentations

**Configuration:**
```bash
# Default - no configuration needed
export LLM_BACKEND=local_stub

# Optional: Custom provider ID for metrics/logging
export LOCAL_STUB_PROVIDER_ID=my_test_stub
```

**Response format:**
```
NEURO-RESPONSE: {prompt_preview} [Generated with max_tokens={n}]. This is a stub response...
```

### OpenAI

Integration with OpenAI's API (GPT-3.5, GPT-4, etc.).

**Requirements:**
- `openai` package: `pip install openai`
- Valid API key

**Configuration:**
```bash
export LLM_BACKEND=openai
export OPENAI_API_KEY=sk-your-api-key-here
export OPENAI_MODEL=gpt-3.5-turbo  # Optional, default: gpt-3.5-turbo
```

**Supported models:**
- `gpt-3.5-turbo` (default)
- `gpt-4`
- `gpt-4-turbo`
- `gpt-4o`

### Anthropic

Integration with Anthropic's Claude API.

**Requirements:**
- `anthropic` package: `pip install anthropic`
- Valid API key

**Configuration:**
```bash
export LLM_BACKEND=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-api-key-here
export ANTHROPIC_MODEL=claude-3-sonnet-20240229  # Optional
```

**Supported models:**
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229` (default)
- `claude-3-haiku-20240307`

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `local_stub` | Backend to use: `local_stub`, `openai`, `anthropic` |
| `OPENAI_API_KEY` | - | Required for OpenAI backend |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model name |
| `ANTHROPIC_API_KEY` | - | Required for Anthropic backend |
| `ANTHROPIC_MODEL` | `claude-3-sonnet-20240229` | Anthropic model name |
| `LOCAL_STUB_PROVIDER_ID` | `local_stub` | Custom ID for local stub |
| `MULTI_LLM_BACKENDS` | - | Multi-provider configuration |

### Multi-Provider Mode

For A/B testing or rule-based routing, configure multiple providers:

```bash
# Named providers
export MULTI_LLM_BACKENDS="control:local_stub,treatment:openai"

# Unnamed (uses backend as name)
export MULTI_LLM_BACKENDS="local_stub,openai"
```

---

## Routing Strategies

### Single Provider

Default mode - all requests go to one provider.

```python
from mlsdm.engine import build_neuro_engine_from_env

# Uses LLM_BACKEND env var
engine = build_neuro_engine_from_env()
result = engine.generate("Hello!", max_tokens=100)
```

### Rule-Based Router

Route requests based on metadata (mode, intent, priority).

```python
from mlsdm.engine import NeuroEngineConfig, build_neuro_engine_from_env

config = NeuroEngineConfig(
    router_mode="rule_based",
    rule_based_config={
        "deep": "openai",      # Complex queries → OpenAI
        "cheap": "local_stub", # Simple queries → Local stub
        "default": "local_stub"
    }
)

engine = build_neuro_engine_from_env(config=config)

# Routes to OpenAI
result = engine.generate("Complex analysis...", mode="deep")

# Routes to local_stub
result = engine.generate("Hello!", mode="cheap")
```

### A/B Test Router

Split traffic for experimentation.

```python
from mlsdm.engine import NeuroEngineConfig, build_neuro_engine_from_env

config = NeuroEngineConfig(
    router_mode="ab_test",
    ab_test_config={
        "control": "local_stub",
        "treatment": "openai",
        "treatment_ratio": 0.1  # 10% to treatment
    }
)

engine = build_neuro_engine_from_env(config=config)

# Automatically routes based on treatment_ratio
result = engine.generate("Test prompt")
# Result contains response, phase, accepted, and meta fields
print(result["response"])  # Generated text
print(result["meta"]["variant"])  # "control" or "treatment" (when using router)
print(result["meta"]["backend_id"])  # Provider ID used
```

---

## Error Handling

All providers raise consistent exceptions:

```python
from mlsdm.adapters import LLMProviderError, LLMTimeoutError

try:
    result = engine.generate("Test")
except LLMTimeoutError as e:
    print(f"Timeout from {e.provider_id}: {e.timeout_seconds}s")
except LLMProviderError as e:
    print(f"Provider error from {e.provider_id}: {e}")
    if e.original_error:
        print(f"Original: {e.original_error}")
```

**Exception hierarchy:**
```
Exception
└── LLMProviderError
    └── LLMTimeoutError
```

**HTTP API error responses:**

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

## Adding New Adapters

To add a new LLM provider:

1. **Create adapter class** in `src/mlsdm/adapters/`:

```python
# src/mlsdm/adapters/my_provider.py
from mlsdm.adapters.llm_provider import LLMProvider, LLMProviderError

class MyProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("MY_PROVIDER_API_KEY")
        if not self.api_key:
            raise ValueError("MY_PROVIDER_API_KEY required")

    def generate(self, prompt: str, max_tokens: int, **kwargs) -> str:
        try:
            # Your API call here
            return response_text
        except SomeAPIError as e:
            raise LLMProviderError(
                f"MyProvider error: {e}",
                provider_id=self.provider_id,
                original_error=e
            )

    @property
    def provider_id(self) -> str:
        return "my_provider"
```

2. **Register in factory** (`src/mlsdm/adapters/provider_factory.py`):

```python
from mlsdm.adapters.my_provider import MyProvider

def build_provider_from_env(backend: str | None = None, **kwargs) -> LLMProvider:
    # ... existing code ...
    elif backend == "my_provider":
        api_key = kwargs.get("api_key") or os.environ.get("MY_PROVIDER_API_KEY")
        return MyProvider(api_key=api_key)
```

3. **Export in `__init__.py`**:

```python
from .my_provider import MyProvider
__all__ = [..., "MyProvider"]
```

4. **Add tests** in `tests/unit/test_provider_factory.py`

---

## Testing

### Run adapter tests

```bash
# Unit tests for providers
pytest tests/unit/test_provider_factory.py -v

# Unit tests for router
pytest tests/unit/test_llm_router.py -v

# Integration tests with HTTP API
pytest tests/integration/test_api_with_adapters.py -v

# E2E tests
pytest tests/e2e/test_neuro_cognitive_engine_stub_backend.py -v
```

### Test with local stub

```bash
export LLM_BACKEND=local_stub
uvicorn mlsdm.api.app:app --port 8000

# Test endpoint
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "max_tokens": 100}'
```

### Test with OpenAI (requires API key)

```bash
export LLM_BACKEND=openai
export OPENAI_API_KEY=sk-your-key
uvicorn mlsdm.api.app:app --port 8000
```

---

## Quick Reference

| Task | Configuration |
|------|---------------|
| Local development | `LLM_BACKEND=local_stub` |
| Production OpenAI | `LLM_BACKEND=openai` + `OPENAI_API_KEY=...` |
| A/B testing | `router_mode=ab_test` + `MULTI_LLM_BACKENDS=...` |
| Route by mode | `router_mode=rule_based` + rules config |

For complete API documentation, see [API_REFERENCE.md](./API_REFERENCE.md).
