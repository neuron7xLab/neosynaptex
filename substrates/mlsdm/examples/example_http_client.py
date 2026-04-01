#!/usr/bin/env python3
"""
HTTP Client Example for MLSDM.

This example demonstrates how to interact with the MLSDM HTTP API
using simple HTTP requests.

Usage:
    1. Start the server: mlsdm serve
    2. Run this script: python examples/example_http_client.py

Prerequisites:
    pip install requests
"""

import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)


BASE_URL = "http://localhost:8000"

# Define newline character for cross-platform compatibility
newline = "\n"


def check_server() -> bool:
    """Check if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def example_health_check():
    """Health check endpoints."""
    print("=" * 60)
    print("Health Check Endpoints")
    print("=" * 60)

    # Simple health
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print("\nGET /health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # Liveness probe
    response = requests.get(f"{BASE_URL}/health/live", timeout=5)
    print("\nGET /health/live")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # Readiness probe
    response = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    print("\nGET /health/ready")
    print(f"  Status: {response.status_code}")
    data = response.json()
    print(f"  Ready: {data.get('ready', False)}")


def example_generate():
    """Basic generate endpoint."""
    print("\n" + "=" * 60)
    print("Generate Endpoint")
    print("=" * 60)

    payload = {
        "prompt": "What is artificial intelligence?",
        "max_tokens": 256,
        "moral_value": 0.8,
    }

    print("\nPOST /generate")
    print(f"  Payload: {json.dumps(payload, indent=4)}")

    response = requests.post(
        f"{BASE_URL}/generate",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    print(f"\n  Status: {response.status_code}")
    data = response.json()
    print(f"  Accepted: {data.get('accepted', False)}")
    print(f"  Phase: {data.get('phase', 'unknown')}")
    print(f"  Response: {data.get('response', '')[:200]}...")


def example_infer():
    """Extended infer endpoint with governance options."""
    print("\n" + "=" * 60)
    print("Infer Endpoint (Extended)")
    print("=" * 60)

    payload = {
        "prompt": "Explain machine learning in simple terms",
        "moral_value": 0.85,
        "max_tokens": 256,
        "secure_mode": False,
        "aphasia_mode": False,
        "rag_enabled": True,
        "context_top_k": 5,
    }

    print("\nPOST /infer")
    print(f"  Payload: {json.dumps(payload, indent=4)}")

    response = requests.post(
        f"{BASE_URL}/infer",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    print(f"\n  Status: {response.status_code}")
    data = response.json()
    print(f"  Accepted: {data.get('accepted', False)}")
    print(f"  Phase: {data.get('phase', 'unknown')}")
    print(f"  Response: {data.get('response', '')[:200]}...")

    # Show metadata
    moral_metadata = data.get("moral_metadata", {})
    print("\n  Moral Metadata:")
    print(f"    Threshold: {moral_metadata.get('threshold', 0)}")
    print(f"    Applied Value: {moral_metadata.get('applied_moral_value', 0)}")

    rag_metadata = data.get("rag_metadata", {})
    print("\n  RAG Metadata:")
    print(f"    Enabled: {rag_metadata.get('enabled', False)}")
    print(f"    Context Items: {rag_metadata.get('context_items_retrieved', 0)}")


def example_status():
    """Service status endpoint."""
    print("\n" + "=" * 60)
    print("Status Endpoint")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/status", timeout=5)
    print("\nGET /status")
    print(f"  Status: {response.status_code}")
    data = response.json()
    print(f"  Version: {data.get('version', 'unknown')}")
    print(f"  Backend: {data.get('backend', 'unknown')}")
    print(f"  Memory (MB): {data.get('system', {}).get('memory_mb', 0):.2f}")


def example_metrics():
    """Prometheus metrics endpoint."""
    print("\n" + "=" * 60)
    print("Metrics Endpoint")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health/metrics", timeout=5)
    print("\nGET /health/metrics")
    print(f"  Status: {response.status_code}")
    # Show first few lines
    lines = response.text.strip().split("\n")[:10]
    print("  Sample metrics:")
    for line in lines:
        if not line.startswith("#"):
            print(f"    {line}")
    print(f"  ... ({len(response.text.split(newline))} total lines)")


def show_curl_examples():
    """Print curl command examples."""
    print("\n" + "=" * 60)
    print("Curl Examples")
    print("=" * 60)
    print("""
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Generate request
curl -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "Hello, world!", "moral_value": 0.8}'

# Extended inference
curl -X POST http://localhost:8000/infer \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Explain AI safety",
    "moral_value": 0.9,
    "secure_mode": true,
    "rag_enabled": true
  }'

# Service status
curl http://localhost:8000/status

# Prometheus metrics
curl http://localhost:8000/health/metrics
""")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MLSDM HTTP Client Examples")
    print("=" * 60)

    # Check if server is running
    if not check_server():
        print("\nWARNING: Server not available at http://localhost:8000")
        print("Start the server with: mlsdm serve")
        print("\nShowing curl examples instead...\n")
        show_curl_examples()
        sys.exit(0)

    print("\n✓ Server is running")

    # Run examples
    example_health_check()
    example_generate()
    example_infer()
    example_status()
    example_metrics()
    show_curl_examples()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")
