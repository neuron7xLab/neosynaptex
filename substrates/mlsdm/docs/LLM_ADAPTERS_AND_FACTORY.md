# LLM Adapters and Factory Pattern

## Overview

This document describes the LLM adapter architecture and factory pattern introduced in Phase 2-3 of the NeuroCognitiveEngine development.

## Architecture

### LLM Adapters

LLM adapters provide a consistent interface for different language model backends:

```python
Callable[[str, int], str]
# (prompt: str, max_tokens: int) -> str
```

**Available Adapters:**

1. **OpenAI Adapter** (`build_openai_llm_adapter`)
   - Connects to OpenAI's API
   - Requires `OPENAI_API_KEY` environment variable
   - Optional `OPENAI_MODEL` (default: "gpt-3.5-turbo")

2. **Local Stub Adapter** (`build_local_stub_llm_adapter`)
   - Deterministic mock for testing
   - No external dependencies
   - Returns predictable responses

### Factory Pattern

The factory pattern simplifies engine creation with environment-based configuration:

```python
from mlsdm.engine import build_neuro_engine_from_env

# Using local stub (default)
engine = build_neuro_engine_from_env()

# Using OpenAI
import os
os.environ["LLM_BACKEND"] = "openai"
os.environ["OPENAI_API_KEY"] = "sk-..."
engine = build_neuro_engine_from_env()
```

**Environment Variables:**
- `LLM_BACKEND`: "openai" or "local_stub" (default: "local_stub")
- `OPENAI_API_KEY`: Required when using OpenAI backend
- `OPENAI_MODEL`: Optional OpenAI model name
- `EMBEDDING_DIM`: Embedding dimensionality (default: 384)

## Usage Examples

### Basic Usage

```python
import os
from mlsdm.engine import build_neuro_engine_from_env

# Set backend
os.environ["LLM_BACKEND"] = "local_stub"

# Create engine
engine = build_neuro_engine_from_env()

# Generate response
result = engine.generate(
    prompt="Hello, how are you?",
    max_tokens=128,
    moral_value=0.5,
    user_intent="conversational"
)

print(result["response"])
print(result["timing"])
print(result["validation_steps"])
```

### Custom Configuration

```python
from mlsdm.engine import build_neuro_engine_from_env, NeuroEngineConfig

# Create custom config
config = NeuroEngineConfig(
    dim=384,
    capacity=10000,
    enable_fslgs=False,
    initial_moral_threshold=0.3
)

# Build engine with custom config
engine = build_neuro_engine_from_env(config=config)
```

### Using OpenAI Backend

```python
import os
from mlsdm.engine import build_neuro_engine_from_env

# Configure OpenAI
os.environ["LLM_BACKEND"] = "openai"
os.environ["OPENAI_API_KEY"] = "sk-your-api-key"
os.environ["OPENAI_MODEL"] = "gpt-4"  # Optional

# Create engine
engine = build_neuro_engine_from_env()

# Use normally
result = engine.generate("Explain quantum computing", max_tokens=512)
```

### Creating Custom Adapters

```python
from typing import Callable

def build_custom_llm_adapter() -> Callable[[str, int], str]:
    """Build a custom LLM adapter."""

    def llm_generate_fn(prompt: str, max_tokens: int) -> str:
        # Your custom implementation
        response = your_llm_call(prompt, max_tokens)
        return response

    return llm_generate_fn

# Use custom adapter
from mlsdm.engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.engine.factory import build_stub_embedding_fn

llm_fn = build_custom_llm_adapter()
embedding_fn = build_stub_embedding_fn(384)
config = NeuroEngineConfig()

engine = NeuroCognitiveEngine(
    llm_generate_fn=llm_fn,
    embedding_fn=embedding_fn,
    config=config
)
```

## CLI Demo

A command-line demo is available at `examples/neuro_engine_cli_demo.py`:

```bash
# Basic usage
python examples/neuro_engine_cli_demo.py --prompt "Hello!"

# With OpenAI
export OPENAI_API_KEY="sk-..."
python examples/neuro_engine_cli_demo.py --backend openai --prompt "Hello!"

# From stdin
echo "Tell me about AI" | python examples/neuro_engine_cli_demo.py

# Interactive mode
python examples/neuro_engine_cli_demo.py --interactive

# Verbose output
python examples/neuro_engine_cli_demo.py --prompt "Test" --verbose
```

**CLI Options:**
- `--backend`: Choose LLM backend (openai/local_stub)
- `--prompt`: Input prompt text
- `--max-tokens`: Maximum tokens to generate (default: 512)
- `--moral`: Moral threshold (0.0-1.0, default: 0.5)
- `--intent`: User intent category (default: conversational)
- `--verbose`: Show validation steps and JSON output
- `--interactive`: Run in interactive mode
- `--disable-fslgs`: Disable FSLGS layer

## Testing

### End-to-End Tests

E2E tests are located in `tests/e2e/test_neuro_cognitive_engine_stub_backend.py`:

```bash
# Run all e2e tests
pytest tests/e2e/ -v

# Run specific test
pytest tests/e2e/test_neuro_cognitive_engine_stub_backend.py::TestNeuroCognitiveEngineE2EStubBackend::test_e2e_basic_request_returns_response -v
```

**Test Coverage:**
- Basic request/response flow
- Moral rejection handling
- Response structure and JSON serialization
- Multiple request isolation
- Parameter propagation
- Custom configuration
- State persistence

### Unit Tests for Adapters

```python
def test_local_stub_adapter():
    llm_fn = build_local_stub_llm_adapter()
    response = llm_fn("Test prompt", max_tokens=100)
    assert "NEURO-RESPONSE:" in response
    assert "Test prompt" in response
```

## Response Structure

The engine returns a structured response:

```python
{
    "response": str,           # Generated text (may be empty if rejected)
    "governance": dict | None, # FSLGS output (if enabled)
    "mlsdm": dict | None,      # MLSDM state
    "timing": {                # Timing metrics in milliseconds
        "moral_precheck": float,
        "generation": float,
        "total": float
    },
    "validation_steps": [      # Validation step results
        {
            "step": str,
            "passed": bool,
            "score": float,     # Optional
            "threshold": float, # Optional
            "skipped": bool,    # Optional
            "reason": str       # Optional
        }
    ],
    "error": {                 # Error info (if any)
        "type": str,
        "message": str
    } | None,
    "rejected_at": str | None  # "pre_flight" or "generation" if rejected
}
```

## Best Practices

1. **Use the Factory Pattern**: Prefer `build_neuro_engine_from_env()` over direct instantiation for consistent configuration.

2. **Handle Adaptive Moral Filter**: The MLSDM moral filter adapts after each request. For tests, use low moral thresholds (0.3) or create fresh engine instances.

3. **Error Handling**: Always check `result["error"]` and `result["rejected_at"]` before using the response.

4. **Testing**: Use `local_stub` backend for tests to avoid external dependencies and ensure deterministic behavior.

5. **Environment Variables**: Set environment variables before importing to ensure proper configuration.

6. **Custom Configurations**: Use `NeuroEngineConfig` for production deployments with specific requirements.

## Troubleshooting

### "OPENAI_API_KEY environment variable is required"
- Set the `OPENAI_API_KEY` environment variable before calling `build_openai_llm_adapter()`.

### "Invalid LLM_BACKEND"
- Valid values are: "openai", "local_stub"
- Default is "local_stub" if not set

### Unexpected Rejections
- The moral filter adapts after each request
- Use lower moral thresholds (0.3) for testing
- Check `result["validation_steps"]` for details

### Empty Responses
- Check `result["error"]` for rejection reason
- Check `result["rejected_at"]` for rejection stage
- Review `result["validation_steps"]` for which checks failed

## Architecture Compliance

This implementation maintains the core MLSDM architecture:

✅ **Single Memory Source**: MLSDM remains the only source of truth
✅ **Pre-flight Checks**: Moral and grammar checks before generation
✅ **Structured Responses**: Consistent response format with timing and validation
✅ **Backward Compatibility**: All existing tests pass (415 tests)
✅ **No Breaking Changes**: Existing API preserved

## Future Extensions

Potential future enhancements:

- Additional LLM backends (Anthropic, local models, etc.)
- Real embedding function integration (sentence-transformers, OpenAI embeddings)
- Async adapter support
- Streaming response support
- Adapter health checks and metrics
- Configuration validation and type safety
- Adapter middleware/interceptors

## References

- [NeuroCognitiveEngine Documentation](../src/mlsdm/engine/neuro_cognitive_engine.py)
- [Adapter Implementation](../src/mlsdm/adapters/)
- [Factory Pattern](../src/mlsdm/engine/factory.py)
- [E2E Tests](../tests/e2e/)
- [CLI Demo](../examples/neuro_engine_cli_demo.py)
