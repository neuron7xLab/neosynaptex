"""Input guards for computational safety.

Validates inputs BEFORE they enter the computation pipeline.
Catches NaN, Inf, wrong shapes, out-of-range values at the gate
instead of letting them cascade through 20+ subsystems.
"""

from __future__ import annotations

import numpy as np

__all__ = ["ValidationError", "validate_field", "validate_field_sequence"]


class ValidationError(ValueError):
    """Raised when input fails validation."""


def validate_field(field: np.ndarray, context: str = "field") -> None:
    """Validate a 2D field array before computation.

    Checks:
        - Is ndarray
        - Is 2D
        - Is square
        - No NaN
        - No Inf
        - Not empty
        - Reasonable size (2-1024)

    Raises:
        ValidationError with descriptive message.
    """
    if not isinstance(field, np.ndarray):
        msg = f"{context}: expected ndarray, got {type(field).__name__}"
        raise ValidationError(msg)

    if field.ndim != 2:
        msg = f"{context}: expected 2D, got {field.ndim}D shape={field.shape}"
        raise ValidationError(msg)

    if field.shape[0] != field.shape[1]:
        msg = f"{context}: expected square, got shape={field.shape}"
        raise ValidationError(msg)

    N = field.shape[0]
    if N < 2:
        msg = f"{context}: grid too small (N={N}, min=2)"
        raise ValidationError(msg)

    if N > 1024:
        msg = f"{context}: grid too large (N={N}, max=1024)"
        raise ValidationError(msg)

    if np.any(np.isnan(field)):
        n_nan = int(np.sum(np.isnan(field)))
        msg = f"{context}: contains {n_nan} NaN values"
        raise ValidationError(msg)

    if np.any(np.isinf(field)):
        n_inf = int(np.sum(np.isinf(field)))
        msg = f"{context}: contains {n_inf} Inf values"
        raise ValidationError(msg)


def validate_field_sequence(seq: object, context: str = "FieldSequence") -> None:
    """Validate a FieldSequence before it enters the pipeline.

    Checks field + history consistency.
    """
    if not hasattr(seq, "field"):
        msg = f"{context}: missing 'field' attribute"
        raise ValidationError(msg)

    validate_field(seq.field, f"{context}.field")  # type: ignore[arg-type]

    history = getattr(seq, "history", None)
    if history is not None:
        if not isinstance(history, np.ndarray):
            msg = f"{context}.history: expected ndarray, got {type(history).__name__}"
            raise ValidationError(msg)

        if history.ndim != 3:
            msg = f"{context}.history: expected 3D (T,N,N), got {history.ndim}D"
            raise ValidationError(msg)

        if history.shape[1:] != seq.field.shape:  # type: ignore[union-attr]
            msg = (
                f"{context}.history: shape mismatch — "
                f"history={history.shape[1:]}, field={seq.field.shape}"  # type: ignore[union-attr]
            )
            raise ValidationError(msg)

        if np.any(np.isnan(history)):
            msg = f"{context}.history: contains NaN"
            raise ValidationError(msg)

        if np.any(np.isinf(history)):
            msg = f"{context}.history: contains Inf"
            raise ValidationError(msg)


def safe_json_value(v: object) -> object:
    """Sanitize a value for JSON serialization (NaN/Inf → None)."""
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return v
