# Experiments

Reproducible experimental outputs from NFI substrate validation.

## Index

| Experiment | Status | Key Result |
|------------|--------|------------|
| [scaffolding_trap](scaffolding_trap/) | Complete | dskill/dt = 0.02 × gap × effort (R²=0.9999) |
| [lm_substrate](lm_substrate/) | Complete | γ ≈ 0 (null — stateless API not a substrate) |

## Scaffolding Trap

ABM simulation (100 agents, 21 AI regimes) demonstrating that:
1. CRR is invalid for ordered curricula (measurement artifact)
2. dskill/dt is the clean learning rate metric
3. Delegation suppresses learning: −9.5% per 10% delegation
4. The law is linear: dskill/dt = α × gap × effort

## LM Substrate

GPT-4o-mini logprob analysis (200 prompts × 2 conditions):
- Stateless calls → γ ≈ 0 (white noise, no temporal structure)
- Feedback chain → γ ≈ 0 (API context window is stateless)
- Confirms CFP thesis: γ ≠ 0 requires closed-loop dynamics
