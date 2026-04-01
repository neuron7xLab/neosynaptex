# PR Pipeline SLO

- **Standard PR SLO:** end-to-end required checks complete in **<= 10 minutes**.
- **Risky PR SLO (`heavy-ci` and/or `run-codeql`):** extended checks complete in **<= 25 minutes**.

## Label policy

- `run-validation` — force-run `pytest -m validation` on PR.
- `run-property` — force-run `pytest -m property` on PR.
- `run-codeql` — force-run CodeQL job on PR.
- `heavy-ci` — force-run validation + property + docs + codeql paths in PR pipeline.
