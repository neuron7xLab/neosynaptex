# ADR-0013: Torch Test Isolation Strategy

## Status
Accepted

## Context
24 test files use `pytest.importorskip("torch")`. Without `[ml]` extra, these 24 files are completely skipped. This includes `test_biophysics_core.py` and `test_math_model_validation.py` which genuinely use torch for tensor operations (22+ torch calls in biophysics alone).

## Decision
Keep `importorskip` pattern — it correctly skips ML tests on CPU-only installs.

The test suite is structured as:
- **Core tests (1700+)**: run without any optional deps
- **ML tests (24 files)**: gracefully skip via `importorskip("torch")`
- **Accel tests**: gracefully skip via `importorskip("numba")`

CI matrix enforces both paths:
- `unit` job: runs on Python 3.10-3.13 with `[dev]` only (core tests)
- Full validation: requires `[ml]` extra for complete biophysics coverage

## Consequences
- CPU-only CI always green (skips not failures)
- Full ML coverage requires explicit `uv sync --extra ml`
- `pytest --co -q | grep "no tests"` shows 0 collection errors
- 6 skipped tests in default run = torch-dependent tests correctly deferred

## Non-Goals
- Not moving torch tests to separate directory (24 files, high disruption)
- Not rewriting biophysics tests in pure numpy (torch ops are the point)
