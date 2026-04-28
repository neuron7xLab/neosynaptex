# Recursive claim refinement architecture

> **claim_status: derived** — this document formalises the recursive evidence-refinement architecture that already governs NeoSynaptex; it makes no new scientific claim.

## 1. Purpose

This document is an **architectural model** of how NeoSynaptex turns substrate output into admissible scientific claims. It is a **process specification**, not new theory. Every statement here either restates an existing repository invariant or names a gate already enforced in code (`contracts/`, `tools/audit/`, the BN-Syn evidence path, the γ-pipeline, the canon ledger).

The model exists for one reason: to prevent claim accumulation from masquerading as claim validation. Substrates produce evidence; only the recursive gate structure converts evidence into a **claim status**.

## 2. Claim ladder

NeoSynaptex recognises exactly four discrete claim states. They are totally ordered by evidence strength:

```
NO_ADMISSIBLE_CLAIM
        ↓
ARTIFACT_SUSPECTED
        ↓
LOCAL_STRUCTURAL_EVIDENCE_ONLY
        ↓
VALIDATED_SUBSTRATE_EVIDENCE
```

- **NO_ADMISSIBLE_CLAIM** — a required input, metric, file, or invariant is missing or invalid. The system refuses to speak.
- **ARTIFACT_SUSPECTED** — surrogate / null-control evidence indicates the signal is likely an artifact. The system flags it as such.
- **LOCAL_STRUCTURAL_EVIDENCE_ONLY** — local substrate-level evidence passes; γ-side evaluation is absent, declined, or deferred.
- **VALIDATED_SUBSTRATE_EVIDENCE** — both local and γ-side evidence pass independently.

The ladder is monotonic but **not automatic**: every step requires positive evidence. Failure of any required gate downgrades the claim, never silently upgrades it.

## 3. Recursive loop

The repository implements one canonical refinement cycle:

```
substrate output
    → adapter (typed contract; refuses fabrication)
    → evidence contract (validated_metrics, non_claims, sanitiser)
    → gates (provenance, determinism, surrogate, γ-pipeline)
    → verdict (one of the four ladder states)
    → downgrade / preserve / upgrade
    → next substrate
```

Each substrate enters this loop through the same fixed structure. The loop is **recursive in the substrates**, not in the gates: the gates are immutable; the population of substrates is what grows.

Restructure ≠ accumulate. New substrate evidence does **not** add a fresh column of claims; it forces the shared verdict to be re-evaluated under the same gate structure. A new substrate may strengthen the model (raise the ladder), downgrade the claim (lower the ladder), or falsify the path entirely (block escalation).

## 4. BN-Syn position

BN-Syn is a **local structural-evidence substrate**. It contributes exactly four observables:

| observable                  | role                                         |
|-----------------------------|----------------------------------------------|
| κ (branching-criticality)   | local critical proxy; not γ                  |
| avalanche distribution + fit| power-law tail evidence                      |
| phase coherence             | global synchrony scalar                      |
| surrogate / proxy verdict   | weak null-rejection (avalanche-fit-based)    |

BN-Syn does **not** emit γ. The adapter explicitly raises `NotImplementedError` for `topo()` and `thermo_cost()`.

## 5. κ ≠ γ invariant

Branching criticality (κ) and metastability scaling (γ) are **distinct observables on distinct measurement spaces**:

- κ is computed per timestep from local activity statistics; its critical value is `κ ≈ 1` for branching processes.
- γ is the metastability scaling exponent obtained from a separate population-level synchronisation pipeline; its critical value (`γ ≈ 1.0`) is what NeoSynaptex authors as the gamma-side claim.

Equality of numerical values (e.g. both being near 1) is **not** identity of observables. Treating κ as γ would conflate two unrelated measurement chains and inject the BN-Syn local proxy directly into the γ-claim surface — exactly the failure mode this architecture exists to block.

The invariant is enforced **structurally**, not by review:

```python
# substrates/bnsyn_structural_adapter.py
def topo(self): raise NotImplementedError(...)
def thermo_cost(self): raise NotImplementedError(...)
```

Any C/K projection from BN-Syn into the γ-pipeline is a refused operation.

## 6. Fail-closed criticality

Each of the following blocks claim escalation:

1. Missing required bundle file → `NO_ADMISSIBLE_CLAIM`.
2. NaN / non-finite metric → `NO_ADMISSIBLE_CLAIM`; the strict-JSON sanitiser converts the value to `null` and `json.dump(..., allow_nan=False)` enforces RFC 8259 compliance on the evidence ledger.
3. Provenance missing (`run_manifest.json` absent or empty) → cap at `LOCAL_STRUCTURAL_EVIDENCE_ONLY`.
4. Determinism failure (replay non-identical) → cap at `LOCAL_STRUCTURAL_EVIDENCE_ONLY`.
5. Surrogate / proxy verdict not in admissible set → `ARTIFACT_SUSPECTED`.
6. C/K fabrication attempt from a non-γ substrate → adapter refuses with `NotImplementedError`.

There is no escape hatch and no override flag in the public surface. A failed gate is permanent for that bundle.

## 7. VALIDATED requirements

`VALIDATED_SUBSTRATE_EVIDENCE` is reachable **only** when **all** of the following are simultaneously true on the same bundle:

- local structural pass (`local_pass = True`),
- provenance pass,
- determinism pass,
- surrogate / null evidence admissible,
- caller supplies `gamma_pass=True` from the **external** NeoSynaptex γ-pipeline.

The importer alone has no path to `VALIDATED_SUBSTRATE_EVIDENCE`. The default `gamma_pass=None` keeps the verdict capped at `LOCAL_STRUCTURAL_EVIDENCE_ONLY` regardless of how strong the local evidence is.

## 8. Recursive refinement

The system does **not** accumulate claims. It **restructures** them.

Two substrates with overlapping observables produce one shared verdict, evaluated under the same gate structure. Three outcomes are possible:

- **Strengthen**: both substrates pass independently → shared verdict moves up the ladder.
- **Downgrade**: one substrate fails → shared verdict drops to the lower bound.
- **Falsify**: a substrate exposes a structural inconsistency (e.g. a previously-passed gate now fails on shared input) → escalation path is blocked until the inconsistency is resolved.

Concretely, the unit of progress is **gate-pass under shared invariants**, not substrate count. A repository with ten substrates and one passing γ-pipeline outranks a repository with a hundred substrates and no γ-pipeline.

## 9. Non-claims

This document explicitly does **not**:

- prove γ ≈ 1.0;
- validate BN-Syn scientifically;
- prove consciousness, AGI, biological equivalence, or cross-substrate universality;
- promote any claim to a higher ladder state;
- modify any gate logic, claim threshold, or measurement contract.

It defines architecture only. All scientific claims continue to require the gates, the γ-pipeline, and the existing canon-ledger evidence chain.

## 10. Integration rule

Any future substrate (mycelial, synthetic, neuromorphic, simulated, biological, or other) **must** enter the same recursive structure:

1. Define a typed evidence contract (`contracts/<substrate>_evidence.py`) with explicit `non_claims`.
2. Implement a fail-closed adapter that refuses any observable it cannot honestly emit.
3. Provide a method-definition gate (Gate 0) that proves the substrate's intended observables can be defined within NeoSynaptex's existing measurement spaces. If the gate cannot be proven, the substrate enters at `BLOCKED_BY_METHOD_DEFINITION` and no data is admitted.
4. Pass through the canonical gate sequence: provenance → determinism → surrogate → local pass → γ-pipeline (external).
5. Emit verdicts only through the canonical claim ladder.

No substrate may bypass these steps. No substrate may project its local proxy onto γ. No substrate may upgrade its own verdict.

---

*This architecture is descriptive of the existing NeoSynaptex repository state and prescriptive for all future substrate integrations. It does not introduce new theory and does not change existing claim logic.*
