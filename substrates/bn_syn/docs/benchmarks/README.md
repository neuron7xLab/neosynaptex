# BN-Syn Benchmark Results
**Generated:** 2026-01-24T09:50:08.236090Z
**Git SHA:** `05f63878`
**Python:** 3.12.3

## Summary Table
| Scenario | N | Steps | dt (ms) | Time (s) | RSS (MB) | Throughput (neuron-steps/s) |
|----------|---|-------|---------|----------|----------|------------------------------|
| ci_smoke | 50 | 100 | 0.10 | 0.01 | 59.5 | 484,000 |
| n_sweep_100 | 100 | 500 | 0.10 | 0.05 | 59.5 | 990,043 |
| n_sweep_200 | 200 | 500 | 0.10 | 0.06 | 59.9 | 1,793,993 |
| steps_sweep_500 | 500 | 500 | 0.10 | 0.06 | 62.2 | 3,887,652 |
| steps_sweep_1000 | 500 | 1,000 | 0.10 | 0.13 | 62.2 | 3,935,724 |

## Detailed Metrics
### ci_smoke
**Description:** Minimal scenario for CI smoke test

**Parameters:**
- N_neurons: 50
- steps: 100
- dt_ms: 0.1
- p_conn: 0.05
- frac_inhib: 0.2
- seed: 42
- repeats: 3

**Timing:**
- wall_time: 0.010s (p50=0.010, p95=0.010, std=0.000)
- per_step: 0.103ms (p50=0.103, p95=0.104, std=0.000)

**Memory:**
- peak_rss: 59.5MB (p50=59.5, p95=59.6, std=0.1)

**Throughput:**
- neuron_steps/sec: 484,000 (p50=483,311, p95=486,060, std=1,721)

**Activity:**
- spike_count_total: 0

### n_sweep_100
**Description:** Network size sweep: N=100

**Parameters:**
- N_neurons: 100
- steps: 500
- dt_ms: 0.1
- p_conn: 0.05
- frac_inhib: 0.2
- seed: 42
- repeats: 3

**Timing:**
- wall_time: 0.051s (p50=0.051, p95=0.051, std=0.000)
- per_step: 0.101ms (p50=0.101, p95=0.102, std=0.001)

**Memory:**
- peak_rss: 59.5MB (p50=59.4, p95=59.6, std=0.1)

**Throughput:**
- neuron_steps/sec: 990,043 (p50=989,011, p95=999,785, std=8,541)

**Activity:**
- spike_count_total: 0

### n_sweep_200
**Description:** Network size sweep: N=200

**Parameters:**
- N_neurons: 200
- steps: 500
- dt_ms: 0.1
- p_conn: 0.05
- frac_inhib: 0.2
- seed: 42
- repeats: 3

**Timing:**
- wall_time: 0.056s (p50=0.056, p95=0.056, std=0.000)
- per_step: 0.111ms (p50=0.112, p95=0.112, std=0.001)

**Memory:**
- peak_rss: 59.9MB (p50=59.8, p95=59.9, std=0.1)

**Throughput:**
- neuron_steps/sec: 1,793,993 (p50=1,787,379, p95=1,812,115, std=15,084)

**Activity:**
- spike_count_total: 0

### steps_sweep_500
**Description:** Steps sweep: steps=500

**Parameters:**
- N_neurons: 500
- steps: 500
- dt_ms: 0.1
- p_conn: 0.05
- frac_inhib: 0.2
- seed: 42
- repeats: 3

**Timing:**
- wall_time: 0.064s (p50=0.064, p95=0.065, std=0.000)
- per_step: 0.129ms (p50=0.129, p95=0.129, std=0.001)

**Memory:**
- peak_rss: 62.2MB (p50=62.2, p95=62.2, std=0.0)

**Throughput:**
- neuron_steps/sec: 3,887,652 (p50=3,877,054, p95=3,920,682, std=27,635)

**Activity:**
- spike_count_total: 0

### steps_sweep_1000
**Description:** Steps sweep: steps=1000

**Parameters:**
- N_neurons: 500
- steps: 1,000
- dt_ms: 0.1
- p_conn: 0.05
- frac_inhib: 0.2
- seed: 42
- repeats: 3

**Timing:**
- wall_time: 0.127s (p50=0.127, p95=0.128, std=0.001)
- per_step: 0.127ms (p50=0.127, p95=0.128, std=0.001)

**Memory:**
- peak_rss: 62.2MB (p50=62.3, p95=62.3, std=0.1)

**Throughput:**
- neuron_steps/sec: 3,935,724 (p50=3,942,354, p95=3,957,744, std=22,574)

**Activity:**
- spike_count_total: 0

---
*This report is auto-generated from benchmark results. See [PROTOCOL.md](PROTOCOL.md) for reproducibility details.*
