# MyceliumFractalNet Troubleshooting Guide

This guide helps you diagnose and resolve common issues with MyceliumFractalNet.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Import Errors](#import-errors)
- [Configuration Problems](#configuration-problems)
- [API Errors](#api-errors)
- [Performance Issues](#performance-issues)
- [Simulation Issues](#simulation-issues)
- [Docker & Kubernetes](#docker--kubernetes)
- [Testing Issues](#testing-issues)
- [FAQ](#faq)

---

## Installation Issues

### Problem: pip install fails with dependency conflicts

**Symptoms:**
```
ERROR: Cannot install mycelium-fractal-net because these package versions have conflicting dependencies.
```

**Solution:**
```bash
# Create a fresh virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install with pinned versions
pip install -e ".[dev]"
```

### Problem: torch installation fails or is slow

**Symptoms:**
```
Building wheel for torch (setup.py) ... error
```

**Solution:**
```bash
# Install PyTorch separately with appropriate CUDA version
# CPU only (faster download):
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Then install MFN:
pip install -e ".[dev]"
```

### Problem: Python version not supported

**Symptoms:**
```
ERROR: Package requires Python >=3.10
```

**Solution:**

Check your Python version:
```bash
python --version
```

Install Python 3.10 or newer:
- **Ubuntu/Debian**: `sudo apt install python3.10`
- **macOS**: `brew install python@3.10`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

---

## Import Errors

### Problem: ModuleNotFoundError: No module named 'mycelium_fractal_net'

**Symptoms:**
```python
>>> from mycelium_fractal_net import simulate_mycelium_field
ModuleNotFoundError: No module named 'mycelium_fractal_net'
```

**Solution:**

1. Check if package is installed:
```bash
pip list | grep mycelium-fractal-net
```

2. Install in development mode:
```bash
pip install -e .
```

3. Verify Python path:
```python
import sys
print(sys.path)
```

### Problem: ImportError for optional dependencies

**Symptoms:**
```python
ImportError: prometheus_client not installed
```

**Solution:**

Install optional dependencies:
```bash
pip install prometheus_client  # For metrics
pip install locust              # For load testing
pip install httpx               # For API client
```

Or install all dev dependencies:
```bash
pip install -e ".[dev]"
```

---

## Configuration Problems

### Problem: API key authentication not working

**Symptoms:**
```json
{
  "detail": "Missing or invalid API key"
}
```

**Solution:**

1. Set the environment variable:
```bash
export MFN_API_KEY="your-secret-key"
export MFN_API_KEY_REQUIRED="true"
```

2. Include the header in requests:
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/validate
```

3. Verify configuration:
```python
from mycelium_fractal_net.integration import get_api_config
config = get_api_config()
print(f"Auth required: {config.api_key_required}")
print(f"Valid keys: {len(config.valid_api_keys)}")
```

### Problem: CORS errors in browser

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/validate' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Solution:**

Set allowed origins:
```bash
# Allow all origins (development only)
export MFN_ENV=dev

# Or specify specific origins
export MFN_CORS_ORIGINS="http://localhost:3000,https://myapp.com"
```

### Problem: Configuration file not found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'configs/medium.json'
```

**Solution:**

1. Check available configs:
```bash
ls configs/
```

2. Use existing config:
```python
from mycelium_fractal_net import make_simulation_config
config = make_simulation_config("small")  # or "medium", "large"
```

3. Or use the demo config:
```python
from mycelium_fractal_net import make_simulation_config_demo
config = make_simulation_config_demo()
```

---

## API Errors

### Problem: 429 Too Many Requests

**Symptoms:**
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

**Solution:**

1. Wait for the retry period (check `Retry-After` header)

2. Disable rate limiting for testing:
```bash
export MFN_RATE_LIMIT_ENABLED="false"
```

3. Increase rate limits:
```bash
export MFN_RATE_LIMIT_REQUESTS=1000  # requests per minute
```

### Problem: 500 Internal Server Error

**Symptoms:**
```json
{
  "detail": "Internal server error"
}
```

**Solution:**

1. Check server logs:
```bash
# If running with uvicorn
uvicorn api:app --log-level debug
```

2. Enable detailed error responses in development:
```bash
export MFN_ENV=dev
```

3. Validate request payload:
```python
# Use Pydantic models for validation
from mycelium_fractal_net.integration import ValidateRequest
request = ValidateRequest(seed=42, epochs=5)
```

### Problem: API server won't start

**Symptoms:**
```
ERROR:    [Errno 48] Address already in use
```

**Solution:**

1. Check if port is in use:
```bash
lsof -i :8000  # On Unix
netstat -ano | findstr :8000  # On Windows
```

2. Use a different port:
```bash
uvicorn api:app --port 8001
```

3. Kill the process using the port:
```bash
kill -9 <PID>  # On Unix
taskkill /PID <PID> /F  # On Windows
```

---

## Performance Issues

### Problem: Simulations are too slow

**Symptoms:**
- Simulations take several minutes
- High CPU usage

**Solutions:**

1. **Reduce grid size**:
```python
config = make_simulation_config("small")  # 32×32 instead of 128×128
```

2. **Decrease simulation steps**:
```python
config.steps = 50  # Instead of 200
```

3. **Disable Turing morphogenesis for testing**:
```python
config.turing_enabled = False
```

4. **Use GPU if available**:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Problem: High memory usage

**Symptoms:**
- OOM (Out of Memory) errors
- System becomes unresponsive

**Solutions:**

1. **Clear history if not needed**:
```python
# Don't track full history
result = simulate_mycelium_field(rng, grid_size=64, steps=100)
# Instead of run_mycelium_simulation_with_history()
```

2. **Process in batches**:
```python
# Instead of generating 1000 samples at once
for batch in range(10):
    results = generate_batch(size=100)
    save_results(results)
    del results  # Free memory
```

3. **Use smaller data types**:
```python
# Convert to float32 if precision is not critical
field = field.astype(np.float32)
```

### Problem: Feature extraction is slow

**Symptoms:**
- `compute_fractal_features()` takes > 5 seconds

**Solutions:**

1. **Use smaller fields**:
```python
# Downsample field before feature extraction
from scipy.ndimage import zoom
field_small = zoom(field, 0.5)  # Reduce by 50%
```

2. **Extract only needed features**:
```python
# Use specific feature functions instead of computing all 18
from analytics import compute_fractal_dimension
D = compute_fractal_dimension(binary_field)
```

---

## Simulation Issues

### Problem: Simulation produces NaN values

**Symptoms:**
```python
RuntimeWarning: invalid value encountered in divide
```

**Solution:**

1. Check input parameters:
```python
# Ensure parameters are valid
assert 0 < config.alpha < 1
assert config.grid_size >= 8
assert config.steps > 0
```

2. Use validated configuration:
```python
from mycelium_fractal_net import make_simulation_config_demo
config = make_simulation_config_demo()  # Known-good parameters
```

### Problem: Growth events always zero

**Symptoms:**
```
growth_events: 0
```

**Solution:**

Enable Turing morphogenesis:
```python
config.turing_enabled = True
config.turing_threshold = 0.75  # Default threshold
```

### Problem: Unrealistic potential values

**Symptoms:**
- Potentials outside [-100, 50] mV range

**Solution:**

Enable clamping:
```python
# Potentials are automatically clamped to biophysical range
# Check if clamping events are occurring:
print(f"Clamping events: {result.clamping_events}")
```

---

## Docker & Kubernetes

### Problem: Docker build fails

**Symptoms:**
```
ERROR [builder 5/6] RUN pip install -e .
```

**Solution:**

1. Build with no cache:
```bash
docker build --no-cache -t mfn:4.1 .
```

2. Check Docker has enough memory:
```bash
docker system df
docker system prune  # Clean up space
```

### Problem: Kubernetes pod crashes

**Symptoms:**
```
CrashLoopBackOff
```

**Solution:**

1. Check logs:
```bash
kubectl logs -n mfn-prod <pod-name>
kubectl describe pod -n mfn-prod <pod-name>
```

2. Verify resource limits:
```yaml
# In k8s.yaml, increase resources:
resources:
  limits:
    memory: "2Gi"  # Increase if needed
    cpu: "1000m"
  requests:
    memory: "1Gi"
    cpu: "500m"
```

3. Check health probes:
```bash
# Test health endpoint manually
kubectl port-forward -n mfn-prod <pod-name> 8000:8000
curl http://localhost:8000/health
```

### Problem: Ingress not routing traffic

**Symptoms:**
- 404 Not Found from ingress

**Solution:**

1. Verify ingress controller is installed:
```bash
kubectl get pods -n ingress-nginx
```

2. Check ingress configuration:
```bash
kubectl get ingress -n mfn-prod
kubectl describe ingress -n mfn-prod mfn-ingress
```

3. Verify DNS:
```bash
nslookup your-domain.com
```

---

## Testing Issues

### Problem: Tests fail with "fixture not found"

**Symptoms:**
```
fixture 'some_fixture' not found
```

**Solution:**

Run tests from project root:
```bash
cd /path/to/mycelium-fractal-net
pytest
```

### Problem: Tests timeout

**Symptoms:**
```
TIMEOUT after 60 seconds
```

**Solution:**

Increase timeout for slow tests:
```bash
pytest --timeout=300  # 5 minutes
```

Or mark tests as slow:
```python
@pytest.mark.slow
def test_long_simulation():
    pass
```

### Problem: Hypothesis tests fail

**Symptoms:**
```
hypothesis.errors.Flaky: Test is flaky
```

**Solution:**

Set a fixed seed:
```python
from hypothesis import settings, seed

@seed(42)
@given(...)
def test_with_fixed_seed():
    pass
```

---

## Getting Help

If you can't find a solution here:

1. **Check the documentation**:
   - [README.md](../README.md)
   - [ARCHITECTURE.md](ARCHITECTURE.md)
   - [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md)

2. **Search existing issues**:
   - [GitHub Issues](https://github.com/neuron7x/mycelium-fractal-net/issues)

3. **Open a new issue**:
   - Include error messages
   - Provide reproduction steps
   - Specify your environment (Python version, OS, etc.)

4. **Enable debug logging**:
```bash
export MFN_LOG_LEVEL=DEBUG
python mycelium_fractal_net_v4_1.py --mode validate
```

---

## FAQ

**Q: What is the fastest way to confirm my installation works?**  
A: Run the validate mode and confirm you get a JSON response without errors:
```bash
python mycelium_fractal_net_v4_1.py --mode validate
```

**Q: Which config should I use for a quick smoke test?**  
A: Use the demo configuration or the smallest built-in config:
```python
from mycelium_fractal_net import make_simulation_config_demo, make_simulation_config
config = make_simulation_config_demo()  # Known-good defaults
config_small = make_simulation_config("small")
```

**Q: How do I turn off rate limiting in development?**  
A: Disable it via env var:
```bash
export MFN_RATE_LIMIT_ENABLED="false"
```

**Q: Where do I see structured logs with request IDs?**  
A: Run the API with debug logging and look for `request_id` fields:
```bash
export MFN_LOG_LEVEL=DEBUG
uvicorn api:app --log-level debug
```

**Q: What should I include when reporting a bug?**  
A: Provide the error message, reproduction steps, config used, and environment info:
```bash
python --version
pip freeze | rg "mycelium|torch|fastapi"
```

---

## Common Error Messages

| Error | Likely Cause | Quick Fix |
|:------|:------------|:----------|
| `ModuleNotFoundError` | Package not installed | `pip install -e ".[dev]"` |
| `401 Unauthorized` | Missing/invalid API key | Set `MFN_API_KEY` env var |
| `429 Too Many Requests` | Rate limit exceeded | Wait or disable rate limiting |
| `500 Internal Server Error` | Bug or invalid input | Check logs with `--log-level debug` |
| `Address already in use` | Port conflict | Use `--port 8001` |
| `CUDA out of memory` | GPU memory full | Use CPU or smaller batch size |
| `NaN in simulation` | Invalid parameters | Use `make_simulation_config_demo()` |

---

**Last Updated**: 2025-12-04  
**Version**: 4.1.0
