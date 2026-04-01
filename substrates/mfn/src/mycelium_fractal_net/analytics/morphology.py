"""Morphology descriptor computation.

Includes LZ76 complexity (Kaspar & Schuster 1987) for temporal analysis.
"""

from __future__ import annotations

import numpy as np


def _lempel_ziv_76_complexity(s: str) -> float:
    """Lempel-Ziv complexity (LZ76) via sequential parsing.

    Counts the number of new patterns encountered when parsing
    the binary string left-to-right. Normalized by ``len(s) / log2(len(s))``
    to give a value in approximately [0, 1] for comparison across lengths.

    Reference: Kaspar & Schuster (1987) Phys Rev A 36:842-848
               Lempel & Ziv (1976) IEEE Trans Inform Theory IT-22:75-81
    """
    n = len(s)
    if n <= 1:
        return 0.0

    complexity = 1
    i = 0
    k = 1
    k_max = 1

    while i + k <= n:
        # Check if s[i+1..i+k] is a substring of s[0..i+k-1]
        substring = s[i + 1 : i + k + 1] if i + k + 1 <= n else s[i + 1 : n]
        prefix = s[0 : i + k]

        if substring in prefix:
            k += 1
            if i + k > n:
                complexity += 1
                break
        else:
            k_max = max(k_max, k)
            complexity += 1
            i += k_max if k_max > 0 else 1
            k = 1
            k_max = 1

    # Normalize: for random binary string, LZ76 ~ n / log2(n)
    import math

    normalizer = n / max(1.0, math.log2(n))
    return float(complexity / normalizer)


from typing import TYPE_CHECKING

from mycelium_fractal_net.analytics.connectivity import compute_connectivity_features
from mycelium_fractal_net.analytics.embedding import build_embedding
from mycelium_fractal_net.analytics.legacy_features import compute_features
from mycelium_fractal_net.analytics.multiscale import compute_multiscale_profile
from mycelium_fractal_net.analytics.temporal_features import compute_temporal_features
from mycelium_fractal_net.types.analytics import (
    ComplexityMetrics,
    ConnectivityFeatures,
    NeuromodulationFeatures,
    StabilityMetrics,
    TemporalFeatures,
)
from mycelium_fractal_net.types.features import MorphologyDescriptor

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

_DESCRIPTOR_VERSION = "mfn-morphology-v2"


def _stability_metrics(sequence: FieldSequence) -> StabilityMetrics:
    field = sequence.field
    history = sequence.history
    instability_index = float(np.std(field) / (abs(np.mean(field)) + 1e-12))
    collapse_score = float(np.mean(field < -0.090))
    transition_score = 0.0
    if history is not None and history.shape[0] >= 2:
        deltas = np.diff(history, axis=0)
        transition_score = float(np.max(np.mean(np.abs(deltas), axis=(1, 2))))
    return StabilityMetrics(
        instability_index=instability_index,
        near_transition_score=transition_score,
        collapse_risk_score=collapse_score,
    )


def _complexity_metrics(sequence: FieldSequence) -> ComplexityMetrics:
    history = sequence.history if sequence.history is not None else sequence.field[None, :, :]
    mean_series = np.mean(history, axis=(1, 2))
    if len(mean_series) < 2:
        temporal_lzc = 0.0
        temporal_hfd = 0.0
        multiscale_entropy_short = 0.0
    else:
        bits = "".join("1" if value > np.mean(mean_series) else "0" for value in mean_series)
        temporal_lzc = _lempel_ziv_76_complexity(bits)
        diffs = np.abs(np.diff(mean_series))
        temporal_hfd = float(np.mean(diffs) / (np.std(mean_series) + 1e-12))
        coarse = (
            mean_series.reshape(-1, 2).mean(axis=1)
            if len(mean_series) >= 4 and len(mean_series) % 2 == 0
            else mean_series
        )
        multiscale_entropy_short = float(np.std(coarse) / (abs(np.mean(coarse)) + 1e-12))
    return ComplexityMetrics(
        temporal_lzc=temporal_lzc,
        temporal_hfd=temporal_hfd,
        multiscale_entropy_short=multiscale_entropy_short,
    )


def _neuromodulation_metrics(sequence: FieldSequence) -> NeuromodulationFeatures:
    spec = sequence.spec.neuromodulation if sequence.spec is not None else None
    # Prefer strongly-typed snapshot; fall back to untyped metadata for backward compat
    ns = sequence.neuromodulation_state
    if ns is not None:
        plasticity = ns.plasticity_index
        inhibition = ns.effective_inhibition
        gain = ns.effective_gain
        obs = ns.observation_noise_gain
    else:
        meta = dict(sequence.metadata or {})
        state = dict(meta.get("neuromodulation_state") or {})
        plasticity = float(state.get("plasticity_index", meta.get("plasticity_index_mean", 0.0)))
        inhibition = float(
            state.get("effective_inhibition", meta.get("effective_inhibition_mean", 0.0))
        )
        gain = float(state.get("effective_gain", meta.get("effective_gain_mean", 0.0)))
        obs = float(
            state.get("observation_noise_gain", meta.get("observation_noise_gain_mean", 0.0))
        )
    return NeuromodulationFeatures(
        enabled=1.0 if (spec is not None and spec.enabled) else 0.0,
        plasticity_index=plasticity,
        effective_inhibition=inhibition,
        effective_gain=gain,
        observation_noise_gain=obs,
    )


import threading

_descriptor_cache: dict[str, MorphologyDescriptor] = {}
_CACHE_MAX_SIZE = 64
_cache_lock = threading.Lock()


def compute_morphology_descriptor(sequence: FieldSequence) -> MorphologyDescriptor:
    """Compute morphology descriptor with automatic caching by runtime_hash.

    Thread-safe LRU cache eliminates redundant recomputation when the same
    FieldSequence is analyzed by detect, forecast, compare, and report.
    """
    cache_key = sequence.runtime_hash
    with _cache_lock:
        cached = _descriptor_cache.get(cache_key)
        if cached is not None:
            return cached

    field_data = sequence.history if sequence.history is not None else sequence.field
    base = compute_features(field_data).to_dict()
    temporal_raw = compute_temporal_features(sequence.history)
    multiscale = compute_multiscale_profile(sequence.field)
    stability = _stability_metrics(sequence)
    complexity = _complexity_metrics(sequence)
    connectivity_raw = compute_connectivity_features(sequence)
    neuromodulation = _neuromodulation_metrics(sequence)

    # Build typed objects from raw dicts
    temporal = TemporalFeatures.from_dict(temporal_raw)
    connectivity = ConnectivityFeatures.from_dict(connectivity_raw)

    # Build embedding from dict representations
    embedding = build_embedding(
        [
            base,
            temporal.to_dict(),
            multiscale,
            stability.to_dict(),
            complexity.to_dict(),
            connectivity.to_dict(),
            neuromodulation.to_dict(),
        ]
    )
    metadata = {
        "grid_size": sequence.grid_size,
        "num_steps": sequence.num_steps,
        "runtime_hash": sequence.runtime_hash,
        "descriptor_family": _DESCRIPTOR_VERSION,
    }
    # Pass typed objects directly — MorphologyDescriptor normalizes to dicts internally
    result = MorphologyDescriptor(
        version=_DESCRIPTOR_VERSION,
        embedding=embedding,
        features={k: float(v) for k, v in base.items()},
        temporal=temporal.to_dict(),
        multiscale=multiscale,
        stability=stability.to_dict(),
        complexity=complexity.to_dict(),
        connectivity=connectivity.to_dict(),
        neuromodulation=neuromodulation.to_dict(),
        metadata=metadata,
    )
    # Cache result; thread-safe eviction
    with _cache_lock:
        if len(_descriptor_cache) >= _CACHE_MAX_SIZE:
            oldest_key = next(iter(_descriptor_cache))
            del _descriptor_cache[oldest_key]
        _descriptor_cache[cache_key] = result
    return result
