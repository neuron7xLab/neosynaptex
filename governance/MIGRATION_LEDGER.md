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
| neuron7xLab/neuron7x-agents | agents | PARTIAL | benchmark raw runs, release notes, py.typed/package artifacts | provenance continuity incomplete |
| neuron7x/bnsyn-phase-controlled-emergent-dynamics | BN-Syn | PARTIAL | canonical bundle history + manifests + release hashes | claim replay risk |
| neuron7x/TradePulse | kuramoto/tradepulse | PARTIAL | golden data lineage + deployment manifests + incident records | operational reproducibility risk |
| neuron7xLab/mlsdm | mlsdm | PARTIAL | CI evidence snapshots + API baselines + governance history | governance drift risk |
| private experiment repos | cross-substrate | UNKNOWN | notebooks, datasets, prompts, pipeline scripts | unknown intellectual capital gap |

## Archival Gate
Legacy repo archival is forbidden while any row is `UNKNOWN` or `BLOCKER`.
