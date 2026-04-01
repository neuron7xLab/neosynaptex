"""Feature extraction from FieldSequence via MorphologyDescriptor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor

if TYPE_CHECKING:
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.field import FieldSequence



__all__ = ['extract']

def extract(sequence: FieldSequence) -> MorphologyDescriptor:
    """Canonical morphology extraction operation."""
    return compute_morphology_descriptor(sequence)
