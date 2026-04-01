# MFN Performance Baselines

Performance baselines for MyceliumFractalNet v4.1 key execution paths.

These baselines are used by `tests/perf/test_mfn_performance.py` to verify
that performance does not regress beyond the allowed threshold (+20%).

---

## Test Environment

- Python: 3.10+
- NumPy: 1.24+
- Hardware: Standard GitHub Actions runner (2 vCPU, 7GB RAM)
- Measurement: Average over multiple runs with `time.perf_counter()`

---

## 1. Simulation Performance

### 1.1 Demo Configuration

Configuration: `make_simulation_config_demo()`
- grid_size: 32
- steps: 32
- seed: 42

| Metric | Baseline | Threshold (+20%) |
|--------|----------|------------------|
| Time (s) | 0.040 | 0.048 |
| Peak Memory (KB) | 1000 | 1200 |

### 1.2 Default Configuration

Configuration: `make_simulation_config_default()`
- grid_size: 64
- steps: 100
- seed: 42

| Metric | Baseline | Threshold (+20%) |
|--------|----------|------------------|
| Time (s) | 0.120 | 0.144 |
| Peak Memory (KB) | 500 | 600 |

---

## 2. Feature Extraction Performance

### 2.1 Demo Configuration

Input: SimulationResult from demo config with history

| Metric | Baseline | Threshold (+20%) |
|--------|----------|------------------|
| Time (s) | 0.010 | 0.012 |
| Peak Memory (KB) | 2000 | 2400 |

---

## 3. Dataset Generation Performance

### 3.1 Demo Configuration (5 samples)

Configuration: `make_dataset_config_demo()` (5 samples)
- grid_sizes: [32]
- steps_range: (30, 50)
- num_samples: 5

| Metric | Baseline | Threshold (+20%) |
|--------|----------|------------------|
| Total Time (s) | 0.300 | 0.360 |
| Per Sample (s) | 0.060 | 0.072 |
| Peak Memory (KB) | 1500 | 1800 |

---

## 4. End-to-End Pipeline Performance

### 4.1 Full Pipeline (Demo)

1. SimulationConfig → run_mycelium_simulation → SimulationResult
2. SimulationResult → compute_fractal_features → FeatureVector
3. DatasetConfig → generate_dataset → dataset file

| Stage | Baseline (s) | Threshold (+20%) |
|-------|--------------|------------------|
| Simulation | 0.040 | 0.048 |
| Features | 0.010 | 0.012 |
| Total Pipeline | 0.050 | 0.060 |

---

## 5. API Load Tests

### 5.1 Overview

API load testing is performed using Locust. Test scenarios are defined in
`load_tests/locustfile.py` and cover all API endpoints.

### 5.2 Running Locust Tests

```bash
# Start the API server
uvicorn api:app --host 0.0.0.0 --port 8000

# Run Locust with web UI (in another terminal)
locust -f load_tests/locustfile.py --host http://localhost:8000

# Run headless with specific parameters
locust -f load_tests/locustfile.py --host http://localhost:8000 \
    --headless -u 10 -r 2 -t 1m
```

### 5.3 Endpoint Baselines

| Endpoint | Method | p50 (ms) | p95 (ms) | p99 (ms) | Max RPS |
|----------|--------|----------|----------|----------|---------|
| /health | GET | <10 | <50 | <100 | 1000+ |
| /metrics | GET | <10 | <50 | <100 | 500+ |
| /nernst | POST | <50 | <200 | <500 | 100+ |
| /simulate (32x32) | POST | <1000 | <2000 | <5000 | 10+ |
| /validate | POST | <5000 | <10000 | <15000 | 5+ |

### 5.4 Load Test Scenarios

| Scenario | Users | Duration | Target RPS | Error Rate |
|----------|-------|----------|------------|------------|
| Smoke | 1 | 30s | - | 0% |
| Steady | 10 | 5m | 50 | <1% |
| Spike | 50 | 1m | 100 | <5% |

### 5.5 Monitoring During Tests

Use the `/metrics` endpoint to observe:
- `mfn_http_requests_total` - Request count by endpoint/status
- `mfn_http_request_duration_seconds` - Latency histogram
- `mfn_http_requests_in_progress` - Active requests

Example Prometheus queries:
```promql
# Request rate
rate(mfn_http_requests_total[1m])

# P95 latency
histogram_quantile(0.95, rate(mfn_http_request_duration_seconds_bucket[5m]))

# Error rate
rate(mfn_http_requests_total{status=~"5.."}[1m])
```

### 5.6 Environment Variables for Load Tests

| Variable | Description | Default |
|----------|-------------|---------|
| MFN_LOADTEST_BASE_URL | API base URL | http://localhost:8000 |
| MFN_LOADTEST_API_KEY | API key for authentication | (none) |
| MFN_LOADTEST_DURATION | Test duration (headless) | (via CLI) |

---

## 6. Notes

### Measurement Guidelines

1. Baselines are measured on standard CI hardware
2. Warm-up run is excluded from timing
3. Multiple runs averaged (3-5 typically)
4. Memory measured with `tracemalloc`

### Allowed Variance

- Time: +20% from baseline
- Memory: +20% from baseline

### Update Process

When optimizing code:
1. Run profiling script to get new measurements
2. Update baselines in this document
3. Update test thresholds if baselines improve

---

## 7. Commands

### Run Performance Tests

```bash
pytest tests/perf/test_mfn_performance.py -v
```

### Run Small Performance Tests (CI)

```bash
pytest tests/performance/test_api_performance_small.py -v
```

### Profile Key Paths

```bash
python -c "
from mycelium_fractal_net.config import make_simulation_config_demo
from mycelium_fractal_net import run_mycelium_simulation
import time

config = make_simulation_config_demo()
start = time.perf_counter()
result = run_mycelium_simulation(config)
print(f'Time: {time.perf_counter() - start:.4f}s')
"
```

---

## 8. Today's Baseline (2025-11-30)

Benchmark results from CI run 19803646754 on GitHub Actions runner:

### Core Benchmarks

| Benchmark | Value | Target | Margin |
|-----------|-------|--------|--------|
| Forward pass latency | 0.22 ms | <10 ms | 45x |
| Forward pass (batch=128) | 0.29 ms | <50 ms | 172x |
| Field simulation (64x64, 100 steps) | 19.08 ms | <100 ms | 5x |
| Fractal dimension estimation | 0.22 ms | <50 ms | 227x |
| Training step | 1.68 ms | <20 ms | 12x |
| Peak memory usage | 0.24 MB | <500 MB | 2083x |
| Inference throughput | 264,031 samples/sec | >1,000 | 264x |
| Model initialization | 0.50 ms | <100 ms | 200x |

**Result:** 8/8 passed with significant performance headroom.

### Scientific Validation

| Validation | Expected | Computed | Error |
|------------|----------|----------|-------|
| K+ Nernst (mammalian) | -89.0 mV | -89.0 mV | 0.0 mV |
| Na+ Nernst (mammalian) | 66.0 mV | 66.6 mV | 0.6 mV |
| Cl- Nernst (mammalian) | -89.0 mV | -90.9 mV | 1.9 mV |
| Ca2+ Nernst (mammalian) | 102.0 mV | 101.5 mV | 0.5 mV |
| RT/F constant | 26.730 mV | 26.712 mV | 0.018 mV |
| Fractal dimension | 1.585 | 1.762 | 0.177 |

**Result:** 11/11 scientific validations passed.

### Test Metrics

| Metric | Value |
|--------|-------|
| Total tests | 807 |
| Passed | 806 |
| Skipped | 1 |
| Coverage | 84% |
| Warnings | 1585 (mostly from dependencies) |

---

## 9. Stress Testing & Scalability

### 9.1 Scalability Benchmarks

Run scalability benchmarks with:

```bash
python benchmarks/benchmark_scalability.py
```

| Benchmark | Target | Description |
|-----------|--------|-------------|
| Large grid (128x128) | <15s | 200 steps simulation |
| Large grid (256x256) | <60s | 100 steps simulation |
| Long simulation | <30s | 64x64, 1000 steps |
| Concurrent throughput | >3 sim/s | 4 workers, 16 tasks |
| Memory efficiency | <100MB | 20 repeated runs |
| Fractal dimension (256x256) | <0.5s | Large field analysis |
| Lyapunov (500x64x64) | <2s | Large history analysis |

### 9.2 Stress Tests

Run stress tests with:

```bash
pytest tests/perf/test_stress_scalability.py -v
```

Tests cover:
- **Large Grid Simulations**: 128x128 and 256x256 grids
- **Long Simulations**: 1000+ steps
- **Memory Stress**: Repeated runs without memory leaks
- **Concurrent Processing**: Thread-safe multi-worker execution
- **Large Data Processing**: Fractal dimension, Lyapunov analysis
- **Federated Scalability**: Many clients, large gradients
- **Numerical Stability**: Edge parameters, extreme conditions

### 9.3 Memory Limits

| Configuration | Max Memory (MB) | Description |
|---------------|-----------------|-------------|
| Small (32x32) | 100 | Quick tests, CI |
| Medium (64x64) | 200 | Development |
| Large (128x128) | 500 | Production simulations |
| XLarge (256x256) | 1500 | High-resolution analysis |

### 9.4 Locust Load Testing

For API load testing, use:

```bash
# Start the API server
uvicorn api:app --host 0.0.0.0 --port 8000

# Run stress tests (in another terminal)
locust -f load_tests/locustfile.py --host http://localhost:8000 \
    --headless -u 20 -r 5 -t 2m
```

Available user classes:
- `MFNAPIUser`: Standard mixed load
- `MFNReadOnlyUser`: Read-only operations
- `MFNHeavyUser`: Computation-heavy operations
- `MFNStressUser`: Large payloads, high-frequency
- `MFNScalabilityUser`: Varying load patterns

---

*Document Version: 1.3*
*Last Updated: 2025-12-01*
*Applies to: MyceliumFractalNet v4.1.0*
