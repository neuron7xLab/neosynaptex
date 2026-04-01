from __future__ import annotations

import logging
import os
import re
import threading
from collections import deque
from typing import TYPE_CHECKING, Any, ClassVar, Final

if TYPE_CHECKING:
    from mlsdm.config import MoralFilterCalibration

# Import drift telemetry
from mlsdm.observability.policy_drift_telemetry import record_threshold_change

logger = logging.getLogger(__name__)

# Import calibration defaults - these can be overridden via config
# Type hints use Optional to allow None when calibration module unavailable
MORAL_FILTER_DEFAULTS: MoralFilterCalibration | None

try:
    from mlsdm.config import MORAL_FILTER_DEFAULTS
except ImportError:
    MORAL_FILTER_DEFAULTS = None

# Pre-compiled regex patterns for word boundary matching (module-level for performance)
# These patterns match whole words only to avoid false positives like "harm" in "pharmacy"
_HARMFUL_PATTERNS: Final[list[str]] = [
    "hate",
    "violence",
    "attack",
    "kill",
    "destroy",
    "harm",
    "abuse",
    "exploit",
    "discriminate",
    "racist",
    "sexist",
    "terrorist",
    "weapon",
    "bomb",
    "murder",
]
_POSITIVE_PATTERNS: Final[list[str]] = [
    "help",
    "support",
    "care",
    "love",
    "kind",
    "respect",
    "ethical",
    "fair",
    "honest",
    "trust",
    "safe",
    "protect",
    "collaborate",
    "peace",
    "understanding",
]
# Compile single regex patterns for O(n) matching instead of O(n*m)
_HARMFUL_REGEX: Final[re.Pattern[str]] = re.compile(r"\b(" + "|".join(_HARMFUL_PATTERNS) + r")\b", re.IGNORECASE)
_POSITIVE_REGEX: Final[re.Pattern[str]] = re.compile(r"\b(" + "|".join(_POSITIVE_PATTERNS) + r")\b", re.IGNORECASE)


class MoralFilterV2:
    """Adaptive moral threshold filter with homeostatic EMA-based control.

    The MoralFilterV2 implements a self-regulating moral evaluation system that
    maintains a stable acceptance rate through exponential moving average (EMA)
    feedback control. The filter adapts its threshold to balance permissiveness
    and safety, inspired by homeostatic mechanisms in biological systems.

    Algorithm - EMA Threshold Adaptation:
        The filter maintains an exponential moving average of acceptance rate:

        .. math::
            r_t = \\alpha \\cdot a_t + (1 - \\alpha) \\cdot r_{t-1}

        Where:
            - :math:`r_t` = EMA acceptance rate at time t
            - :math:`a_t` ∈ {0, 1} = acceptance indicator (1 if accepted, 0 if rejected)
            - :math:`\\alpha` = EMA_ALPHA = 0.1 (smoothing factor)

        The threshold adapts to maintain :math:`r_t \\approx 0.5` (50% acceptance):

        .. math::
            \\theta_{t+1} = \\begin{cases}
                \\min(\\theta_t + \\delta, \\theta_{max}) & \\text{if } r_t - 0.5 > \\epsilon \\\\
                \\max(\\theta_t - \\delta, \\theta_{min}) & \\text{if } r_t - 0.5 < -\\epsilon \\\\
                \\theta_t & \\text{otherwise}
            \\end{cases}

        Where:
            - :math:`\\theta_t` = threshold at time t
            - :math:`\\delta` = 0.05 (adaptation step size)
            - :math:`\\epsilon` = DEAD_BAND = 0.05 (prevents oscillation)
            - :math:`\\theta_{min}` = 0.30, :math:`\\theta_{max}` = 0.90

    Convergence Properties:
        - **EMA Convergence**: :math:`r_t \\to \\mathbb{E}[a_t]` as :math:`t \\to \\infty`
        - **Threshold Stability**: :math:`|\\theta_t - \\theta_{t-1}| \\leq \\delta = 0.05`
        - **Bounded Drift**: :math:`\\theta_t \\in [0.30, 0.90]` always (INV-MORAL-01)
        - **Dead-band Damping**: Prevents oscillation for :math:`|r_t - 0.5| < \\epsilon`

    Invariants:
        - **INV-MORAL-01**: Threshold ∈ [0.30, 0.90] always (enforced by min/max clipping)
        - **INV-MORAL-02**: Bounded drift under adversarial input (max Δθ = 0.05 per step)
        - **INV-MORAL-03**: EMA converges to empirical acceptance rate
        - **INV-MORAL-04**: Dead-band prevents oscillation when near equilibrium
        - **INV-MORAL-05**: Deterministic evaluation (same input → same output)
        - **INV-MORAL-06**: Adaptation direction is correct (error sign matches adjustment)

    Complexity Analysis:
        - ``evaluate()``: O(1) - constant time threshold comparison
        - ``adapt()``: O(1) - constant time EMA update and threshold adjustment
        - ``compute_moral_value()``: O(n) where n = text length for regex matching

    Performance Optimization:
        Uses pure Python arithmetic instead of numpy for scalar operations (faster).
        Pre-computes (1 - α) as _ONE_MINUS_ALPHA to avoid repeated subtraction.

    Drift Detection & Telemetry:
        Tracks threshold changes over time to detect anomalous drift:
        - Logs WARNING for drift > 0.05 in single step
        - Logs ERROR for drift > 0.10 in single step (critical)
        - Logs ERROR for sustained drift > 0.15 over 10 steps
        - Records Prometheus metrics for threshold changes

    Example:
        >>> # Initialize filter with default threshold 0.50
        >>> filter = MoralFilterV2(initial_threshold=0.50, filter_id="main")
        >>>
        >>> # Evaluate moral values
        >>> assert filter.evaluate(0.8) == True   # Above threshold → accept
        >>> assert filter.evaluate(0.3) == False  # Below threshold → reject
        >>>
        >>> # Simulate high acceptance rate (should increase threshold)
        >>> for _ in range(100):
        ...     filter.adapt(accepted=True)
        >>> assert filter.threshold > 0.50  # Adapted upward
        >>>
        >>> # Simulate low acceptance rate (should decrease threshold)
        >>> for _ in range(200):
        ...     filter.adapt(accepted=False)
        >>> assert filter.threshold < filter.MAX_THRESHOLD  # Adapted downward
        >>>
        >>> # Verify invariants
        >>> assert 0.30 <= filter.threshold <= 0.90  # INV-MORAL-01
        >>> state = filter.get_state()
        >>> assert 0.0 <= state['ema'] <= 1.0  # EMA in valid range

    Homeostatic Control Mechanism:
        The filter implements a negative feedback loop analogous to biological
        homeostasis (e.g., blood glucose regulation, temperature control):

        1. **Sensor**: EMA acceptance rate :math:`r_t`
        2. **Setpoint**: Target acceptance rate = 0.5 (50%)
        3. **Error Signal**: :math:`e_t = r_t - 0.5`
        4. **Actuator**: Threshold adjustment :math:`\\Delta\\theta = \\pm \\delta`
        5. **Negative Feedback**: High acceptance → raise threshold → lower acceptance

        This creates a stable equilibrium where the system self-regulates to maintain
        approximately 50% acceptance rate across diverse input distributions.

    References:
        - Exponential Moving Average (EMA): Widely used in signal processing and
          control systems for smoothing noisy signals while remaining responsive.
        - Dead-band control: Common in HVAC and industrial control to prevent
          actuator oscillation ("hunting") near setpoint.
        - Homeostasis: Bernard, C. (1865). Introduction à l'étude de la médecine
          expérimentale. Concept of "milieu intérieur" (internal environment stability).

    See Also:
        - ``CognitiveController``: Integrates moral filter into cognitive pipeline
        - ``compute_moral_value()``: Heuristic text scoring for moral evaluation

    Thread Safety:
        The filter uses internal locking to ensure thread-safe operation. All mutation
        methods (``adapt()``) and read methods (``get_state()``, ``get_drift_stats()``,
        ``get_current_threshold()``, ``get_ema_value()``) are protected by the same
        lock, allowing safe concurrent access from multiple threads. The ``evaluate()``
        method is read-only and does not require explicit locking.

    .. versionadded:: 1.0.0
       Initial implementation with basic EMA adaptation.
    .. versionchanged:: 1.2.0
       Added drift detection, telemetry, and configurable dead-band.
    .. versionchanged:: 1.3.0
       Added thread-safety with internal locking for all mutation and read operations.
    """

    # Default class-level constants (overridden by calibration if available)
    # Using ClassVar to indicate these are class-level, not instance-level
    MIN_THRESHOLD: ClassVar[float] = MORAL_FILTER_DEFAULTS.min_threshold if MORAL_FILTER_DEFAULTS else 0.30
    MAX_THRESHOLD: ClassVar[float] = MORAL_FILTER_DEFAULTS.max_threshold if MORAL_FILTER_DEFAULTS else 0.90
    DEAD_BAND: ClassVar[float] = MORAL_FILTER_DEFAULTS.dead_band if MORAL_FILTER_DEFAULTS else 0.05
    EMA_ALPHA: ClassVar[float] = MORAL_FILTER_DEFAULTS.ema_alpha if MORAL_FILTER_DEFAULTS else 0.1
    # Pre-computed constants for optimization
    _ONE_MINUS_ALPHA: ClassVar[float] = 1.0 - EMA_ALPHA
    _ADAPT_DELTA: ClassVar[float] = 0.05
    _BOUNDARY_EPS: ClassVar[float] = 0.01
    _DRIFT_LOGGING_MODE: ClassVar[str] = os.getenv("MLSDM_DRIFT_LOGGING", "production")
    _DRIFT_LOG_THRESHOLD: ClassVar[float] = float(os.getenv("MLSDM_DRIFT_THRESHOLD", "0.05"))
    _DRIFT_CRITICAL_THRESHOLD: ClassVar[float] = float(os.getenv("MLSDM_DRIFT_CRITICAL_THRESHOLD", "0.1"))
    _DRIFT_MIN_LOGGING: ClassVar[float] = float(os.getenv("MLSDM_DRIFT_MIN_LOGGING", "0.03"))

    def __init__(
        self, initial_threshold: float | None = None, filter_id: str = "default"
    ) -> None:
        # Use calibration default if not specified
        if initial_threshold is None:
            initial_threshold = (
                MORAL_FILTER_DEFAULTS.threshold if MORAL_FILTER_DEFAULTS else 0.50
            )

        # Validate input
        if not isinstance(initial_threshold, int | float):
            raise TypeError(
                f"initial_threshold must be a number, got {type(initial_threshold).__name__}"
            )

        # Optimization: Use pure Python min/max instead of np.clip for scalar
        self.threshold = max(
            self.MIN_THRESHOLD, min(float(initial_threshold), self.MAX_THRESHOLD)
        )
        self.ema_accept_rate = 0.5

        # Thread-safety lock for adapt() operations
        self._lock = threading.Lock()

        # NEW: Drift detection
        self._filter_id = filter_id
        self._max_history = 100  # Keep last 100 changes
        self._drift_history: deque[float] = deque(maxlen=self._max_history)

        # Initialize metrics
        record_threshold_change(
            filter_id=self._filter_id,
            old_threshold=self.threshold,
            new_threshold=self.threshold,
            ema_value=self.ema_accept_rate,
        )

    def evaluate(self, moral_value: float) -> bool:
        """Evaluate whether a moral value meets the current adaptive threshold.

        This is a deterministic function that compares the input moral value
        against the current threshold. No side effects - use adapt() to update
        the threshold based on feedback.

        Algorithm:
            - Fast-path for extreme values (≥ MAX_THRESHOLD → accept, < MIN_THRESHOLD → reject)
            - Standard case: moral_value ≥ threshold → accept

        Args:
            moral_value: Moral score to evaluate. Must satisfy:
                - Range: [0.0, 1.0] where 0.0 = maximally harmful, 1.0 = maximally beneficial
                - Type: float or int (will be converted to float)
                - Interpretation: Higher values are more morally acceptable
                - Examples: 0.8 = helpful, 0.5 = neutral, 0.2 = harmful

        Returns:
            True if moral_value ≥ threshold (accepted), False otherwise (rejected).

            Boundary behavior:
                - moral_value == threshold → True (accepted, inclusive)
                - moral_value ≥ MAX_THRESHOLD → True (always accept, safety override)
                - moral_value < MIN_THRESHOLD → False (always reject, safety override)

        Complexity:
            O(1) - constant time comparison with optional debug logging.

        Side Effects:
            - If DEBUG logging enabled, logs boundary cases (near min/max/threshold)
            - No state modifications (pure function for given threshold state)
            - Deterministic output (INV-MORAL-05)

        Thread Safety:
            This method is read-only and thread-safe without explicit locking.
            Concurrent evaluations with concurrent adapt() may see threshold changes,
            but each individual evaluation is atomic and consistent.

        Example:
            >>> filter = MoralFilterV2(initial_threshold=0.50)
            >>>
            >>> # Standard evaluation
            >>> assert filter.evaluate(0.75) == True   # Above threshold
            >>> assert filter.evaluate(0.50) == True   # Equal to threshold (inclusive)
            >>> assert filter.evaluate(0.40) == False  # Below threshold
            >>>
            >>> # Boundary cases (safety overrides)
            >>> assert filter.evaluate(0.95) == True   # ≥ MAX_THRESHOLD (0.90) → always accept
            >>> assert filter.evaluate(0.25) == False  # < MIN_THRESHOLD (0.30) → always reject
            >>>
            >>> # Verify deterministic behavior (INV-MORAL-05)
            >>> results = [filter.evaluate(0.60) for _ in range(100)]
            >>> assert all(r == results[0] for r in results)  # Same input → same output

        See Also:
            - ``adapt()``: Update threshold based on acceptance feedback
            - ``compute_moral_value()``: Compute moral score from text

        Notes:
            - This method does NOT adapt the threshold. Call adapt() separately.
            - Fast-path optimization handles extreme values without threshold check.
            - Logging at DEBUG level for boundary cases (within 0.01 of thresholds).

        .. versionadded:: 1.0.0
        """
        if logger.isEnabledFor(logging.DEBUG):
            self._log_boundary_cases(moral_value)

        # Optimize: fast-path for clear accept/reject cases
        if moral_value >= self.MAX_THRESHOLD:
            return True
        if moral_value < self.MIN_THRESHOLD:
            return False
        return moral_value >= self.threshold

    def adapt(self, accepted: bool) -> None:
        """Adapt threshold using EMA homeostatic control with drift detection.

        Updates the exponential moving average (EMA) of acceptance rate and adjusts
        the moral threshold to maintain approximately 50% acceptance rate. This
        implements a negative feedback control loop analogous to biological homeostasis.

        Algorithm:
            1. Update EMA: :math:`r_t = \\alpha a_t + (1-\\alpha) r_{t-1}`
            2. Compute error: :math:`e_t = r_t - 0.5` (target rate)
            3. If :math:`|e_t| > \\epsilon` (dead-band), adjust threshold:
               - Positive error (too many accepts) → increase threshold
               - Negative error (too many rejects) → decrease threshold
            4. Clip threshold to [MIN_THRESHOLD, MAX_THRESHOLD]
            5. Record drift metrics if threshold changed

        Args:
            accepted: Whether the last event was accepted. Must be:
                - Type: bool
                - True: Event was morally acceptable
                - False: Event was morally rejected
                - Interpretation: Provides feedback for adaptive control

        Complexity:
            O(1) - constant time EMA update, threshold adjustment, and drift recording.

        Side Effects:
            - Updates self.ema_accept_rate (EMA state)
            - May update self.threshold (if error exceeds dead-band)
            - Records Prometheus metrics for threshold changes
            - Logs WARNING/ERROR for significant drift (> 0.05 or > 0.10)
            - Appends to internal drift history (max 100 entries)

        Convergence:
            - EMA converges to empirical acceptance rate: :math:`r_\\infty \\to \\mathbb{E}[a_t]`
            - Threshold stabilizes when :math:`r_t \\approx 0.5`
            - Dead-band prevents oscillation for :math:`|r_t - 0.5| < 0.05`

        Drift Detection:
            Monitors threshold changes to detect anomalous behavior:
            - Single-step drift > 0.05 → WARNING (configurable via MLSDM_DRIFT_THRESHOLD)
            - Single-step drift > 0.10 → ERROR (critical, configurable via MLSDM_DRIFT_CRITICAL_THRESHOLD)
            - Sustained drift > 0.15 over 10 steps → ERROR (trend)
            - Drift < 0.03 → silent (configurable via MLSDM_DRIFT_MIN_LOGGING)

        Thread Safety:
            This method is now thread-safe with internal locking. Multiple threads can
            safely call adapt() concurrently.

        Example:
            >>> filter = MoralFilterV2(initial_threshold=0.50)
            >>> initial_threshold = filter.threshold
            >>>
            >>> # Simulate high acceptance rate (80%)
            >>> for _ in range(100):
            ...     filter.adapt(accepted=True)
            >>> # Threshold should increase to compensate
            >>> assert filter.threshold > initial_threshold
            >>> assert filter.ema_accept_rate > 0.50  # EMA reflects high acceptance
            >>>
            >>> # Simulate low acceptance rate (20%)
            >>> for _ in range(200):
            ...     filter.adapt(accepted=False)
            >>> # Threshold should decrease to compensate
            >>> assert filter.threshold < filter.MAX_THRESHOLD
            >>> assert filter.ema_accept_rate < 0.50  # EMA reflects low acceptance
            >>>
            >>> # Verify invariants hold
            >>> assert 0.30 <= filter.threshold <= 0.90  # INV-MORAL-01

        See Also:
            - ``evaluate()``: Evaluate moral value against current threshold
            - ``get_drift_stats()``: Get drift statistics and history

        Mathematical Proof Sketch (EMA Convergence):
            Let :math:`a_t \\sim \\text{Bernoulli}(p)` be i.i.d. acceptance indicators.
            Then the EMA :math:`r_t = \\alpha a_t + (1-\\alpha) r_{t-1}` satisfies:

            .. math::
                \\mathbb{E}[r_t] \\to p \\text{ as } t \\to \\infty

            Proof: :math:`\\mathbb{E}[r_t] = \\alpha p + (1-\\alpha) \\mathbb{E}[r_{t-1}]`
            has fixed point :math:`r^* = p`. Since :math:`|1-\\alpha| < 1`, the
            recursion converges geometrically to :math:`p`.

        .. versionadded:: 1.0.0
        .. versionchanged:: 1.2.0
           Added drift detection and telemetry.
        .. versionchanged:: 1.3.0
           Added thread-safety with internal locking.
        """
        with self._lock:
            # Store old value for drift calculation
            old_threshold = self.threshold

            # Existing adaptation logic
            signal = 1.0 if accepted else 0.0
            self.ema_accept_rate = (
                self.EMA_ALPHA * signal + self._ONE_MINUS_ALPHA * self.ema_accept_rate
            )
            error = self.ema_accept_rate - 0.5

            if error > self.DEAD_BAND:
                # Positive error - increase threshold
                new_threshold = self.threshold + self._ADAPT_DELTA
                self.threshold = min(new_threshold, self.MAX_THRESHOLD)
            elif error < -self.DEAD_BAND:
                # Negative error - decrease threshold
                new_threshold = self.threshold - self._ADAPT_DELTA
                self.threshold = max(new_threshold, self.MIN_THRESHOLD)

            # NEW: Record drift if threshold changed
            if self.threshold != old_threshold:
                self._record_drift(old_threshold, self.threshold)

    def get_state(self) -> dict[str, float]:
        with self._lock:
            return {
                "threshold": float(self.threshold),
                "ema": float(self.ema_accept_rate),
                "min_threshold": float(self.MIN_THRESHOLD),
                "max_threshold": float(self.MAX_THRESHOLD),
                "dead_band": float(self.DEAD_BAND),
            }

    def _log_boundary_cases(self, moral_value: float) -> None:
        """Log boundary cases for moral evaluation at DEBUG level."""
        is_near_min = abs(moral_value - self.MIN_THRESHOLD) <= self._BOUNDARY_EPS
        is_near_max = abs(moral_value - self.MAX_THRESHOLD) <= self._BOUNDARY_EPS
        is_near_threshold = abs(moral_value - self.threshold) <= self._BOUNDARY_EPS

        if is_near_min or is_near_max or is_near_threshold:
            logger.debug(
                "MoralFilterV2 boundary case: value=%.3f threshold=%.3f min=%.3f max=%.3f",
                moral_value,
                self.threshold,
                self.MIN_THRESHOLD,
                self.MAX_THRESHOLD,
            )

    def _record_drift(self, old: float, new: float) -> None:
        """Record and analyze threshold drift.

        Args:
            old: Previous threshold value
            new: New threshold value

        Side Effects:
            - Updates drift history
            - Records Prometheus metrics
            - Logs warnings/errors for significant drift
        """
        # Update drift history
        self._drift_history.append(new)

        # Record metrics
        record_threshold_change(
            filter_id=self._filter_id,
            old_threshold=old,
            new_threshold=new,
            ema_value=self.ema_accept_rate,
        )

        # Check for sustained drift (trend over history)
        if len(self._drift_history) >= 10:
            recent_drift = self._drift_history[-1] - self._drift_history[-10]
            if abs(recent_drift) >= 0.15:  # >=0.15 absolute change over 10 operations
                logger.error(
                    "SUSTAINED DRIFT: threshold drifted %.3f over last 10 operations "
                    "for filter '%s'",
                    recent_drift,
                    self._filter_id,
                )

        # Analyze for anomalous drift
        drift_magnitude = abs(new - old)

        if drift_magnitude <= self._DRIFT_MIN_LOGGING:
            return

        # Note: These are absolute threshold differences, not percentages
        # since thresholds are in [0.3, 0.9] range, 0.1 absolute = ~17% relative change
        if drift_magnitude > self._DRIFT_CRITICAL_THRESHOLD:
            logger.error(
                "CRITICAL DRIFT: threshold changed %.3f (%.3f → %.3f) for filter '%s'",
                drift_magnitude,
                old,
                new,
                self._filter_id,
            )
        elif (
            drift_magnitude > self._DRIFT_LOG_THRESHOLD
            and self._DRIFT_LOGGING_MODE != "silent"
        ):
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(
                    "Significant drift: threshold changed %.3f (%.3f → %.3f) for filter '%s'",
                    drift_magnitude,
                    old,
                    new,
                    self._filter_id,
                )

    def get_drift_stats(self) -> dict[str, float]:
        """Get drift statistics.

        Returns:
            Dictionary with drift statistics including:
            - total_changes: Number of threshold changes recorded
            - drift_range: Range of threshold values seen
            - min_threshold: Minimum threshold in history
            - max_threshold: Maximum threshold in history
            - current_threshold: Current threshold value
            - ema_acceptance: Current EMA acceptance rate
        """
        with self._lock:
            if len(self._drift_history) < 2:
                return {
                    "total_changes": 0,
                    "drift_range": 0.0,
                    "current_threshold": self.threshold,
                }

            return {
                "total_changes": len(self._drift_history),
                "drift_range": max(self._drift_history) - min(self._drift_history),
                "min_threshold": min(self._drift_history),
                "max_threshold": max(self._drift_history),
                "current_threshold": self.threshold,
                "ema_acceptance": self.ema_accept_rate,
            }

    def get_current_threshold(self) -> float:
        """Get the current moral threshold value.

        Read-only method for introspection - no side effects.

        Returns:
            Current threshold value (0.0-1.0).
        """
        with self._lock:
            return float(self.threshold)

    def get_ema_value(self) -> float:
        """Get the current EMA (exponential moving average) of acceptance rate.

        Read-only method for introspection - no side effects.

        Returns:
            Current EMA value (0.0-1.0).
        """
        with self._lock:
            return float(self.ema_accept_rate)

    def compute_moral_value(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> float:
        """Compute a moral value score for the given text.

        This is a heuristic-based scoring method that analyzes text for
        potentially harmful patterns. The approach is "innocent until proven
        guilty" - text is considered acceptable (high score) unless harmful
        patterns are detected.

        Uses pre-compiled regex patterns with word boundary matching to avoid
        false positives (e.g., "harm" won't match "pharmacy" or "harmless").
        O(n) complexity for text length n due to single-pass regex matching.

        Args:
            text: Input text to analyze for moral content.

        Returns:
            Moral value score in [0.0, 1.0] where higher is more acceptable.
            - 0.8: Neutral/normal text (no harmful patterns)
            - 0.3-0.7: Text with some harmful patterns
            - <0.3: Text with multiple harmful patterns

        Note:
            This implementation uses simple pattern matching. For production
            use with higher accuracy, consider integrating with toxicity
            detection APIs (e.g., Perspective API) or fine-tuned classifiers.
        """
        if not text or not text.strip():
            return 0.8  # Assume empty text is acceptable

        # Use pre-compiled regex patterns with word boundary matching
        # This is O(n) for text length and avoids false positives
        harmful_matches = _HARMFUL_REGEX.findall(text)
        positive_matches = _POSITIVE_REGEX.findall(text)

        harmful_count = len(harmful_matches)
        positive_count = len(positive_matches)
        if metadata is not None:
            metadata["harmful_count"] = harmful_count
            metadata["positive_count"] = positive_count
        if context is not None:
            context_metadata = context.setdefault("metadata", {})
            if isinstance(context_metadata, dict):
                context_metadata["harmful_count"] = harmful_count
                context_metadata["positive_count"] = positive_count

        # Base score is high (0.8) - "innocent until proven guilty"
        # This ensures neutral text passes normal moral thresholds
        base_score = 0.8

        # Adjust score based on pattern matches
        # Each harmful pattern reduces score by 0.15 (more aggressive penalty)
        # Each positive pattern increases score by 0.05 (max 1.0)
        adjusted_score = base_score - (harmful_count * 0.15) + (positive_count * 0.05)

        # Clamp to valid range
        return max(0.0, min(1.0, adjusted_score))
