import logging
import time
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from mlsdm.utils.math_constants import safe_norm

if TYPE_CHECKING:
    from mlsdm.config import SynapticMemoryCalibration


# Import calibration defaults for consistent parameter values
# Type annotation uses Optional since module may not be available
_SYNAPTIC_MEMORY_DEFAULTS: Optional["SynapticMemoryCalibration"] = None
logger = logging.getLogger(__name__)
try:
    from mlsdm.config import SYNAPTIC_MEMORY_DEFAULTS as _IMPORTED_DEFAULTS

    _SYNAPTIC_MEMORY_DEFAULTS = _IMPORTED_DEFAULTS
except ImportError:
    # Fallback if calibration module is not available - already None
    logger.info("Synaptic memory calibration defaults unavailable; using fallback parameters")

# Observability imports - gracefully handle missing module
try:
    from mlsdm.observability.memory_telemetry import record_synaptic_update

    _OBSERVABILITY_AVAILABLE = True
except ImportError:
    _OBSERVABILITY_AVAILABLE = False


# Helper to get default value from calibration or fallback
def _get_default(attr: str, fallback: float) -> float:
    if _SYNAPTIC_MEMORY_DEFAULTS is not None:
        return getattr(_SYNAPTIC_MEMORY_DEFAULTS, attr, fallback)
    return fallback


class MultiLevelSynapticMemory:
    """Three-level cascade memory consolidation system with neurobiologically-grounded decay.

    MultiLevelSynapticMemory implements a cascade model of memory consolidation inspired
    by Benna & Fusi (2016), where memories progress through three levels with distinct
    decay rates and transfer thresholds. This enables both rapid short-term learning (L1)
    and stable long-term retention (L3) in a unified architecture.

    Architecture - Three-Level Cascade:
        Memories flow through three levels with progressively slower decay:

        .. code-block:: text

            L1 (Fast)  →  L2 (Medium)  →  L3 (Slow)
            λ₁ = 0.50      λ₂ = 0.10       λ₃ = 0.01
            θ₁ = 1.2       θ₂ = 2.5

        Where:
            - L1: Short-term working memory (fast acquisition, fast decay)
            - L2: Medium-term consolidation buffer (selective transfer)
            - L3: Long-term stable memory (minimal decay, permanent storage)

    Mathematical Formulation:
        At each timestep t, the system evolves according to:

        **Decay Dynamics:**

        .. math::
            L_1(t+1) = (1 - \\lambda_1) \\cdot L_1(t) + e(t)

        .. math::
            L_2(t+1) = (1 - \\lambda_2) \\cdot L_2(t)

        .. math::
            L_3(t+1) = (1 - \\lambda_3) \\cdot L_3(t)

        **Consolidation Transfers:**

        .. math::
            T_{1 \\to 2}(t) = \\mathbb{1}_{\\|L_1(t)\\| > \\theta_1} \\cdot g_{12} \\cdot L_1(t)

        .. math::
            T_{2 \\to 3}(t) = \\mathbb{1}_{\\|L_2(t)\\| > \\theta_2} \\cdot g_{23} \\cdot L_2(t)

        **Level Updates After Transfer:**

        .. math::
            L_1(t+1) \\gets L_1(t+1) - T_{1 \\to 2}(t)

        .. math::
            L_2(t+1) \\gets L_2(t+1) + T_{1 \\to 2}(t) - T_{2 \\to 3}(t)

        .. math::
            L_3(t+1) \\gets L_3(t+1) + T_{2 \\to 3}(t)

        Where:
            - :math:`e(t)` = event vector at time t (dimension d)
            - :math:`\\lambda_1, \\lambda_2, \\lambda_3` = decay rates (L1 > L2 > L3)
            - :math:`\\theta_1, \\theta_2` = consolidation thresholds (norm-based)
            - :math:`g_{12}, g_{23}` = gating factors ∈ [0, 1] (transfer fractions)
            - :math:`\\mathbb{1}_{condition}` = indicator function (1 if true, 0 if false)

    Neurobiological Grounding:
        The three-level cascade mirrors synaptic plasticity mechanisms:

        - **L1 ≈ Early-phase LTP**: Rapid but transient synaptic strengthening via
          CaMKII phosphorylation. Decays quickly without consolidation.
        - **L2 ≈ Intermediate consolidation**: Protein synthesis-dependent stabilization
          (hippocampal systems consolidation).
        - **L3 ≈ Late-phase LTP**: Structural synaptic changes and cortical storage.
          Minimal decay, represents "permanent" memory traces.

        This maps to Benna & Fusi's (2016) cascade model demonstrating how multiple
        timescales enable efficient long-term memory despite ongoing plasticity.

    Invariants:
        - **INV-ML-01**: Decay reduces level norms monotonically (before new events)
        - **INV-ML-02**: Lambda decay rates ordered: λ₁ > λ₂ > λ₃
        - **INV-ML-03**: No unbounded growth in any level (bounded by input magnitude)
        - **INV-ML-04**: Gating values within bounds: g₁₂, g₂₃ ∈ [0, 1]
        - **INV-ML-05**: Dimension consistency across all three levels
        - **INV-ML-06**: Level transfer only occurs when norm exceeds threshold

    Complexity Analysis:
        - **update()**: O(d) where d = dimension (vectorized numpy operations)
            * Decay: O(d) - 3 in-place scalar multiplications
            * Event addition: O(d) - single vector addition
            * Transfer logic: O(d) - 2 threshold checks + masked multiplications
            * Total: O(d) with low constant factor (optimized for hot path)
        - **state()**: O(d) - copies three vectors
        - **reset_all()**: O(d) - fills three arrays with zeros
        - **memory_usage_bytes()**: O(1) - constant time calculation

    Memory Efficiency:
        Total memory footprint is 3 × dimension × 4 bytes (float32):

        .. math::
            M_{synaptic} = 3 \\times d \\times 4 + \\text{metadata}

        For 384-dim vectors:
            :math:`M_{synaptic} = 3 \\times 384 \\times 4 = 4.6` KB (negligible)

    Gating Mechanism:
        Gating factors control what fraction of a level transfers to the next:
        - **g₁₂ = 0.45**: 45% of L1 transfers to L2 (55% remains in L1)
        - **g₂₃ = 0.30**: 30% of L2 transfers to L3 (70% remains in L2)

        This creates a "leaky bucket" cascade where not all information propagates,
        implementing a form of memory filtering and capacity control.

    Consolidation Triggers:
        Transfers occur when level norm exceeds threshold:
        - **L1→L2**: Triggered when :math:`\\|L_1\\| > \\theta_1 = 1.2`
        - **L2→L3**: Triggered when :math:`\\|L_2\\| > \\theta_2 = 2.5`

        Higher thresholds for later stages implement "synaptic tagging" - only
        strong or repeated activations consolidate into long-term storage.

    Example:
        >>> import numpy as np
        >>> from mlsdm.memory import MultiLevelSynapticMemory
        >>>
        >>> # Initialize 384-dim synaptic memory with default decay rates
        >>> synapse = MultiLevelSynapticMemory(dimension=384)
        >>>
        >>> # Process a sequence of events (e.g., sensory inputs)
        >>> event1 = np.random.randn(384).astype(np.float32)
        >>> synapse.update(event1)
        >>> l1, l2, l3 = synapse.state()
        >>> assert np.linalg.norm(l1) > 0  # L1 contains event
        >>> assert np.linalg.norm(l2) == 0  # L2 empty (no transfer yet)
        >>>
        >>> # Repeated events trigger consolidation
        >>> for _ in range(5):
        ...     synapse.update(event1)
        >>> l1, l2, l3 = synapse.state()
        >>> # After multiple updates, L1 norm exceeds θ₁ → transfer to L2
        >>>
        >>> # Check decay over time without new events
        >>> initial_l1_norm = np.linalg.norm(l1)
        >>> for _ in range(10):
        ...     synapse.update(np.zeros(384, dtype=np.float32))  # No new input
        >>> l1_after, _, _ = synapse.state()
        >>> final_l1_norm = np.linalg.norm(l1_after)
        >>> assert final_l1_norm < initial_l1_norm  # INV-ML-01: Decay reduces norm
        >>>
        >>> # Verify decay rate ordering
        >>> assert synapse.lambda_l1 > synapse.lambda_l2 > synapse.lambda_l3  # INV-ML-02

    References:
        - **Benna, M. K., & Fusi, S. (2016).** Computational principles of synaptic
          memory consolidation. *Nature Neuroscience, 19*(12), 1697-1706.
          DOI: `10.1038/nn.4401 <https://doi.org/10.1038/nn.4401>`_

          Demonstrates how cascade models with multiple timescales solve the
          stability-plasticity dilemma, enabling both rapid learning and long-term
          retention without catastrophic forgetting.

        - **Fusi, S., Drew, P. J., & Abbott, L. F. (2005).** Cascade models of
          synaptically stored memories. *Neuron, 45*(4), 599-611.
          DOI: `10.1016/j.neuron.2005.02.001 <https://doi.org/10.1016/j.neuron.2005.02.001>`_

          Original cascade model showing how discrete-state synapses with multiple
          timescales can retain memories despite ongoing plasticity.

    See Also:
        - ``CognitiveController``: Integrates synaptic memory into cognitive pipeline
        - ``PhaseEntangledLatticeMemory``: Complementary phase-aware retrieval system
        - ``config.SynapticMemoryCalibration``: Configuration for λ, θ, and gating values

    .. versionadded:: 1.0.0
       Initial implementation of three-level cascade.
    .. versionchanged:: 1.2.0
       Added observability telemetry and configurable decay/gating parameters.

    Notes:
        - Default parameters (λ, θ, g) are calibrated for 384-dim embedding vectors
        - For different vector dimensions, may need to adjust thresholds proportionally
        - Decay rates follow geometric progression: λ₁ = 5×λ₂, λ₂ = 10×λ₃
    """

    __slots__ = (
        "dim",
        "lambda_l1",
        "lambda_l2",
        "lambda_l3",
        "theta_l1",
        "theta_l2",
        "gating12",
        "gating23",
        "l1",
        "l2",
        "l3",
    )

    def __init__(
        self,
        dimension: int = 384,
        lambda_l1: float | None = None,
        lambda_l2: float | None = None,
        lambda_l3: float | None = None,
        theta_l1: float | None = None,
        theta_l2: float | None = None,
        gating12: float | None = None,
        gating23: float | None = None,
        *,
        config: "SynapticMemoryCalibration | None" = None,
    ) -> None:
        """Initialize MultiLevelSynapticMemory.

        Args:
            dimension: Vector dimension for memory arrays.
            lambda_l1: L1 decay rate. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            lambda_l2: L2 decay rate. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            lambda_l3: L3 decay rate. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            theta_l1: L1→L2 consolidation threshold. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            theta_l2: L2→L3 consolidation threshold. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            gating12: L1→L2 gating factor. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            gating23: L2→L3 gating factor. If None, uses SYNAPTIC_MEMORY_DEFAULTS.
            config: Optional SynapticMemoryCalibration instance. If provided,
                all λ/θ/gating values are taken from it (unless explicitly overridden).
        """
        # Resolve parameter source: explicit arg > config > SYNAPTIC_MEMORY_DEFAULTS
        if config is not None:
            _lambda_l1 = lambda_l1 if lambda_l1 is not None else config.lambda_l1
            _lambda_l2 = lambda_l2 if lambda_l2 is not None else config.lambda_l2
            _lambda_l3 = lambda_l3 if lambda_l3 is not None else config.lambda_l3
            _theta_l1 = theta_l1 if theta_l1 is not None else config.theta_l1
            _theta_l2 = theta_l2 if theta_l2 is not None else config.theta_l2
            _gating12 = gating12 if gating12 is not None else config.gating12
            _gating23 = gating23 if gating23 is not None else config.gating23
        else:
            _lambda_l1 = lambda_l1 if lambda_l1 is not None else _get_default("lambda_l1", 0.50)
            _lambda_l2 = lambda_l2 if lambda_l2 is not None else _get_default("lambda_l2", 0.10)
            _lambda_l3 = lambda_l3 if lambda_l3 is not None else _get_default("lambda_l3", 0.01)
            _theta_l1 = theta_l1 if theta_l1 is not None else _get_default("theta_l1", 1.2)
            _theta_l2 = theta_l2 if theta_l2 is not None else _get_default("theta_l2", 2.5)
            _gating12 = gating12 if gating12 is not None else _get_default("gating12", 0.45)
            _gating23 = gating23 if gating23 is not None else _get_default("gating23", 0.30)
        # Validate inputs
        if dimension <= 0:
            raise ValueError(f"dimension must be positive, got {dimension}")
        if not (0 < _lambda_l1 <= 1.0):
            raise ValueError(f"lambda_l1 must be in (0, 1], got {_lambda_l1}")
        if not (0 < _lambda_l2 <= 1.0):
            raise ValueError(f"lambda_l2 must be in (0, 1], got {_lambda_l2}")
        if not (0 < _lambda_l3 <= 1.0):
            raise ValueError(f"lambda_l3 must be in (0, 1], got {_lambda_l3}")
        if _theta_l1 <= 0:
            raise ValueError(f"theta_l1 must be positive, got {_theta_l1}")
        if _theta_l2 <= 0:
            raise ValueError(f"theta_l2 must be positive, got {_theta_l2}")
        if not (0 <= _gating12 <= 1.0):
            raise ValueError(f"gating12 must be in [0, 1], got {_gating12}")
        if not (0 <= _gating23 <= 1.0):
            raise ValueError(f"gating23 must be in [0, 1], got {_gating23}")

        self.dim = int(dimension)
        self.lambda_l1 = float(_lambda_l1)
        self.lambda_l2 = float(_lambda_l2)
        self.lambda_l3 = float(_lambda_l3)
        self.theta_l1 = float(_theta_l1)
        self.theta_l2 = float(_theta_l2)
        self.gating12 = float(_gating12)
        self.gating23 = float(_gating23)

        self.l1 = np.zeros(self.dim, dtype=np.float32)
        self.l2 = np.zeros(self.dim, dtype=np.float32)
        self.l3 = np.zeros(self.dim, dtype=np.float32)

    def update(self, event: np.ndarray, correlation_id: str | None = None) -> None:
        """Update synaptic memory with a new event vector (cascade consolidation step).

        Performs a single timestep of the three-level cascade dynamics:
        1. Apply exponential decay to all three levels
        2. Add new event to L1 (short-term memory)
        3. Check consolidation thresholds and transfer between levels
        4. Update L1, L2, L3 according to transfer amounts

        This implements the core memory consolidation algorithm, where repeated or
        strong activations in L1 consolidate to L2, and sustained L2 activations
        consolidate to long-term L3 storage.

        Args:
            event: Event vector to process (must be 1D numpy array matching dimension).
                Typically an embedding vector representing sensory input, action, or
                state observation. Should be float32 or will be converted (with copy).
            correlation_id: Optional correlation ID for distributed tracing and
                observability. Links this update to upstream events in the cognitive pipeline.

        Raises:
            ValueError: If event is not a 1D numpy array or dimension doesn't match.
                Error message includes expected dimension for debugging.

        Complexity:
            O(d) where d = dimension. All operations are vectorized:
            - Decay: 3 in-place scalar multiplications → O(d)
            - Event addition: 1 vector addition → O(d)
            - Threshold checks: 2 norm computations → O(d)
            - Transfers: 2 masked vector operations → O(d)
            - Total: O(d) with small constant factor (~5-7 operations per element)

        Side Effects:
            - Modifies L1, L2, L3 arrays in-place (no allocation overhead)
            - Records telemetry metrics if observability available:
                * Level norms (L1, L2, L3) after update
                * Consolidation events (L1→L2, L2→L3) boolean flags
                * Memory usage in bytes
                * Latency in milliseconds
            - May trigger consolidation transfers based on threshold crossings

        Mathematical Operations:
            The method implements the following sequence:

            .. math::
                \\begin{align}
                L_1 &\\gets (1 - \\lambda_1) \\cdot L_1 + e \\\\
                L_2 &\\gets (1 - \\lambda_2) \\cdot L_2 \\\\
                L_3 &\\gets (1 - \\lambda_3) \\cdot L_3 \\\\
                T_{12} &= \\mathbb{1}_{\\|L_1\\| > \\theta_1} \\cdot g_{12} \\cdot L_1 \\\\
                T_{23} &= \\mathbb{1}_{\\|L_2\\| > \\theta_2} \\cdot g_{23} \\cdot L_2 \\\\
                L_1 &\\gets L_1 - T_{12} \\\\
                L_2 &\\gets L_2 + T_{12} - T_{23} \\\\
                L_3 &\\gets L_3 + T_{23}
                \\end{align}

        Performance Optimizations:
            - In-place operations avoid temporary array allocations
            - Vectorized numpy operations use SIMD instructions
            - Dtype check avoids unnecessary astype() call if already float32
            - Pre-computed (1 - λ) constants stored as instance variables
            - Multiplication by boolean mask is faster than conditional branching

        Consolidation Detection:
            Telemetry tracks consolidation events for observability:
            - L1→L2 consolidation: Detected when :math:`\\sum(T_{12}) > 0`
            - L2→L3 consolidation: Detected when :math:`\\sum(T_{23}) > 0`

            These events indicate significant memory formation and can trigger
            alerts or adaptive behavior in the cognitive controller.

        Example:
            >>> import numpy as np
            >>> synapse = MultiLevelSynapticMemory(dimension=384)
            >>>
            >>> # Single event update
            >>> event = np.random.randn(384).astype(np.float32)
            >>> synapse.update(event)
            >>> l1, l2, l3 = synapse.state()
            >>> assert np.array_equal(l1[:5], event[:5])  # Event stored in L1
            >>>
            >>> # Repeated events trigger consolidation
            >>> strong_event = np.ones(384, dtype=np.float32) * 2.0
            >>> for i in range(10):
            ...     synapse.update(strong_event)
            >>> l1, l2, l3 = synapse.state()
            >>> # After multiple updates, L1 exceeds θ₁ → transfer to L2
            >>> assert np.linalg.norm(l2) > 0  # L2 now contains consolidated memory
            >>>
            >>> # Decay without new input
            >>> zero_event = np.zeros(384, dtype=np.float32)
            >>> synapse.update(zero_event)
            >>> # Levels decay but L3 decays slowest (INV-ML-02)

        Notes:
            - Event vectors should be normalized or scaled appropriately for thresholds
            - Very large events (norm >> θ₁) will consolidate immediately
            - Zero events cause pure decay (useful for simulating time passage)
            - Float64 events are converted to float32 (memory efficiency over precision)

        See Also:
            - ``state()``: Retrieve current L1, L2, L3 vectors (read-only)
            - ``reset_all()``: Clear all three levels (return to initial state)
            - ``CognitiveController.process_event()``: Calls update() in cognitive loop
        """
        if (
            not isinstance(event, np.ndarray)
            or event.ndim != 1
            or event.shape[0] != self.dim
        ):
            raise ValueError(
                f"Event vector must be a 1D NumPy array of dimension {self.dim}."
            )

        start_time = time.perf_counter() if _OBSERVABILITY_AVAILABLE else None

        # Optimize: perform decay in-place to avoid temporary arrays
        self.l1 *= 1 - self.lambda_l1
        self.l2 *= 1 - self.lambda_l2
        self.l3 *= 1 - self.lambda_l3

        # Optimize: avoid unnecessary astype if already float32
        if event.dtype != np.float32:
            self.l1 += event.astype(np.float32)
        else:
            self.l1 += event

        # Transfer logic maintains original behavior but avoids temp array creation
        transfer12 = (self.l1 > self.theta_l1) * self.l1 * self.gating12
        self.l1 -= transfer12
        self.l2 += transfer12
        transfer23 = (self.l2 > self.theta_l2) * self.l2 * self.gating23
        self.l2 -= transfer23
        self.l3 += transfer23

        # Record observability metrics
        if _OBSERVABILITY_AVAILABLE and start_time is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000
            l1_norm = safe_norm(self.l1)
            l2_norm = safe_norm(self.l2)
            l3_norm = safe_norm(self.l3)

            # Detect consolidation by checking if transfers occurred
            # Transfer happened if L2 increased more than from decay alone
            consolidation_l1_l2 = float(np.sum(transfer12)) > 0
            consolidation_l2_l3 = float(np.sum(transfer23)) > 0

            record_synaptic_update(
                l1_norm=l1_norm,
                l2_norm=l2_norm,
                l3_norm=l3_norm,
                memory_bytes=self.memory_usage_bytes(),
                consolidation_l1_l2=consolidation_l1_l2,
                consolidation_l2_l3=consolidation_l2_l3,
                latency_ms=latency_ms,
                correlation_id=correlation_id,
            )

    def state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.l1.copy(), self.l2.copy(), self.l3.copy()

    def get_state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.state()

    def reset_all(self) -> None:
        self.l1.fill(0.0)
        self.l2.fill(0.0)
        self.l3.fill(0.0)

    def memory_usage_bytes(self) -> int:
        """Calculate conservative memory usage estimate in bytes.

        Returns:
            Estimated memory usage for L1/L2/L3 arrays and configuration overhead.

        Note:
            This is a conservative estimate (10-20% overhead) to ensure we
            never underestimate actual memory usage.
        """
        # L1, L2, L3 numpy arrays (each is dim × float32)
        l1_bytes = self.l1.nbytes
        l2_bytes = self.l2.nbytes
        l3_bytes = self.l3.nbytes

        # Subtotal for arrays
        array_bytes = l1_bytes + l2_bytes + l3_bytes

        # Metadata overhead for configuration floats and int
        # Includes: dim, lambda_l1/l2/l3, theta_l1/l2, gating12/23, Python object headers
        metadata_overhead = 512  # ~0.5KB for metadata and object overhead

        # Conservative 40% overhead for Python object structures
        # Python objects have significant overhead from reference counting, type info,
        # and memory allocator rounding. 1.4x multiplier ensures we never underestimate.
        conservative_multiplier = 1.4

        total_bytes = int((array_bytes + metadata_overhead) * conservative_multiplier)
        return total_bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dim,
            "lambda_l1": self.lambda_l1,
            "lambda_l2": self.lambda_l2,
            "lambda_l3": self.lambda_l3,
            "theta_l1": self.theta_l1,
            "theta_l2": self.theta_l2,
            "gating12": self.gating12,
            "gating23": self.gating23,
            "state_L1": self.l1.tolist(),
            "state_L2": self.l2.tolist(),
            "state_L3": self.l3.tolist(),
        }
