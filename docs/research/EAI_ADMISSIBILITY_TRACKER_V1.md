# EAI Admissibility Tracker v1

## Purpose

Cumulate the γ-ledger bridge measurements over time. The bridge
(see `docs/research/EAI_GAMMA_LEDGER_BRIDGE_V1.md`) produces a single
admissibility snapshot per run. This tracker records each snapshot
as a row in
`artifacts/eai/benchmarks/gamma_ledger_admissibility_history.jsonl`
and **fails CI** when the new measurement regresses below the most
recent committed one.

The tracker answers:

> *Did this PR or push raise, lower, or preserve the project's
> EAI admissibility rate on the γ-ledger?*

## Regression policy

Two failure modes are caught:

1. **Determinism drift** — same `ledger_sha256` AND same
   `bridge_module_sha256` as a prior row, but a different
   `admissibility_rate`. Indicates the bridge stopped being
   deterministic. CI must block.
2. **Rate regression** — different inputs, but
   `admissibility_rate < prior_rate`. Indicates the gate became
   *less* strict (false-promotion danger) or a ledger entry
   slipped below threshold without compensating improvements
   elsewhere.

Improvements (`admissibility_rate >=` prior) are permitted and
silently logged.

## History schema (`EAI-GAMMA-ADMISSIBILITY-HISTORY-v1`)

Each line of the JSONL file is one row:

```jsonc
{
  "schema_version": "EAI-GAMMA-ADMISSIBILITY-HISTORY-v1",
  "recorded_at": "2026-05-13T16:45:05+00:00",
  "ledger_path": "evidence/gamma_ledger.json",
  "ledger_version": "2.0.0",
  "ledger_sha256": "3f2ed37e…",
  "bridge_module_sha256": "41df9787…",
  "total_entries": 10,
  "gate_verdict_counts": {"EVIDENCE": 2, "KILLED": 4, "QUARANTINED": 4},
  "hash_bound_count": 3,
  "candidate_total": 7,
  "admissible_evidence": 2,
  "admissibility_rate": 0.285714
}
```

`recorded_at` is wall-clock UTC; it is the only non-deterministic
field. `compute_history_digest` in
`tools/eai/track_admissibility.py` produces a stable digest over
all rows excluding `recorded_at`, suitable for audit checksums.

## Exact commands

```bash
# Append a new row + fail on regression (CI use)
PYTHONPATH=. python tools/eai/track_admissibility.py \
  --ledger evidence/gamma_ledger.json \
  --history artifacts/eai/benchmarks/gamma_ledger_admissibility_history.jsonl \
  --check-regression

# Append a new row, no regression check (forensic only)
PYTHONPATH=. python tools/eai/track_admissibility.py
```

## Exit codes

| code | meaning |
|---|---|
| 0 | row appended, no regression |
| 1 | error (malformed history file) |
| 2 | regression detected; row still appended for audit; CI blocks |

## Claim boundary

> The EAI admissibility tracker v1 records longitudinal admissibility
> measurements of the γ-ledger under the EAI gate.

**Forbidden phrasings**:

- "Tracker proves γ admissibility"
- "Tracker validates the gate's correctness"
- "Tracker measures intelligence over time"
- "Rising admissibility means the science is improving"
- "Falling admissibility means the science is degrading"

The tracker measures a relation between the ledger and the gate at
a point in time; the rate's movement reflects engineering changes
on either side, not changes in the underlying scientific reality.
