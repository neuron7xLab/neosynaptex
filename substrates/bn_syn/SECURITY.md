# Security

This repository is a research-grade simulator. Do not deploy it as a security boundary.

We do not claim this project is "secure". We claim only that defined security gates can pass with evidence.

## Supported Versions

- **Best effort support:** only the current default branch and most recent tagged release receive security fixes.
- Older snapshots may remain vulnerable and should be upgraded.

## Reporting a Vulnerability

Please open a private report using GitHub Security Advisories for this repository.

When reporting, include:
- affected file(s) and commit SHA,
- reproduction steps,
- expected vs observed behavior,
- impact/severity estimate.

Do **not** include live secrets in issue text, PR text, or logs.

## Security Reproducibility Assumptions

The security gate is designed to run without repository secrets.

- Python dependencies are installed deterministically from `requirements-lock.txt` using hashes.
- Secret scanning uses pinned `gitleaks` via `scripts/ensure_gitleaks.py` and `.gitleaks.toml`.
- Dependency vulnerability audit uses `pip-audit` JSON output.
- Baseline SAST uses Bandit JSON output.
- SBOM generation uses CycloneDX JSON output, with `cyclonedx-bom` installed from `requirements-sbom-lock.txt` via hash-locked install.

## Canonical Local Commands

```bash
make security
make sbom
```

Expected artifacts:
- `artifacts/security/gitleaks-report.json`
- `artifacts/security/pip-audit.json`
- `artifacts/security/bandit.json`
- `artifacts/sbom/sbom.cdx.json`

## Secret Response (If Any Secret Is Found)

1. Revoke/rotate the credential immediately in the upstream provider.
2. Remove the secret from the repository state and history if necessary.
3. Add a narrowly scoped detection/prevention rule to prevent recurrence.
4. Document rotation and cleanup steps in the incident follow-up (without exposing the secret value).
