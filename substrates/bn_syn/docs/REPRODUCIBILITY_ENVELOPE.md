# Reproducibility Envelope

This document defines the reproducibility guarantees enforced by BN-Syn benchmarks and CI gates.

## Seed Protocol

* All benchmarks use explicit integer seeds via `bnsyn.rng.seed_all`.
* Seed values are recorded in benchmark outputs and must be reused for exact trace reproduction.
* Determinism is verified by asserting bitwise-identical traces for identical seeds.

## Δt Tolerance

* Δt invariance is assessed by comparing `dt = 0.1 ms` and `dt = 0.05 ms` for equal wall-clock
  duration.
* Allowed drift thresholds:
  * Sigma drift ≤ 0.05 (relative).
  * Firing-rate drift ≤ 0.15 (relative).
  * Weight distribution drift ≤ 1e-12 (relative).

## Floating-Point Drift Limits

* Determinism uses max absolute error ≤ `1e-12` for identical-seed traces.
* All benchmarks reject NaN/Inf metric values and enforce finite correlation values.

## Platform Expectations

* Benchmarks are CPU-only and must remain reproducible on standard x86_64 Linux runners.
* GPU and mixed-precision execution are out of scope for the reproducibility envelope.

## CI Verification

The `benchmarks.yml` workflow (standard tier, `ci` profile) enforces determinism, Δt-invariance,
criticality thresholds, and rejects regressions outside the envelope.


## Canonical proof spine note

The canonical proof spine gate (`bnsyn proof-check-envelope`) currently enforces a fixed-policy 10-seed **admissibility band** (sanity envelope), not a calibrated statistical confidence envelope.
