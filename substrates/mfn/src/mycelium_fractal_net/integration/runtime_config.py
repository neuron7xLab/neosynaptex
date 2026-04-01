"""Shared runtime configuration assembly for API and CLI."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from mycelium_fractal_net.config_profiles import (
    ConfigProfile,
    ConfigValidationError,
    load_config_profile,
)

if TYPE_CHECKING:
    from mycelium_fractal_net.integration.schemas import ValidateRequest

DEFAULT_PROFILE_ENV = "MFN_CONFIG_PROFILE"
DEFAULT_PROFILE_NAME = "dev"


def _load_profile(profile_name: str | None) -> ConfigProfile | None:
    """Load a config profile, returning None when the profile is missing."""
    if not profile_name:
        return None
    try:
        return load_config_profile(profile_name)
    except (FileNotFoundError, ConfigValidationError):
        return None


def assemble_validation_config(
    request: ValidateRequest | Mapping[str, Any] | None = None,
    profile_name: str | None = None,
):
    """
    Build ValidationConfig using a deterministic precedence:
    defaults → profile → env overrides (applied via load_config_profile) → request overrides.
    """
    from mycelium_fractal_net.model import ValidationConfig

    base_config = ValidationConfig()
    # ValidationConfig is a simple container; copying vars() is sufficient for defaults.
    base = vars(base_config).copy()
    profile = _load_profile(profile_name or os.getenv(DEFAULT_PROFILE_ENV, DEFAULT_PROFILE_NAME))
    if profile:
        base.update(profile.to_dict().get("validation", {}))

    if request:
        if isinstance(request, BaseModel):
            request_data = request.model_dump()
        elif isinstance(request, Mapping):
            request_data = dict(request)
        else:
            raise TypeError(f"Unsupported request type: {type(request)!r}")
        base.update(request_data)

    return ValidationConfig(**base)


__all__ = ["assemble_validation_config"]
