# API Stability

Stability labels used in `docs/PROJECT_SURFACES.md`:
- `stable`: compatibility expectation for downstream users.
- `experimental`: may change with notice.
- `internal`: no compatibility promise.

Package-level exported symbols from `src/bnsyn/__init__.py` are currently treated as `internal`, except CLI/schemas and canonical docs surfaced as `stable`.
