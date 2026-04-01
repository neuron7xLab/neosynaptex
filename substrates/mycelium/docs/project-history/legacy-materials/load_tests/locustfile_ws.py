"""
Locust load test for WebSocket streaming endpoints.

Tests WebSocket streaming under load with:
- Concurrent connections
- Real-time feature streaming
- Live simulation updates
- Connection lifecycle management

Usage:
    # Run locally (requires API server running)
    locust -f load_tests/locustfile_ws.py --host ws://localhost:8000

    # Run with specific users and spawn rate
    locust -f load_tests/locustfile_ws.py --host ws://localhost:8000 \
        --headless -u 100 -r 10 -t 5m

    # Test 500 concurrent connections
    locust -f load_tests/locustfile_ws.py --host ws://localhost:8000 \
        --headless -u 500 -r 50 -t 2m

Environment Variables:
    MFN_LOADTEST_BASE_URL  - WebSocket base URL (default: ws://localhost:8000)
    MFN_LOADTEST_API_KEY   - API key for authentication (optional)

Acceptance Criteria (from MFN-API-STREAMING):
- 30sec stream without drop/frame > 0.5%
- <120ms latency on local cluster
- 500 concurrent ws-clients in test environment

Reference: docs/MFN_BACKLOG.md#MFN-API-STREAMING
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from locust import User, between, events, task
from websocket import create_connection


class WebSocketClient:
    """
    WebSocket client wrapper for Locust load testing.

    Manages WebSocket connection lifecycle and tracks metrics.
    """

    def __init__(self, host: str, api_key: Optional[str] = None):
        self.host = host
        self.api_key = api_key
        self.ws = None
        self.stream_id = None
        self.message_count = 0
        self.error_count = 0
        self.latencies = []

    def connect(self, endpoint: str) -> None:
        """Connect to WebSocket endpoint."""
        url = f"{self.host}{endpoint}"
        start_time = time.time()
        try:
            self.ws = create_connection(url, timeout=10)
            latency = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WSC",
                name=f"{endpoint} [connect]",
                response_time=latency,
                response_length=0,
                exception=None,
                context={},
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WSC",
                name=f"{endpoint} [connect]",
                response_time=latency,
                response_length=0,
                exception=e,
                context={},
            )
            raise

    def send_json(self, data: dict, name: str) -> None:
        """Send JSON message."""
        start_time = time.time()
        try:
            message = json.dumps(data)
            self.ws.send(message)
            latency = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WSS",
                name=name,
                response_time=latency,
                response_length=len(message),
                exception=None,
                context={},
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WSS",
                name=name,
                response_time=latency,
                response_length=0,
                exception=e,
                context={},
            )
            self.error_count += 1
            raise

    def receive_json(self, name: str, timeout: float = 5.0) -> dict:
        """Receive JSON message."""
        start_time = time.time()
        try:
            self.ws.settimeout(timeout)
            message = self.ws.recv()
            latency = (time.time() - start_time) * 1000
            self.latencies.append(latency)
            data = json.loads(message)
            events.request.fire(
                request_type="WSR",
                name=name,
                response_time=latency,
                response_length=len(message),
                exception=None,
                context={},
            )
            self.message_count += 1
            return data
        except (OSError, json.JSONDecodeError) as e:
            latency = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WSR",
                name=name,
                response_time=latency,
                response_length=0,
                exception=e,
                context={},
            )
            self.error_count += 1
            raise

    def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except (OSError, Exception):
                # Ignore errors on close
                pass

    def get_avg_latency(self) -> float:
        """Get average message latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    def get_error_rate(self) -> float:
        """Get error rate as percentage."""
        total = self.message_count + self.error_count
        if total == 0:
            return 0.0
        return (self.error_count / total) * 100


class WebSocketStreamUser(User):
    """
    User that streams features via WebSocket.

    Tests the /ws/stream_features endpoint.
    """

    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")
        self.ws_client = None

    def on_start(self):
        """Setup WebSocket connection."""
        self.ws_client = WebSocketClient(self.host, self.api_key)

    def on_stop(self):
        """Cleanup WebSocket connection."""
        if self.ws_client:
            self.ws_client.close()

    @task
    def stream_features_session(self):
        """
        Complete streaming session: connect, auth, subscribe, receive, close.

        Acceptance: 30sec stream without drop/frame > 0.5%
        """
        try:
            # Connect
            self.ws_client.connect("/ws/stream_features")

            # Init
            self.ws_client.send_json(
                {
                    "type": "init",
                    "payload": {
                        "protocol_version": "1.0",
                        "client_info": "locust-load-test",
                    },
                },
                name="/ws/stream_features [init]",
            )
            self.ws_client.receive_json("/ws/stream_features [init response]")

            # Auth
            self.ws_client.send_json(
                {
                    "type": "auth",
                    "payload": {
                        "api_key": self.api_key or "test-key",
                        "timestamp": time.time() * 1000,
                    },
                },
                name="/ws/stream_features [auth]",
            )
            auth_response = self.ws_client.receive_json("/ws/stream_features [auth response]")

            if auth_response.get("type") != "auth_success":
                # Auth failed, close and retry
                self.ws_client.close()
                return

            # Subscribe
            stream_id = f"stream-{int(time.time() * 1000)}"
            self.ws_client.send_json(
                {
                    "type": "subscribe",
                    "payload": {
                        "stream_type": "stream_features",
                        "stream_id": stream_id,
                        "params": {
                            "update_interval_ms": 100,
                            "compression": False,
                        },
                    },
                },
                name="/ws/stream_features [subscribe]",
            )
            self.ws_client.receive_json("/ws/stream_features [subscribe response]")

            # Receive updates for 30 seconds (acceptance test)
            start_time = time.time()
            duration = 30.0  # 30 seconds as per acceptance criteria
            updates_received = 0

            while (time.time() - start_time) < duration:
                try:
                    response = self.ws_client.receive_json(
                        "/ws/stream_features [update]", timeout=1.0
                    )
                    if response.get("type") == "feature_update":
                        updates_received += 1

                    # Respond to heartbeat
                    if response.get("type") == "heartbeat":
                        self.ws_client.send_json(
                            {
                                "type": "pong",
                                "timestamp": time.time() * 1000,
                            },
                            name="/ws/stream_features [pong]",
                        )
                except (OSError, TimeoutError, Exception):
                    # Timeout or connection error, continue
                    pass

            # Calculate metrics
            avg_latency = self.ws_client.get_avg_latency()
            error_rate = self.ws_client.get_error_rate()

            # Log metrics
            events.request.fire(
                request_type="METRICS",
                name="/ws/stream_features [30s session metrics]",
                response_time=avg_latency,
                response_length=updates_received,
                exception=None if error_rate <= 0.5 else Exception(f"Error rate {error_rate:.2f}%"),
                context={
                    "avg_latency_ms": avg_latency,
                    "error_rate_pct": error_rate,
                    "updates_received": updates_received,
                },
            )

            # Unsubscribe
            self.ws_client.send_json(
                {
                    "type": "unsubscribe",
                    "payload": {"stream_id": stream_id},
                },
                name="/ws/stream_features [unsubscribe]",
            )

            # Close
            self.ws_client.send_json(
                {"type": "close"},
                name="/ws/stream_features [close]",
            )
            self.ws_client.close()

        except Exception:
            # Log error and cleanup
            if self.ws_client:
                self.ws_client.close()
            raise


class WebSocketSimulationUser(User):
    """
    User that streams live simulation via WebSocket.

    Tests the /ws/simulation_live endpoint.
    """

    wait_time = between(2, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")
        self.ws_client = None

    def on_start(self):
        """Setup WebSocket connection."""
        self.ws_client = WebSocketClient(self.host, self.api_key)

    def on_stop(self):
        """Cleanup WebSocket connection."""
        if self.ws_client:
            self.ws_client.close()

    @task
    def simulation_live_session(self):
        """
        Complete simulation streaming session.

        Tests live simulation updates with state-by-state streaming.
        """
        try:
            # Connect
            self.ws_client.connect("/ws/simulation_live")

            # Init
            self.ws_client.send_json(
                {
                    "type": "init",
                    "payload": {"protocol_version": "1.0"},
                },
                name="/ws/simulation_live [init]",
            )
            self.ws_client.receive_json("/ws/simulation_live [init response]")

            # Auth
            self.ws_client.send_json(
                {
                    "type": "auth",
                    "payload": {
                        "api_key": self.api_key or "test-key",
                        "timestamp": time.time() * 1000,
                    },
                },
                name="/ws/simulation_live [auth]",
            )
            auth_response = self.ws_client.receive_json("/ws/simulation_live [auth response]")

            if auth_response.get("type") != "auth_success":
                self.ws_client.close()
                return

            # Subscribe
            stream_id = f"sim-stream-{int(time.time() * 1000)}"
            self.ws_client.send_json(
                {
                    "type": "subscribe",
                    "payload": {
                        "stream_type": "simulation_live",
                        "stream_id": stream_id,
                        "params": {
                            "seed": int(time.time()),
                            "grid_size": 32,
                            "steps": 50,
                            "update_interval_steps": 5,
                        },
                    },
                },
                name="/ws/simulation_live [subscribe]",
            )
            self.ws_client.receive_json("/ws/simulation_live [subscribe response]")

            # Receive state updates until completion
            completed = False
            state_updates = 0

            while not completed:
                try:
                    response = self.ws_client.receive_json(
                        "/ws/simulation_live [update]", timeout=5.0
                    )

                    if response.get("type") == "simulation_state":
                        state_updates += 1
                    elif response.get("type") == "simulation_complete":
                        completed = True
                    elif response.get("type") == "heartbeat":
                        self.ws_client.send_json(
                            {"type": "pong", "timestamp": time.time() * 1000},
                            name="/ws/simulation_live [pong]",
                        )

                except (OSError, TimeoutError, Exception):
                    # Timeout or connection error
                    break

            # Log metrics
            avg_latency = self.ws_client.get_avg_latency()
            error_rate = self.ws_client.get_error_rate()

            events.request.fire(
                request_type="METRICS",
                name="/ws/simulation_live [session metrics]",
                response_time=avg_latency,
                response_length=state_updates,
                exception=None if completed else Exception("Simulation incomplete"),
                context={
                    "avg_latency_ms": avg_latency,
                    "error_rate_pct": error_rate,
                    "state_updates": state_updates,
                    "completed": completed,
                },
            )

            # Close
            self.ws_client.close()

        except Exception:
            if self.ws_client:
                self.ws_client.close()
            raise


class WebSocketMixedUser(User):
    """
    User that performs mixed WebSocket operations.

    Simulates realistic usage with both feature streaming and simulation.
    """

    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")

    @task(3)
    def short_feature_stream(self):
        """Short feature streaming session (5 seconds)."""
        ws_client = WebSocketClient(self.host, self.api_key)
        try:
            ws_client.connect("/ws/stream_features")

            # Init and auth
            ws_client.send_json(
                {"type": "init", "payload": {"protocol_version": "1.0"}},
                name="/ws/stream_features [quick init]",
            )
            ws_client.receive_json("/ws/stream_features [quick init response]")

            ws_client.send_json(
                {
                    "type": "auth",
                    "payload": {
                        "api_key": self.api_key or "test-key",
                        "timestamp": time.time() * 1000,
                    },
                },
                name="/ws/stream_features [quick auth]",
            )
            ws_client.receive_json("/ws/stream_features [quick auth response]")

            # Subscribe
            stream_id = f"quick-stream-{int(time.time() * 1000)}"
            ws_client.send_json(
                {
                    "type": "subscribe",
                    "payload": {
                        "stream_type": "stream_features",
                        "stream_id": stream_id,
                        "params": {"update_interval_ms": 200},
                    },
                },
                name="/ws/stream_features [quick subscribe]",
            )
            ws_client.receive_json("/ws/stream_features [quick subscribe response]")

            # Receive for 5 seconds
            start = time.time()
            while (time.time() - start) < 5.0:
                try:
                    ws_client.receive_json("/ws/stream_features [quick update]", timeout=1.0)
                except (OSError, TimeoutError):
                    pass

            ws_client.close()

        except (OSError, Exception):
            ws_client.close()

    @task(1)
    def quick_simulation(self):
        """Quick simulation stream."""
        ws_client = WebSocketClient(self.host, self.api_key)
        try:
            ws_client.connect("/ws/simulation_live")

            # Quick setup
            ws_client.send_json(
                {"type": "init", "payload": {"protocol_version": "1.0"}},
                name="/ws/simulation_live [quick init]",
            )
            ws_client.receive_json("/ws/simulation_live [quick init response]")

            ws_client.send_json(
                {
                    "type": "auth",
                    "payload": {
                        "api_key": self.api_key or "test-key",
                        "timestamp": time.time() * 1000,
                    },
                },
                name="/ws/simulation_live [quick auth]",
            )
            ws_client.receive_json("/ws/simulation_live [quick auth response]")

            # Small simulation
            ws_client.send_json(
                {
                    "type": "subscribe",
                    "payload": {
                        "stream_type": "simulation_live",
                        "stream_id": f"quick-sim-{int(time.time() * 1000)}",
                        "params": {
                            "seed": int(time.time()),
                            "grid_size": 16,
                            "steps": 10,
                            "update_interval_steps": 2,
                        },
                    },
                },
                name="/ws/simulation_live [quick subscribe]",
            )
            ws_client.receive_json("/ws/simulation_live [quick subscribe response]")

            # Wait for completion
            for _ in range(20):
                try:
                    response = ws_client.receive_json(
                        "/ws/simulation_live [quick update]", timeout=2.0
                    )
                    if response.get("type") == "simulation_complete":
                        break
                except (OSError, TimeoutError):
                    break

            ws_client.close()

        except (OSError, Exception):
            ws_client.close()
