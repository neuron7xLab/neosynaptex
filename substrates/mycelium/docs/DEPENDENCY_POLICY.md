# Dependency Policy

## Criteria for Adding Dependencies

A new dependency is accepted only if:

1. **Necessity** — No reasonable way to implement the required functionality without it.
2. **Maintenance** — Actively maintained, >1000 GitHub stars or institutional backing.
3. **License** — Compatible with MIT (no GPL, AGPL, or copyleft).
4. **Size** — Does not significantly increase install footprint for the default profile.
5. **Security** — No known unpatched CVEs at time of addition.

## Dependency Tiers

| Tier | Profile | Purpose | Examples |
|------|---------|---------|----------|
| **Core** | `pip install .` | Minimum for all operations | numpy, pydantic, fastapi, cryptography |
| **Dev** | `pip install .[dev]` | Development and testing | pytest, ruff, mypy, hypothesis |
| **ML** | `pip install .[ml]` | Neural network surfaces | torch |
| **Accel** | `pip install .[accel]` | JIT acceleration | numba |
| **Security** | `pip install .[security]` | Security scanning | bandit, pip-audit, checkov |

## Version Constraints

- **Lower bound**: Always specify minimum version (`>=X.Y`).
- **Upper bound**: Specify for dependencies with known breaking patterns (`<X+1.0`).
- **Pin**: Never pin exact versions in `pyproject.toml` — use `uv.lock` for reproducibility.

## Audit

- `pip-audit` runs in CI on every push to `main` and weekly.
- `uv lock --check` verifies lockfile consistency.
- SBOM generated for every release via `scripts/generate_sbom.py`.

## Current Dependencies

### Core (11)

| Package | Constraint | Rationale |
|---------|-----------|-----------|
| numpy | >=1.24 | Array computation, Laplacian, field operations |
| sympy | >=1.12 | Symbolic computation for Nernst equation |
| pydantic | >=2.0 | Request/response validation for API |
| fastapi | >=0.100.0 | REST API framework |
| pandas | >=1.5.3,<3.0.0 | DataFrame operations for feature export |
| pyarrow | >=10.0.0 | Parquet I/O for datasets |
| prometheus_client | >=0.17.0 | API metrics collection |
| cryptography | >=44.0.0 | Ed25519 artifact signing |
| websockets | >=12.0 | WebSocket adapter (frozen surface) |
| httpx | >=0.24.0 | HTTP client for health checks |
