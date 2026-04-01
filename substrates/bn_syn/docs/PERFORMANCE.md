# BN-Syn Performance Benchmarks

Environment:

| Field | Value |
| --- | --- |
| Timestamp | 2026-01-25T10:11:14Z |
| Git commit | 90fb51101f7ef8f8f67aa9d6fcaaabfdf74879c1 |
| CPU | x86_64 |
| RAM (GB) | 17.930950164794922 |
| Seed | 42 |

## Benchmark: Scale (N ∈ {100, 500, 1000, 2000})

Parameters: dt=0.1 ms, steps=200, p_conn=0.05, frac_inhib=0.2.

| N | Synapses | Runtime (s) | Peak RSS (MB) | Synaptic updates/s | Spikes/s |
| --- | --- | --- | --- | --- | --- |
| 100 | 504 | 0.024907982000058837 | 87.07421875 | 4,046,895.4891553195 | 0.0 |
| 500 | 12,395 | 0.039186363000226265 | 90.15625 | 63,261,803.602076724 | 0.0 |
| 1000 | 49,742 | 0.05490010899984554 | 97.54296875 | 181,209,111.98970458 | 0.0 |
| 2000 | 199,915 | 0.08572894300004918 | 126.96875 | 466,388,580.1085529 | 0.0 |

## Benchmark: dt sweep (dt ∈ {0.2, 0.1, 0.05})

Parameters: N=500, steps=200, p_conn=0.05, frac_inhib=0.2.

| dt (ms) | Runtime (s) | Peak RSS (MB) | Synaptic updates/s | Stable |
| --- | --- | --- | --- | --- |
| 0.2 | 0.02900384899976416 | 89.71875 | 85,471,414.50157727 | true |
| 0.1 | 0.03479983600027481 | 89.84375 | 71,235,967.89307927 | true |
| 0.05 | 0.03228141900035553 | 89.84375 | 76,793,402.4205286 | true |

## Benchmark: Plasticity ON vs OFF

Parameters: N=300, steps=120, dt=0.1 ms, p_conn=0.1, spike_prob=0.05.

| Plasticity | Runtime (s) | Peak RSS (MB) | Synaptic updates/s | Weight sum |
| --- | --- | --- | --- | --- |
| ON | 0.25660505199994077 | 92.5390625 | 4,158,764.5749088614 | 13,488.99561453496 |
| OFF | 0.0003319930001453031 | 89.79296875 | 0.0 | 8,879.236943223797 |

## Scaling curves (measured values)

* Scale benchmark synaptic updates/s rises from 4,046,895.4891553195 (N=100) to 466,388,580.1085529 (N=2000) at dt=0.1 ms.  
* dt sweep runtime remains in the 0.02900384899976416–0.03479983600027481 s range for N=500 and steps=200.  
* Plasticity ON adds 0.25660505199994077 s runtime versus 0.0003319930001453031 s with plasticity OFF for N=300.  

## Practical limits (measured in this environment)

* Max neurons measured: N=2000 (synapses=199,915) at dt=0.1 ms.  
* Max dt resolution measured: dt=0.05 ms (stable=true).  
* Plasticity cost: 4,158,764.5749088614 synaptic updates/s with plasticity ON at N=300.  

## Reproduce

```bash
python benchmarks/benchmark_scale.py
python benchmarks/benchmark_dt.py
python benchmarks/benchmark_plasticity.py
```

## Performance baselines and regression gate

Baselines for the physics benchmark and kernel profiling live in:

* `benchmarks/baselines/physics_baseline.json`
* `benchmarks/baselines/kernel_profile.json`

CI executes the benchmarks and blocks PRs when regressions exceed 10% relative
to the baselines. The regression gate is enforced via:

```bash
python -m scripts.benchmark_physics --output benchmarks/physics_current.json
python -m scripts.profile_kernels --steps 100 --output benchmarks/kernel_profile_current.json
python -m scripts.check_benchmark_regressions \
  --physics-baseline benchmarks/baselines/physics_baseline.json \
  --physics-current benchmarks/physics_current.json \
  --kernel-baseline benchmarks/baselines/kernel_profile.json \
  --kernel-current benchmarks/kernel_profile_current.json \
  --threshold 0.10
```

## Benchmark JSON samples

### Scale

```json
{
  "git_commit": "90fb51101f7ef8f8f67aa9d6fcaaabfdf74879c1",
  "hardware": {
    "cpu": "x86_64",
    "ram_gb": 17.930950164794922
  },
  "parameters": {
    "dt_ms": 0.1,
    "frac_inhib": 0.2,
    "max_memory_mb": 1024.0,
    "max_runtime_sec": 30.0,
    "p_conn": 0.05,
    "sizes": [
      100,
      500,
      1000,
      2000
    ],
    "smoke": false,
    "steps": 200
  },
  "results": {
    "dt": 0.1,
    "events_per_sec": 466388580.1085529,
    "memory_mb": 126.96875,
    "neurons": 2000,
    "runtime_sec": 0.5360601430002134,
    "spike_count": 0.0,
    "spikes_per_sec": 0.0,
    "steps": 200,
    "synapses": 199915,
    "synaptic_updates_per_sec": 466388580.1085529
  },
  "seed": 42,
  "timestamp": "2026-01-25T10:11:03.872742+00:00"
}
```

### dt sweep

```json
{
  "git_commit": "90fb51101f7ef8f8f67aa9d6fcaaabfdf74879c1",
  "hardware": {
    "cpu": "x86_64",
    "ram_gb": 17.930950164794922
  },
  "parameters": {
    "dt_values": [
      0.2,
      0.1,
      0.05
    ],
    "frac_inhib": 0.2,
    "neurons": 500,
    "p_conn": 0.05,
    "smoke": false,
    "steps": 200
  },
  "results": {
    "dt": 0.05,
    "events_per_sec": 76793402.4205286,
    "memory_mb": 89.84375,
    "neurons": 500,
    "runtime_sec": 0.0960851040003945,
    "spike_count": 0.0,
    "spikes_per_sec": 0.0,
    "steps": 200,
    "synapses": 12395,
    "synaptic_updates_per_sec": 76793402.4205286
  },
  "seed": 42,
  "timestamp": "2026-01-25T10:11:09.228996+00:00"
}
```

### Plasticity

```json
{
  "git_commit": "90fb51101f7ef8f8f67aa9d6fcaaabfdf74879c1",
  "hardware": {
    "cpu": "x86_64",
    "ram_gb": 17.930950164794922
  },
  "parameters": {
    "dt_ms": 0.1,
    "neurons": 300,
    "p_conn": 0.1,
    "smoke": false,
    "spike_prob": 0.05,
    "steps": 120
  },
  "results": {
    "dt": 0.1,
    "events_per_sec": 4158764.5749088614,
    "memory_mb": 92.5390625,
    "neurons": 300,
    "runtime_sec": 0.25660505199994077,
    "spike_count": 0.0,
    "spikes_per_sec": 0.0,
    "steps": 120,
    "synapses": 8893,
    "synaptic_updates_per_sec": 4158764.5749088614
  },
  "seed": 42,
  "timestamp": "2026-01-25T10:11:14.247132+00:00"
}
```
