# Replications registry

> **Canonical protocol.** `docs/REPLICATION_PROTOCOL.md`
> **Preregistration template.** `docs/REPLICATION_PROTOCOL.md §7`
> **Ratchet gate.** `tools/audit/replication_index_check.py` +
> `.github/workflows/replication_index.yml`

## Purpose

This directory is the append-only index of every independent replication attempt filed against a γ-claim — whether supporting, falsifying, or theory-revising. The registry is deliberately empty at scaffold time: zero external replications have been logged.

## Shape

- `registry.yaml` — canonical machine-readable index. One `replications[]` entry per filed PR. Schema is verified by `tools/audit/replication_index_check.py`.
- `<slug>/` — per-replication directory. Contains the preregistration YAML, the raw evidence produced by the replication, and any supporting notes.

## How to file a replication

1. Create `evidence/replications/<slug>/prereg.yaml` populated per `docs/REPLICATION_PROTOCOL.md §7`.
2. Append a block to `registry.yaml` referencing the prereg by path.
3. Bump `min_replications_count` in `tools/audit/replication_baseline.json` by exactly the number of new entries; update `last_bumped` and append a rationale.
4. Open a PR. CI runs `tools/audit/replication_index_check.py` which verifies:
   - `registry.yaml` parses into the expected shape.
   - Every `prereg_path` exists on disk.
   - Every `verdict` is in the allowed set.
   - Every `substrate_class` is in the allowed set.
   - The replication count is `>= min_replications_count`.

Regressing the registry (removing an entry, or pointing at a missing prereg file) requires an explicit diff to the baseline and the registry, visible at review. The machine does not prevent legitimate redactions — it makes them non-silent.

## Integrity scope

The gate is **structural only**: it does not re-run any replication, does not verify γ values against the ledger, does not judge claim scope. Semantic correctness — whether the prereg meets §7, whether controls are adequate, whether the verdict is warranted — remains the reviewer's job per the protocol.

## What this directory does **not** duplicate

- `evidence/PREREG.md` — the original γ-measurement preregistration log. Different artefact: PREREG.md pins *measurement pipelines* to commit SHAs; this directory pins *replication attempts* to the canonical protocol.
- `evidence/gamma_ledger.json` — authoritative γ values per substrate. Replications link back to ledger entries they test.
- `evidence/EVIDENCE_INDEX.md` — manuscript-claim-to-evidence map. Replications of a claim update that map; they do not replace it.
