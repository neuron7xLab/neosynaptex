# Frozen Surfaces

**Updated:** 2026-03-27

These modules are **frozen** — maintained for backward compatibility but not
actively developed. They will be removed in v5.0 unless unfrozen.

Do not add features, fix style issues, or refactor these modules.

## Frozen modules (4,163 LOC = 8.3% of codebase)

| Module | LOC | Reason | Removal |
|--------|-----|--------|---------|
| `crypto/key_exchange.py` | 538 | Replaced by artifact_bundle | v5.0 |
| `crypto/signatures.py` | 613 | Replaced by artifact_bundle | v5.0 |
| `crypto/symmetric.py` | 528 | Replaced by artifact_bundle | v5.0 |
| `core/federated.py` | 464 | No active development | v5.0 |
| `core/stdp.py` | 422 | Requires torch, niche use | v5.0 |
| `core/turing.py` | 183 | Replaced by reaction_diffusion_engine | v5.0 |
| `core/reaction_diffusion_compat.py` | 143 | Thin wrapper, backward compat | v5.0 |
| `signal/denoise_1d.py` | 768 | Quarantined, tests skipped | v5.0 |
| `signal/preprocessor.py` | 193 | Orphan, never imported | v5.0 |
| `analytics/legacy_features.py` | 767 | Superseded by fractal_features.py | v5.0 |

## Policy

- **Do not import** frozen modules from active code
- **Do not fix** ruff/mypy issues in frozen modules
- **Do not test** frozen modules (quarantined)
- **Import-linter** should block active → frozen imports
- Frozen modules are excluded from `ruff check` and `mypy --strict`

## What happens in v5.0

All frozen modules will be:
1. Removed from source tree
2. Removed from `__init__.py` lazy attrs
3. Migration guide published for any external users
