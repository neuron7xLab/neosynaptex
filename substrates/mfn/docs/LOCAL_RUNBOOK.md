# Local Development Runbook

## Setup

### First-time installation

```bash
make bootstrap        # Install uv, sync dependencies, run dev_doctor.py
```

### Install profiles

```bash
uv sync --group dev                      # Core + development tools
uv sync --group dev --extra ml           # + PyTorch (ML surfaces)
uv sync --group dev --extra accel        # + Numba (JIT Laplacian)
uv sync --group dev --group security     # + bandit, pip-audit, checkov
```

### Environment health check

```bash
make doctor           # Run dev_doctor.py diagnostic
```

---

## Daily Development

### Quality checks

```bash
make lint             # Ruff lint + format check (24 rule categories)
make typecheck        # mypy strict on types/ and security/
make test             # Full test suite (1,228 tests)
make coverage         # Tests + branch coverage (fail_under=80%)
make security         # Bandit + pip-audit
```

### Full verification

```bash
make verify           # lint + typecheck + import-linter + OpenAPI + verification matrix
make fullcheck        # verify + test + security — all gates in one command
```

---

## Pipeline Operations

```bash
make simulate         # Run 24x24 simulation
make extract          # Extract morphology descriptor
make detect           # Anomaly detection
make forecast         # Forecast field evolution
make compare          # Compare two field states
make report           # Full pipeline with artifact generation
```

---

## API Server

```bash
make api              # Start REST API on localhost:8000
```

---

## Benchmarks & Validation

```bash
make benchmark        # Core + scalability + quality benchmarks
make validate         # Scientific validation experiments + neurochem controls
```

---

## Contracts & Release

```bash
make contracts        # import-linter + OpenAPI + contract tests
make openapi          # Export + verify OpenAPI schema
make sbom             # Generate SBOM + sign artifacts
make release-proof    # Prepare release evidence pack
```

---

## Neuromodulation

```bash
# Scientific controls
uv run python validation/neurochem_controls.py

# Criticality sweep
uv run python scripts/criticality_sweep.py

# Neuromodulated report
uv run mfn report --grid-size 24 --steps 16 \
    --neuromod-profile gabaa_tonic_muscimol_alpha1beta3 \
    --agonist-concentration-um 0.85 \
    --output-root artifacts/runs
```

---

## Regression Hardening

```bash
make showcase         # showcase-generation + criticality sweep
make baseline-parity  # Baseline parity verification
make docs-drift       # Documentation drift check
```

### Full attestation pipeline

```bash
uv run python scripts/showcase_run.py       # showcase-generation
uv run python scripts/baseline_parity.py    # baseline-parity
uv run python scripts/docs_drift_check.py   # docs-drift
uv run python scripts/attest_artifacts.py   # attestation — Ed25519 signing
```

---

## Bundle Verification

```bash
uv run mfn verify-bundle artifacts/showcase/showcase_manifest.json
uv run mfn verify-bundle artifacts/release/release_manifest.json
```
