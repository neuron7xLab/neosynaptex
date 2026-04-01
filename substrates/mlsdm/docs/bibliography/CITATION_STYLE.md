# MLSDM Citation Style

- **Inline syntax:** `[@bibkey]`
  - Example: “We use retrieval-augmented generation [@lewis2020_rag].”
- **Source of truth:** Only cite keys that exist in `docs/bibliography/REFERENCES.bib`.
- **Applicability:** Every non-trivial claim in foundation docs **must** include at least one citation.
- **No raw links as authority:** Use bibliography keys instead of embedding external URLs.
- **Multiple citations:** Use `[@key1; @key2]` if needed for the same claim.

Foundation docs (must be cited):
- `docs/ARCHITECTURE_SPEC.md`
- `docs/BENCHMARK_BASELINE.md`
- `docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md`
- `docs/FORMAL_INVARIANTS.md`
- `docs/DEVELOPER_GUIDE.md`

## Neuro-Core Evidence Policy (Audit Gate)

Neuro-core docs require strict evidence handling to prevent unsupported neuro claims:

- **Neuro-core docs:** `docs/NEURO_FOUNDATIONS.md`, `docs/APHASIA_SPEC.md`,
  `docs/APHASIA_OBSERVABILITY.md`
- **Citation format:** Only `[@bibkey]` entries that resolve to
  `docs/bibliography/REFERENCES.bib` are permitted.
- **UNPROVEN labeling:** Any neuroscience claim that cannot be cited must be
  labeled explicitly as `UNPROVEN (engineering analogy)` or `UNPROVEN
  (engineering heuristic)` and must not be presented as factual neuroscience.
- **Non-clinical boundary:** "Aphasia/Broca" references in MLSDM denote
  LLM-output phenotypes/heuristics inspired by literature, not medical diagnosis
  or clinical models.
