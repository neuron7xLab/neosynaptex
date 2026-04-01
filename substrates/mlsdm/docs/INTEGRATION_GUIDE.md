# MLSDM Integration Guide

**Version:** 1.2.0
**Last Updated:** November 2025

This guide helps you integrate MLSDM into your application in under 30 minutes.

## Table of Contents

- [Quick Start (5 minutes)](#quick-start)
- [Python API Integration](#python-api-integration)
- [HTTP API Integration](#http-api-integration)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
pip install -e .
# Or from requirements
pip install -r requirements.txt
```

### 10-Line Integration

```python
from mlsdm import create_neuro_engine

# Create engine with sensible defaults
engine = create_neuro_engine()

# Generate governed response
result = engine.generate("Tell me about machine learning")

print(result["response"])              # Generated text
print(result["mlsdm"]["accepted"])     # True if accepted
print(result["timing"]["total"])       # Timing in milliseconds
```

That's it! The engine handles moral filtering, memory management, and cognitive rhythm automatically.

---

## Python API Integration

### Option 1: High-Level Engine (Recommended)

```python
from mlsdm import create_neuro_engine, NeuroEngineConfig

# Custom configuration
config = NeuroEngineConfig(
    dim=384,                      # Embedding dimension
    enable_fslgs=False,           # FSLGS governance (optional)
    enable_metrics=True,          # Enable Prometheus metrics
    initial_moral_threshold=0.5,  # Starting moral filter
)

engine = create_neuro_engine(config=config)

# Generate with parameters
result = engine.generate(
    prompt="Explain quantum computing",
    max_tokens=256,
    moral_value=0.8,        # Moral score for this request
    user_intent="educational",
    context_top_k=5,        # RAG context items
)

# Check result
if result["error"] is None:
    print(f"Response: {result['response']}")
    print(f"Timing: {result['timing']}")
else:
    print(f"Error: {result['error']}")
```

### Option 2: Low-Level LLMWrapper

For direct LLM integration with cognitive governance:

```python
from mlsdm import create_llm_wrapper

# With custom LLM function
def my_llm(prompt: str, max_tokens: int) -> str:
    # Your LLM call here (OpenAI, Anthropic, local model, etc.)
    return "Generated response..."

def my_embedding(text: str) -> np.ndarray:
    # Your embedding function
    return np.random.randn(384).astype(np.float32)

wrapper = create_llm_wrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedding,
    dim=384,
    capacity=20_000,          # Memory capacity
    wake_duration=8,          # Wake phase steps
    sleep_duration=3,         # Sleep phase steps
    initial_moral_threshold=0.5,
)

# Generate
result = wrapper.generate(
    prompt="Hello, how are you?",
    moral_value=0.9
)

if result["accepted"]:
    print(result["response"])
else:
    print(f"Rejected: {result['note']}")

# Get system state
state = wrapper.get_state()
print(f"Phase: {state['phase']}")
print(f"Memory used: {state['pelm_stats']['used']}/{state['pelm_stats']['capacity']}")
```

### Option 3: SDK Client

```python
from mlsdm import NeuroCognitiveClient

# Local testing (no API key needed)
client = NeuroCognitiveClient(backend="local_stub")

# Or with OpenAI
# client = NeuroCognitiveClient(
#     backend="openai",
#     api_key="sk-...",
#     model="gpt-4"
# )

# Or with Anthropic
# client = NeuroCognitiveClient(
#     backend="anthropic",
#     api_key="sk-ant-...",
#     model="claude-3-sonnet-20240229"
# )

result = client.generate(
    prompt="What is consciousness?",
    max_tokens=256,
    moral_value=0.7
)
print(result["response"])
```

---

## HTTP API Integration

### Starting the Server

```bash
# Using CLI
mlsdm serve --port 8000

# Or directly with uvicorn
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000
```

### Endpoints

#### POST /infer (Recommended)

Extended inference with governance options:

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain AI safety",
    "moral_value": 0.8,
    "max_tokens": 256,
    "secure_mode": false,
    "aphasia_mode": false,
    "rag_enabled": true,
    "context_top_k": 5
  }'
```

**Request Parameters:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | required | Input text |
| `moral_value` | float | 0.5 | Moral threshold (0.0-1.0) |
| `max_tokens` | int | 512 | Max generation tokens |
| `secure_mode` | bool | false | Enhanced security filtering |
| `aphasia_mode` | bool | false | Detect/repair telegraphic speech |
| `rag_enabled` | bool | true | Enable RAG context retrieval |
| `context_top_k` | int | 5 | Number of context items |

**Response:**

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
  "aphasia_metadata": null,
  "timing": {
    "total": 15.2,
    "generation": 12.1
  }
}
```

#### POST /generate

Basic generation (simpler interface):

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!"}'
```

#### GET /health

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

#### GET /status

```bash
curl http://localhost:8000/status
# {"status": "ok", "version": "1.2.0", "backend": "local_stub", ...}
```

#### GET /metrics

Prometheus-compatible metrics:

```bash
curl http://localhost:8000/metrics
```

---

## CLI Usage

### Installation

The CLI is installed automatically with the package:

```bash
pip install -e .
mlsdm --version  # mlsdm 1.2.0
```

### Commands

#### Check Environment

```bash
mlsdm check
# Validates Python version, dependencies, configuration
```

#### Interactive Demo

```bash
# Interactive chat
mlsdm demo --interactive

# Single prompt
mlsdm demo -p "Tell me about Python"

# With custom settings
mlsdm demo -p "Hello" --moral-value 0.9 --moral-threshold 0.5
```

#### Start Server

```bash
# Default settings
mlsdm serve

# Custom port and host
mlsdm serve --host 127.0.0.1 --port 8080

# With specific backend
mlsdm serve --backend openai

# Development mode with auto-reload
mlsdm serve --reload --log-level debug
```

---

## Examples

### Example 1: Governed Chat (Basic)

```python
from mlsdm import create_neuro_engine

engine = create_neuro_engine()

# Simulate conversation
prompts = [
    "Hello, how can you help me?",
    "What is machine learning?",
    "Can you explain neural networks?",
]

for prompt in prompts:
    result = engine.generate(prompt, moral_value=0.8)

    if result["accepted"]:
        print(f"User: {prompt}")
        print(f"MLSDM: {result['response'][:100]}...")
        print(f"Phase: {result['mlsdm']['phase']}")
        print("---")
```

### Example 2: RAG Task (Context Retrieval)

```python
from mlsdm import create_llm_wrapper

# Build knowledge base
wrapper = create_llm_wrapper(wake_duration=20)

# Add documents
docs = [
    "Python is a programming language",
    "Machine learning uses statistical models",
    "Neural networks have layers of neurons",
]

for doc in docs:
    wrapper.generate(doc, moral_value=0.95)

# Query with RAG context
result = wrapper.generate(
    prompt="What programming language is good for ML?",
    moral_value=0.85,
    context_top_k=3  # Retrieve 3 related items
)

print(f"Answer: {result['response']}")
print(f"Context items used: {result['context_items']}")
```

### Example 3: Secure Mode Processing

```python
import httpx

response = httpx.post(
    "http://localhost:8000/infer",
    json={
        "prompt": "Process this sensitive request",
        "secure_mode": True,    # Raises moral threshold
        "moral_value": 0.6,
        "rag_enabled": True,
    }
)

data = response.json()
print(f"Accepted: {data['accepted']}")
print(f"Effective moral: {data['moral_metadata']['applied_moral_value']}")
# secure_mode adds 0.2 to moral_value -> 0.8 effective threshold
```

### Example 4: Speech Governance

```python
from mlsdm import (
    SpeechGovernanceResult,
    PipelineSpeechGovernor,
    create_llm_wrapper,
)

# Custom governor
class FormalStyleGovernor:
    def __call__(self, *, prompt, draft, max_tokens):
        formal = draft.replace("don't", "do not").replace("can't", "cannot")
        return SpeechGovernanceResult(
            final_text=formal,
            raw_text=draft,
            metadata={"style": "formal"}
        )

# Use in wrapper
wrapper = create_llm_wrapper(
    speech_governor=FormalStyleGovernor()
)

result = wrapper.generate("Test", moral_value=0.9)
print(result["speech_governance"])
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `local_stub` | Backend: `local_stub`, `openai`, `anthropic` |
| `OPENAI_API_KEY` | - | Required for OpenAI backend |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model name |
| `ANTHROPIC_API_KEY` | - | Required for Anthropic backend |
| `ANTHROPIC_MODEL` | `claude-3-sonnet-20240229` | Anthropic model name |
| `CONFIG_PATH` | `config/default_config.yaml` | Configuration file path |
| `DISABLE_RATE_LIMIT` | - | Set to `1` to disable rate limiting |

### Configuration File

```yaml
# config/production.yaml
dimension: 384
pelm:
  capacity: 20000
  phase_tolerance: 0.15
cognitive_rhythm:
  wake_duration: 8
  sleep_duration: 3
moral_filter:
  threshold: 0.50
  adapt_rate: 0.05
```

---

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed
pip install -e .

# Check installation
mlsdm check
```

### Memory Issues

```python
# Reduce capacity for low-memory environments
wrapper = create_llm_wrapper(capacity=5000)
```

### Rate Limiting

```bash
# Disable for testing
export DISABLE_RATE_LIMIT=1
mlsdm serve
```

### Sleep Phase Rejections

Requests during sleep phase are rejected. Increase wake_duration:

```python
wrapper = create_llm_wrapper(wake_duration=20, sleep_duration=2)
```

---

## End-to-End Examples

Ready-to-run example scripts are available in the `examples/` directory:

### SDK Examples

**Basic SDK Usage** (`examples/example_basic_sdk.py`):
```bash
python examples/example_basic_sdk.py
```

Demonstrates:
- NeuroCognitiveClient usage
- LLMWrapper generation
- NeuroCognitiveEngine
- Moral filtering behavior

### HTTP API Examples

**HTTP Client** (`examples/example_http_client.py`):
```bash
# Start server first
mlsdm serve

# In another terminal
python examples/example_http_client.py
```

Demonstrates:
- Health check endpoints
- Generate endpoint
- Extended inference with governance options
- Prometheus metrics

### Additional Examples

| Example | Description |
|---------|-------------|
| `llm_wrapper_example.py` | Detailed LLM wrapper usage with mock LLM |
| `http_inference_example.py` | HTTP API interaction patterns |
| `production_chatbot_example.py` | Full chatbot integration |
| `observability_metrics_example.py` | Prometheus metrics usage |

### Sample Response

Calling `/infer` endpoint:

```json
{
  "response": "Machine learning is a subset of artificial intelligence...",
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
  "timing": {
    "total": 15.2,
    "generation": 12.1
  }
}
```

---

## Next Steps

- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [ARCHITECTURE_SPEC.md](ARCHITECTURE_SPEC.md) - System architecture
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Advanced configuration
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production deployment

---

**Version:** 1.2.0 | **Updated:** December 2025
