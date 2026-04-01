## Summary
This PR adds an audit-only usability blocker analysis package for the repository. It introduces no runtime or product logic changes.

## Added artifacts
- `reports/usability_blockers_report.md`
- `reports/usability_blockers.json`
- `reports/repo_representator.json`
- `proof_bundle/toolchain_fingerprint.json`
- `proof_bundle/index.json`
- command logs under `proof_bundle/logs/`
- `proof_bundle/hashes/sha256sums.txt`

## Key findings
- P0: Canonical test command fails due to stale proof bundle hash index entry.
- P0: Canonical build command unavailable after documented dev setup (`python -m build` missing module until extra install).

## Evidence
All executed commands are logged under `proof_bundle/logs/` with timestamp, command, exit code, stdout, stderr.
