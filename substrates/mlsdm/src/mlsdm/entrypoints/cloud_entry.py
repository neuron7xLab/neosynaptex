#!/usr/bin/env python3
"""
Cloud Service Mode Entrypoint for MLSDM.

Starts the MLSDM HTTP API server in cloud production mode with:
- Multiple workers (via Gunicorn recommended, but uvicorn used here)
- JSON structured logging
- Secure mode enabled
- Full observability (metrics + tracing)

Usage:
    # Direct execution
    python -m mlsdm.entrypoints.cloud

    # With custom settings
    LLM_BACKEND=openai OPENAI_API_KEY=sk-... python -m mlsdm.entrypoints.cloud

    # Using Docker
    docker run -e LLM_BACKEND=openai -e OPENAI_API_KEY=sk-... mlsdm:latest

    # Using Makefile
    make run-cloud-local

Environment Variables:
    HOST: Server host (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    MLSDM_WORKERS: Number of workers (default: 4)
    LLM_BACKEND: LLM backend to use (default: local_stub)
    OPENAI_API_KEY: OpenAI API key (required if LLM_BACKEND=openai)
    CONFIG_PATH: Config file path (default: config/production.yaml)
    API_KEY: API authentication key
    OTEL_EXPORTER_TYPE: OpenTelemetry exporter (default: otlp)

Docker/Kubernetes Notes:
    - Use health endpoints: /health/live and /health/ready
    - Metrics available at: /health/metrics
    - Recommended resource limits: 1-2 CPU, 1-4 GB RAM
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Run the cloud production server.

    DEPRECATED: Use `mlsdm serve` (CLI) instead.
    This entrypoint is maintained for backward compatibility.
    """
    import warnings

    # Emit deprecation warning
    warnings.warn(
        "Direct execution of 'python -m mlsdm.entrypoints.cloud' is deprecated. "
        "Use 'mlsdm serve' or 'python -m mlsdm.cli serve' instead. "
        "This entrypoint will be maintained for backward compatibility.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Apply environment compatibility layer
    from mlsdm.config.env_compat import apply_env_compat

    apply_env_compat()

    # Set runtime mode
    os.environ["MLSDM_RUNTIME_MODE"] = "cloud-prod"

    # Import and apply configuration
    from mlsdm.config.runtime import (
        RuntimeMode,
        apply_runtime_config,
        get_runtime_config,
        print_runtime_config,
    )

    config = get_runtime_config(RuntimeMode.CLOUD_PROD)
    apply_runtime_config(config)

    # Print configuration (will be JSON logged in production)
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
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health/live")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health/ready")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health/metrics")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/status")
    print()

    # Warn if using local stub in production
    if config.engine.llm_backend == "local_stub":
        print("⚠️  WARNING: Using local_stub backend in cloud mode.")
        print("   Set LLM_BACKEND=openai for production.")
        print()

    from mlsdm.entrypoints.serve import serve

    print(f"🚀 Starting cloud production server on {config.server.host}:{config.server.port}")
    print(f"   Workers: {config.server.workers}")
    print(f"   Secure Mode: {config.security.secure_mode}")
    print(f"   Tracing: {config.observability.tracing_enabled}")
    print()

    return serve(
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        log_level=config.server.log_level,
        timeout_keep_alive=config.server.timeout_keep_alive,
    )


if __name__ == "__main__":
    sys.exit(main())
