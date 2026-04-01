# Evidence Snapshots

Evidence is a repository-level contract. Snapshots live under:

```
artifacts/evidence/YYYY-MM-DD/<short_sha>/
```

## Evidence Contract (v1)

- **Manifest**: `manifest.json` with `schema_version="evidence-v1"`, `git_sha`, `short_sha`,
  `created_utc`, `source_ref`, `commands`, `outputs`, `status`, and `file_index`.
- **Required files** (relative to the snapshot directory):
  - `manifest.json`
  - `coverage/coverage.xml`
  - `pytest/junit.xml`
- **Optional**:
  - `logs/*.log`
  - `benchmarks/*`
  - `env/python_version.txt`, `env/uv_lock_sha256.txt`
- **Outputs mapping**: `coverage_xml` → `coverage/coverage.xml`, `junit_xml` → `pytest/junit.xml`.
- **Status**: `{ok: bool, partial: bool, failures: [...]}` — partial is allowed when tests fail but evidence exists.
- **File index**: every file except `manifest.json` must appear in `file_index` with `{path, sha256, bytes, mime_guess}`.

### Invariants

1. All manifest paths are relative and resolve **inside** the snapshot directory (no path traversal).
2. Size bounds: single file ≤ 2 MB; total snapshot ≤ 5 MB.
3. Secret guard: reject `PRIVATE KEY`, AWS keys, GitHub tokens, and `Authorization: Bearer` patterns.
4. Deterministic assembly: `capture_evidence.py --mode pack` never re-runs tests; it packages provided outputs.
5. Integrity: verifier recomputes sha256/size for every indexed file.

## Tooling

- Capture (local build): `python scripts/evidence/capture_evidence.py --mode build`
- Capture (CI pack): `python scripts/evidence/capture_evidence.py --mode pack --inputs <paths.json>`
- Verify: `python scripts/evidence/verify_evidence_snapshot.py --evidence-dir artifacts/evidence/<date>/<sha>/`

Snapshots are immutable once committed. Do not overwrite prior dates; add a new dated folder instead.
