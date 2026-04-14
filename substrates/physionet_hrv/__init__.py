"""PhysioNet HRV substrate — γ-measurement on free public cardiac data.

Substrate class: ``physiological_cardiac``. Fetches RR-interval
records from PhysioNet's Normal Sinus Rhythm RR Interval Database
(NSR2DB) via the ``wfdb`` package, no auth, fully public.

This is the FIRST non-market γ-replication in the γ-program.
Combined with the FRED + BTCUSDT pilots, brings the cross-substrate
matrix to three substrate classes:
- market_macro (FRED INDPRO)
- market_microstructure (BTCUSDT hourly)
- physiological_cardiac (PhysioNet NSR2DB) ← THIS PR

Per ``docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`` entry hrv_physionet,
the canonical method is Welch PSD on RR-intervals at the
very-low-frequency band (0.003-0.04 Hz), with DFA α as
cross-validation. This package implements both.

Caveats:
* PhysioNet NSR2DB subjects are HEALTHY adults — does not represent
  pathological cardiac dynamics. γ on this substrate addresses
  baseline / resting-regime cardiac scaling only.
* RR-intervals are NOT uniformly sampled in time. Standard practice
  (Task Force of ESC/NASPE 1996) is to interpolate onto a uniform
  4 Hz grid before Welch PSD. This package does that.
"""
