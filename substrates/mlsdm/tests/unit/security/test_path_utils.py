"""Tests for security path matching utilities and defaults."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mlsdm.security.mtls import MTLSMiddleware
from mlsdm.security.oidc import OIDCAuthenticator, OIDCAuthMiddleware, OIDCConfig
from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_match, is_path_skipped
from mlsdm.security.rbac import RBACMiddleware, RoleValidator
from mlsdm.security.signing import SigningMiddleware


class TestPathSkipMatching:
    """Validate boundary-safe skip matching semantics."""

    def test_boundary_safe_matches(self) -> None:
        """Test positive and negative boundary matches."""
        skip_paths = DEFAULT_PUBLIC_PATHS

        for path in ("/docs", "/docs/", "/docs/x"):
            assert is_path_skipped(path, skip_paths) is True
        for path in ("/redoc", "/redoc/x"):
            assert is_path_skipped(path, skip_paths) is True
        for path in ("/health", "/health/live"):
            assert is_path_skipped(path, skip_paths) is True
        assert is_path_skipped("/openapi.json", skip_paths) is True

        for path in (
            "/docs2",
            "/docs-private",
            "/healthcheck",
            "/healthz",
            "/redoc2",
            "/openapi.json.bak",
        ):
            assert is_path_skipped(path, skip_paths) is False

    def test_query_string_and_encoding_paths(self) -> None:
        """Test that unexpected path forms are not misclassified."""
        skip_paths = DEFAULT_PUBLIC_PATHS
        assert is_path_skipped("/docs?x=1", skip_paths) is False
        assert is_path_skipped("/docs%2Fsecret", skip_paths) is False

    def test_root_path_only_matches_root(self) -> None:
        """Test explicit root skip only matches root."""
        assert is_path_skipped("/", ["/"]) is True
        assert is_path_skipped("/health", ["/"]) is False

    def test_boundary_safe_match_paths(self) -> None:
        """Test boundary-safe matching for required paths."""
        assert is_path_match("/admin", ["/admin/"]) is True
        assert is_path_match("/admin/settings", ["/admin/"]) is True
        assert is_path_match("/adminx", ["/admin/"]) is False

    @pytest.mark.parametrize(
        ("path", "skip_paths", "expected"),
        [
            ("/docs", ["/docs/"], True),
            ("/docs/", ["/docs"], True),
            ("/docs/x", ["/docs/"], True),
            ("/docs2", ["/docs/"], False),
            ("/", ["/"], True),
            ("/health", ["/"], False),
            ("/docs", [], False),
            ("/docs", [""], False),
        ],
    )
    def test_skip_path_normalization_matrix(
        self,
        path: str,
        skip_paths: list[str],
        expected: bool,
    ) -> None:
        """Test skip path normalization and edge-case handling."""
        assert is_path_skipped(path, skip_paths) is expected


class TestMiddlewareDefaultParity:
    """Assert default public skip paths are consistent across middleware."""

    def test_default_skip_paths_match_canonical(self) -> None:
        """Test all middleware defaults include the canonical public paths."""
        mock_app = MagicMock()
        validator = RoleValidator()
        oidc_auth = OIDCAuthenticator(OIDCConfig(enabled=False))

        oidc_middleware = OIDCAuthMiddleware(mock_app, authenticator=oidc_auth)
        mtls_middleware = MTLSMiddleware(mock_app)
        signing_middleware = SigningMiddleware(mock_app)
        rbac_middleware = RBACMiddleware(mock_app, role_validator=validator)

        for path in DEFAULT_PUBLIC_PATHS:
            assert path in oidc_middleware.skip_paths
            assert path in mtls_middleware.skip_paths
            assert path in signing_middleware.skip_paths
            assert path in rbac_middleware.skip_paths
