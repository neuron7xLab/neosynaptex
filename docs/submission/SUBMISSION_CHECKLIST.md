# Submission Checklist — NeoSynaptex Manuscript

> **Audience:** corresponding author preparing the manuscript for journal
> submission (target: *Nature Communications*, *PLOS Computational Biology*,
> *Physical Review Letters*, or equivalent).
>
> Complete all items before submitting. Items marked **[GATE]** block
> submission if not resolved.

---

## 1. Code and Data Integrity

- [ ] **[GATE]** `python scripts/ci_canonical_gate.py` exits 0 on current `main`
- [ ] **[GATE]** `python scripts/verify_manuscript_claims.py` exits 0 (all 20 claims pass)
- [ ] **[GATE]** `python reproduce.py` produces gamma values matching `evidence/gamma_ledger.json`
      within rounding tolerance
- [ ] `pytest tests/ -q -m "not slow" --timeout=300` exits 0 (all non-slow tests pass)
- [ ] Docker reproduction: `docker build -f Dockerfile.reproduce -t t . && docker run --rm t`
      exits 0
- [ ] `evidence/data_hashes.json` hashes verified against current data files
- [ ] All T1 substrate data files present in `data/` with matching SHA-256 hashes

---

## 2. Evidence Ledger

- [ ] **[GATE]** Every substrate in Table 1 has a `VALIDATED` entry in `evidence/gamma_ledger.json`
- [ ] Every `VALIDATED` entry has `ci_low`, `ci_high`, `r2`, and `n_pairs` populated
- [ ] Ledger version matches `version` field in `evidence_bundle_v1/manifest.json`
- [ ] `cfp_diy` entry present and marked `OUT-OF-REGIME` with honest documentation
- [ ] Pre-registration hashes in `evidence/PREREG.md` verified against git log

---

## 3. Statistical Claims

- [ ] **[GATE]** All Tier-1 substrates pass IAAFT surrogate test (p < 0.05)
- [ ] Cross-substrate mean gamma CI reported in manuscript matches ledger computation
- [ ] Bootstrap n >= 500 for all gamma CI computations (check `_BOOTSTRAP_N` constant)
- [ ] Permutation p-value < 0.05 for all VALIDATED substrates
- [ ] Negative controls (white noise, random walk, supercritical) produce gamma outside [0.7, 1.3]
      — verified by `tests/test_falsification_negative.py`
- [ ] BN-Syn finite-size deviation (gamma ≈ 0.49) documented and explained in manuscript
- [ ] No p-hacking: pre-registration timestamps predate measurement dates in ledger

---

## 4. Manuscript Text

- [ ] Abstract matches key results in `XFORM_MANUSCRIPT_DRAFT.md` (root pointer)
- [ ] All gamma values in text match `evidence/gamma_ledger.json` (no manual edits)
- [ ] All CI values reported as [lower, upper] with explicit confidence level (95%)
- [ ] Hypothesis H1 and H2 stated with explicit falsification conditions
- [ ] Limitations section present — cross-reference `docs/KNOWN_LIMITATIONS.md`
- [ ] Negative controls described honestly (cfp_diy out-of-regime control)
- [ ] Methods section references `core/gamma.py` and `core/bootstrap.py` for computation details
- [ ] Data availability statement: links to PhysioNet, McGuirl 2020, and this repository
- [ ] Code availability statement: AGPL-3.0, GitHub URL, archived Zenodo DOI

---

## 5. Figures

- [ ] All figures reproducible from `python scripts/generate_figures.py` (or equivalent)
- [ ] Figure captions reference the substrate and ledger key
- [ ] Phase diagram figure (`phase_diagram.svg`) matches current ledger values
- [ ] Gamma trajectory figure (`gamma_trajectory.pdf`) present and matches `reproduce.py` output
- [ ] Figure files included in `figures/` directory

---

## 6. Supplementary Material

- [ ] `XFORM_NEURO_DIGITAL_SYMBIOSIS.md` reviewed for consistency with main manuscript
- [ ] Extended methods for each substrate in `substrates/*/README.md`
- [ ] `xform_statistical_tests.json` included as supplementary data
- [ ] `coherence_bridge_demo.json` referenced if used in manuscript

---

## 7. Repository and Archival

- [ ] Repository tagged with submission version: `git tag v{VERSION}-submit`
- [ ] Zenodo DOI created for submission tag (update `.zenodo.json` metadata first)
- [ ] `CANONICAL_OWNERSHIP.yaml` up to date with current authorship
- [ ] `LICENSE` file present (AGPL-3.0)
- [ ] `README.md` badge counts accurate (substrates, tests, p-value)
- [ ] `AUDIT_REPORT_2026-04-01.md` included as supplementary verification document

---

## 8. Reviewer Readiness

- [ ] `docs/REVIEWER_GUIDE.md` updated and reviewed
- [ ] `docs/REPRODUCIBILITY.md` step-by-step guide verified by third party
- [ ] All relative links in documentation resolve correctly
- [ ] `docs/KNOWN_LIMITATIONS.md` reviewed — all CRITICAL items addressed or documented

---

## 9. Cover Letter Items

- [ ] Confirm no prior publication of these specific gamma results
- [ ] Declare no competing interests
- [ ] Suggested reviewers list prepared (minimum 3)
- [ ] Target journal data/code sharing policy reviewed — AGPL compliance confirmed

---

## Sign-off

| Item | Verified by | Date |
|------|-------------|------|
| Canonical gate pass | | |
| Manuscript claims verified | | |
| Docker reproduction | | |
| Figure reproducibility | | |
| Ledger integrity | | |
