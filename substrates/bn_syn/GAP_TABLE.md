# GAP TABLE — CI_BATTLE_USAGE_AUDIT_2026-02-07

| gap_id | description | risk | blocking |
|---|---|---|---|
| GAP-001 | Local gate failure: `ruff format --check .` was non-zero in prior audit evidence. | CI/local determinism mismatch; merge risk. | no (closed) |
| GAP-002 | Local gate failure: `mypy src --strict --config-file pyproject.toml` was non-zero in prior audit evidence. | Type-safety gate not reproducible locally. | no (closed) |
| GAP-003 | Snapshot source provenance was ambiguous (`/mnt/data/...zip` vs workspace checkout). | Audit-trace ambiguity. | no (reframed optional; source recorded explicitly) |
| GAP-004 | Battle usage verdict was `NOT_PROVEN` without permanent anti-overclaim guard. | External readiness ambiguity; governance risk. | no (closed) |
| GAP-005 | No PR-specific fresh CI run URL captured for current branch revision. | Cannot prove branch-level CI convergence from immutable run artifact. | no (closed) |
