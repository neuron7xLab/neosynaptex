# Repository Manifest (Generated)

- Manifest version: `1.0`
- Generated marker: `deterministic`
- Repository fingerprint: `7575b122eb42ac1d586886b25eb9738bb57f429c66d210ddde5f42d52f954bc1`
- Required PR gates source: `.github/PR_GATES.yml`
- Required PR gates SHA-256: `5ec87b49db654362aceda66d6cb036ee6b94ef7046d8bf5c89a620e909683b17`

## Metrics

- Workflow files (`.github/workflows/*.yml`): **40**
- Reusable workflow files (`_reusable_*.yml`): **9**
- Workflows declaring `workflow_call`: **11**
- Required PR gates (`.github/PR_GATES.yml`): **7**
- Coverage minimum percent (`quality/coverage_gate.json`): **95.0**
- Coverage baseline percent (`quality/coverage_gate.json`): **95.98**
- Mutation baseline score (`quality/mutation_baseline.json`): **51.61**
- Mutation total mutants (`quality/mutation_baseline.json`): **31**
- `ci_manifest.json` exists: **False**
- `ci_manifest.json` references in scoped scan: **0**
- `ci_manifest.json` scan scope:
  - `.github/workflows`
  - `scripts`
  - `docs`
  - `Makefile`
  - `README.md`

## Invariants

| ID | Statement | Enforcement | Evidence kind |
|---|---|---|---|
| INV-001 | Repository manifest markdown and computed snapshot are generated artifacts. | `python -m tools.manifest generate && git diff --exit-code -- .github/REPO_MANIFEST.md manifest/repo_manifest.computed.json` | artifact |
| INV-002 | PR gate workflows required by .github/PR_GATES.yml exist in .github/workflows/. | `python -m tools.manifest validate` | path:line-span |
| INV-003 | Coverage gate baseline is defined and parseable from quality/coverage_gate.json. | `python -m tools.manifest validate` | path:line-span |
| INV-004 | Mutation baseline is defined and parseable from quality/mutation_baseline.json. | `python -m tools.manifest validate` | path:line-span |
| INV-005 | ci_manifest.json is not used by automation and must remain absent. | `python -m tools.manifest validate` | artifact |

## Evidence Rules

Accepted pointer formats:
- `path:line-span`
- `artifact`
