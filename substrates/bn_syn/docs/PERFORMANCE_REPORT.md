# Performance Report

Benchmark performance summary from the current benchmark baselines.

## Network Size vs Performance

| Scenario | N | Steps | Wall time (s) | Per-step (ms) | Peak RSS (MB) | Throughput (neuron-steps/s) |
| --- | --- | --- | --- | --- | --- | --- |
| small_network | 128 | 300 | 0.1129 | 0.3764 | 67.51 | 340,058 |
| medium_network | 512 | 400 | 0.2220 | 0.5551 | 71.75 | 922,394 |
| large_network | 2000 | 400 | 1.1421 | 2.8554 | 71.75 | 700,436 |

## Notes

- Values are from the locked benchmark baselines and are intended for regression detection and trend tracking.
