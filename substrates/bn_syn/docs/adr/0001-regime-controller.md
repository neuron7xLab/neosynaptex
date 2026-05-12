# ADR 0001: Regime Controller as online control primitive
Status: Accepted
Date: 2026-05-05

Decision: keep gamma-monitor -> gate -> adaptive-update as explicit bounded control loop with invariant-bound tests and release gate.

Consequences:
- deterministic auditable behavior,
- explicit fallback visibility,
- tighter release governance.
