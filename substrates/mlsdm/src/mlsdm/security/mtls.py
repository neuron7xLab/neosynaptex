"""Mutual TLS (mTLS) Support for MLSDM API (SEC-006).

This module provides mutual TLS (client certificate) authentication,
enabling zero-trust network security by verifying client identities
at the transport layer.

Features:
- Client certificate validation
- Certificate subject (CN) extraction for identity
- Integration with RBAC for certificate-based access control
- Support for certificate chains and CA bundles
- Configurable via environment variables

Configuration (Environment Variables):
    MLSDM_MTLS_ENABLED: "true" to enable mTLS (default: "false")
    MLSDM_MTLS_CA_CERT: Path to CA certificate bundle (PEM format)
    MLSDM_MTLS_REQUIRE_CLIENT_CERT: "true" to require client certs (default: "true")
    MLSDM_MTLS_VERIFY_DEPTH: Certificate chain verification depth (default: "3")

Server Configuration (uvicorn):
    uvicorn mlsdm.api.app:app \\
      --host 0.0.0.0 \\
      --port 8443 \\
      --ssl-keyfile /path/to/server.key \\
      --ssl-certfile /path/to/server.crt \\
      --ssl-ca-certs /path/to/ca-bundle.crt \\
      --ssl-cert-reqs 2  # CERT_REQUIRED

Example:
    >>> from mlsdm.security.mtls import MTLSMiddleware, get_client_cert_cn
    >>>
    >>> # Add middleware to verify client certificates
    >>> app.add_middleware(MTLSMiddleware, ca_cert_path="/path/to/ca.crt")
    >>>
    >>> # Get client identity in endpoint
    >>> @app.get("/whoami")
    >>> async def whoami(request: Request):
    ...     cn = get_client_cert_cn(request)
    ...     return {"identity": cn}

Note:
    mTLS is configured at the ASGI server level (uvicorn, gunicorn).
    This module provides helpers for extracting client identity from
    the validated certificate.
"""

from __future__ import annotations

import logging
import os
import ssl
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_skipped

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class MTLSConfig:
    """mTLS Configuration.

    Attributes:
        enabled: Whether mTLS is enabled
        ca_cert_path: Path to CA certificate bundle
        require_client_cert: Whether to require client certificates
        verify_depth: Certificate chain verification depth
    """

    enabled: bool = False
    ca_cert_path: str | None = None
    require_client_cert: bool = True
    verify_depth: int = 3

    @classmethod
    def from_env(cls) -> MTLSConfig:
        """Load configuration from environment variables.

        Returns:
            MTLSConfig instance
        """
        require_cert = os.getenv("MLSDM_MTLS_REQUIRE_CLIENT_CERT", "true").lower() == "true"
        return cls(
            enabled=os.getenv("MLSDM_MTLS_ENABLED", "false").lower() == "true",
            ca_cert_path=os.getenv("MLSDM_MTLS_CA_CERT"),
            require_client_cert=require_cert,
            verify_depth=int(os.getenv("MLSDM_MTLS_VERIFY_DEPTH", "3")),
        )


@dataclass
class ClientCertInfo:
    """Client certificate information.

    Attributes:
        common_name: Certificate Common Name (CN)
        organization: Certificate Organization (O)
        organizational_unit: Certificate Organizational Unit (OU)
        serial_number: Certificate serial number
        subject: Full subject string
        issuer: Certificate issuer
        not_before: Certificate validity start
        not_after: Certificate validity end
    """

    common_name: str | None = None
    organization: str | None = None
    organizational_unit: str | None = None
    serial_number: str | None = None
    subject: str | None = None
    issuer: str | None = None
    not_before: str | None = None
    not_after: str | None = None


def get_client_cert_from_request(request: Request) -> dict[str, Any] | None:
    """Extract client certificate from request.

    Args:
        request: FastAPI request

    Returns:
        Certificate dictionary or None if not present
    """
    # Get transport from ASGI scope
    transport = request.scope.get("transport")
    if transport is None:
        return None

    # Get SSL object
    ssl_object = getattr(transport, "get_extra_info", lambda x: None)("ssl_object")
    if ssl_object is None:
        return None

    # Get peer certificate
    try:
        # ssl.SSLSocket.getpeercert() returns dict[str, Any] when binary_form=False
        peer_cert: dict[str, Any] | None = ssl_object.getpeercert()
        return peer_cert
    except Exception as e:
        logger.debug("Failed to get peer certificate: %s", e)
        return None


def parse_certificate_subject(cert: dict[str, Any]) -> ClientCertInfo:
    """Parse certificate subject into structured format.

    Args:
        cert: Certificate dictionary from SSL

    Returns:
        ClientCertInfo with parsed fields
    """
    info = ClientCertInfo()

    # Parse subject
    subject = cert.get("subject", ())
    subject_dict: dict[str, str] = {}
    for rdns in subject:
        for attr_type, attr_value in rdns:
            subject_dict[attr_type] = attr_value

    info.common_name = subject_dict.get("commonName")
    info.organization = subject_dict.get("organizationName")
    info.organizational_unit = subject_dict.get("organizationalUnitName")

    # Parse issuer
    issuer = cert.get("issuer", ())
    issuer_parts = []
    for rdns in issuer:
        for attr_type, attr_value in rdns:
            issuer_parts.append(f"{attr_type}={attr_value}")
    info.issuer = ", ".join(issuer_parts) if issuer_parts else None

    # Other fields
    info.serial_number = str(cert.get("serialNumber", ""))
    info.not_before = cert.get("notBefore")
    info.not_after = cert.get("notAfter")

    # Full subject string
    subject_parts = []
    for rdns in subject:
        for attr_type, attr_value in rdns:
            subject_parts.append(f"{attr_type}={attr_value}")
    info.subject = ", ".join(subject_parts) if subject_parts else None

    return info


def get_client_cert_cn(request: Request) -> str | None:
    """Get client certificate Common Name (CN).

    Args:
        request: FastAPI request

    Returns:
        Common Name or None if not available
    """
    cert = get_client_cert_from_request(request)
    if cert is None:
        return None

    info = parse_certificate_subject(cert)
    return info.common_name


def get_client_cert_info(request: Request) -> ClientCertInfo | None:
    """Get full client certificate information.

    Args:
        request: FastAPI request

    Returns:
        ClientCertInfo or None if not available
    """
    cert = get_client_cert_from_request(request)
    if cert is None:
        return None

    return parse_certificate_subject(cert)


class MTLSMiddleware(BaseHTTPMiddleware):
    """Middleware for mTLS client certificate validation.

    Extracts client certificate information and stores in request.state.
    Optionally requires client certificates for all requests.

    Example:
        >>> app.add_middleware(
        ...     MTLSMiddleware,
        ...     require_cert=True,
        ...     skip_paths=["/health", "/docs", "/redoc", "/openapi.json"]
        ... )
    """

    def __init__(
        self,
        app: Any,
        require_cert: bool = True,
        skip_paths: list[str] | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            require_cert: Whether to require client certificates
            skip_paths: Paths to skip certificate requirement
        """
        super().__init__(app)
        self.require_cert = require_cert
        self.skip_paths = skip_paths or list(DEFAULT_PUBLIC_PATHS)
        self.config = MTLSConfig.from_env()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        """Process request through mTLS validation.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        path = request.url.path

        # Skip certain paths
        if is_path_skipped(path, self.skip_paths):
            request.state.client_cert = None
            return await call_next(request)

        # Skip if mTLS not enabled
        if not self.config.enabled:
            request.state.client_cert = None
            return await call_next(request)

        # Get client certificate
        cert_info = get_client_cert_info(request)
        request.state.client_cert = cert_info

        # Require certificate if configured
        if self.require_cert and cert_info is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client certificate required",
            )

        # Log client identity
        if cert_info and cert_info.common_name:
            logger.info("mTLS client: %s", cert_info.common_name)

        return await call_next(request)


def create_ssl_context(config: MTLSConfig) -> ssl.SSLContext | None:
    """Create SSL context for server with mTLS.

    This is a helper for configuring uvicorn/hypercorn with mTLS.
    Typically, you configure SSL at the server level, not in Python.

    Args:
        config: mTLS configuration

    Returns:
        Configured SSL context or None if mTLS disabled
    """
    if not config.enabled or not config.ca_cert_path:
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_verify_locations(config.ca_cert_path)

    if config.require_client_cert:
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_OPTIONAL

    return context
