# Troubleshooting Guide

**Common issues and solutions for MLSDM**

## Table of Contents

- [Installation Issues](#installation-issues)
- [Import Errors](#import-errors)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Configuration Problems](#configuration-problems)
- [API Errors](#api-errors)
- [Testing Issues](#testing-issues)
- [Getting Help](#getting-help)

---

## Installation Issues

### Issue: `pip install` fails with dependency conflicts

**Symptoms:**
```
ERROR: Cannot install mlsdm because these package versions have conflicting dependencies
```

**Solutions:**

1. **Use a clean virtual environment:**
   ```bash
   python -m venv mlsdm-env
   source mlsdm-env/bin/activate  # On Windows: mlsdm-env\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Install minimal dependencies first:**
   ```bash
   # Install only core deps without optional features
   pip install numpy sentence-transformers fastapi uvicorn pyyaml pydantic prometheus-client tenacity requests psutil
   ```

3. **Check Python version:**
   ```bash
   python --version  # Should be 3.10 or higher
   ```

### Issue: Installing OpenTelemetry takes too long

**Symptoms:**
- Slow installation
- Large download sizes

**Solution:**

OpenTelemetry is now optional! Skip it for faster installation:

```bash
# Install without OpenTelemetry
pip install numpy sentence-transformers fastapi uvicorn pyyaml pydantic prometheus-client tenacity requests psutil

# Only install if you need distributed tracing
pip install ".[observability]"
```

---

## Import Errors

### Issue: `ModuleNotFoundError: No module named 'opentelemetry'`

**Symptoms:**
```python
from opentelemetry import trace
ModuleNotFoundError: No module named 'opentelemetry'
```

**Solution:**

✅ **This is expected and OK!** OpenTelemetry is an optional dependency.

**Important:** Importing `mlsdm` and using the core system does NOT require OpenTelemetry:
```python
import mlsdm  # ✓ This works without OTEL
from mlsdm import LLMWrapper  # ✓ This works too
```

You'll only see this error if you directly import from `opentelemetry` in your own code without having it installed.

**Options:**
1. **Do nothing** - MLSDM works perfectly without OpenTelemetry (tracing is disabled)
2. **Install it** only if you need distributed tracing:
   ```bash
   pip install ".[observability]"
   # OR
   pip install opentelemetry-api opentelemetry-sdk
   ```

### Issue: `ModuleNotFoundError: No module named 'mlsdm'`

**Symptoms:**
```python
import mlsdm
ModuleNotFoundError: No module named 'mlsdm'
```

**Solutions:**

1. **Install the package:**
   ```bash
   cd /path/to/mlsdm
   pip install -e .
   ```

2. **Or add to Python path:**
   ```python
   import sys
   sys.path.insert(0, '/path/to/mlsdm/src')
   import mlsdm
   ```

### Issue: `ImportError: cannot import name 'SpanKind'`

**Symptoms:**
```python
from opentelemetry.trace import SpanKind
ImportError: cannot import name 'SpanKind' from 'opentelemetry.trace'
```

**Solution:**

This is an internal compatibility issue. Update to the latest MLSDM version which handles missing OpenTelemetry gracefully:

```bash
git pull origin main
```

---

## Runtime Errors

### Issue: Rate limit errors in development

**Symptoms:**
```
HTTPException: 429 Too Many Requests - Rate limit exceeded
```

**Solution:**

Disable rate limiting for development:

```bash
# Set environment variable
export DISABLE_RATE_LIMIT=1

# Or in Python
import os
os.environ["DISABLE_RATE_LIMIT"] = "1"
```

### Issue: Memory errors with large embeddings

**Symptoms:**
```
MemoryError: Cannot allocate memory for array
numpy.core._exceptions._ArrayMemoryError
```

**Solutions:**

1. **Reduce memory capacity:**
   ```python
   wrapper = LLMWrapper(
       llm_generate_fn=my_llm,
       embedding_fn=my_embedder,
       dim=384,
       capacity=10_000,  # Reduced from default 20,000
   )
   ```

2. **Use smaller embedding dimension:**
   ```python
   # Use 384 instead of 768 or 1536
   from sentence_transformers import SentenceTransformer
   embedder = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim
   ```

3. **Monitor memory usage:**
   ```python
   state = wrapper.get_state()
   print(f"Memory usage: {state['memory_stats']['total_vectors']} vectors")
   ```

### Issue: "LLM generate function failed"

**Symptoms:**
```
RuntimeError: LLM generate function failed: [error details]
```

**Solutions:**

1. **Check your LLM function:**
   ```python
   # Test LLM independently
   result = my_llm("test prompt", max_tokens=50)
   print(result)  # Should return a string
   ```

2. **Verify function signature:**
   ```python
   def my_llm(prompt: str, max_tokens: int) -> str:
       # Must accept these exact parameters
       # Must return a string
       return "response"
   ```

3. **Check API keys (if using external LLM):**
   ```python
   import os
   print(os.getenv("OPENAI_API_KEY"))  # Should not be None
   ```

### Issue: Embedding function errors

**Symptoms:**
```
ValueError: Embedding dimension mismatch
TypeError: Embedder must return numpy array
```

**Solutions:**

1. **Ensure correct return type:**
   ```python
   import numpy as np

   def my_embedder(text: str) -> np.ndarray:
       # Must return numpy array
       embedding = get_embedding(text)
       return np.array(embedding, dtype=np.float32)
   ```

2. **Verify dimension matches:**
   ```python
   test_embedding = my_embedder("test")
   print(f"Embedding shape: {test_embedding.shape}")
   # Should be (dim,) where dim matches LLMWrapper(dim=...)

   wrapper = LLMWrapper(
       llm_generate_fn=my_llm,
       embedding_fn=my_embedder,
       dim=test_embedding.shape[0],  # Must match!
   )
   ```

---

## Performance Issues

### Issue: Slow response times

**Symptoms:**
- Generate calls take > 10 seconds
- High latency in production

**Solutions:**

1. **Check LLM response time:**
   ```python
   import time
   start = time.time()
   result = my_llm("test", max_tokens=50)
   print(f"LLM time: {time.time() - start:.2f}s")
   ```

2. **Reduce memory retrieval:**
   ```python
   # Reduce number of retrieved memories
   wrapper = LLMWrapper(
       llm_generate_fn=my_llm,
       embedding_fn=my_embedder,
       dim=384,
       # Internal settings reduce retrieval overhead
   )
   ```

3. **Use faster embedding model:**
   ```python
   # Switch to faster model
   from sentence_transformers import SentenceTransformer
   embedder = SentenceTransformer("all-MiniLM-L6-v2")  # Fast & small
   ```

4. **Profile the code:**
   ```python
   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   result = wrapper.generate("test prompt", moral_value=0.8)

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(10)
   ```

### Issue: High memory usage

**Symptoms:**
- Process uses > 500MB RAM
- Memory grows over time

**Solutions:**

1. **Check memory stats:**
   ```python
   state = wrapper.get_state()
   print(state['memory_stats'])
   ```

2. **Reduce capacity:**
   ```python
   wrapper = LLMWrapper(
       llm_generate_fn=my_llm,
       embedding_fn=my_embedder,
       dim=384,
       capacity=5_000,  # Lower capacity
   )
   ```

3. **Trigger consolidation manually:**
   ```python
   # Force sleep/consolidation phase
   for _ in range(8):  # Complete wake cycle
       wrapper.generate("prompt", moral_value=0.8)
   ```

---

## Configuration Problems

### Issue: Configuration file not found

**Symptoms:**
```
FileNotFoundError: config/production.yaml not found
```

**Solutions:**

1. **Use absolute path:**
   ```python
   import os
   config_path = os.path.join(os.getcwd(), "config", "production.yaml")
   config = ConfigLoader.load_config(config_path)
   ```

2. **Copy example config:**
   ```bash
   cp config/default_config.yaml config/my_config.yaml
   # Edit config/my_config.yaml
   ```

3. **Use environment variables instead:**
   ```bash
   export MLSDM_DIM=384
   export MLSDM_CAPACITY=20000
   export MLSDM_WAKE_DURATION=8
   ```

### Issue: Invalid configuration values

**Symptoms:**
```
ValidationError: Invalid dimension value
ValueError: capacity must be positive
```

**Solution:**

Check configuration constraints:

```yaml
# Valid ranges
dimension: 384          # 2-4096
capacity: 20000         # > 0
wake_duration: 8        # > 0
sleep_duration: 3       # > 0
initial_moral_threshold: 0.50  # 0.30-0.90
```

---

## API Errors

### Issue: FastAPI server won't start

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**

1. **Change port:**
   ```bash
   uvicorn mlsdm.api.app:app --port 8001
   ```

2. **Kill existing process:**
   ```bash
   # Find process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

### Issue: 401 Unauthorized errors

**Symptoms:**
```
HTTPException: 401 Unauthorized
```

**Solutions:**

1. **Disable auth for development:**
   ```python
   # In app.py or env
   os.environ["MLSDM_AUTH_DISABLED"] = "1"
   ```

2. **Provide valid token:**
   ```python
   import requests
   headers = {"Authorization": "Bearer your-token"}
   response = requests.post(
       "http://localhost:8000/generate",
       headers=headers,
       json={"prompt": "test", "moral_value": 0.8}
   )
   ```

### Issue: 422 Validation Error

**Symptoms:**
```json
{
  "detail": [
    {
      "loc": ["body", "moral_value"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Solution:**

Provide all required fields:

```python
# Correct request
data = {
    "prompt": "Your prompt here",
    "moral_value": 0.8,  # Required
    # Optional fields:
    "max_tokens": 150,
    "temperature": 0.7,
}
```

---

## Testing Issues

### Issue: Tests fail with import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'mlsdm'
```

**Solutions:**

1. **Install in editable mode:**
   ```bash
   pip install -e .
   ```

2. **Install test dependencies:**
   ```bash
   pip install -e ".[test]"
   # OR
   pip install pytest pytest-cov pytest-asyncio hypothesis
   ```

### Issue: Tests timeout

**Symptoms:**
```
FAILED tests/test_something.py::test_function - timeout
```

**Solutions:**

1. **Increase timeout:**
   ```bash
   pytest tests/ --timeout=300
   ```

2. **Skip slow tests:**
   ```bash
   pytest tests/ -m "not slow"
   ```

3. **Run specific test:**
   ```bash
   pytest tests/unit/test_specific.py::test_function -v
   ```

---

## Getting Help

### Before Asking for Help

1. **Check existing documentation:**
   - [README.md](README.md)
   - [GETTING_STARTED.md](GETTING_STARTED.md)
   - [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
   - [API_REFERENCE.md](API_REFERENCE.md)

2. **Search existing issues:**
   - [GitHub Issues](https://github.com/neuron7xLab/mlsdm/issues)

3. **Gather diagnostic information:**
   ```bash
   # Python version
   python --version

   # Package versions
   pip list | grep -E "mlsdm|numpy|fastapi|opentelemetry"

   # System info
   uname -a  # Linux/Mac
   # or
   systeminfo  # Windows
   ```

### Reporting Issues

**Good issue report template:**

```markdown
## Description
Brief description of the problem

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.0]
- MLSDM version: [e.g., 1.2.0]
- OpenTelemetry installed: [Yes/No]

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Error Messages
```
Paste error messages here
```

## Code Sample
```python
# Minimal code to reproduce
```

## Logs
```
Paste relevant logs
```
```

### Community Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/neuron7xLab/mlsdm/issues)
- **Discussions**: [Ask questions or share ideas](https://github.com/neuron7xLab/mlsdm/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute

---

**Last Updated:** December 2025
**Version:** 1.2.0
**Maintainer:** neuron7x

---

**Didn't find your issue?** [Create a new issue](https://github.com/neuron7xLab/mlsdm/issues/new) with the template above.
