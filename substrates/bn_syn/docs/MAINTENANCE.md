# Maintenance

## Canonical maintenance commands
- Test: `python -m pytest -m "not validation" -q`
- Lint: `ruff check .` and `pylint src/bnsyn`
- Typecheck: `mypy src --strict --config-file pyproject.toml`
- Build: `python -m build`
- Traceability: `python -m scripts.validate_traceability`
- Surface discovery: `python -m scripts.discover_public_surfaces`
- Internal link integrity: `python -m scripts.check_internal_links`

## Update protocol
1. Update SSOT-bearing specs/schemas/claims first.
2. Update code/tests.
3. Regenerate `docs/PROJECT_SURFACES.md`.
4. Update `docs/TRACEABILITY.md` and validate.
5. Run gates from `docs/ENFORCEMENT_MATRIX.md`.
