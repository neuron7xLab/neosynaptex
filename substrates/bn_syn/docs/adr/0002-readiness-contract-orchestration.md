# ADR 0002: Execution-backed readiness orchestration

## Context / problem
The previous release-readiness flow could drift toward a file-presence checklist even when the user-facing contract required real command execution. That weakens trust in `python -m scripts.release_readiness`, creates ambiguity between docs and runtime state, and makes fail-closed behavior for malformed governance inputs harder to reason about.

## Decision
Keep `src/bnsyn/qa/readiness_contract.py` as the single readiness truth source and harden it around four principles:
- readiness remains execution-backed across static quality, canonical proof path, and bundle validation
- governance checks fail closed when mutation or entropy JSON inputs are unreadable or malformed
- command output stored in readiness reports is scrubbed before serialization to avoid leaking paths, tokens, or environment-style assignments
- docs are validated structurally through a lightweight markdown AST, not by loose substring search alone
- CI keeps lint/type/security gates blocking, exercises `tests/test_release_readiness.py` directly in the contracts lane, and enforces a truth-model fingerprint/version check through the regression suite

## Why this approach
- It preserves the repository's canonical proof path instead of introducing parallel readiness mechanisms.
- It improves auditability without expanding scope into new services or infrastructure.
- It keeps the CLI contract stable: `python -m scripts.release_readiness` remains the entrypoint while the internal report becomes more trustworthy.
- It avoids `sys.path` mutation in the CLI wrapper and relies on the installed package/runtime environment expected by CI and normal project usage.

## Compatibility impact
- CLI entrypoint and `--advisory` behavior remain unchanged.
- The report still exposes `release_ready`, while newer consumers should prefer `state`, `truth_model_version`, and per-subsystem results.
- Malformed governance inputs and abnormal subprocess terminations now produce deterministic blocking results instead of bubbling exceptions, which is an intentional fail-closed hardening.

## Follow-up / deferred work
- Containerized sandboxing, formal proofs, adversarial audit loops, and deeper chaos testing remain deferred because they exceed the scoped readiness hardening requested here.
