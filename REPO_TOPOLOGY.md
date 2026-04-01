# NeoSynaptex Canonical Target Topology (v1.0)

## Root Authority Spine
- `CANONICAL_OWNERSHIP.yaml` — owner/authority contract.
- `LICENSE_BOUNDARIES.md` — path-scoped licensing contract.
- `REPO_TOPOLOGY.md` — architectural authority map.
- `core/` + `contracts/` + root `tests/` — integration contract runtime.

## Substrate Layer (Single Owner Per Package)
- `substrates/bn_syn/` — surviving authority for BN-Syn.
- `substrates/mfn/` — target surviving authority for MFN/Mycelium merge.
- `substrates/kuramoto/` — Kuramoto/TradePulse stack.
- `substrates/mlsdm/` — ML-SDM stack.
- `substrates/ca1/` — CA1-LAM (target rename from `substrates/hippocampal_ca1/`).
- `substrates/zebrafish/`, `substrates/gray_scott/`, `substrates/cns_ai_loop/` — thin adapters.

## Shared Verification and Evidence
- `verification/kriterion/` — shared verification schemas migrated from agents.
- `evidence/registry.json` — global admissible evidence index.
- `governance/MIGRATION_LEDGER.md` and `governance/ARCHIVE_POLICY.md` — archival gates.
- `data/golden/` and `formal/` — benchmark anchors and formal artifacts.

## Consolidated Documentation
- `docs/science/` — manuscripts (root + agents).
- `docs/bibliography/` — unified bibliography index.
- `docs/evidence_ledgers/` — BN-Syn claims gate + MLSDM evidence ledger.
- `docs/traceability/` — Kuramoto requirement traceability matrix.
- `docs/adr/` — architecture decision records (MLSDM + Kuramoto).
- `formal/coq/` + `formal/tla/` — BN-Syn formal specifications.

## Resolved Conflicts (2026-04-01)
1. ~~`bn_syn/` vs `substrates/bn_syn/`~~ — root `bn_syn/` is now a deprecated re-export shim.
2. ~~`mfn_plus/` vs `mycelium/`~~ — `mycelium/` confirmed as surviving authority; `mfn_plus/` deprecated.
3. ~~Kuramoto license~~ — set to AGPL-3.0-or-later.
4. Root README already frames meta-contract correctly (Conflict C: no action needed).
