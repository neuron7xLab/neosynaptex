# NeoSynaptex Repository Topology (v2.0)

## Architecture Overview

```
neosynaptex/
├── neosynaptex.py          ← Single-file engine (1200 LOC, all γ computation)
├── core/                   ← Infrastructure (21 modules, 3500 LOC)
├── contracts/              ← Invariants + truth criterion
├── substrates/             ← Independent γ witnesses (8 substrates)
├── evl/                    ← Evidence Verification Ledger
├── experiments/            ← Reproducible experiment outputs
├── tests/                  ← 370+ tests, 29 test files
├── scripts/                ← 13 operational scripts
├── evidence/               ← gamma_ledger.json + proof chains
├── data/golden/            ← Benchmark anchors
├── docs/                   ← Science, manuscripts
├── formal/                 ← Coq/TLA+ specifications
├── agents/                 ← Agent subsystem
└── .github/workflows/      ← CI (4 workflows, all green)
```

## Substrate Map

| Substrate | Package | γ | Status | Source |
|-----------|---------|---|--------|--------|
| Zebrafish | `substrates/zebrafish/` | 1.055 | VALIDATED | McGuirl 2020 .mat data |
| Gray-Scott | `substrates/gray_scott/` | 0.979 | VALIDATED | PDE simulation, F-sweep |
| Kuramoto | `substrates/kuramoto/` | 0.963 | VALIDATED | 128-oscillator Kc sim |
| BN-Syn | `substrates/bn_syn/` | 0.946 | VALIDATED | 1/f spiking network |
| CNS-AI | `substrates/cns_ai_loop/` | 1.059 | CONSTRUCTED | Cognitive loop sim |
| CFP/ДІЙ | `substrates/cfp_diy/` | 1.832 | CONSTRUCTED | ABM, 25 AI-quality regimes |
| HRV | `substrates/hrv/` | −0.306 | CONSTRUCTED | Synthetic 1/f RR |
| Lotka-Volterra | `substrates/lotka_volterra/` | −1.103 | CONSTRUCTED | Competition dynamics |

## Core Modules

| Module | Purpose |
|--------|---------|
| `axioms.py` | γ_PSD = 2H+1, regime classification |
| `adapter_registry.py` | Auto-discovery of substrate adapters |
| `coherence_bridge.py` | JSON-RPC API surface |
| `falsification.py` | Automated falsification logic |
| `gamma_registry.py` | Read-only gateway to gamma_ledger.json |
| `evidence_pipeline.py` | Collect → validate → register → query |
| `granger_multilag.py` | Cross-substrate causality |
| `block_bootstrap.py` | Bootstrap CI computation |
| `iaaft.py` | Surrogate generation (amplitude-adjusted FFT) |
| `rqa.py` | Recurrence quantification analysis |
| `value_function.py` | Value estimation |
| `multiverse.py` | Multi-parameter sensitivity |

## Experiments

| Experiment | Path | Key Finding |
|------------|------|-------------|
| Scaffolding Trap | `experiments/scaffolding_trap/` | dskill/dt = 0.02 × gap × effort, delegation −9.5%/10% |
| LM Substrate | `experiments/lm_substrate/` | Stateless γ≈0 (null), coupled chain pending |

## CI Workflows

| Workflow | Jobs | Status |
|----------|------|--------|
| NFI CI | lint, typecheck, verify×3, invariants, coverage, canonical-gate, ci-gate | GREEN |
| Security | bandit SAST, pip-audit, gitleaks | GREEN |
| CodeQL | SAST analysis | GREEN |
| Benchmarks | Performance regression | GREEN |

## Contracts

- `γ derived only, never assigned` — enforced by gamma_registry.py + AST tests
- `STATE ≠ PROOF` — CRR state ≠ topology law proof
- `SSI external only` — external measurement, no hidden state inference
- `Bounded modulation` — CPR drift triggers recalibration

## Evidence Chain

```
gamma_ledger.json → gamma_registry.py → neosynaptex.py (read-only)
                  → evidence_pipeline.py (append-only)
                  → proof_chain.jsonl (immutable log)
```

## Resolved Conflicts (2026-04-01)

1. `bn_syn/` vs `substrates/bn_syn/` — root is deprecated re-export shim
2. `mfn_plus/` vs `mycelium/` — mycelium is surviving authority
3. Kuramoto license — AGPL-3.0-or-later
4. CRR as metric — invalidated for ordered curricula, replaced by dskill/dt
