# Benchmarks

## Overview

MFN benchmarks measure throughput, latency, accuracy, and scalability across the simulation pipeline. Benchmarks run on commodity hardware (single-threaded CPU, no GPU) to establish reproducible baselines.

## Benchmark Suite

| Benchmark | Script | What it measures |
|-----------|--------|-----------------|
| Core | `benchmarks/benchmark_core.py` | Per-operation latency: simulate, extract, detect, forecast, compare |
| Scalability | `benchmarks/benchmark_scalability.py` | Grid scaling (16x16 to 256x256), step scaling, memmap history overhead |
| Quality | `benchmarks/benchmark_quality.py` | Forecast accuracy (structural error, damping), feature extraction consistency |

### Running Benchmarks

```bash
make benchmark
```

Or individually:

```bash
uv run python benchmarks/benchmark_core.py
uv run python benchmarks/benchmark_scalability.py
uv run python benchmarks/benchmark_quality.py
```

Results are written to `benchmarks/results/` as JSON and CSV.

## Performance Characteristics

### Throughput

| Operation | Grid | Steps | Time | Throughput |
|-----------|------|-------|------|-----------|
| simulate | 64x64 | 32 | ~18 ms | 27M cells/sec |
| extract | 64x64 | - | ~4 ms | - |
| detect | 64x64 | - | ~2 ms | - |
| forecast | 64x64 | h=4 | ~8 ms | - |
| compare | 64x64 | - | ~1 ms | - |
| **Full pipeline** | **64x64** | **32** | **~77 ms** | - |

### Scalability

| Grid | Steps | simulate | Full pipeline | Memory |
|------|-------|----------|---------------|--------|
| 16x16 | 16 | ~1 ms | ~5 ms | ~2 MB |
| 32x32 | 32 | ~5 ms | ~20 ms | ~4 MB |
| 64x64 | 32 | ~18 ms | ~77 ms | ~8 MB |
| 128x128 | 64 | ~120 ms | ~400 ms | ~32 MB |
| 256x256 | 128 | ~900 ms | ~2.5 s | ~128 MB |

### Scale Limits

| Contour | Grid | Status |
|---------|------|--------|
| Default | up to 512x512 | Recommended for production use |
| Stress | 512x512 long-history | Benchmark contour, memmap required |
| Experimental | 1024x1024 | Requires explicit opt-in, OOM profiling incomplete |

## Quality Baselines

### Forecast Accuracy

| Metric | Baseline | Acceptable range |
|--------|----------|-----------------|
| Structural error | up to 0.15 | [0.0, 0.20] |
| Damping coefficient | 0.85-0.92 | [0.80, 0.95] |

### Feature Extraction Consistency

Deterministic: identical `SimulationSpec` produces bit-identical `MorphologyDescriptor` across runs (verified by golden regression tests with SHA256 fingerprinting).

### Detection Stability

Perturbation tests verify that anomaly and regime labels are stable under noise injection (epsilon = 1e-6) across 3 independent seeds (causal rules PTB-001, PTB-002).

## Methodology

1. **Warm-up:** 3 untimed iterations before measurement.
2. **Measurement:** 10 timed iterations, report median and p95.
3. **Isolation:** Single-threaded, no background load, `gc.disable()` during measurement.
4. **Reproducibility:** Fixed seeds, deterministic engine, results include SHA256 of input spec.

## Baseline Configuration

Baseline parameters are stored in `benchmarks/bio_baseline.json`. Benchmark gates compare measured values against baseline with margin to detect regressions.

## Artifacts

| File | Format | Content |
|------|--------|---------|
| `benchmarks/results/benchmark_core.json` | JSON | Per-operation timing results |
| `benchmarks/results/benchmark_core.csv` | CSV | Tabular core results |
| `benchmarks/results/benchmark_scalability.json` | JSON | Grid/step scaling data |
| `benchmarks/results/benchmark_scalability.csv` | CSV | Tabular scalability results |
| `benchmarks/results/benchmark_quality.json` | JSON | Accuracy and consistency metrics |
| `benchmarks/results/benchmark_quality.csv` | CSV | Tabular quality results for analysis |

All benchmark claims in documentation or publications must cite these files directly.
