# CI Permissions & Supply-Chain Policy

Every workflow must follow least-privilege and supply-chain hardening rules:
- **Explicit permissions** at the top level (no implicit defaults).
- **Pinned actions**: all `uses:` references must point to immutable commit SHAs (no `@v1`, `@main`, etc.).
- **Triggers**: `pull_request_target` is blocked unless explicitly justified (not allowed in this repo).
- **Filesystem safety**: no `chmod`/`chown` on `/__w` or runner temp directories.

Enforced by `scripts/ci_policy_check.py`, which runs in CI and fails on violations.

**Local run**
```bash
python scripts/ci_policy_check.py
```
