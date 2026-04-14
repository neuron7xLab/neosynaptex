# CNS-AI Path Contract — frozen record of path mismatch at downgrade

> **Status:** CLOSED at downgrade. This document records the path
> mismatch that was called out in
> `CNS-AI Validation Protocol v1 §Step 4` and freezes it so future
> refactors of `substrates/cns_ai_loop/` do not accidentally revive
> the broken contract as if it had a valid target.
> **Pair document:** `docs/CLAIM_BOUNDARY_CNS_AI.md`.

## 1. What `derive_real_gamma.py` declared as canonical

`substrates/cns_ai_loop/derive_real_gamma.py:16–17`:

```python
SESSIONS_DIR  = Path(__file__).resolve().parent / "evidence" / "sessions"
EVIDENCE_DIR  = Path(__file__).resolve().parent.parent.parent / "evidence"
```

Expected shape: `SESSIONS_DIR / "session_*" / "analysis.json"` with fields
`statistics.{n_tasks, accuracy_pct, latency_cv}`.

## 2. What the repo actually contains (at the downgrade commit)

| Expected | Actual |
|---|---|
| `substrates/cns_ai_loop/evidence/sessions/` | **Does not exist.** Zero `session_*` directories. Zero `analysis.json` files. |
| `./evidence/sessions/` (repo root) | **Exists.** 12 `session_*` directories. Each contains `events.jsonl` only. No `analysis.json`. No `decisions.jsonl`. |
| `conversations.json` (input to `xform_session_probe.py`) | **Not in repo.** Required external ChatGPT export. |
| `decisions.jsonl` anywhere | **Zero files in repo.** |
| File-archive scan of workspace that produced `n=8271` | **Not preserved.** Owner confirmed on 2026-04-14 that the workspace state that produced the number is gone. |

## 3. Why the mismatch is structural, not fixable

Repairing the path would mean:

- Pointing the loader at `./evidence/sessions/` — but that directory's sessions contain only `events.jsonl`, not the `analysis.json` shape the loader reads. Even a successful path fix would produce zero rows.
- Supplying a fresh `conversations.json` — but the 216-session ChatGPT export counted by `xform_session_probe.py` is a different dataset from the 8271-file scan that produced the headline. Substituting one for the other is not a repair, it is a new substrate.
- Regenerating `xform_full_archive_gamma_report.json` — the original workspace is not preserved; the scan cannot be repeated.

The headline claim's pipeline and the headline claim's data **never lived at the same path**. There is no well-defined "fixed path" to migrate to. Repair has no valid target.

## 4. Cascade of blocked protocol steps

| Protocol step | Status | Reason |
|---|---|---|
| §Step 3 dataset card | CLOSED | Unit of analysis is file-scan — category error. Writing a card would canonise the error. |
| §Step 4 pipeline repair | CLOSED | No valid target (this document). |
| §Step 5 public bundle | CLOSED | Zero `decisions.jsonl`; scan cannot be reproduced. |
| §Step 6 reproduction | CLOSED | Non-existent corpus. |
| §Step 7 surrogate validation | CLOSED | Surrogates on non-existent data are undefined. |
| §Step 8 exploratory/evidential split | CLOSED | Verdict: exploratory. |
| §Step 9 independent rerun | CLOSED | §5 precondition unmet. |
| §Step 10 final decision | CLOSED | Branch C — falsified/downgraded. |

## 5. What the code now does instead

`substrates/cns_ai_loop/derive_real_gamma.py` is patched in the same PR that ships this document:

- Module-level comment explicitly flags `DATA SOURCE NON-EXISTENT`.
- Loader entry raises `CorpusNotFoundError` with a pointer at `docs/CLAIM_BOUNDARY_CNS_AI.md`.
- No silent fallback. No ambiguous exit code. No dry-run mode that pretends to have data.

## 6. Reactivation

A PR that restores CNS-AI as an evidential substrate MUST:

1. Define a new unit of analysis (probably sessions, not files).
2. Declare a new `SESSIONS_DIR` whose contents match the loader contract.
3. Populate `decisions.jsonl` with per-unit decision records.
4. Stamp `data_sha256` and `substrate_code_hash` on every derived row.
5. Satisfy every reactivation condition in
   `docs/CLAIM_BOUNDARY_CNS_AI.md §6`.

A PR that only moves paths around without addressing the unit-of-analysis category error is rejected on review.

---

**claim_status:** measured (about the path mismatch; the claim itself is downgraded in the companion document)
**closed:** 2026-04-14
**supersedes:** `derive_real_gamma.py` silent-skip behaviour
