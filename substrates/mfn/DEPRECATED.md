# DEPRECATED — mfn_plus

**Status:** DEPRECATED as of 2026-04-01
**Surviving authority:** `substrates/mycelium/`
**Conflict:** B (see CANONICAL_OWNERSHIP.yaml)

This subtree is a diverged fork of `substrates/mycelium/`.
Both contain 279 source files and 223 test files with content differences.

## Migration plan
1. `substrates/mycelium/` retains canonical authority (newer modifications)
2. Any unique changes in `mfn_plus/` must be cherry-picked into `mycelium/` before deletion
3. Do NOT delete this directory until differential review is complete

## Differential files requiring review
Run: `diff -rq substrates/mfn_plus/src/ substrates/mycelium/src/`
