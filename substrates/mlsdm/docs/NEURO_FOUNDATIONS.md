# Neuroscience Foundations for MLSDM Architecture

**Document Version:** 1.0.0
**Project Version:** 1.1.0
**Last Updated:** November 2025
**Status:** Production

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Memory Systems](#2-memory-systems)
- [3. Circadian Rhythms and Sleep](#3-circadian-rhythms-and-sleep)
- [4. Language Processing and Aphasia](#4-language-processing-and-aphasia)
- [5. Neural Constraints and Homeostasis](#5-neural-constraints-and-homeostasis)
- [6. Module-Specific Foundations](#6-module-specific-foundations)
- [7. References](#7-references)

---

## 1. Overview

MLSDM architecture draws inspiration from well-established neuroscience and cognitive science principles. This document provides the biological foundations that motivate each architectural component, with explicit citations to peer-reviewed research.

**Key Principle:** MLSDM does not claim to simulate biological neurons. Instead, it adopts computational principles derived from neuroscience to achieve engineering goals (bounded resources, stable behavior, interpretability).

**Evidence Status:** Neuroscience statements in this document include inline citations to
`docs/bibliography/REFERENCES.bib`. Any uncited analogies are explicitly labeled as
`UNPROVEN (engineering analogy)` or `UNPROVEN (engineering heuristic)`.

---

## 2. Memory Systems

### 2.1 Multi-Timescale Synaptic Memory

#### Biological Background

**Synaptic Plasticity Timescales:**
Biological synapses exhibit plasticity across multiple timescales [@benna2016_synaptic]:

1. **Short-term plasticity** (milliseconds to minutes):
   - Calcium-dependent facilitation and depression
   - Presynaptic vesicle dynamics
   - Postsynaptic receptor trafficking

2. **Intermediate plasticity** (minutes to hours):
   - Protein kinase activation cascades
   - Local protein synthesis
   - Early-phase long-term potentiation (E-LTP)

3. **Long-term structural changes** (hours to years):
   - Gene transcription and protein synthesis
   - Dendritic spine growth and pruning
   - Late-phase long-term potentiation (L-LTP)

**Cascade Models:**
Fusi et al. demonstrated that synaptic complexity through cascade models enables memory lifetimes far exceeding single-state synapses [@fusi2005_cascade]. Key insights:
- Multiple metastable states buffer against noise
- Slow transitions between states provide long-term stability
- Fast initial transitions allow rapid learning

**Computational Principle:**
Multi-timescale memory consolidation balances:
- **Plasticity**: Rapid adaptation to new information
- **Stability**: Resistance to interference and catastrophic forgetting
- **Capacity**: Efficient use of limited synaptic resources

#### MLSDM Implementation

**MultiLevelSynapticMemory** (`src/mlsdm/memory/multi_level_memory.py`):

**L1 - Short-term Buffer:**
- **Decay timescale**: Hours (τ₁ ≈ 2-4 hours)
- **Capacity**: High turnover, ~100-500 entries
- **UNPROVEN (engineering analogy)**: Working memory, prefrontal cortex maintenance
- **Function**: Immediate conversational context, recent events

**L2 - Intermediate Consolidation:**
- **Decay timescale**: Days (τ₂ ≈ 1-7 days)
- **Capacity**: Moderate, ~50-200 entries
- **UNPROVEN (engineering analogy)**: Episodic memory, hippocampal-dependent consolidation
- **Function**: Recent interaction history, episodic recall

**L3 - Long-term Storage:**
- **Decay timescale**: Weeks to months (τ₃ ≈ 7-30 days)
- **Capacity**: Limited, ~20-100 critical entries
- **UNPROVEN (engineering analogy)**: Semantic memory, cortical consolidation
- **Function**: Core agent identity, stable knowledge, critical events

**Consolidation Mechanisms:**
- Replay-triggered promotion from L1 → L2 → L3
- Adaptive decay rates based on access frequency
- Priority-based eviction when capacity reached

**Scientific Grounding:**
- Architecture directly implements cascade model principles [@fusi2005_cascade]
- Timescales calibrated to agent interaction patterns (hours to weeks) rather than biological timescales (milliseconds to years)
- Consolidation logic inspired by systems consolidation theory [@benna2016_synaptic]

### 2.2 Hippocampal Replay and Memory Consolidation

#### Biological Background

**Hippocampal Replay:**
The hippocampus exhibits spontaneous reactivation of neural sequences during rest and sleep [@foster2006_reverse]:

1. **Forward replay**: Recapitulation of recent experiences
2. **Reverse replay**: Backward reactivation linking outcomes to preceding states
3. **Preplay**: Anticipatory sequences for future planning [@olafsdottir2018_replay]

**Functional Significance:**
- **Memory consolidation**: Transfer from hippocampus to neocortex [@carr2011_replay]
- **Credit assignment**: Linking actions to delayed outcomes through reverse replay
- **Planning and simulation**: Evaluating potential future trajectories
- **Memory stabilization**: Protecting recent memories from interference

**Computational Theories:**
- Complementary learning systems (CLS) theory: Fast hippocampal learning, slow cortical consolidation
- Dual-process theory: Replay supports both memory consolidation and decision-making

#### MLSDM Implementation

**Replay Mechanisms in MLSDM:**

**Trigger Conditions:**
- High-salience events (moral filter triggers, safety violations)
- Phase transitions (wake → sleep)
- Explicit consolidation requests
- Memory capacity pressure

**Replay Operations:**
- Reactivation of memory entries with priority scoring
- Promotion from short-term (L1) to long-term (L3) storage
- Association strengthening in Phase-Entangled Lattice Memory (PELM)
- Context linking for episodic coherence

**Integration with Cognitive Rhythm:**
- **Wake phase**: Sparse replay for high-priority events
- **Sleep phase**: Systematic replay for consolidation
- **Phase-dependent gating**: Different replay strategies per phase

**Scientific Grounding:**
- Replay-based consolidation mirrors hippocampal-cortical transfer [@foster2006_reverse]
- Priority-based replay consistent with salience-modulated consolidation
- Phase-dependent replay inspired by sleep-dependent memory consolidation [@carr2011_replay]

### 2.3 Phase-Entangled Lattice Memory (PELM)

#### Biological Background

**Associative Memory in Neural Systems:**
Biological memory exhibits [@hebb1949_organization; @hopfield1982_neural]:
- Content-addressable retrieval (partial cues activate full memories)
- Pattern completion and pattern separation
- Distributed representations across neural populations
- Attractor dynamics for stable memory states

**Bidirectional Associations:**
- Recurrent connectivity in cortex and hippocampus
- Hebbian learning: "neurons that fire together, wire together"
- Auto-associative networks (e.g., CA3 region of hippocampus)

#### Engineering Analog: Quantum-Inspired Memory

**Mathematical Framework:**
Masuyama et al. developed quantum-inspired associative memory models [@masuyama2014_qibam; @masuyama2018_qmam]:
- Phase-based encoding for bidirectional associations
- Self-convergent iterative retrieval
- Bounded capacity with graceful degradation
- Multi-directional mappings beyond simple key-value pairs

**Note on "Quantum-Inspired":**
MLSDM uses the term "quantum-inspired" following Masuyama et al. to indicate mathematical structures (phases, superposition-like representations) that are analogous to quantum mechanics but implemented on classical hardware [@masuyama2014_qibam]. The term "phase-entangled" in PELM similarly references phase-based associations, not quantum entanglement.

Recent work by Vallverdú & Rius further explores quantum-inspired frameworks for brain emulation, supporting the conceptual framing of phase-based cognitive memory [@vallverdu2025_neuroq].

#### MLSDM Implementation

**PELM Architecture** (`src/mlsdm/memory/phase_entangled_lattice_memory.py`):

**Core Features:**
- **Phase-based encoding**: Keys and values encoded with phase information
- **Bidirectional retrieval**: Query by key → value, or value → key
- **Bounded capacity**: Hard limits with priority-based eviction
- **Sentence-transformer backend**: Dense embeddings (384-dim) for semantic similarity

**Retrieval Mechanisms:**
- Cosine similarity for semantic matching
- Phase coherence for associative linking
- Top-k retrieval with configurable thresholds
- Context-dependent filtering

**Scientific Grounding:**
- Inspired by quantum-inspired associative memory models [@masuyama2014_qibam; @masuyama2018_qmam]
- Content-addressable retrieval consistent with hippocampal CA3 function
- Phase-based organization enables efficient context-dependent access
- Mathematical framework from quantum-inspired multidirectional associative memory [@masuyama2018_qmam]

---

## 3. Circadian Rhythms and Sleep

### 3.1 Suprachiasmatic Nucleus and Rhythm Generation

#### Biological Background

**SCN as Master Clock:**
The suprachiasmatic nucleus (SCN) generates robust ~24-hour rhythms [@hastings2018_circadian]:

1. **Cellular oscillators**: Individual SCN neurons exhibit ~24h transcriptional-translational feedback loops
2. **Network synchronization**: Gap junctions and neuropeptides (VIP, AVP) synchronize cellular clocks
3. **Environmental entrainment**: Light input via retinohypothalamic tract phase-shifts the clock
4. **Distributed outputs**: SCN coordinates peripheral clocks throughout brain and body

**Key Properties:**
- **Robustness**: Rhythm persists in constant darkness (free-running period)
- **Precision**: Network synchronization reduces period variability
- **Adaptability**: Phase-shifts in response to environmental changes
- **Hierarchical control**: SCN coordinates distributed brain clocks [@mendoza2009_clocks]

#### MLSDM Implementation

**CognitiveRhythm** (`src/mlsdm/rhythm/cognitive_rhythm.py`):

**Architecture:**
- **Period**: Configurable cycle length (default: simulated hours, not real 24h)
- **Phases**: Binary wake/sleep states with smooth transitions
- **Entrainment**: External signals can phase-shift the rhythm
- **Outputs**: Phase-dependent gating of memory and processing operations

**Wake Phase Characteristics:**
- Active processing mode
- Fresh memory retrieval emphasis
- High responsiveness
- Resource-intensive operations permitted

**Sleep Phase Characteristics:**
- Reduced throughput (gated requests)
- Consolidation and replay emphasis
- Memory reorganization
- Resource conservation

**Phase Transitions:**
- Hysteresis to prevent rapid oscillations
- Graceful degradation at boundaries
- State preservation across transitions

**Scientific Grounding:**
- Binary wake/sleep inspired by mammalian sleep-wake cycles [@hastings2018_circadian]
- Hierarchical control mirrors SCN coordination of distributed clocks [@mendoza2009_clocks]
- Period and phase-shifting mechanisms analogous to circadian entrainment

### 3.2 Sleep-Dependent Memory Consolidation

#### Biological Background

**Functions of Sleep:**
Sleep serves critical cognitive functions [@carr2011_replay; @tononi2014_sleep]:

1. **Memory consolidation**: Transfer from hippocampus to neocortex during NREM sleep [@carr2011_replay; @tononi2014_sleep]
2. **Synaptic homeostasis**: Downscaling of synaptic weights (synaptic homeostasis hypothesis) [@tononi2014_sleep]
3. **Metabolic restoration**: Clearance of metabolic waste via glymphatic system [@xie2013_glymphatic]
4. **Offline learning**: Replay-based credit assignment and model updating

**Replay During Sleep:**
- **Sharp-wave ripples**: High-frequency oscillations during NREM sleep associated with replay
- **Temporal compression**: Replayed sequences occur faster than original experience
- **Selectivity**: High-salience memories preferentially replayed [@foster2006_reverse]

**Computational Benefits:**
- Reduced interference during consolidation (offline processing)
- Integration across multiple episodes
- Schema formation and generalization
- Memory stabilization against catastrophic forgetting

#### MLSDM Implementation

**Sleep Phase Operations:**

**Consolidation:**
- Promotion of important memories from L1/L2 → L3
- Association strengthening in PELM
- Pruning of low-priority entries

**Resource Management:**
- Reduced throughput frees resources for consolidation
- Background operations without user-facing latency pressure
- Batch processing of accumulated events

**Quality Control:**
- Coherence checking across memory levels
- Duplicate detection and merging
- Integrity verification

**Scientific Grounding:**
- Offline consolidation reduces interference [@carr2011_replay]
- Priority-based replay consistent with salience-modulated sleep consolidation
- Resource efficiency mirrors metabolic restoration function of biological sleep

**Empirical Evidence:**
- 89.5% reduction in processing load during sleep phase (see `EFFECTIVENESS_VALIDATION_REPORT.md`)
- Maintained coherence across phase transitions (±5% baseline)
- Distinct memory organization by phase (wake vs. sleep storage)

---

## 4. Language Processing and Aphasia

### 4.1 Broca's Area and Speech Production

#### Biological Background

**Broca's Area (BA44/45):**
Located in the left inferior frontal gyrus, Broca's area is critical for [@friederici2011_brain; @hickok2007_cortical]:

1. **Speech production**: Motor planning for articulation
2. **Grammar processing**: Syntax and morphology
3. **Phonological working memory**: Maintaining sound sequences
4. **Sequence processing**: Hierarchical structure building

**Classic Lesion Studies:**
Damage to Broca's area produces characteristic aphasia [@asha_aphasia; @fedorenko2023_agrammatic]:
- **Telegraphic speech**: Short, simple sentences
- **Agrammatism**: Omission of function words and inflections
- **Preserved comprehension**: Understanding remains relatively intact
- **Effortful speech**: Slow, labored production
- **Semantic preservation**: Core meaning conveyed despite grammatical errors

**Neural Circuitry:**
- Dorsal stream: Broca's area → motor cortex for speech production
- Ventral stream: Inferior temporal → Broca's area for semantic processing
- Working memory: Broca's area as articulatory rehearsal component
[@hickok2007_cortical]

### 4.2 Broca's Aphasia: Clinical Characteristics

#### Linguistic Features

**Primary Symptoms:** [@asha_aphasia; @fedorenko2023_agrammatic]

1. **Reduced phrase length**: Mean length of utterance (MLU) < 4 words
2. **Low grammatical complexity**: Simple subject-verb-object structures
3. **Function word omission**: Missing articles (a, the), prepositions (in, on), conjunctions (and, but)
4. **Telegraphic quality**: "Want coffee" instead of "I want a coffee"
5. **Preserved content words**: Nouns and verbs largely intact

**Quantitative Markers (UNPROVEN — engineering heuristic):**
- Function word density: < 30% of total words (vs. ~50% in healthy speech)
- Average sentence length: < 5 words
- Grammatical complexity: Reduced subordinate clauses, conjunctions

**Comprehension Profile:** [@asha_aphasia]
- Single-word comprehension: Intact
- Simple sentence comprehension: Mostly preserved
- Complex syntax comprehension: Some deficits (e.g., passive sentences)

#### MLSDM Analogy

**LLM "Aphasic" Outputs (UNPROVEN — engineering analogy):**
Large language models occasionally produce degraded outputs resembling telegraphic speech:
- Very short responses (< 3 sentences)
- Fragmented sentence structure
- Minimal elaboration or detail
- Preserved semantic content but poor expression

**Triggers for Degraded Output (UNPROVEN — engineering heuristic):**
- Context window overflow
- Adversarial prompts
- Model uncertainty/low confidence
- Token budget constraints
- Repetition penalties causing avoidance

### 4.3 MLSDM Implementation

**AphasiaSpeechGovernor** (`src/mlsdm/speech/speech_governor.py`):

**Detection Metrics:**

1. **Token-to-Sentence Ratio**:
   - Formula: total_tokens / sentence_count
   - Threshold: < 10 tokens/sentence → suspect
   - UNPROVEN (engineering analogy): Mean length of utterance (MLU)

2. **Function Word Density**:
   - Formula: function_words / total_words
   - Threshold: < 0.20 (20%) → suspect
   - UNPROVEN (engineering analogy): Function word omission in agrammatism

3. **Average Sentence Length**:
   - Formula: mean(tokens per sentence)
   - Threshold: < 6 tokens → suspect
   - UNPROVEN (engineering analogy): Phrase length reduction

4. **Response Length**:
   - Total word count
   - Very short responses (< 20 words) flag potential issues

**Severity Classification:**
- **NONE**: All metrics normal
- **MILD**: 1 metric flagged
- **MODERATE**: 2 metrics flagged
- **SEVERE**: 3+ metrics flagged

**Corrective Action:**
- MODERATE or SEVERE → trigger regeneration
- Enhanced prompt: "Provide a detailed, grammatically complete response..."
- Explicit grammar requirements injected
- Increased token budget to avoid premature truncation

**Scientific Grounding:**
- Metrics inspired by clinical assessment summaries of Broca's aphasia [@asha_aphasia; @fedorenko2023_agrammatic]
- Quantitative thresholds are UNPROVEN (engineering heuristic)
- Self-repair mechanism is UNPROVEN (engineering analogy) to biological speech monitoring

**Limitations and Future Work:**
- Current metrics are heuristic, not linguistically sophisticated
- No deep syntactic parsing (POS tagging could improve detection)
- Language-specific tuning needed for non-English
- No modeling of Wernicke's aphasia (semantic incoherence) vs. Broca's (grammatical impairment)

---

## 5. Neural Constraints and Homeostasis

### 5.1 Homeostatic Control in Biological Systems

#### Biological Background

**Neural Homeostasis:**
Nervous systems maintain stability through multiple homeostatic mechanisms [@turrigiano2012_homeostatic]:

1. **Synaptic scaling**: Global adjustment of synaptic strengths to maintain target firing rates [@turrigiano2012_homeostatic]
2. **Intrinsic plasticity**: Regulation of neuronal excitability [@turrigiano2012_homeostatic]
3. **UNPROVEN (engineering analogy)**: Metabolic homeostasis balances energy supply and demand
4. **UNPROVEN (engineering analogy)**: Neuromodulatory control regulates global state

**Constraint Enforcement (UNPROVEN — engineering analogy):**
- **Metabolic limits**: Brain operates within ~20% of body's energy budget
- **Firing rate bounds**: Neurons maintain activity within functional ranges
- **Population homeostasis**: Excitation/inhibition balance prevents runaway activity

**Adaptive Control:**
- Set-point regulation with feedback loops
- Anticipatory control (feedforward mechanisms)
- Multi-level regulation (synaptic, cellular, circuit, systems)

#### MLSDM Implementation

**MoralFilterV2 as Homeostatic Controller** (`src/mlsdm/cognition/moral_filter_v2.py`):

**Homeostatic Variables:**
- **Moral threshold**: Adaptive set-point for acceptable moral scores
- **Drift bounds**: Maximum allowable deviation from baseline
- **Update rate**: Speed of threshold adaptation

**Control Mechanisms:**
- **Feedback**: Adjust threshold based on observed moral score distribution
- **Bounded adaptation**: Hard limits on drift prevent catastrophic threshold collapse
- **State persistence**: Thresholds persist across sessions (analogous to synaptic consolidation)

**Comparison to Neural Homeostasis:**
- Moral threshold ↔ Synaptic scaling (global adjustment)
- Bounded drift ↔ Homeostatic set-point regulation
- Adaptive update ↔ Plasticity with stability constraints

**Scientific Grounding:**
- Homeostatic control principle from neuroscience
- Engineering implementation provides formal guarantees (bounded drift)
- Analogous to physiological homeostasis but in moral/value space

### 5.2 Resource Bounds and Metabolic Constraints

#### Biological Background

**Brain Resource Constraints (UNPROVEN — engineering estimate):**
- **Energy**: ~20W power consumption, ~20% of basal metabolic rate
- **Space**: ~1350 cm³ volume, ~86 billion neurons
- **Wiring**: Physical constraints on axonal connectivity
- **Signal propagation**: Speed-of-light and ionic conduction limits

**Computational Consequences:**
- Sparse coding and efficient representations
- Local computation preferred over long-range communication
- Predictive coding to minimize surprise and metabolic cost
- Sleep for metabolic restoration and waste clearance

#### MLSDM Implementation

**Hard Resource Bounds:**

**Memory Limits:**
- Total memory: ≤ 1.4 GB (formal invariant INV-LLM-S1)
- PELM capacity: Fixed maximum entries
- MultiLevelMemory capacity: Bounded per level (L1/L2/L3)

**Computational Limits:**
- Phase-gated processing during sleep (reduced throughput)
- Circuit breaker for cascading failures
- Timeout bounds on external calls

**Eviction Strategies:**
- Priority-based eviction when capacity reached (analogous to synaptic pruning)
- Decay-based forgetting (analogous to synaptic depression)
- Least-recently-used (LRU) with salience weighting

**Scientific Grounding:**
- UNPROVEN (engineering analogy): Bounded resources mirror biological metabolic constraints
- UNPROVEN (engineering analogy): Efficient memory management inspired by neural sparse coding
- UNPROVEN (engineering analogy): Phase-dependent resource allocation mirrors sleep-wake metabolic cycles

**Empirical Validation:**
- Fixed 29.37 MB memory footprint maintained under load
- Zero capacity violations in property-based testing
- Graceful degradation under resource pressure

---

## 6. Module-Specific Foundations

### 6.1 CognitiveController: Executive Function

#### Biological Analog (UNPROVEN — engineering analogy)
Prefrontal cortex as executive controller:
- Coordinates distributed cognitive processes
- Maintains goal states and task representations
- Arbitrates between competing subsystems
- Implements cognitive control and attention

#### MLSDM Implementation
Thread-safe orchestrator coordinating:
- Moral filtering
- Rhythm management
- Memory operations
- Event processing

**Scientific Grounding:**
- UNPROVEN (engineering analogy): Centralized coordination inspired by prefrontal executive control
- UNPROVEN (engineering analogy): Modular architecture consistent with functional specialization in brain

### 6.2 MoralFilterV2: Value Alignment

#### Biological Analog (UNPROVEN — engineering analogy)
Emotion and value systems:
- Amygdala for salience and threat detection
- Orbitofrontal cortex for value representation
- Anterior cingulate cortex for conflict monitoring
- Dopaminergic system for reward prediction

#### MLSDM Implementation
Adaptive moral threshold enforcement:
- Homeostatic set-point regulation
- Bounded drift guarantees
- Observable state for auditing

**Scientific Grounding:**
- UNPROVEN (engineering analogy): Homeostatic control from neural regulation
- UNPROVEN (engineering analogy): Adaptive thresholds inspired by reward prediction and learning
- Value alignment theory from AI safety research [@gabriel2020_alignment]

### 6.3 Memory System: PELM + MultiLevel

#### Biological Analog (UNPROVEN — engineering analogy)
Hippocampal-cortical memory system:
- Hippocampus for rapid, episodic encoding
- Cortex for slow, semantic consolidation
- Replay for systems consolidation

#### MLSDM Implementation
Two-component system:
- PELM for associative, content-addressable memory
- MultiLevel for temporal, consolidation-based memory

**Scientific Grounding:**
- Multi-timescale consolidation [@benna2016_synaptic; @fusi2005_cascade]
- Hippocampal replay [@foster2006_reverse; @carr2011_replay]
- Quantum-inspired associative memory [@masuyama2014_qibam; @masuyama2018_qmam]

### 6.4 CognitiveRhythm: Circadian Control

#### Biological Analog (UNPROVEN — engineering analogy)
SCN-driven circadian system:
- Master clock synchronization
- Phase-dependent cognitive performance
- Sleep-wake transitions

#### MLSDM Implementation
Wake/sleep cycle with phase-dependent processing:
- Gated operations
- Consolidation scheduling
- Resource optimization

**Scientific Grounding:**
- SCN rhythm generation [@hastings2018_circadian]
- Distributed brain clocks [@mendoza2009_clocks]
- Sleep-dependent consolidation [@carr2011_replay]

### 6.5 AphasiaSpeechGovernor: Language Quality Control

#### Biological Analog (UNPROVEN — engineering analogy)
Broca's area and speech production:
- Grammar processing
- Motor planning
- Error monitoring

#### MLSDM Implementation
Pattern detection for telegraphic speech:
- Quantitative linguistic metrics
- Severity classification
- Regeneration with corrective prompts

**Scientific Grounding:**
- Clinical characteristics of Broca's aphasia [@asha_aphasia; @fedorenko2023_agrammatic]
- UNPROVEN (engineering analogy): Speech error monitoring in biological systems
- UNPROVEN (engineering analogy): Self-repair mechanisms

---

## 7. References

### Neuroscience - Memory

- [@benna2016_synaptic]
- [@fusi2005_cascade]
- [@foster2006_reverse]
- [@carr2011_replay]
- [@olafsdottir2018_replay]
- [@tononi2014_sleep]
- [@xie2013_glymphatic]

### Neuroscience - Circadian Rhythms

- [@hastings2018_circadian]
- [@mendoza2009_clocks]

### Quantum-Inspired Associative Memory

- [@masuyama2014_qibam]
- [@masuyama2018_qmam]
- [@vallverdu2025_neuroq]

### AI Safety and Value Alignment

- [@gabriel2020_alignment]

---

## Related Documentation

- [SCIENTIFIC_RATIONALE.md](SCIENTIFIC_RATIONALE.md) - High-level scientific rationale
- [ALIGNMENT_AND_SAFETY_FOUNDATIONS.md](ALIGNMENT_AND_SAFETY_FOUNDATIONS.md) - AI safety foundations
- [ARCHITECTURE_SPEC.md](../ARCHITECTURE_SPEC.md) - Technical architecture
- [APHASIA_SPEC.md](../APHASIA_SPEC.md) - Aphasia model specification
- [BIBLIOGRAPHY.md](bibliography/README.md) - Complete bibliography
