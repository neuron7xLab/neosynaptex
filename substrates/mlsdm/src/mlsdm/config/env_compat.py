"""
Environment Variable Compatibility Layer.

Provides backward compatibility for legacy environment variables.

Note: This module is currently a placeholder for future compatibility needs.
Most environment variables (CONFIG_PATH, LLM_BACKEND, DISABLE_RATE_LIMIT) are
already part of the stable API and handled directly by RuntimeConfig in runtime.py.

DISABLE_RATE_LIMIT is handled natively by RuntimeConfig and does not need mapping
to MLSDM_RATE_LIMIT_ENABLED because:
1. MLSDM_* prefix is reserved for SystemConfig env overrides (cognitive engine config)
2. DISABLE_RATE_LIMIT is part of RuntimeConfig (deployment/server config)
3. RuntimeConfig handles the inversion logic directly (see runtime.py line 305-311)

This separation maintains clear boundaries between:
- SystemConfig: Cognitive engine configuration (embeddings, memory, etc.)
- RuntimeConfig: Runtime/deployment configuration (server, security, observability)
"""

from __future__ import annotations

import os


def apply_env_compat() -> None:
    """Apply environment variable compatibility mapping.

    Currently a no-op as all environment variables are handled directly
    by their respective configuration systems:
    - CONFIG_PATH, LLM_BACKEND: Used directly by RuntimeConfig
    - DISABLE_RATE_LIMIT: Handled by RuntimeConfig (inverted to rate_limit_enabled)
    - MLSDM_*: Handled by SystemConfig._apply_env_overrides()

    This function is kept for potential future compatibility needs and to
    maintain the API contract established in entrypoints and CLI.
    """
    # No-op: All environment variables are handled directly by runtime.py
    # and config_loader.py without needing intermediate mapping.
    pass


def warn_if_legacy_vars_used() -> list[str]:
    """Check for legacy environment variables and warn if found.

    Returns:
        List of legacy variable names that are currently set.
        Currently returns empty list as all variables are part of stable API.

    Note:
        DISABLE_RATE_LIMIT, CONFIG_PATH, and LLM_BACKEND are all part of the
        stable, documented API and are not considered legacy. No deprecation
        warnings are needed.
    """
    # No legacy variables to warn about - all environment variables
    # (DISABLE_RATE_LIMIT, CONFIG_PATH, LLM_BACKEND) are part of stable API
    return []


def get_env_compat_info() -> dict[str, dict[str, str | None]]:
    """Get information about environment variables.

    Returns:
        Dictionary mapping variable names to their status and usage.

    Note:
        All listed variables are part of the stable API, not legacy.
    """
    return {
        "DISABLE_RATE_LIMIT": {
            "status": "stable",
            "current_value": os.environ.get("DISABLE_RATE_LIMIT"),
            "note": "Part of RuntimeConfig. Set to '1' to disable rate limiting.",
        },
        "CONFIG_PATH": {
            "status": "stable",
            "current_value": os.environ.get("CONFIG_PATH"),
            "note": "Part of RuntimeConfig. Specifies cognitive engine config file path.",
        },
        "LLM_BACKEND": {
            "status": "stable",
            "current_value": os.environ.get("LLM_BACKEND"),
            "note": "Part of RuntimeConfig. Specifies LLM backend (e.g., 'local_stub', 'openai').",
        },
    }
