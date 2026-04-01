# ADR-0010: Core Dependency Minimization

## Status
Proposed

## Context
Core `dependencies` includes `fastapi`, `websockets`, `pandas`, `pyarrow`, `prometheus_client`, `httpx`. For the simulation/detection pipeline (`mfn.simulate()` + `mfn.detect()`), none of these are needed. This inflates install size and attack surface for users who only need the computation engine.

## Decision (Proposed)
Move transport/data deps to optional extras in v5.0:
- Core: `numpy`, `sympy`, `pydantic`, `cryptography`
- `[api]`: fastapi, uvicorn, httpx
- `[data]`: pandas, pyarrow
- `[metrics]`: prometheus_client
- `[ws]`: websockets

## Consequences
- Breaking change for `pip install mycelium-fractal-net` users who use API.
- Requires conditional imports in api.py, integration/, metrics.
- Significant testing matrix expansion.
- Deferred to v5.0 due to scope.

## Non-Goals
- Not reducing numpy/pydantic (these are essential for core).
