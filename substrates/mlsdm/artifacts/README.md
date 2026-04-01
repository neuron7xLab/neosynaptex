Artifacts policy
----------------
- Purpose: one-time baseline snapshot (lint/type/test + environment) captured on 2025-12-15 for reproducibility of PR #259.
- Retention: keep committed snapshot as-is; future baselines should go into a new dated folder (e.g., artifacts/baseline/YYYY-MM-DD) instead of overwriting.
- Scope: contains environment fingerprint, install logs, and lint/type/test logs; no secrets should be present.
- Usage: read-only evidence for CI archaeology; do not regenerate in-place.
