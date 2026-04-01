# CI/CD Overview

This repository uses multiple focused workflows to keep security and correctness fully automated.

## Workflows

- **python-tests.yml** — runs `python -m pytest -q` on Python 3.10, 3.11, 3.12 for every push to `main` and all pull requests.
- **gitleaks.yml / security-secrets.yml** — secrets scanning on every push/PR.
- **security-unicode.yml** — Trojan Source prevention via `scripts/unicode_scan.py`.
- **security-validate-configs.yml / validate-configs.yml** — YAML/JSON validation.
- **security-ci-policy.yml** — enforces workflow pinning and policy checks.
- **security-actionlint.yml / actionlint.yml** — validates GitHub Actions syntax.
- **security-deps.yml / dependency-audit.yml** — dependency review and SBOM audit.
- **docs-link-check.yml** — validates documentation links.
- **phase-validation.yml** — ensures PR metadata matches the evolution plan.

All workflows trigger on pull requests; security suites also run on pushes to `main`.

## Local Reproduction

```bash
pip install -r requirements-dev.txt

# Security gates
gitleaks detect --config .gitleaks.toml --report-format sarif --report-path gitleaks.sarif
python scripts/unicode_scan.py
python scripts/validate_configs.py .
python scripts/ci_policy_check.py
pip-audit -r requirements.txt && pip-audit -r requirements-dev.txt

# Lint/format (PEP8)
pre-commit install
pre-commit run --all-files

# Tests
python -m pytest -q
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Deployment

- **Staging/preview:** run `bash deploy_to_github.sh` from a clean branch after all gates pass to publish artifacts to your fork for validation.
- **Production:** merge to `main` only after staging verification and passing CI. All workflow actions are pinned to SHAs for supply-chain safety.

## PR Checklist

- Link to the relevant roadmap issue (e.g., `Phase: X.Y` or `Closes #123`).
- Include `Verification:` with the exact commands executed (tests, audits, benchmarks).
- Attach CI run links or logs showing success for security gates, tests, and coverage.
