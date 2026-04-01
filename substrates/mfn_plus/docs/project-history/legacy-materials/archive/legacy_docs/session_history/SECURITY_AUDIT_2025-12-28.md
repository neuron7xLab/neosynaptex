## Security Audit — 2025-12-28

### Commands executed
- `pip-audit -r requirements.txt --desc on --format json --no-deps --progress-spinner off > audit_report.json`
- `pip-audit -r requirements.txt --desc on --format json --no-deps --progress-spinner off > audit_dev_report.json` (dev extras live in the same requirements file)
- `pip-audit --desc on` (environment scan to surface concrete CVEs below)

### Findings
The requirements-based audits returned **no vulnerabilities** (exit code `0`); the JSON outputs show resolver-selected current versions for reference. A direct environment scan surfaced the following issues (13 total) with available fixes (versions below reflect the runner’s installed packages and therefore differ from the JSON reports):

| Package | Current Ver | CVE ID | Severity | Fixed In | Breaking? |
| --- | --- | --- | --- | --- | --- |
| certifi | 2023.11.17 | CVE-2024-39689 | High | 2024.7.4 | No (root CA removal only) |
| cryptography | 41.0.7 | CVE-2024-26130 | High | 42.0.4 | No |
| cryptography | 41.0.7 | CVE-2023-50782 | High | 42.0.0 | No |
| cryptography | 41.0.7 | CVE-2024-0727 | Medium | 42.0.2 | No |
| cryptography | 41.0.7 | GHSA-h4gh-qq45-vh27 | High | 43.0.1 | No (OpenSSL rebuild) |
| requests | 2.31.0 | CVE-2024-35195 | Medium | 2.32.0 | Low risk |
| requests | 2.31.0 | CVE-2024-47081 | High | 2.32.4 | No |
| setuptools | 68.1.2 | CVE-2025-47273 | High | 78.1.1 | Low (packaging internals) |
| setuptools | 68.1.2 | CVE-2024-6345 | High | 70.0.0 | Low |
| jinja2 | 3.1.2 | CVE-2024-56201 | High | 3.1.5 | Low (template strictness) |
| jinja2 | 3.1.2 | CVE-2024-56326 | High | 3.1.5 | Low |
| urllib3 | 2.0.7 | CVE-2024-37891 | Medium | 2.2.2 | No |
| urllib3 | 2.0.7 | CVE-2025-66471 | High | 2.6.0 | Low |

### Compatibility notes for ML stack
- Torch (>=2.0) with NumPy (>=1.24) and newer `cryptography`/`requests`/`urllib3` versions have no known ABI conflicts; upgrades are API-compatible for core training/inference paths.
- pandas (>=1.5.3) with pyarrow (>=10) remains compatible when upgrading to latest patch releases; serialization/feather/parquet interfaces are stable.
- FastAPI (>=0.109) with Pydantic v2.x remains compatible across security patch bumps.

### Recommendations
- Pin and upgrade the listed packages to at least the “Fixed In” versions above, then re-run `pip-audit` and `bandit`.
- Add hash-pinned lock generation (e.g., `pip-compile --generate-hashes`) to keep CI security-min reproducible.
- After updating, rerun `pytest -q`, `ruff check`, and `mypy` to confirm compatibility.
