# DFP-COMPACT: Documentation Formalization Protocol (Operational)

## Overview

This protocol defines standards for formalizing documentation according to linguistic science and ISO/IEC/IEEE standards. Use this guide when creating or reviewing documentation for MyceliumFractalNet.

**Version**: 1.0.0  
**Last Updated**: 2025-12-18  
**Standard References**: ISO/IEC/IEEE 26511, ISO/IEC/IEEE 26512

---

## Core Principles

### Cognitive

- Chunk content into 7±2 items per section
- Integrate related information
- Eliminate redundancy

### Pragmatic (Grice's Maxims)

| Maxim | Requirement |
|-------|-------------|
| Quantity | Provide sufficient information, no more |
| Quality | Verify all claims before inclusion |
| Relevance | Include only pertinent content |
| Clarity | Write unambiguous prose |

### Structural

- Use a single Diátaxis document type per document
- Apply Toulmin argument structure for claims
- Use explicit transitions between sections

### Linguistic

- Active voice for procedures (mandatory)
- 20-25 word maximum sentence length
- One term equals one concept (no synonyms)

---

## Diátaxis Decision Matrix

Use this matrix to determine the correct document type based on user intent.

|               | PRACTICAL        | THEORETICAL      |
|---------------|------------------|------------------|
| **LEARNING**  | TUTORIAL         | EXPLANATION      |
|               | "Follow me"      | "Understand why" |
| **WORKING**   | HOW-TO           | REFERENCE        |
|               | "Achieve goal"   | "Look up fact"   |

### Quick Selection Guide

| User Need | Document Type | Key Characteristic |
|-----------|---------------|-------------------|
| Learn a new skill | Tutorial | Steps ≤7 per section, verify each step |
| Solve a specific problem | How-To | Goal first, minimal theory |
| Understand a concept | Explanation | Toulmin argument structure |
| Look up specifications | Reference | Complete, no tutorial content |
| Document an AI model | Model Card | 9 sections, disaggregated metrics |
| Record a decision | ADR | Options with rationale |

---

## Document Templates

### Tutorial Template

Use for teaching new skills through guided practice.

```markdown
# [Tutorial Title]

## Learning Objectives

By the end of this tutorial, you will:

1. [Measurable objective 1]
2. [Measurable objective 2]
3. [Measurable objective 3]

## Prerequisites

- [Prerequisite 1]
- [Prerequisite 2]

## Steps

### Step 1: [Action]

1. [Action instruction]
2. [Action instruction]

**Result**: [Expected outcome]

**Checkpoint**: [Verification method]

### Step 2: [Action]

...

## What You Learned

- [Learning outcome 1]
- [Learning outcome 2]

## Next Steps

- [Suggested next tutorial or resource]
```

### How-To Template

Use for solving specific problems with step-by-step instructions.

```markdown
# How to [Achieve Goal]

## Goal

[One sentence describing the goal]

## Prerequisites

- [Requirement 1]
- [Requirement 2]

## Steps

1. [Imperative action]

   ```code
   [Example code]
   ```

   **Verify**: [Verification step]

2. [Imperative action]

   ...

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| [Issue 1] | [Root cause] | [Fix] |
| [Issue 2] | [Root cause] | [Fix] |

## Related Guides

- [Link to related how-to 1]
- [Link to related how-to 2]
```

### Explanation Template

Use for explaining concepts and providing context.

```markdown
# [Concept Name]

## Context

[Why this concept matters and when you need it]

## Concept

### Claim

[Main assertion about the concept]

### Grounds

[Evidence supporting the claim]

**Source**: [Citation]  
**Strength**: strong | moderate | weak

### Warrant

[Why the grounds support the claim]

### Backing

[Why the warrant is valid]

### Qualifier

certainly | presumably | probably | possibly

### Rebuttal

Unless [condition that would invalidate the claim]

## Elaboration

[Examples, analogies, and detailed explanation]

## Implications

[Consequences and applications of understanding this concept]

## Connections

- [Related concept 1]
- [Related concept 2]
```

### Reference Template

Use for technical specifications and API documentation.

```markdown
# [API/Feature Name]

## Synopsis

[One paragraph summary of functionality]

## Signature

```python
def function_name(
    param1: type,  # Description
    param2: type   # Description
) -> return_type:
    ...
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | `type` | Yes | [Description] |
| `param2` | `type` | No | [Description] |

### Returns

| Type | Description |
|------|-------------|
| `return_type` | [Description] |

### Errors

| Error | Condition |
|-------|-----------|
| `ValueError` | [When raised] |
| `TypeError` | [When raised] |

## Description

[Detailed semantics and behavior]

## Examples

```python
# Minimal example
result = function_name(value1, value2)
```

## See Also

- [Related reference 1]
- [Related reference 2]
```

### Model Card Template

Use for documenting machine learning models.

```markdown
# Model Card: [Model Name]

## 1. Model Details

- **Organization**: [Organization name]
- **Version**: [Version number]
- **Type**: [Model type/architecture]
- **Date**: [Release date]
- **License**: [License type]

## 2. Intended Use

### In-Scope Uses

- [Primary use case 1]
- [Primary use case 2]

### Out-of-Scope Uses

- [Inappropriate use 1]
- [Inappropriate use 2]

## 3. Factors

### Relevant Demographics/Domains

- [Factor 1]
- [Factor 2]

## 4. Metrics

| Metric | Threshold | Actual |
|--------|-----------|--------|
| [Metric 1] | [Target] | [Value] |
| [Metric 2] | [Target] | [Value] |

## 5. Evaluation Data

- **Dataset**: [Dataset name]
- **Size**: [Number of samples]
- **Preprocessing**: [Description]

## 6. Training Data

- **Dataset**: [Dataset name]
- **Size**: [Number of samples]
- **Preprocessing**: [Description]

## 7. Quantitative Analyses

### Disaggregated Results

| Subgroup | Metric | Value |
|----------|--------|-------|
| [Group 1] | [Metric] | [Value] |
| [Group 2] | [Metric] | [Value] |

## 8. Ethical Considerations

- [Consideration 1]
- [Consideration 2]

## 9. Caveats and Recommendations

- [Caveat 1]
- [Recommendation 1]
```

---

## Toulmin Argument Template

Use for supporting claims with structured reasoning.

```
CLAIM: [Assertion to be proven]

  GROUNDS: [Evidence supporting the claim]
    Source: [Citation or reference]
    Strength: strong | moderate | weak

  WARRANT: [Principle explaining why grounds support claim]

  BACKING: [Evidence that the warrant is valid]

  QUALIFIER: certainly | presumably | probably | possibly

  REBUTTAL: Unless [condition that invalidates the claim]
```

### Example

```
CLAIM: MyceliumFractalNet achieves production-grade performance.

  GROUNDS: Benchmark tests show 200x speedup over baseline.
    Source: docs/MFN_PERFORMANCE_BASELINES.md
    Strength: strong

  WARRANT: Performance exceeding baseline by >10x indicates
           production readiness for real-time applications.

  BACKING: Industry standard defines production-grade as
           meeting latency requirements with margin.

  QUALIFIER: certainly

  REBUTTAL: Unless hardware specifications differ significantly
            from benchmark environment.
```

---

## CER Scientific Claims

Use Claim-Evidence-Reasoning (CER) format for scientific statements.

```
CLAIM: [Testable statement]

EVIDENCE: [Quantified data with source]

REASONING: [Scientific principle connecting evidence to claim]
```

### Example

```
CLAIM: The Nernst potential calculation is accurate.

EVIDENCE: Computed K+ potential is -89.01 mV, matching
          the physiological reference value of -89 mV
          (source: Hille, B. Ion Channels of Excitable Membranes).

REASONING: The Nernst equation E = (RT/zF)ln([ion]out/[ion]in)
           correctly models equilibrium membrane potential
           for a single ion species.
```

---

## Linguistic Rules

### Procedures

| Rule | Requirement |
|------|-------------|
| Voice | Active (mandatory) |
| Sentence length | ≤20 words |
| Structure | One action per sentence |
| Verb position | First word or after subject |

**Example**:  
✓ "Run the test suite."  
✗ "The test suite should be run."

### Descriptions

| Rule | Requirement |
|------|-------------|
| Voice | Active preferred, passive permitted |
| Sentence length | ≤25 words |
| Structure | One topic per paragraph |

### Terminology

| Rule | Requirement |
|------|-------------|
| Synonyms | Forbidden (one term = one concept) |
| Acronyms | Define as "Full Name (ACRONYM)" on first use |
| Definitions | Inline on first use or link to glossary |

**Example**:  
✓ "Spike-Timing-Dependent Plasticity (STDP) modulates..."  
✗ "STDP modulates..." (undefined on first use)

### Transitions

Use explicit transition words between sections and ideas.

| Type | Words |
|------|-------|
| Additive | additionally, furthermore, also |
| Contrast | however, nevertheless, conversely |
| Causal | therefore, consequently, because |
| Sequence | first, then, finally, subsequently |

---

## Quality Checklist

Before submitting documentation, verify each item.

- [ ] Single Diátaxis type (no mixing)
- [ ] All claims have Toulmin structure
- [ ] Readability: grade ≤10 (procedures ≤8)
- [ ] Passive voice: ≤15% (procedures: 0%)
- [ ] Terminology consistent throughout
- [ ] All acronyms defined on first use
- [ ] Cross-references valid
- [ ] Procedures have verification steps

---

## Input Format

Use this YAML format when requesting documentation formalization.

```yaml
content: |
  [Raw content to formalize]

type: tutorial | howto | explanation | reference | model_card | adr

audience: developer | researcher | user | stakeholder

domain: [your domain]

constraints:
  grade_level: 10
  sentence_max: 25
```

---

## Output Format

Formalized documentation returns in this format.

```yaml
document: |
  [Formalized content]

metadata:
  type: [classified type]
  readability_grade: [float]
  word_count: [int]

issues:
  - location: [section]
    severity: error | warning
    description: [text]
    fix: [suggestion]
```

---

## Activation

To request documentation formalization, use this format:

```
[DFP] type={type} audience={audience}

{content}
```

### Example

```
[DFP] type=howto audience=developer

Install MyceliumFractalNet on Ubuntu 22.04.
```

---

## Quality Targets

| Quality Metric | Target Value |
|----------------|--------------|
| Grade level | ≤10 (procedures ≤8) |
| Sentence length | ≤25 words |
| Passive voice | ≤15% |
| Terms per concept | 1 |

---

## References

- ISO/IEC/IEEE 26511:2018 - Requirements for managers of information
- ISO/IEC/IEEE 26512:2018 - Requirements for acquirers and suppliers
- Diátaxis Documentation Framework - https://diataxis.fr/
- Toulmin Model of Argumentation - Stephen Toulmin, 1958
- Grice's Cooperative Principle - H.P. Grice, 1975
