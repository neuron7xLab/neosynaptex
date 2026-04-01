# BN-Syn Benchmark Protocol

Reproducibility protocol for BN-Syn performance benchmarks.

## Determinism Guarantees

All benchmarks are deterministic given fixed environment and seeds:

1. **RNG seeding**: All randomness flows through `bnsyn.rng.seed_all(seed)` which seeds:
   - `numpy.random.Generator` (primary)
   - Python `random` module (fallback)
   - `PYTHONHASHSEED` environment variable

2. **Parameter serialization**: All scenario parameters are serialized to JSON with exact types

3. **Subprocess isolation**: Each run executes in a fresh subprocess with clean state

4. **No hidden state**: BN-Syn core has no module-level globals that accumulate state

Notes:
- Subprocess teardown releases Python and (if enabled) GPU allocations.
- OS-level caches are not explicitly flushed; performance metrics should be interpreted with this in mind.
- Hot-path current buffers are preallocated; per-step allocations inside `Network.step()` are not permitted for benchmark stability.
- Benchmarks are tagged with a regime ID (`alloc_v2`); CI comparisons use baselines from the same regime.
- Kernel `max_time_sec` uses a p95 estimate to reduce sensitivity to outliers.

## Environment Requirements

### Pinned Dependencies

Install exact versions:
```bash
pip install -e ".[dev,test]"
```

Core dependencies (from `pyproject.toml`):
- `numpy>=1.26`
- `scipy>=1.10`
- `psutil>=5.9` (benchmark-specific)

### Python Version

Tested on Python 3.11+. Results may vary on older Python versions due to NumPy implementation changes.

### Operating System

Benchmarks are OS-agnostic but timing will vary:
- **Linux**: Most consistent (recommended for CI)
- **macOS**: Generally fast but subject to CPU throttling
- **Windows**: Higher OS noise

## Running Benchmarks

### Scenario Sets

- **small_network**: single scenario, N=128, steps=300
- **medium_network**: single scenario, N=512, steps=400
- **large_network**: single scenario, N=2000, steps=400
- **criticality_sweep**: sigma_target in [0.8, 1.0, 1.2], steps=300
- **temperature_sweep**: T0 in [0.5, 1.0, 1.5], steps=300
- **dt_sweep**: dt_ms in [0.05, 0.1, 0.2], steps=400 (adaptive dt enabled)

Defaults:
- `--repeats` defaults to 3 (increase to 5+ for baselines)
- `--warmup` defaults to 1 (set to 0 if you need to skip warmup)

### Minimal Example (CI Smoke Test)

```bash
python benchmarks/run_benchmarks.py \
  --scenario small_network \
  --repeats 3 \
  --warmup 1 \
  --json results/small_network.json
```

Expected runtime: <1 minute

### Full Parameter Sweep

```bash
python benchmarks/run_benchmarks.py \
  --scenario full \
  --repeats 5 \
  --warmup 1 \
  --json results/full.json
```

Expected runtime: 10-30 minutes (depends on hardware)

## Interpreting Results

### Scalability Parameters

| Parameter | Complexity Driver | Expected Scaling |
|-----------|------------------|------------------|
| `N_neurons` | Network size | O(N) time, O(N) memory for sparse connectivity |
| `steps` | Simulation length | O(steps) time, O(1) memory |
| `p_conn` | Connection density | O(N² × p_conn) memory, O(N × fan_in) time per step |
| `dt_ms` | Timestep | O(1/dt) time for fixed real-time duration |

### Metric Definitions

**performance_wall_time_sec:**
- Total elapsed wall-clock time (includes Python overhead)
- Use for absolute performance assessment

**performance_per_step_ms:**
- Time per simulation step (wall_time / steps × 1000)
- Use for comparing step efficiency across scenarios

**performance_peak_rss_mb:**
- Peak resident set size (process memory footprint)
- Includes Python interpreter, NumPy arrays, overhead
- Use for memory scaling analysis

**performance_neuron_steps_per_sec:**
- Throughput metric: (N_neurons × steps) / wall_time
- Use for comparing hardware efficiency
- Higher is better

**physics_spike_rate_hz:**
- Mean spike rate across the run (Hz)
- Computed from per-step spike_rate_hz values

**physics_sigma:**
- Mean σ tracking signal across the run
- Reported alongside `physics_sigma_std`

**stability_nan_rate:**
- Fraction of NaN entries observed in state vectors

**reproducibility_bitwise_delta:**
- Fraction of float64 entries that differ at the bit level between two runs
- Computed as max(delta(sigma), delta(spike_rate_hz))
- 0.0 indicates bitwise-identical outputs

### Aggregated Outputs

Per-scenario JSON output aggregates each base metric with suffixes:
- `_mean`, `_std`, `_p5`, `_p50`, `_p95`

`benchmarks/run_benchmarks.py` also logs per-scenario summaries (mean, p50/p95) to `bench.log`
for CI traceability.

### Expected Variance

**Shared/CI Runners:**
- Timing: ±5-10% (CPU throttling, OS noise)
- Memory: ±2-5% (Python GC non-determinism)

**Dedicated Hardware:**
- Timing: ±1-3% (cache effects, OS scheduling)
- Memory: ±1% (Python GC non-determinism)

### Serialization and Aggregation

- Non-finite metric values (NaN/Inf) are serialized as `null` in JSON output.
- Aggregation removes outliers with |z-score| > 2 for performance metrics when 3+ repeats are available.

### Regression Detection

**Significant regression:**
- >15% increase in wall_time (same hardware)
- >10% increase in peak_rss (same hardware)

**Investigate if:**
- Throughput drops >10%
- Stability metrics change unexpectedly (determinism violation)

**Likely false positive:**
- <5% changes on shared runners
- Single-run outliers (check p95 vs mean)

### Regression Test Tolerances

`tests/benchmarks/test_regression.py` compares two runs per scenario and enforces:
- Default `rtol=1e-6`, `atol=1e-9`
- Stricter overrides for deterministic metrics:
  - `stability_nan_rate`: `rtol=0`, `atol=1e-12`
  - `stability_divergence_rate`: `rtol=0`, `atol=1e-12`
  - `reproducibility_bitwise_delta`: `rtol=0`, `atol=1e-8`
  - `thermostat_temperature_exploration_corr`: `rtol=1e-6`, `atol=1e-8`

Performance metrics are excluded from this deterministic regression check.

## Baseline Establishment

To establish a baseline for regression tracking:

1. Run full sweep with 5+ repeats on dedicated hardware
2. Record: hardware spec, OS, Python version, git SHA
3. Store results as `baselines/{sha}.json`
4. Use p50 values for comparison (robust to outliers)

## Limitations

### Known Variability Sources

1. **CPU throttling**: Thermal or power management can reduce clock speed mid-run
2. **OS scheduler**: Non-real-time scheduling introduces jitter
3. **Python GC**: Non-deterministic garbage collection timing
4. **Shared caches**: Other processes evict cache lines
5. **Turbo boost**: CPU frequency varies with thermal headroom

### Not Measured

- **Energy consumption**: Requires hardware counters
- **GPU performance**: BN-Syn is CPU-only
- **I/O time**: Benchmarks are compute-bound
- **Network latency**: Single-process only

### Excluded from Scope

- **Model accuracy**: See validation tests in `tests/validation/`
- **Numerical stability**: See dt-invariance tests
- **Determinism**: See `tests/test_determinism.py`

## CI Integration

The `benchmarks.yml` workflow (standard tier, scenario profile):
- Runs `ci_smoke` scenario (N=50, steps=100)
- Uploads CSV/JSON artifacts
- Does NOT block PR merges by default
- Scheduled weekly for trend tracking

To make merge-blocking (not recommended without baselines):
- Add workflow to branch protection checks
- Implement automated baseline comparison with thresholds

## Changelog

- **2026-01-24**: Initial protocol (git SHA: cc3b5f0c8d75c398a488d70390e9917cc720ba21)
