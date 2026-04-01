# BN‑Syn Constitutional Audit Report (Evidence-First)

This document defines the **constitutional constraints** for the BN‑Syn specification:
- Quantitative claims in **normative** sections are allowed only if they are proven by Tier‑A SSOT sources.
- Anything else is downgraded to NON‑NORMATIVE examples or removed.

Inventory of governed paths: see `docs/INVENTORY.md`.

## Normative labeling convention
Use explicit tags:
- **NORMATIVE** — for correctness, reproducibility, or safety gates
- **NON‑NORMATIVE** — illustrative, optional, or example-only

## Claim binding
Every **NORMATIVE** quantitative claim includes a `CLM-0001`-style identifier, e.g.:
> [NORMATIVE][CLM-0003] NMDA Mg²⁺ block uses canonical coefficients ...

The authoritative claim record lives in `claims/claims.yml`.

## Criticality: proxy vs measurement
- Runtime control uses a **σ proxy** (fast, biased, for control).
- Offline validation uses MR estimator + power-law fitting + model comparison.

See: `docs/CRITICALITY_CONTROL_VS_MEASUREMENT.md`.
