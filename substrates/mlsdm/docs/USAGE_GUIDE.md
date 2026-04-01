# Usage Guide

**Document Version:** 1.2.0
**Project Version:** 1.2.0
**Last Updated:** December 2025
**Status:** See [status/READINESS.md](./status/READINESS.md) (not yet verified)

Comprehensive guide for using MLSDM Governed Cognitive Memory in your applications.

---

## Quick Start: Universal LLM Wrapper

The MLSDM system provides a governed wrapper for any LLM that enforces biological constraints and prevents degradation; readiness is tracked in [status/READINESS.md](./status/READINESS.md).

### Basic Integration

```python
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

# Step 1: Define your LLM generation function
def my_llm_generate(prompt: str, max_tokens: int) -> str:
    """
    Replace with your actual LLM:
    - OpenAI: openai.ChatCompletion.create(...)
    - Anthropic: anthropic.messages.create(...)
    - Local: your_model.generate(...)
    """
    return "Your LLM response here"

# Step 2: Define your embedding function
def my_embedding(text: str) -> np.ndarray:
    """
    Replace with your actual embeddings:
    - sentence-transformers: model.encode(text)
    - OpenAI: openai.Embedding.create(...)
    - Local: your_embedding_model(text)
    """
    return np.random.randn(384).astype(np.float32)

# Step 3: Create the wrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm_generate,
    embedding_fn=my_embedding,
    dim=384,                      # Embedding dimension
    capacity=20_000,              # Hard memory limit
    wake_duration=8,              # Wake cycle length
    sleep_duration=3,             # Sleep cycle length
    initial_moral_threshold=0.50  # Starting moral threshold
)

# Step 4: Generate with governance
result = wrapper.generate(
    prompt="Hello, how are you?",
    moral_value=0.8  # Moral score (0.0-1.0)
)

print(result["response"])
print(f"Accepted: {result['accepted']}, Phase: {result['phase']}")
```

## Key Parameters

### LLMWrapper Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_generate_fn` | Callable | Required | Your LLM function that takes (prompt, max_tokens) and returns response text |
| `embedding_fn` | Callable | Required | Your embedding function that takes text and returns numpy array |
| `dim` | int | 384 | Embedding dimension (must match your embeddings) |
| `capacity` | int | 20,000 | Maximum memory vectors (hard limit) |
| `wake_duration` | int | 8 | Number of steps in wake phase |
| `sleep_duration` | int | 3 | Number of steps in sleep phase |
| `initial_moral_threshold` | float | 0.50 | Starting moral threshold (0.30-0.90) |

### Generate Method

```python
result = wrapper.generate(
    prompt: str,              # User input text
    moral_value: float,       # Moral score 0.0-1.0 (higher = more acceptable)
    max_tokens: Optional[int], # Override default max tokens
    context_top_k: int = 5    # Number of context items to retrieve
)
```

**Returns:** Dictionary with:
- `response`: Generated text (empty if rejected)
- `accepted`: Boolean - whether request was accepted
- `phase`: Current phase ("wake" or "sleep")
- `step`: Current step counter
- `note`: Processing note (e.g., "processed", "morally rejected", "sleep phase")
- `moral_threshold`: Current moral threshold
- `context_items`: Number of context items retrieved
- `max_tokens_used`: Max tokens used for this generation

## Integration Examples

### Example 1: OpenAI Integration

```python
import openai
from sentence_transformers import SentenceTransformer
from mlsdm.core.llm_wrapper import LLMWrapper

# Initialize OpenAI
openai.api_key = "your-api-key"

# Initialize embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def openai_generate(prompt: str, max_tokens: int) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def openai_embed(text: str) -> np.ndarray:
    return embedder.encode(text, convert_to_numpy=True)

wrapper = LLMWrapper(
    llm_generate_fn=openai_generate,
    embedding_fn=openai_embed,
    dim=384
)

result = wrapper.generate("Explain quantum computing", moral_value=0.9)
print(result["response"])
```

### Example 2: Anthropic Integration

```python
import anthropic
from mlsdm.core.llm_wrapper import LLMWrapper

client = anthropic.Anthropic(api_key="your-api-key")

def anthropic_generate(prompt: str, max_tokens: int) -> str:
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

wrapper = LLMWrapper(
    llm_generate_fn=anthropic_generate,
    embedding_fn=your_embedding_function,
    dim=384
)
```

### Example 3: Local LLM (llama.cpp, HuggingFace)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from mlsdm.core.llm_wrapper import LLMWrapper

# Load local model
model = AutoModelForCausalLM.from_pretrained("your-model")
tokenizer = AutoTokenizer.from_pretrained("your-model")

def local_generate(prompt: str, max_tokens: int) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=max_tokens)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

wrapper = LLMWrapper(
    llm_generate_fn=local_generate,
    embedding_fn=your_embedding_function,
    dim=384
)
```

## Understanding the System

### Cognitive Phases

The system alternates between wake and sleep phases:

**Wake Phase (8 steps default):**
- Processes new requests
- Adds memories to buffer
- Retrieves fresh context (phase 0.1)
- Maximum 2048 tokens

**Sleep Phase (3 steps default):**
- Rejects new processing
- Consolidates buffered memories
- Forces short responses (150 tokens)
- Memory re-encoded with phase 0.9

### Moral Filtering

The system maintains adaptive moral homeostasis:

1. **Evaluation**: Compares moral_value against current threshold
2. **Adaptation**: Adjusts threshold to maintain ~50% acceptance rate
3. **Bounds**: Threshold stays in [0.30, 0.90] range
4. **EMA Tracking**: Exponential moving average of acceptance rate

**Moral Value Guidelines:**
- `0.9-1.0`: Highly positive, helpful content
- `0.7-0.9`: Normal, acceptable content
- `0.5-0.7`: Borderline content
- `0.3-0.5`: Questionable content
- `0.0-0.3`: Toxic, harmful content

### Memory Management

**Three-Level Synaptic Memory:**
- **L1**: Fast, high decay (λ=0.50) - immediate working memory
- **L2**: Medium decay (λ=0.10) - short-term memory
- **L3**: Slow decay (λ=0.01) - long-term memory

**PELM (Phase-Entangled Lattice Memory):**
- Fixed capacity (20,000 vectors)
- Phase-entangled storage
- Cosine similarity retrieval
- Zero-allocation after initialization

### Consolidation

During sleep phase transitions:
1. Wake memories buffered during processing
2. Sleep phase begins
3. Buffered memories re-encoded with sleep phase (0.9)
4. Buffer cleared
5. Consolidated memories available for future retrieval

## Advanced Usage

### Monitoring System State

```python
# Get current state
state = wrapper.get_state()

print(f"Steps: {state['step']}")
print(f"Phase: {state['phase']} (counter: {state['phase_counter']})")
print(f"Moral: threshold={state['moral_threshold']}, ema={state['moral_ema']}")
print(f"Accepted: {state['accepted_count']}")
print(f"Rejected: {state['rejected_count']}")
print(f"Memory: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")
print(f"Memory MB: {state['qilm_stats']['memory_mb']}")
print(f"Synaptic L1: {state['synaptic_norms']['L1']:.2f}")
print(f"Synaptic L2: {state['synaptic_norms']['L2']:.2f}")
print(f"Synaptic L3: {state['synaptic_norms']['L3']:.2f}")
```

### Custom Phase Durations

Adjust for your use case:

```python
# Long wake, short sleep (high throughput)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    wake_duration=20,   # Process many messages
    sleep_duration=2    # Quick consolidation
)

# Balanced (default)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    wake_duration=8,
    sleep_duration=3
)

# Frequent consolidation
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    wake_duration=5,
    sleep_duration=5    # Equal wake/sleep
)
```

### Adjusting Moral Threshold

```python
# Strict filtering (fewer acceptances)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    initial_moral_threshold=0.80  # High bar
)

# Lenient filtering (more acceptances)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    initial_moral_threshold=0.30  # Low bar
)

# Balanced (default)
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    initial_moral_threshold=0.50  # Middle ground
)
```

### Context Retrieval Control

```python
# Get more context
result = wrapper.generate(
    prompt="Complex question",
    moral_value=0.9,
    context_top_k=10  # Retrieve 10 context items
)

# Minimal context
result = wrapper.generate(
    prompt="Simple question",
    moral_value=0.9,
    context_top_k=1  # Just top match
)
```

## Performance Characteristics

### Memory Footprint

With default settings (20,000 capacity, 384 dimensions):
- **PELM**: 29.37 MB (fixed)
- **Synaptic Memory**: ~0.005 MB (3 x 384 x float32)
- **Total**: ~29.5 MB (well under 1.4 GB limit)

### Throughput

- **P50 latency**: ~2ms (process_event)
- **P95 latency**: ~10ms (with retrieval)
- **Throughput**: 5,500 ops/sec (verified)
- **Concurrency**: Thread-safe, tested at 1000+ parallel requests

### Scalability

The system maintains constant memory regardless of usage:
- 1,000 messages: 29.5 MB
- 10,000 messages: 29.5 MB
- 100,000 messages: 29.5 MB (memory wraps at capacity)

## Best Practices

### 1. Moral Value Scoring

Implement a moral scoring function:

```python
def score_moral_value(text: str) -> float:
    """Score moral acceptability of text."""
    # Option 1: Use a classifier
    # toxicity_score = toxicity_classifier(text)
    # return 1.0 - toxicity_score

    # Option 2: Simple heuristics
    bad_words = ["toxic", "harmful", "hate"]
    if any(word in text.lower() for word in bad_words):
        return 0.2
    return 0.9
```

### 2. Error Handling

```python
try:
    result = wrapper.generate(prompt, moral_value)
    if result["accepted"]:
        return result["response"]
    else:
        return f"Request rejected: {result['note']}"
except Exception as e:
    logging.error(f"Generation failed: {e}")
    return "An error occurred"
```

### 3. Monitoring

Track key metrics:

```python
import logging

def monitored_generate(wrapper, prompt, moral_value):
    result = wrapper.generate(prompt, moral_value)

    # Log rejections
    if not result["accepted"]:
        logging.warning(f"Rejected: {result['note']}")

    # Alert on sleep phase
    if result["phase"] == "sleep":
        logging.info("Sleep phase consolidation")

    # Track moral drift
    state = wrapper.get_state()
    if state["moral_threshold"] < 0.35:
        logging.warning("Moral threshold very low")

    return result
```

### 4. Graceful Degradation

Handle system limits:

```python
result = wrapper.generate(prompt, moral_value)

if not result["accepted"]:
    if "sleep phase" in result["note"]:
        # Wait and retry during wake
        time.sleep(1)
        result = wrapper.generate(prompt, moral_value)
    elif "morally rejected" in result["note"]:
        # Inform user
        return "This request cannot be processed due to content policy."
```

## Troubleshooting

### Issue: High rejection rate

**Solution**: Lower initial threshold or check moral_value scoring

```python
# Check current state
state = wrapper.get_state()
print(f"Threshold: {state['moral_threshold']}")
print(f"Rejected: {state['rejected_count']}/{state['step']}")

# Lower threshold
wrapper = LLMWrapper(..., initial_moral_threshold=0.40)
```

### Issue: Memory not being used

**Solution**: Verify embeddings are being generated correctly

```python
# Test embedding function
test_text = "Hello"
embedding = my_embedding(test_text)
print(f"Embedding shape: {embedding.shape}")
print(f"Embedding norm: {np.linalg.norm(embedding)}")
```

### Issue: Context not relevant

**Solution**: Increase context_top_k or check embedding quality

```python
# Retrieve more context
result = wrapper.generate(
    prompt="...",
    moral_value=0.9,
    context_top_k=10  # More context
)
```

## Local Stack (docker-compose)

The easiest way to run MLSDM locally is using docker-compose.

### Quick Start

```bash
# 1. Navigate to project directory
cd mlsdm

# 2. Start the local stack
docker compose -f docker/docker-compose.yaml up

# 3. Verify it's running
curl http://localhost:8000/health
# Output: {"status": "healthy"}

# 4. Test generation
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!", "moral_value": 0.8}'
```

### Background Mode

```bash
# Start in background
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

### Environment Customization

Create a `.env` file based on `env.dev.example`:

```bash
cp env.dev.example .env
# Edit .env to customize settings
```

Available environment variables:
- `LLM_BACKEND`: Backend type (`local_stub`, `openai`)
- `OPENAI_API_KEY`: API key for OpenAI backend
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `DISABLE_RATE_LIMIT`: Set to `1` to disable rate limiting

## Production Deployment

### Docker Example

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY examples/ examples/

CMD ["python", "examples/llm_wrapper_example.py"]
```

### FastAPI Integration

```python
from fastapi import FastAPI
from mlsdm.core.llm_wrapper import LLMWrapper

app = FastAPI()
wrapper = LLMWrapper(...)

@app.post("/generate")
async def generate(prompt: str, moral_value: float = 0.8):
    result = wrapper.generate(prompt, moral_value)
    return result
```

### Request Priority (REL-005)

When using the HTTP API, you can prioritize requests using the `X-MLSDM-Priority` header:

```bash
# High priority request - processed first under load
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-MLSDM-Priority: high" \
  -d '{"prompt": "Critical request that needs fast processing"}'

# Normal priority (default)
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Regular request"}'

# Low priority - processed last under load
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-MLSDM-Priority: low" \
  -d '{"prompt": "Background task"}'
```

**Priority Levels:**
- `high` (weight: 3): For critical, user-facing requests
- `normal` (weight: 2): Default for most requests
- `low` (weight: 1): For background tasks, batch processing

**Best Practices:**
- Don't overuse `high` priority - it loses meaning if everything is high priority
- Use `low` for batch processing, analytics, and non-time-sensitive tasks
- Default `normal` is appropriate for most interactive requests

## See Also

- [README.md](README.md) - Project overview
- [ARCHITECTURE_SPEC.md](ARCHITECTURE_SPEC.md) - Architecture details
- [EFFECTIVENESS_VALIDATION_REPORT.md](EFFECTIVENESS_VALIDATION_REPORT.md) - Validation results
- [examples/llm_wrapper_example.py](examples/llm_wrapper_example.py) - Code examples

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/neuron7xLab/mlsdm/issues
- Documentation: See README.md and inline code documentation
