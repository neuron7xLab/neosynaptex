"""Causal graph topology comparison — BN-Syn × GeoSync.

DCVP closed cross-substrate γ propagation; Spectral v3 closed shared
temporal frequency. This experiment opens a third question: when two
substrates are simultaneously in the METASTABLE regime (γ ≈ 1.0), is
the topology of their INTERNAL causal graphs isomorphic?

Pipeline:
    1. Acquire per-tick state dictionaries for each substrate
    2. Build a directed Granger-causality graph between state variables
       over a rolling window
    3. Compute three graph-distance metrics (edit / degree / spectral)
    4. Split observations by regime (both metastable vs else)
    5. Mann-Whitney U test on the conditional distance distributions
    6. Permutation-shuffle null to guard against alignment artifacts
    7. Verdict TOPOLOGY_CONVERGENCE / TOPOLOGY_INDEPENDENT

RULE ZERO: γ is derived from (topo, cost) pairs, never assigned; the
regime label is read downstream from that γ series.
"""
