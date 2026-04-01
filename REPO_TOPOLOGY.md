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

## Known Current Conflicts
1. `bn_syn/` (root adapter) vs `substrates/bn_syn/` (full authority).
2. `substrates/mfn_plus/` vs `substrates/mycelium/` split package identity.
3. Mixed license zones unresolved for `substrates/kuramoto/`.
