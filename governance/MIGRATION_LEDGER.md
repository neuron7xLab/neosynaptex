# External Repo Import Ledger

## Purpose
Fail-closed record of technical memory that may still live outside this monorepo.

## Status Key
- IMPORTED: fully ingested and mapped.
- PARTIAL: some assets ingested; gaps remain.
- UNKNOWN: no verified inventory yet.
- BLOCKER: prevents archival.

## Ledger

| External Source (expected) | Domain | Current Status | Required Assets | Blocker Reason |
|---|---|---|---|---|
| neuron7xLab/neuron7x-agents | agents | IMPORTED | agents/ fully integrated, DNCA bridge operational (core/dnca_bridge.py) | — |
| neuron7x/bnsyn-phase-controlled-emergent-dynamics | BN-Syn | IMPORTED | substrates/bn_syn/ is surviving authority, adapter.py wired | — |
| neuron7x/TradePulse | kuramoto/tradepulse | IMPORTED | substrates/kuramoto/ integrated, golden data pending | operational reproducibility risk |
| neuron7xLab/mlsdm | mlsdm | IMPORTED | substrates/mlsdm/ fully ingested with tests | — |
| private experiment repos | cross-substrate | PENDING_INVENTORY | notebooks, datasets, prompts, pipeline scripts | requires manual audit of local dirs |

## Archival Gate
Legacy repo archival is forbidden while any row is `UNKNOWN` or `BLOCKER`.
