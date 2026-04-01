# Getting Started with MLSDM

**Quick guide to get up and running with MLSDM in under 5 minutes.**

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## Quick Installation

### Option 1: Minimal Installation (Recommended for First-Time Users)

Install just the core dependencies without optional features:

```bash
# Clone the repository
git clone https://github.com/neuron7xLab/mlsdm.git
cd mlsdm

# Install minimal core dependencies (excludes OpenTelemetry tracing)
pip install numpy sentence-transformers fastapi uvicorn pyyaml pydantic prometheus-client tenacity requests psutil
```

### Option 2: Full Installation (Includes All Features)

Install with all optional dependencies including OpenTelemetry distributed tracing:

```bash
# Clone the repository
git clone https://github.com/neuron7xLab/mlsdm.git
cd mlsdm

# Install all dependencies
pip install -r requirements.txt

# Optional: Install for development with testing tools
pip install -e ".[dev]"
```

## Your First MLSDM Wrapper

Create a file called `my_first_wrapper.py`:

```python
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

# 1. Define a simple LLM function (replace with your actual LLM)
def my_llm(prompt: str, max_tokens: int) -> str:
    """Simple stub LLM for testing - replace with OpenAI, Anthropic, etc."""
    return f"Echo: {prompt[:50]}..."

# 2. Define an embedding function (replace with your actual embedder)
def my_embedder(text: str) -> np.ndarray:
    """Simple stub embedder - replace with sentence-transformers, OpenAI, etc."""
    # For testing, return random embeddings
    # In production, use: sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
    return np.random.randn(384).astype(np.float32)

# 3. Create the governed wrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    dim=384,                        # Embedding dimension (must match your embedder)
    capacity=20_000,                # Memory capacity
    wake_duration=8,                # Wake phase steps
    sleep_duration=3,               # Sleep phase steps
    initial_moral_threshold=0.50    # Starting moral threshold
)

# 4. Generate with governance
result = wrapper.generate(
    prompt="Explain the benefits of cognitive governance",
    moral_value=0.8  # Higher value = more stringent moral filtering
)

# 5. View the results
print(f"✓ Response: {result['response']}")
print(f"✓ Accepted: {result['accepted']}")
print(f"✓ Current Phase: {result['phase']}")
print(f"✓ Moral Threshold: {result['moral_threshold']:.2f}")
```

Run it:

```bash
python my_first_wrapper.py
```

## Using Real LLMs

### With OpenAI

```python
from openai import OpenAI
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

client = OpenAI(api_key="your-api-key")

def openai_generate(prompt: str, max_tokens: int) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def openai_embed(text: str) -> np.ndarray:
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

wrapper = LLMWrapper(
    llm_generate_fn=openai_generate,
    embedding_fn=openai_embed,
    dim=1536  # Ada embedding dimension
)
```

### With Local Models (Hugging Face)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

# Load local models
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1")
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def local_generate(prompt: str, max_tokens: int) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=max_tokens)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def local_embed(text: str) -> np.ndarray:
    return embedder.encode(text).astype(np.float32)

wrapper = LLMWrapper(
    llm_generate_fn=local_generate,
    embedding_fn=local_embed,
    dim=384
)
```

## Running Tests

Verify your installation works:

```bash
# Run a simple test
pytest tests/unit/test_llm_wrapper.py -v

# Run all tests (may take several minutes)
pytest tests/ -v
```

## Common Configuration Options

### Disable Rate Limiting (for development)

```bash
export DISABLE_RATE_LIMIT=1
```

### Configure Memory Capacity

```python
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    dim=384,
    capacity=50_000,  # Increase memory capacity
)
```

### Adjust Moral Filtering

```python
# More permissive (threshold range: 0.30 - 0.90)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    dim=384,
    initial_moral_threshold=0.35  # Lower = more permissive
)
```

## Optional Features

### OpenTelemetry Distributed Tracing

If you want distributed tracing capabilities, install the observability extras:

```bash
pip install ".[observability]"
# OR
pip install opentelemetry-api opentelemetry-sdk
```

Then configure tracing:

```python
import os
os.environ["OTEL_EXPORTER_TYPE"] = "console"  # or "otlp" for production
os.environ["OTEL_SERVICE_NAME"] = "my-mlsdm-app"
```

**Note:** If OpenTelemetry is not installed, MLSDM will work perfectly fine without it - tracing will simply be disabled.

### Aphasia Detection (Speech Quality)

For speech quality detection and repair, install the neurolang extension:

```bash
pip install -r requirements-neurolang.txt
```

Then use `NeuroLangWrapper` instead of `LLMWrapper`:

```python
from mlsdm.extensions.neuro_lang_extension import NeuroLangWrapper

wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    dim=384
)
```

## Running as a Service

Start MLSDM as a FastAPI service using the canonical CLI:

```bash
# Development mode (recommended)
mlsdm serve --mode dev --reload --log-level debug

# OR use make targets (internally calls mlsdm serve)
make run-dev

# Cloud production mode
mlsdm serve --mode cloud-prod

# Agent/API mode
mlsdm serve --mode agent-api
```

**Legacy entrypoints** (deprecated but still supported):
```bash
# Deprecated (shows deprecation warning)
python -m mlsdm.entrypoints.dev
python -m mlsdm.entrypoints.cloud
python -m mlsdm.entrypoints.agent
```

Then access the API at `http://localhost:8000`:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "moral_value": 0.8}'
```

### Runtime Modes

MLSDM provides three runtime modes optimized for different scenarios:

- **dev**: Hot reload, debug logging, rate limiting disabled
- **cloud-prod**: Multiple workers, secure mode, structured logging
- **agent-api**: Optimized for LLM platform integration

See the [Runtime Modes section in README](../README.md#runtime-modes) for details.

## Next Steps

- **Full Documentation**: See [README.md](README.md) for complete features
- **Architecture**: Read [ARCHITECTURE_SPEC.md](ARCHITECTURE_SPEC.md) to understand the system design
- **Configuration**: Check [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for all options
- **API Reference**: See [API_REFERENCE.md](API_REFERENCE.md) for detailed API documentation
- **Examples**: Explore the [examples/](examples/) directory for more use cases

## Troubleshooting

### Import Error: No module named 'opentelemetry'

**Solution**: OpenTelemetry is optional. Either install it with:
```bash
pip install opentelemetry-api opentelemetry-sdk
```
Or just ignore it - MLSDM will work without tracing.

### Import Error: No module named 'sentence_transformers'

**Solution**: Install sentence-transformers:
```bash
pip install sentence-transformers
```

### Rate Limit Errors in Development

**Solution**: Disable rate limiting:
```bash
export DISABLE_RATE_LIMIT=1
```

## Verifying Key Metrics

Want to verify the documented effectiveness metrics? Here's how:

### Memory Footprint (29.37 MB claim)

```bash
# Install numpy if not already installed
pip install numpy

# Run memory benchmark
python benchmarks/measure_memory_footprint.py

# Expected output: ~29.37 MB (within 10% margin)
# Configuration: 20,000 vectors × 384 dimensions
```

### Effectiveness Metrics

```bash
# Install full dependencies
pip install -e .

# Moral filter effectiveness (93.3% toxic rejection)
pytest tests/validation/test_moral_filter_effectiveness.py -v -s

# Wake/sleep effectiveness (89.5% resource savings)
pytest tests/validation/test_wake_sleep_effectiveness.py -v -s

# Aphasia detection (100% TPR, 80% TNR on 100-sample corpus)
pytest tests/eval/test_aphasia_eval_suite.py -v
```

### Full Test Suite

```bash
# Run all tests (requires full install)
pytest tests/ --ignore=tests/load -v

# Run with coverage measurement
./coverage_gate.sh

# Expected: ~86% overall coverage, 3,600+ tests passing
```

See [CLAIMS_TRACEABILITY.md](CLAIMS_TRACEABILITY.md) for complete metric documentation.

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/neuron7xLab/mlsdm/issues)
- **Documentation**: [docs/index.md](index.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Welcome to MLSDM! 🧠**
