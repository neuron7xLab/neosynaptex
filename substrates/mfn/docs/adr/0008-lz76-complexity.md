# ADR-0008: Replace Naive Substring Count with LZ76 Complexity

## Status
Accepted

## Context
`temporal_lzc` was computed as `len(unique_substrings) / len(bits)` — counting unique substrings up to length 5. This is not Lempel-Ziv complexity. LZ76 uses sequential left-to-right parsing to count new patterns, which is fundamentally different for quasi-periodic signals (typical in Turing morphogenesis).

## Decision
Implement LZ76 (Lempel & Ziv 1976, Kaspar & Schuster 1987) with normalization by `n / log2(n)` for cross-length comparability. The function `_lempel_ziv_76_complexity()` lives in `analytics/morphology.py`.

## Consequences
- `temporal_lzc` values change — golden regression tests need updating.
- More accurate complexity measurement for reaction-diffusion dynamics.
- O(n²) worst case but n is typically < 100 (number of simulation steps).

## References
- Lempel & Ziv (1976) IEEE Trans Inform Theory IT-22:75-81
- Kaspar & Schuster (1987) Phys Rev A 36:842-848
