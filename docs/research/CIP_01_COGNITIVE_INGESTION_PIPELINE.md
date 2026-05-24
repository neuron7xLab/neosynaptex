# CIP-01 · Cognitive Ingestion Pipeline

claim_status: derived

## Status

- **Protocol ID:** `CIP-01`
- **Parent protocol:** `NEOSYNAPTEX-PROTOCOL-v1.1`
- **Status:** PROPOSED / INTEGRATION-READY
- **Scope:** перетворення зовнішнього аудіо/текстового потоку на перевірювані research-engineering артефакти.
- **Non-claim:** цей документ не стверджує біологічну тотожність із нейропластичністю або синаптичним прунінгом. Ці терміни використовуються як операційна аналогія для routing, retention і pruning у людсько-LLM контурі.

---

## 1. Problem

Стохастичні потоки знання з подкастів, лекцій, діалогів і голосових фрагментів швидко втрачаються або перетворюються на шум, якщо не проходять через явний контур: capture → hypothesis → protocol gate → artifact → CI trace.

## 2. Falsification Condition

`CIP-01` спростовується як корисний механізм, якщо захоплений фрагмент не може бути:

1. перетворений на falsifiable hypothesis;
2. прив’язаний до checklist ID або value-function mapping;
3. збережений як артефакт із provenance;
4. перевірений або відкинутий протягом TTL;
5. пов’язаний з PR/CI trace або явно видалений як noise.

Якщо хоча б один із цих пунктів системно не виконується, pipeline виробляє інформаційний шум, а не інженерну цінність.

---

## 3. Contract

### Inputs

- `audio_stream`: transient voice/audio stream.
- `raw_text`: transcript generated from the audio stream.
- `source_context`: optional source metadata such as title, timestamp, URL, speaker, or local note.
- `operator_intent`: short human-selected reason for capturing the fragment.

### Outputs

- `hypothesis_candidate`: falsifiable claim candidate.
- `classification`: one of `ACCEPT`, `REJECT`, `ENTROPY`, `QUARANTINE`.
- `target_artifact`: proposed destination such as `01_problem.md`, `04_test_plan.md`, `06_change_plan.md`, issue, PR note, or kill-artifact.
- `provenance_record`: source, timestamp, capture mode, model/tool used, and operator note.

### Required metadata

```yaml
protocol_id: CIP-01
claim_status: derived
source_type: audio|video|dialogue|note
capture_mode: voice_to_text|manual_excerpt|transcript_import
operator_intent: string
created_at_utc: iso8601
classification: ACCEPT|REJECT|ENTROPY|QUARANTINE
ttl_hours: 48
linked_pr: integer|null
linked_ci_run: string|null
```

---

## 4. Pipeline

### 4.1 Ingestion Phase — Stochastic Capture

**Goal:** capture the smallest meaningful external signal without pretending that the transcript is already knowledge.

```text
Voice / Audio → Raw Transcript → Candidate Segment
```

**Constraints:**

- Do not preserve filler words unless they alter meaning.
- Do not preserve emotional noise as evidence.
- Do not store sensitive or private content without explicit need.
- Do not treat transcript text as verified fact.
- Do not import long copyrighted passages; summarize and cite/record source metadata where available.

### 4.2 Distillation Phase — Semantic Filtering

Each captured segment is compressed into a falsifiable hypothesis using two mandatory prompts:

```text
Context: Which system invariant or value function does this strengthen?
Falsification: How would we prove this fragment has no engineering value?
```

The result must map to at least one of:

- `PRE-01`: falsifiable hypothesis;
- `VAL-01`: red/green evidence;
- `SEM-01`: semantic validity;
- `ARCH-01`: first-principles/value-function mapping;
- `GOV-03`: CI failure mapping;
- a documented negative result / kill-artifact.

If no mapping exists, mark as `ENTROPY`.

### 4.3 Protocol Alignment Gate

```text
IF violates FP-01 Contract-before-implementation → REJECT
IF strengthens VF-01 correctness → ACCEPT or QUARANTINE for validation
IF lacks falsification condition → ENTROPY
IF useful but not actionable now → QUARANTINE with TTL
```

A model may propose the mapping, but the operator remains the final gate. LLM consensus is not falsification evidence.

### 4.4 Persistence & TTL

- `ACCEPT`: integrate into a target artifact with provenance.
- `QUARANTINE`: store temporarily with TTL and reason.
- `REJECT`: preserve only if it is useful as a negative result.
- `ENTROPY`: delete or ignore.

Default TTL:

```yaml
ttl_hours: 48
```

If a quarantined item is not linked to a PR, issue, CI trace, or accepted research artifact within TTL, it is pruned.

---

## 5. Invariants

```yaml
invariants:
  - id: CIP-01-PRE-01
    metric: falsifiable_hypothesis_presence
    pass_condition: hypothesis_candidate contains falsification_condition

  - id: CIP-01-SEM-01
    metric: semantic_mapping_presence
    pass_condition: candidate maps to at least one checklist_id or value_function

  - id: CIP-01-GOV-01
    metric: human_gate_preserved
    pass_condition: operator_decision is required before artifact integration

  - id: CIP-01-ART-01
    metric: provenance_record_presence
    pass_condition: provenance_record has source_type, capture_mode, created_at_utc, operator_intent

  - id: CIP-01-PRUNE-01
    metric: ttl_enforcement
    pass_condition: unlinked_quarantine_items older than ttl_hours are pruned or converted to negative-result artifacts
```

---

## 6. Implementation Logic

```python
def ingest_cognition(audio_stream, source_context, operator_intent):
    raw_text = transcribe(audio_stream)
    segment = extract_candidate_segment(raw_text)

    hypothesis = distill(
        segment,
        prompts=[
            "Which system invariant or value function does this strengthen?",
            "How would we prove this fragment has no engineering value?",
        ],
    )

    if not hypothesis.has_falsification_condition:
        return mark("ENTROPY", reason="missing_PRE_01")

    mapping = map_to_protocol(hypothesis, targets=["PRE-01", "SEM-01", "ARCH-01", "VAL-01", "GOV-03"])
    if not mapping:
        return mark("ENTROPY", reason="no_protocol_mapping")

    if violates_first_principle(hypothesis, "FP-01"):
        return mark("REJECT", reason="contract_before_implementation_violation")

    artifact = propose_artifact(hypothesis, mapping)
    decision = operator_gate(artifact)

    if decision == "ACCEPT":
        return persist_with_provenance(artifact)

    if decision == "QUARANTINE":
        return persist_with_ttl(artifact, ttl_hours=48)

    return mark("REJECT", reason="operator_rejected")
```

---

## 7. Validation Plan

### Positive test

Given a captured transcript fragment that contains a clear engineering insight, the pipeline must produce:

- one falsifiable hypothesis;
- one protocol/checklist mapping;
- one proposed artifact destination;
- one provenance record.

### Negative controls

The pipeline must reject or mark as `ENTROPY`:

- emotionally intense but non-actionable fragments;
- quotes without system relevance;
- claims with no falsification condition;
- model-generated agreement without external grounding;
- transcript noise with no artifact destination.

### Adversarial cases

- transcript contains a persuasive but false claim;
- transcript contains private/sensitive content;
- transcript contains copyrighted long-form text;
- transcript maps to multiple checklist IDs but no concrete artifact;
- LLM proposes acceptance without falsification.

Expected behavior: `QUARANTINE` or `REJECT`, never silent integration.

---

## 8. Integration Targets

`CIP-01` may write into:

- `docs/research/01_problem.md` when the fragment defines a better problem/falsification condition;
- `docs/research/04_test_plan.md` when it creates a validation or adversarial case;
- `docs/research/06_change_plan.md` when it changes implementation order;
- PR body when it maps a CI failure to `GOV-03`;
- a negative-result artifact when it falsifies a tempting but invalid idea.

`CIP-01` must not write directly into implementation code without an accepted contract artifact.

---

## 9. Governance

- Human operator remains the final decision gate.
- LLM output is candidate inference, not authority.
- No artifact is promoted without falsification boundary.
- No transcript becomes evidence without provenance.
- No quarantined note survives past TTL without PR/CI/artifact linkage.

Rollback path:

```text
Remove CIP-01 artifact → remove associated generated notes/reports → revert PR commit.
```

---

## 10. Summary

`CIP-01` converts ambient learning into a bounded engineering loop. It does not claim that hearing equals understanding or that transcription equals knowledge. It enforces a stricter rule:

```text
captured signal → falsifiable hypothesis → protocol mapping → human gate → artifact or pruning
```

This is the operational form of semantic capture: not hoarding information, but forcing every captured fragment to earn its place in the system.
