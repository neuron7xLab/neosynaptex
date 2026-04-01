import logging
import time
from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING, Any, Final, cast

import numpy as np
import psutil

from ..memory.phase_entangled_lattice_memory import MemoryRetrieval
from ..observability.metrics import get_metrics_exporter
from ..observability.tracing import get_tracer_manager
from .governance_kernel import GovernanceKernel, PelmRO

if TYPE_CHECKING:
    from mlsdm.config import SynapticMemoryCalibration

# Import recovery calibration parameters and synaptic memory defaults
# Type annotations use X | None since module may not be available
_SYNAPTIC_MEMORY_DEFAULTS: "SynapticMemoryCalibration | None" = None
_get_synaptic_memory_config: (
    Callable[[dict[str, Any] | None], "SynapticMemoryCalibration"] | None
) = None

# Default max memory bytes: 1.4 GB (constant - never modified)
_DEFAULT_MAX_MEMORY_BYTES: Final[int] = int(1.4 * 1024**3)

# Recovery and controller constants - assigned once in try-except block below
# Using module-level declarations to satisfy mypy Final semantics (PEP 591)
_CC_RECOVERY_COOLDOWN_STEPS: int
_CC_RECOVERY_MEMORY_SAFETY_RATIO: float
_CC_RECOVERY_MAX_ATTEMPTS: int
_CC_MAX_MEMORY_BYTES: int
_CC_AUTO_RECOVERY_ENABLED: bool
_CC_AUTO_RECOVERY_COOLDOWN_SECONDS: float

try:
    from mlsdm.config import (
        COGNITIVE_CONTROLLER_DEFAULTS,
    )
    from mlsdm.config import (
        SYNAPTIC_MEMORY_DEFAULTS as _IMPORTED_DEFAULTS,
    )
    from mlsdm.config import (
        get_synaptic_memory_config as _imported_get_config,
    )

    _CC_RECOVERY_COOLDOWN_STEPS = COGNITIVE_CONTROLLER_DEFAULTS.recovery_cooldown_steps
    _CC_RECOVERY_MEMORY_SAFETY_RATIO = COGNITIVE_CONTROLLER_DEFAULTS.recovery_memory_safety_ratio
    _CC_RECOVERY_MAX_ATTEMPTS = COGNITIVE_CONTROLLER_DEFAULTS.recovery_max_attempts
    _CC_MAX_MEMORY_BYTES = COGNITIVE_CONTROLLER_DEFAULTS.max_memory_bytes
    _CC_AUTO_RECOVERY_ENABLED = COGNITIVE_CONTROLLER_DEFAULTS.auto_recovery_enabled
    _CC_AUTO_RECOVERY_COOLDOWN_SECONDS = (
        COGNITIVE_CONTROLLER_DEFAULTS.auto_recovery_cooldown_seconds
    )
    _SYNAPTIC_MEMORY_DEFAULTS = _IMPORTED_DEFAULTS
    _get_synaptic_memory_config = _imported_get_config
except ImportError:
    # Fallback defaults if calibration module is not available
    _CC_RECOVERY_COOLDOWN_STEPS = 10
    _CC_RECOVERY_MEMORY_SAFETY_RATIO = 0.8
    _CC_RECOVERY_MAX_ATTEMPTS = 3
    _CC_MAX_MEMORY_BYTES = _DEFAULT_MAX_MEMORY_BYTES
    _CC_AUTO_RECOVERY_ENABLED = True
    _CC_AUTO_RECOVERY_COOLDOWN_SECONDS = 60.0

logger = logging.getLogger(__name__)


class CognitiveController:
    """Thread-safe orchestrator of cognitive subsystems with bounded resources.

    The CognitiveController coordinates moral filtering, circadian rhythm management,
    phase-entangled memory (PELM), and multi-level synaptic memory consolidation
    following neurobiological principles. It enforces strict resource bounds and
    provides automatic recovery from emergency states.

    Architecture:
        The controller integrates four core subsystems via a GovernanceKernel:

        1. **Moral Filter** (MoralFilterV2): EMA-based threshold adaptation with
           homeostatic control to maintain acceptance rates around 50%.

        2. **Cognitive Rhythm** (CognitiveRhythm): Deterministic wake/sleep cycling
           inspired by suprachiasmatic nucleus (SCN) circadian oscillators.

        3. **PELM** (PhaseEntangledLatticeMemory): Phase-aware vector retrieval with
           cosine similarity scoring and circular buffer eviction.

        4. **Synaptic Memory** (MultiLevelSynapticMemory): Three-level consolidation
           cascade (L1→L2→L3) implementing Benna & Fusi (2016) cascade model.

    Thread Safety:
        All public methods are thread-safe via a single threading.Lock protecting
        internal state. Lock acquisition is O(1) and contention-free in typical
        single-threaded scenarios. Concurrent calls serialize at the lock boundary.

    Invariants:
        - **INV-CC-01**: State transitions are atomic (protected by _lock)
        - **INV-CC-02**: Moral threshold ∈ [0.30, 0.90] after any operation
        - **INV-CC-03**: Memory usage ≤ max_memory_bytes after any commit operation
        - **INV-CC-04**: Emergency recovery attempts ≤ max_recovery_attempts
        - **INV-CC-05**: Step counter is monotonically increasing

    Complexity Analysis:
        - ``process_event()``: O(n + k log k) where n = PELM size, k = retrieval top_k
        - ``retrieve_context()``: O(n log k) where n = PELM size, k = top_k
        - ``memory_usage_bytes()``: O(1) - constant time aggregation
        - ``get_state()``: O(d) where d = vector dimension (for norm computation)

    Resource Bounds (CORE-04):
        The controller enforces a global memory bound across all subsystems:

        .. math::
            M_{total} = M_{PELM} + M_{synaptic} + M_{overhead} \\leq M_{max}

        Where:
            - :math:`M_{PELM} = capacity \\times dimension \\times 4` bytes (float32)
            - :math:`M_{synaptic} = 3 \\times dimension \\times 4` bytes (L1+L2+L3)
            - :math:`M_{overhead} \\approx 4` KB (controller state, caches, locks)
            - :math:`M_{max}` defaults to 1.4 GB (configurable)

    Emergency Shutdown & Recovery:
        When memory or processing time limits are exceeded, the controller enters
        emergency shutdown. Recovery is automatic after a cooldown period:

        .. math::
            t_{recovery} = \\max(t_{step\\_cooldown}, t_{time\\_cooldown})

        Where:
            - :math:`t_{step\\_cooldown}` = steps since emergency ≥ 10 steps
            - :math:`t_{time\\_cooldown}` = wall time since emergency ≥ 60 seconds

        Recovery requires memory usage < 80% of threshold (safety margin).

    References:
        - Benna, M. K., & Fusi, S. (2016). Computational principles of synaptic
          memory consolidation. Nature Neuroscience, 19(12), 1697-1706.
          DOI: 10.1038/nn.4401

        - Governing kernel pattern inspired by microkernel architectures ensuring
          subsystem isolation and resource enforcement.

    Example:
        >>> # Initialize controller with 384-dim embeddings, 20K capacity
        >>> controller = CognitiveController(dim=384, capacity=20_000)
        >>>
        >>> # Process a morally acceptable event
        >>> import numpy as np
        >>> event_vec = np.random.randn(384).astype(np.float32)
        >>> result = controller.process_event(event_vec, moral_value=0.8)
        >>> assert result['accepted'] in (True, False)
        >>> assert 0.30 <= result['moral_threshold'] <= 0.90  # INV-CC-02
        >>>
        >>> # Retrieve contextually similar memories
        >>> query_vec = np.random.randn(384).astype(np.float32)
        >>> memories = controller.retrieve_context(query_vec, top_k=5)
        >>> assert len(memories) <= 5
        >>> assert all(0 <= m.resonance <= 1.0 for m in memories)

    See Also:
        - ``GovernanceKernel``: Encapsulates subsystem coordination
        - ``MoralFilterV2``: EMA-based moral threshold adaptation
        - ``CognitiveRhythm``: Wake/sleep state machine
        - ``PhaseEntangledLatticeMemory``: Phase-aware vector storage
        - ``MultiLevelSynapticMemory``: Three-level consolidation cascade

    .. versionadded:: 1.0.0
    .. versionchanged:: 1.2.0
       Added time-based auto-recovery and global memory bound enforcement.
    """

    def __init__(
        self,
        dim: int = 384,
        memory_threshold_mb: float = 8192.0,
        max_processing_time_ms: float = 1000.0,
        *,
        max_memory_bytes: int | None = None,
        synaptic_config: "SynapticMemoryCalibration | None" = None,
        yaml_config: dict[str, Any] | None = None,
        auto_recovery_enabled: bool | None = None,
        auto_recovery_cooldown_seconds: float | None = None,
    ) -> None:
        """Initialize the CognitiveController with specified resource bounds.

        Args:
            dim: Vector dimension for embeddings. Must match the embedding model's
                output dimension (e.g., 384 for sentence-transformers/all-MiniLM-L6-v2).
                Valid range: [1, 4096]. Default: 384.

            memory_threshold_mb: Legacy psutil-based memory threshold in MB before
                emergency shutdown. This monitors process RSS memory.
                Default: 8192.0 MB (8 GB). Deprecated in favor of max_memory_bytes.

            max_processing_time_ms: Maximum allowed processing time per event in
                milliseconds. Events exceeding this are rejected to prevent DoS.
                Default: 1000.0 ms (1 second).

            max_memory_bytes: Global memory bound in bytes for cognitive circuit
                (PELM + SynapticMemory + controller buffers). This is the hard limit
                from CORE-04 specification enforcing INV-CC-03.
                Default: 1.4 GB (1,468,006,400 bytes).

            synaptic_config: Optional SynapticMemoryCalibration for synaptic memory
                parameters (λ decay rates, θ thresholds, gating factors). If provided,
                overrides SYNAPTIC_MEMORY_DEFAULTS. See SynapticMemoryCalibration docs.

            yaml_config: Optional YAML config dictionary. If provided and
                synaptic_config is None, loads synaptic memory config from
                'multi_level_memory' section merged with SYNAPTIC_MEMORY_DEFAULTS.
                Useful for production deployments with centralized configuration.

            auto_recovery_enabled: Enable time-based auto-recovery after emergency
                shutdown. When True, controller attempts recovery after cooldown period.
                When False, only step-based recovery is available. Default: True.

            auto_recovery_cooldown_seconds: Time in seconds to wait before attempting
                automatic recovery after emergency shutdown. Must be ≥ 0.
                Default: 60.0 seconds. Only applies when auto_recovery_enabled=True.

        Raises:
            ValueError: If dim ≤ 0 or synaptic_config parameters are invalid.

        Complexity:
            O(d × c) where d = dimension, c = capacity for memory allocation.
            Dominated by PELM and synaptic memory numpy array initialization.

        Postconditions:
            - emergency_shutdown = False
            - step_counter = 0
            - moral.threshold ∈ [0.30, 0.90]  (INV-CC-02)
            - memory_usage_bytes() ≤ max_memory_bytes  (INV-CC-03)
        """
        self.dim = dim
        self._lock = Lock()

        # Resolve synaptic memory configuration:
        # Priority: synaptic_config > yaml_config > SYNAPTIC_MEMORY_DEFAULTS
        resolved_config: SynapticMemoryCalibration | None = synaptic_config
        if resolved_config is None and yaml_config is not None:
            if _get_synaptic_memory_config is not None:
                resolved_config = _get_synaptic_memory_config(yaml_config)
        if resolved_config is None:
            resolved_config = _SYNAPTIC_MEMORY_DEFAULTS

        self._kernel = GovernanceKernel(
            dim=dim,
            capacity=20_000,
            wake_duration=8,
            sleep_duration=3,
            initial_moral_threshold=0.50,
            synaptic_config=resolved_config,
        )
        self._bind_kernel_views()
        self.step_counter = 0
        # Optimization: Cache for phase values to avoid repeated computation
        self._phase_cache: dict[str, float] = {"wake": 0.1, "sleep": 0.9}
        # Optimization: Cache for frequently accessed state values
        self._state_cache: dict[str, Any] = {}
        self._state_cache_valid = False
        # Memory monitoring and limits
        self.memory_threshold_mb = memory_threshold_mb
        self.max_processing_time_ms = max_processing_time_ms
        # Global memory bound (CORE-04): PELM + Synaptic + controller buffers
        self.max_memory_bytes = (
            max_memory_bytes if max_memory_bytes is not None else _CC_MAX_MEMORY_BYTES
        )
        self.emergency_shutdown = False
        self._emergency_reason: str | None = None
        self._process = psutil.Process()
        # Auto-recovery state tracking
        self._last_emergency_step: int = 0
        self._recovery_attempts: int = 0
        # Time-based auto-recovery (REL-001)
        self._last_emergency_time: float = 0.0
        self.auto_recovery_enabled = (
            auto_recovery_enabled
            if auto_recovery_enabled is not None
            else _CC_AUTO_RECOVERY_ENABLED
        )
        self.auto_recovery_cooldown_seconds = (
            auto_recovery_cooldown_seconds
            if auto_recovery_cooldown_seconds is not None
            else _CC_AUTO_RECOVERY_COOLDOWN_SECONDS
        )

    def _bind_kernel_views(self) -> None:
        """Expose read-only proxies from the governance kernel."""
        self.moral = self._kernel.moral_ro
        self.synaptic = self._kernel.synaptic_ro
        self.pelm = self._kernel.pelm_ro
        self.rhythm = self._kernel.rhythm_ro

    def rhythm_step(self) -> None:
        """Advance rhythm via governance kernel."""
        self._kernel.rhythm_step()

    def moral_adapt(self, accepted: bool) -> None:
        """Adapt moral filter via governance kernel."""
        self._kernel.moral_adapt(accepted)

    def memory_commit(
        self, vector: np.ndarray, phase: float, *, provenance: Any | None = None
    ) -> None:
        """Commit memory via governance kernel."""
        self._kernel.memory_commit(vector, phase, provenance=provenance)

    @property
    def qilm(self) -> PelmRO:
        """Backward compatibility alias for pelm (deprecated, use self.pelm instead).

        This property will be removed in v2.0.0. Migrate to using self.pelm directly.
        """
        return self.pelm

    def memory_usage_bytes(self) -> int:
        """Calculate total memory usage for cognitive circuit in bytes.

        Aggregates memory usage from:
        - PELM (Phase-Entangled Lattice Memory)
        - MultiLevelSynapticMemory (L1/L2/L3)
        - Controller internal buffers and overhead

        Returns:
            Total estimated memory usage in bytes (conservative estimate).

        Note:
            This method is thread-safe and can be called from outside the lock.
            Used for enforcing the global memory bound (CORE-04 invariant).
        """
        pelm_bytes = self.pelm.memory_usage_bytes()
        synaptic_bytes = self.synaptic.memory_usage_bytes()

        # Controller internal overhead (caches, state, locks, etc.)
        # Estimate: phase_cache dict, state_cache dict, misc Python object overhead
        controller_overhead = 4096  # ~4KB for internal structures

        return pelm_bytes + synaptic_bytes + controller_overhead

    def get_phase(self) -> str:
        """Get the current cognitive phase from rhythm.

        Read-only method for introspection - no side effects.

        Returns:
            Current phase as string (e.g., "wake", "sleep").
        """
        return self.rhythm.phase

    def get_step_counter(self) -> int:
        """Get the current step counter.

        Read-only method for introspection - no side effects.

        Returns:
            Current step count (number of processed events).
        """
        return self.step_counter

    def is_emergency_shutdown(self) -> bool:
        """Check if the controller is in emergency shutdown state.

        Read-only method for introspection - no side effects.

        Returns:
            True if emergency shutdown is active, False otherwise.
        """
        return self.emergency_shutdown

    def process_event(self, vector: np.ndarray, moral_value: float) -> dict[str, Any]:
        """Process a cognitive event through the full moral-memory pipeline.

        This is the primary interaction method for the cognitive architecture. It
        performs moral evaluation, phase checking, memory consolidation, and rhythm
        advancement in a single atomic operation. All subsystem interactions are
        wrapped with OpenTelemetry spans for observability.

        Processing Pipeline:
            1. **Emergency Check**: Verify controller is operational or attempt recovery
            2. **Memory Check**: Validate process memory < threshold (legacy psutil-based)
            3. **Moral Evaluation**: Score input against adaptive moral threshold
            4. **Phase Check**: Verify wake state (sleep phase rejects all events)
            5. **Memory Commit**: Store vector in PELM and update synaptic cascade
            6. **Rhythm Step**: Advance circadian counter
            7. **Bounds Check**: Validate global memory limit (CORE-04)
            8. **Timing Check**: Verify processing time < max_processing_time_ms

        Args:
            vector: Input embedding vector as numpy array. Must satisfy:
                - Shape: (dimension,) matching controller's dimension
                - Dtype: Any numeric type (will be converted to float32)
                - Values: Finite real numbers (no NaN or Inf)

            moral_value: Moral score for this interaction. Must satisfy:
                - Range: [0.0, 1.0] where 0.0 = maximally harmful, 1.0 = maximally beneficial
                - Type: float or int (will be converted to float)
                - Interpretation: Values ≥ moral.threshold are accepted

        Returns:
            State dictionary with the following keys:
                - ``step`` (int): Current step counter (monotonically increasing)
                - ``phase`` (str): Current circadian phase ("wake" or "sleep")
                - ``moral_threshold`` (float): Current adaptive threshold ∈ [0.30, 0.90]
                - ``moral_ema`` (float): Exponential moving average of acceptance rate
                - ``synaptic_norms`` (dict): L1/L2/L3 norms (magnitude of each level)
                - ``pelm_used`` (int): Number of vectors stored in PELM
                - ``qilm_used`` (int): Deprecated alias for pelm_used
                - ``rejected`` (bool): True if event was rejected, False if accepted
                - ``accepted`` (bool): Inverse of rejected (redundant for clarity)
                - ``note`` (str): Human-readable rejection reason or "processed"

        Raises:
            This method does not raise exceptions. Instead, it returns rejected=True
            with an appropriate note. Possible rejection reasons:
                - "emergency shutdown": Controller is in emergency state
                - "emergency shutdown: memory exceeded": Process memory threshold exceeded
                - "morally rejected": moral_value < moral.threshold
                - "sleep phase": Cognitive rhythm is in sleep state
                - "emergency shutdown: global memory limit exceeded": CORE-04 bound violated
                - "processing time exceeded: X.XX ms": Operation took too long

        Complexity:
            - **Time**: O(n + k log k) where:
                - n = PELM size (for potential retrieval during commit)
                - k = retrieval top_k (if context is requested)
                - Memory commit is O(1) amortized (circular buffer)
                - Moral evaluation is O(1)
                - Rhythm step is O(1)

            - **Space**: O(d) where d = dimension for temporary vector storage

            - **Lock hold time**: Proportional to O(n), typically < 10ms for n=20K

        Side Effects:
            On successful acceptance (not rejected):
                - Increments step_counter (INV-CC-05)
                - Advances cognitive rhythm counter
                - Stores vector in PELM (may evict oldest if at capacity)
                - Updates synaptic memory L1/L2/L3 with decay and consolidation
                - Adapts moral threshold based on acceptance (EMA update)
                - May enter emergency shutdown if bounds violated
                - Invalidates internal state cache

            On rejection:
                - Increments step_counter
                - Adapts moral threshold (only if morally rejected)
                - No memory modifications

            Observability:
                - Emits OpenTelemetry span "cognitive_controller.process_event"
                - Emits child spans for "moral_filter" and "memory_update"
                - Records processing time, rejection reason, and recovery attempts
                - Updates Prometheus metrics (if metrics exporter available)

        Thread Safety:
            This method is thread-safe. Concurrent calls will serialize at the lock
            boundary. Only one thread can process an event at a time. Lock contention
            may occur if calling from multiple threads simultaneously.

        Example:
            >>> controller = CognitiveController(dim=384)
            >>>
            >>> # Process morally acceptable event during wake phase
            >>> event = np.random.randn(384).astype(np.float32)
            >>> result = controller.process_event(event, moral_value=0.75)
            >>>
            >>> if result['accepted']:
            ...     print(f"Event accepted at step {result['step']}")
            ...     print(f"Moral threshold: {result['moral_threshold']:.3f}")
            ...     print(f"PELM size: {result['pelm_used']}")
            ... else:
            ...     print(f"Event rejected: {result['note']}")
            >>>
            >>> # Check invariants
            >>> assert 0.30 <= result['moral_threshold'] <= 0.90  # INV-CC-02
            >>> assert result['step'] >= 1  # INV-CC-05
            >>> assert result['pelm_used'] <= 20_000  # Capacity bound

        See Also:
            - ``retrieve_context()``: Retrieve similar memories from PELM
            - ``get_state()``: Get current controller state without side effects
            - ``reset_emergency_shutdown()``: Manually clear emergency state

        .. versionadded:: 1.0.0
        .. versionchanged:: 1.2.0
           Added global memory bound checking and time-based auto-recovery.
        """
        # Get tracer manager for spans (graceful fallback if tracing disabled)
        tracer_manager = get_tracer_manager()

        with self._lock:  # noqa: SIM117 - Lock must be held for entire operation
            # Create span for the entire process_event operation
            with tracer_manager.start_span(
                "cognitive_controller.process_event",
                attributes={
                    "mlsdm.step": self.step_counter + 1,
                    "mlsdm.moral_value": moral_value,
                    "mlsdm.emergency_shutdown": self.emergency_shutdown,
                },
            ) as event_span:
                # Check emergency shutdown and attempt auto-recovery if applicable
                if self.emergency_shutdown:
                    steps_since_emergency = self.step_counter - self._last_emergency_step
                    time_since_emergency = (
                        time.time() - self._last_emergency_time
                        if self._last_emergency_time > 0
                        else 0.0
                    )
                    logger.info(
                        "Emergency shutdown active; evaluating auto-recovery "
                        f"(reason={self._emergency_reason}, steps_since={steps_since_emergency}, "
                        f"time_since={time_since_emergency:.1f}s, "
                        f"recovery_attempts={self._recovery_attempts})"
                    )
                    if self._try_auto_recovery():
                        logger.info(
                            "auto-recovery succeeded after emergency_shutdown "
                            f"(cooldown_steps={self.step_counter - self._last_emergency_step}, "
                            f"recovery_attempt={self._recovery_attempts})"
                        )
                        event_span.set_attribute("mlsdm.auto_recovery", True)
                    else:
                        logger.debug(
                            "Auto-recovery conditions not met; rejecting event "
                            f"(reason={self._emergency_reason}, steps_since={steps_since_emergency}, "
                            f"time_since={time_since_emergency:.1f}s)"
                        )
                        event_span.set_attribute("mlsdm.rejected", True)
                        event_span.set_attribute("mlsdm.rejected_reason", "emergency_shutdown")
                        return self._build_state(rejected=True, note="emergency shutdown")

                start_time = time.perf_counter()
                self.step_counter += 1
                # Optimization: Invalidate state cache when processing
                self._state_cache_valid = False

                # Validate moral_value range
                if not (0.0 <= moral_value <= 1.0):
                    event_span.set_attribute("mlsdm.rejected", True)
                    event_span.set_attribute("mlsdm.rejected_reason", "invalid_moral_value")
                    logger.warning(
                        f"Invalid moral_value: {moral_value}. Must be in [0.0, 1.0]. Rejecting event."
                    )
                    return self._build_state(
                        rejected=True,
                        note=f"invalid moral_value: {moral_value} (must be in [0.0, 1.0])"
                    )

                # Check memory usage before processing (psutil-based, legacy)
                memory_mb = self._check_memory_usage()
                if memory_mb > self.memory_threshold_mb:
                    logger.info(
                        "Entering emergency shutdown due to process memory threshold "
                        f"(memory_mb={memory_mb:.2f}, threshold_mb={self.memory_threshold_mb:.2f})"
                    )
                    self._enter_emergency_shutdown("process_memory_exceeded")
                    event_span.set_attribute("mlsdm.rejected", True)
                    event_span.set_attribute("mlsdm.rejected_reason", "memory_exceeded")
                    event_span.set_attribute("mlsdm.emergency_shutdown", True)
                    return self._build_state(
                        rejected=True, note="emergency shutdown: memory exceeded"
                    )

                # Moral evaluation with tracing
                with tracer_manager.start_span(
                    "cognitive_controller.moral_filter",
                    attributes={
                        "mlsdm.moral_value": moral_value,
                        "mlsdm.moral_threshold": self.moral.threshold,
                    },
                ) as moral_span:
                    accepted = self.moral.evaluate(moral_value)
                    self._kernel.moral_adapt(accepted)
                    moral_span.set_attribute("mlsdm.moral.accepted", accepted)

                    if not accepted:
                        event_span.set_attribute("mlsdm.rejected", True)
                        event_span.set_attribute("mlsdm.rejected_reason", "morally_rejected")
                        return self._build_state(rejected=True, note="morally rejected")

                # Check cognitive phase
                if not self.rhythm.is_wake():
                    event_span.set_attribute("mlsdm.rejected", True)
                    event_span.set_attribute("mlsdm.rejected_reason", "sleep_phase")
                    event_span.set_attribute("mlsdm.phase", "sleep")
                    return self._build_state(rejected=True, note="sleep phase")

                event_span.set_attribute("mlsdm.phase", "wake")

                # Memory update with tracing
                with tracer_manager.start_span(
                    "cognitive_controller.memory_update",
                    attributes={
                        "mlsdm.phase": self.rhythm.phase,
                    },
                ) as memory_span:
                    # Optimization: use cached phase value
                    phase_val = self._phase_cache[self.rhythm.phase]
                    self.memory_commit(vector, phase_val)
                    memory_span.set_attribute(
                        "mlsdm.pelm_used", self.pelm.get_state_stats()["used"]
                    )

                self.rhythm_step()

                # Check global memory bound (CORE-04) after memory-modifying operations
                current_memory_bytes = self.memory_usage_bytes()
                if current_memory_bytes > self.max_memory_bytes:
                    logger.info(
                        "Entering emergency shutdown due to global memory limit "
                        f"(current_bytes={current_memory_bytes}, max_bytes={self.max_memory_bytes})"
                    )
                    self._enter_emergency_shutdown("memory_limit_exceeded")
                    logger.warning(
                        f"Global memory limit exceeded: {current_memory_bytes} > {self.max_memory_bytes} bytes. "
                        "Emergency shutdown triggered."
                    )
                    event_span.set_attribute("mlsdm.rejected", True)
                    event_span.set_attribute("mlsdm.rejected_reason", "memory_limit_exceeded")
                    event_span.set_attribute("mlsdm.emergency_shutdown", True)
                    return self._build_state(
                        rejected=True, note="emergency shutdown: global memory limit exceeded"
                    )

                # Check processing time
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                event_span.set_attribute("mlsdm.processing_time_ms", elapsed_ms)

                if elapsed_ms > self.max_processing_time_ms:
                    event_span.set_attribute("mlsdm.rejected", True)
                    event_span.set_attribute("mlsdm.rejected_reason", "processing_timeout")
                    return self._build_state(
                        rejected=True, note=f"processing time exceeded: {elapsed_ms:.2f}ms"
                    )

                # Success
                event_span.set_attribute("mlsdm.accepted", True)
                return self._build_state(rejected=False, note="processed")

    def retrieve_context(self, query_vector: np.ndarray, top_k: int = 5) -> list[MemoryRetrieval]:
        """Retrieve contextually similar memories from PELM using phase-aware search.

        Performs approximate nearest neighbor (ANN) search in the PELM vector space,
        filtering by current cognitive phase and ranking by cosine similarity (resonance).
        The retrieval is phase-aware: memories stored during similar circadian phases
        are preferentially retrieved.

        Algorithm:
            1. Validate query vector dimensions
            2. Compute cosine similarity for all PELM vectors within phase tolerance
            3. Filter by phase proximity: |phase_stored - phase_current| ≤ tolerance
            4. Rank by cosine similarity (descending)
            5. Return top-k results with provenance metadata

        Phase Tolerance:
            Default tolerance is 0.15, meaning:
            - If current phase is "wake" (0.1), retrieves vectors with phase ∈ [0.0, 0.25]
            - If current phase is "sleep" (0.9), retrieves vectors with phase ∈ [0.75, 1.0]
            - Cross-phase retrieval is controlled by this tolerance parameter

        Args:
            query_vector: Query embedding vector. Must satisfy:
                - Shape: (dimension,) matching controller's dimension
                - Dtype: Any numeric type (will be converted to float32)
                - Values: Finite real numbers (no NaN or Inf)
                - Semantics: Embedding of user query or context prompt

            top_k: Maximum number of results to return. Must satisfy:
                - Range: [1, PELM size]
                - Default: 5
                - Recommendation: 3-10 for typical RAG use cases
                - Note: Fewer results may be returned if PELM size < top_k
                      or if no memories match phase filter

        Returns:
            List of MemoryRetrieval objects, ordered by descending resonance:
                - ``vector`` (np.ndarray): Retrieved embedding vector
                - ``phase`` (float): Phase value when memory was stored ∈ [0, 1]
                - ``resonance`` (float): Cosine similarity score ∈ [-1, 1]
                  (typically [0, 1] for normalized vectors)
                - ``provenance`` (MemoryProvenance): Source, confidence, timestamp
                - ``memory_id`` (str): UUID for this specific memory

            Empty list if:
                - PELM is empty (size = 0)
                - No memories match phase filter
                - Controller is in emergency shutdown (graceful degradation)

        Complexity:
            - **Time**: O(n log k) where:
                - n = PELM size (for similarity computation)
                - k = top_k (for partial sorting)
                - Uses numpy vectorized operations for O(n) similarity computation
                - Uses argpartition for O(n + k log k) partial sort when n > 2k
                - Uses full argsort for O(n log n) when n ≤ 2k (faster for small arrays)

            - **Space**: O(n) for temporary similarity array

            - **Lock hold time**: Proportional to O(n log k), typically < 5ms for n=20K

        Side Effects:
            - Emits OpenTelemetry span "cognitive_controller.retrieve_context"
            - Records retrieval metrics (latency, result count, average resonance)
            - No state modifications (read-only operation)
            - Does NOT increment step counter (unlike process_event)

        Thread Safety:
            This method is thread-safe via internal lock. Concurrent retrievals
            will serialize but do not conflict with concurrent process_event calls.

        Example:
            >>> controller = CognitiveController(dim=384)
            >>>
            >>> # Store some memories first
            >>> for i in range(100):
            ...     vec = np.random.randn(384).astype(np.float32)
            ...     controller.process_event(vec, moral_value=0.8)
            >>>
            >>> # Retrieve contextually similar memories
            >>> query = np.random.randn(384).astype(np.float32)
            >>> results = controller.retrieve_context(query, top_k=5)
            >>>
            >>> # Examine results
            >>> for mem in results:
            ...     print(f"Resonance: {mem.resonance:.3f}, Phase: {mem.phase:.2f}")
            ...     print(f"Source: {mem.provenance.source}, Confidence: {mem.provenance.confidence}")
            >>>
            >>> # Verify ordering invariant
            >>> resonances = [m.resonance for m in results]
            >>> assert resonances == sorted(resonances, reverse=True)  # Descending order

        See Also:
            - ``process_event()``: Store new memories
            - ``PhaseEntangledLatticeMemory.retrieve()``: Underlying PELM retrieval
            - ``MemoryRetrieval``: Return type dataclass
            - ``MemoryProvenance``: Provenance metadata structure

        Notes:
            - This method does NOT perform re-ranking or semantic re-weighting
            - Pure cosine similarity in embedding space
            - For production RAG, consider adding re-ranker or cross-encoder
            - Phase filtering prevents "context leakage" across cognitive states

        .. versionadded:: 1.0.0
        .. versionchanged:: 1.1.0
           Added provenance tracking and memory_id to results.
        """
        tracer_manager = get_tracer_manager()

        with self._lock:  # noqa: SIM117 - Lock must be held for entire operation
            with tracer_manager.start_span(
                "cognitive_controller.retrieve_context",
                attributes={
                    "mlsdm.top_k": top_k,
                    "mlsdm.phase": self.rhythm.phase,
                },
            ) as span:
                # Optimize: use cached phase value
                phase_val = self._phase_cache[self.rhythm.phase]
                results = cast(
                    "list[MemoryRetrieval]",
                    self.pelm.retrieve(
                        query_vector.tolist(),
                        current_phase=phase_val,
                        phase_tolerance=0.15,
                        top_k=top_k,
                    ),
                )
                span.set_attribute("mlsdm.results_count", len(results))
                return results

    def _check_memory_usage(self) -> float:
        """Check current memory usage in MB."""
        memory_info = self._process.memory_info()
        return float(memory_info.rss / (1024 * 1024))  # Convert bytes to MB

    def get_memory_usage(self) -> float:
        """Public method to get current memory usage in MB."""
        return self._check_memory_usage()

    def reset_emergency_shutdown(self) -> None:
        """Reset emergency shutdown flag (use with caution).

        This also resets recovery attempt counter and time tracking,
        allowing auto-recovery to function again if the controller
        enters emergency state again.
        """
        self.emergency_shutdown = False
        self._emergency_reason = None
        self._recovery_attempts = 0
        self._last_emergency_time = 0.0
        logger.info("Emergency shutdown reset manually")
        try:
            metrics_exporter = get_metrics_exporter()
        except Exception:
            logger.debug(
                "Failed to initialize metrics exporter for manual emergency reset",
                exc_info=True,
            )
        else:
            metrics_exporter.set_emergency_shutdown_active(False)

    def _enter_emergency_shutdown(self, reason: str = "unknown") -> None:
        """Enter emergency shutdown state and record the step and time.

        Args:
            reason: The reason for emergency shutdown (e.g., 'memory_limit_exceeded').
        """
        self.emergency_shutdown = True
        self._emergency_reason = reason
        self._last_emergency_step = self.step_counter
        self._last_emergency_time = time.time()
        self._recovery_attempts += 1
        logger.warning(f"Emergency shutdown entered: reason={reason}, step={self.step_counter}")
        try:
            metrics_exporter = get_metrics_exporter()
        except Exception:
            logger.debug(
                "Failed to initialize metrics exporter for emergency shutdown",
                exc_info=True,
            )
        else:
            metrics_exporter.increment_emergency_shutdown(reason)
            metrics_exporter.set_emergency_shutdown_active(True)

    def _try_auto_recovery(self) -> bool:
        """Attempt automatic recovery from emergency shutdown.

        Returns:
            True if recovery succeeded and emergency_shutdown was cleared,
            False if recovery conditions are not met.

        Recovery requires:
        1. Either step-based cooldown OR time-based cooldown has passed
           - Step-based: step_counter - _last_emergency_step >= cooldown_steps
           - Time-based: time.time() - _last_emergency_time >= cooldown_seconds
             (only if auto_recovery_enabled is True)
        2. Memory usage is below safety threshold
        3. Recovery attempts have not exceeded the maximum limit
        """
        # Guard: check if max recovery attempts exceeded
        if self._recovery_attempts >= _CC_RECOVERY_MAX_ATTEMPTS:
            self._record_auto_recovery("failure", "max_attempts_exceeded")
            return False

        # Check cooldown period (step-based OR time-based)
        steps_since_emergency = self.step_counter - self._last_emergency_step
        step_cooldown_passed = steps_since_emergency >= _CC_RECOVERY_COOLDOWN_STEPS

        time_cooldown_passed = False
        if self.auto_recovery_enabled and self._last_emergency_time > 0:
            time_since_emergency = time.time() - self._last_emergency_time
            time_cooldown_passed = time_since_emergency >= self.auto_recovery_cooldown_seconds

        if not (step_cooldown_passed or time_cooldown_passed):
            self._record_auto_recovery("failure", "cooldown_pending")
            return False

        # Health check: verify memory is within safe limits
        memory_mb = self._check_memory_usage()
        memory_safety_threshold = self.memory_threshold_mb * _CC_RECOVERY_MEMORY_SAFETY_RATIO
        if memory_mb > memory_safety_threshold:
            self._record_auto_recovery("failure", "memory_above_safety_threshold")
            return False

        # All conditions met - perform recovery
        self.emergency_shutdown = False
        recovery_mode = "time" if time_cooldown_passed and not step_cooldown_passed else "step"
        logger.info(
            f"Auto-recovery succeeded via {recovery_mode}-based cooldown "
            f"(steps_since={steps_since_emergency}, time_since={time.time() - self._last_emergency_time:.1f}s)"
        )
        self._record_auto_recovery("success", "recovered")
        return True

    def _record_auto_recovery(self, result: str, reason: str) -> None:
        """Record observability for auto-recovery attempts."""
        logger.debug("Auto-recovery result=%s reason=%s", result, reason)
        try:
            metrics_exporter = get_metrics_exporter()
        except Exception:
            logger.debug("Failed to initialize metrics exporter for auto-recovery", exc_info=True)
            return
        metrics_exporter.increment_auto_recovery(result)
        metrics_exporter.set_emergency_shutdown_active(result != "success")

    def _build_state(self, rejected: bool, note: str) -> dict[str, Any]:
        # Optimization: Use cached norm calculations when state hasn't changed
        # Only cache when not rejected (rejected responses are cheap anyway)
        if not rejected and self._state_cache_valid and self._state_cache:
            # Use cached values but update step counter and note
            result = self._state_cache.copy()
            result["step"] = self.step_counter
            result["rejected"] = rejected
            result["accepted"] = not rejected
            result["note"] = note
            return result

        # Calculate fresh state
        l1, l2, l3 = self.synaptic.state()

        # Optimization: Compute norms in a single pass when possible
        # Pre-allocate result dict to avoid resizing
        result = {
            "step": self.step_counter,
            "phase": self.rhythm.phase,
            "moral_threshold": round(self.moral.threshold, 4),
            "moral_ema": round(self.moral.ema_accept_rate, 4),
            "synaptic_norms": {
                "L1": float(np.linalg.norm(l1)),
                "L2": float(np.linalg.norm(l2)),
                "L3": float(np.linalg.norm(l3)),
            },
            "pelm_used": self.pelm.get_state_stats()["used"],
            # Backward compatibility (deprecated)
            "qilm_used": self.pelm.get_state_stats()["used"],
            "rejected": rejected,
            "accepted": not rejected,
            "note": note,
        }

        # Cache result for accepted events
        if not rejected:
            self._state_cache = result.copy()
            self._state_cache_valid = True

        return result
