# Regime Control Contract (γ-monitor -> gate -> adaptive update)

## Problem (one sentence)
Maintain online learning near a target regime (`gamma_target`) while suppressing unstable updates under high entropy.

## Falsifiable hypothesis
If entropy is maximized (`entropy=1.0`) for sustained steps, then gate output remains non-action-dominant (`gate_signal <= 0.5`) and weight norm does not diverge under rest consolidation.

## Invariants
1. `compute_gamma` returns NaN for short/non-finite activation series.
2. `RegimeGate.gate` returns in `[0,1]` and enforces entropy threshold.
3. `adaptive_update` rejects shape mismatches and non-finite gate values.
4. `RegimeController.step` always returns structured diagnostics.

## I/O contract
- Input: `weights, grad, activations, entropy`
- Output: `(updated_weights, RegimeStepDiagnostics)`
- Numeric bounds: `entropy` clipped to `[0,1]`, gate in `[0,1]`, `learning_rate >= 0`.

## One-command run
```bash
python -m pytest tests/test_regime.py -q
```

## Rollback path
Revert commit introducing regime module changes:
```bash
git revert <commit_sha>
```


## Mathematical gating formulation

Given entropy-clipped value $e_t = clip(entropy_t, 0, 1)$ and target $\gamma^*$:

- $V_t = (\gamma_t - \gamma^*) \cdot (1 - e_t)$ if $e_t < e_{th}$ else $0$
- $g_t = \sigma(V_t - V_{t-1})$
- update: $w_{t+1} = w_t + \eta \cdot g_t \cdot \nabla w_t$
- rest decay if $g_t < r_{th}$: $w_{t+1} \leftarrow (1-\alpha) w_{t+1}$
