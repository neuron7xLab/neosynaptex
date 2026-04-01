#!/usr/bin/env python3
"""
Agent/API Mode Entrypoint for MLSDM.

Starts the MLSDM in agent/API mode suitable for integration with:
- LLM platforms (OpenAI-compatible APIs)
- External clients
- Multi-agent systems
- LangChain/LlamaIndex integrations

This mode provides:
- JSON structured logging
- Secure mode enabled
- Metrics enabled
- FSLGS governance enabled
- Designed for API-first usage

Usage:
    # Direct execution
    python -m mlsdm.entrypoints.agent

    # With custom settings
    API_KEY=my-secret-key python -m mlsdm.entrypoints.agent

    # Using Makefile
    make run-agent

Environment Variables:
    HOST: Server host (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    LLM_BACKEND: LLM backend to use (default: local_stub)
    OPENAI_API_KEY: OpenAI API key (required if LLM_BACKEND=openai)
    API_KEY: API authentication key for incoming requests
    CONFIG_PATH: Config file path (default: config/production.yaml)

API Endpoints (Agent Mode):
    POST /generate - Generate response with full governance
    POST /infer - Extended inference with governance options
    GET /status - Extended service status
    GET /health/* - Health check endpoints
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Run the agent/API server.

    DEPRECATED: Use `mlsdm serve` (CLI) instead.
    This entrypoint is maintained for backward compatibility.
    """
    import warnings

    # Emit deprecation warning
    warnings.warn(
        "Direct execution of 'python -m mlsdm.entrypoints.agent' is deprecated. "
        "Use 'mlsdm serve' or 'python -m mlsdm.cli serve' instead. "
        "This entrypoint will be maintained for backward compatibility.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Apply environment compatibility layer
    from mlsdm.config.env_compat import apply_env_compat

    apply_env_compat()

    # Set runtime mode
    os.environ["MLSDM_RUNTIME_MODE"] = "agent-api"

    # Import and apply configuration
    from mlsdm.config.runtime import (
        RuntimeMode,
        apply_runtime_config,
        get_runtime_config,
        print_runtime_config,
    )

    config = get_runtime_config(RuntimeMode.AGENT_API)
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

    # Show agent-specific information
    print("Agent/API Mode:")
    print("  - Designed for external LLM/client integration")
    print("  - Full moral governance enabled")
    print("  - FSLGS safety checks enabled")
    print()

    # Show API endpoints
    print("API Endpoints:")
    print(f"  - POST http://{config.server.host}:{config.server.port}/generate")
    print("      Body: {'prompt': 'your prompt', 'moral_value': 0.8}")
    print(f"  - POST http://{config.server.host}:{config.server.port}/infer")
    print("      Body: {'prompt': 'your prompt', 'secure_mode': true}")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/status")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/health")
    print(f"  - GET  http://{config.server.host}:{config.server.port}/docs")
    print()

    # Show authentication info
    if config.security.api_key:
        print("Authentication:")
        print("  - Bearer token authentication enabled")
        print("  - Set Authorization header: Bearer <API_KEY>")
        print()
    else:
        print("⚠️  WARNING: No API_KEY set. API is unauthenticated.")
        print("   Set API_KEY environment variable for production.")
        print()

    from mlsdm.entrypoints.serve import serve

    print(f"🤖 Starting agent/API server on {config.server.host}:{config.server.port}")
    print("   Press Ctrl+C to stop")
    print()

    return serve(
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        log_level=config.server.log_level,
    )


if __name__ == "__main__":
    sys.exit(main())
