# CI Gates and Test Selection Strategy

**Version:** 2.0  
**Date:** 2026-01-27  
**Repository:** neuron7x/bnsyn-phase-controlled-emergent-dynamics

---

## Overview

This document defines the **3-tier test selection strategy** for BN-Syn, balancing fast PR feedback with comprehensive validation coverage.

### Design Principles

1. **BLOCKING gates** run on every PR (fast, <10 min total)
2. **NON-BLOCKING validation** runs on schedule (thorough, 30+ min)
3. **Isolation** ensures validation tests never block PRs
4. **Observability** through artifacts, summaries, and logs

---

## Test Tiers

### Tier 1: BLOCKING (PR Gates) ⚡

**Trigger:** Every push, every PR  
**Runtime:** <10 minutes total  
**Purpose:** Fast feedback, prevent obviously broken code  
**Policy:** Passing is mandatory for merge

#### Included Tests

1. **Smoke Suite** (`-m "not (validation or property)"`)
   - Unit tests, fast integration tests, edge cases
   - Target: ~85% code coverage
   - Runtime: ~5 minutes

2. **SSOT Validation**
   - Bibliography, claims, **claims coverage** (NEW, CLM-0011)
   - Normative tags, TierS misuse
   - Runtime: <30 seconds

3. **CLM-0011 Enforcement** - Ensures all normative claims have complete evidence
4. **Build & Import** - Package build + import checks
5. **Quality Gates** - Ruff, Pylint, Mypy
6. **Security Scans** - Gitleaks, pip-audit, Bandit
   - pip-audit runs with `--desc --format json` and stores `artifacts/pip-audit.json` for traceability

**Total Runtime:** ~8-10 minutes

---

### Tier 2: NON-BLOCKING Validation 🔬

**Trigger:** Daily 2 AM UTC + manual (mode: `elite`)  
**Runtime:** ~30 minutes  
**Policy:** Informational only

- **Validation Tests** (`-m validation`): Tests validating empirical claims
- **Property Tests** (`-m property`): Hypothesis tests with thorough profile (1000 examples)
- **Chaos Tests** (`-m "validation and chaos"`): Fault injection resilience tests

**Workflows:** `ci-validation.yml` (modes: `elite`, `property`, `chaos`)

---

### Tier 3: Performance Tracking 📊

**Trigger:** Weekly Sunday 3 AM UTC + manual  
**Runtime:** ~20 minutes  
**Policy:** Non-blocking

- 8 benchmark comparisons against golden baseline
- **Workflow:** `benchmarks.yml` (tier=elite)

---

## Coverage Trend History

Coverage trend observability is emitted directly by the reusable pytest workflow used by smoke/unit jobs.

- Artifact name (stable): `coverage-trend-metrics`
- Payload files: `coverage-trend.json`, `coverage-trend.csv`
- Fields: `timestamp`, `sha`, `branch`, `total_coverage` (0..100 scale), `coverage_state` (critical/low/moderate/high/excellent)
- Quantization thresholds: critical <50, low <70, moderate <85, high <95, excellent >=95
- Retention policy: 90 days
- Coverage XML remains mandatory and is uploaded as `coverage-xml-<sha>`

Viewer entry point:
1. Open GitHub Actions run for `ci-pr-atomic` or `ci-smoke`.
2. Open job `tests-smoke`.
3. Download artifact `coverage-trend-metrics`.

---

## Makefile Targets

```bash
make test                      # Smoke suite (excludes validation/property)
make test-validation           # Run validation suite locally
make validate-claims-coverage  # Check claims→evidence coverage
make docs-evidence             # Regenerate EVIDENCE_COVERAGE.md
```

---

## Summary Table

| Tier | Marker | Trigger | Runtime | Blocks PR | Workflow |
|------|--------|---------|---------|-----------|----------|
| **BLOCKING** | smoke | Every PR | ~8 min | ✅ YES | `ci-pr.yml` |
| **VALIDATION** | `@pytest.mark.validation` | Daily 2 AM | varies | ❌ NO | `ci-validation.yml` (mode: `elite`) |
| **PROPERTY** | `@pytest.mark.property` | Daily 2:30 AM | ~10 min | ❌ NO | `ci-validation.yml` (mode: `property`) |
| **CHAOS** | `@pytest.mark.chaos` | Daily 4 AM | ~20 min | ❌ NO | `ci-validation.yml` (mode: `chaos`) |
| **BENCHMARKS** | N/A | Weekly Sun 3 AM | ~20 min | ❌ NO | `benchmarks.yml` (tier=elite) |
