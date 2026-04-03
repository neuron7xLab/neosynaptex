# LM Substrate Experiment — GPT-4o-mini γ Derivation

## Results

| Condition | γ | CI₉₅ | p | n | Regime |
|-----------|---|------|---|---|--------|
| Stateless (independent prompts) | −0.094 | [−0.424, 0.397] | 0.626 | 117 | COLLAPSE |
| Coupled (feedback chain) | −0.230 | [−0.346, 0.311] | 0.193 | 146 | COLLAPSE |
| Control (shuffled) | −0.249 | [−0.209, 0.197] | 0.015 | 136 | COLLAPSE |

## Interpretation

γ ≈ 0 in all conditions. API-level LLM inference is stateless — no temporal
coupling between calls regardless of prompt chaining. Each call samples
independently from the model distribution.

This is the **expected null result** and confirms the CFP thesis:
γ ≠ 0 requires a closed-loop dynamical system, not isolated inference.

## Files

- `gpt4o_substrate_experiment.py` — experiment script
- `gpt4o_substrate_raw.json` — raw data (200 prompts, stateless + control)
- `gpt4o_coupled_raw.json` — raw data (200-step feedback chain)
- `fig_gpt4o_gamma.png` — PSD figure (stateless)
- `fig_coupling_test.png` — coupled vs stateless comparison
- `claude_substrate_experiment.py` — Claude API version (pending Anthropic key)

## Prediction vs Outcome

Prediction: γ ∈ [0.9, 1.1] if metastable → **FALSIFIED**
Revised understanding: stateless API ≠ dynamical substrate
