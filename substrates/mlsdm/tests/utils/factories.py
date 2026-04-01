"""
Factory functions for creating test objects.

This module provides reusable factories for common test objects
to reduce duplication across test files.
"""

from collections.abc import Callable

import numpy as np


def create_test_vector(dim: int = 384, seed: int | None = None) -> np.ndarray:
    """
    Create a normalized test vector.

    Args:
        dim: Dimensionality of the vector.
        seed: Random seed for reproducibility. If None, uses current random state.

    Returns:
        A normalized numpy array of shape (dim,).
    """
    if seed is not None:
        np.random.seed(seed)
    vec = np.random.randn(dim).astype(np.float32)
    return vec / np.linalg.norm(vec)


def create_test_vectors(
    n: int,
    dim: int = 384,
    seed: int = 42,
) -> list[np.ndarray]:
    """
    Create a list of normalized test vectors.

    Args:
        n: Number of vectors to create.
        dim: Dimensionality of each vector.
        seed: Random seed for reproducibility.

    Returns:
        A list of n normalized numpy arrays.
    """
    np.random.seed(seed)
    vectors = []
    for _ in range(n):
        vec = np.random.randn(dim).astype(np.float32)
        vectors.append(vec / np.linalg.norm(vec))
    return vectors


def create_mock_llm(
    response: str = "Mock LLM response with proper grammar and function words.",
    delay: float = 0.0,
) -> Callable[[str, int], str]:
    """
    Create a mock LLM generation function.

    Args:
        response: The fixed response to return.
        delay: Optional delay in seconds before returning.

    Returns:
        A function that simulates LLM generation.
    """
    import time

    def _generate(prompt: str, max_tokens: int = 100) -> str:
        if delay > 0:
            time.sleep(delay)
        return response

    return _generate


def create_mock_embedder(dim: int = 384) -> Callable[[str], np.ndarray]:
    """
    Create a mock embedding function.

    The embedder generates deterministic embeddings based on text hash,
    ensuring the same text always produces the same embedding.

    Args:
        dim: Dimensionality of embeddings.

    Returns:
        A function that generates embeddings for text.
    """

    def _embed(text: str) -> np.ndarray:
        # Use text hash for deterministic output
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(dim).astype(np.float32)
        return vec / np.linalg.norm(vec)

    return _embed


def create_moral_value_distribution(
    n: int,
    toxic_ratio: float = 0.3,
    seed: int = 42,
) -> list[float]:
    """
    Create a distribution of moral values for testing.

    Args:
        n: Number of values to generate.
        toxic_ratio: Proportion of toxic (low moral) values.
        seed: Random seed for reproducibility.

    Returns:
        A shuffled list of moral values.
    """
    np.random.seed(seed)
    n_toxic = int(n * toxic_ratio)
    n_safe = n - n_toxic

    # Toxic content: moral values between 0.1-0.4
    toxic_values = np.random.uniform(0.1, 0.4, n_toxic).tolist()

    # Safe content: moral values between 0.6-0.95
    safe_values = np.random.uniform(0.6, 0.95, n_safe).tolist()

    all_values = toxic_values + safe_values
    np.random.shuffle(all_values)
    return all_values


def create_pelm_memory(
    dim: int = 384,
    capacity: int = 1000,
) -> "PhaseEntangledLatticeMemory":  # noqa: F821
    """
    Create a PhaseEntangledLatticeMemory instance for testing.

    Args:
        dim: Vector dimensionality.
        capacity: Maximum number of vectors.

    Returns:
        A PELM instance.
    """
    from mlsdm.memory import PhaseEntangledLatticeMemory

    return PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)


def create_moral_filter(
    threshold: float = 0.5,
    adapt_rate: float = 0.05,
) -> "MoralFilter":  # noqa: F821
    """
    Create a MoralFilter instance for testing.

    Args:
        threshold: Initial moral threshold.
        adapt_rate: Adaptation rate.

    Returns:
        A MoralFilter instance.
    """
    from mlsdm.cognition.moral_filter import MoralFilter

    return MoralFilter(threshold=threshold, adapt_rate=adapt_rate)


def create_cognitive_rhythm(
    wake_duration: int = 10,
    sleep_duration: int = 5,
) -> "CognitiveRhythm":  # noqa: F821
    """
    Create a CognitiveRhythm instance for testing.

    Args:
        wake_duration: Duration of wake phase.
        sleep_duration: Duration of sleep phase.

    Returns:
        A CognitiveRhythm instance.
    """
    from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm

    return CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)
