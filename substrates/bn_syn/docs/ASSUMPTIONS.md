# Assumptions

- Determinism assumptions rely on explicit seed inputs in CLI and test paths (`src/bnsyn/cli.py`, `tests/test_determinism.py`).
- SSOT order follows user contract: `specs/**` → `schemas/**` → `claims/**` → `src/**` → `scripts/**` → `docs/**`.
- Existing coverage threshold is inherited from baseline artifacts, not newly introduced.
- MISSING: explicit semver governance policy tied to release process.
  - DERIVE FROM: `CHANGELOG.md`, release workflow contracts.
  - ACTION: define semver authority in `docs/VERSIONING.md` and link in release checklist.
