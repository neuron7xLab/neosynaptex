# ADR 0002: Architecture boundaries

- Status: Accepted
- Layers: `core` (domain), `pipelines` (application), `integration` (adapters), `cli/api` (interfaces), `types` (contracts).
- Boundaries are enforced by import-linter and tests.
