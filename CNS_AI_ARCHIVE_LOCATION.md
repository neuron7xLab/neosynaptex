# CNS-AI Archive Location (Step 2 stub — awaiting owner)

> **Purpose.** First required artefact of `CNS-AI Validation Protocol v1`
> (Step 2). Locates the physical archive that produced the headline
> `γ = 1.059, p = 0.005, n = 8271` claim attributed to substrate
> `cns_ai_loop`.
>
> **Status.** `blocked_by_owner_action` — the engine has completed
> all forensic discovery possible from repo contents. The remaining
> fields can only be populated by the owner. Until they are, the
> protocol cannot leave Step 2.
>
> **Claim status.** `unverified_evidence` per `CNS-AI Validation
> Protocol v1 §1`. Forbidden formulations remain forbidden.

## 1. Forensic findings (from repo contents on this commit)

### 1.1 Source of the headline number

The `γ=1.059 / n=8271` claim is produced by
`xform_full_archive_gamma_report.json` at the repo root:

```json
{
  "all":           {"g": 1.0585, "r2": 0.0951, "n": 8271, "cl": 0.9847, "ch": 1.1305},
  "productive":    {"g": 1.1381, "r2": 0.1219, "n": 6873, "cl": 1.0548, "ch": 1.2198},
  "nonproductive": {"g": -0.5573, "r2": -0.1005, "n": 1398, "cl": -0.6521, "ch": -0.4629},
  "by_ext": {
    ".py":   {"n": 5979, "g": 1.2984},
    ".odt":  {"n":  986, "g": 1.8238},
    ".md":   {"n":  938, "g": 0.1420},
    ".txt":  {"n":  188, "g": 0.2026},
    ".json": {"n":  147, "g": 0.6377}
  },
  "total": 8273
}
```

The `by_ext` breakdown proves that **the unit of analysis is files
grouped by file extension**, not sessions, not decisions, not
prompt-response pairs. `n=8271` is a count of files across a
file-system scan, with a productive/non-productive split applied
per-file.

### 1.2 Three pipelines, three disagreeing γ values

The repo contains three CNS-AI-adjacent gamma pipelines that do
not agree with each other:

| Report file | γ | n | unit | Notes |
|---|---|---|---|---|
| `xform_full_archive_gamma_report.json` | **1.0585** | **8271** | files by extension | **the headline source** |
| `xform_gamma_report.json` | n/a | 216 | ChatGPT export sessions | prod=110, nonprod=106 |
| `xform_odt_gamma_report.json` | 0.5941 | 986 | "ODT_3year_archive" docs | `gamma_productive: 0.5986` |
| `xform_combined_gamma_report.json` `ALL` | 1.695 | 1201 | sessions + ODT merged | different γ entirely |
| `xform_combined_gamma_report.json` `ODT_ALL` | 1.6206 | 986 | ODT only | same 986 as above, γ differs |

The same ODT subset (n=986) reports `γ=1.8238` in
`xform_full_archive_gamma_report.json` but `γ=0.5941` in
`xform_odt_gamma_report.json` and `γ=1.6206` in
`xform_combined_gamma_report.json`. **The three pipelines
disagree on the same subset.** This is a direct signal of the
"path mismatch" called out in §Step 4 of the validation protocol.

### 1.3 Path mismatches in the CNS-AI pipeline code

`substrates/cns_ai_loop/derive_real_gamma.py:16–17` declares:

```python
SESSIONS_DIR  = Path(__file__).resolve().parent / "evidence" / "sessions"
EVIDENCE_DIR  = Path(__file__).resolve().parent.parent.parent / "evidence"
```

- `substrates/cns_ai_loop/evidence/sessions/` — **directory does
  not exist** (0 `session_*` dirs, 0 `analysis.json` files).
- `./evidence/sessions/` (repo root) — **12 `session_*`
  directories** exist but contain only `events.jsonl`; no
  `analysis.json` files. The loader expects `analysis.json` with
  `statistics.{n_tasks,accuracy_pct,latency_cv}` — that shape is
  not present in the repo today.

`xform_session_probe.py` accepts a `conversations.json` path as an
argument (ChatGPT export format). **The file is not in the repo.**
Its physical location is unknown to the engine.

`decisions.jsonl` — **zero files in the repo.** Per §Step 5 of
the validation protocol: "without decisions.jsonl CNS-AI
evidence is not reproducible". The requirement is therefore
currently unmet.

### 1.4 Non-reproducibility from repo state

| Dimension | Report claim (n=8271) | Repo state today |
|---|---|---|
| `.py` files scanned | 5979 | 4056 |
| `.odt` files scanned | 986 | **0** |
| `.md` files scanned | 938 | (uncounted; present but not 938 exactly verifiable) |
| `.txt` files scanned | 188 | (uncounted) |
| `.json` files scanned | 147 | (uncounted) |

The archive that produced `n=8271` scanned **a broader file set
than is currently in the repository**, including 986 `.odt`
documents that have left zero trace in-tree. The scan was
therefore executed against a wider workspace or an historical
snapshot. **Which workspace, and when, the engine cannot
determine.**

## 2. Protocol-mandated fields — OWNER TO COMPLETE

The following fields are required by
`CNS-AI Validation Protocol v1 §Step 2`. The engine **refuses** to
fill them from inference because §XIII of the constitution
prohibits "synthetic evidence created to satisfy a protocol
narrative". Owner MUST populate.

- **storage_location**: `<UNRESOLVED — local machine | private repo | external storage | historical export bundle>`
- **owner**: `<UNRESOLVED — the person who retains operational access>`
- **raw_file_count**: `<UNRESOLVED — total files in the archive before productive/non-productive split>`
- **total_sessions_or_documents**: `<UNRESOLVED — if the archive contains sessions rather than files, how many>`
- **current_accessibility_status**: `<UNRESOLVED — readable today / behind credentials / offline / lost>`
- **decisions_jsonl_present**: **no** (verified: zero files in repo). If a `decisions.jsonl` exists in the physical archive, state where.
- **events_jsonl_alone_used**: `<UNRESOLVED>` — the 12 session dirs in `evidence/sessions/` carry only `events.jsonl`; if the 8271-count archive also had only events (no decisions), the protocol may not treat it as evidential.
- **unit_of_analysis_for_8271**: `documents (files classified by extension)`. Forensically verified from `xform_full_archive_gamma_report.json` `by_ext` tree. Owner: confirm or correct.

## 3. What the engine already locked down

- `substrate` = `cns_ai_loop` (confirmed in `README.md:179–181`).
- `reported result` = `γ=1.059, p=0.005, n=8271, CI=[0.985,1.131]` (confirmed in `substrates/cns_ai_loop/__init__.py:1` and `README.md:181–182`).
- `current status` = `unverified_evidence`.
- `source_report_file` = `xform_full_archive_gamma_report.json`.
- `derivation_code` = **three candidate pipelines present in the repo; which one actually produced the headline is not recorded in the report**. Owner: name the exact script + commit SHA that produced `xform_full_archive_gamma_report.json`.

## 4. Why this is Step 2 only

This document **does not** fulfil any of `Step 3`–`Step 10`. Specifically:

- `unit_of_analysis` is forensically inferred (files by extension) but
  has not been canonically declared in a `CNS_AI_DATASET_CARD.md`.
- Pipeline repair, public bundle, reproduction, surrogate validation,
  and external rerun all remain not-started.
- No downgrade / upgrade of the headline claim beyond
  `unverified_evidence` is performed here.

## 5. Next action

Owner edits §2 of this file with the five unresolved fields and
commits. The engine then proceeds to `Step 3 — CNS_AI_DATASET_CARD.md`
with a locked `storage_location` to reference.

Until §2 is completed, Step 3 and onward remain blocked. Per
`CNS-AI Validation Protocol v1 §1`:

> "reported internal result pending corpus publication, path
> repair, and surrogate validation"

is the only admissible claim-status phrasing.

---

**claim_status**: unverified_evidence
**blocked_by**: owner-action (§2 fields)
**forensic evidence gathered by**: engine, from repo contents on the current commit
**next required human input**: answer the question — where physically do the 8271 files live?
