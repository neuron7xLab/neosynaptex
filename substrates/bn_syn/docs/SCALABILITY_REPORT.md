# Scalability Report

Scalability observations from baseline benchmark runs.

## Network Size vs Memory

| Scenario | N | Peak RSS (MB) | Wall time (s) | Throughput (neuron-steps/s) |
| --- | --- | --- | --- | --- |
| small_network | 128 | 67.51 | 0.1129 | 340,058 |
| medium_network | 512 | 71.75 | 0.2220 | 922,394 |
| large_network | 2000 | 71.75 | 1.1421 | 700,436 |

## Notes

- Metrics are captured under fixed seeds and deterministic configuration.
- Large network scenario ensures scale coverage for nightly benchmarks.
