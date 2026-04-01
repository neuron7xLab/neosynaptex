# Release Candidate Checklist — v4.1.0

## Baseline Reference

| Property | Value |
|----------|-------|
| **Baseline commit** | `ca636a7009995263b4d66877e0707156ce59f7f2` |
| **Branch** | `main` |
| **Date** | 2026-03-22 |
| **Engine version** | 4.1.0 |
| **Python** | >=3.10, <3.14 |

## Baseline Metrics

| Metric | Value |
|--------|-------|
| Tests passed | 1,689 |
| Tests skipped | 6 |
| Tests failed | 0 |
| Coverage (branch) | 82.21% |
| Causal rules | 41 |
| Import contracts | 7/7 KEPT |
| Docs drift | OK |
| Config-governed thresholds | 87 |
| CI workflows | 5 |
| Silent downgrades | 0 |

## Release Readiness Gates

### 1. Environment Reproducibility
- [ ] `pip install -e ".[dev]"` in clean venv succeeds
- [ ] `pytest` runs without manual `PYTHONPATH` or `addopts` override
- [ ] `import mycelium_fractal_net` works from any directory
- [ ] `uv sync --group dev` equivalent result
- [ ] Container build reproduces the same test results

### 2. CI/CD
- [ ] `.github/workflows/ci.yml` — lint, types, test matrix, coverage, import contracts
- [ ] `.github/workflows/release.yml` — artifact build, sign, publish gate
- [ ] `.github/workflows/security.yml` — bandit, pip-audit, gitleaks, SBOM
- [ ] `.github/workflows/benchmarks.yml` — regression detection with threshold
- [ ] PR cannot merge without green CI
- [ ] Release cannot publish without artifact integrity pass

### 3. Causal Validation Gate
- [ ] Machine-readable output: rule_id, severity, category, evidence, provenance_hash, decision
- [ ] Modes: `strict` (release), `observe` (dev), `permissive` (experiment)
- [ ] Replay-consistent: same input → same causal decision
- [ ] Failure taxonomy: numerical, structural, causal, contract, provenance
- [ ] High-level report blocked without causal verdict
- [ ] `provenance_hash` computed from input + config + engine version

### 4. Threshold/Config Governance
- [ ] All decision thresholds in versioned `configs/*.json`
- [ ] Zero inline magic numbers in detect/compare/forecast decision paths
- [ ] Config schema validation at load time
- [ ] Config hash in every manifest and report
- [ ] Config drift test between code and documentation

### 5. Artifact Integrity
- [ ] Bundle self-hash verification
- [ ] Deterministic artifact naming
- [ ] No missing/extra artifacts between manifest and filesystem
- [ ] Block publish on integrity failure
- [ ] Report bundle reproducibility documented

### 6. Test Hardening
- [ ] Coverage ≥ 80% overall, ≥ 90% on decision paths
- [ ] Property tests: perturbation stability, threshold monotonicity, replay determinism
- [ ] Negative tests: corrupted descriptor, forged manifest, config mismatch
- [ ] Separate regression suite for release contour

### 7. API/CLI Contract Alignment
- [ ] Same semantics across SDK, CLI, API
- [ ] Same error codes and causal semantics
- [ ] Same config resolution
- [ ] Same artifact contract
- [ ] Documented breaking changes (if any)

### 8. Release Governance
- [ ] `RELEASE_GOVERNANCE.md` with criteria and classification
- [ ] Mandatory benchmark comparison for release
- [ ] Reproducibility sheet for each release
- [ ] Signed release checklist
- [ ] Known limitations explicit

### 9. Observability
- [ ] Structured logging on causal/report/release paths
- [ ] Diagnostic dump on failure
- [ ] No silent downgrades
- [ ] Machine evidence separated from human summary

### 10. Security & Supply Chain
- [ ] Lockfile discipline (`uv.lock` committed and verified)
- [ ] Dependency audit in CI (pip-audit)
- [ ] Secret scan in CI (gitleaks)
- [ ] SBOM generated for release
- [ ] Dockerfile reproducible build path
- [ ] Release artifacts checksummed

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | | | |
| Reviewer | | | |
