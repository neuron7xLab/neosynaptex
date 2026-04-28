# Claim Surface Reconciliation Report — Phase 1 baseline

> **Verdict at PR head:** `NOT_RECONCILED` — 48 contradictions across the
> ledger, README, and BN-Syn surface.
>
> **Scope of this report:** Phase 1 only **detects** contradictions; it
> does not modify any claim surface. Phase 2 (Ledger Evidence Hardening)
> acts on the findings; Phase 3+ adds null screens, negative substrates,
> meta-analysis, and replication packs. See the canonical protocol for
> the full sequence.

The full machine-readable JSON and the always-regenerable markdown
listing are produced by:

```bash
python -m tools.audit.claim_surface_reconciliation \
    --report docs/audit/CLAIM_SURFACE_RECONCILIATION_REPORT.md \
    --json-out evidence/claim_surface_reconciliation.json
```

Re-running the tool overwrites this file with the current contradiction
set. The headline counts below are the **baseline at the merge of this
PR**; any drift from this baseline must be explained in a follow-up PR.

## Baseline contradiction tally (2026-04-28)

| Code                                              | Severity  | Count |
|---------------------------------------------------|-----------|-------|
| `VALIDATED_WITHOUT_RERUN_COMMAND`                 | HIGH      | 10    |
| `VALIDATED_WITHOUT_NULL_FAMILY_STATUS`            | HIGH      | 10    |
| `VALIDATED_WITHOUT_CLAIM_BOUNDARY_REF`            | HIGH      | 10    |
| `VALIDATED_WITHOUT_DATA_SHA256`                   | CRITICAL  | 9     |
| `VALIDATED_WITHOUT_ADAPTER_CODE_HASH`             | CRITICAL  | 7     |
| `README_VALIDATED_COUNT_INCONSISTENT_WITH_EMPTY_CORE` | HIGH  | 1     |
| `BNSYN_OVERCLAIM`                                 | CRITICAL  | 1     |
| **Total**                                         |           | **48**|

## Contradiction families

### 1. Ledger vs CLAIM_BOUNDARY §5.1 (44 violations)

`evidence/gamma_ledger.json` carries 10 entries with `status=VALIDATED`
(`zebrafish_wt`, `gray_scott`, `kuramoto`, `bnsyn`, `eeg_physionet`,
`hrv_physionet`, `eeg_resting`, `serotonergic_kuramoto`, `hrv_fantasia`,
`lemma_1_kuramoto_dense`). `docs/CLAIM_BOUNDARY.md §5.1` declares the
evidential core **empty** because no substrate has yet closed all six
§5.1 gates. Every VALIDATED entry therefore lacks at least one of:

- a real `data_source.sha256` (free-text pointers like `"see ..."` are
  not 64-hex sha256 strings);
- a real `adapter_code_hash`;
- a `null_family_status` field;
- a `rerun_command` field;
- a `claim_boundary_ref` field.

These are exposed as `VALIDATED_WITHOUT_*` violations. Phase 2
(Ledger Evidence Hardening) will either populate the missing fields
with concrete evidence or downgrade each entry to a status the existing
evidence supports (`LOCAL_STRUCTURAL_EVIDENCE_ONLY`,
`EVIDENCE_CANDIDATE`, `INCONCLUSIVE`).

### 2. BN-Syn overclaim (1 violation)

`evidence/gamma_ledger.json#entries.bnsyn` is `status=VALIDATED`, but
`docs/claim_boundaries/BN_SYN_LOCAL_STRUCTURAL_EVIDENCE.md` constrains
BN-Syn to `LOCAL_STRUCTURAL_EVIDENCE_ONLY` until an external NeoSynaptex
γ-pipeline supplies `gamma_pass=True`. The `κ ≠ γ` invariant
(`docs/architecture/recursive_claim_refinement.md` §5) explicitly forbids
projecting the BN-Syn local proxy onto the γ-claim surface.

Phase 2 must downgrade `bnsyn` to `LOCAL_STRUCTURAL_EVIDENCE_ONLY` with
an explicit `downgrade_reason="KAPPA_NOT_GAMMA"`.

### 3. README inflation (1 violation)

`README.md` line 82 reads "Mean across 6 validated substrates." This
contradicts §5.1 of the claim boundary (empty evidential core). The
`README_VALIDATED_COUNT_INCONSISTENT_WITH_EMPTY_CORE` rule fires.

Phase 2 reword: replace "validated substrates" with "measured
substrates" or with the §3.1 regime-marker framing. The mean and CI
remain reportable as **measurements**; only the framing changes.

## What this report does NOT do

- Does not auto-modify `evidence/gamma_ledger.json`.
- Does not auto-edit `README.md`.
- Does not auto-modify `docs/CLAIM_BOUNDARY.md`.
- Does not promote, downgrade, or invent any claim status.
- Does not implement the Phase 2 ledger schema (`null_family_status`,
  `rerun_command`, `claim_boundary_ref`, etc.) — it only flags their
  absence so Phase 2 can act.

## Invariants preserved by Phase 1

- κ ≠ γ (BN-Syn overclaim is **detected**, not silently fixed).
- Four-state ladder unchanged.
- `BLOCKED_BY_METHOD_DEFINITION` remains the canonical Mycelium verdict.
- Strict-JSON output (`allow_nan=False`).
- No new substrate, no new theory, no claim promotion.

## How to consume this report

Reviewers and downstream tooling should treat the JSON output as the
machine-readable source of truth:

```bash
python -m tools.audit.claim_surface_reconciliation --json-out evidence/recon.json
jq '.verdict, .violation_count' evidence/recon.json
jq '[.violations[] | .code] | group_by(.) | map({code: .[0], count: length})' evidence/recon.json
```

Exit code is `0` when `verdict == "RECONCILED"`, `2` otherwise. The gate
is fail-closed: zero contradictions are required before Phase 2 can
declare the canon coherent.

## Next phase pointer

Phase 2 (Ledger Evidence Hardening) extends `evidence/gamma_ledger.json`
with the required fields, populates real hashes where evidence exists,
and downgrades entries where evidence is incomplete. The reconciliation
gate's contradiction count must monotonically decrease across the Phase
2 sequence.
