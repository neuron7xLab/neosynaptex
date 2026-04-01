# Reproducibility Policy

## Guarantee

Given the same `SimulationSpec` (including `seed`), MFN produces **bit-exact** output
for `field`, `descriptor`, `detection`, and `forecast` across:

- Multiple runs on the same machine
- Different Python versions (3.10–3.13) on the same platform
- Different numpy versions (>=1.24) on the same platform

## Canonical Golden Hashes

| Profile | Field Hash | Descriptor Hash |
|---------|-----------|-----------------|
| baseline | `5fe822d89ae49eb9` | `be6ff3cd36a44f81` |
| gabaa_tonic | `de412a6243b4a2f6` | `a5d2f3db0dd7f55e` |
| serotonergic | `52aa7806e2ea9c43` | `cb58257a360d33ba` |
| balanced_criticality | `e0f579fbf0c056a4` | `4031821d7d45c854` |

## Cross-Platform Tolerance

Floating-point behavior may differ across CPU architectures (x86 vs ARM).
For cross-platform comparison, use **tolerance-based** comparison:

```python
np.testing.assert_allclose(field_a, field_b, atol=1e-10)
```

## Verification

```bash
python scripts/generate_reproducibility_matrix.py
```

Produces `artifacts/reproducibility_matrix.json` with per-profile hashes
and environment metadata.

## CI Enforcement

The `test_reproducibility_matrix.py` test verifies golden hashes in CI.
Any hash drift fails the build and requires:

1. Investigation of the root cause
2. Update of golden hashes via `scripts/generate_reproducibility_matrix.py`
3. Changelog entry explaining the drift
