# NFI x SSI Protocol v2

**Status: EXECUTED | 31.03.2026**
**Author: Yaroslav Vasylenko / neuron7xLab**

## Results

| Task | Status | Tests | Commit |
|------|--------|-------|--------|
| 1. INVARIANT_IV enforcement | DONE | 7/7 | 6496290 |
| 2. Transfer Entropy engine | DONE | 4/4 | 6496290 |
| 3. Phi-Proxy | DONE | 3/3 | 6496290 |
| 4. Cell Assembly detection | DONE | 3/3 | 6496290 |
| 5. CoherenceBridge v2 | DONE | 7/7 | 6496290 |
| 6. Manuscript PRR | DONE | -- | d8578f1 |
| 7. Temporal gamma viz | DONE | -- | e609cc2 |
| 8. AXIOM_0 encoding | DONE | 6/6 | 6496290 |

**Total tests: 73/73 GREEN**

## AXIOM_0

> Intelligence is a property of the regime in which a system
> builds independent witnesses of its own error -- and remains in motion.

```
gamma = 0.994 | 6 substrates | slope = -0.0016 | CONFIRMED
```

## Invariants

| # | Name | Enforcement |
|---|------|-------------|
| I | GAMMA DERIVED ONLY | `enforce_gamma_derived()` raises `InvariantViolation` |
| II | STATE != PROOF | `enforce_state_not_proof()` raises `InvariantViolation` |
| III | BOUNDED MODULATION | `enforce_bounded_modulation()` clamps to [-0.05, +0.05] |
| IV | SSI EXTERNAL ONLY | `ssi_enforce_domain()` raises `InvariantViolation` |

## Critical Formula

```
gamma_PSD = 2H + 1    (VERIFIED, NEVER 2H-1)
H=0.5 -> gamma=2.0    (Brownian, known result)
H->0  -> gamma=1.0    (anti-persistent)
H->1  -> gamma=3.0    (persistent)
```

## File Map

```
contracts/invariants.py       4 invariants, runtime enforcement
bn_syn/transfer_entropy.py    TE engine, Granger-style
bn_syn/phi_proxy.py           Phi via TE-partition
bn_syn/cell_assembly.py       ICA + bootstrap CI95
tradepulse/coherence_bridge.py CoherenceBridge v2 (SSI.EXTERNAL)
axioms.py                     AXIOM_0 formal encoding
test_protocol_v2.py           31 tests, all green
gamma_trajectory.pdf          3-panel publication figure
coherence_bridge_demo.json    Demo output for Ali
```
