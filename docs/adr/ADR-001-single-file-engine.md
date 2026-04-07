# ADR-001 — Single-file engine (`neosynaptex.py`)

**Status:** Accepted

---

## Context

The NeoSynaptex integrating mirror layer needs to be importable by any
substrate adapter with a single import and zero configuration. The system
integrates at most four domain adapters simultaneously (Invariant MAX_DOMAINS),
each providing a simple five-method protocol.

The codebase already has a `core/` package for reusable math (gamma
regression, bootstrap, axioms). The question was whether the top-level
integration logic should live in a package (`neosynaptex/`) or in a single
module (`neosynaptex.py`).

---

## Decision

The engine is implemented as a single file: **`neosynaptex.py`** in the
repository root.

All public API — `Neosynaptex`, `NeosynaptexState`, `DomainAdapter`,
mock adapters — lives in this one file. Internal helpers (circular buffer,
Jacobian, gamma, Granger) are private functions or classes within the same
file.

---

## Consequences

**Positive:**

- One-line integration: `from neosynaptex import Neosynaptex, MockBnSynAdapter`
- No package installation required beyond `pip install -e .` — substrates can
  even copy the single file.
- The entire public surface is readable in one scroll; no module-hopping needed
  for code review or replication.
- `__all__` in the file is the authoritative public API contract.
- Simplifies Docker reproduction — `Dockerfile.reproduce` only needs the root.

**Negative / trade-offs:**

- The file grows large (~1 400 lines). Mitigated by clear section comments
  (`# --- Layer 1: Collect ---`, `# --- Constants ---`, etc.).
- Adding a new diagnostic requires editing the one large file rather than
  creating a new module. Accepted as a deliberate friction point: new
  diagnostics are expensive and must be justified.
- Cannot import subsets of the engine. Full import cost is paid on every use.

---

## Alternatives considered

| Option | Rejected because |
|--------|-----------------|
| `neosynaptex/` package with submodules | Adds import complexity; no real benefit at current scale |
| `core/neosynaptex.py` inside the core package | Circular dependency risk with substrates importing `core`; breaks single-import goal |
| Split into `engine.py` + `adapters.py` + `state.py` | Arbitrary split; increases navigation cost for reviewers |
