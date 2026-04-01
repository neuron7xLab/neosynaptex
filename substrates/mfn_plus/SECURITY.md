# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 4.1.x   | :white_check_mark: |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in MyceliumFractalNet, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email: **security@example.com** with the subject line `[MFN-SECURITY] <brief description>`
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgement**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix timeline**: Depends on severity
  - Critical: Patch release within 72 hours
  - High: Patch release within 2 weeks
  - Medium/Low: Next scheduled release

### Scope

The following are in scope:

- `src/mycelium_fractal_net/` — all production code
- `src/mycelium_fractal_net/security/` — input validation, encryption, hardening
- `src/mycelium_fractal_net/crypto/` — artifact signing
- API endpoints exposed via `mfn-api`
- CLI argument handling via `mfn`
- Dependencies listed in `pyproject.toml`

### Security Measures in Place

- **Input validation**: SQL injection, XSS, and path traversal patterns blocked (`security/input_validation.py`)
- **Artifact signing**: Ed25519 deterministic signatures for release artifacts
- **Secret scanning**: Gitleaks configured (`.gitleaks.toml`)
- **Dependency auditing**: `pip-audit` in CI pipeline
- **Static analysis**: Bandit security linter in CI and pre-commit
- **Import boundaries**: 8 enforced contracts prevent privilege escalation across module layers

### Cryptography

This project uses `cryptography>=44.0.0` for Ed25519 signing. The `crypto/` module is frozen and scheduled for removal in v5.0 — all signing goes through `artifact_bundle.py`.

## Acknowledgements

We thank security researchers who responsibly disclose vulnerabilities. Contributors will be credited in release notes (unless they prefer anonymity).
