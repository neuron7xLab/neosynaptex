"""
MLSDM HTTP Client SDK.

Provides a Python client for interacting with the MLSDM HTTP API.

Example:
    >>> from sdk.python.client import MLSDMClient
    >>> client = MLSDMClient(base_url="http://localhost:8000")
    >>> result = client.infer("What is machine learning?")
    >>> print(result.response)
"""

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class InferResponse:
    """Structured response from /infer endpoint.

    Attributes:
        response: Generated text response.
        accepted: Whether the request was accepted by moral filter.
        phase: Current cognitive phase (wake/sleep).
        moral_metadata: Moral filtering metadata.
        timing: Performance timing information.
        governance: Full governance state (if available).
    """

    response: str
    accepted: bool
    phase: str
    moral_metadata: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None
    governance: dict[str, Any] | None = None
    rag_metadata: dict[str, Any] | None = None
    aphasia_metadata: dict[str, Any] | None = None


@dataclass
class HealthResponse:
    """Structured response from /health endpoint.

    Attributes:
        status: Health status (healthy/unhealthy).
    """

    status: str


@dataclass
class ReadinessResponse:
    """Structured response from /health/readiness endpoint.

    Attributes:
        ready: Whether service is ready.
        status: Status string (ready/not_ready).
        checks: Individual check results.
    """

    ready: bool
    status: str
    checks: dict[str, bool]


class MLSDMClient:
    """HTTP client for MLSDM API.

    Args:
        base_url: Base URL for the API (default: http://localhost:8000).
        api_key: Optional API key for authenticated endpoints.
        timeout: Request timeout in seconds (default: 30).

    Example:
        >>> client = MLSDMClient(base_url="http://localhost:8000")
        >>> # Check health
        >>> health = client.health()
        >>> print(f"Status: {health.status}")
        >>> # Run inference
        >>> result = client.infer("Hello, world!")
        >>> print(f"Response: {result.response}")
        >>> print(f"Accepted: {result.accepted}")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def health(self) -> HealthResponse:
        """Check service health.

        Returns:
            HealthResponse with status.

        Raises:
            requests.HTTPError: If request fails.
        """
        response = requests.get(
            f"{self.base_url}/health",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return HealthResponse(status=data["status"])

    def readiness(self) -> ReadinessResponse:
        """Check service readiness.

        Returns:
            ReadinessResponse with ready status and checks.

        Raises:
            requests.HTTPError: If request fails.
        """
        response = requests.get(
            f"{self.base_url}/health/readiness",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return ReadinessResponse(
            ready=data["ready"],
            status=data["status"],
            checks=data["checks"],
        )

    def infer(
        self,
        prompt: str,
        *,
        moral_value: float | None = None,
        max_tokens: int | None = None,
        secure_mode: bool = False,
        aphasia_mode: bool = False,
        rag_enabled: bool = True,
        context_top_k: int | None = None,
        user_intent: str | None = None,
    ) -> InferResponse:
        """Run inference with governance.

        Args:
            prompt: Input text prompt.
            moral_value: Moral threshold (0.0-1.0, default: 0.5).
            max_tokens: Maximum tokens to generate.
            secure_mode: Enable enhanced security filtering.
            aphasia_mode: Enable aphasia detection/repair.
            rag_enabled: Enable RAG context retrieval (default: True).
            context_top_k: Number of context items for RAG.
            user_intent: User intent category.

        Returns:
            InferResponse with response and metadata.

        Raises:
            requests.HTTPError: If request fails.

        Example:
            >>> result = client.infer(
            ...     "Explain quantum computing",
            ...     moral_value=0.7,
            ...     secure_mode=True
            ... )
            >>> print(result.response)
        """
        payload: dict[str, Any] = {
            "prompt": prompt,
            "secure_mode": secure_mode,
            "aphasia_mode": aphasia_mode,
            "rag_enabled": rag_enabled,
        }

        if moral_value is not None:
            payload["moral_value"] = moral_value
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if context_top_k is not None:
            payload["context_top_k"] = context_top_k
        if user_intent is not None:
            payload["user_intent"] = user_intent

        response = requests.post(
            f"{self.base_url}/infer",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return InferResponse(
            response=data["response"],
            accepted=data["accepted"],
            phase=data["phase"],
            moral_metadata=data.get("moral_metadata"),
            timing=data.get("timing"),
            governance=data.get("governance"),
            rag_metadata=data.get("rag_metadata"),
            aphasia_metadata=data.get("aphasia_metadata"),
        )

    def generate(
        self,
        prompt: str,
        *,
        moral_value: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate response using /generate endpoint.

        Args:
            prompt: Input text prompt.
            moral_value: Moral threshold (0.0-1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            Full response dictionary from API.

        Raises:
            requests.HTTPError: If request fails.
        """
        payload: dict[str, Any] = {"prompt": prompt}
        if moral_value is not None:
            payload["moral_value"] = moral_value
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = requests.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    def status(self) -> dict[str, Any]:
        """Get service status with system information.

        Returns:
            Status dictionary with version, backend, system info.

        Raises:
            requests.HTTPError: If request fails.
        """
        response = requests.get(
            f"{self.base_url}/status",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    # Legacy methods for backward compatibility
    def process_event(self, event_vector: list[float], moral_value: float) -> dict[str, Any]:
        """Process event (legacy v1 API).

        Args:
            event_vector: Event embedding vector.
            moral_value: Moral value for the event.

        Returns:
            State response dictionary.

        Raises:
            requests.HTTPError: If request fails.
        """
        payload = {"event_vector": event_vector, "moral_value": moral_value}
        response = requests.post(
            f"{self.base_url}/v1/process_event/",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    def get_state(self) -> dict[str, Any]:
        """Get current state (legacy v1 API).

        Returns:
            State dictionary with memory norms and metrics.

        Raises:
            requests.HTTPError: If request fails.
        """
        response = requests.get(
            f"{self.base_url}/v1/state/",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
