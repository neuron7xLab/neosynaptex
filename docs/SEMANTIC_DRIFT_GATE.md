# Semantic Drift Gate

A deterministic PR-time audit that blocks prose from **outrunning the
evidence it cites**. Complements the `claim_status_check` (structural
presence of a `claim_status:` block) with a **semantic** check: does
the changed wording sit inside the ceiling authorized by the linked
evidence and the registered claim status?

- **Script:** `tools/audit/semantic_drift_gate.py`
- **Contracts:** `contracts/claim_strength.py`
- **Config:** `contracts/semantic_drift_config.yaml`
- **Workflow:** `.github/workflows/semantic_drift_gate.yml`
- **Tests:** `tests/audit/test_semantic_drift_gate.py`

## Two companions, one loop

| Gate | Question | Layer |
|------|----------|-------|
| `claim_status_check` | Does the PR body declare a canonical `claim_status:` label? | Syntactic |
| `semantic_drift_gate` | Does the changed prose respect the authorized ceiling of that label? | Semantic |

Both are needed. The first prevents PRs from silently dropping the
taxonomy; the second prevents PRs from keeping the taxonomy but
quietly strengthening prose beyond what evidence and status license.

## What the gate does

1. Scans the diff on protected files (`README.md`,
   `CANONICAL_POSITION.md`, `PROTOCOL.md`, `CONTRACT.md`,
   `docs/SYSTEM_PROTOCOL.md`, `docs/ADVERSARIAL_CONTROLS.md`,
   `docs/REPLICATION_PROTOCOL.md`, and anything under `manuscript/`).
2. Segments each file into claim-bearing spans (headings, bullets,
   sentences, table cells).
3. For each changed span, assigns:
   - **Tier** 0–8 (descriptive → universal law) from lexical markers.
   - **Scope** 0–4 (local → universal).
   - **Causality** 0–4 (none → causal intervention).
   - **Boundary markers** (`bounded`, `substrate-specific`, …).
4. Looks up the *authorized ceiling* = `min(evidence ceiling, status
   ceiling)`:
   - **Evidence ceiling** from `evidence/semantic_drift_registry.json`
     or `evidence/evidence_registry.json`, indexed by claim IDs
     parsed inline (`evidence: ev42` or `[evidence: ev42]`) or from
     `evidence_by_file` in the registry.
   - **Status ceiling** from the canonical 5-label taxonomy
     (`measured`=4, `derived`=3, `hypothesized`=1, `unverified
     analogy`=1, `falsified`=0) plus the extended labels used
     internally by the gate.
5. Classifies the event as **pass / warn / fail** by the rules in
   `_event_is_fail` and `_hard_failures`.

### Canonical 5 labels are mapped

The `STATUS_CEILINGS` map in `contracts/claim_strength.py` and
`contracts/semantic_drift_config.yaml` must keep all five canonical
labels from `tools.audit.claim_status_applied.CANONICAL_LABELS` in
sync. A regression test enforces this invariant:

```python
tests/audit/test_semantic_drift_gate.py
  ::test_canonical_five_labels_all_have_ceilings
```

If the taxonomy changes, update both files and rerun the test.

## Hard-fail patterns (non-exhaustive)

- `consistent with` → `demonstrates` without a new evidence object.
- `candidate` → `validated` without replication.
- `substrate-specific` / `bounded` stripped while certainty rises.
- `associated with` → `causes` without intervention evidence.
- `measured_but_bounded` rewritten as `proof`.
- `honest_null` rewritten as support for a positive theory.
- `universal` / `law` language from local or exploratory evidence.
- README boundary language stripped while `claim_status` is unchanged.
- PR title / body stronger than the changed evidence allows (when
  `enforce_pr_surfaces: true`).

## Adoption: PR-surface enforcement is off by default

The gate's strictest mode audits PR titles and bodies against the
authorized ceiling of the claims they make. That mode collapses to
hard-fail whenever no evidence-registry entry is linked to the PR —
which would be every PR until the HRV / γ-program corpus is
catalogued in `evidence/semantic_drift_registry.json`.

To avoid blocking legitimate PRs during the adoption phase,
`contracts/semantic_drift_config.yaml` ships with
`enforce_pr_surfaces: false`. File-level enforcement on the protected
canonical documents is active from day one; the PR-surface layer
activates once the registry is populated.

To enable PR-surface enforcement later:

```yaml
# contracts/semantic_drift_config.yaml
enforce_pr_surfaces: true
```

## Local dry-run

```bash
python -m tools.audit.semantic_drift_gate \
    --base-ref origin/main \
    --head-ref HEAD
```

Writes `reports/semantic_drift/latest.json` and `latest.md`. Exits
non-zero only if the report verdict is `fail`.

## Extending

- **New hard-fail reason** — add the string to `_HARD_FAIL_REASONS`
  in `tools/audit/semantic_drift_gate.py` **and** return it from
  `_hard_failures` (or from the ceiling check in `classify_event`).
  The aggregate verdict and per-type counts go through
  `_event_is_fail`; they stay consistent automatically.
- **New status label** — add it to `STATUS_CEILINGS` in
  `contracts/claim_strength.py` and the YAML config in one patch;
  the canonical-label regression test above guards against drift.
- **New boundary marker** — add it to `BOUNDARY_MARKERS` in
  `contracts/claim_strength.py` and to
  `tools/audit/claim_span_extractor.extract_boundary_markers`
  (already auto-picks up the list).
