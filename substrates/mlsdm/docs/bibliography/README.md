# Bibliography — Repository Standard (2025)

This directory is the canonical source of bibliographic metadata for this repository.

## Files (single source of truth)
- `REFERENCES_APA7.md` — human-readable bibliography in **APA 7**.
- `REFERENCES.bib` — machine-readable **BibTeX**.
- `metadata/identifiers.json` — offline canonical identifiers + frozen metadata.
- `VERIFICATION.md` — verification table generated from `identifiers.json`.

Root:
- `CITATION.cff` — repository-level citation metadata (GitHub "Cite this repository").

## Release Citation Contract
- `CITATION.cff` fields `version` and `date-released` **must match** the latest release entry in `CHANGELOG.md`.
- `CITATION.bib` **must be synchronized** with `CITATION.cff` (same release metadata and citation content).
- Do not update `CITATION.cff` or `CITATION.bib` in isolation; update them together when a new release is recorded.

## Policy
- Allowed: peer-reviewed journals, top-tier conferences (ACM/IEEE/USENIX), academic books, official standards (NIST/ISO/IEEE), widely-used arXiv preprints.
- Disallowed: personal blogs, unreviewed claims, non-stable URLs, sources without DOI/arXiv/canonical issuer URL.

## Risk-Aware Bibliography Governance
### Trust tiers
- **Standards**: normative specifications from official standards bodies (e.g., NIST/ISO/IEEE).
- **Peer-reviewed**: journal articles or top-tier conference proceedings with formal peer review.
- **arXiv**: preprints allowed only when no peer-reviewed version exists.
- **Official reports**: issuer-hosted technical reports from government or recognized institutions.

### Critical subsystem requirements
- Critical subsystems (**security**, **governance**, **safety**) must cite a minimum trust tier of **Standards** or **Peer-reviewed**.
- Critical subsystems (**security**, **governance**, **safety**) must include **at least 2** citations from **Standards** or **Peer-reviewed** sources in the Literature Map.

## Authoritative Source Audit
Explicitly verify the authority of every source before adding it:
- **Publication type**: journal article, top-tier conference proceeding, academic book, or official standard/issuer publication.
- **Peer review**: confirm the venue has a formal peer-review process (journals/conferences/books) or is an official issuer (standards/government).
- **Canonical identifier**: must include **DOI**, **ISBN**, or an **official issuer URL** (e.g., NIST/ISO/IEEE). Use the canonical issuer URL only when DOI/ISBN is not applicable.
- **arXiv policy**: arXiv-only entries are allowed **only if no journal or conference version exists**. If a journal/conference version exists, use that canonical ID instead.

## Peer-review Upgrade
When a peer-reviewed version becomes available, upgrade canonical identifiers and metadata accordingly:
- **Journal/conference version exists** → switch `canonical_id_type` to **DOI** and update `canonical_id`/`canonical_url` to the DOI-based canonical record.
- **No peer-reviewed version exists** → keep the arXiv canonical ID **and** add a metadata note (e.g., `peer_review_note`) explaining why a peer-reviewed version is unavailable or not applicable.

## Authority-Proof Checklist (blocking)
Complete this checklist **before** starting the Update workflow:
- Source passes the Authoritative Source Audit (type + peer review + identifier).
- `metadata/identifiers.json` includes the authority-proof minimum fields:
  `canonical_id_type`, `canonical_id`, `canonical_url`, `verification_method`.
- If the source is arXiv-only, confirm and note that no journal/conference version exists.

## Authority Proof (mandatory)
Every source must include **authority proof**; without it, the source is **not allowed**.

**Accepted authority proof types:**
- **DOI**
- **ISBN**
- **Official issuer URL** (standards bodies, government, or publisher-hosted canonical pages)
- **arXiv** (allowed **only** when no peer-reviewed version exists)

**Prohibited:**
- **Unstable URLs** (e.g., personal sites, link shorteners, ephemeral documents, or non-canonical mirrors).

**Authority proof source field:**
- In `metadata/identifiers.json`, the `verification_method` field records the **source of authority proof** used to validate the identifier (e.g., DOI registry, publisher, issuer catalog).

## Update workflow
1) Add entry to `REFERENCES.bib` (unique key; include title+year + one of doi/url/eprint/isbn).
2) Add same entry to `REFERENCES_APA7.md` with `<!-- key: ... -->` marker (APA 7).
3) Add/update the record in `metadata/identifiers.json` and regenerate the row in `VERIFICATION.md`.
4) Validate locally:
   - `python scripts/validate_bibliography.py`
   - `cffconvert --validate -i CITATION.cff`
5) Open PR; CI blocks invalid metadata.

## Atomic Update Protocol
All bibliography updates are a single, fully synchronized cycle across **all** of:
`REFERENCES.bib`, `REFERENCES_APA7.md`, `metadata/identifiers.json`, `VERIFICATION.md`.

**Mandatory synchronization steps (in order):**
1) Update `REFERENCES.bib` with the new or edited entry.
2) Mirror the same entry in `REFERENCES_APA7.md` (matching key via `<!-- key: ... -->`).
3) Update the corresponding record in `metadata/identifiers.json`.
4) Regenerate the matching row in `VERIFICATION.md` from `metadata/identifiers.json`.
5) Run local verification before PR:
   - `python scripts/validate_bibliography.py`
   - `cffconvert --validate -i CITATION.cff`

**Rules (non-negotiable):**
- **No partial updates** — any change must touch all four files in the same cycle.
- **1 commit = 1 full cycle** — a single commit must include the complete synchronized update.
- **Local verification before PR** — do not open a PR without passing local checks.

## Preflight Checklist
- Keep BibTeX, APA, metadata, and verification tables in sync (no drift between `REFERENCES.bib`, `REFERENCES_APA7.md`, `metadata/identifiers.json`, and `VERIFICATION.md`).
- Run `python scripts/validate_bibliography.py` (offline only; no network calls per `VERIFICATION.md` policy).
- Run `python scripts/docs/validate_literature_map.py` (offline only; no network calls per `VERIFICATION.md` policy).
- Before making changes, confirm every `paths:` entry exists in the repo (the `python scripts/docs/validate_literature_map.py` check enforces this).

## Safe Change Strategy
- one-commit update
- sync all four files
- verify locally

Incomplete updates (for example, adding a BibTeX entry without matching metadata/verification updates) are guaranteed to break CI.

## Literature map (CI-enforced)
- `docs/bibliography/LITERATURE_MAP.md` is required and validated in CI.
- Each subsystem entry must list 1–5 repo paths and **3+ citations** using `[@key]` from `REFERENCES.bib`.
- To add a subsystem: append a `## Subsystem Name` block with `paths:`, `citations:`, and a short rationale, then run `python scripts/docs/validate_literature_map.py`.

## Literature Map Path Integrity
- Every `paths:` entry **must** exist in the repository.
- When modules are renamed or moved, the corresponding `paths:` entries must be updated in the same change.
- Enforcement check: `python scripts/docs/validate_literature_map.py` validates the map, including path existence.

## Subsystem Coverage Audit
Any change to a subsystem or its API/modules **requires** auditing the corresponding block in `docs/bibliography/LITERATURE_MAP.md` before merge.

**Audit actions (blocking):**
1) **Path existence**: confirm every path in the subsystem block exists in the repo (same rule enforced by `python scripts/docs/validate_literature_map.py`).
2) **Citation completeness**: ensure the block still has **3+ citations** and each `[@key]` resolves to `REFERENCES.bib`.
3) **Rationale alignment**: update the rationale so it still matches the subsystem behavior, scope, and interfaces after the change.

Run `python scripts/docs/validate_literature_map.py` as the technical enforcement step whenever applicable.
