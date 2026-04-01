#!/usr/bin/env python3
"""
Development Mode Entrypoint for MLSDM.

Starts the MLSDM HTTP API server in development mode with:
- Hot reload enabled
- Debug logging
- Rate limiting disabled
- Local stub backend

Usage:
    # Direct execution
    python -m mlsdm.entrypoints.dev

    # With custom settings
    HOST=127.0.0.1 PORT=8080 python -m mlsdm.entrypoints.dev

    # Using Makefile
    make run-dev

Environment Variables:
    HOST: Server host (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    LLM_BACKEND: LLM backend to use (default: local_stub)
    CONFIG_PATH: Config file path (default: config/default_config.yaml)
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Run the development server.

    DEPRECATED: Use `mlsdm serve` (CLI) instead.
    This entrypoint is maintained for backward compatibility.
    """
    import warnings

    # Emit deprecation warning
    warnings.warn(
        "Direct execution of 'python -m mlsdm.entrypoints.dev' is deprecated. "
        "Use 'mlsdm serve' or 'python -m mlsdm.cli serve' instead. "
        "This entrypoint will be maintained for backward compatibility.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Apply environment compatibility layer
    from mlsdm.config.env_compat import apply_env_compat

    apply_env_compat()

    # Set runtime mode
    os.environ["MLSDM_RUNTIME_MODE"] = "dev"

    # Import and apply configuration
    from mlsdm.config.runtime import (
        RuntimeMode,
        apply_runtime_config,
        get_runtime_config,
        print_runtime_config,
    )

    config = get_runtime_config(RuntimeMode.DEV)
    apply_runtime_config(config)

    # Print configuration
    print_runtime_config(config)

    # Check health before starting
    from mlsdm.entrypoints.health import health_check

    health = health_check()
    if health["status"] == "unhealthy":
        print("\n❌ Health check failed:")
        for check_name, check_result in health["checks"].items():
            if not check_result["healthy"]:
                print(f"   - {check_name}: {check_result['details']}")
        return 1

    print(f"\n✓ Health check: {health['status']}")
    print()

    # Show API endpoints
    print("API Endpoints:")
    print(f"  - POST http://{config.server.host}:{config.server.port}/generate")
    print(f"  - POST http://{config.server.host}:{config.server.port}/infer")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health/ready")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health/metrics")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/status")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/docs (Swagger UI)")
    print()

    from mlsdm.entrypoints.serve import serve

    print(f"🚀 Starting development server on {config.server.host}:{config.server.port}")
    print("   Press Ctrl+C to stop")
    print()

    return serve(
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level,
    )


if __name__ == "__main__":
    sys.exit(main())
