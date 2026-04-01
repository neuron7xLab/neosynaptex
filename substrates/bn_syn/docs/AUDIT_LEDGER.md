# Audit Ledger

## FND-0001 — Governed doc scanner drift
- **Symptom:** Governed doc scans were limited to tag checks and lacked an inventory-based doc list, leaving normative keyword lines unenforced. (scripts/scan_governed_docs.py:L1-L109, docs/INVENTORY.md:L5-L57)
- **Root cause:** Governed docs list lived outside the inventory and the scanner did not evaluate normative keywords.
- **Blast radius:** Any governed document line using normative keywords could bypass claim tagging.
- **Fix decision:** **FIX** — Moved the authoritative governed docs list to `docs/INVENTORY.md` and upgraded `scan_governed_docs.py` to enforce keyword + tag requirements.
- **Acceptance criteria:** `python -m scripts.scan_governed_docs` fails on missing NORMATIVE + CLM-#### tags in governed docs and reports counts.

## FND-0002 — SSOT rules missing expected fields
- **Symptom:** SSOT rule registry lacked scope and examples, and used inconsistent enforcement field naming. (docs/SSOT_RULES.md:L1-L94)
- **Root cause:** Rule schema was underspecified relative to governance requirements.
- **Blast radius:** Drift between documented rules and validators could go unnoticed.
- **Fix decision:** **FIX** — Expanded each rule entry to include `scope`, `enforcement_script`, and `examples` fields.
- **Acceptance criteria:** `docs/SSOT_RULES.md` lists the expected metadata for every rule and remains synchronized with `scripts/ssot_rules.py`.

## FND-0003 — Untagged normative keywords in governed docs
- **Symptom:** Governed docs used normative keywords without claim binding tags. (README.md:L48-L56, docs/CI_GATES.md:L1-L78, docs/PERFORMANCE.md:L29-L35)
- **Root cause:** Policy and CI documentation used normative phrasing without explicit claim linkage.
- **Blast radius:** Violates G0 “No Soft Text” by leaving normative statements untraceable.
- **Fix decision:** **FIX** — Rephrased lines to remove normative keywords while preserving intent.
- **Acceptance criteria:** `python -m scripts.scan_governed_docs` reports zero orphan normative lines.

## FND-0004 — Normative tag scan lacked tier validation
- **Symptom:** NORMATIVE tag scanning only verified claim existence, not Tier-A/normative compliance. (scripts/scan_normative_tags.py:L1-L103)
- **Root cause:** Validator omitted tier/normativity enforcement despite SSOT rules.
- **Blast radius:** Non-Tier-A claims could be referenced as normative without detection.
- **Fix decision:** **FIX** — Enforced Tier-A + normative validation for every NORMATIVE + CLM-#### reference.
- **Acceptance criteria:** `python -m scripts.scan_normative_tags` fails on non-Tier-A or non-normative references.

## FND-0005 — Evidence coverage missing status + DOI/URL
- **Symptom:** Evidence coverage table omitted claim status and Tier-S canonical URLs. (docs/EVIDENCE_COVERAGE.md:L1-L30, scripts/generate_evidence_coverage.py:L1-L121)
- **Root cause:** Generator only emitted DOI values without status or URL fallback.
- **Blast radius:** Evidence coverage could not show provenance completeness for all claim tiers.
- **Fix decision:** **FIX** — Added status column and DOI/URL resolution from `sources.lock`.
- **Acceptance criteria:** `docs/EVIDENCE_COVERAGE.md` includes status and DOI/URL for every claim.
