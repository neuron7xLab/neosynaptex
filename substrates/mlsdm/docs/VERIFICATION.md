# Verification

## Objective
Enumerate the documentation truth gates, how they run locally, and how CI enforces them.

## Make targets
| Target | Checks | Script(s) |
| --- | --- | --- |
| `make verify-docs` | Documentation claims match code defaults; skip_paths examples include safe defaults. | `scripts/verify_docs_claims_against_code.py`, `scripts/verify_docs_examples.py`, `scripts/verify_docs_contracts.py` |
| `make verify-security-skip` | Skip-path defaults and boundary safety for security middleware. | `scripts/verify_security_skip_invariants.py`, `scripts/verify_docs_examples.py` |

## Scripts
- `scripts/verify_docs_examples.py`: scans `docs/**/*.md` for skip_paths list/tuple examples and enforces that every example contains all default public paths.
- `scripts/verify_docs_claims_against_code.py`: checks that documented default public paths match `mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS`.
- `scripts/verify_docs_contracts.py`: verifies JSON `doc_contract` blocks in `docs/CONTRACTS_CRITICAL_SUBSYSTEMS.md` against code defaults.

## CI expectations
- The `ci-neuro-cognitive-engine` workflow runs `make verify-docs` and fails on any mismatch between documentation and code defaults.

## Local reproduction
```bash
make verify-docs
make verify-security-skip
```
