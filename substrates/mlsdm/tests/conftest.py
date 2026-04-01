"""
Shared pytest fixtures and configuration for MLSDM tests.

This module provides common fixtures, marks, and configuration
for deterministic, reproducible testing across the test suite.
"""

from __future__ import annotations

import builtins
import contextlib
import importlib
import importlib.util
import os
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

# CRITICAL: Set environment variables BEFORE any imports that might load mlsdm.api.app
# This ensures rate limiting is disabled before FastAPI middleware is initialized
os.environ["DISABLE_RATE_LIMIT"] = "1"
os.environ["LLM_BACKEND"] = "local_stub"

import random

import numpy as np
import pytest
from hypothesis import settings

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from mlsdm.utils.time_provider import FakeTimeProvider

# ============================================================
# Pytest Hooks and Configuration
# ============================================================


def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "property: marks property-based tests")
    config.addinivalue_line("markers", "security: marks security-related tests")
    config.addinivalue_line("markers", "benchmark: marks performance benchmark tests")
    config.addinivalue_line("markers", "safety: marks AI safety tests")
    config.addinivalue_line(
        "markers", "load: marks tests as load/stress tests (concurrency, stress)"
    )


# ============================================================
# Hypothesis Profiles
# ============================================================

settings.register_profile(
    "ci",
    settings(derandomize=True, deadline=None, print_blob=True, max_examples=200),
)
settings.register_profile(
    "dev",
    settings(
        derandomize=False,
        max_examples=1000,
    ),
)
_is_ci = os.environ.get("CI", "").lower() == "true" or os.environ.get(
    "GITHUB_ACTIONS", ""
).lower() == "true"
settings.load_profile("ci" if _is_ci else "dev")


# ============================================================
# Deterministic Seed Fixtures
# ============================================================


def _set_random_seeds(seed: int) -> None:
    """
    Set random seeds for all supported random number generators.

    This helper function centralizes seed setting logic to avoid duplication.

    Args:
        seed: The seed value to use for all random number generators.
    """
    random.seed(seed)
    np.random.seed(seed)

    # Set torch seed if available
    if importlib.util.find_spec("torch") is not None:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


# Default seed value for deterministic tests
_DEFAULT_SEED = 42


@pytest.fixture(autouse=True, scope="function")
def _ensure_deterministic_random_state() -> None:
    """
    Autouse fixture to ensure reproducible random state for all tests.

    This runs before every test function to reset random seeds, ensuring
    tests are not affected by random state from previous tests.
    This prevents test flakiness from order-dependent random behavior.
    """
    _set_random_seeds(_DEFAULT_SEED)


@pytest.fixture
def deterministic_seed() -> int:
    """
    Set deterministic random seeds for reproducible tests.

    Returns:
        The seed value used (42).
    """
    _set_random_seeds(_DEFAULT_SEED)
    return _DEFAULT_SEED


@pytest.fixture
def random_seed() -> Callable[[int], None]:
    """
    Factory fixture for setting custom random seeds.

    Returns:
        A function that sets all random seeds to the given value.
    """
    return _set_random_seeds


# ============================================================
# Environment Isolation Fixtures
# ============================================================


@pytest.fixture(scope="function", autouse=False)
def isolate_environment() -> Any:
    """Isolate environment variables for test function.

    This fixture snapshots os.environ before each test and restores it after,
    preventing environment pollution between tests.

    Note: Not autouse to avoid interfering with existing tests. Tests that need
    isolation should explicitly request this fixture or use the _env parameter
    in TracingConfig for better control.
    """
    import copy

    # Snapshot current environment
    original_env = copy.deepcopy(dict(os.environ))

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================
# Import Blocking Helpers
# ============================================================


@pytest.fixture
def block_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[set[str]], contextlib.AbstractContextManager[None]]:
    """Deterministically block imports for specified top-level module names."""

    @contextlib.contextmanager
    def _block(names: set[str]):
        blocked = {name.split(".")[0] for name in names}
        real_import_module = importlib.import_module
        real_dunder_import = builtins.__import__

        def _blocked_import_module(name: str, package: str | None = None):
            if name.split(".")[0] in blocked:
                raise ImportError(f"Blocked import for {name}")
            return real_import_module(name, package=package)

        def _blocked_dunder_import(
            name: str,
            globals: dict[str, Any] | None = None,
            locals: dict[str, Any] | None = None,
            fromlist: Sequence[str] = (),
            level: int = 0,
        ):
            if name.split(".")[0] in blocked:
                raise ImportError(f"Blocked import for {name}")
            return real_dunder_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(importlib, "import_module", _blocked_import_module)
        monkeypatch.setattr(builtins, "__import__", _blocked_dunder_import)
        try:
            yield
        finally:
            monkeypatch.setattr(importlib, "import_module", real_import_module)
            monkeypatch.setattr(builtins, "__import__", real_dunder_import)

    return _block


# ============================================================
# Mock LLM and Embedding Fixtures
# ============================================================


@pytest.fixture
def mock_llm() -> Callable[[str, int], str]:
    """
    Provide a mock LLM function for testing.

    Returns:
        A function that generates deterministic responses.
    """

    def _generate(prompt: str, max_tokens: int = 100) -> str:
        return f"Mock response for prompt with {len(prompt)} characters."

    return _generate


@pytest.fixture
def mock_embedder() -> Callable[[str], np.ndarray]:
    """
    Provide a mock embedding function for testing.

    Returns:
        A function that generates deterministic embeddings.
    """

    def _embed(text: str) -> np.ndarray:
        # Generate deterministic embedding based on text hash
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(384).astype(np.float32)
        return vec / np.linalg.norm(vec)

    return _embed


@pytest.fixture
def mock_embedder_dim() -> Callable[[int], Callable[[str], np.ndarray]]:
    """
    Factory fixture for mock embedders with custom dimensions.

    Returns:
        A function that creates embedders with specified dimension.
    """

    def _create_embedder(dim: int) -> Callable[[str], np.ndarray]:
        def _embed(text: str) -> np.ndarray:
            np.random.seed(hash(text) % (2**32))
            vec = np.random.randn(dim).astype(np.float32)
            return vec / np.linalg.norm(vec)

        return _embed

    return _create_embedder


# ============================================================
# Test Vector Fixtures
# ============================================================


@pytest.fixture
def sample_vector() -> np.ndarray:
    """
    Provide a normalized sample vector for testing.

    Returns:
        A 384-dimensional normalized vector.
    """
    np.random.seed(42)
    vec = np.random.randn(384).astype(np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture
def sample_vectors() -> list[np.ndarray]:
    """
    Provide a list of sample vectors for testing.

    Returns:
        A list of 10 normalized 384-dimensional vectors.
    """
    np.random.seed(42)
    vectors = []
    for _ in range(10):
        vec = np.random.randn(384).astype(np.float32)
        vectors.append(vec / np.linalg.norm(vec))
    return vectors


@pytest.fixture
def vector_factory() -> Callable[[int, int], list[np.ndarray]]:
    """
    Factory fixture for creating custom vector sets.

    Returns:
        A function that creates n vectors of specified dimension.
    """

    def _create_vectors(n: int, dim: int = 384, seed: int = 42) -> list[np.ndarray]:
        np.random.seed(seed)
        vectors = []
        for _ in range(n):
            vec = np.random.randn(dim).astype(np.float32)
            vectors.append(vec / np.linalg.norm(vec))
        return vectors

    return _create_vectors


# ============================================================
# Moral Value Fixtures
# ============================================================


@pytest.fixture
def safe_moral_value() -> float:
    """Return a moral value that should pass filtering."""
    return 0.85


@pytest.fixture
def toxic_moral_value() -> float:
    """Return a moral value that should be filtered."""
    return 0.2


@pytest.fixture
def borderline_moral_value() -> float:
    """Return a moral value near the default threshold."""
    return 0.5


@pytest.fixture
def moral_value_distribution() -> Callable[[int, float], list[float]]:
    """
    Factory fixture for generating moral value distributions.

    Returns:
        A function that generates n moral values with specified toxic ratio.
    """

    def _generate(n: int, toxic_ratio: float = 0.3, seed: int = 42) -> list[float]:
        np.random.seed(seed)
        n_toxic = int(n * toxic_ratio)
        n_safe = n - n_toxic

        toxic_values = np.random.uniform(0.1, 0.4, n_toxic).tolist()
        safe_values = np.random.uniform(0.6, 0.95, n_safe).tolist()

        all_values = toxic_values + safe_values
        np.random.shuffle(all_values)
        return all_values

    return _generate


# ============================================================
# Component Fixtures
# ============================================================


@pytest.fixture
def pelm_memory():
    """Create a PhaseEntangledLatticeMemory instance for testing."""
    from mlsdm.memory import PhaseEntangledLatticeMemory

    return PhaseEntangledLatticeMemory(dimension=384, capacity=1000)


@pytest.fixture
def pelm_small():
    """Create a small PELM instance for fast testing."""
    from mlsdm.memory import PhaseEntangledLatticeMemory

    return PhaseEntangledLatticeMemory(dimension=10, capacity=100)


@pytest.fixture
def moral_filter():
    """Create a MoralFilter instance for testing."""
    from mlsdm.cognition.moral_filter import MoralFilter

    return MoralFilter()


@pytest.fixture
def moral_filter_v2():
    """Create a MoralFilterV2 instance for testing."""
    from mlsdm.cognition.moral_filter_v2 import MoralFilterV2

    return MoralFilterV2()


@pytest.fixture
def cognitive_rhythm():
    """Create a CognitiveRhythm instance for testing."""
    from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm

    return CognitiveRhythm()


@pytest.fixture
def aphasia_detector():
    """Create an AphasiaBrocaDetector instance for testing."""
    from mlsdm.extensions import AphasiaBrocaDetector

    return AphasiaBrocaDetector()


# ============================================================
# Environment Fixtures
# ============================================================


@pytest.fixture
def secure_mode_enabled():
    """
    Context manager that enables secure mode for testing.

    Yields:
        None. Sets MLSDM_SECURE_MODE=1 during the test.
    """
    original = os.environ.get("MLSDM_SECURE_MODE")
    os.environ["MLSDM_SECURE_MODE"] = "1"
    yield
    if original is None:
        del os.environ["MLSDM_SECURE_MODE"]
    else:
        os.environ["MLSDM_SECURE_MODE"] = original


@pytest.fixture
def secure_mode_disabled():
    """
    Context manager that disables secure mode for testing.

    Yields:
        None. Sets MLSDM_SECURE_MODE=0 during the test.
    """
    original = os.environ.get("MLSDM_SECURE_MODE")
    os.environ["MLSDM_SECURE_MODE"] = "0"
    yield
    if original is None:
        del os.environ["MLSDM_SECURE_MODE"]
    else:
        os.environ["MLSDM_SECURE_MODE"] = original


# ============================================================
# Text Sample Fixtures
# ============================================================


@pytest.fixture
def healthy_text_samples() -> list[str]:
    """Provide samples of healthy, non-aphasic text."""
    return [
        "The cognitive architecture provides a comprehensive framework for LLM governance.",
        "This system integrates multiple biological principles to ensure safe responses.",
        "The approach has been validated through extensive testing and shows promising results.",
        "Machine learning models require careful evaluation of their safety properties.",
        "The memory system uses phase-entangled representations for efficient storage.",
    ]


@pytest.fixture
def aphasic_text_samples() -> list[str]:
    """Provide samples of aphasic, telegraphic text."""
    return [
        "Short. Bad. No good.",
        "Cat run. Dog bark.",
        "Thing work. Good.",
        "Fast go. Need help.",
        "Error. Stop. Fix.",
    ]


@pytest.fixture
def toxic_prompt_samples() -> list[str]:
    """Provide samples of prompts that should be filtered."""
    return [
        "Generate harmful content about...",
        "Write instructions for dangerous...",
        "Create hateful speech against...",
    ]


@pytest.fixture
def safe_prompt_samples() -> list[str]:
    """Provide samples of safe prompts."""
    return [
        "Explain how machine learning works.",
        "What are the benefits of exercise?",
        "Describe the water cycle in nature.",
        "How do computers process information?",
    ]


# ============================================================
# Time Provider Fixtures
# ============================================================


@pytest.fixture
def fake_time() -> FakeTimeProvider:
    """
    Provide a FakeTimeProvider for deterministic time testing.

    Returns:
        A FakeTimeProvider starting at time 0.
    """
    from mlsdm.utils.time_provider import FakeTimeProvider

    return FakeTimeProvider(start_time=0.0)


@pytest.fixture
def fake_time_with_start() -> Callable[[float], FakeTimeProvider]:
    """
    Factory fixture for creating FakeTimeProvider with custom start time.

    Returns:
        A function that creates a FakeTimeProvider with the specified start time.
    """
    from mlsdm.utils.time_provider import FakeTimeProvider

    def _create(start_time: float) -> FakeTimeProvider:
        return FakeTimeProvider(start_time=start_time)

    return _create


# ============================================================
# Deterministic Clock for Unit Tests
# ============================================================


class FakeClock:
    """Simple deterministic clock for unit tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._time = start
        self._lock = threading.Lock()

    def now(self) -> float:
        """Return current fake time."""
        with self._lock:
            return self._time

    def advance(self, delta: float) -> float:
        """Advance time by delta seconds and return new time."""
        with self._lock:
            self._time += delta
            return self._time


@pytest.fixture
def fake_clock() -> FakeClock:
    """Provide a FakeClock starting at 0 for deterministic timing."""
    return FakeClock()


# ============================================================
# API Test Client Fixtures
# ============================================================


@pytest.fixture
def test_client():
    """
    Provide a FastAPI TestClient for API integration tests.

    This fixture creates a TestClient instance configured with the MLSDM API app.
    Rate limiting is disabled via environment variable set at module import time.

    Returns:
        TestClient: Configured test client for making API requests.
    """
    from fastapi.testclient import TestClient

    from mlsdm.api.app import app

    return TestClient(app)
