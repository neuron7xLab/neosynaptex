"""Traceability helpers for mathematical test governance."""

from __future__ import annotations

import pytest


def traces_equation(eq_id: str):
    """Bind a test to a formal equation identifier."""
    return pytest.mark.trace_eq(eq_id)
