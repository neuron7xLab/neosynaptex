# ADR-0002: Phase-Entangled Lattice Memory (PELM) Design

**Status**: Accepted
**Date**: 2025-11-30
**Deciders**: MLSDM Core Team
**Categories**: Architecture, Memory Systems

## Context

MLSDM requires a memory system that can:
1. **Store embeddings** from LLM interactions for context retrieval
2. **Support cognitive phases** (wake/sleep) with different retrieval characteristics
3. **Maintain bounded memory** to enable edge deployment
4. **Provide fast retrieval** with sub-millisecond latency
5. **Be thread-safe** for concurrent access

The system is neurobiologically-inspired, drawing from hippocampal memory systems that exhibit phase-dependent encoding and retrieval properties.

### Key Forces

- **Biological inspiration**: Memory consolidation varies with brain state (theta rhythm)
- **Bounded resources**: Cannot allow unbounded memory growth
- **Retrieval quality**: Need relevant context, not just recent items
- **Performance**: Must support high-throughput concurrent access
- **Simplicity**: Prefer simple, testable implementations over complex ones

## Decision

We will implement Phase-Entangled Lattice Memory (PELM) as the primary semantic memory system.

### Core Design

**Data Structure**:
- Fixed-capacity ring buffer for embedding storage
- Parallel array for phase values (continuous 0.0–1.0 range; typical values: wake≈0.1, sleep≈0.9)
- Pre-normalized vectors for fast similarity computation

**Phase Entanglement**:
- Each vector is stored with its cognitive phase at time of encoding
- Retrieval uses both semantic similarity and phase proximity
- Phase tolerance parameter controls phase sensitivity

**Retrieval Algorithm**:
```python
score = cosine_similarity(query, stored_vector) * phase_resonance(query_phase, stored_phase)
```

Where `phase_resonance` is a configurable function that weights phase proximity.

### Key Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `capacity` | 20,000 | 1–1,000,000 | Maximum stored vectors |
| `dimension` | 384 | 1–4096 | Embedding dimension |
| `phase_tolerance` | 0.15 | 0.0–1.0 | Phase matching tolerance |
| `top_k` | 5 | 1–100 | Results per retrieval |

### Memory Layout

```
memory_bank: np.ndarray[capacity, dimension] (float32)
phase_bank:  np.ndarray[capacity]            (float32)
norms:       np.ndarray[capacity]            (float32)
pointer:     int                             # Ring buffer position
size:        int                             # Current fill level
```

**Memory footprint formula**:
```
bytes = capacity * (dimension * 4 + 4 + 4) + overhead
      = capacity * (dimension + 2) * 4 + ~4KB overhead
```

For default values: `20,000 * (384 + 2) * 4 ≈ 30.88 MB`

## Consequences

### Positive

- **Bounded memory**: Hard capacity limit prevents unbounded growth
- **O(n) retrieval**: Linear scan is simple and predictable
- **Phase-aware**: Context relevance varies with cognitive state
- **Thread-safe**: Lock-based design ensures consistency
- **Integrity checking**: Checksums detect memory corruption
- **Auto-recovery**: Graceful handling of corruption scenarios

### Negative

- **Linear search**: Not optimal for very large capacities (>100K)
- **Fixed schema**: Cannot store arbitrary metadata per entry
- **Single dimension**: All vectors must have same dimension
- **Overwrite semantics**: Oldest entries evicted without consideration

### Neutral

- Ring buffer means FIFO eviction policy
- Phase values are continuous in [0.0, 1.0] range (implementation uses wake=0.1, sleep=0.9 for typical operation)

## Alternatives Considered

### Alternative 1: Vector Database (Pinecone, Milvus, etc.)

- **Description**: Use external vector database for embedding storage
- **Pros**: Scalable, approximate nearest neighbor, managed service
- **Cons**: Network latency, external dependency, cost, complexity
- **Reason for rejection**: MLSDM targets edge deployment where external services may not be available; sub-millisecond latency required

### Alternative 2: FAISS Index

- **Description**: Use Facebook's FAISS for efficient similarity search
- **Pros**: Fast approximate search, GPU support, production-proven
- **Cons**: Complex API, C++ dependency, harder to add phase semantics
- **Reason for rejection**: Added complexity not justified for 20K capacity; linear scan is fast enough

### Alternative 3: Hierarchical Memory (L1/L2/L3 only)

- **Description**: Use only the multi-level synaptic memory without PELM
- **Pros**: Simpler, fewer components
- **Cons**: No phase-awareness, weaker semantic retrieval
- **Reason for rejection**: Phase-entangled retrieval is core to the neurobiological model

### Alternative 4: LSH (Locality-Sensitive Hashing)

- **Description**: Use LSH for approximate nearest neighbor with O(1) lookup
- **Pros**: Constant-time retrieval, scalable
- **Cons**: Approximate, harder to incorporate phase, more complex
- **Reason for rejection**: Precision loss not acceptable for safety-critical context

## Implementation

### Affected Components

- `src/mlsdm/memory/phase_entangled_lattice_memory.py` - Core implementation
- `src/mlsdm/core/cognitive_controller.py` - PELM integration
- `src/mlsdm/core/llm_wrapper.py` - Context retrieval
- `tests/property/test_invariants_memory.py` - Property tests
- `tests/unit/test_phase_entangled_memory.py` - Unit tests

### Key Invariants

From `docs/FORMAL_INVARIANTS.md`:

- **INV-LLM-S1**: Memory usage ≤ 1.4 GB
- **INV-LLM-S2**: |memory_vectors| ≤ capacity
- **INV-LLM-S3**: ∀v ∈ memory: dim(v) = configured_dim

### Configuration

```yaml
# config/production-ready.yaml
memory:
  pelm:
    capacity: 20000
    phase_tolerance: 0.15
    min_norm_threshold: 1e-9
```

### Related Documents

- `docs/NEURO_FOUNDATIONS.md` - Section 2.3 on PELM biological basis
- `ARCHITECTURE_SPEC.md` - Memory system overview
- `docs/FORMAL_INVARIANTS.md` - Memory invariants

## References

- Benna, M.K. & Fusi, S. (2016). "Computational principles of synaptic memory consolidation." *Nature Neuroscience*, 19(12), 1697-1706.
- Foster, D.J. & Wilson, M.A. (2006). "Reverse replay of behavioural sequences in hippocampal place cells during the awake state." *Nature*, 440(7084), 680-683.
- Carr, M.F., Jadhav, S.P., & Frank, L.M. (2011). "Hippocampal replay in the awake state: a potential substrate for memory consolidation and retrieval." *Nature Neuroscience*, 14(2), 147-153.

---

*This ADR documents the rationale for PELM design as part of DOC-001 from PROD_GAPS.md*
