# Contributing to MyceliumFractalNet

Thank you for your interest in contributing. This document describes the development workflow, code standards, and review process.

## Development Setup

```bash
git clone https://github.com/neuron7x/mycelium-fractal-net.git
cd mycelium-fractal-net
make bootstrap          # Install uv, sync dependencies, run health check
make fullcheck          # Verify everything passes before you start
```

### Prerequisites

- Python ≥ 3.10, < 3.14
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

## Workflow

### 1. Create a branch

```bash
git checkout -b feat/your-feature-name
```

Branch naming conventions:
- `feat/` — new functionality
- `fix/` — bug fix
- `refactor/` — code restructuring without behavior change
- `docs/` — documentation only
- `perf/` — performance improvement
- `test/` — test additions or fixes

### 2. Make changes

Follow the [Code Standards](#code-standards) below. Run quality checks frequently:

```bash
make lint          # Ruff lint + format check
make typecheck     # mypy strict on types/ and security/
make test          # Full test suite
```

### 3. Verify before pushing

```bash
make fullcheck     # lint + typecheck + test + verify + security
```

All 7 import contracts must pass. Coverage must stay ≥ 80%.

### 4. Open a pull request

- Keep the title under 70 characters.
- Reference relevant issues.
- Describe **what** changed and **why**.
- Include test evidence for behavioral changes.

### 5. Review process

- All CI jobs must pass (lint, typecheck, test matrix, coverage, security, import contracts).
- At least one maintainer approval required.
- Causal validation rules must not regress (44 rules, 0 errors).

## Code Standards

### Architecture constraints

The project follows a strict layered architecture enforced by import-linter:

```
types/  →  core/  →  pipelines/  →  integration/  →  cli.py / api.py
```

**Rules (enforced by CI):**
1. Core must not import interfaces or adapters.
2. Pipelines must not import CLI/API transport.
3. CLI/API must not import crypto directly.
4. Numerics compat layer must not own simulation logic.
5. Types must not import core operations.
6. Analytics must not depend on integration.
7. Security must not depend on domain logic.

See `.importlinter` for the full contract definitions.

### Python style

- **Formatter:** Ruff (line length 100).
- **Linter:** Ruff with 24 rule categories — see `pyproject.toml [tool.ruff.lint]`.
- **Type hints:** Required on all public functions. `from __future__ import annotations` in every module.
- **Dataclasses:** Use `@dataclass(frozen=True)` for domain types. Mutable state is exceptional.
- **No `print()` in production code.** Use `logging.getLogger(__name__)` for diagnostics, `sys.stdout.write()` for CLI output formatters.
- **No `assert` in production code.** Use explicit `if not condition: raise ValueError(...)`.
- **No magic numbers.** Named constants with documented thresholds.

### Testing

- Tests live in `tests/` mirroring the source layout.
- Use `pytest` with `--strict-markers`.
- Mark slow tests with `@pytest.mark.slow`.
- Mark integration tests with `@pytest.mark.integration`.
- Hypothesis property-based testing encouraged for numerical code.
- Golden regression tests: if you change detection or forecasting behavior, update the expected values explicitly.

### Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `perf:`, `ci:`, `chore:`.
- Keep commits atomic — one logical change per commit.
- Write commit messages that explain **why**, not just **what**.

### Documentation

- Update `CHANGELOG.md` for user-visible changes (Keep a Changelog format).
- Update `docs/` if you change architecture, API, or causal rules.
- ADRs (`docs/adr/`) for significant architectural decisions.

## Adding a Causal Rule

Causal rules live in `src/mycelium_fractal_net/core/causal_validation.py`:

```python
@rule(
    id="SIM-011",
    claim="Your scientific claim",
    math="Mathematical formulation",
    ref="Paper reference, doi:...",
    stage="simulate",
    severity="error",
    category="numerical",
    rationale="Why this matters",
    falsifiable_by="How to disprove this",
)
def sim_011_your_rule(sequence):
    observed = compute_something(sequence)
    expected = THRESHOLD
    return observed <= expected, observed, expected
```

**Requirements for new rules:**
1. Must have a falsifiable scientific claim.
2. Must include `math` or `ref` field (preferably both).
3. Must include `rationale` explaining why violation matters.
4. Must have a corresponding test in `tests/test_causal_invariants.py`.
5. Must update `docs/CAUSAL_VALIDATION.md` rule catalog.
6. Must update `configs/causal_validation_v1.json` if the rule affects release criteria.

## Release Process

1. All CI jobs green on `main`.
2. `make fullcheck` passes locally.
3. `make validate` — scientific validation experiments pass.
4. `make benchmark` — no performance regressions.
5. Update `CHANGELOG.md` with release date.
6. Tag: `git tag -a v4.x.y -m "Release v4.x.y"`.
7. `make sbom` — generate SBOM and sign artifacts.
8. Push tag and create GitHub Release.

## Questions?

Open an issue on [GitHub](https://github.com/neuron7x/mycelium-fractal-net/issues).
