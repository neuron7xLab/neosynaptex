"""Embedding vector construction with L2 normalization.

Builds a fixed-dimensional embedding from feature group dictionaries
and normalizes using L2 norm for scale-invariant distance metrics.

Previous approach (element-wise ``arr / max(1, |arr|)``) allowed
high-magnitude features to dominate cosine/Euclidean distance.
L2 normalization ensures ``||embedding|| = 1``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable


def build_embedding(parts: Iterable[dict[str, float]]) -> tuple[float, ...]:
    """Build an L2-normalized embedding vector from feature group dicts.

    Parameters
    ----------
    parts:
        Iterable of dicts mapping feature names to float values.
        Keys sorted within each dict for deterministic ordering.

    Returns
    -------
    tuple[float, ...]
        L2-normalized embedding. NaN/Inf replaced with 0.
    """
    values: list[float] = []
    for part in parts:
        for key in sorted(part):
            values.append(float(part[key]))
    arr = np.asarray(values, dtype=np.float64)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    norm = float(np.linalg.norm(arr))
    if norm > 0.0:
        arr = arr / norm

    return tuple(float(v) for v in arr)
