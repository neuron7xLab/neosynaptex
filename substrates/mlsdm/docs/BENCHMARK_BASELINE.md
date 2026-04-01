# Benchmark Baseline Management

This document explains how to manage performance benchmark baselines for MLSDM.

## Overview

MLSDM tracks performance metrics using benchmarks and compares them against established baselines to detect performance regressions, aligning with risk-managed performance governance expectations [@nist2023_rmf].

## Baseline File

The baseline is stored in `benchmarks/baseline.json` and includes:

- **Threshold values**: Absolute limits (e.g., P95 < 500ms)
- **Baseline metrics**: Expected performance values
- **Regression tolerance**: Allowable variance (default: 20%)
- **Metadata**: Update timestamp, git commit, notes

## Running Benchmarks

### Locally

```bash
# Run benchmarks
make bench

# This generates benchmark-metrics.json with current performance data
```

### In CI

Benchmarks run automatically in the `ci-neuro-cognitive-engine.yml` workflow:
- Runs on every PR and push to main
- Generates `benchmark-metrics.json` artifact
- Uploads artifact with 90-day retention

## Checking for Drift

### Automatic (in CI)

The CI workflow automatically checks for baseline drift after running benchmarks. Results appear in the GitHub Actions summary.

### Manual

```bash
# Run benchmarks first
make bench

# Check drift against baseline
make bench-drift

# Or use the script directly
python scripts/check_benchmark_drift.py benchmark-metrics.json
```

### Drift Check Modes

- **Warning mode** (default): Reports drift but doesn't fail
- **Strict mode**: Fails on any regression
  ```bash
  python scripts/check_benchmark_drift.py benchmark-metrics.json --strict
  ```

## Updating the Baseline

Update the baseline when:
1. You've made intentional performance improvements
2. The baseline is outdated due to infrastructure changes
3. You've verified new performance is acceptable and sustainable

### Steps to Update

1. **Run benchmarks** to generate current metrics:
   ```bash
   make bench
   ```

2. **Review the results** to ensure they're acceptable:
   ```bash
   cat benchmark-metrics.json
   ```

3. **Update the baseline**:
   ```bash
   python scripts/check_benchmark_drift.py benchmark-metrics.json --update-baseline
   ```

4. **Commit the updated baseline**:
   ```bash
   git add benchmarks/baseline.json
   git commit -m "Update benchmark baseline after performance improvement"
   ```

5. **Document the change** in your PR description:
   - What changed
   - Why performance improved (or changed)
   - New baseline values

## Benchmark Metrics Schema

The `benchmark-metrics.json` file follows this schema:

```json
{
  "timestamp": "ISO 8601 timestamp",
  "commit": "git commit SHA (first 8 chars)",
  "metrics": {
    "p95_latencies_ms": [15.2, 85.3, 420.1],
    "max_p95_ms": 420.1
  },
  "slo_compliant": true
}
```

## Interpreting Results

### ✅ Pass

- Current metrics are within baseline + tolerance
- SLO compliance check passed
- No action needed

### ⚠️ Warning

- Current metrics exceed baseline by more than tolerance
- Still within absolute thresholds
- Review the change and consider if it's acceptable

### ❌ Regression

- Current metrics exceed absolute thresholds
- This blocks merges in strict mode
- **Action required**: Investigate and fix the regression

## Troubleshooting

### Benchmarks are flaky

1. Benchmarks use `local_stub` backend for consistency
2. Run benchmarks multiple times to verify consistency
3. Consider increasing regression tolerance if needed

### Baseline seems wrong

1. Check when baseline was last updated: `cat benchmarks/baseline.json`
2. Review baseline notes for context
3. Run benchmarks on main branch to compare
4. If baseline is clearly outdated, follow update steps above

### Drift check fails in CI but passes locally

1. CI environment may differ from local
2. Check CI logs for actual metrics
3. Download CI artifacts to compare
4. Consider that CI may have more or less resources

## Related Files

- `benchmarks/baseline.json` - Baseline configuration
- `benchmarks/test_neuro_engine_performance.py` - Benchmark tests
- `scripts/check_benchmark_drift.py` - Drift checking script
- `.github/workflows/ci-neuro-cognitive-engine.yml` - CI integration
- `Makefile` - Convenience commands (`make bench`, `make bench-drift`)

## Best Practices

1. **Always run benchmarks** before updating baseline
2. **Document changes** when updating baseline
3. **Review trends** over time using CI artifacts
4. **Keep tolerance reasonable** (20% is a good default)
5. **Don't update baseline** to hide regressions
6. **Run benchmarks on same hardware** for consistency
