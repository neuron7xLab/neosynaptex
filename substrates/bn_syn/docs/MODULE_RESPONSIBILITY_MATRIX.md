# Module Responsibility Matrix

This matrix maps implementation modules to responsibilities, entrypoints, and operational invariants.

| Module / Path | Responsibility | Primary entrypoints | Key invariants |
| --- | --- | --- | --- |
| `src/bnsyn/cli.py` | Command-line interface for simulation and utility commands. | `main()` | CLI commands must be deterministic for fixed seeds and config. |
| `src/bnsyn/config.py` | Typed parameter/config structures for simulation components. | parameter models and defaults | Parameter contracts must remain schema-stable and validated. |
| `src/bnsyn/simulation.py` | High-level simulation orchestration wrapper. | simulation runner functions | No hidden randomness outside controlled RNG injection. |
| `src/bnsyn/neurons.py`, `src/bnsyn/neuron/adex.py` | AdEx neuron dynamics primitives and step rules. | neuron update APIs | Numerical updates must preserve model domain constraints. |
| `src/bnsyn/synapses.py`, `src/bnsyn/synapse/conductance.py` | Conductance synapse dynamics and receptor components. | synapse update APIs | Conductance state must remain finite and non-negative where required. |
| `src/bnsyn/plasticity/three_factor.py` | Three-factor plasticity and eligibility traces. | plasticity update functions | Plasticity updates must follow configured bounds and traces. |
| `src/bnsyn/criticality/branching.py` | Branching ratio estimation and criticality tracking. | detector/estimator APIs | Sigma estimation pipeline remains deterministic for fixed streams. |
| `src/bnsyn/temperature/schedule.py` | Temperature schedule and phase gating logic. | schedule update APIs | Temperature trajectory follows configured schedule semantics. |
| `src/bnsyn/connectivity/sparse.py` | Sparse connectivity construction/utilities. | connectivity builders | Graph structure generation is reproducible with fixed seed. |
| `src/bnsyn/rng.py` | Seed and random generator utilities. | `seed_all` and helpers | Same seed returns equivalent generator streams per backend. |
| `src/contracts/math_contracts.py` | Math-level contract checks for validated constraints. | contract assertion functions | Contract checks fail closed on violated invariants. |
| `scripts/*.py` | Operational gates, audits, benchmarks, and validation automation. | `python -m scripts.<name>` | CI scripts must fail non-zero on detected policy/quality drift. |

For architecture narrative context, see [ARCHITECTURE.md](ARCHITECTURE.md).
