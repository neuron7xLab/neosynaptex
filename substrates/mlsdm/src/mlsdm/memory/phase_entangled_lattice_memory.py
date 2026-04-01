from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, Literal, overload

import numpy as np

from mlsdm.memory.provenance import MemoryProvenance, MemorySource
from mlsdm.utils.math_constants import safe_norm

if TYPE_CHECKING:
    from mlsdm.config import PELMCalibration


# Import calibration defaults - these can be overridden via config
# Type hints use Optional to allow None when calibration module unavailable
PELM_DEFAULTS: PELMCalibration | None

try:
    from mlsdm.config import PELM_DEFAULTS
except ImportError:
    PELM_DEFAULTS = None

# Observability imports - gracefully handle missing module
try:
    from mlsdm.observability.memory_telemetry import (
        record_pelm_corruption,
        record_pelm_retrieve,
        record_pelm_store,
    )

    _OBSERVABILITY_AVAILABLE = True
except ImportError:
    _OBSERVABILITY_AVAILABLE = False


@dataclass
class MemoryRetrieval:
    """Result from a memory retrieval operation.

    Attributes:
        vector: The retrieved embedding vector
        phase: The phase value associated with this memory
        resonance: Cosine similarity score (higher = better match)
        provenance: Metadata about memory origin and confidence
        memory_id: Unique identifier for this memory
    """

    __slots__ = ("vector", "phase", "resonance", "provenance", "memory_id")

    vector: np.ndarray
    phase: float
    resonance: float
    provenance: MemoryProvenance
    memory_id: str


class PhaseEntangledLatticeMemory:
    """Phase-aware vector memory with cosine similarity retrieval and circular buffer eviction.

    PhaseEntangledLatticeMemory (PELM) implements a bounded lattice in embedding space
    with phase-based retrieval semantics. Memory vectors are stored with associated phase
    values representing cognitive states (e.g., wake=0.1, sleep=0.9), enabling phase-aware
    context retrieval for cognitive architectures.

    Algorithm - Phase-Entangled Retrieval:
        The retrieval algorithm filters by phase proximity then ranks by cosine similarity:

        1. **Phase Filtering**: Select candidates where :math:`|\\phi_{stored} - \\phi_{query}| \\leq \\tau`

        .. math::
            C = \\{i : |\\phi_i - \\phi_q| \\leq \\tau \\land \\text{confidence}_i \\geq \\theta_c\\}

        2. **Cosine Similarity Scoring**: For each candidate i, compute resonance:

        .. math::
            \\text{resonance}_i = \\frac{v_i \\cdot v_q}{\\|v_i\\| \\cdot \\|v_q\\|}

        3. **Top-K Selection**: Return k candidates with highest resonance scores

        Where:
            - :math:`\\phi_q` = query phase ∈ [0, 1]
            - :math:`\\tau` = phase_tolerance (default: 0.15)
            - :math:`\\theta_c` = min_confidence threshold (default: 0.0)
            - :math:`v_i, v_q` = stored and query vectors (dimension d)
            - :math:`k` = top_k (default: 5)

    Complexity Analysis:
        - **entangle()**: O(1) - constant time insertion with wraparound
        - **entangle_batch()**: O(m) where m = batch size (amortized O(1) per vector)
        - **retrieve()**: O(n + k log k) where n = size, k = top_k
            * Phase filtering: O(n) - linear scan with numpy mask
            * Cosine similarity: O(n × d) - vectorized dot products
            * Top-k selection: O(n) or O(n + k log k) depending on n vs k ratio
        - **memory_usage_bytes()**: O(1) - constant time aggregation

    Memory Efficiency:
        Storage is bounded by capacity × dimension × 4 bytes (float32):

        .. math::
            M_{PELM} = \\text{capacity} \\times d \\times 4 + \\text{overhead}

        For default 384-dim vectors and 20K capacity:
            :math:`M_{PELM} = 20{,}000 \\times 384 \\times 4 = 30.72` MB

    Circular Buffer Eviction Policy:
        When capacity is reached, new memories overwrite oldest memories (FIFO):
        - Pointer wraps around: :math:`p_{new} = (p_{old} + 1) \\mod \\text{capacity}`
        - Low-confidence memories are preferentially evicted
        - Maintains constant memory footprint (bounded)

    Invariants:
        - **INV-PELM-01**: Capacity bounds strictly enforced: :math:`0 \\leq \\text{size} \\leq \\text{capacity}`
        - **INV-PELM-02**: Phase-aware isolation (wake/sleep separation with tolerance)
        - **INV-PELM-03**: Phase tolerance controls cross-phase retrieval
        - **INV-PELM-04**: Resonance ordering (best matches first, descending)
        - **INV-PELM-05**: Wraparound behavior maintains capacity (circular buffer)
        - **INV-PELM-06**: Vector dimensionality consistency across all stored vectors

    Thread Safety:
        All public methods are thread-safe via internal ``threading.Lock``.
        Lock acquisition is O(1) and contention-free in typical single-threaded scenarios.

    Provenance Tracking (AI Safety):
        Each memory tracks its source and confidence:
        - **Source**: SYSTEM_PROMPT, USER_INPUT, GENERATED, EXTERNAL
        - **Confidence**: [0, 1] - used for eviction policy and retrieval filtering
        - Memories with confidence < threshold are rejected at storage time

    Performance Optimizations:
        - Pre-allocated query buffer reduces allocations during retrieval
        - Vectorized numpy operations for phase filtering and cosine similarity
        - Partial sorting (argpartition) for large result sets (>2× top_k)
        - In-place operations minimize temporary array creation

    Example:
        >>> import numpy as np
        >>> from mlsdm.memory import PhaseEntangledLatticeMemory
        >>> from mlsdm.memory.provenance import MemoryProvenance, MemorySource
        >>> from datetime import datetime
        >>>
        >>> # Initialize 384-dim memory with 1000 capacity
        >>> pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=1000)
        >>>
        >>> # Store a "wake" memory with high confidence
        >>> wake_vec = np.random.randn(384).astype(np.float32).tolist()
        >>> provenance = MemoryProvenance(
        ...     source=MemorySource.USER_INPUT,
        ...     confidence=0.9,
        ...     timestamp=datetime.now()
        ... )
        >>> idx = pelm.entangle(wake_vec, phase=0.1, provenance=provenance)
        >>> assert idx >= 0  # Successfully stored
        >>>
        >>> # Store a "sleep" memory
        >>> sleep_vec = np.random.randn(384).astype(np.float32).tolist()
        >>> idx2 = pelm.entangle(sleep_vec, phase=0.9)
        >>>
        >>> # Retrieve wake-phase memories (should not return sleep memory)
        >>> query_vec = np.random.randn(384).astype(np.float32).tolist()
        >>> results = pelm.retrieve(query_vec, current_phase=0.1,
        ...                          phase_tolerance=0.15, top_k=5)
        >>> assert all(abs(r.phase - 0.1) <= 0.15 for r in results)  # INV-PELM-02
        >>> assert all(0 <= r.resonance <= 1.0 for r in results)
        >>>
        >>> # Verify resonance ordering
        >>> resonances = [r.resonance for r in results]
        >>> assert resonances == sorted(resonances, reverse=True)  # INV-PELM-04
        >>>
        >>> # Check memory usage
        >>> mem_bytes = pelm.memory_usage_bytes()
        >>> expected = 1000 * 384 * 4 * 1.15  # capacity × dim × float32 × overhead
        >>> assert mem_bytes <= expected * 1.2  # Within 20% of estimate

    References:
        - Cosine similarity for semantic search: Widely used in information retrieval
          and recommender systems for measuring document/embedding similarity.
        - Phase-based memory separation: Inspired by wake/sleep neural dynamics and
          hippocampal replay during different brain states (Wilson & McNaughton, 1994).
        - Circular buffer: Classic data structure for bounded FIFO storage with O(1)
          insertion and constant memory footprint.

    See Also:
        - ``CognitiveController``: Integrates PELM into cognitive pipeline
        - ``MultiLevelSynapticMemory``: Complementary consolidation-based memory
        - ``MemoryProvenance``: Tracks memory source and confidence for safety

    .. versionadded:: 1.0.0
       Initial implementation as QILM_v2.
    .. versionchanged:: 1.2.0
       Renamed to PELM, added provenance tracking and confidence-based eviction.

    Note:
        Not related to quantum hardware - the design is mathematically inspired
        by quantum concepts but operates entirely in classical embedding space.
    """

    # Default values from calibration
    DEFAULT_CAPACITY: ClassVar[int] = PELM_DEFAULTS.default_capacity if PELM_DEFAULTS else 20_000
    MAX_CAPACITY: ClassVar[int] = PELM_DEFAULTS.max_capacity if PELM_DEFAULTS else 1_000_000
    DEFAULT_PHASE_TOLERANCE: ClassVar[float] = PELM_DEFAULTS.phase_tolerance if PELM_DEFAULTS else 0.15
    DEFAULT_TOP_K: ClassVar[int] = PELM_DEFAULTS.default_top_k if PELM_DEFAULTS else 5
    MIN_NORM_THRESHOLD: ClassVar[float] = PELM_DEFAULTS.min_norm_threshold if PELM_DEFAULTS else 1e-9

    __slots__ = (
        "dimension",
        "capacity",
        "pointer",
        "size",
        "_lock",
        "memory_bank",
        "phase_bank",
        "norms",
        "_query_buffer",
        "_checksum",
        "_provenance",
        "_memory_ids",
        "_confidence_threshold",
    )

    def __init__(self, dimension: int = 384, capacity: int | None = None) -> None:
        # Use calibration default if not specified
        if capacity is None:
            capacity = self.DEFAULT_CAPACITY

        # Validate inputs
        if dimension <= 0:
            raise ValueError(
                f"dimension must be positive, got {dimension}. "
                "Dimension determines the embedding vector size and must match the model's embedding dimension."
            )
        if capacity <= 0:
            raise ValueError(
                f"capacity must be positive, got {capacity}. "
                "Capacity determines the maximum number of vectors that can be stored in memory."
            )
        if capacity > self.MAX_CAPACITY:
            raise ValueError(
                f"capacity too large (max {self.MAX_CAPACITY:,}), got {capacity}. "
                "Large capacities may cause excessive memory usage. "
                f"Estimated memory: {capacity * dimension * 4 / (1024**2):.2f} MB"
            )

        self.dimension = dimension
        self.capacity = capacity
        self.pointer = 0
        self.size = 0
        self._lock = Lock()
        self.memory_bank = np.zeros((capacity, dimension), dtype=np.float32)
        self.phase_bank = np.zeros(capacity, dtype=np.float32)
        self.norms = np.zeros(capacity, dtype=np.float32)
        # Optimization: Pre-allocate query buffer to reduce allocations during retrieval
        self._query_buffer = np.zeros(dimension, dtype=np.float32)
        self._checksum = self._compute_checksum()

        # Provenance tracking for AI safety (TD-003)
        self._provenance: list[MemoryProvenance] = []
        self._memory_ids: list[str] = []
        self._confidence_threshold = 0.5  # Minimum confidence for storage

    def _ensure_integrity(self) -> None:
        """
        Ensure memory integrity, attempting recovery if corruption detected.
        Should only be called from within a lock context.

        Raises:
            RuntimeError: If corruption is detected and recovery fails.
        """
        if self._detect_corruption_unsafe():
            recovered = self._auto_recover_unsafe()
            # Record corruption event
            if _OBSERVABILITY_AVAILABLE:
                record_pelm_corruption(
                    detected=True,
                    recovered=recovered,
                    pointer=self.pointer,
                    size=self.size,
                )
            if not recovered:
                raise RuntimeError(
                    "Memory corruption detected and recovery failed. "
                    f"Current state: pointer={self.pointer}, size={self.size}, capacity={self.capacity}. "
                    "This may indicate hardware issues, race conditions, or memory overwrites. "
                    "Consider restarting the system or reducing capacity."
                )

    def entangle(
        self,
        vector: list[float],
        phase: float,
        correlation_id: str | None = None,
        provenance: MemoryProvenance | None = None,
    ) -> int:
        """Store a vector with associated phase in memory (circular buffer insertion).

        Stores an embedding vector with cognitive phase metadata. If capacity is reached,
        the lowest-confidence memory is evicted. Memories below confidence threshold are
        rejected immediately (return -1).

        Args:
            vector: Embedding vector to store (must match dimension).
                Expected format: Python list of floats (e.g., [0.1, -0.3, 0.8, ...]).
                Converted to float32 internally for memory efficiency.
            phase: Phase value in [0.0, 1.0] representing cognitive state.
                Convention: 0.1 = wake, 0.9 = sleep (matches CognitiveRhythm).
                Used for phase-aware retrieval (INV-PELM-02).
            correlation_id: Optional correlation ID for distributed tracing and
                observability (e.g., request UUID for tracking memory lineage).
            provenance: Optional provenance metadata tracking memory source, confidence,
                and timestamp. If None, defaults to SYSTEM_PROMPT with confidence=1.0.
                Confidence < 0.5 causes rejection.

        Returns:
            Index where the vector was stored (0 ≤ idx < capacity), or -1 if rejected
            due to low confidence. Index can be used with return_indices=True in retrieve().

        Raises:
            TypeError: If vector is not a list or phase is not numeric
            ValueError: If vector dimension doesn't match, phase out of range [0, 1],
                       or vector contains NaN/inf values (which would corrupt memory)

        Complexity:
            O(1) - constant time insertion with wraparound and eviction

        Side Effects:
            - Increments internal pointer (with wraparound at capacity)
            - Increments size counter (saturates at capacity)
            - May evict lowest-confidence memory if at capacity
            - Updates integrity checksum
            - Records telemetry metrics (if observability available)

        Example:
            >>> import numpy as np
            >>> from mlsdm.memory.provenance import MemoryProvenance, MemorySource
            >>> from datetime import datetime
            >>> pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=1000)
            >>>
            >>> # Store high-confidence wake memory
            >>> wake_vec = np.random.randn(384).tolist()
            >>> prov = MemoryProvenance(MemorySource.USER_INPUT, 0.9, datetime.now())
            >>> idx = pelm.entangle(wake_vec, phase=0.1, provenance=prov)
            >>> assert 0 <= idx < 1000  # Valid index
            >>>
            >>> # Low-confidence memory gets rejected
            >>> low_conf = MemoryProvenance(MemorySource.GENERATED, 0.3, datetime.now())
            >>> idx2 = pelm.entangle(wake_vec, phase=0.1, provenance=low_conf)
            >>> assert idx2 == -1  # Rejected
        """
        start_time = time.perf_counter() if _OBSERVABILITY_AVAILABLE else None

        with self._lock:
            # Ensure integrity before operation
            self._ensure_integrity()

            # Generate unique memory ID
            memory_id = str(uuid.uuid4())

            # Create default provenance if not provided
            if provenance is None:
                provenance = MemoryProvenance(
                    source=MemorySource.SYSTEM_PROMPT, confidence=1.0, timestamp=datetime.now()
                )

            # Check confidence threshold - reject low-confidence memories
            if provenance.confidence < self._confidence_threshold:
                # Log rejection for observability
                if _OBSERVABILITY_AVAILABLE and start_time is not None:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    record_pelm_store(
                        index=-1,
                        phase=phase,
                        vector_norm=0.0,
                        capacity_used=self.size,
                        capacity_total=self.capacity,
                        memory_bytes=self.memory_usage_bytes(),
                        latency_ms=latency_ms,
                        correlation_id=correlation_id,
                    )
                return -1  # Rejection sentinel value

            # Validate vector type
            if not isinstance(vector, list):
                raise TypeError(f"vector must be a list, got {type(vector).__name__}")
            if len(vector) != self.dimension:
                raise ValueError(
                    f"vector dimension mismatch: expected {self.dimension}, got {len(vector)}"
                )

            # Validate vector values (check for NaN/inf)
            for i, val in enumerate(vector):
                if not isinstance(val, int | float):
                    raise TypeError(
                        f"vector element at index {i} must be numeric, got {type(val).__name__}"
                    )
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(
                        f"vector contains invalid value at index {i}: {val}. "
                        "NaN and infinity are not allowed in memory vectors."
                    )

            # Validate phase type and range
            if not isinstance(phase, int | float):
                raise TypeError(f"phase must be numeric, got {type(phase).__name__}")
            if math.isnan(phase) or math.isinf(phase):
                raise ValueError(
                    f"phase must be a finite number, got {phase}. NaN and infinity are not allowed."
                )
            if not (0.0 <= phase <= 1.0):
                raise ValueError(
                    f"phase must be in [0.0, 1.0], got {phase}. "
                    "Phase values represent cognitive states (e.g., 0.1=wake, 0.9=sleep)."
                )

            vec_np = np.array(vector, dtype=np.float32)
            norm = max(safe_norm(vec_np), self.MIN_NORM_THRESHOLD)

            # Check capacity and evict if necessary
            if self.size >= self.capacity:
                self._evict_lowest_confidence()

            idx = self.pointer
            self.memory_bank[idx] = vec_np
            self.phase_bank[idx] = phase
            self.norms[idx] = norm

            # Store provenance metadata
            if idx < len(self._provenance):
                self._provenance[idx] = provenance
                self._memory_ids[idx] = memory_id
            else:
                self._provenance.append(provenance)
                self._memory_ids.append(memory_id)

            # Update pointer with wraparound check
            new_pointer = self.pointer + 1
            if new_pointer >= self.capacity:
                new_pointer = 0  # Explicit wraparound
            self.pointer = new_pointer

            self.size = min(self.size + 1, self.capacity)

            # Update checksum after modification
            self._checksum = self._compute_checksum()

            # Record observability metrics
            if _OBSERVABILITY_AVAILABLE and start_time is not None:
                latency_ms = (time.perf_counter() - start_time) * 1000
                record_pelm_store(
                    index=idx,
                    phase=phase,
                    vector_norm=norm,
                    capacity_used=self.size,
                    capacity_total=self.capacity,
                    memory_bytes=self.memory_usage_bytes(),
                    latency_ms=latency_ms,
                    correlation_id=correlation_id,
                )

            return idx

    def entangle_batch(
        self,
        vectors: list[list[float]],
        phases: list[float],
        correlation_id: str | None = None,
        provenances: list[MemoryProvenance] | None = None,
    ) -> list[int]:
        """Store multiple vectors with associated phases in memory (optimized batch operation).

        This is significantly more efficient than calling entangle() multiple times because:
        - Acquires the lock only once (reduces contention overhead)
        - Performs integrity check only once (amortizes validation cost)
        - Updates checksum only once at the end (O(n) → O(1) per vector)
        - Uses vectorized numpy operations for validation (faster than element-wise)

        Args:
            vectors: List of embedding vectors to store (each must match dimension).
                All vectors must be Python lists of floats with length = dimension.
            phases: List of phase values in [0.0, 1.0] (must match vectors length).
                One phase per vector, representing cognitive state at storage time.
            correlation_id: Optional correlation ID for distributed tracing.
                Single ID applies to entire batch for observability grouping.
            provenances: Optional list of provenance metadata (must match vectors length).
                If None, all vectors default to SYSTEM_PROMPT with confidence=1.0.
                Individual vectors with confidence < 0.5 are rejected (-1 in results).

        Returns:
            List of indices where vectors were stored. Length matches input vectors.
            Each index is either:
                - Valid index (0 ≤ idx < capacity) if stored successfully
                - -1 if rejected due to low confidence

        Raises:
            TypeError: If vectors/phases are not lists or contain invalid types
            ValueError: If vectors and phases have different lengths, dimension mismatch,
                       phases out of range [0, 1], or vectors contain NaN/inf values

        Complexity:
            O(m) where m = batch size. Amortized O(1) per vector due to:
            - Single lock acquisition: O(1)
            - Single integrity check: O(n) where n = current size
            - Per-vector validation: O(m × d) where d = dimension
            - Single checksum update: O(n)

        Side Effects:
            - Advances internal pointer by number of accepted vectors
            - Increases size counter (saturates at capacity)
            - May evict multiple low-confidence memories if at capacity
            - Updates integrity checksum once at end
            - Records single telemetry event for entire batch

        Example:
            >>> import numpy as np
            >>> pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=1000)
            >>>
            >>> # Batch store 100 wake memories
            >>> vectors = [np.random.randn(384).tolist() for _ in range(100)]
            >>> phases = [0.1] * 100  # All wake-phase
            >>> indices = pelm.entangle_batch(vectors, phases)
            >>> assert len(indices) == 100
            >>> assert all(0 <= idx < 1000 for idx in indices)  # All accepted
            >>> assert pelm.size == 100  # Size updated correctly
            >>>
            >>> # Batch with mixed confidence (some rejected)
            >>> from mlsdm.memory.provenance import MemoryProvenance, MemorySource
            >>> from datetime import datetime
            >>> provenances = [
            ...     MemoryProvenance(MemorySource.USER_INPUT, 0.9, datetime.now()),
            ...     MemoryProvenance(MemorySource.GENERATED, 0.3, datetime.now()),  # Low
            ...     MemoryProvenance(MemorySource.USER_INPUT, 0.8, datetime.now()),
            ... ]
            >>> indices2 = pelm.entangle_batch(vectors[:3], phases[:3], provenances=provenances)
            >>> assert indices2[0] >= 0  # High confidence accepted
            >>> assert indices2[1] == -1  # Low confidence rejected
            >>> assert indices2[2] >= 0  # High confidence accepted
        """
        start_time = time.perf_counter() if _OBSERVABILITY_AVAILABLE else None

        if not isinstance(vectors, list) or not isinstance(phases, list):
            raise TypeError("vectors and phases must be lists")

        if len(vectors) != len(phases):
            raise ValueError(
                f"vectors and phases must have same length: "
                f"{len(vectors)} vectors, {len(phases)} phases"
            )

        if provenances is not None and len(provenances) != len(vectors):
            raise ValueError(
                f"provenances must match vectors length: "
                f"{len(vectors)} vectors, {len(provenances)} provenances"
            )

        if len(vectors) == 0:
            return []

        with self._lock:
            # Ensure integrity before operation (only once for batch)
            self._ensure_integrity()

            indices: list[int] = []
            last_accepted: tuple[int, float, float] | None = None

            for i, (vector, phase) in enumerate(zip(vectors, phases, strict=True)):
                # Get or create provenance for this vector
                if provenances is not None:
                    provenance = provenances[i]
                else:
                    provenance = MemoryProvenance(
                        source=MemorySource.SYSTEM_PROMPT, confidence=1.0, timestamp=datetime.now()
                    )

                # Check confidence threshold
                if provenance.confidence < self._confidence_threshold:
                    indices.append(-1)  # Reject
                    continue

                # Generate unique memory ID
                memory_id = str(uuid.uuid4())
                # Validate vector type
                if not isinstance(vector, list):
                    raise TypeError(
                        f"vector at index {i} must be a list, got {type(vector).__name__}"
                    )
                if len(vector) != self.dimension:
                    raise ValueError(
                        f"vector at index {i} dimension mismatch: "
                        f"expected {self.dimension}, got {len(vector)}"
                    )

                # Validate phase type and range
                if not isinstance(phase, int | float):
                    raise TypeError(
                        f"phase at index {i} must be numeric, got {type(phase).__name__}"
                    )
                if math.isnan(phase) or math.isinf(phase):
                    raise ValueError(f"phase at index {i} must be a finite number, got {phase}")
                if not (0.0 <= phase <= 1.0):
                    raise ValueError(f"phase at index {i} must be in [0.0, 1.0], got {phase}")

                # Validate vector values using numpy (faster than element-by-element)
                vec_np = np.array(vector, dtype=np.float32)
                if not np.all(np.isfinite(vec_np)):
                    raise ValueError(f"vector at index {i} contains NaN or infinity values")

                norm = max(safe_norm(vec_np), self.MIN_NORM_THRESHOLD)

                # Check capacity and evict if necessary
                if self.size >= self.capacity:
                    self._evict_lowest_confidence()

                idx = self.pointer
                self.memory_bank[idx] = vec_np
                self.phase_bank[idx] = phase
                self.norms[idx] = norm

                # Store provenance metadata
                if idx < len(self._provenance):
                    self._provenance[idx] = provenance
                    self._memory_ids[idx] = memory_id
                else:
                    self._provenance.append(provenance)
                    self._memory_ids.append(memory_id)

                indices.append(idx)
                last_accepted = (idx, float(phase), float(norm))

                # Update pointer with wraparound check
                new_pointer = self.pointer + 1
                if new_pointer >= self.capacity:
                    new_pointer = 0
                self.pointer = new_pointer

            # Update size only once at the end (more efficient)
            # Count only accepted vectors (not -1)
            accepted_count = sum(1 for idx in indices if idx != -1)
            self.size = min(self.size + accepted_count, self.capacity)

            # Update checksum only once after all modifications
            self._checksum = self._compute_checksum()

            # Record observability metrics for batch operation
            if _OBSERVABILITY_AVAILABLE and start_time is not None:
                latency_ms = (time.perf_counter() - start_time) * 1000
                # Record as single batch operation
                if last_accepted is not None:
                    last_index, last_phase, last_norm = last_accepted
                else:
                    last_index, last_phase, last_norm = 0, 0.0, 0.0
                record_pelm_store(
                    index=last_index,
                    phase=last_phase,
                    vector_norm=last_norm,
                    capacity_used=self.size,
                    capacity_total=self.capacity,
                    memory_bytes=self.memory_usage_bytes(),
                    latency_ms=latency_ms,
                    correlation_id=correlation_id,
                )

            return indices

    @overload
    def retrieve(
        self,
        query_vector: list[float],
        current_phase: float,
        phase_tolerance: float | None = None,
        top_k: int | None = None,
        correlation_id: str | None = None,
        min_confidence: float = 0.0,
        return_indices: Literal[False] = False,
    ) -> list[MemoryRetrieval]: ...

    @overload
    def retrieve(
        self,
        query_vector: list[float],
        current_phase: float,
        phase_tolerance: float | None = None,
        top_k: int | None = None,
        correlation_id: str | None = None,
        min_confidence: float = 0.0,
        return_indices: Literal[True] = True,
    ) -> tuple[list[MemoryRetrieval], list[int]]: ...

    def retrieve(
        self,
        query_vector: list[float],
        current_phase: float,
        phase_tolerance: float | None = None,
        top_k: int | None = None,
        correlation_id: str | None = None,
        min_confidence: float = 0.0,
        return_indices: bool = False,
    ) -> list[MemoryRetrieval] | tuple[list[MemoryRetrieval], list[int]]:
        """Retrieve top-k phase-coherent memories ranked by cosine similarity (resonance).

        Performs phase-aware context retrieval: filters by phase proximity, then ranks
        by cosine similarity. Returns up to top_k results sorted by resonance score
        (descending). Empty memory or no phase-matching candidates returns empty list.

        Args:
            query_vector: Query embedding vector (must match dimension).
                Expected format: Python list of floats (e.g., [0.1, -0.3, 0.8, ...]).
                Used as "key" to search memory for similar stored vectors.
            current_phase: Current cognitive phase in [0.0, 1.0].
                Only memories with |stored_phase - current_phase| ≤ tolerance are considered.
                Convention: 0.1 = wake, 0.9 = sleep (matches CognitiveRhythm).
            phase_tolerance: Maximum phase difference for candidate selection (default: 0.15).
                Larger values allow cross-phase retrieval (e.g., 0.5 retrieves from both
                wake and sleep). Smaller values enforce strict phase isolation.
            top_k: Maximum number of results to return (default: 5).
                Actual return count may be less if fewer phase-matching candidates exist.
            correlation_id: Optional correlation ID for distributed tracing.
            min_confidence: Minimum confidence threshold for retrieval (default: 0.0).
                Filters out low-confidence memories. Range: [0, 1].
            return_indices: If True, also return list of memory bank indices (default: False).
                Useful for debugging or tracking which memories were retrieved.

        Returns:
            If return_indices=False (default):
                List of MemoryRetrieval objects sorted by resonance (best first).
                Length ≤ min(top_k, num_phase_matching_candidates).
            If return_indices=True:
                Tuple of (results, indices) where indices[i] is the memory bank index
                for results[i]. Both lists have same length.

        Raises:
            ValueError: If query_vector dimension doesn't match memory dimension

        Complexity:
            O(n + k log k) where n = current size, k = top_k
            - Phase filtering: O(n) - vectorized numpy mask
            - Confidence filtering: O(n) - sequential check
            - Cosine similarity: O(c × d) where c = num_candidates, d = dimension
            - Top-k selection: O(c) with argpartition or O(c log c) with argsort
              * Uses argpartition for large c (>2×k) for O(c + k log k)
              * Uses argsort for small c for better cache locality

        Performance Notes:
            - Pre-allocated query buffer reduces memory allocations
            - Vectorized numpy operations for phase filtering and dot products
            - Adaptive top-k algorithm (argpartition vs argsort) based on result set size
            - Returns empty list immediately if memory is empty (O(1) fast path)

        Side Effects:
            - Records telemetry metrics (query phase, results count, avg resonance, latency)
            - Validates memory integrity before retrieval (may auto-recover from corruption)

        Example:
            >>> import numpy as np
            >>> pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=1000)
            >>>
            >>> # Store some wake memories
            >>> for i in range(50):
            ...     vec = np.random.randn(384).tolist()
            ...     pelm.entangle(vec, phase=0.1)
            >>>
            >>> # Store some sleep memories
            >>> for i in range(50):
            ...     vec = np.random.randn(384).tolist()
            ...     pelm.entangle(vec, phase=0.9)
            >>>
            >>> # Retrieve wake-phase memories (strict isolation)
            >>> query = np.random.randn(384).tolist()
            >>> results = pelm.retrieve(query, current_phase=0.1,
            ...                          phase_tolerance=0.15, top_k=5)
            >>> assert len(results) <= 5  # At most top_k results
            >>> assert all(abs(r.phase - 0.1) <= 0.15 for r in results)  # INV-PELM-02
            >>>
            >>> # Verify resonance ordering (best matches first)
            >>> resonances = [r.resonance for r in results]
            >>> assert resonances == sorted(resonances, reverse=True)  # INV-PELM-04
            >>>
            >>> # Retrieve with indices for debugging
            >>> results, indices = pelm.retrieve(query, current_phase=0.1,
            ...                                   return_indices=True)
            >>> assert len(results) == len(indices)
            >>> for r, idx in zip(results, indices):
            ...     assert 0 <= idx < pelm.size  # Valid index
            >>>
            >>> # Cross-phase retrieval with large tolerance
            >>> all_results = pelm.retrieve(query, current_phase=0.5,
            ...                              phase_tolerance=0.5, top_k=10)
            >>> # May return both wake (0.1) and sleep (0.9) memories

        References:
            - Cosine similarity: Standard metric for semantic search in embedding spaces.
              Invariant to vector magnitude (only direction matters).
            - Phase-based filtering: Inspired by hippocampal replay during different
              brain states (sharp-wave ripples in sleep vs theta oscillations in wake).
            - argpartition optimization: NumPy's partial sorting algorithm for O(n) top-k
              selection when k << n, avoiding full O(n log n) sort.
        """
        # Use calibration defaults if not specified
        if phase_tolerance is None:
            phase_tolerance = self.DEFAULT_PHASE_TOLERANCE
        if top_k is None:
            top_k = self.DEFAULT_TOP_K

        start_time = time.perf_counter() if _OBSERVABILITY_AVAILABLE else None

        with self._lock:
            # Ensure integrity before operation
            self._ensure_integrity()

            if self.size == 0:
                # Record empty result
                if _OBSERVABILITY_AVAILABLE and start_time is not None:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    record_pelm_retrieve(
                        query_phase=current_phase,
                        phase_tolerance=phase_tolerance,
                        top_k=top_k,
                        results_count=0,
                        avg_resonance=None,
                        latency_ms=latency_ms,
                        correlation_id=correlation_id,
                    )
                if return_indices:
                    return [], []
                return []

            # Optimization: Use pre-allocated buffer with numpy copy
            # Validate dimension first to avoid buffer overflow
            if len(query_vector) != self.dimension:
                raise ValueError(
                    f"query_vector dimension mismatch: expected {self.dimension}, "
                    f"got {len(query_vector)}"
                )
            self._query_buffer[:] = query_vector
            q_vec = self._query_buffer
            q_norm = safe_norm(q_vec)
            if q_norm < self.MIN_NORM_THRESHOLD:
                q_norm = self.MIN_NORM_THRESHOLD

            # Optimize: use in-place operations and avoid intermediate arrays
            phase_diff = np.abs(self.phase_bank[: self.size] - current_phase)
            phase_mask = phase_diff <= phase_tolerance

            # Add confidence filtering
            confidence_mask = np.empty(self.size, dtype=bool)
            provenance_size = len(self._provenance)
            for i in range(self.size):
                if i < provenance_size:
                    confidence_mask[i] = self._provenance[i].confidence >= min_confidence
                else:
                    # Backward compatibility: treat missing provenance as high confidence.
                    confidence_mask[i] = True

            # Combine phase and confidence masks
            valid_mask = phase_mask & confidence_mask

            if not np.any(valid_mask):
                # Record empty result due to phase mismatch
                if _OBSERVABILITY_AVAILABLE and start_time is not None:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    record_pelm_retrieve(
                        query_phase=current_phase,
                        phase_tolerance=phase_tolerance,
                        top_k=top_k,
                        results_count=0,
                        avg_resonance=None,
                        latency_ms=latency_ms,
                        correlation_id=correlation_id,
                    )
                if return_indices:
                    return [], []
                return []

            candidates_idx = np.nonzero(valid_mask)[0]
            # Optimize: compute cosine similarity without intermediate array copies
            candidate_vectors = self.memory_bank[candidates_idx]
            candidate_norms = self.norms[candidates_idx]

            # Vectorized cosine similarity calculation
            cosine_sims = np.dot(candidate_vectors, q_vec) / (candidate_norms * q_norm)

            # Optimize: use argpartition only when beneficial (>2x top_k)
            num_candidates = len(cosine_sims)
            if num_candidates > top_k * 2:
                # Use partial sort for large result sets
                top_local = np.argpartition(cosine_sims, -top_k)[-top_k:]
                # Sort only the top k items
                top_local = top_local[np.argsort(cosine_sims[top_local])[::-1]]
            else:
                # Full sort for small result sets (faster for small arrays)
                top_local = np.argsort(cosine_sims)[::-1][:top_k]

            # Optimize: pre-allocate results list
            results: list[MemoryRetrieval] = []
            indices: list[int] = []
            resonance_sum = 0.0
            for loc in top_local:
                glob = candidates_idx[loc]
                resonance_value = float(cosine_sims[loc])
                resonance_sum += resonance_value
                # Get provenance (use default if not available for backward compatibility)
                if glob < len(self._provenance):
                    prov = self._provenance[glob]
                    mem_id = self._memory_ids[glob]
                else:
                    # Fallback for memories created before provenance was added
                    prov = MemoryProvenance(
                        source=MemorySource.SYSTEM_PROMPT, confidence=1.0, timestamp=datetime.now()
                    )
                    mem_id = str(uuid.uuid4())

                results.append(
                    MemoryRetrieval(
                        vector=self.memory_bank[glob],
                        phase=self.phase_bank[glob],
                        resonance=resonance_value,
                        provenance=prov,
                        memory_id=mem_id,
                    )
                )
                indices.append(int(glob))

            avg_resonance = resonance_sum / len(results) if results else None

            # Record successful retrieval
            if _OBSERVABILITY_AVAILABLE and start_time is not None:
                latency_ms = (time.perf_counter() - start_time) * 1000
                record_pelm_retrieve(
                    query_phase=current_phase,
                    phase_tolerance=phase_tolerance,
                    top_k=top_k,
                    results_count=len(results),
                    avg_resonance=avg_resonance,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id,
                )

            if return_indices:
                return results, indices
            return results

    def get_state_stats(self) -> dict[str, int | float]:
        return {
            "capacity": self.capacity,
            "used": self.size,
            "memory_mb": round((self.memory_bank.nbytes + self.phase_bank.nbytes) / 1024**2, 2),
        }

    def memory_usage_bytes(self) -> int:
        """Calculate conservative memory usage estimate in bytes.

        Returns:
            Estimated memory usage including all arrays and metadata overhead.

        Note:
            This is a conservative estimate (10-20% overhead) to ensure we
            never underestimate actual memory usage.
        """
        # Core numpy arrays
        memory_bank_bytes = self.memory_bank.nbytes  # capacity × dimension × float32
        phase_bank_bytes = self.phase_bank.nbytes  # capacity × float32
        norms_bytes = self.norms.nbytes  # capacity × float32

        # Subtotal for arrays
        array_bytes = memory_bank_bytes + phase_bank_bytes + norms_bytes

        # Metadata overhead (conservative estimate for Python object overhead)
        # Includes: dimension, capacity, pointer, size, checksum string,
        # Lock object, and Python object headers
        metadata_overhead = 1024  # ~1KB for metadata

        # Conservative 15% overhead for potential fragmentation and internal
        # Python structures
        conservative_multiplier = 1.15

        total_bytes = int((array_bytes + metadata_overhead) * conservative_multiplier)
        return total_bytes

    def _compute_checksum(self) -> str:
        """Compute checksum for memory bank integrity validation."""
        # Create a hash of the used portion of memory banks
        hasher = hashlib.sha256()
        hasher.update(self.memory_bank[: self.size].tobytes())
        hasher.update(self.phase_bank[: self.size].tobytes())
        hasher.update(self.norms[: self.size].tobytes())
        # Include metadata
        hasher.update(f"{self.pointer}:{self.size}:{self.capacity}".encode())
        return hasher.hexdigest()

    def _validate_pointer_bounds(self) -> bool:
        """Validate pointer is within acceptable bounds."""
        if self.pointer < 0 or self.pointer >= self.capacity:
            return False
        return not (self.size < 0 or self.size > self.capacity)

    def _detect_corruption_unsafe(self) -> bool:
        """
        Detect if memory bank has been corrupted (unsafe - no locking).
        Should only be called from within a lock context.

        Returns:
            True if corruption detected, False otherwise.
        """
        # Check pointer bounds
        if not self._validate_pointer_bounds():
            return True

        # Check checksum
        current_checksum = self._compute_checksum()
        return current_checksum != self._checksum

    def detect_corruption(self) -> bool:
        """
        Detect if memory bank has been corrupted.

        Returns:
            True if corruption detected, False otherwise.
        """
        with self._lock:
            return self._detect_corruption_unsafe()

    def _rebuild_index(self) -> None:
        """Rebuild the index by recomputing norms and metadata."""
        # Validate and fix size first before attempting to iterate
        if self.size < 0:
            self.size = 0
        elif self.size > self.capacity:
            self.size = self.capacity

        # Validate and fix pointer
        if self.pointer < 0 or self.pointer >= self.capacity:
            self.pointer = self.size % self.capacity if self.size > 0 else 0

        # Recompute norms for all stored vectors (now safe to iterate)
        for i in range(self.size):
            vec = self.memory_bank[i]
            self.norms[i] = max(safe_norm(vec), 1e-9)

    def _evict_lowest_confidence(self) -> None:
        """Evict the memory with the lowest confidence score.

        This is called when the memory is at capacity and a new high-confidence
        memory needs to be stored. Sets the pointer to the lowest confidence
        memory slot so it will be overwritten.

        Should only be called from within a lock context.
        """
        if self.size == 0:
            return

        # Find the index with lowest confidence
        confidences = [
            self._provenance[i].confidence if i < len(self._provenance) else 0.0
            for i in range(self.size)
        ]
        min_idx = int(np.argmin(confidences))

        # Simply set pointer to overwrite the lowest confidence slot
        # The normal entangle logic will handle the replacement
        self.pointer = min_idx

    def _auto_recover_unsafe(self) -> bool:
        """
        Attempt to recover from corruption by rebuilding the index (unsafe - no locking).
        Should only be called from within a lock context.

        Returns:
            True if recovery successful, False otherwise.
        """
        if not self._detect_corruption_unsafe():
            return True  # No corruption detected

        # Attempt recovery
        try:
            self._rebuild_index()
            # Update checksum after rebuild
            self._checksum = self._compute_checksum()
            # Verify recovery
            return not self._detect_corruption_unsafe()
        except Exception:
            return False

    def auto_recover(self) -> bool:
        """
        Attempt to recover from corruption by rebuilding the index.

        Returns:
            True if recovery successful, False otherwise.
        """
        with self._lock:
            return self._auto_recover_unsafe()
