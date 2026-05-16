# DOPA-VALIDITY-001 — Repo Audit

Authoritative status: `evidence/dopa_closure/RETRACTION.md`. PR #198/#199 are
RETRACTED, `KILL-0979` is void, **DOPA-CLOSURE is UNTESTED, not killed**. This
audit answers only: *what real material exists to build an admissible test?*

## Where is real DNCA/dopamine signal available?

| location | content | executable? |
|---|---|---|
| `agents/src/neuron7x_agents/dnca/neuromodulators/dopamine.py` → `DopamineOperator` | TD prediction error `δ = r + γ·V(s_t) − V(s_{t-1})`, Schultz asymmetric gain, signed `valence` + gained `dopamine_signal` | **YES** — imports under `torch 2.5.1`; `neuron7x_agents` is pip-installed editable; forward verified |
| `core/dnca_bridge.py` → `DncaBridge` | transports gamma/regime/neuromod between DNCA and engine; bounded \|Δ\|≤0.05 | yes, but it is a *bridge*, carries no RPE of its own |
| `substrates/kuramoto/.../dopamine_controller.py` | market-feed dopamine TD controller | separate substrate; not the DNCA cognitive operator |

The DNCA dopamine signal **is executable** — Step A of the gate genuinely
passes. This is the decisive difference from #199, which used sklearn TF-IDF.

## Which signal can become signed vRPE?

`DopamineOperator.modulate(...)["valence"] = clamp(δ, −1, 1)` — the
**pre-asymmetric**, sign-preserving TD error. The asymmetric-gained
`dopamine_signal` is *not* used as vRPE: its ×5.5/×1.0 gain distorts sign
symmetry and is unsuited to a true sign-flip control. The negative control
negates this signed scalar (`vRPE → −vRPE`), never a `|vRPE|` complement
(that function-substitution was an explicit #199 invalidator).

## Which task can define Verified Closure beyond accuracy?

No existing neosynaptex asset ties dopamine vRPE to a verification-benefit
signal with a closure event distinct from accuracy. `core/hallucination_benchmark.py`
is a synthetic ΔS *classifier* scored by **plain accuracy** — reusing it as VCR
would be metric collapse (forbidden). DOPA-VALIDITY-001 therefore ships a
**minimal deterministic arithmetic-closure micro-task**: Verified Closure = an
independent verifier spends a budgeted action and returns a definitive
VERIFIED/REFUTED bound to an evidence hash under a fixed boundary. VCR counts
closure events, not policy correctness.

## Which verifier is admissible?

`core/eai/external_verification.py::run_local_command` is the right *shape* of
admissible verifier (argv-list, `shell=False`, network disabled, hash-bound
report) but needs a task whose claims are command-verifiable. The scaffold uses
a pure-recomputation verifier of the same admissibility class: deterministic,
network-free, **accuracy 1.0 ≫ majority ≈ 0.52 ≫ random 0.5** — admissible by
construction (Step B1 passes).

## What is missing?

1. A **truth-correlated vRPE** (RETRACTION precondition #3). The shipped
   `DopamineOperator.value_net` is *untrained*; its δ over inference features is
   not yet shown to correlate with verification benefit. This is the binding
   gap: Step B2 fails today → verdict `INADMISSIBLE_WEAK_VERIFIER`.
2. A real (non-arithmetic) hallucination/truthfulness corpus with
   command-verifiable Verified Closure.
3. A trained or theoretically-anchored value estimator before any routing read.

## Conclusion

Materials suffice to build the **admissibility machine**, not to test the
theory. The honest outcome today is a clean INADMISSIBLE — by design.
