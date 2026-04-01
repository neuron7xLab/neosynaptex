# METHODOLOGY

I did not build this repository to make evaluation feel smarter. I built it to make evaluation harder to fake.

Most evaluation systems fail at the same point: the evidence runs out, but the scoring continues. Someone sees a confident candidate, a polished presentation, a clean résumé, a persuasive story, or a familiar employer name, and the evaluator silently compensates for what was never actually proved. That compensation is usually described as judgment. In practice it is uncontrolled synthesis.

I rejected that design completely.

The structural choice in this repository is evidence over eloquence. That is not a preference. It is an engineering decision about where trust is allowed to come from. Eloquence is useful only after the evidence is fixed, normalized, and bounded. Before that point, eloquence is one of the main attack surfaces. It can inflate apparent capability, disguise contribution ambiguity, smooth over missing provenance, and convert incomplete artifacts into plausible-sounding competence. The protocol therefore treats communication as secondary and traceability as primary. The candidate is free to explain. The evaluator is not free to score beyond the admissible evidence surface.

That inversion leads directly to what I call fail-closed epistemic design.

In a fail-open system, missing evidence is treated as a gap to be filled by human interpretation. In a fail-closed system, missing evidence is treated as a state that constrains what may be claimed. This repository does not assume validity and then look for reasons to keep it. It assumes non-admissibility until structure, provenance, and integrity are proved. That is why missing fingerprints, weak provenance, self-review loops, schema failures, and insufficient evidence coverage do not produce “partial confidence.” They produce caps, invalid states, or gate failure. Existing evaluation cultures often confuse flexibility with wisdom. I do not. Flexibility at the point of proof is usually where rigor dies.

The orchestration logic follows the same philosophy.

My practical method is adversarial orchestration: creator, critic, auditor, verifier. I do not treat prompt construction as a single linear instruction-writing act. I treat it as a controlled conflict between roles. The creator generates structure. The critic attacks assumptions and weak wording. The auditor checks whether the structure is internally coherent, bounded, and usable. The verifier asks a simpler question: if this were executed today by a machine or a hiring panel, what exactly would break?

That role loop maps naturally into the pipeline phases.

P1 and P2 define what counts as input and how raw material is extracted. That is the creator stage: create order from raw artifacts without inventing content.

P3 and P4 normalize and validate structure. That is the critic stage: force the object to survive schema and integrity scrutiny, not just narrative plausibility.

P5 through P7 evaluate tasks and domains under scoring constraints. That is the auditor stage: compare the evidence against explicit domain requirements, caps, and gates.

P8 through P10 classify, trace, and emit the result. That is the verifier stage: make the final object deterministic, inspectable, and resistant to retrospective reinterpretation.

I chose determinism as a design goal because the problem being solved is not expression. It is drift.

A flexible evaluator may look sophisticated, but that flexibility is often just hidden variance. Two evaluators look at the same candidate, use the same rubric, and still produce different outcomes because each silently interprets confidence, evidence sufficiency, ownership, and relevance in slightly different ways. If the framework permits that level of hidden movement, it is not audit-grade. Determinism does not mean pretending human contexts are identical. It means minimizing variance where variance is unnecessary: field order, phase order, score aggregation, gate logic, confidence caps, artifact admissibility, and output shape. The goal is not machine mystique. The goal is reproducible judgment.

The same logic drove the decision to treat prompt injection resistance as part of human capability evaluation.

Before this project, prompt injection resistance was usually framed as an AI application security problem: an agent reads hostile text and is redirected away from system intent. That is real, but it is incomplete. Human capability evaluation now happens inside contexts assembled by models, repositories, documents, tickets, notes, comments, and artifacts that may themselves contain instructions, framing language, or embedded bias. If the evaluator reads artifact text as authority rather than data, the evaluation can be redirected without anyone noticing. In this repository, artifact content is non-authoritative by default. The protocol and execution policy hold authority. The evidence is scored as data, not obeyed as instruction. That seems obvious once stated. It was missing in practice.

The point of all of this is not severity for its own sake.

The point is to build a framework where competence has to survive contact with structure. If a claim is real, it should survive canonicalization, provenance checks, evidence mapping, reviewer independence checks, anti-gaming controls, and deterministic scoring. If it does not survive, then the framework has done its job.

I would rather reject a flattering story than certify a false signal.

That is the methodology.
