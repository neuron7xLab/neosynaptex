#!/usr/bin/env python3
"""
HTTP Inference Example for MLSDM API.

This example demonstrates how to interact with the MLSDM HTTP API
for inference requests using both raw HTTP (requests) and the SDK client.

Prerequisites:
    1. Start the API server:
       $ uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000

    2. Run this example:
       $ python examples/http_inference_example.py

API Endpoints demonstrated:
    - GET  /health           - Simple health check
    - GET  /health/readiness - Readiness probe
    - POST /infer            - Main inference endpoint
    - GET  /status           - Service status with system info
"""

import json
import sys

import requests


def example_raw_http():
    """Example using raw HTTP requests."""
    print("=" * 60)
    print("EXAMPLE 1: Raw HTTP Requests")
    print("=" * 60)

    base_url = "http://localhost:8000"

    # 1. Health Check
    print("\n1. Health Check (GET /health)")
    print("-" * 40)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except requests.ConnectionError:
        print("   ERROR: Could not connect to server. Is it running?")
        return False

    # 2. Readiness Check
    print("\n2. Readiness Check (GET /health/readiness)")
    print("-" * 40)
    response = requests.get(f"{base_url}/health/readiness", timeout=5)
    print(f"   Status Code: {response.status_code}")
    data = response.json()
    print(f"   Ready: {data['ready']}")
    print(f"   Checks: {data['checks']}")

    # 3. Basic Inference
    print("\n3. Basic Inference (POST /infer)")
    print("-" * 40)
    payload = {"prompt": "What is machine learning?", "moral_value": 0.7}
    print(f"   Request: {json.dumps(payload, indent=6)}")

    response = requests.post(
        f"{base_url}/infer", json=payload, headers={"Content-Type": "application/json"}, timeout=30
    )
    print(f"   Status Code: {response.status_code}")
    data = response.json()
    print(f"   Response text: {data['response'][:100]}...")
    print(f"   Accepted: {data['accepted']}")
    print(f"   Phase: {data['phase']}")

    # 4. Inference with all options
    print("\n4. Inference with All Options (POST /infer)")
    print("-" * 40)
    payload = {
        "prompt": "Explain neural networks briefly",
        "moral_value": 0.6,
        "max_tokens": 256,
        "secure_mode": True,
        "aphasia_mode": True,
        "rag_enabled": True,
        "context_top_k": 3,
    }
    print("   Request options: secure_mode=True, aphasia_mode=True")

    response = requests.post(
        f"{base_url}/infer", json=payload, headers={"Content-Type": "application/json"}, timeout=30
    )
    data = response.json()
    print(f"   Response text: {data['response'][:100]}...")
    print(f"   Accepted: {data['accepted']}")
    print(f"   Applied Moral Value: {data['moral_metadata']['applied_moral_value']}")
    print(f"   Secure Mode: {data['moral_metadata']['secure_mode']}")
    print(f"   RAG Enabled: {data['rag_metadata']['enabled']}")

    # 5. Service Status
    print("\n5. Service Status (GET /status)")
    print("-" * 40)
    response = requests.get(f"{base_url}/status", timeout=5)
    data = response.json()
    print(f"   Version: {data['version']}")
    print(f"   Backend: {data['backend']}")
    print(f"   Memory: {data['system']['memory_mb']:.2f} MB")
    print(f"   Dimension: {data['config']['dimension']}")

    return True


def example_sdk_client():
    """Example using the SDK client."""
    print("\n")
    print("=" * 60)
    print("EXAMPLE 2: SDK Client")
    print("=" * 60)

    # Import SDK client
    try:
        from sdk.python.client import MLSDMClient
    except ImportError:
        # Try alternative import path
        sys.path.insert(0, ".")
        from sdk.python.client import MLSDMClient

    client = MLSDMClient(base_url="http://localhost:8000")

    # 1. Health check
    print("\n1. Health Check")
    print("-" * 40)
    try:
        health = client.health()
        print(f"   Status: {health.status}")
    except requests.ConnectionError:
        print("   ERROR: Could not connect to server")
        return False

    # 2. Readiness check
    print("\n2. Readiness Check")
    print("-" * 40)
    readiness = client.readiness()
    print(f"   Ready: {readiness.ready}")
    print(f"   Checks: {readiness.checks}")

    # 3. Inference
    print("\n3. Inference")
    print("-" * 40)
    result = client.infer(prompt="What is artificial intelligence?", moral_value=0.7)
    print(f"   Response: {result.response[:100]}...")
    print(f"   Accepted: {result.accepted}")
    print(f"   Phase: {result.phase}")

    # 4. Inference with secure mode
    print("\n4. Inference with Secure Mode")
    print("-" * 40)
    result = client.infer(
        prompt="Explain quantum computing", moral_value=0.5, secure_mode=True, max_tokens=256
    )
    print(f"   Response: {result.response[:100]}...")
    print(f"   Accepted: {result.accepted}")
    print(f"   Applied Moral Value: {result.moral_metadata['applied_moral_value']}")
    print("   (0.5 + 0.2 secure boost = 0.7)")

    # 5. Service status
    print("\n5. Service Status")
    print("-" * 40)
    status = client.status()
    print(f"   Version: {status['version']}")
    print(f"   Backend: {status['backend']}")

    return True


def example_curl_commands():
    """Print curl command examples."""
    print("\n")
    print("=" * 60)
    print("CURL COMMAND EXAMPLES")
    print("=" * 60)

    print("""
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/readiness

# Basic inference
curl -X POST http://localhost:8000/infer \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "Hello, world!", "moral_value": 0.7}'

# Inference with all options
curl -X POST http://localhost:8000/infer \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Explain machine learning",
    "moral_value": 0.6,
    "max_tokens": 256,
    "secure_mode": true,
    "aphasia_mode": true,
    "rag_enabled": true,
    "context_top_k": 5
  }'

# Service status
curl http://localhost:8000/status

# Prometheus metrics
curl http://localhost:8000/health/metrics
""")


if __name__ == "__main__":
    print("MLSDM HTTP API Examples")
    print("=" * 60)
    print("\nNote: Make sure the API server is running on port 8000")
    print("Start with: uvicorn mlsdm.api.app:app --port 8000")
    print()

    # Check if server is available
    try:
        requests.get("http://localhost:8000/health", timeout=2)
        server_available = True
    except (requests.ConnectionError, requests.Timeout):
        server_available = False
        print("WARNING: Server not available at http://localhost:8000")
        print("Showing curl examples instead...\n")

    if server_available:
        # Run examples
        success = example_raw_http()
        if success:
            example_sdk_client()

    # Always show curl examples
    example_curl_commands()
