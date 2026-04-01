# ADR-0014: OpenAPI Schema Authority

## Status: Accepted

## Context

Two OpenAPI schema files exist:
- `docs/contracts/openapi.v1.json` — original v1 schema (575 lines)
- `docs/contracts/openapi.v2.json` — extended v2 schema (752 lines)

Both describe the same `/v1/*` endpoints. v2 adds richer response schemas
and WebSocket definitions. Previously v2 carried `"version": "openapi-v2"`
instead of a proper semver, creating ambiguity about which was authoritative.

## Decision

- **`openapi.v2.json` is the authoritative contract** for all API consumers.
- `openapi.v1.json` is retained as a compatibility reference (read-only).
- Both files MUST carry the same version string as `pyproject.toml`.
- `scripts/check_contract_version_sync.py` enforces this in CI.

## Consequences

- API client generators SHOULD use `openapi.v2.json`.
- Any schema changes MUST be applied to v2 first; v1 is updated only for
  backward-compatible subset changes.
- Version sync is enforced by CI — no manual drift possible.
