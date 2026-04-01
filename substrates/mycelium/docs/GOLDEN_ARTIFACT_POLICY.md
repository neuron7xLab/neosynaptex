# Golden Artifact Policy

## What are golden artifacts?

Golden artifacts are SHA256 hashes of simulation outputs under a fixed
`DeterminismSpec`. They serve as the ultimate regression gate: if a code
change alters a golden hash, it MUST be intentional and documented.

## Current profiles

| Profile | Seed | Label | Field Hash |
|---------|------|-------|------------|
| baseline | 42 | nominal | `c36b8404d9280844` |
| gabaa_tonic | 131 | nominal | `54289613d556cff7` |
| serotonergic | 91 | watch | `c77dbc41b0c93b39` |
| balanced_criticality | 113 | nominal | `c36b8404d9280844` |

## Determinism contour

Hashes are valid ONLY under:
- OS: Linux
- Python: 3.12.x
- NumPy: 2.x
- BLAS: OpenBLAS
- dtype: float64
- Backend: cpu_numpy
- Threads: 1

See `src/mycelium_fractal_net/core/determinism.py` for `CANONICAL_SPEC`.

## Update protocol

1. **Never regenerate hashes silently.** Every hash change requires:
   - A commit message explaining WHY the hashes changed
   - Before/after comparison in the PR description
   - Review by the project lead

2. **Regeneration command:**
   ```bash
   python scripts/regenerate_golden_hashes.py
   ```

3. **CI gate:** `tests/test_golden_hashes.py` blocks merge on unexpected
   hash changes. This is a HARD gate — no exceptions.

4. **Acceptable reasons for hash changes:**
   - Bug fix in simulation numerics
   - Intentional algorithm improvement
   - NumPy/BLAS version upgrade (documented in release notes)

5. **Unacceptable reasons:**
   - "I don't know why it changed"
   - Refactoring that shouldn't affect numerics
   - Adding features to unrelated modules

## File locations

- `tests/golden_hashes.json` — active hashes (used by pytest)
- `artifacts/golden/golden_manifest.json` — full manifest with metadata
- `tests/test_golden_hashes.py` — CI gate
- `tests/test_golden_regression.py` — numerical regression (approx)
