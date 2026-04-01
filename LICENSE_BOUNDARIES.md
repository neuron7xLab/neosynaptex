# License Boundaries (Canonical Policy)

## Purpose
Define legal and packaging boundaries inside the monorepo to prevent cross-contamination across incompatible license zones.

## Declared Zones

| Zone | Path Prefix | Declared License Surface | Boundary Rule |
|---|---|---|---|
| Root Neosynaptex | `/` (excluding `agents/`, `substrates/kuramoto/`) | AGPL-3.0-or-later | AGPL-compatible code only in root runtime package |
| Agents | `agents/` | MIT | Keep independently distributable package boundary |
| TradePulse/Kuramoto | `substrates/kuramoto/` | AGPL-3.0-or-later | Isolated subsystem boundary |
| BN-Syn | `substrates/bn_syn/` | AGPL-3.0-or-later | Isolated subsystem boundary |
| MLSDM | `substrates/mlsdm/` | AGPL-3.0-or-later | Isolated subsystem boundary |
| Mycelium/MFN | `substrates/mfn/` target | AGPL-3.0-or-later | Single surviving package owner only |

## Mandatory Rules
1. Cross-zone imports must be adapter-mediated and explicitly documented.
2. Shared utilities across zones require declared neutral licensing and legal approval.
3. CI must fail if incompatible zone moves happen without this file update.
4. Release tooling must publish per-zone artifacts, not blended monolithic artifacts.

## Open Items (Fail-Closed)
- ~~Kuramoto final license posture~~: **RESOLVED** — AGPL-3.0-or-later (2026-04-01).
- Umbrella meta-repo distribution legal posture: **UNKNOWN**.
