# Benchmark Protocol (alloc_v2)

## Scope

This protocol governs benchmark baselines and CI regression checks for the
current allocation regime (`alloc_v2`). It applies only to benchmark code,
CI logic, baseline artifacts, and documentation.

## Regime Identity

- **Regime ID**: `alloc_v2`
- **Rationale**: allocation-free hot paths in `Network.step()` and kernel profiling.

## Baseline Artifacts (SSOT)

Baselines are versioned by regime and stored in `benchmarks/baselines/`:

- `physics_baseline_alloc_v2.json`
- `kernel_profile_alloc_v2.json`
- `checksums_alloc_v2.json`
- Raw runs: `benchmarks/baselines/raw/*_alloc_v2.json`

Baselines are immutable once published.
Kernel `max_time_sec` metrics use a p95 estimate to reduce outlier noise.

## Regime Matching (CI)

`scripts/check_benchmark_regressions.py` enforces:

- `regime_id` must exist in both baseline and current files.
- `regime_id` must match `alloc_v2`.
- Missing or mismatched regimes cause CI failure.
- Threshold overrides are stored in each baseline JSON under `thresholds`.

## Baseline Regeneration Procedure

1. Warmup runs ≥ 2.
2. Measurement runs ≥ 5.
3. Median aggregation for each metric.
4. Store raw JSON runs and aggregated baseline JSON.
5. Generate checksums for all baseline files.

Command (local or controlled runner):

```bash
python -m scripts.generate_benchmark_baseline \
  --warmup 2 \
  --runs 5 \
  --physics-steps 1000 \
  --kernel-steps 100 \
  --output-dir benchmarks/baselines \
  --raw-dir benchmarks/baselines/raw
```

## Threshold Derivation

Empirical variance is logged in:

- `docs/benchmarks/threshold_derivation_alloc_v2.md`

Threshold overrides must be justified by observed max deltas plus safety margin.

## CI Comparison Report

Latest comparison report (baseline vs baseline sanity):

- `docs/benchmarks/ci_comparison_report_alloc_v2.txt`

## Regime Migration Notes

- `alloc_v2` replaces prior allocation regime by removing per-step heap
  allocations in hot loops. Baselines for previous regimes remain in
  `benchmarks/baselines/` for audit traceability.
