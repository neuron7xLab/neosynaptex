# ADR-0012: Spectral Modularity for Connectivity Analysis

## Status
Accepted

## Context
Connectivity features used proxy metrics: `modularity_proxy` = mean absolute diff of row/col strengths. This is not a standard graph connectivity metric. For a project targeting computational neuroscience, at least one graph-theoretic metric is expected.

## Decision
Add Newman spectral modularity (2006) via leading eigenvector of the modularity matrix. Use compact adjacency (only active cells), power iteration for eigendecomposition. Budget: ≤50ms for 64×64 grids. Falls back to proxy for grids >64×64.

## Consequences
- `modularity_spectral` added alongside existing `modularity_proxy`.
- No existing metric removed — backward compatible.
- O(k²) where k = number of active cells (typically 30-60% of grid).
- For 32×32: ~5ms. For 64×64: ~40ms. Acceptable within budget.

## References
- Newman (2006) PNAS 103:8577-8582, doi:10.1073/pnas.0601602103
