"""Request Signing Verification for MLSDM API (SEC-007).

This module provides HMAC-based request signature verification,
enabling integrity verification and authentication for API requests.

Features:
- HMAC-SHA256 signature generation and verification
- Timestamp-based replay attack prevention
- Support for multiple signing keys (key rotation)
- Request body integrity verification
- Configurable via environment variables

Header Format:
    X-MLSDM-Signature: timestamp=1699123456,signature=abc123...
    X-MLSDM-Key-ID: key-name (optional, for key rotation)

Signature Algorithm:
    1. Create canonical request string:
       method + path + timestamp + sha256(body)
    2. Sign with HMAC-SHA256 using secret key
    3. Base64 encode the signature

Configuration (Environment Variables):
    MLSDM_SIGNING_ENABLED: "true" to enable signing verification
    MLSDM_SIGNING_KEY: HMAC secret key (or use key store)
    MLSDM_SIGNING_MAX_AGE: Max request age in seconds (default: 300)
    MLSDM_SIGNING_KEYS_PATH: Path to JSON file with key mappings

Example:
    >>> from mlsdm.security.signing import (
    ...     SigningMiddleware,
    ...     generate_signature,
    ...     verify_signature,
    ... )
    >>>
    >>> # Add middleware
    >>> app.add_middleware(SigningMiddleware)
    >>>
    >>> # Client-side: generate signature
    >>> signature = generate_signature(
    ...     method="POST",
    ...     path="/generate",
    ...     body=b'{"prompt":"Hello"}',
    ...     secret_key="your-secret-key",
    ... )
    >>> headers = {"X-MLSDM-Signature": signature}
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_match, is_path_skipped

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class SigningConfig:
    """Request signing configuration.

    Attributes:
        enabled: Whether signing verification is enabled
        secret_key: HMAC secret key (single key mode)
        max_age_seconds: Maximum request age for replay prevention
        keys: Dictionary of key_id -> secret_key (multi-key mode)
    """

    enabled: bool = False
    secret_key: str | None = None
    max_age_seconds: int = 300  # 5 minutes
    keys: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> SigningConfig:
        """Load configuration from environment variables.

        Returns:
            SigningConfig instance
        """
        config = cls(
            enabled=os.getenv("MLSDM_SIGNING_ENABLED", "false").lower() == "true",
            secret_key=os.getenv("MLSDM_SIGNING_KEY"),
            max_age_seconds=int(os.getenv("MLSDM_SIGNING_MAX_AGE", "300")),
        )

        # Load keys from file if specified
        keys_path = os.getenv("MLSDM_SIGNING_KEYS_PATH")
        if keys_path and os.path.exists(keys_path):
            try:
                with open(keys_path) as f:
                    config.keys = json.load(f)
                logger.info("Loaded %d signing keys from %s", len(config.keys), keys_path)
            except Exception as e:
                logger.error("Failed to load signing keys from %s: %s", keys_path, e)

        return config


@dataclass
class SignatureInfo:
    """Parsed signature information.

    Attributes:
        timestamp: Request timestamp (Unix epoch)
        signature: Base64-encoded HMAC signature
        key_id: Optional key identifier for multi-key setups
    """

    timestamp: int
    signature: str
    key_id: str | None = None


def compute_signature(
    method: str,
    path: str,
    timestamp: int,
    body: bytes,
    secret_key: str,
) -> str:
    """Compute HMAC-SHA256 signature for request.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        timestamp: Unix timestamp
        body: Request body bytes
        secret_key: HMAC secret key

    Returns:
        Base64-encoded signature
    """
    # Compute body hash
    body_hash = hashlib.sha256(body).hexdigest()

    # Create canonical request
    canonical = f"{method.upper()}\n{path}\n{timestamp}\n{body_hash}"

    # Compute HMAC
    signature = hmac.new(
        secret_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(signature).decode("ascii")


def generate_signature(
    method: str,
    path: str,
    body: bytes,
    secret_key: str,
    key_id: str | None = None,
) -> str:
    """Generate signature header value for request.

    Args:
        method: HTTP method
        path: Request path
        body: Request body
        secret_key: HMAC secret key
        key_id: Optional key identifier

    Returns:
        Header value for X-MLSDM-Signature

    Example:
        >>> sig = generate_signature(
        ...     method="POST",
        ...     path="/generate",
        ...     body=b'{"prompt":"Hello"}',
        ...     secret_key="my-secret-key",
        ... )
        >>> # Result: "timestamp=1699123456,signature=abc123..."
    """
    timestamp = int(time.time())
    signature = compute_signature(method, path, timestamp, body, secret_key)

    header_value = f"timestamp={timestamp},signature={signature}"
    if key_id:
        header_value = f"key_id={key_id},{header_value}"

    return header_value


def parse_signature_header(header_value: str) -> SignatureInfo | None:
    """Parse X-MLSDM-Signature header.

    Args:
        header_value: Header value string

    Returns:
        SignatureInfo or None if invalid

    Expected format:
        timestamp=1699123456,signature=abc123...
        key_id=key-name,timestamp=1699123456,signature=abc123...
    """
    try:
        parts = {}
        for part in header_value.split(","):
            key, value = part.strip().split("=", 1)
            parts[key] = value

        if "timestamp" not in parts or "signature" not in parts:
            return None

        return SignatureInfo(
            timestamp=int(parts["timestamp"]),
            signature=parts["signature"],
            key_id=parts.get("key_id"),
        )
    except Exception as e:
        logger.debug("Failed to parse signature header: %s", e)
        return None


def verify_signature(
    method: str,
    path: str,
    body: bytes,
    signature_info: SignatureInfo,
    secret_key: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify request signature.

    Args:
        method: HTTP method
        path: Request path
        body: Request body
        signature_info: Parsed signature information
        secret_key: HMAC secret key
        max_age_seconds: Maximum request age in seconds

    Returns:
        True if signature is valid, False otherwise
    """
    # Check timestamp (replay prevention)
    current_time = int(time.time())

    # Reject requests from the future (with small clock skew allowance)
    clock_skew_allowance = 30  # 30 seconds for clock drift
    if signature_info.timestamp > current_time + clock_skew_allowance:
        logger.warning(
            "Signature timestamp in future: ts=%d, current=%d",
            signature_info.timestamp,
            current_time,
        )
        return False

    # Reject requests that are too old
    age = current_time - signature_info.timestamp
    if age > max_age_seconds:
        logger.warning("Signature expired: age=%d seconds", age)
        return False

    # Compute expected signature
    expected = compute_signature(
        method,
        path,
        signature_info.timestamp,
        body,
        secret_key,
    )

    # Constant-time comparison
    return hmac.compare_digest(expected, signature_info.signature)


class SigningMiddleware(BaseHTTPMiddleware):
    """Middleware for request signature verification.

    Verifies HMAC signatures on incoming requests to ensure
    integrity and authenticity.

    Example:
        >>> app.add_middleware(
        ...     SigningMiddleware,
        ...     skip_paths=["/health", "/docs", "/redoc", "/openapi.json"],
        ... )
    """

    def __init__(
        self,
        app: Any,
        config: SigningConfig | None = None,
        skip_paths: list[str] | None = None,
        require_signature_paths: list[str] | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            config: Signing configuration (defaults to from_env())
            skip_paths: Paths to skip signature verification
            require_signature_paths: Paths that require signatures (if None, all paths)
        """
        super().__init__(app)
        self.config = config or SigningConfig.from_env()
        self.skip_paths = skip_paths or list(DEFAULT_PUBLIC_PATHS)
        self.require_signature_paths = require_signature_paths

    def _get_secret_key(self, key_id: str | None) -> str | None:
        """Get secret key for signature verification.

        Args:
            key_id: Optional key identifier

        Returns:
            Secret key or None if not found
        """
        # If key_id specified, look up in keys dict
        if key_id and self.config.keys:
            return self.config.keys.get(key_id)

        # Fall back to single key
        return self.config.secret_key

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        """Process request through signature verification.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        path = request.url.path

        # Skip certain paths
        if is_path_skipped(path, self.skip_paths):
            return await call_next(request)

        # Skip if signing not enabled
        if not self.config.enabled:
            return await call_next(request)

        # Check if this path requires signature
        if self.require_signature_paths:
            if not is_path_match(path, self.require_signature_paths):
                return await call_next(request)

        # Get signature header
        signature_header = request.headers.get("X-MLSDM-Signature")
        if not signature_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing request signature",
            )

        # Parse signature
        signature_info = parse_signature_header(signature_header)
        if signature_info is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature format",
            )

        # Get secret key
        secret_key = self._get_secret_key(signature_info.key_id)
        if not secret_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid key ID" if signature_info.key_id else "Signing not configured",
            )

        # Read body for verification
        body = await request.body()

        # Verify signature
        is_valid = verify_signature(
            method=request.method,
            path=path,
            body=body,
            signature_info=signature_info,
            secret_key=secret_key,
            max_age_seconds=self.config.max_age_seconds,
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature",
            )

        logger.debug("Signature verified for %s %s", request.method, path)

        return await call_next(request)


# Client-side helper class
class RequestSigner:
    """Client-side request signer.

    Provides convenient methods for signing outgoing requests.

    Example:
        >>> import httpx
        >>>
        >>> signer = RequestSigner(secret_key="my-secret")
        >>>
        >>> body = b'{"prompt": "Hello"}'
        >>> headers = signer.sign_request(
        ...     method="POST",
        ...     path="/generate",
        ...     body=body,
        ... )
        >>>
        >>> response = httpx.post(
        ...     "https://api.example.com/generate",
        ...     content=body,
        ...     headers=headers,
        ... )
    """

    def __init__(self, secret_key: str, key_id: str | None = None) -> None:
        """Initialize signer.

        Args:
            secret_key: HMAC secret key
            key_id: Optional key identifier
        """
        self.secret_key = secret_key
        self.key_id = key_id

    def sign_request(
        self,
        method: str,
        path: str,
        body: bytes | str = b"",
    ) -> dict[str, str]:
        """Generate signature headers for request.

        Args:
            method: HTTP method
            path: Request path
            body: Request body (bytes or string)

        Returns:
            Dictionary of headers to include
        """
        if isinstance(body, str):
            body = body.encode("utf-8")

        signature = generate_signature(
            method=method,
            path=path,
            body=body,
            secret_key=self.secret_key,
            key_id=self.key_id,
        )

        headers = {"X-MLSDM-Signature": signature}
        if self.key_id:
            headers["X-MLSDM-Key-ID"] = self.key_id

        return headers
