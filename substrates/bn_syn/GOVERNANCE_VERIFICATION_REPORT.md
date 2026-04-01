# BN-SYN GOVERNANCE VERIFICATION REPORT (TEMPLATE)

This file is a **template** only. Do **not** commit filled results or PASS/FAIL claims.
Generate verification evidence in CI artifacts or in the PR description instead.

---

## Metadata (fill in when generating a report)

- **Date**:
- **PR / Commit**:
- **Executor**:

## Verification Commands

Record the exact commands executed and their outputs (attach logs/artifacts):

```bash
# Example (replace with actual commands run)
pytest -q tests/test_tla_invariants_guard.py tests/test_vcg_invariants_guard.py
make test
```

## Evidence Links

- CI run URL / artifact links:
- Logs (paths or URLs):

## Notes / Limitations

- Known limitations observed during the run:
- Deviations from expected behavior:

---

## Directory Completion Notes (Non-Executable)

This report records structural completeness changes without claiming test results:

- API Sphinx static assets contract and manifest tooling: `docs/api/_static/README.md`,
  `docs/api/_static/manifest.json`, `docs/api/_static/tools/update_manifest.py`.
- API Sphinx template overrides contract and manifest tooling: `docs/api/_templates/README.md`,
  `docs/api/_templates/manifest.json`, `docs/api/_templates/tools/update_manifest.py`.

**Policy**: This repository must not contain evergreen certification claims.
