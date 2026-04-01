# Benchmark Summary

## Quick Reference

| Operation | Grid | Time | Throughput |
|-----------|------|------|-----------|
| simulate | 64x64 | ~18 ms | 27M cells/sec |
| extract | 64x64 | ~4 ms | - |
| detect | 64x64 | ~2 ms | - |
| forecast (h=4) | 64x64 | ~8 ms | - |
| compare | 64x64 | ~1 ms | - |
| **Full pipeline** | **64x64** | **~77 ms** | - |

## Generated Artifacts

| File | Content |
|------|---------|
| `benchmarks/results/benchmark_core.json` | Per-operation timing and throughput |
| `benchmarks/results/benchmark_core.csv` | Tabular core benchmark data |
| `benchmarks/results/benchmark_scalability.json` | Grid scaling (16x16 to 256x256) |
| `benchmarks/results/benchmark_scalability.csv` | Tabular scalability data |
| `benchmarks/results/benchmark_quality.json` | Forecast accuracy, detection stability |
| `benchmarks/results/benchmark_quality.csv` | Tabular quality metrics |

## Running Benchmarks

```bash
make benchmark
```

## Policy

Quality benchmark baseline deltas are recorded in `benchmark_quality.json` / `.csv`. Public benchmark claims must cite these files directly, not prose-only statements.

Benchmark acceptance is consumed by the showcase generation, baseline parity, and attestation release pipeline.

Full methodology: [docs/BENCHMARKS.md](docs/BENCHMARKS.md)
