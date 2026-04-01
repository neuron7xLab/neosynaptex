# Hardened Validator — Real Failures Found and Fixed

## Initial hardened run failures
- `distribution_anomaly` false-positive FAILs on heterogeneous benchmark/result JSON payloads (`max_z > 6`) where scalar flattening mixed incompatible units.
- `log_domain_guard` check failed with `NameError` due missing contract import wiring.

## Root causes
1. Distribution anomaly check was mathematically invalid for nested heterogeneous records.
2. Validator wiring bug omitted `assert_no_log_domain_violation` from imports.

## Fixes
1. Scoped `distribution_anomaly` to skip heterogeneous dict records and rely on domain-specific trajectory checks for temperature-ablation payloads.
2. Added missing import for log-domain contract and executed numeric hazard guard check in `src/bnsyn/criticality/analysis.py` path.

## Verification
- Re-run `python scripts/math_validate.py` produced `FAIL: 0` with category coverage retained.
- Updated report files in `artifacts/math_audit/` reflect post-fix state.
