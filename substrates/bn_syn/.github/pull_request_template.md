<!--
CI policy check enforces these exact sections (case-insensitive text match):
- what changed
- why
- risk
- evidence
- how to test
Do not remove or rename these headings.
-->

## What changed

> **Required by CI policy:** keep these 5 section titles exactly as written: `What changed`, `Why`, `Risk`, `Evidence`, `How to test`.

-

## Why

-

## Risk

-

## Evidence

-

## How to test

```bash
# add exact verification commands
```

## Canonical Vector Check (Required)
- [ ] Preserves `bnsyn run --profile canonical --plot --export-proof` as the canonical proof command.
- [ ] Preserves canonical artifacts: `emergence_plot.png`, `summary_metrics.json`, `criticality_report.json`, `avalanche_report.json`, `phase_space_report.json`, `run_manifest.json`.
- [ ] Strengthens at least one of Result / Narrative / Audience vectors without introducing drift.

## Labels policy

Supported control labels:
- `run-property`
- `run-validation`
- `run-codeql`
- `heavy-ci`

---

## Description

Provide a clear and concise description of your changes.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🏗️ Infrastructure/CI change
- [ ] 🧪 Test improvement

## Pre-Merge Checklist

**REQUIRED before creating PR:**

### Local Verification
- [ ] Ran `pre-commit run --all-files` ✅
- [ ] Ran `make check` (ruff, mypy, pylint) ✅
- [ ] Ran `pytest -m "not validation" --cov=src/bnsyn --cov-fail-under=85` ✅
- [ ] Code coverage ≥85% ✅
- [ ] No linter errors ✅
- [ ] mypy --strict passed ✅

### SSOT Gates (Single Source of Truth)
- [ ] Validated bibliography: `python -m scripts.validate_bibliography` ✅
- [ ] Validated claims: `python -m scripts.validate_claims` ✅
- [ ] Scanned governed docs: `python -m scripts.scan_governed_docs` ✅
- [ ] Scanned normative tags: `python -m scripts.scan_normative_tags` ✅

### Determinism (A1: 96%)
- [ ] Used `seed_all()` for any random operations ✅
- [ ] Verified determinism (3x runs with same seed produce identical outputs) ✅
- [ ] No global numpy RNG usage ✅

### Documentation (A7: 90%)
- [ ] All new functions have docstrings (Google style) ✅
- [ ] Updated `docs/SPEC.md` if changing specifications ✅
- [ ] Updated `README.md` if changing user-facing features ✅

### Security (A6: 90%)
- [ ] No secrets committed (verified with gitleaks) ✅
- [ ] Ran `pip-audit` (no vulnerabilities) ✅
- [ ] Ran `bandit -r src/ -ll` (no high/medium issues) ✅

## Testing

**Categories tested:**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Property-based tests (Hypothesis)
- [ ] Validation tests (large N, statistical)
- [ ] Benchmarks (performance)

**Commands run:**
```bash
# Example:
pytest tests/test_neuron.py -v
pytest tests/test_determinism.py -v --count 3  # 3x for determinism
```

## Performance Impact

- [ ] No performance impact
- [ ] Performance improved (provide benchmarks)
- [ ] Performance degraded (justify and provide mitigation)

**Benchmarks (if applicable):**
```
# Before: X ms
# After: Y ms
```

## Breaking Changes

- [ ] No breaking changes
- [ ] Breaking changes (list below):

**Migration guide (if breaking):**
```
# How to update existing code
```

## Reproducibility Commands

Provide exact commands to reproduce your changes:

```bash
# Clone and setup
git clone https://github.com/neuron7x/bnsyn-phase-controlled-emergent-dynamics.git
cd bnsyn-phase-controlled-emergent-dynamics
git checkout <branch-name>

# Install dependencies
pip install -e ".[dev,test,viz]"

# Run specific tests
pytest tests/... -v

# Verify determinism
pytest tests/test_determinism.py -v --count 3
```

## Checklist for Reviewer

**Axiom Compliance:**
- [ ] A1 (Determinism): seed_all() used, no global RNG
- [ ] A2 (Composability): Reusable functions/classes, no tight coupling
- [ ] A3 (Observability): Logging, error messages, docstrings
- [ ] A4 (Exhaustiveness): Edge cases tested, coverage ≥85%
- [ ] A5 (Performance): No unnecessary loops, efficient algorithms
- [ ] A6 (Security): No secrets, no unsafe operations
- [ ] A7 (Documentation): Docstrings, README updates, SPEC.md updates

**Code Quality:**
- [ ] Code is readable and maintainable
- [ ] No unnecessary complexity
- [ ] Follows existing code style
- [ ] Tests are clear and comprehensive

## Related Issues

Closes #(issue number)

## Additional Notes

Any additional information that would be helpful for reviewers.


## Documentation and Traceability Obligations

- [ ] If touching `specs/**`, `schemas/**`, `claims/**`, `src/**`, or `scripts/**`, updated `docs/TRACEABILITY.md`.
- [ ] Ran `python -m scripts.validate_traceability`.
- [ ] Ran `python -m scripts.check_internal_links`.
- [ ] Ran `python -m scripts.discover_public_surfaces` when public surfaces changed.
- [ ] Updated `docs/ENFORCEMENT_MATRIX.md` if verification commands changed.

