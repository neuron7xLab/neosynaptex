# `evidence/levin_bridge/`

Evidence directory for the Levin → Neosynaptex Integration Protocol.

**Canonical spec:** `docs/protocols/levin_bridge_protocol.md`

## Files

| File | Role | Required before first measurement? |
|---|---|---|
| `hypotheses.yaml` | Pre-registered predictions (Step 5) | Yes |
| `controls.yaml` | Adversarial control families (Step 6) | Yes |
| `cross_substrate_horizon_metrics.csv` | Per-run row-level metrics (Step 8) | Yes — header-only at scaffold |
| `horizon_knobs.md` | Per-substrate definition of the H-intervention (Step 3) | Yes — to be added before any run |
| `LEVIN_BRIDGE_VERDICT.md` | Outcome document (Step 9–10) | No — emitted after analysis |
| `replications/` | External or internal replications | No — populated over time |

## Rules of engagement

1. No commit that writes a row into `cross_substrate_horizon_metrics.csv` may be merged unless the run's `commit_sha` pre-registers the adapter code at or before the measurement tick, following the existing pattern in `evidence/PREREG.md`.
2. Rows are append-only. Corrections append a new row with a status column in a follow-up schema bump, never rewrite history.
3. Any document outside this directory that cites a γ-vs-horizon result MUST reference either the commit SHA of the row in this CSV or the verdict file.
