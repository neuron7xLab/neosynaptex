# Aphasia-Broca Model Specification

**Version:** 1.3.0
**Status:** Implemented
**Last Updated:** November 23, 2025

> **Implementation Note:** As of v1.2.0, the Aphasia-Broca detection and repair functionality is now implemented as a pluggable **Speech Governor** (`AphasiaSpeechGovernor`) that integrates with the universal Speech Governance framework in `LLMWrapper`. As of v1.3.0, the system uses `PipelineSpeechGovernor` for composable, deterministic governance pipelines with failure isolation. See the [Speech Governance](#speech-governance-integration) section for details.

## Table of Contents

- [Overview](#overview)
- [Neurobiological Foundation](#neurobiological-foundation)
- [Architecture](#architecture)
- [Detection Algorithm](#detection-algorithm)
- [Integration with MLSDM](#integration-with-mlsdm)
- [Classification Criteria](#classification-criteria)
- [Correction Pipeline](#correction-pipeline)
- [Performance Characteristics](#performance-characteristics)
- [Validation](#validation)
- [Speech Governance Integration](#speech-governance-integration)

---

## Overview

The Aphasia-Broca Model is a neurobiologically-inspired component for detecting and correcting LLM-output phenotypes. It models characteristics reported for Broca's aphasia to identify when an LLM generates telegraphic, fragmented responses that lack proper grammatical structure [@asha_aphasia; @fedorenko2023_agrammatic].

## Non-Clinical Boundary

The Aphasia-Broca Model is an **LLM-output phenotype detector** inspired by clinical descriptions. It is **not** a clinical aphasia model, does **not** perform diagnosis, and must not be used for medical or therapeutic decisions.

### Key Features

- **Detection**: Identifies telegraphic speech patterns in LLM outputs
- **Classification**: Quantifies severity of aphasic characteristics
- **Correction**: Triggers regeneration with explicit grammar requirements
- **Thread-Safe**: Stateless, pure-functional design
- **Observable**: Returns structured diagnostic metadata

---

## Neurobiological Foundation

### Broca's Aphasia in Humans

**Clinical Characteristics:**

Broca's aphasia (also called expressive or non-fluent aphasia) is a language disorder associated with damage to the left inferior frontal gyrus (Broca's area, BA44/45) [@asha_aphasia; @friederici2011_brain]. The condition is characterized by [@asha_aphasia; @fedorenko2023_agrammatic]:

1. **Telegraphic Speech**: Short, simple sentences lacking grammatical complexity
2. **Preserved Comprehension**: Understanding remains largely intact
3. **Omission of Function Words**: Missing articles, prepositions, conjunctions
4. **Grammatical Structure Loss**: Difficulty with proper sentence construction (agrammatism)
5. **Semantic Preservation**: Core meaning is often conveyed despite grammatical errors

**Neural Basis:**

Broca's area serves critical functions in [@friederici2011_brain; @hickok2007_cortical]:
- Speech production motor planning
- Grammar processing and syntactic structure
- Phonological working memory
- Hierarchical sequence processing

For detailed neuroscience foundations, see [docs/NEURO_FOUNDATIONS.md](docs/NEURO_FOUNDATIONS.md#4-language-processing-and-aphasia).

**Evidence Note:** All neuroscience claims in this section are supported by canonical citations in `docs/bibliography/REFERENCES.bib`. Any uncited analogies are explicitly marked as `UNPROVEN (engineering analogy)`.

### Mapping to LLM Behavior

In LLMs, analogous patterns emerge when:

- Response consists of short, disconnected fragments
- Function words (the, is, and, of, to, etc.) are underrepresented
- Logical connections between ideas are missing
- Model conveys information but lacks proper structure
- Output appears "clipped" or incomplete

This occurs due to:
- Token budget constraints forcing brevity
- Context window limitations
- Incomplete reasoning chains
- Over-compression of information

---

## Architecture

### Three-Level Model

The Aphasia-Broca Model maps to three cognitive levels:

```
┌─────────────────────────────────────────────────────┐
│  PLAN (Semantics / Wernicke-like)                  │
│  - High-level intent formation                      │
│  - Semantic content organization                    │
│  - Context integration via QILM + Memory            │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  SPEECH (Production / Broca-like)                   │
│  - Verbalization of semantic plan                   │
│  - Grammar application via InnateGrammarModule      │
│  - Syntactic structure generation                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  DETECTOR (Aphasia-Broca)                           │
│  - Text analysis and pattern detection              │
│  - Severity quantification                          │
│  - Regeneration trigger decision                    │
└─────────────────────────────────────────────────────┘
```

### Component Roles

1. **CognitiveController**: Manages semantic planning and context
2. **ModularLanguageProcessor**: Handles speech production
3. **AphasiaBrocaDetector**: Analyzes output and triggers corrections
4. **NeuroLangWrapper**: Orchestrates the full pipeline

---

## Detection Algorithm

### Input

```python
text: str  # LLM-generated response text
```

### Analysis Steps

1. **Sentence Segmentation**
   ```python
   sentences = split_into_sentences(text)
   sentence_lengths = [len(word_tokenize(s)) for s in sentences]
   ```

2. **Function Word Analysis**
   ```python
   function_words = {'the', 'is', 'are', 'and', 'or', 'but', 'if',
                     'to', 'of', 'in', 'on', 'at', 'for', 'with', ...}
   total_words = count_words(text)
   func_word_count = count_function_words(text, function_words)
   func_word_ratio = func_word_count / total_words
   ```

3. **Fragment Detection**
   ```python
   SHORT_SENTENCE_THRESHOLD = 4
   fragments = [s for s in sentences if len(word_tokenize(s)) < SHORT_SENTENCE_THRESHOLD]
   fragment_ratio = len(fragments) / len(sentences)
   ```

4. **Metric Calculation**
   ```python
   avg_sentence_len = mean(sentence_lengths)
   ```

### Classification Thresholds

```python
MIN_SENTENCE_LENGTH = 6        # words
MIN_FUNCTION_RATIO = 0.15      # 15%
MAX_FRAGMENT_RATIO = 0.5       # 50%
```

### Severity Calculation

```python
def calculate_severity(avg_sent_len, func_ratio, frag_ratio):
    # Delta from healthy thresholds
    delta_len = max(0, MIN_SENTENCE_LENGTH - avg_sent_len)
    delta_func = max(0, MIN_FUNCTION_RATIO - func_ratio)
    delta_frag = max(0, frag_ratio - MAX_FRAGMENT_RATIO)

    # Normalized contributions
    contrib_len = delta_len / MIN_SENTENCE_LENGTH
    contrib_func = delta_func / MIN_FUNCTION_RATIO
    contrib_frag = delta_frag / MAX_FRAGMENT_RATIO

    # Average severity (capped at 1.0)
    severity = min(1.0, (contrib_len + contrib_func + contrib_frag) / 3)

    return severity
```

### Output

```python
{
    "is_aphasic": bool,              # True if any threshold violated
    "severity": float,                # 0.0 (healthy) to 1.0 (severe)
    "avg_sentence_len": float,        # Average words per sentence
    "function_word_ratio": float,     # Ratio of function words
    "fragment_ratio": float,          # Ratio of short fragments
    "flags": List[str]                # Specific violations detected
}
```

---

## Integration with MLSDM

### NeuroLangWrapper Flow

```
1. User Request
   └─> prompt: str, moral_value: float

2. Embedding Generation
   └─> event_vector = embedding_fn(prompt)

3. Cognitive Processing
   └─> CognitiveController.process_event(event_vector, moral_value)
       ├─> MoralFilter evaluation
       ├─> CognitiveRhythm phase management
       └─> Memory storage (PELM + MultiLevelMemory)

4. NeuroLang Enhancement
   └─> ModularLanguageProcessor.process(prompt)
       └─> neuro_response with grammar enrichment

5. LLM Generation
   └─> base_response = llm_generate_fn(enhanced_prompt, tokens)

6. Aphasia Detection
   └─> analysis = AphasiaBrocaDetector.analyze(base_response)
       ├─> if is_aphasic: regenerate with grammar constraints
       └─> else: accept response

7. Return
   └─> {
         "response": final_text,
         "phase": current_phase,
         "accepted": bool,
         "neuro_enhancement": str,
         "aphasia_flags": dict
       }
```

### Thread Safety

- `AphasiaBrocaDetector` is **stateless**
- All methods are **pure functions**
- No shared mutable state
- Safe for concurrent access

---

## Classification Criteria

### Healthy (Non-Aphasic) Response

**Criteria:**
- `avg_sentence_len ≥ 6` words
- `function_word_ratio ≥ 0.15` (15% or more)
- `fragment_ratio ≤ 0.5` (50% or less)

**Example:**
```
"The cognitive architecture provides a comprehensive framework for LLM governance.
It integrates multiple biological principles to ensure safe and coherent responses.
This approach has been validated through extensive testing."

Analysis:
- avg_sentence_len: 10.3 words ✓
- function_word_ratio: 0.22 (22%) ✓
- fragment_ratio: 0.0 (0%) ✓
- is_aphasic: False
- severity: 0.0
```

### Aphasic Response

**Criteria:**
- `avg_sentence_len < 6` words, OR
- `function_word_ratio < 0.15`, OR
- `fragment_ratio > 0.5`

**Example:**
```
"Architecture. Multiple principles. Safe responses. Testing done."

Analysis:
- avg_sentence_len: 2.5 words ✗
- function_word_ratio: 0.0 (0%) ✗
- fragment_ratio: 1.0 (100%) ✗
- is_aphasic: True
- severity: 0.87
- flags: ["short_sentences", "low_function_words", "high_fragments"]
```

---

## Correction Pipeline

### Regeneration Strategy

When aphasic patterns are detected, the system:

1. **Identifies the Issue**
   ```python
   if analysis["is_aphasic"]:
       # Determine specific problems
       issues = analysis["flags"]
   ```

2. **Constructs Correction Prompt**
   ```python
   correction_prompt = f"""
   Previous response was too fragmented. Please provide a complete response with:
   - Full, grammatically correct sentences
   - Proper use of conjunctions and transitions
   - All technical details preserved
   - Clear logical flow

   Original prompt: {original_prompt}
   """
   ```

3. **Regenerates Response**
   ```python
   corrected_response = llm_generate_fn(
       correction_prompt,
       max_tokens=original_tokens * 1.5  # Allow more space
   )
   ```

4. **Re-analyzes**
   ```python
   new_analysis = detector.analyze(corrected_response)
   if not new_analysis["is_aphasic"]:
       return corrected_response
   else:
       # Log warning, return best attempt
       return corrected_response  # with metadata
   ```

### Adaptive Token Allocation

```python
# If aphasic and in sleep phase
if is_aphasic and phase == "sleep":
    # Override sleep token reduction
    tokens = max_tokens  # Full allocation for correction
```

---

## Performance Characteristics

### Computational Complexity

- **Time Complexity**: O(n) where n = text length
  - Sentence splitting: O(n)
  - Word tokenization: O(n)
  - Function word counting: O(n)
  - Overall: Linear in text length

- **Space Complexity**: O(n)
  - Stores sentence list and word tokens
  - No persistent state

### Latency

| Operation | Typical Latency |
|-----------|----------------|
| analyze() for 100-word text | ~1-2ms |
| analyze() for 500-word text | ~5-8ms |
| analyze() for 1000-word text | ~10-15ms |

### Throughput

- **Single-threaded**: ~5,000 analyses/sec (short texts)
- **Parallel**: Linear scaling (stateless design)

### NeuroLang Performance Modes

The NeuroLangWrapper supports three operational modes to optimize resource usage:

#### Mode Comparison

| Mode | Training | Startup Time | Runtime Overhead | Memory | Production Use |
|------|----------|-------------|------------------|--------|----------------|
| **disabled** | None | Instant | Zero | ~50 MB | ✅ Recommended |
| **eager_train** (checkpoint) | Pre-trained | Fast (~1s) | Low | ~150 MB | ⚠️ If NeuroLang needed |
| **eager_train** (no checkpoint) | At init | Slow (~5-10s) | Low | ~150 MB | ❌ Development only |
| **lazy_train** | First call | Instant | Medium (first call) | ~150 MB | ❌ Demo/testing only |

#### Mode Descriptions

**1. Disabled Mode (Recommended for Production)**
```python
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    neurolang_mode="disabled"
)
```
- **What's included**: CognitiveController + AphasiaBrocaDetector
- **What's excluded**: NeuroLang grammar models (actor/critic/trainer)
- **Resource impact**: Minimal (~50 MB memory, instant startup)
- **Use case**: Production deployments prioritizing resource efficiency
- **Trade-off**: No recursive grammar enhancement (Aphasia detection still works)

**2. Eager Training Mode**
```python
# With pre-trained checkpoint (recommended if NeuroLang needed)
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    neurolang_mode="eager_train",
    neurolang_checkpoint_path="config/neurolang_grammar.pt"
)

# Without checkpoint (development only)
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    neurolang_mode="eager_train"
)
```
- **Training timing**: Initialization (before first request)
- **Resource impact**: High CPU/GPU during startup
- **Checkpoint option**: Skip training by loading pre-trained weights
- **Use case**: R&D, development, or production if NeuroLang enhancement required

**3. Lazy Training Mode**
```python
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    neurolang_mode="lazy_train"
)
```
- **Training timing**: First `generate()` call
- **Thread-safe**: Uses lock to train exactly once
- **Resource impact**: First request experiences 5-10s delay
- **Use case**: Demo servers, testing environments with delayed initialization

#### Creating Pre-trained Checkpoints

For production deployments using `eager_train` mode, generate checkpoints offline:

```bash
# Train models offline (3 epochs recommended)
python scripts/train_neurolang_grammar.py \
    --epochs 3 \
    --output config/neurolang_grammar.pt
```

Then configure in `config/production.yaml`:
```yaml
neurolang:
  mode: "eager_train"
  checkpoint_path: "config/neurolang_grammar.pt"
```

#### Resource Recommendations

**Low-Resource Environments (< 1 GB available):**
```yaml
neurolang:
  mode: "disabled"
```
- Provides full Aphasia-Broca functionality
- Zero NeuroLang overhead
- Suitable for serverless, edge devices, containers with memory limits

**Standard Environments (> 2 GB available):**
```yaml
neurolang:
  mode: "eager_train"
  checkpoint_path: "config/neurolang_grammar.pt"
```
- Full NeuroLang + Aphasia-Broca functionality
- Fast startup with pre-trained weights
- Best quality for recursive grammar enhancement

**Development/Research:**
```yaml
neurolang:
  mode: "eager_train"
  checkpoint_path: null  # Train from scratch
```
- Useful for model experimentation
- Not recommended for production

---

## Validation

### Test Coverage

1. **Unit Tests**: `tests/unit/test_aphasia_detector.py`
   - Healthy response detection
   - Aphasic pattern recognition
   - Severity calculation accuracy
   - Edge cases (empty text, single word, etc.)

2. **Integration Tests**: `tests/integration/test_neuro_lang_wrapper.py`
   - End-to-end pipeline with detection
   - Regeneration trigger logic
   - Metadata propagation

3. **Validation Tests**: `tests/validation/test_aphasia_detection.py`
   - Detection rate ≥80% for telegraphic samples
   - False positive rate <10% for healthy samples
   - Severity range validation [0.0, 1.0]

4. **Evaluation Suite**: `tests/eval/aphasia_eval_suite.py`
   - Corpus: `tests/eval/aphasia_corpus.json` (100 samples: 50 telegraphic + 50 normal)
   - True Positive Rate (TPR): 100% (all telegraphic detected)
   - True Negative Rate (TNR): 88% (44/50 normal correctly classified)
   - Overall Accuracy: 94%
   - Balanced Accuracy: 94%
   - Mean Severity (telegraphic): 0.885

### Key Metrics

The following metrics are **fully validated** against the repository corpus:

| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| True Positive Rate (TPR) | ≥95% | 100% | ✅ Backed |
| True Negative Rate (TNR) | ≥85% | 88% | ✅ Backed |
| Overall Accuracy | ≥90% | 94% | ✅ Backed |
| Balanced Accuracy | ≥90% | 94% | ✅ Backed |
| Mean Severity | ≥0.3 | 0.885 | ✅ Backed |

### Running the Evaluation Locally

```bash
# Run the eval suite directly (prints detailed metrics)
python tests/eval/aphasia_eval_suite.py

# Run tests with assertions (enforces thresholds)
pytest tests/eval/test_aphasia_eval_suite.py -v
```

### Corpus Characteristics

**Repository Corpus** (`tests/eval/aphasia_corpus.json`):
- **Telegraphic samples**: 50 short, fragmented texts (e.g., "Me go store now.", "Server down. Check logs.")
- **Normal samples**: 50 well-formed sentences with proper grammar and function words
- **Edge cases**: Empty text, punctuation-only, URLs, code snippets, multilingual (English, Ukrainian, Russian)

The corpus is designed to test:
- Short telegraphic phrases with missing function words
- Longer but grammatically broken sentences
- Normal sentences of varying complexity
- Edge cases that might cause false positives

### Empirical Results

**Note on Metrics**: The 87.2% reduction figure is from an internal empirical study on 1,000 LLM responses (not included in repository). The repository validation suite uses a balanced corpus for detection accuracy verification. Real-world effectiveness depends on LLM backend and prompt patterns.

**Reported Study Results** (1,000 LLM responses, v1.1.0):
- Baseline telegraphic rate: 23.4%
- With Aphasia-Broca: 3.0% (~87.2% reduction)
- Average function word ratio: 0.19 (vs 0.13 baseline)
- Average sentence length: 8.7 words (vs 5.2 baseline)

**Validation Approach**: To reproduce metrics with your LLM backend, run the detection on your own corpus and measure before/after telegraphic rates.

---

## Future Enhancements

### Planned (v1.2+)

1. **Adaptive Thresholds**
   - Learn domain-specific norms
   - Adjust based on prompt type

2. **Multi-Language Support**
   - Language-specific function word lists
   - Cultural grammar norms

3. **Finer-Grained Diagnostics**
   - Clause complexity analysis
   - Syntactic tree depth
   - Semantic coherence scoring

4. **Integration with NeuroLang Grammar**
   - Direct feedback to InnateGrammarModule
   - Recursive structure enforcement
   - Prosodic pattern analysis

---

## Speech Governance Integration

**As of MLSDM v1.2.0**, Aphasia-Broca detection and repair is implemented as a pluggable **Speech Governor** that integrates with the universal Speech Governance framework.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  LLMWrapper (Core)                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Moral Filter                                  │  │
│  │  2. Memory Retrieval (QILM + Synaptic)           │  │
│  │  3. LLM Generation                                │  │
│  │  4. Speech Governor (Optional) ◄─── NEW          │  │
│  │     └─> AphasiaSpeechGovernor                    │  │
│  │  5. Memory Update                                 │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### AphasiaSpeechGovernor

The `AphasiaSpeechGovernor` class encapsulates aphasia detection and repair logic:

```python
from mlsdm.extensions.neuro_lang_extension import (
    AphasiaBrocaDetector,
    AphasiaSpeechGovernor
)
from mlsdm.core.llm_wrapper import LLMWrapper

# Create detector
detector = AphasiaBrocaDetector(
    min_sentence_len=6.0,
    min_function_word_ratio=0.15,
    max_fragment_ratio=0.5
)

# Create governor
governor = AphasiaSpeechGovernor(
    detector=detector,
    repair_enabled=True,
    severity_threshold=0.3,
    llm_generate_fn=my_llm_function
)

# Use with LLMWrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm_function,
    embedding_fn=my_embed_function,
    speech_governor=governor  # Plug in the governor
)
```

### How It Works

1. **LLM generates draft response** → `draft_text`
2. **Speech governor is invoked** (if configured)
   - Analyzes draft with `AphasiaBrocaDetector`
   - If aphasia detected and severity > threshold
   - Triggers repair using provided LLM function
3. **Returns `SpeechGovernanceResult`**
   - `final_text`: Repaired text (or original if no repair)
   - `raw_text`: Original draft
   - `metadata`: Full aphasia report + repair status

### Benefits of Governance Approach

1. **Pluggability**: Can swap aphasia detection for other policies
2. **Composability**: Multiple governors can be chained via `PipelineSpeechGovernor`
3. **Transparency**: Full metadata about detection and repair
4. **Reusability**: Same governor works with any `LLMWrapper` instance
5. **Testability**: Governor can be unit tested in isolation
6. **Backward Compatibility**: Existing code without governor works unchanged
7. **Failure Isolation**: Failing governors don't break the entire pipeline

### Pipeline Composition

**As of MLSDM v1.3.0**, multiple speech governors can be composed into a deterministic pipeline using `PipelineSpeechGovernor`:

```python
from mlsdm.speech.governance import PipelineSpeechGovernor
from mlsdm.extensions.neuro_lang_extension import AphasiaSpeechGovernor

# Create individual governors
aphasia_governor = AphasiaSpeechGovernor(
    detector=detector,
    repair_enabled=True,
    severity_threshold=0.3,
    llm_generate_fn=my_llm_function
)

# Compose into pipeline
pipeline = PipelineSpeechGovernor(
    governors=[
        ("aphasia_broca", aphasia_governor),
        ("style_normalizer", StyleGovernor(...)),
        ("length_control", LengthGovernor(...)),
    ]
)

# Use with LLMWrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm_function,
    embedding_fn=my_embed_function,
    speech_governor=pipeline
)
```

The pipeline:
- Executes governors in the specified order
- Each governor receives the output of the previous one
- Failures are isolated: a failing governor is skipped with error logging
- All intermediate results are recorded in metadata
- Returns deterministic `speech_governance` structure

#### Pipeline Metadata Structure

When using `PipelineSpeechGovernor`, the response includes:

```json
{
  "response": "final processed text",
  "speech_governance": {
    "raw_text": "original LLM draft",
    "metadata": {
      "pipeline": [
        {
          "name": "aphasia_broca",
          "status": "ok",
          "raw_text": "text before this governor",
          "final_text": "text after this governor",
          "metadata": {
            "aphasia_report": {...},
            "repaired": true
          }
        },
        {
          "name": "style_normalizer",
          "status": "ok",
          "raw_text": "text from previous step",
          "final_text": "normalized text",
          "metadata": {"style": "formal"}
        }
      ]
    }
  }
}
```

If a governor fails:

```json
{
  "name": "failing_governor",
  "status": "error",
  "error_type": "RuntimeError",
  "error_message": "description of error"
}
```

### Migration from NeuroLangWrapper

For users of `NeuroLangWrapper`, the aphasia functionality is automatically configured via the pipeline pattern. The existing parameters work as before:

```python
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    aphasia_detect_enabled=True,   # Creates governor
    aphasia_repair_enabled=True,   # Configures repair
    aphasia_severity_threshold=0.3 # Sets threshold
)
```

Internally, `NeuroLangWrapper` creates a `PipelineSpeechGovernor` with the "aphasia_broca" step and passes it to the parent `LLMWrapper` constructor. This enables future addition of other governance steps without code changes.

### Custom Speech Policies

The governance framework enables custom linguistic policies:

```python
from mlsdm.speech.governance import SpeechGovernanceResult

class FormalnessGovernor:
    """Enforce formal language style."""

    def __call__(self, *, prompt: str, draft: str, max_tokens: int):
        # Apply formalization logic
        formal_text = self.make_formal(draft)

        return SpeechGovernanceResult(
            final_text=formal_text,
            raw_text=draft,
            metadata={"style": "formal", "changes_made": 5}
        )

wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    speech_governor=FormalnessGovernor()
)
```

See [API_REFERENCE.md](./API_REFERENCE.md#speech-governance) for complete Speech Governance documentation.

---

## References

### Scientific Foundation

For detailed neuroscience foundations and complete bibliography:
- [docs/NEURO_FOUNDATIONS.md](docs/NEURO_FOUNDATIONS.md#4-language-processing-and-aphasia) - Neuroscience foundations for language and aphasia
- [docs/SCIENTIFIC_RATIONALE.md](docs/SCIENTIFIC_RATIONALE.md) - Scientific rationale for MLSDM architecture
- [BIBLIOGRAPHY.md](bibliography/README.md) - Complete bibliography with peer-reviewed sources

### Clinical Neuroscience

**Note:** The linguistic characteristics referenced here (telegraphic speech, agrammatism, function word omission) are drawn from clinical literature [@asha_aphasia; @fedorenko2023_agrammatic]. MLSDM applies them as non-clinical heuristics for LLM output quality and does not claim diagnostic validity.

Canonical references (tracked in `docs/bibliography/REFERENCES.bib`):
- [@asha_aphasia; @fedorenko2023_agrammatic; @friederici2011_brain; @hickok2007_cortical]

### Empirical Validation

- Internal validation studies (MLSDM v1.1.0)
- Statistical analysis of 1,000+ LLM outputs
- Comparative studies across GPT, Claude, and local models
- See [EFFECTIVENESS_VALIDATION_REPORT.md](EFFECTIVENESS_VALIDATION_REPORT.md) for quantitative results

---

**Document Status:** Active
**Review Cycle:** Per minor version
**Last Reviewed:** November 23, 2025
**Next Review:** Version 1.3.0 release
