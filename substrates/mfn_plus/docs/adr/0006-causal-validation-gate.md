# ADR-0006: Causal Validation Gate

## Status
Accepted

## Context
The MFN pipeline (simulate → extract → detect → forecast → compare → report) executes stages sequentially, with each stage trusting the previous one's output. No mechanism existed to verify that conclusions follow from data and invariants rather than from type compatibility alone.

Symptoms observed:
- Detection could produce "reorganized" regime without plasticity evidence
- Forecast could produce field values outside biophysical bounds without flagging
- Report published artifacts regardless of internal consistency
- No perturbation stability check — small noise could flip detection labels near thresholds

## Decision
Introduce a **Causal Validation Gate** — an independent verification layer that checks every algorithmic conclusion against system goals, internal invariants, environment constraints, and expected consequences.

### Architecture
- `types/causal.py`: Typed result schema (`CausalRuleResult`, `CausalValidationResult`, `CausalSeverity`, `CausalDecision`, `ViolationCategory`)
- `core/causal_validation.py`: Rule engine with `validate_causal_consistency()` entrypoint
- `configs/causal_validation_v1.json`: Versioned rule catalog with severity and thresholds
- Integration in `pipelines/reporting.py`: after all stages, before manifest finalization

### Rule Categories
- **Numerical**: NaN/Inf, bounds, conservation laws
- **Structural**: Shape consistency, required keys
- **Causal**: Cause-effect consistency between stages
- **Provenance**: Version, hash, traceability
- **Contract**: API/type contract compliance

### Failure Semantics
- **PASS**: Zero errors, zero warnings
- **DEGRADED**: Warnings present (report proceeds, logged in `causal_validation.json`)
- **FAIL**: Errors present (report blocked with RuntimeError)

## Consequences
- Every report includes `causal_validation.json` with full rule trace
- No report can be published with error-level violations
- Perturbation stability is checked for every detection
- CI includes `CAUSAL_VALIDATION` stage
- Rule catalog is versioned and config↔code sync is tested

## Non-Goals
- Does not prove external truth — only internal logical correctness
- Does not replace the simulation engine or detection strategy
- Does not add latency-critical path checks (perturbation is bounded to 3 seeds)
