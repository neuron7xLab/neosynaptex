1. EXECUTIVE_VERDICT
This repository is not ready to be the single canonical repo. It is a meta-monorepo that aggregates multiple independently-canonical systems (Neosynaptex core, BN-Syn, TradePulse/Kuramoto, MLSDM, Mycelium/MFN+, neuron7x-agents) with conflicting package identities, duplicated codebases, mixed licenses, and non-hermetic test/dependency surfaces. Canonical R&D value is high, but authority is split across parallel truth layers; archive operations on predecessor repos are unsafe until authority ownership, migration map, and reproducibility contracts are normalized.

2. DISTINGUISHED_ENGINEER_FELLOW_GRADE
PARTIAL

3. SYSTEM_IDENTITY
- Real system: umbrella research/product aggregation repo, not a single cohesive product.
- Strategic center: root `neosynaptex.py` + `contracts/` + `core/` + root tests for gamma/coherence contract.
- Real layers:
  - Canonical-core candidate: root `neosynaptex.py`, `core/`, `contracts/`, `tests/`.
  - Imported substrate stacks: `substrates/bn_syn`, `substrates/kuramoto`, `substrates/mlsdm`, `substrates/mfn_plus`, `substrates/mycelium`.
  - Parallel agent framework: `agents/`.
  - Narrative/proof surfaces: `manuscript/`, `evidence/`, substrate `docs/`, `artifacts/`.

4. ARCHITECTURAL_TRUTH_MAP
- `neosynaptex.py` -> integration runtime for gamma/coherence -> canonical.
- `core/` + `contracts/` + root `tests/` -> root contract layer -> canonical.
- `bn_syn/` (root mini-package) -> adapter/proxy surface -> adapter.
- `substrates/bn_syn/` -> full BN-Syn program + proof pipeline -> authority_conflict (with root `bn_syn/`).
- `agents/` -> standalone package `neuron7x-agents` -> partial ingest (independent canonical).
- `substrates/kuramoto/` -> standalone TradePulse platform -> drifted (independent canonical).
- `substrates/mlsdm/` -> standalone MLSDM platform -> drifted (independent canonical).
- `substrates/mfn_plus/` and `substrates/mycelium/` -> near-duplicate MyceliumFractalNet trees -> duplicate + authority_conflict.
- `manuscript/` + `agents/manuscript/` + substrate docs -> scientific narrative surfaces -> fragmented.
- `evidence/` (root) -> mostly empty placeholder -> dead/unclear.

5. REQUIRED_MIGRATION
- source: `substrates/mfn_plus/src/mycelium_fractal_net/**`
  target: `substrates/mycelium/src/mycelium_fractal_net/**`
  classification: REQUIRED_MIGRATION
  why: duplicate package identity (`mycelium-fractal-net`) split across two trees.
  risk_if_omitted: split-brain fixes, unverifiable provenance.

- source: `substrates/mfn_plus/tests/**`
  target: `substrates/mycelium/tests/**`
  classification: REQUIRED_MIGRATION
  why: preserve differential tests before deprecating one owner.
  risk_if_omitted: silent regression coverage loss.

- source: `bn_syn/*.py`
  target: `substrates/bn_syn/src/bnsyn/adapters/neosynaptex_compat/`
  classification: REQUIRED_MIGRATION
  why: remove dual BN-Syn code ownership.
  risk_if_omitted: adapter/runtime drift.

- source: `agents/src/neuron7x_agents/verification/kriterion/**`
  target: `substrates/verification/kriterion/**`
  classification: REQUIRED_MIGRATION
  why: high-value verification schemas/tools should be canonicalized once and reused.
  risk_if_omitted: duplicated governance semantics.

- source: `manuscript/XFORM_MANUSCRIPT_DRAFT.md`
  target: `docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md`
  classification: REQUIRED_MIGRATION
  why: root scientific claim surface currently detached from substrate evidence indices.
  risk_if_omitted: claim/evidence traceability break.

- source: `agents/docs/BIBLIOGRAPHY.md`
  target: `docs/bibliography/AGENTS_BIBLIOGRAPHY.md`
  classification: REQUIRED_MIGRATION
  why: bibliography memory otherwise remains subsystem-local.
  risk_if_omitted: citation loss during archival.

- source: `substrates/mlsdm/docs/CLAIM_EVIDENCE_LEDGER.md`
  target: `docs/evidence_ledgers/mlsdm_claim_evidence_ledger.md`
  classification: REQUIRED_MIGRATION
  why: high-value claim-to-proof mapping.
  risk_if_omitted: unverifiable subsystem claims.

- source: `substrates/bn_syn/README_CLAIMS_GATE.md`
  target: `docs/evidence_ledgers/bnsyn_claims_gate.md`
  classification: REQUIRED_MIGRATION
  why: explicit claims gate contract.
  risk_if_omitted: weakened scientific governance.

- source: `substrates/kuramoto/docs/requirements/traceability_matrix.md`
  target: `docs/traceability/kuramoto_traceability_matrix.md`
  classification: REQUIRED_MIGRATION
  why: load-bearing requirement-to-implementation map.
  risk_if_omitted: impossible safety/compliance reconciliation.

- source: `substrates/kuramoto/data/golden/**`
  target: `data/golden/kuramoto/**`
  classification: REQUIRED_MIGRATION
  why: reproducibility anchors.
  risk_if_omitted: benchmark non-replayability.

6. OPTIONAL_HIGH_VALUE_MIGRATION
- `agents/manuscript/**` -> `docs/science/agents/**` -> OPTIONAL_HIGH_VALUE -> preserves derivations and result narratives.
- `substrates/mlsdm/docs/adr/**` -> `docs/adr/mlsdm/**` -> OPTIONAL_HIGH_VALUE -> architectural decision memory.
- `substrates/kuramoto/docs/adr/**` -> `docs/adr/kuramoto/**` -> OPTIONAL_HIGH_VALUE -> cross-subsystem design rationale.
- `substrates/bn_syn/specs/coq/**` -> `formal/coq/bnsyn/**` -> OPTIONAL_HIGH_VALUE -> formal methods continuity.
- `substrates/bn_syn/specs/tla/**` -> `formal/tla/bnsyn/**` -> OPTIONAL_HIGH_VALUE -> protocol/state invariants.
- `substrates/mlsdm/artifacts/evidence/**/manifest.json` -> `evidence/mlsdm/manifests/**` -> OPTIONAL_HIGH_VALUE -> release evidence lineage.

7. DO_NOT_MIGRATE
- `substrates/mfn_plus/artifacts/release/scenarios/runs/**` -> NOISE (bulk run outputs; keep only indexed manifests/summaries).
- `substrates/mlsdm/docs/archive/reports/**` -> ARCHIVE_ONLY (historical reports, non-authoritative).
- duplicated decorative assets (`**/header.svg`, banner variants beyond one canonical set) -> NOISE.
- CI-generated logs/temp caches (`.import_linter_cache`, transient benchmark dumps) -> NOISE.
- any unindexed raw notebook checkpoints or ad-hoc outputs under `artifacts/**` without manifest linkage -> ARCHIVE_ONLY.

8. AUTHORITY_CONFLICTS
- Conflict A:
  competing: `bn_syn/` vs `substrates/bn_syn/`
  surviving_authority: `substrates/bn_syn/`
  why: full proof/tests/governance stack lives there.

- Conflict B:
  competing: `substrates/mfn_plus/` vs `substrates/mycelium/`
  surviving_authority: `substrates/mycelium/`
  why: same package identity; must retain one canonical owner.

- Conflict C:
  competing: root README narrative vs substrate-specific READMEs claiming independent canon
  surviving_authority: root for meta-contract; each substrate README scoped as subsystem-local only.
  why: current wording implies multiple canonical entrypoints.

- Conflict D:
  competing licenses: root AGPL, `agents` MIT, `kuramoto` proprietary label
  surviving_authority: UNKNOWN until legal packaging boundary file is added.
  why: current aggregate repo has mixed licensing boundaries.

9. MISSING_INTELLECTUAL_CAPITAL_RISKS
- Missing unified bibliography index across root/substrates/agents.
- Missing canonical evidence manifest registry at repo root.
- Missing explicit ontology/invariant registry linking `contracts/`, substrate schemas, and claim ledgers.
- Missing single proof-of-proofs index for generated artifacts with retention policy.
- Missing canonical owner map for duplicated Mycelium/MFN+ code lines.
- UNKNOWN: external repos still holding unique notebooks/datasets; no import ledger present.

10. REPO_ENTROPY_REPORT
- Duplication: high (`mfn_plus` vs `mycelium`, BN-Syn dual surfaces).
- Drift: high (independent product-grade subrepos aggregated without normalization).
- Orphan artifacts: medium-high (`evidence/.gitkeep`, many artifact trees without global index).
- Contract fragmentation: high (root contracts + substrate-specific governance contracts).
- Benchmark fragmentation: high (golden data and benchmark harnesses distributed by substrate).
- Documentation fragmentation: very high (multiple README/ADR/evidence hierarchies).
- Scientific proof fragmentation: high (proof bundles local, no global provenance spine).
- Operator-surface fragmentation: high (multiple CLIs, multiple "first command" narratives).

11. EXACT_NEXT_ACTIONS
- action 1: Add `CANONICAL_OWNERSHIP.yaml` at root: subsystem owner, scope, authoritative paths, deprecation paths.
- action 2: Freeze conflict B by selecting surviving owner (`mycelium`) and opening mechanical migration PR from `mfn_plus`.
- action 3: Freeze conflict A by migrating root `bn_syn/*.py` into `substrates/bn_syn` adapter namespace and deprecating root duplicate.
- action 4: Create root `evidence/registry.json` listing every admissible evidence artifact with hash + source subsystem.
- action 5: Add root `LICENSE_BOUNDARIES.md` and enforce CI check for mixed-license path boundaries.
- action 6: Partition root pytest collection: remove `.` from root `testpaths`; add matrix jobs per subsystem.
- action 7: Create root `governance/MIGRATION_LEDGER.md`; mark UNKNOWN gaps and block archival until resolved.
- action 8: Consolidate bibliography and claim ledgers into `docs/bibliography/` and `docs/evidence_ledgers/` with backlink checks.
- action 9: Add `REPO_TOPOLOGY.md` with subsystem graph, API boundaries, and adapter contracts.
- action 10: Archive-only prune policy for raw run outputs; keep manifest-backed summaries only.

12. ARCHIVE_READINESS_VERDICT
NOT_READY
conditions:
- resolve authority conflicts A/B/C/D,
- complete REQUIRED_MIGRATION inventory and migrations,
- publish global evidence registry + import ledger,
- enforce hermetic CI partition by subsystem,
- establish legal/license boundary documentation.

13. SUMMARY
Repository contains significant intellectual capital but is architecturally multi-canonical, not singular. Root Neosynaptex runtime and contracts form one coherent core, while BN-Syn, TradePulse/Kuramoto, MLSDM, neuron7x-agents, and Mycelium/MFN+ remain semi-independent systems with their own manifests, CI, and governance surfaces. Highest-risk issue is split authority: duplicate package ownership (`mfn_plus` vs `mycelium`) and dual BN-Syn surfaces (`bn_syn/` vs `substrates/bn_syn/`) create non-deterministic maintenance and archival risk. Proof, benchmark, and bibliography assets are rich but fragmented; no unified root evidence spine exists. Mixed license regimes across subtree packages further block canonical archival decisions. Immediate value is preserved by locking ownership, migrating duplicated surfaces into single authorities, centralizing evidence/claim ledgers, and partitioning CI/test/dependency boundaries per subsystem. Until these migrations and governance artifacts are completed, old-repo archival is unsafe and canonical-repo status is not achieved.


14. IMPLEMENTED_BOOTSTRAP_ARTIFACTS
- `CANONICAL_OWNERSHIP.yaml`
- `LICENSE_BOUNDARIES.md`
- `evidence/registry.json`
- `governance/MIGRATION_LEDGER.md`
- `REPO_TOPOLOGY.md`

15. SHIELD_HARDENING
- STATUS: COMPLETE
- DATE: 2026-04-13
- LOCATION: `tests/falsification/test_shield_hardening.py`
- TESTS_ADDED: 4 adversarial tests (+ 5 parametrized/auxiliary cases = 9 collected)
- FAILURE_MODES_COVERED: A, B, C, D
  - A — Circular construction: AST walk of every `substrates/*/adapter.py`
    flags any `thermo_cost` body that calls `self.topo()`. Adapters that
    own gamma outside the protocol (via `get_gamma_result` /
    `compute_gamma`) are recorded as protocol-compatibility-shim
    exemptions and logged by name so they cannot quietly multiply.
    Current exemptions: `eeg_physionet`, `eeg_resting`, `hrv_fantasia`
    (all derive gamma directly from per-subject DFA / aperiodic
    exponents; the circular `thermo_cost = 1/topo` is vestigial and
    never touches the reported gamma).
  - B — Data leakage: `observe()` is called twice with an RNG-level
    perturbation in between; the reported gamma must differ and the
    adapter must carry no `gamma` or `_gamma_cached` attribute.
  - C — Window gaming: synthetic stream with known `gamma_true = 1.0`
    is run through `core.gamma.compute_gamma` at window in
    {8, 16, 32, 64}; every recovered gamma must lie in [0.80, 1.20]
    and their std across {8, 16, 32, 64, 128} must be < 0.15.
  - D — Adversarial injection: an adapter providing `gamma = 1.0`,
    `_gamma_cached = 1.0`, `_compute_gamma()` returning 1.0, and a
    `"gamma"` key in its state dict is registered with `gamma_true`
    of 0.5 in its (topo, cost) stream; the engine must report ~0.5
    and never 1.0. A structural AST check further asserts the engine's
    `observe()` body contains no `adapter.gamma` attribute access.
- FULL-SUITE STATUS: 802 passed, 20 skipped, 0 failed (~5 min local).
