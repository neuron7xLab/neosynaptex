#!/usr/bin/env python3
"""Export OpenAPI specification from FastAPI app.

This script generates a static OpenAPI JSON file from the FastAPI application,
which can be used for documentation, client generation, and API validation.

Usage:
    python scripts/export_openapi.py [--output OUTPUT_PATH]

Examples:
    # Export to default location (docs/openapi.json)
    python scripts/export_openapi.py

    # Export to custom location
    python scripts/export_openapi.py --output api-spec.json

    # Export with validation
    python scripts/export_openapi.py --validate
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_openapi_spec() -> dict[str, Any]:
    """Get OpenAPI specification from FastAPI app.

    Returns:
        OpenAPI specification dictionary
    """
    # Import app lazily to avoid startup side effects
    os.environ.setdefault("CONFIG_PATH", str(project_root / "config" / "default_config.yaml"))
    os.environ.setdefault("DISABLE_RATE_LIMIT", "1")

    from mlsdm.api.app import app

    return app.openapi()


def enhance_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Enhance OpenAPI spec with additional metadata and examples.

    Args:
        spec: Raw OpenAPI specification

    Returns:
        Enhanced OpenAPI specification
    """
    # Add additional info
    spec["info"]["x-logo"] = {"url": "https://github.com/neuron7xLab/mlsdm/raw/main/docs/logo.png"}

    # Add tags descriptions
    spec["tags"] = [
        {
            "name": "Generation",
            "description": "Text generation with cognitive governance",
        },
        {
            "name": "Events",
            "description": "Event processing and state management",
        },
        {
            "name": "Health",
            "description": "Health check endpoints",
        },
    ]

    # Add servers
    spec["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.mlsdm.example.com",
            "description": "Production server",
        },
    ]

    # Add security schemes if not present
    if "components" not in spec:
        spec["components"] = {}

    if "securitySchemes" not in spec["components"]:
        spec["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": "API key authentication. Include your API key as a Bearer token.",
            },
            "apiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key authentication via header.",
            },
        }

    # Add request examples to paths
    if "paths" in spec:
        # Add example to /generate endpoint
        if "/generate" in spec["paths"]:
            generate_path = spec["paths"]["/generate"]
            if "post" in generate_path and "requestBody" in generate_path["post"]:
                content = generate_path["post"]["requestBody"].get("content", {})
                if "application/json" in content:
                    content["application/json"]["examples"] = {
                        "simple": {
                            "summary": "Simple prompt",
                            "value": {
                                "prompt": "Explain quantum computing in simple terms",
                                "max_tokens": 256,
                                "moral_value": 0.8,
                            },
                        },
                        "creative": {
                            "summary": "Creative writing",
                            "value": {
                                "prompt": "Write a short poem about artificial intelligence",
                                "max_tokens": 512,
                                "moral_value": 0.9,
                            },
                        },
                    }

    return spec


def validate_spec(spec: dict[str, Any]) -> bool:
    """Validate OpenAPI specification.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to import openapi-spec-validator
        from openapi_spec_validator import validate_spec as validate_openapi

        validate_openapi(spec)
        logger.info("✅ OpenAPI specification is valid")
        return True
    except ImportError:
        logger.warning("⚠️ openapi-spec-validator not installed, skipping validation")
        logger.warning("   Install with: pip install openapi-spec-validator")
        return True
    except Exception as e:
        logger.error(f"❌ OpenAPI specification validation failed: {e}")
        return False


def export_openapi(
    output_path: str | Path,
    validate: bool = False,
    enhance: bool = True,
) -> bool:
    """Export OpenAPI specification to file.

    Args:
        output_path: Path to write the specification
        validate: Whether to validate the specification
        enhance: Whether to enhance with additional metadata

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("📝 Generating OpenAPI specification...")
        spec = get_openapi_spec()

        if enhance:
            logger.info("✨ Enhancing specification with metadata and examples...")
            spec = enhance_spec(spec)

        if validate:
            if not validate_spec(spec):
                return False

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ OpenAPI specification exported to: {output_path}")
        logger.info(f"   Version: {spec.get('info', {}).get('version', 'unknown')}")
        logger.info(f"   Endpoints: {len(spec.get('paths', {}))}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to export OpenAPI specification: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Export OpenAPI specification from FastAPI app",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="docs/openapi.json",
        help="Output path for OpenAPI specification (default: docs/openapi.json)",
    )
    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="Validate the generated specification",
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Don't enhance specification with additional metadata",
    )

    args = parser.parse_args()

    success = export_openapi(
        output_path=args.output,
        validate=args.validate,
        enhance=not args.no_enhance,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
