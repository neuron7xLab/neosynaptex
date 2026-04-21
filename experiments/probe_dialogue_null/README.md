# Why the dialogue γ-probe failed the AT battery

**Status:** archived null result. No substrate adapter is shipped from
this experiment. Kept here as a guide rail: future attempts at a
dialogue criticality substrate should avoid the same mistake.

## Hypothesis

The hypothesis was that `K(t) ~ C(t)^(-γ)` — with `K` a cumulative
lexical/semantic observable and `C` a cumulative token count —
would detect edge-of-chaos dynamics in human–AI dialogue, mirroring
the way neosynaptex extracts γ on BN-Syn spike trains, Kuramoto phase
ensembles, and HRV recordings. Two operationalisations were tested:

- **v1 (lexical)** — `topo = |unique-tokens-seen-so-far|`,
  `thermo_cost = cumulative token count`.
- **v2 (entropy)** — `topo = Σ_t H(turn_t)` with `H` the Shannon
  entropy of the per-turn word distribution, same cumulative
  `thermo_cost`.

Both were guarded by the four-test anti-tautology (AT) battery
(shuffle, lexical surrogate, piecewise stability, leave-one-turn-out).

## Result

**0/5 real Claude Code human–AI sessions passed the AT battery under
either v1 or v2.**

| session (24 turns) | v1 γ | v1 passed | v2 γ | v2 passed |
|---|---:|:---:|---:|:---:|
| 28fde1cc… | NaN | ✗ | −0.125 | ✗ (I+O) |
| 466f89b5… | NaN | ✗ | −0.408 | ✗ (I+O+S) |
| 77629f4f… | −1.255 | ✗ (T+S) | −0.992 | ✗ (T+I+S) |
| 9d66f9d3… | −1.612 | ✗ (S) | −1.023 | ✗ (T+S) |
| b8d6eef2… | NaN | ✗ | −0.231 | ✗ (O) |

Flag legend: T tautology (shuffle-invariant), I instability
(piecewise split drifts), O outlier (single turn dominates),
S surrogate (random content reproduces γ).

Raw evidence: [`at_report_v1.json`](at_report_v1.json),
[`at_report_v2.json`](at_report_v2.json).

## Root cause — architectural, not a tuning problem

Both adapters use **cumulative** observables. By construction the
resulting `(topo(t), thermo_cost(t))` trajectory is monotonic: it is
a one-way curve in log-log space that trivially admits a power-law
fit regardless of the underlying dialogue structure. The AT battery
correctly detects this as a tautology:

- **Shuffle-invariance (T flag)** — permuting turn order leaves the
  final cumulative sums unchanged; γ does not move.
- **Surrogate-insensitivity (S flag)** — random content with the
  same per-turn token counts reproduces γ within noise, because
  `thermo_cost` depends only on token counts and `topo` saturates
  or grows near-linearly either way.

Contrast with the existing working substrates:

| substrate | topo | instantaneous? | γ theoretical anchor |
|---|---|:---:|---|
| BN-Syn | windowed firing rate | yes | σ = 1 branching (Beggs-Plenz 2003) |
| Kuramoto | order parameter r(t) | yes | K_c from phase distribution |
| HRV | RR-interval variability in window | yes | mono-/multi-fractal scaling |
| Lotka-Volterra | biomass | yes | attractor-geometry prediction |
| **probe (this)** | **cumulative vocab / entropy** | **no** | **none** |

All working substrates observe quantities that can **rise and fall**
within a sliding window. γ there is the *dynamic* relationship
between two fluctuating signals. A monotonic cumulative sum collapses
that dynamic into a line; there is no fluctuation to scale.

## Deeper gap: no theoretical γ for dialogue

BN-Syn's γ ≈ 1 is not guessed — it is derived from the critical
branching ratio σ = 1 (mean-field directed percolation universality
class). Kuramoto's K_c has an analytical form. HRV is anchored in
decades of multi-fractal literature.

Dialogue has **no such prediction**. Reporting a γ number on
conversation data, without a derivation for what value to expect,
would be nomenclature without content — the AT battery is generous
to show this early.

## Conclusion

A valid dialogue substrate for the neosynaptex engine would need:

1. A **windowed, non-monotonic** topo observable (e.g. a
   type/token-ratio in the last K turns, an information-rate
   estimate, a graph density in the recent topic network) so that
   γ can reflect dynamic rather than cumulative behaviour.
2. A **theoretical anchor** for what γ should be — for example a
   Zipf-like prediction for turn-level word-frequency tails
   (Miller 1957, Zipf 1935) or a Beggs-Plenz–style avalanche-size
   distribution for topic-shift cascades.

Neither condition was satisfied by v1 or v2. Future work is out of
scope for this archive; the instrument (neosynaptex core and all
existing substrates) is unchanged.

## What this archive contains

- `README.md` — this file.
- `at_report_v1.json` — AT battery output on 5 real Claude Code
  sessions with the lexical adapter.
- `at_report_v2.json` — same 5 sessions with the entropy adapter.

Closed PR: [#144](https://github.com/neuron7xLab/neosynaptex/pull/144).
Related existing null result: `experiments/lm_substrate/`
(γ = −0.094, p = 0.626 on stateless GPT-4o-mini).
