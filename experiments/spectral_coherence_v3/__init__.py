"""Spectral Law Validation v3 — BN-Syn × GeoSync γ.

Strict-order pipeline:
    Phase 1  physical audit (characteristic timescales, not γ)
    Phase 2  adapter fixes (no repetition, burn-in, raw export)
    Phase 3  long-run acquisition (burn_in=300 + logged=2000)
    Phase 4  spectral battery (Welch + DPSS multi-taper + Morlet wavelet)
    Phase 5  null ensemble (5 families × 1000 surrogates per estimator)
    Phase 6  stability tests (frequency / estimator / segment)
    Phase 7  verdict logic
    Phase 8  result.json + artifacts
    Phase 9  ten tests enforcing every guarantee

RULE ZERO — γ is always derived, never assigned, never smoothed before
primary analysis; no modulo-cycling, no silent padding, no hidden
interpolation before raw export; every positive verdict requires
physical interpretability.
"""
