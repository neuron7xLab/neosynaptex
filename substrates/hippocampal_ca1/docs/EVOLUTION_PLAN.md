# 🎯 HIPPOCAMPAL-CA1-LAM: COMPLETE EVOLUTION PLAN

## PHASE 0: FOUNDATION AUDIT

### 0.1 Code Analysis
**Agent**: Code Auditor

**Tasks**:
- [ ] Map all existing components
  - [ ] `laminar_structure.py` (ZINB v1.1)
  - [ ] `hierarchical_laminar.py` (Random Effects v2.0)
  - [ ] `unified_weights.py` (W+STP+Ca²⁺)
  - [ ] `neuron_model.py` (Two-compartment)
  - [ ] `theta_swr_switching.py` (State machine)
  - [ ] `memory_module.py` (LLM integration)
- [ ] Extract all parameters (13 DOI sources)
- [ ] Document all APIs
- [ ] Identify dependencies
- [ ] Measure performance baselines

**Deliverables**:
- [ ] Complete code map
- [ ] Performance report (N=100, 1K, 10K)
- [ ] API compatibility matrix
- [ ] Dependency graph

**Exit**: Full understanding of current state

---

### 0.2 Model Comparison
**Agent**: Model Evaluator

**Tasks**:
- [ ] ZINB model validation
  - [ ] CE metric (target: ≤0.05)
  - [ ] EM convergence analysis
  - [ ] Parameter recovery tests
- [ ] Random Effects validation
  - [ ] I(L;z) metric (target: >0.1)
  - [ ] Coherence analysis
  - [ ] Spatial prior effectiveness
- [ ] Head-to-head comparison
  - [ ] Same data, both models
  - [ ] Performance vs accuracy trade-off
  - [ ] Use case analysis

**Deliverables**:
- [ ] Comparison report
- [ ] Recommendation: Keep both, merge, or choose one
- [ ] Use case matrix (when to use which)

**Exit**: Clear decision on model strategy

---

### 0.3 Baseline Establishment
**Agent**: Benchmark Engineer

**Tasks**:
- [ ] Golden tests baseline
  - [ ] Network Stability (ρ(W))
  - [ ] Ca²⁺ Plasticity (LTP/LTD)
  - [ ] Input-Specific (EC/CA3 ratio)
  - [ ] Theta-SWR (state switching)
  - [ ] Reproducibility (seed=42)
- [ ] Performance baseline
  - [ ] Time per step (N=100, 1K, 10K)
  - [ ] Memory usage
  - [ ] CPU utilization
- [ ] Biological baseline
  - [ ] Firing rate distributions
  - [ ] Phase precession
  - [ ] Replay statistics

**Deliverables**:
- [ ] Baseline report
- [ ] Regression test suite
- [ ] Performance budget (targets)

**Exit**: All baselines documented, regression tests ready

---

## PHASE 1: ATOMIC PRIMITIVES

### 1.1 Primitive Extraction Strategy
**Agent**: Architect

**Tasks**:
- [ ] Design primitive hierarchy
  - [ ] Neurons (base classes)
  - [ ] Synapses (base classes)
  - [ ] Plasticity (base rules)
  - [ ] Inference (base algorithms)
  - [ ] Connectivity (base topologies)
- [ ] Define interfaces
  - [ ] Abstract base classes
  - [ ] Required methods
  - [ ] Optional methods
  - [ ] Data structures
- [ ] Plan backward compatibility
  - [ ] Facade pattern for old API
  - [ ] Deprecation strategy
  - [ ] Migration helpers

**Deliverables**:
- [ ] Architecture Decision Records (ADRs)
- [ ] Interface specifications
- [ ] Migration plan

**Exit**: Architecture approved

---

### 1.2 Neuron Primitives
**Agent**: Neuron Specialist

**Tasks**:
- [ ] `primitives/neurons/base.py`
  - [ ] `AbstractNeuron` class
  - [ ] `step(I, dt)` method signature
  - [ ] `get_voltage()` method
  - [ ] `spike` property
- [ ] `primitives/neurons/point.py`
  - [ ] Leaky Integrate-and-Fire
  - [ ] Exponential IF
  - [ ] Adaptive Exponential IF
- [ ] `primitives/neurons/compartmental.py`
  - [ ] Generic N-compartment base
  - [ ] Cable theory
  - [ ] Compartment coupling
- [ ] `primitives/neurons/two_compartment.py`
  - [ ] Migrate from current `neuron_model.py`
  - [ ] Soma + dendrite
  - [ ] HCN gradient
  - [ ] All biophysical parameters

**Deliverables**:
- [ ] Neuron primitive library
- [ ] Unit tests per model
- [ ] Documentation + examples
- [ ] Benchmark vs current

**Exit**: Neurons work, tests pass, no regression

---

### 1.3 Synapse Primitives
**Agent**: Synapse Specialist

**Tasks**:
- [ ] `primitives/synapses/base.py`
  - [ ] `AbstractSynapse` class
  - [ ] `transmit(spike_pre, V_post)` signature
  - [ ] Conductance/current interface
- [ ] `primitives/synapses/stp.py`
  - [ ] Short-term plasticity (U, R dynamics)
  - [ ] Tsodyks-Markram model
  - [ ] Extract from `unified_weights.py`
- [ ] `primitives/synapses/calcium.py`
  - [ ] Ca²⁺ dynamics
  - [ ] Graupner-Brunel thresholds
  - [ ] Extract from `unified_weights.py`
- [ ] `primitives/synapses/composite.py`
  - [ ] Composite synapses (W + STP + Ca²⁺)
  - [ ] Migrate `UnifiedWeightMatrix`
  - [ ] Matrix operations
- [ ] `primitives/synapses/channels.py`
  - [ ] AMPA, NMDA, GABA_A
  - [ ] Voltage-dependent Mg²⁺ block
  - [ ] Kinetics

**Deliverables**:
- [ ] Synapse primitive library
- [ ] Unit tests
- [ ] Integration tests (neurons + synapses)
- [ ] Documentation

**Exit**: Synapses work, compose with neurons

---

### 1.4 Plasticity Primitives
**Agent**: Plasticity Specialist

**Tasks**:
- [ ] `primitives/plasticity/base.py`
  - [ ] `AbstractPlasticityRule` class
  - [ ] `update(pre_spikes, post_spikes, W)` signature
- [ ] `primitives/plasticity/calcium_based.py`
  - [ ] Graupner-Brunel implementation
  - [ ] θ_d, θ_p thresholds
  - [ ] LTP/LTD dynamics
  - [ ] Extract from current code
- [ ] `primitives/plasticity/spike_timing.py`
  - [ ] STDP (optional, for future)
  - [ ] Asymmetric window
- [ ] `primitives/plasticity/homeostatic.py`
  - [ ] Synaptic scaling
  - [ ] Firing rate homeostasis
  - [ ] Extract from current code
- [ ] `primitives/plasticity/input_specific.py`
  - [ ] CA3 vs EC channels
  - [ ] 10x modulation factor
  - [ ] Extract from current code
- [ ] `primitives/plasticity/olm_gating.py`
  - [ ] OLM interneuron gating
  - [ ] State-dependent modulation
  - [ ] Extract from current code

**Deliverables**:
- [ ] Plasticity rule library
- [ ] Unit tests (LTP/LTD verification)
- [ ] Integration tests (neurons + synapses + plasticity)
- [ ] Documentation

**Exit**: Plasticity rules work, reproduce golden tests

---

### 1.5 Inference Primitives
**Agent**: Inference Specialist

**Tasks**:
- [ ] `primitives/inference/base.py`
  - [ ] `AbstractInference` class
  - [ ] `infer_labels(data)` signature
  - [ ] `get_parameters()` method
- [ ] `primitives/inference/zinb.py`
  - [ ] Zero-Inflated Negative Binomial
  - [ ] EM algorithm (from v1.1 document)
  - [ ] Correct PMF: nbinom(n=θ, p=θ/(μ+θ))
  - [ ] M-step optimization via minimize
  - [ ] CE validation (≤0.05)
- [ ] `primitives/inference/random_effects.py`
  - [ ] Random effects model
  - [ ] Extract from `hierarchical_laminar.py`
  - [ ] Animal-level variance
  - [ ] I(L;z) validation (>0.1)
- [ ] `primitives/inference/mrf.py`
  - [ ] Markov Random Field spatial prior
  - [ ] Extract from `hierarchical_laminar.py`
  - [ ] Coherence improvement
- [ ] `primitives/inference/hybrid.py`
  - [ ] Combine ZINB + Random Effects + MRF
  - [ ] Best of all worlds
  - [ ] Switchable components

**Deliverables**:
- [ ] Inference library
- [ ] Both ZINB and Random Effects available
- [ ] Unit tests (parameter recovery)
- [ ] Validation tests (CE, I(L;z))
- [ ] Documentation

**Exit**: Both models work, validated against baselines

---

### 1.6 Connectivity Primitives
**Agent**: Topology Specialist

**Tasks**:
- [ ] `primitives/connectivity/base.py`
  - [ ] `AbstractConnectivity` class
  - [ ] `generate(N_pre, N_post)` signature
  - [ ] Sparse matrix support
- [ ] `primitives/connectivity/random.py`
  - [ ] Erdős-Rényi random
  - [ ] Probability-based
- [ ] `primitives/connectivity/distance.py`
  - [ ] Distance-dependent
  - [ ] Gaussian falloff
- [ ] `primitives/connectivity/structured.py`
  - [ ] Layered connectivity
  - [ ] Feed-forward/recurrent
- [ ] `primitives/connectivity/input_sources.py`
  - [ ] CA3 vs EC labeling
  - [ ] Extract from current code

**Deliverables**:
- [ ] Connectivity library
- [ ] Sparse matrix optimization
- [ ] Unit tests
- [ ] Documentation

**Exit**: Connectivity patterns work

---

### 1.7 Primitive Integration Testing
**Agent**: Integration Tester

**Tasks**:
- [ ] Compose all primitives
  - [ ] Neurons + Synapses
  - [ ] Synapses + Plasticity
  - [ ] All together in mini-network
- [ ] Test scenarios
  - [ ] 10 neurons, full composition
  - [ ] 100 neurons, reproduction of golden tests
  - [ ] 1000 neurons, performance check
- [ ] Verify backward compatibility
  - [ ] Old API still works via facade
  - [ ] Same results as v2.0
  - [ ] Golden tests: 5/5 PASSED

**Deliverables**:
- [ ] Integration test suite
- [ ] Backward compatibility tests
- [ ] Performance comparison report
- [ ] Migration guide (old → new API)

**Exit**: All primitives integrate, golden tests pass

---

### 1.8 Primitive Documentation
**Agent**: Technical Writer

**Tasks**:
- [ ] API documentation
  - [ ] Docstrings (Google style)
  - [ ] Type hints (mypy compatible)
  - [ ] Usage examples
- [ ] Architecture documentation
  - [ ] Primitive hierarchy diagram
  - [ ] Composition patterns
  - [ ] Design rationale (ADRs)
- [ ] Migration guide
  - [ ] Old vs new API
  - [ ] Code examples
  - [ ] Common patterns
- [ ] Tutorial notebooks
  - [ ] Basic usage
  - [ ] Custom primitives
  - [ ] Composition examples

**Deliverables**:
- [ ] Complete API docs
- [ ] Architecture docs updated
- [ ] Migration guide
- [ ] 3+ tutorial notebooks

**Exit**: Documentation complete, reviewable

---

## PHASE 2: FRACTAL REGIONS

### 2.1 Region Architecture
**Agent**: Region Architect

**Tasks**:
- [ ] Design fractal layer structure
  ```
  Layer (recursive):
    ├─ Neurons (population)
    ├─ Local Connectivity
    ├─ Plasticity Rules
    └─ Sub-layers (optional, fractal)
  ```
- [ ] Define region composition
  ```
  Region (CA1):
    ├─ Layer: SO (Stratum Oriens)
    ├─ Layer: SP (Stratum Pyramidale)
    ├─ Layer: SR (Stratum Radiatum)
    ├─ Layer: SLM (Stratum Lacunosum-Moleculare)
    ├─ Inter-layer connectivity
    └─ Inference model (ZINB/Random Effects/Hybrid)
  ```
- [ ] Interface design
  - [ ] `Region.encode(input)` → activity
  - [ ] `Region.decode(activity)` → output
  - [ ] `Region.infer_structure(data)` → labels

**Deliverables**:
- [ ] Region architecture spec
- [ ] Layer interface spec
- [ ] Composition rules

**Exit**: Architecture approved

---

### 2.2 Layer Implementation
**Agent**: Layer Builder

**Tasks**:
- [ ] `regions/ca1/layers/base.py`
  - [ ] `AbstractLayer` class
  - [ ] `add_neurons(model, N, params)`
  - [ ] `add_connectivity(rule, params)`
  - [ ] `add_plasticity(rule, params)`
  - [ ] `simulate(input, T, dt)`
- [ ] `regions/ca1/layers/so.py` (Stratum Oriens)
  - [ ] Pyramidal neurons (apical dendrites)
  - [ ] Local interneurons
  - [ ] Parameters from literature
- [ ] `regions/ca1/layers/sp.py` (Stratum Pyramidale)
  - [ ] Pyramidal soma layer
  - [ ] Dense packing (58,065 cells total)
  - [ ] Parameters from Pachicano 2025
- [ ] `regions/ca1/layers/sr.py` (Stratum Radiatum)
  - [ ] CA3 input zone
  - [ ] Schaffer collaterals
  - [ ] Parameters from literature
- [ ] `regions/ca1/layers/slm.py` (Stratum Lacunosum-Moleculare)
  - [ ] EC input zone
  - [ ] Perforant path
  - [ ] Parameters from literature

**Deliverables**:
- [ ] 4 layer implementations
- [ ] Unit tests per layer
- [ ] Integration tests (layers together)
- [ ] Documentation

**Exit**: Layers work independently and together

---

### 2.3 CA1 Region Assembly
**Agent**: Region Assembler

**Tasks**:
- [ ] `regions/ca1/network.py`
  - [ ] `CA1Network` class
  - [ ] Compose 4 layers
  - [ ] Inter-layer connectivity (SO↔SP↔SR↔SLM)
  - [ ] Input routing (CA3→SR, EC→SLM)
  - [ ] Output collection (SP spikes)
- [ ] `regions/ca1/inference.py`
  - [ ] Support ZINB model
  - [ ] Support Random Effects model
  - [ ] Support Hybrid model
  - [ ] Auto-selection based on data
- [ ] `regions/ca1/state_control.py`
  - [ ] Integrate `theta_swr_switching.py`
  - [ ] State-dependent dynamics
  - [ ] Theta: encoding mode
  - [ ] SWR: consolidation mode

**Deliverables**:
- [ ] Complete CA1 network
- [ ] Inference integration
- [ ] State control integration
- [ ] Golden tests: 5/5 PASSED

**Exit**: CA1 region functional, reproduces v2.0

---

### 2.4 Region Validation
**Agent**: Region Validator

**Tasks**:
- [ ] Structural validation
  - [ ] 58,065 neurons total (Pachicano)
  - [ ] Laminar distribution correct
  - [ ] Connectivity statistics match
- [ ] Functional validation
  - [ ] Firing rates (Allen Institute data)
  - [ ] Phase precession (θ phase)
  - [ ] Replay during SWR
- [ ] Inference validation
  - [ ] ZINB: CE ≤ 0.05
  - [ ] Random Effects: I(L;z) > 0.1
  - [ ] Hybrid: Best of both
- [ ] Plasticity validation
  - [ ] LTP: Ca > θ_p → ΔW > 0
  - [ ] LTD: θ_d < Ca < θ_p → ΔW < 0
  - [ ] Input-specific: EC/CA3 ratio = 10x

**Deliverables**:
- [ ] Validation report
- [ ] Biological plausibility score
- [ ] Comparison with experimental data

**Exit**: All validations pass

---

### 2.5 Future Region Scaffolds
**Agent**: Scaffold Builder

**Tasks**:
- [ ] `regions/ca3/` (placeholder)
  - [ ] `__init__.py` with interface spec
  - [ ] README: Future implementation
  - [ ] Design notes (recurrent attractor)
- [ ] `regions/ec/` (placeholder)
  - [ ] `__init__.py` with interface spec
  - [ ] README: Future implementation
  - [ ] Design notes (grid cells)
- [ ] `regions/subiculum/` (placeholder)
  - [ ] `__init__.py` with interface spec
  - [ ] README: Future implementation

**Deliverables**:
- [ ] Scaffold directories
- [ ] Interface specs
- [ ] Design documents

**Exit**: Clear path for expansion

---

### 2.6 Region Documentation
**Agent**: Region Documenter

**Tasks**:
- [ ] CA1 architecture document
  - [ ] Laminar structure
  - [ ] Neuron types
  - [ ] Connectivity patterns
  - [ ] Plasticity rules
  - [ ] Inference models
- [ ] Usage guide
  - [ ] Creating CA1 network
  - [ ] Running simulations
  - [ ] Inference on data
  - [ ] State control
- [ ] Tutorial notebooks
  - [ ] Basic CA1 usage
  - [ ] Custom layer
  - [ ] Multi-region (future)

**Deliverables**:
- [ ] Architecture documentation
- [ ] Usage guide
- [ ] Tutorial notebooks

**Exit**: Documentation complete

---

## PHASE 3: AI MEMORY ENGINE

### 3.1 Memory Architecture
**Agent**: Memory Architect

**Tasks**:
- [ ] Design memory system
  ```
  Memory System:
    ├─ Episodic Memory (events, theta-encoded)
    ├─ Semantic Memory (facts, consolidated)
    ├─ Working Memory (buffer, temporary)
    └─ Consolidation (SWR replay)
  ```
- [ ] Define memory trace
  ```
  MemoryTrace:
    ├─ Content (embedding vector)
    ├─ Context (spatial, temporal)
    ├─ Neural Pattern (CA1 activity)
    ├─ Importance (computed)
    └─ Timestamp
  ```
- [ ] Design retrieval strategy
  ```
  Retrieval:
    ├─ Query embedding
    ├─ CA3 pattern completion
    ├─ CA1 context filtering
    ├─ Theta-gated output
    └─ Ranked results
  ```

**Deliverables**:
- [ ] Memory architecture spec
- [ ] Data structures
- [ ] Retrieval algorithm spec

**Exit**: Architecture approved

---

### 3.2 Episodic Memory Implementation
**Agent**: Memory Engineer

**Tasks**:
- [ ] `ai/memory/episodic/encoder.py`
  - [ ] `encode(event, context)` → MemoryTrace
  - [ ] Theta-gated encoding
  - [ ] CA1 network integration
  - [ ] Pattern separation
- [ ] `ai/memory/episodic/consolidator.py`
  - [ ] `consolidate()` → strengthened traces
  - [ ] SWR replay simulation
  - [ ] Importance computation
  - [ ] Trace pruning (forget unimportant)
- [ ] `ai/memory/episodic/retriever.py`
  - [ ] `retrieve(query, k)` → List[MemoryTrace]
  - [ ] CA3 pattern completion
  - [ ] CA1 context matching
  - [ ] Theta-gated retrieval
  - [ ] Ranking (similarity + recency + importance)
- [ ] `ai/memory/episodic/trace.py`
  - [ ] `MemoryTrace` dataclass
  - [ ] Serialization
  - [ ] Comparison operators

**Deliverables**:
- [ ] Episodic memory system
- [ ] Unit tests
- [ ] Integration tests (with CA1)
- [ ] Documentation

**Exit**: Episodic memory works

---

### 3.3 Semantic Memory Implementation
**Agent**: Semantic Memory Engineer

**Tasks**:
- [ ] `ai/memory/semantic/knowledge_base.py`
  - [ ] `store_fact(fact, embedding)`
  - [ ] `retrieve_facts(query, k)`
  - [ ] Graph structure (concept relations)
- [ ] `ai/memory/semantic/consolidator.py`
  - [ ] `consolidate_episodes()` → facts
  - [ ] Extract patterns from episodes
  - [ ] Generalization
- [ ] Integration with episodic
  - [ ] Episode → Semantic (offline)
  - [ ] Semantic → Episode retrieval (priming)

**Deliverables**:
- [ ] Semantic memory system
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

**Exit**: Semantic memory works

---

### 3.4 Working Memory Implementation
**Agent**: Working Memory Engineer

**Tasks**:
- [ ] `ai/memory/working/buffer.py`
  - [ ] `add(item)` - Limited capacity
  - [ ] `retrieve(query)` - Fast access
  - [ ] `decay()` - Temporal decay
  - [ ] `consolidate()` → episodic memory
- [ ] Short-term dynamics
  - [ ] ~7 items capacity (Miller's law)
  - [ ] FIFO or LRU eviction
  - [ ] Integration with CA1 theta state

**Deliverables**:
- [ ] Working memory system
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

**Exit**: Working memory works

---

### 3.5 Embedding Bridge
**Agent**: Embedding Specialist

**Tasks**:
- [ ] `ai/embedding/neural_to_vector.py`
  - [ ] `encode(spike_trains)` → embedding
  - [ ] Population coding
  - [ ] Rate coding
  - [ ] Temporal coding options
- [ ] `ai/embedding/vector_to_neural.py`
  - [ ] `decode(embedding)` → input currents
  - [ ] Dimensionality mapping
  - [ ] Normalization
- [ ] `ai/embedding/adapters.py`
  - [ ] OpenAI adapter (1536 dims)
  - [ ] Claude adapter (variable)
  - [ ] Llama adapter (4096 dims)
  - [ ] Custom adapter interface

**Deliverables**:
- [ ] Embedding bridge
- [ ] Adapters for major LLMs
- [ ] Unit tests
- [ ] Documentation

**Exit**: Neural ↔ Vector conversion works

---

### 3.6 LLM Integration
**Agent**: LLM Integration Engineer

**Tasks**:
- [ ] `ai/integration/base.py`
  - [ ] `AbstractLLM` interface
  - [ ] `generate(prompt, context)`
  - [ ] `embed(text)`
  - [ ] Async support
- [ ] `ai/integration/openai_gpt.py`
  - [ ] GPT-4o implementation
  - [ ] o1 implementation
  - [ ] Streaming support
- [ ] `ai/integration/anthropic_claude.py`
  - [ ] Claude 4 Opus implementation
  - [ ] Claude 4 Sonnet implementation
  - [ ] Tool use support
- [ ] `ai/integration/meta_llama.py`
  - [ ] Llama 3.1/3.2/3.3 implementation
  - [ ] Local inference support
- [ ] `ai/integration/hippocampal_rag.py`
  - [ ] Main RAG class
  - [ ] Memory-augmented generation
  - [ ] Encode-retrieve-augment-generate loop
  - [ ] Consolidation scheduling

**Implementation Pattern**:
```python
class HippocampalRAG:
    def __init__(self, llm, ca1_network):
        self.llm = llm
        self.episodic = EpisodicMemory(ca1_network)
        self.semantic = SemanticMemory()
        self.working = WorkingMemory()
    
    async def generate(self, prompt, use_memory=True):
        # Add to working memory
        self.working.add(prompt)
        
        if use_memory:
            # Retrieve relevant memories
            episodic_memories = self.episodic.retrieve(
                self.llm.embed(prompt), k=5
            )
            semantic_facts = self.semantic.retrieve_facts(
                self.llm.embed(prompt), k=10
            )
            
            # Augment prompt
            context = self.format_context(
                episodic_memories, 
                semantic_facts
            )
            augmented_prompt = f"{context}\n\n{prompt}"
        else:
            augmented_prompt = prompt
        
        # Generate
        response = await self.llm.generate(augmented_prompt)
        
        # Store interaction
        self.episodic.encode({
            'prompt': prompt,
            'response': response,
            'timestamp': now(),
            'context': context
        })
        
        # Update working memory
        self.working.add(response)
        
        return response
    
    async def consolidate(self):
        # Offline consolidation (during "sleep")
        self.episodic.consolidate()  # SWR replay
        self.semantic.consolidate_episodes()  # Extract facts
        self.working.consolidate()  # Move to episodic
```

**Deliverables**:
- [ ] 3+ LLM integrations
- [ ] HippocampalRAG system
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end examples
- [ ] Documentation

**Exit**: LLM integrations work, RAG functional

---

### 3.7 Benchmark Suite
**Agent**: Benchmark Engineer

**Tasks**:
- [ ] `ai/benchmarks/longbench.py`
  - [ ] LongBench dataset integration
  - [ ] Evaluation metrics
  - [ ] Baseline: Vanilla RAG (FAISS)
  - [ ] Hippocampal RAG evaluation
- [ ] `ai/benchmarks/latency.py`
  - [ ] Retrieval latency tests
  - [ ] Generation latency tests
  - [ ] End-to-end latency
  - [ ] Target: <100ms retrieval
- [ ] `ai/benchmarks/memory_efficiency.py`
  - [ ] Memory usage tracking
  - [ ] Trace storage efficiency
  - [ ] Consolidation effectiveness
- [ ] `ai/benchmarks/ablation.py`
  - [ ] No episodic memory
  - [ ] No semantic memory
  - [ ] No theta gating
  - [ ] No consolidation
  - [ ] Measure impact of each component

**Deliverables**:
- [ ] Benchmark suite
- [ ] Baseline results
- [ ] Hippocampal RAG results
- [ ] Ablation study results
- [ ] Performance report

**Target Metrics**:
- [ ] LongBench accuracy: +15% vs baseline
- [ ] Retrieval latency: <100ms
- [ ] Memory efficiency: <1GB for 10K traces

**Exit**: Benchmarks complete, targets met

---

### 3.8 AI Memory Documentation
**Agent**: AI Docs Writer

**Tasks**:
- [ ] Memory system architecture
  - [ ] Episodic/semantic/working overview
  - [ ] Encoding/consolidation/retrieval
  - [ ] Biological inspiration
- [ ] LLM integration guide
  - [ ] Supported LLMs
  - [ ] API keys setup
  - [ ] Configuration
- [ ] Usage examples
  - [ ] Basic RAG
  - [ ] Custom consolidation
  - [ ] Multi-LLM usage
- [ ] Tutorial notebooks
  - [ ] Getting started
  - [ ] Advanced usage
  - [ ] Custom memory systems

**Deliverables**:
- [ ] Complete AI documentation
- [ ] Usage guide
- [ ] Tutorial notebooks
- [ ] API reference

**Exit**: Documentation complete

---

## PHASE 4: PERFORMANCE & SCALE

### 4.1 Profiling
**Agent**: Profiler

**Tasks**:
- [ ] Profile at multiple scales
  - [ ] N=100: Baseline
  - [ ] N=1K: Small network
  - [ ] N=10K: Medium network
  - [ ] N=100K: Target scale
- [ ] Identify bottlenecks
  - [ ] CPU profiling (cProfile, line_profiler)
  - [ ] Memory profiling (memory_profiler)
  - [ ] I/O profiling
- [ ] Hotspot analysis
  - [ ] Weight matrix operations
  - [ ] Neuron updates
  - [ ] Synapse updates
  - [ ] Plasticity updates
  - [ ] Inference (EM iterations)
- [ ] Create optimization roadmap
  - [ ] Prioritize by impact
  - [ ] Estimate speedup potential
  - [ ] Plan implementation order

**Deliverables**:
- [ ] Profiling report (all scales)
- [ ] Bottleneck analysis
- [ ] Optimization roadmap
- [ ] Performance budget

**Exit**: Clear understanding of performance limits

---

### 4.2 JAX Migration
**Agent**: JAX Specialist

**Tasks**:
- [ ] Setup JAX infrastructure
  - [ ] JAX installation
  - [ ] GPU detection
  - [ ] Backend configuration
- [ ] Migrate critical paths
  - [ ] `primitives/neurons/two_compartment.py` → JAX
  - [ ] `primitives/synapses/composite.py` → JAX
  - [ ] `primitives/plasticity/calcium_based.py` → JAX
  - [ ] `primitives/inference/zinb.py` → JAX (JIT EM)
- [ ] Implementation pattern
  ```python
  import jax.numpy as jnp
  from jax import jit, vmap, grad
  
  @jit
  def update_neuron(state, I, dt, params):
      V, Ca = state
      dV = (-params.g_l*(V - params.E_l) + I) / params.C_m
      dCa = -Ca / params.tau_Ca + params.Ca_in * (V > params.V_thresh)
      return (V + dt*dV, Ca + dt*dCa)
  
  # Vectorize over population
  update_population = vmap(update_neuron, in_axes=(0, 0, None, None))
  ```
- [ ] Backward compatibility
  - [ ] NumPy fallback
  - [ ] Automatic backend selection
  - [ ] Testing both backends

**Deliverables**:
- [ ] JAX versions of hot paths
- [ ] Benchmark: 5-10x speedup
- [ ] Backward compatible
- [ ] GPU support

**Exit**: JAX implementation working, speedup verified

---

### 4.3 Sparse Matrix Optimization
**Agent**: Sparse Matrix Specialist

**Tasks**:
- [ ] Convert connectivity to sparse
  - [ ] Dense (N×N) → CSR (data, indices, indptr)
  - [ ] Memory savings: 10-100x for 10% connectivity
- [ ] Sparse operations
  - [ ] Matrix-vector multiplication (SpMV)
  - [ ] Matrix-matrix multiplication (SpMM)
  - [ ] Element-wise operations
- [ ] JAX sparse support
  - [ ] BCOO format
  - [ ] Sparse @ dense operations
- [ ] Benchmark
  - [ ] Memory usage: Dense vs Sparse
  - [ ] Speed: Dense vs Sparse operations

**Deliverables**:
- [ ] Sparse matrix infrastructure
- [ ] Converted connectivity matrices
- [ ] Benchmark report
- [ ] 10-100x memory savings

**Exit**: Sparse matrices working, memory reduced

---

### 4.4 Parallelization
**Agent**: Parallel Computing Engineer

**Tasks**:
- [ ] Identify parallel opportunities
  - [ ] Neuron updates (embarrassingly parallel)
  - [ ] Synapse updates (parallel per connection)
  - [ ] Multiple simulations (parameter sweeps)
- [ ] Multi-core CPU parallelization
  - [ ] `joblib.Parallel` for Python
  - [ ] Process pools for simulations
- [ ] GPU parallelization
  - [ ] JAX GPU backend
  - [ ] Batch processing
- [ ] Distributed computing (future)
  - [ ] Ray for distributed simulations
  - [ ] MPI for HPC

**Deliverables**:
- [ ] Parallel implementations
- [ ] Benchmark: Linear scaling up to N cores
- [ ] GPU utilization >80%

**Exit**: Parallelization working, scaling verified

---

### 4.5 Batching & Memory Management
**Agent**: Memory Optimizer

**Tasks**:
- [ ] Batch processing
  - [ ] Process neurons in batches (1K-10K)
  - [ ] Avoid loading full matrices
  - [ ] Streaming for large datasets
- [ ] Memory pooling
  - [ ] Reuse allocated arrays
  - [ ] Avoid repeated allocation/deallocation
- [ ] Lazy evaluation
  - [ ] Compute only when needed
  - [ ] Cache intermediate results
- [ ] Memory monitoring
  - [ ] Track peak memory usage
  - [ ] Alert on memory issues

**Deliverables**:
- [ ] Batch processing infrastructure
- [ ] Memory pooling system
- [ ] Monitoring tools
- [ ] Memory usage <50% of available

**Exit**: Memory efficient at all scales

---

### 4.6 Scale Validation
**Agent**: Scale Validator

**Tasks**:
- [ ] Test at multiple scales
  - [ ] N=100: Baseline (current)
  - [ ] N=1K: 10x scale
  - [ ] N=10K: 100x scale
  - [ ] N=100K: 1000x scale (target)
  - [ ] N=1M: 10000x scale (stretch goal)
- [ ] Measure performance
  - [ ] Time per step
  - [ ] Memory usage
  - [ ] Scaling factor (linear expected)
- [ ] Verify correctness
  - [ ] Golden tests at each scale
  - [ ] Statistical properties maintained
  - [ ] Biological metrics stable
- [ ] Regression testing
  - [ ] Performance cannot degrade >5%
  - [ ] Continuous monitoring

**Deliverables**:
- [ ] Scaling report
- [ ] Performance graphs (N vs time, memory)
- [ ] Regression test suite
- [ ] Target achieved: 100K @ <1s/step

**Exit**: 100K neurons stable, <1s per timestep

---

### 4.7 Performance Documentation
**Agent**: Performance Docs Writer

**Tasks**:
- [ ] Optimization guide
  - [ ] JAX usage
  - [ ] Sparse matrices
  - [ ] Parallelization
  - [ ] GPU setup
- [ ] Performance tuning guide
  - [ ] Parameter sweeps
  - [ ] Batch sizes
  - [ ] Backend selection
- [ ] Benchmarking guide
  - [ ] How to profile
  - [ ] How to benchmark
  - [ ] Regression testing

**Deliverables**:
- [ ] Performance documentation
- [ ] Tuning guide
- [ ] Benchmarking guide

**Exit**: Performance docs complete

---

## PHASE 5: BIOLOGICAL FIDELITY

### 5.1 Literature Review
**Agent**: Literature Miner

**Tasks**:
- [ ] Scan recent papers (2024-2025)
  - [ ] Nature, Science, Neuron, Nature Neuroscience
  - [ ] Hippocampus, eLife, Journal of Neuroscience
  - [ ] Focus: CA1, plasticity, memory, coding
- [ ] Extract new findings
  - [ ] Active dendrites (Poirazi lab)
  - [ ] Cell-type diversity (Allen Institute)
  - [ ] Neuromodulation (Lee/Knierim groups)
  - [ ] Spatial coding 2.0 (Moser lab)
  - [ ] Replay mechanisms (Wilson/Buzsáki labs)
- [ ] Identify parameters
  - [ ] New biophysical measurements
  - [ ] Updated models
  - [ ] Experimental datasets

**Deliverables**:
- [ ] Literature review report
- [ ] New findings list
- [ ] Parameter updates
- [ ] Implementation priorities

**Exit**: New biology identified for integration

---

### 5.2 Active Dendrites
**Agent**: Dendrite Specialist

**Tasks**:
- [ ] Implement active dendrites
  - [ ] NMDA spikes (voltage-dependent)
  - [ ] Ca²⁺ plateaus (sustained depolarization)
  - [ ] Branch-specific computation
- [ ] Multi-compartment enhancement
  - [ ] Increase from 2 to N compartments
  - [ ] Dendritic tree structure
  - [ ] Branch points
- [ ] Plasticity enhancement
  - [ ] Branch-specific plasticity
  - [ ] Dendritic spikes trigger LTP
  - [ ] Local Ca²⁺ domains

**Deliverables**:
- [ ] Active dendrite module
- [ ] N-compartment neurons
- [ ] Branch-specific plasticity
- [ ] Unit tests
- [ ] Documentation

**Exit**: Active dendrites work, validated

---

### 5.3 Cell-Type Diversity
**Agent**: Cell-Type Specialist

**Tasks**:
- [ ] Allen Institute data integration
  - [ ] Download CA1 transcriptomic data
  - [ ] Identify major cell types (10+)
  - [ ] Extract type-specific parameters
- [ ] Implement cell types
  - [ ] Pyramidal (multiple subtypes)
  - [ ] Interneurons (PV, SST, VIP, etc.)
  - [ ] Type-specific biophysics
- [ ] Type-specific connectivity
  - [ ] Different E-I balance per type
  - [ ] Type-specific targets
  - [ ] Molecular markers

**Deliverables**:
- [ ] Cell-type library (10+ types)
- [ ] Allen data integration
- [ ] Type-specific parameters
- [ ] Documentation

**Exit**: Cell-type diversity implemented

---

### 5.4 Neuromodulation
**Agent**: Neuromodulation Specialist

**Tasks**:
- [ ] Acetylcholine system
  - [ ] State-dependent modulation
  - [ ] Encoding vs retrieval mode
  - [ ] Theta rhythm modulation
- [ ] Dopamine system
  - [ ] Reward prediction error
  - [ ] Plasticity gating
  - [ ] Motivation/salience
- [ ] Serotonin system
  - [ ] Mood/stress effects
  - [ ] Long-term modulation
- [ ] Implementation
  - [ ] Neuromodulator concentration
  - [ ] Time-varying levels
  - [ ] Effect on parameters (g, tau, etc.)

**Deliverables**:
- [ ] Neuromodulation system
- [ ] ACh, DA, 5-HT modules
- [ ] Unit tests
- [ ] Documentation

**Exit**: Neuromodulation functional

---

### 5.5 Spatial Coding Enhancement
**Agent**: Spatial Coding Specialist

**Tasks**:
- [ ] Grid cell → Place cell transformation
  - [ ] Grid cell input model
  - [ ] Interference mechanism
  - [ ] Place field formation
- [ ] Vector navigation
  - [ ] Path integration
  - [ ] Goal-directed coding
- [ ] Boundary vector cells
  - [ ] Distance to boundaries
  - [ ] Geometry encoding
- [ ] Head direction integration
  - [ ] Angular velocity integration
  - [ ] Landmark alignment

**Deliverables**:
- [ ] Spatial coding module
- [ ] Grid/place cell integration
- [ ] Vector navigation
- [ ] Unit tests
- [ ] Documentation

**Exit**: Spatial coding enhanced

---

### 5.6 Experimental Data Validation
**Agent**: Experimental Validator

**Tasks**:
- [ ] Collect experimental datasets
  - [ ] Allen Institute CA1 recordings
  - [ ] DANDI archive data
  - [ ] Published datasets (Wilson, Buzsáki, etc.)
- [ ] Extract validation metrics
  - [ ] Firing rate distributions
  - [ ] ISI distributions
  - [ ] Phase precession (circular-linear correlation)
  - [ ] Replay compression factor
  - [ ] Place field properties
- [ ] Compare model vs data
  - [ ] Statistical tests
  - [ ] Distribution matching
  - [ ] Correlation analysis
- [ ] Compute biological plausibility score
  ```
  Bio_Score = mean([
      firing_rate_match,
      phase_precession_match,
      replay_match,
      place_field_match,
      ...
  ])
  Target: >0.85
  ```

**Deliverables**:
- [ ] Experimental datasets integrated
- [ ] Validation metrics computed
- [ ] Model vs data comparison
- [ ] Biological plausibility score >0.85

**Exit**: Model validated against experimental data

---

### 5.7 Biological Documentation
**Agent**: Bio Docs Writer

**Tasks**:
- [ ] Biological grounding document
  - [ ] Every parameter → DOI source
  - [ ] Cell types → Allen Institute
  - [ ] Connectivity → Anatomy papers
  - [ ] Dynamics → Electrophysiology papers
- [ ] Validation report
  - [ ] Model vs experimental data
  - [ ] Statistical comparisons
  - [ ] Plausibility score breakdown
- [ ] Limitations document
  - [ ] What's not modeled
  - [ ] Simplifications made
  - [ ] Future improvements

**Deliverables**:
- [ ] Biological grounding doc
- [ ] Validation report
- [ ] Limitations doc

**Exit**: Biology fully documented

---

## PHASE 6: FRAMEWORK LAYER

### 6.1 Framework Architecture
**Agent**: Framework Architect

**Tasks**:
- [ ] Design builder pattern
  ```
  Builder Pattern:
    RegionBuilder
      ├─ add_neurons(model, N, params)
      ├─ add_connectivity(rule, params)
      ├─ add_plasticity(rule, params)
      ├─ add_inference(model, params)
      └─ build() → Region
  
  NetworkBuilder
      ├─ add_region(name, region)
      ├─ connect_regions(source, target, rule)
      ├─ add_state_controller(controller)
      └─ build() → Network
  ```
- [ ] Design simulator interface
  ```
  Simulator:
    ├─ __init__(network, backend='jax')
    ├─ run(T, dt, inputs)
    ├─ step(inputs, dt)
    ├─ get_state()
    └─ set_state(state)
  ```
- [ ] Design plugin system
  ```
  Plugin:
    ├─ register(name, class)
    ├─ load(name)
    ├─ list_available()
    └─ validate(plugin)
  ```

**Deliverables**:
- [ ] Framework architecture spec
- [ ] Builder interface
- [ ] Simulator interface
- [ ] Plugin interface

**Exit**: Architecture approved

---

### 6.2 Region Builder
**Agent**: Builder Developer

**Tasks**:
- [ ] `framework/builder/region.py`
  - [ ] `RegionBuilder` class
  - [ ] Fluent API (method chaining)
  - [ ] Validation (parameters, compatibility)
  - [ ] Build process
- [ ] `framework/builder/network.py`
  - [ ] `NetworkBuilder` class
  - [ ] Multi-region composition
  - [ ] Inter-region connectivity
  - [ ] State controller integration
- [ ] Example usage
  ```python
  from framework import RegionBuilder
  
  # Build custom region
  builder = RegionBuilder(name='MyRegion')
  builder.add_neurons(
      model='two_compartment',
      N=1000,
      params=my_params
  )
  builder.add_connectivity(
      rule='distance_dependent',
      probability=0.1,
      distance_scale=100.0
  )
  builder.add_plasticity(
      rule='calcium_based',
      theta_p=2.0,
      theta_d=1.0
  )
  builder.add_inference(
      model='zinb',
      max_iter=100
  )
  
  region = builder.build()
  ```

**Deliverables**:
- [ ] RegionBuilder implementation
- [ ] NetworkBuilder implementation
- [ ] Unit tests
- [ ] Documentation
- [ ] Examples

**Exit**: Builders working, examples run

---

### 6.3 Simulator
**Agent**: Simulator Developer

**Tasks**:
- [ ] `framework/simulator/base.py`
  - [ ] `AbstractSimulator` interface
  - [ ] State management
  - [ ] Input/output handling
- [ ] `framework/simulator/numpy_backend.py`
  - [ ] NumPy implementation
  - [ ] CPU-optimized
  - [ ] Baseline backend
- [ ] `framework/simulator/jax_backend.py`
  - [ ] JAX implementation
  - [ ] JIT compiled
  - [ ] GPU support
- [ ] `framework/simulator/adaptive.py`
  - [ ] Adaptive timestep (optional)
  - [ ] Event-driven (optional)
- [ ] Backend selection
  ```python
  from framework import Simulator
  
  # Auto-select backend
  sim = Simulator(network, backend='auto')
  # Force specific backend
  sim = Simulator(network, backend='jax')
  
  # Run
  results = sim.run(T=1000, dt=0.1, inputs=my_inputs)
  ```

**Deliverables**:
- [ ] Simulator implementations
- [ ] Multiple backends
- [ ] Unit tests
- [ ] Performance tests
- [ ] Documentation

**Exit**: Simulator working, all backends tested

---

### 6.4 Plugin System
**Agent**: Plugin Developer

**Tasks**:
- [ ] `framework/plugins/base.py`
  - [ ] `Plugin` base class
  - [ ] Registration mechanism
  - [ ] Discovery (scan directories)
  - [ ] Validation (interface compliance)
- [ ] `framework/plugins/registry.py`
  - [ ] Plugin registry
  - [ ] Load/unload
  - [ ] Version management
  - [ ] Dependencies
- [ ] Example plugins
  - [ ] CA3 plugin (recurrent attractor)
  - [ ] EC plugin (grid cells)
  - [ ] Custom neuron plugin
  - [ ] Custom plasticity plugin
- [ ] Plugin development guide
  ```python
  from framework.plugins import Plugin
  
  class MyCustomRegion(Plugin):
      name = 'my_custom_region'
      version = '1.0.0'
      
      def create_network(self, params):
          # Build network using framework primitives
          builder = RegionBuilder()
          # ... configure
          return builder.build()
      
      def encode(self, input_data):
          # Convert input to neural activity
          return neural_activity
      
      def decode(self, neural_activity):
          # Convert neural activity to output
          return output
  ```

**Deliverables**:
- [ ] Plugin system
- [ ] Example plugins (2+)
- [ ] Plugin development guide
- [ ] Unit tests
- [ ] Documentation

**Exit**: Plugin system working, examples functional

---

### 6.5 Framework Documentation
**Agent**: Framework Docs Writer

**Tasks**:
- [ ] Framework overview
  - [ ] Architecture
  - [ ] Components
  - [ ] Design principles
- [ ] Builder guide
  - [ ] RegionBuilder tutorial
  - [ ] NetworkBuilder tutorial
  - [ ] Advanced patterns
- [ ] Simulator guide
  - [ ] Backend selection
  - [ ] Performance tuning
  - [ ] State management
- [ ] Plugin development guide
  - [ ] Creating plugins
  - [ ] Plugin API
  - [ ] Best practices
- [ ] Tutorial notebooks
  - [ ] Building custom region
  - [ ] Multi-region network
  - [ ] Custom plugin
  - [ ] Full workflow

**Deliverables**:
- [ ] Complete framework docs
- [ ] Tutorial notebooks (4+)
- [ ] API reference
- [ ] Best practices guide

**Exit**: Framework fully documented

---

### 6.6 Framework Examples
**Agent**: Example Creator

**Tasks**:
- [ ] `examples/framework/`
  - [ ] `build_ca3.py` - Build CA3 region from primitives
  - [ ] `build_ec.py` - Build EC region from primitives
  - [ ] `build_hippocampus.py` - CA1+CA3+EC full network
  - [ ] `custom_neuron.py` - Custom neuron model
  - [ ] `custom_plasticity.py` - Custom plasticity rule
  - [ ] `custom_inference.py` - Custom inference algorithm
  - [ ] `multi_region_simulation.py` - Full workflow
- [ ] Jupyter notebooks
  - [ ] Interactive tutorials
  - [ ] Visualization
  - [ ] Parameter exploration

**Deliverables**:
- [ ] Example scripts (7+)
- [ ] Jupyter notebooks (3+)
- [ ] Documentation for each
- [ ] All examples tested and working

**Exit**: Examples complete, pedagogical

---

## PHASE 7: QUALITY & RELEASE

### 7.1 Comprehensive Testing
**Agent**: QA Engineer

**Tasks**:
- [ ] Unit tests
  - [ ] All primitives (neurons, synapses, etc.)
  - [ ] All regions (CA1, CA3, EC)
  - [ ] All AI components (memory, LLM)
  - [ ] All framework components
  - [ ] Target: 95%+ coverage
- [ ] Integration tests
  - [ ] Primitives compose correctly
  - [ ] Regions work together
  - [ ] AI integrates with neuroscience
  - [ ] Framework builds complex networks
- [ ] Golden tests
  - [ ] 5 original tests still pass
  - [ ] Additional golden tests for new features
  - [ ] Reproducibility verified (seed=42)
- [ ] Performance regression tests
  - [ ] Benchmark suite runs automatically
  - [ ] Alert on >5% performance degradation
  - [ ] Track performance over time
- [ ] Biological validation tests
  - [ ] Experimental data comparisons
  - [ ] Plausibility score computed
  - [ ] Target: >0.85 maintained

**Deliverables**:
- [ ] Complete test suite
- [ ] 95%+ code coverage
- [ ] Golden tests: All pass
- [ ] Performance: No regressions
- [ ] Biology: Score >0.85
- [ ] CI/CD integration

**Exit**: All tests pass, quality verified

---

### 7.2 Documentation Audit
**Agent**: Docs Auditor

**Tasks**:
- [ ] Review all documentation
  - [ ] README.md (updated for v3.0)
  - [ ] API.md (complete API reference)
  - [ ] ARCHITECTURE.md (updated architecture)
  - [ ] TESTING.md (updated testing guide)
  - [ ] USAGE.md (updated with framework)
  - [ ] BIBLIOGRAPHY.md (all new papers)
  - [ ] INSTALLATION.md (dependencies updated)
- [ ] Check completeness
  - [ ] Every public API documented
  - [ ] Every example explained
  - [ ] Every feature covered
- [ ] Check accuracy
  - [ ] Code examples run
  - [ ] Parameters match implementation
  - [ ] Links work
- [ ] Check clarity
  - [ ] Readable for beginners
  - [ ] Useful for experts
  - [ ] Tutorials pedagogical

**Deliverables**:
- [ ] Documentation audit report
- [ ] All issues fixed
- [ ] Documentation complete and accurate

**Exit**: Documentation audit passed

---

### 7.3 Security & Stability
**Agent**: Security Engineer

**Tasks**:
- [ ] Security scan
  - [ ] Bandit (Python security)
  - [ ] Safety (dependency vulnerabilities)
  - [ ] Code review for security issues
- [ ] Stability testing
  - [ ] Long-running simulations (hours)
  - [ ] Memory leak detection
  - [ ] Edge case testing
  - [ ] Error handling verification
- [ ] Dependency audit
  - [ ] All dependencies up-to-date
  - [ ] No known vulnerabilities
  - [ ] License compatibility (MIT)

**Deliverables**:
- [ ] Security report (no vulnerabilities)
- [ ] Stability report (no crashes)
- [ ] Dependency audit (all clean)

**Exit**: Secure and stable

---

### 7.4 Backward Compatibility
**Agent**: Compatibility Engineer

**Tasks**:
- [ ] Test v2.0 code with v3.0
  - [ ] Old API still works
  - [ ] Deprecation warnings clear
  - [ ] Migration path documented
- [ ] Version compatibility matrix
  - [ ] Python 3.8, 3.9, 3.10, 3.11, 3.12
  - [ ] NumPy versions
  - [ ] JAX versions
  - [ ] Other dependencies
- [ ] Upgrade guide
  - [ ] Step-by-step migration
  - [ ] Breaking changes documented
  - [ ] Code examples

**Deliverables**:
- [ ] Backward compatibility verified
- [ ] Compatibility matrix
- [ ] Upgrade guide

**Exit**: Smooth migration path guaranteed

---

### 7.5 Performance Benchmarking
**Agent**: Benchmark Final Validator

**Tasks**:
- [ ] Comprehensive benchmarks
  - [ ] All scales (100, 1K, 10K, 100K, 1M)
  - [ ] All backends (NumPy, JAX, GPU)
  - [ ] All platforms (Linux, macOS, Windows)
- [ ] Benchmark report
  - [ ] Scaling graphs
  - [ ] Performance tables
  - [ ] Comparison with v2.0
  - [ ] Hardware recommendations
- [ ] Regression tracking
  - [ ] Historical performance data
  - [ ] Trend analysis
  - [ ] Early warning system

**Deliverables**:
- [ ] Benchmark report
- [ ] Performance verified at all scales
- [ ] Targets met (100K @ <1s/step)

**Exit**: Performance targets achieved

---

### 7.6 Release Preparation
**Agent**: Release Manager

**Tasks**:
- [ ] Version tagging
  - [ ] Semantic versioning (v3.0.0)
  - [ ] Git tags
  - [ ] Release branch
- [ ] Release notes
  - [ ] New features summary
  - [ ] Breaking changes
  - [ ] Migration guide
  - [ ] Acknowledgments
- [ ] Release artifacts
  - [ ] Source code archive
  - [ ] Wheel package (PyPI ready)
  - [ ] Documentation bundle
  - [ ] Example datasets
- [ ] Release checklist
  - [ ] All tests pass
  - [ ] Documentation complete
  - [ ] Security audit passed
  - [ ] Performance benchmarks met
  - [ ] Backward compatibility verified

**Deliverables**:
- [ ] Release v3.0.0 tagged
- [ ] Release notes complete
- [ ] Release artifacts ready
- [ ] Release checklist verified

**Exit**: Ready for public release

---

### 7.7 PyPI Publication
**Agent**: Package Publisher

**Tasks**:
- [ ] Package preparation
  - [ ] setup.py configured
  - [ ] MANIFEST.in complete
  - [ ] All files included
- [ ] PyPI metadata
  - [ ] Project description
  - [ ] Keywords
  - [ ] Classifiers
  - [ ] Dependencies
- [ ] Test PyPI upload
  - [ ] Upload to test.pypi.org
  - [ ] Verify installation
  - [ ] Test functionality
- [ ] Production PyPI upload
  - [ ] Upload to pypi.org
  - [ ] Verify availability
  - [ ] Installation test

**Deliverables**:
- [ ] Package published to PyPI
- [ ] Installation verified: `pip install hippocampal-ca1-lam`

**Exit**: Package publicly available

---

## PHASE 8: COMMUNITY & IMPACT

### 8.1 Paper Writing
**Agent**: Paper Writer

**Tasks**:
- [ ] Paper structure
  ```
  1. Introduction
     - Problem: LLMs lack biologically-inspired memory
     - Solution: Hippocampal CA1 framework
     - Contributions: 4 key innovations
  
  2. Background
     - Neurobiology of CA1
     - Computational models
     - LLM memory systems
  
  3. Methods
     - Primitive architecture
     - Fractal region composition
     - AI memory integration
     - Framework design
  
  4. Validation
     - Biological: Experimental data match (>0.85)
     - Computational: Golden tests (5/5)
     - AI: LongBench (+15%)
     - Scale: 100K neurons
  
  5. Results
     - Biological fidelity
     - AI performance
     - Framework extensibility
     - Ablation studies
  
  6. Discussion
     - Implications for AI
     - Neuroscience insights
     - Limitations
     - Future work
  
  7. Conclusion
     - Summary of contributions
     - Broader impact
  ```
- [ ] Figures
  - [ ] Architecture diagram
  - [ ] Performance graphs
  - [ ] Biological validation
  - [ ] AI benchmarks
  - [ ] Ablation results
- [ ] Supplementary materials
  - [ ] Full parameter tables
  - [ ] Extended results
  - [ ] Code availability
  - [ ] Data availability

**Deliverables**:
- [ ] Paper draft v1
- [ ] All figures
- [ ] Supplementary materials

**Exit**: Paper draft complete

---

### 8.2 Target Venue Selection
**Agent**: Publication Strategist

**Tasks**:
- [ ] Evaluate venues
  - [ ] **Computational neuroscience**: NeurIPS (workshop/main), ICML, Frontiers Comp Neurosci
  - [ ] **Neuroscience**: eNeuro, Journal of Neuroscience, Hippocampus
  - [ ] **AI/ML**: TMLR, ICLR (workshop/main)
  - [ ] **Hybrid**: Nature Communications, PLOS Comp Bio
- [ ] Selection criteria
  - [ ] Impact factor
  - [ ] Review timeline
  - [ ] Open access policy
  - [ ] Audience fit
- [ ] Submission strategy
  - [ ] Primary target
  - [ ] Backup options
  - [ ] Timeline

**Deliverables**:
- [ ] Venue selection (primary + backups)
- [ ] Submission timeline
- [ ] Preparation checklist

**Exit**: Venue selected, timeline set

---

### 8.3 Code & Data Release
**Agent**: Open Science Coordinator

**Tasks**:
- [ ] GitHub release
  - [ ] Clean repository
  - [ ] Clear README
  - [ ] Issue templates
  - [ ] Contributing guidelines
  - [ ] Code of conduct
- [ ] Zenodo DOI
  - [ ] Link GitHub to Zenodo
  - [ ] Generate DOI for release
  - [ ] Update citations
- [ ] Data release
  - [ ] Experimental validation data
  - [ ] Benchmark datasets
  - [ ] Example datasets
  - [ ] Upload to DANDI/OSF
- [ ] Code Ocean capsule (optional)
  - [ ] Reproducible environment
  - [ ] One-click execution
  - [ ] Publication companion

**Deliverables**:
- [ ] GitHub release v3.0.0
- [ ] Zenodo DOI
- [ ] Data on public repository
- [ ] Code Ocean capsule (optional)

**Exit**: All resources publicly available

---

### 8.4 Documentation Website
**Agent**: Web Developer

**Tasks**:
- [ ] Documentation site
  - [ ] Sphinx/MkDocs setup
  - [ ] API reference (auto-generated)
  - [ ] Tutorials
  - [ ] Examples gallery
- [ ] GitHub Pages deployment
  - [ ] Automatic builds
  - [ ] Version switching
  - [ ] Search functionality
- [ ] Content
  - [ ] Getting started
  - [ ] User guide
  - [ ] Developer guide
  - [ ] API reference
  - [ ] FAQ
  - [ ] Changelog

**Deliverables**:
- [ ] Documentation website live
- [ ] URL: TBD (GitHub Pages to be configured)
- [ ] Auto-updating with releases

**Exit**: Website deployed and accessible

---

### 8.5 Tutorial Content
**Agent**: Educator

**Tasks**:
- [ ] Video tutorials (YouTube)
  - [ ] Introduction (5 min)
  - [ ] Quick start (10 min)
  - [ ] Framework basics (15 min)
  - [ ] AI memory integration (20 min)
  - [ ] Advanced topics (30 min)
- [ ] Blog posts (Medium/own blog)
  - [ ] "Building Biologically-Inspired AI Memory"
  - [ ] "Hippocampal CA1: A Framework for Neural Computing"
  - [ ] "From Neuroscience to Production ML"
- [ ] Interactive demos
  - [ ] Google Colab notebooks
  - [ ] Binder environment
  - [ ] Streamlit app (optional)

**Deliverables**:
- [ ] 5 video tutorials
- [ ] 3 blog posts
- [ ] Interactive demos

**Exit**: Educational content published

---

### 8.6 Conference Presentations
**Agent**: Presenter

**Tasks**:
- [ ] Identify conferences
  - [ ] NeurIPS (AI/ML)
  - [ ] COSYNE (comp neuroscience)
  - [ ] SfN (neuroscience)
  - [ ] Relevant workshops
- [ ] Prepare materials
  - [ ] Poster (for in-person)
  - [ ] Slides (for talks)
  - [ ] Demos (for workshops)
  - [ ] Handouts (QR codes to resources)
- [ ] Submit abstracts
  - [ ] Tailored to each venue
  - [ ] Deadline tracking
- [ ] Present
  - [ ] Practice talks
  - [ ] Engage with community
  - [ ] Collect feedback

**Deliverables**:
- [ ] Conference submissions
- [ ] Presentation materials
- [ ] Accepted presentations
- [ ] Community feedback

**Exit**: Presented at ≥2 conferences

---

### 8.7 Community Building
**Agent**: Community Manager

**Tasks**:
- [ ] Communication channels
  - [ ] GitHub Discussions (primary)
  - [ ] Discord/Slack (optional, community-driven)
  - [ ] Twitter/X for updates
  - [ ] Mailing list (announcements)
- [ ] Contribution guidelines
  - [ ] CONTRIBUTING.md complete
  - [ ] Code review process
  - [ ] Contributor recognition
  - [ ] First-time contributor help
- [ ] Issue management
  - [ ] Triage new issues
  - [ ] Label appropriately
  - [ ] Respond promptly
  - [ ] Close resolved issues
- [ ] Pull request management
  - [ ] Review process
  - [ ] CI/CD checks
  - [ ] Merge criteria
  - [ ] Acknowledgment
- [ ] Community events
  - [ ] Monthly Q&A sessions
  - [ ] Hackathons
  - [ ] Tutorial sessions
  - [ ] Contributor spotlights

**Deliverables**:
- [ ] Active communication channels
- [ ] Responsive issue management
- [ ] Growing contributor base
- [ ] Regular community events

**Exit**: Healthy, active community

---

### 8.8 Success Metrics Tracking
**Agent**: Metrics Analyst

**Tasks**:
- [ ] Track adoption metrics
  - [ ] GitHub stars
  - [ ] PyPI downloads
  - [ ] Forks
  - [ ] Contributors
  - [ ] Issues/PRs
- [ ] Track impact metrics
  - [ ] Paper citations
  - [ ] Conference presentations
  - [ ] Blog mentions
  - [ ] Social media engagement
- [ ] Track usage metrics
  - [ ] Documentation page views
  - [ ] Tutorial completions
  - [ ] Example usage
- [ ] Community health
  - [ ] Active contributors
  - [ ] Response time to issues
  - [ ] PR merge time
  - [ ] Community satisfaction

**Target Metrics (6 months post-release)**:
- [ ] GitHub stars: 100+
- [ ] PyPI downloads: 1,000+/month
- [ ] Contributors: 10+
- [ ] Paper citations: 5+

**Deliverables**:
- [ ] Metrics dashboard
- [ ] Monthly reports
- [ ] Trend analysis
- [ ] Success evaluation

**Exit**: Metrics tracked, targets achieved

---

## DEPENDENCIES & SEQUENCING

```
PHASE 0 (Foundation Audit)
    ↓
PHASE 1 (Atomic Primitives)
    ↓
PHASE 2 (Fractal Regions)
    ↓
PHASE 3 (AI Memory) ──┐
    ↓                 │
PHASE 4 (Scale) ──────┤
    ↓                 ├──→ Can parallelize
PHASE 5 (Biology) ────┘
    ↓
PHASE 6 (Framework)
    ↓
PHASE 7 (Quality & Release)
    ↓
PHASE 8 (Community & Impact)
```

**Critical Path**: 0→1→2→3→4→5→6→7→8 (sequential)  
**Parallelizable**: Phases 3, 4, 5 can overlap partially

---

## EXIT CRITERIA SUMMARY

| Phase | Gate | Criteria |
|-------|------|----------|
| 0 | Baseline | Current state documented, benchmarks set |
| 1 | Primitives | Golden tests 5/5, coverage 95%, backward compat |
| 2 | Regions | CA1 functional, validates experimentally |
| 3 | AI Memory | LongBench +15%, <100ms latency, 3 LLM integrations |
| 4 | Scale | 100K @ <1s/step, 10x speedup, GPU functional |
| 5 | Biology | Plausibility >0.85, experimental match, diversity |
| 6 | Framework | Builders work, 2+ plugins, docs complete |
| 7 | Release | All tests pass, v3.0 tagged, PyPI published |
| 8 | Impact | Paper submitted, 100+ stars, 10+ contributors |

---

## ROLLBACK STRATEGY

**If Phase N fails**:
1. Assess severity
   - BLOCKER: Must fix to proceed
   - MAJOR: Can workaround
   - MINOR: Can defer
2. Options:
   - Fix in place (small issues)
   - Rollback to Phase N-1 (major issues)
   - Fork approach (try alternative)
3. Document
   - What failed
   - Why it failed
   - How it was resolved
4. Prevent recurrence
   - Add tests
   - Update process
   - Improve validation

**Checkpoints**: After each phase, create checkpoint branch

```bash
git checkout -b checkpoint/phase-N-complete
git tag v3.0-phase-N
```

---

## CONTINUOUS VALIDATION

**Every commit**:
- [ ] Golden tests must pass (5/5)
- [ ] Unit tests must pass (95%+)
- [ ] No performance regression (>5%)
- [ ] Code style checks (black, isort, flake8)

**Every phase**:
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] Benchmarks run
- [ ] Review by orchestrator (you)

**Every release**:
- [ ] All exit criteria met
- [ ] Security audit passed
- [ ] Backward compatibility verified
- [ ] Release notes complete

---

## SUCCESS DEFINITION

**v3.0 is successful when**:

1. **Technical**:
   - [ ] All primitives work
   - [ ] CA1 region validated
   - [ ] AI memory functional
   - [ ] Scales to 100K
   - [ ] Biology score >0.85
   - [ ] Framework extensible

2. **Quality**:
   - [ ] Golden tests: 5/5
   - [ ] Coverage: 95%+
   - [ ] Performance: 10x v2.0
   - [ ] Secure: No vulnerabilities
   - [ ] Documented: Complete

3. **Impact**:
   - [ ] Paper submitted
   - [ ] PyPI published
   - [ ] 100+ GitHub stars
   - [ ] 10+ contributors
   - [ ] 2+ conference presentations

**FINAL DELIVERABLE**: Production-ready, biologically-grounded, extensible neural framework with proven AI applications and active community.

---

## IMMEDIATE ACTION

```bash
# Start Phase 0
git checkout -b feature/phase0-audit
mkdir -p audit_reports
# Begin code analysis
```

**GO!**
