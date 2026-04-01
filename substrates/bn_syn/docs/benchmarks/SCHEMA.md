# BN-Syn Benchmark Results Schema

Schema definition for CSV/JSON benchmark results.

## Output Format

`benchmarks/run_benchmarks.py` writes a JSON array (one object per scenario).

## Field Definitions

### Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `scenario` | string | Unique scenario name | `"n_sweep_1000"` |
| `git_sha` | string | Git commit SHA (full 40 chars) | `"a1b2c3d4..."` |
| `python_version` | string | Python version (major.minor.micro) | `"3.11.5"` |
| `timestamp` | string | UTC timestamp (ISO 8601) | `"2026-01-24T12:34:56.789Z"` |
| `warmup` | integer | Warmup runs per scenario | `1` |
| `repeats` | integer | Number of successful runs | `3` |

### Scenario Parameters

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `seed` | integer | - | RNG seed for deterministic runs |
| `dt_ms` | float | milliseconds | Integration timestep |
| `steps` | integer | - | Number of simulation steps |
| `N_neurons` | integer | - | Total neurons (excitatory + inhibitory) |
| `p_conn` | float | - | Connection probability (0 to 1) |
| `frac_inhib` | float | - | Fraction of inhibitory neurons (0 to 1) |
| `description` | string | - | Human-readable scenario summary |
| `sigma_target` | float or null | - | Criticality target (when applicable) |
| `temperature_T0` | float or null | - | Temperature schedule initial value |
| `temperature_alpha` | float or null | - | Temperature schedule decay factor |
| `temperature_Tmin` | float or null | - | Temperature schedule minimum |
| `temperature_Tc` | float or null | - | Temperature schedule cutoff |
| `temperature_gate_tau` | float or null | - | Temperature gate time constant |
| `use_adaptive_dt` | boolean | - | Enable adaptive timestep integration |

### Timing Metrics

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `performance_wall_time_sec_mean` | float | seconds | Mean wall-clock time across repeats |
| `performance_wall_time_sec_p5` | float | seconds | 5th percentile wall-clock time |
| `performance_wall_time_sec_p50` | float | seconds | Median wall-clock time |
| `performance_wall_time_sec_p95` | float | seconds | 95th percentile wall-clock time |
| `performance_wall_time_sec_std` | float | seconds | Standard deviation of wall-clock time |
| `performance_per_step_ms_mean` | float | milliseconds | Mean time per simulation step |
| `performance_per_step_ms_p5` | float | milliseconds | 5th percentile time per step |
| `performance_per_step_ms_p50` | float | milliseconds | Median time per step |
| `performance_per_step_ms_p95` | float | milliseconds | 95th percentile time per step |
| `performance_per_step_ms_std` | float | milliseconds | Standard deviation of time per step |

**Definition:**
```
performance_per_step_ms = (performance_wall_time_sec / steps) * 1000
```

### Memory Metrics

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `performance_peak_rss_mb_mean` | float | megabytes | Mean peak resident set size |
| `performance_peak_rss_mb_p5` | float | megabytes | 5th percentile peak RSS |
| `performance_peak_rss_mb_p50` | float | megabytes | Median peak RSS |
| `performance_peak_rss_mb_p95` | float | megabytes | 95th percentile peak RSS |
| `performance_peak_rss_mb_std` | float | megabytes | Standard deviation of peak RSS |

**Definition:**
- Measured via `psutil.Process().memory_info().rss`
- Peak during run (max of start and end RSS)
- Includes Python interpreter, libraries, and all allocations

### Throughput Metrics

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `performance_neuron_steps_per_sec_mean` | float | neuron-steps/sec | Mean throughput |
| `performance_neuron_steps_per_sec_p5` | float | neuron-steps/sec | 5th percentile throughput |
| `performance_neuron_steps_per_sec_p50` | float | neuron-steps/sec | Median throughput |
| `performance_neuron_steps_per_sec_p95` | float | neuron-steps/sec | 95th percentile throughput |
| `performance_neuron_steps_per_sec_std` | float | neuron-steps/sec | Standard deviation of throughput |

**Definition:**
```
performance_neuron_steps_per_sec = (N_neurons * steps) / performance_wall_time_sec
```

Interpretation:
- Measures computational throughput (higher is better)
- Accounts for both network size and simulation length
- Use for cross-hardware comparisons

### Activity and Stability Metrics

All base metrics from a single run are aggregated across repeats using the suffixes
`_mean`, `_std`, `_p5`, and `_p95`. Base metric keys include:

| Base Metric | Units | Description |
|-------------|-------|-------------|
| `stability_nan_rate` | fraction | NaN rate across state vectors |
| `stability_divergence_rate` | fraction | Divergence steps / total steps |
| `physics_spike_rate_hz` | Hz | Mean spike rate |
| `physics_sigma` | - | Mean sigma |
| `physics_sigma_std` | - | Sigma standard deviation |
| `learning_weight_entropy` | bits | Shannon entropy of final weights |
| `learning_convergence_error` | - | |mean(sigma_tail) - sigma_target| |
| `thermostat_temperature_mean` | - | Mean temperature schedule value |
| `thermostat_exploration_mean` | - | Mean exploration proxy |
| `thermostat_temperature_exploration_corr` | - | Correlation between temperature and exploration |
| `reproducibility_bitwise_delta` | fraction | Bitwise mismatch fraction across two runs |

**Definition:**
- `reproducibility_bitwise_delta` is the fraction of float64 entries that differ at the bit level between two runs.
- Non-finite values are serialized as `null` in JSON.
- Aggregation removes outliers with |z-score| > 2 for performance metrics when 3+ repeats are available.
- `learning_weight_entropy` uses Shannon entropy on positive weights: `-Σ(p * log2(p))` with `p = w / Σw`.

## Example Object (JSON)

```json
{
  "scenario": "n_sweep_1000",
  "git_sha": "a1b2c3d4e5f6...",
  "python_version": "3.11.5",
  "timestamp": "2026-01-24T12:34:56.789Z",
  "name": "n_sweep_1000",
  "seed": 42,
  "dt_ms": 0.1,
  "steps": 500,
  "N_neurons": 1000,
  "p_conn": 0.05,
  "frac_inhib": 0.2,
  "description": "Network size sweep: N=1000",
  "warmup": 1,
  "repeats": 3,
  "performance_wall_time_sec_mean": 2.451,
  "performance_wall_time_sec_p5": 2.445,
  "performance_wall_time_sec_p50": 2.450,
  "performance_wall_time_sec_p95": 2.475,
  "performance_wall_time_sec_std": 0.012,
  "performance_peak_rss_mb_mean": 125.3,
  "performance_peak_rss_mb_p5": 125.0,
  "performance_peak_rss_mb_p50": 125.1,
  "performance_peak_rss_mb_p95": 126.2,
  "performance_peak_rss_mb_std": 0.5,
  "performance_per_step_ms_mean": 4.902,
  "performance_per_step_ms_p5": 4.895,
  "performance_per_step_ms_p50": 4.900,
  "performance_per_step_ms_p95": 4.950,
  "performance_per_step_ms_std": 0.024,
  "performance_neuron_steps_per_sec_mean": 204082,
  "performance_neuron_steps_per_sec_p5": 202500,
  "performance_neuron_steps_per_sec_p50": 204164,
  "performance_neuron_steps_per_sec_p95": 205000,
  "performance_neuron_steps_per_sec_std": 1020,
  "stability_nan_rate_mean": 0.0,
  "stability_nan_rate_p5": 0.0,
  "stability_nan_rate_p50": 0.0,
  "stability_nan_rate_p95": 0.0,
  "stability_nan_rate_std": 0.0,
  "reproducibility_bitwise_delta_mean": 0.0
}
```

## Units Reference

| Quantity | Unit | Symbol |
|----------|------|--------|
| Time | seconds | s |
| Time | milliseconds | ms |
| Memory | megabytes | MB |
| Timestep | milliseconds | ms |
| Throughput | neuron-steps per second | neuron-steps/sec |

**Conversions:**
- 1 second = 1000 milliseconds
- 1 megabyte = 1024 × 1024 bytes
- 1 neuron-step = 1 neuron simulated for 1 timestep

## Aggregation Statistics

All metrics report 5 aggregation statistics:
- **mean**: Arithmetic mean across repeats
- **p5**: 5th percentile - captures best-case behavior
- **p50**: Median (50th percentile) - robust to outliers
- **p95**: 95th percentile - captures worst-case behavior
- **std**: Standard deviation - measures variance

Use **p50** for typical performance, **p95** for worst-case, **std** for stability assessment.

## Changelog

- **2026-01-24**: Initial schema (git SHA: cc3b5f0c8d75c398a488d70390e9917cc720ba21)
