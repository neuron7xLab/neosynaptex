# Escape Analysis (ranked)

1. Missing contract checks on PR path for tripwires/reproducibility.
   - Impact: high; Likelihood: medium.
   - Fix: add `contracts` job in `ci-pr-atomic.yml` with explicit tests and reproducibility verifier.
2. Bare-except or TODO/FIXME drift in production paths.
   - Impact: high; Likelihood: medium.
   - Fix: `tests/test_no_escape_tripwires.py` AST/text tripwires.
3. Workflow action pinning regression.
   - Impact: high; Likelihood: low-medium.
   - Fix: dedicated `tests/test_actions_pinning.py`.
4. Acceptance map missing fail-closed no-escape criteria.
   - Impact: medium; Likelihood: medium.
   - Fix: `no_escape_acceptance` contract section in `acceptance_map.yaml` + schema test.
5. Generated artifacts drift without deterministic proof.
   - Impact: high; Likelihood: medium.
   - Fix: `scripts.verify_reproducible_artifacts.py`, reproducibility spec and report.
