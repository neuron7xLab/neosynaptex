"""Tests for security skip path invariants across middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import Response

import mlsdm.security.mtls as mtls_module
import mlsdm.security.signing as signing_module
from mlsdm.security.mtls import MTLSMiddleware
from mlsdm.security.oidc import OIDCAuthenticator, OIDCAuthMiddleware
from mlsdm.security.rbac import RBACMiddleware, RoleValidator
from mlsdm.security.signing import SigningConfig, SigningMiddleware


def _make_request(path: str, headers: dict[str, str] | None = None) -> Request:
    header_pairs = [
        (key.lower().encode(), value.encode())
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": header_pairs,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_oidc_skip_paths_respect_boundary() -> None:
    """Ensure prefix collisions do not bypass OIDC auth."""
    authenticator = MagicMock(spec=OIDCAuthenticator)
    authenticator.enabled = True
    authenticator.authenticate = AsyncMock(side_effect=Exception("auth failure"))
    middleware = OIDCAuthMiddleware(
        MagicMock(),
        authenticator=authenticator,
        skip_paths=["/docs"],
    )
    request = _make_request("/docs2")
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(request, call_next)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    call_next.assert_not_awaited()
    authenticator.authenticate.assert_awaited_once()


@pytest.mark.asyncio
async def test_oidc_skip_paths_bypass_authenticator() -> None:
    """Ensure skipped paths never invoke OIDC authentication."""
    authenticator = MagicMock(spec=OIDCAuthenticator)
    authenticator.enabled = True
    authenticator.authenticate = AsyncMock()
    middleware = OIDCAuthMiddleware(
        MagicMock(),
        authenticator=authenticator,
        skip_paths=["/docs"],
    )
    request = _make_request("/docs")
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_200_OK
    call_next.assert_awaited_once()
    authenticator.authenticate.assert_not_awaited()


@pytest.mark.asyncio
async def test_mtls_skip_paths_respect_boundary() -> None:
    """Ensure prefix collisions do not bypass mTLS."""
    middleware = MTLSMiddleware(MagicMock(), skip_paths=["/docs"])
    middleware.config.enabled = True
    request = _make_request("/docs2")
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(request, call_next)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_mtls_skip_paths_bypass_certificate_requirement() -> None:
    """Ensure skipped paths bypass mTLS requirement."""
    middleware = MTLSMiddleware(MagicMock(), skip_paths=["/docs"])
    middleware.config.enabled = True
    request = _make_request("/docs")
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_200_OK
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_signing_skip_paths_respect_boundary() -> None:
    """Ensure prefix collisions do not bypass signing."""
    config = SigningConfig(enabled=True, secret_key="secret")
    middleware = SigningMiddleware(
        MagicMock(),
        config=config,
        skip_paths=["/docs"],
    )
    request = _make_request("/docs2")
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(request, call_next)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_signing_skip_paths_bypass_verification() -> None:
    """Ensure skipped paths bypass signature verification."""
    config = SigningConfig(enabled=True, secret_key="secret")
    middleware = SigningMiddleware(
        MagicMock(),
        config=config,
        skip_paths=["/docs"],
    )
    request = _make_request("/docs")
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_200_OK
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_rbac_skip_paths_respect_boundary() -> None:
    """Ensure prefix collisions do not bypass RBAC validation."""
    validator = MagicMock(spec=RoleValidator)
    validator.validate_key.side_effect = RuntimeError("validator error")
    middleware = RBACMiddleware(MagicMock(), role_validator=validator, skip_paths=["/docs"])
    request = _make_request("/docs2", headers={"Authorization": "Bearer token"})
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(RuntimeError):
        await middleware.dispatch(request, call_next)

    call_next.assert_not_awaited()
    validator.validate_key.assert_called_once()


@pytest.mark.asyncio
async def test_rbac_skip_paths_bypass_validation() -> None:
    """Ensure skipped paths bypass RBAC validation."""
    validator = MagicMock(spec=RoleValidator)
    validator.validate_key.side_effect = RuntimeError("validator error")
    middleware = RBACMiddleware(MagicMock(), role_validator=validator, skip_paths=["/docs"])
    request = _make_request("/docs", headers={"Authorization": "Bearer token"})
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_200_OK
    call_next.assert_awaited_once()
    validator.validate_key.assert_not_called()


@pytest.mark.asyncio
async def test_oidc_fail_closed_on_auth_error() -> None:
    """Ensure OIDC errors fail closed on protected routes."""
    authenticator = MagicMock(spec=OIDCAuthenticator)
    authenticator.enabled = True
    authenticator.authenticate = AsyncMock(side_effect=Exception("boom"))
    middleware = OIDCAuthMiddleware(
        MagicMock(),
        authenticator=authenticator,
        skip_paths=[],
    )
    request = _make_request("/private")
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(request, call_next)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_mtls_fail_closed_on_cert_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure mTLS errors fail closed on protected routes."""
    middleware = MTLSMiddleware(MagicMock(), skip_paths=[])
    middleware.config.enabled = True
    request = _make_request("/private")
    call_next = AsyncMock(return_value=Response("ok"))

    def _raise_cert_error(_: Request) -> None:
        raise RuntimeError("cert parse error")

    monkeypatch.setattr(mtls_module, "get_client_cert_info", _raise_cert_error)

    with pytest.raises(RuntimeError):
        await middleware.dispatch(request, call_next)

    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_signing_fail_closed_on_verifier_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure signing errors fail closed on protected routes."""
    config = SigningConfig(enabled=True, secret_key="secret")
    middleware = SigningMiddleware(MagicMock(), config=config, skip_paths=[])
    request = _make_request(
        "/private",
        headers={"X-MLSDM-Signature": "timestamp=1,signature=abc"},
    )
    call_next = AsyncMock(return_value=Response("ok"))

    def _raise_signature_error(*_: object, **__: object) -> bool:
        raise RuntimeError("signature verification error")

    monkeypatch.setattr(signing_module, "verify_signature", _raise_signature_error)

    with pytest.raises(RuntimeError):
        await middleware.dispatch(request, call_next)

    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_rbac_fail_closed_on_validator_error() -> None:
    """Ensure RBAC errors fail closed on protected routes."""
    validator = MagicMock(spec=RoleValidator)
    validator.validate_key.side_effect = RuntimeError("validator error")
    middleware = RBACMiddleware(MagicMock(), role_validator=validator, skip_paths=[])
    request = _make_request("/private", headers={"Authorization": "Bearer token"})
    call_next = AsyncMock(return_value=Response("ok"))

    with pytest.raises(RuntimeError):
        await middleware.dispatch(request, call_next)

    call_next.assert_not_awaited()
    validator.validate_key.assert_called_once()
