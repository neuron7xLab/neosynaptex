# Scalability

## Methodology

Scalability is measured by running the reference network with a fixed workload and
recording wall-clock runtime, per-step cost, and peak resident memory.

**Configuration**

* Steps: 200
* Δt: 0.1 ms
* External drive: `ext_rate_hz = 1000.0`, `ext_w_nS = 50.0`
* Seed: 13

Command:

```
python benchmarks/scalability.py
```

## Results (CPU)

| N (neurons) | Runtime (s) | Step cost (ms) | Peak RSS (MB) |
| --- | --- | --- | --- |
| 50 | 0.038295 | 0.191474 | 86.54 |
| 100 | 0.036082 | 0.180410 | 86.54 |
| 500 | 0.042170 | 0.210850 | 89.56 |
| 1000 | 0.063340 | 0.316700 | 97.19 |

## Notes

* Results are from a single deterministic run on the CI-like CPU container.
* Use the command above to regenerate measurements on other hardware and compare.
