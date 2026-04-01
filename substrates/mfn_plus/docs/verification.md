# Verification

## Local Verify Pipeline

```bash
bash ci.sh
```

This runs 6 gates in sequence (stops on first failure):

| Gate | What | Command |
|------|------|---------|
| 1 | Lint | `ruff check` on bio/ + analytics/ + core/ |
| 2 | Types | `mypy --strict` on bio/ (15 files) |
| 3 | Core tests | 170+ tests across bio, Levin, fractal, unified engine |
| 4 | Canonical reproduce | `experiments/reproduce.py` — deterministic output vs baseline |
| 5 | Adversarial | `experiments/adversarial.py` — invariants across 50+ seeds |
| 6 | Import contracts | `lint-imports` — 8/8 boundary contracts |

## Adversarial Invariants

The adversarial run checks 6 invariants:

1. **Determinism**: same seed = identical field (bitwise)
2. **NaN/Inf safety**: 50 random seeds, no NaN/Inf in any field or history
3. **Causal gate validity**: 20 seeds, all outputs have valid labels/scores/bounds
4. **Shape invariants**: grid sizes 8-64, field shape always matches spec
5. **Bounded metrics**: 10 seeds through UnifiedEngine, all metrics in valid ranges
6. **Perturbation stability**: nearby seeds produce consistent labels (3/5 majority)

## Makefile Targets

```bash
make reproduce    # Run canonical reproduction only
make adversarial  # Run adversarial validation only
make verify       # Lint + types + reproduce + adversarial + import contracts
make localci      # Full local CI equivalent (bash ci.sh)
```
