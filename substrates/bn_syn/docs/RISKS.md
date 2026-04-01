# Risks

- Documentation drift risk between multiple legacy docs (`docs/TRACEABILITY_MAP.md` vs `docs/TRACEABILITY.md`).
  - Mitigation: machine-validated `docs/TRACEABILITY.md` + script validator.
- Public surface ambiguity risk for symbols exported via modules not listed in `__all__`.
  - Mitigation: conservative discovery in `scripts/discover_public_surfaces.py` with exclusions.
- Governance command drift risk when Make targets change.
  - Mitigation: all normative command references normalized in `docs/ENFORCEMENT_MATRIX.md`.
