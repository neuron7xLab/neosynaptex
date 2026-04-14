# CNS-AI Claim Boundary — DOWNGRADED

> **Canonical status:** `falsified_downgraded`.
> **Effective date:** 2026-04-14.
> **Authority:** repository owner, via `CNS-AI Validation Protocol v1 §Step 10 Branch C`.
> **Applies to:** the CNS-AI Loop substrate claim `γ=1.059, p=0.005, n=8271, CI=[0.985,1.131]` previously displayed in `README.md` and stamped in `substrates/cns_ai_loop/__init__.py`.

## 1. Verdict

The headline CNS-AI result is **not evidential**. It is retained in this repository only as an exploratory historical artefact.

Two independent reasons jointly suffice; either alone would downgrade the claim:

**R1 — Corpus non-existence.** The archive that produced `n=8271` does not exist as a reproducible corpus. Owner confirmed on 2026-04-14 that the figure came from a scan of the owner's local workspace at a specific point in time; the workspace state at that moment has not been preserved. It cannot be re-scanned and cannot be redistributed.

**R2 — Category error in unit of analysis.** `xform_full_archive_gamma_report.json` records `n=8271` with a `by_ext` breakdown (`.py=5979, .odt=986, .md=938, .txt=188, .json=147`). The unit of analysis is therefore **file-system entries classified by extension**. The substrate is described as a human-AI cognitive loop whose unit should be a session, decision, or interaction episode. Files are not cognitions. Counting files produces a number; it does not measure the substrate the claim names.

## 2. Forbidden claims

None of the following may appear in manuscripts, releases, READMEs, or public communication about this repository:

- "confirmed"
- "proved"
- "publishable evidential core"
- "law-supporting substrate"
- "validated sixth substrate"
- "six validated substrates"
- any language that treats `γ=1.059 / n=8271` as evidence for metastability, criticality, cognition, a universal law, or a cross-substrate invariant.

## 3. Allowed claims

The historical result may be referenced only under the following framings:

- "historical exploratory result, non-reproducible"
- "internal file-archive scan, 2026-03/04, not evidential"
- "superseded by `CLAIM_BOUNDARY_CNS_AI.md` downgrade"

Any public reference to the numbers must cite this boundary document by relative path.

## 4. Scope of the downgrade

The downgrade applies to:

- The CNS-AI Loop substrate as a CLAIM (removed from the validated set).
- The headline figures `γ=1.059, p=0.005, n=8271, CI=[0.985,1.131]`.
- The status of `xform_full_archive_gamma_report.json` as evidence (re-classified: report of a historical scan, not a validation artefact).

The downgrade does **not** apply to:

- The five substrates already present in `evidence/gamma_ledger.json` with `status: VALIDATED`:
  `zebrafish_wt`, `gray_scott`, `kuramoto`, `bnsyn`, `eeg_physionet`
  (plus `hrv_physionet`, `eeg_resting`, `serotonergic_kuramoto`, `hrv_fantasia` under their existing entry-level `status` and `verdict` fields).
- The codebase in `substrates/cns_ai_loop/` as EXPERIMENTAL code. The modules remain in-tree for historical continuity and possible future reframing as a different, well-scoped substrate.

## 5. Consequences under `CNS-AI Validation Protocol v1`

- **§Step 1 — Freeze claim**: closed; claim frozen as `falsified_downgraded`.
- **§Step 2 — Locate corpus**: closed; owner verdict recorded as "source data non-existent".
- **§Steps 3–10**: **CLOSED — source data non-existent**. Each is individually unreachable because their precondition is a reproducible corpus that does not exist.

Each step's blocking rationale:

| Step | Blocking rationale |
|---|---|
| §3 dataset card | Unit of analysis is file-extension scan, which is category-error relative to the substrate. A dataset card would canonise a category error. |
| §4 path repair | `derive_real_gamma.py` reads from `substrates/cns_ai_loop/evidence/sessions/` which never contained the 8271 files. Repair has no valid target. |
| §5 public bundle | Zero `decisions.jsonl`; zero sessions matching the loader contract; 986 `.odt` files never in-tree. Nothing to publish. |
| §6 reproduce | Re-deriving γ from the claimed pipeline on the claimed corpus is impossible; the corpus does not exist. |
| §7 surrogate | Surrogates on non-existent data are undefined. |
| §8 exploratory vs evidential | Decided: **exploratory**, closed at this step. |
| §9 independent rerun | Precondition (public bundle) not met. Cascade-blocked. |
| §10 final decision | Decision reached: **Branch C — Falsified/downgraded**. Criterion met: "unit-of-analysis / self-label bias makes claim non-evidential". |

## 6. Reactivation conditions

This downgrade may be reversed only by a PR that:

1. Names a substrate definition whose unit of analysis matches whatever is actually being measured (e.g., if cognitive sessions are the claimed unit, the corpus MUST be cognitive sessions — not files).
2. Provides a publishable, anonymised bundle of ≥ 500 valid units of the claimed type.
3. Contains `decisions.jsonl` with per-unit decision records.
4. Ships a reproducible pipeline that re-derives γ from the bundle with `substrate_code_hash` and `data_sha256` stamped on every row.
5. Passes `CNS-AI Validation Protocol v1` §Steps 2–10 in order, including an independent external rerun (§Step 9).
6. Explicitly revokes §§1–4 of this boundary document, citing which reactivation condition each §§1–4 claim is now supported by.

Anything less is a re-run of the same category error. Refuse on review.

## 7. Cross-references

- **Forensic record:** `CNS_AI_ARCHIVE_LOCATION.md` §1 (engine-produced) + §2 (owner verdict).
- **Path mismatch record:** `docs/protocols/CNS_AI_PATH_CONTRACT.md`.
- **README annotation:** the CNS-AI Loop substrate cell in `README.md` is now marked `[EXPLORATORY — corpus non-reproducible]`.
- **Code annotation:** `substrates/cns_ai_loop/derive_real_gamma.py` now raises `CorpusNotFoundError` at the loader boundary; no silent fallback.

---

**claim_status:** falsified_downgraded
**effective:** 2026-04-14
**superseded:** `README.md:178–182` headline numbers, `substrates/cns_ai_loop/__init__.py:1` module docstring
**next required human input:** none — the downgrade is self-contained
