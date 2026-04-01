"""
Tests for WebSocket streaming endpoints.

Verifies WebSocket streaming functionality:
- Connection lifecycle (init, auth, subscribe, heartbeat, close)
- stream_features endpoint with real-time updates
- simulation_live endpoint with state updates
- Backpressure handling
- Authentication and authorization
- Error handling

Reference: docs/MFN_BACKLOG.md#MFN-API-STREAMING
"""

from __future__ import annotations

import os
import time
from unittest import mock

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("pytest_asyncio")

from mycelium_fractal_net.integration import (
    WSMessageType,
    WSStreamType,
)


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    from mycelium_fractal_net.integration import reset_config

    reset_config()
    yield
    reset_config()


@pytest.fixture
def ws_client():
    """Create test client for WebSocket tests."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",  # Disable auth for basic tests
            "MFN_RATE_LIMIT_ENABLED": "false",
        },
        clear=False,
    ):
        # Import after environment is set
        import mycelium_fractal_net.api as api

        client = TestClient(api.app)
        yield client


@pytest.fixture
def ws_client_with_auth():
    """Create test client with authentication enabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "staging",
            "MFN_API_KEY_REQUIRED": "true",
            "MFN_API_KEY": "test-ws-key-12345",
            "MFN_RATE_LIMIT_ENABLED": "false",
        },
        clear=False,
    ):
        import mycelium_fractal_net.api as api

        client = TestClient(api.app)
        yield client


class TestWebSocketStreamFeatures:
    """Tests for /ws/stream_features endpoint."""

    @pytest.mark.skip(reason="Streaming tests timeout with TestClient - require async test setup")
    def test_stream_features_basic_flow(self, ws_client):
        """Test basic connection and subscription flow."""
        with ws_client.websocket_connect("/ws/stream_features") as websocket:
            # Step 1: Send init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {
                        "protocol_version": "1.0",
                        "client_info": "test-client",
                    },
                }
            )

            # Receive init response
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.INIT.value
            assert "payload" in response

            # Step 2: Send auth (not required in dev mode, but still works)
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {
                        "api_key": "test-key",
                        "timestamp": time.time() * 1000,
                    },
                }
            )

            # Receive auth success
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_SUCCESS.value

            # Step 3: Subscribe to stream
            stream_id = "test-stream-1"
            websocket.send_json(
                {
                    "type": WSMessageType.SUBSCRIBE.value,
                    "payload": {
                        "stream_type": WSStreamType.STREAM_FEATURES.value,
                        "stream_id": stream_id,
                        "params": {
                            "update_interval_ms": 100,  # Fast updates for testing
                            "compression": False,
                        },
                    },
                }
            )

            # Receive subscribe success
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.SUBSCRIBE_SUCCESS.value
            assert response["stream_id"] == stream_id

            # Step 4: Receive feature updates then unsubscribe
            # Try to receive at least one update by checking up to 5 messages
            feature_updates_received = 0
            for _ in range(5):
                response = websocket.receive_json()
                if response["type"] == WSMessageType.FEATURE_UPDATE.value:
                    feature_updates_received += 1
                    assert "payload" in response
                    payload = response["payload"]
                    assert payload["stream_id"] == stream_id
                    assert "features" in payload
                    # Check for expected features
                    features = payload["features"]
                    assert "pot_mean_mV" in features
                    assert "fractal_dimension" in features

                    # Received one update, that's enough - unsubscribe now
                    break

            assert feature_updates_received > 0, "Should receive at least one feature update"

            # Step 5: Unsubscribe before closing
            websocket.send_json(
                {
                    "type": WSMessageType.UNSUBSCRIBE.value,
                    "payload": {"stream_id": stream_id},
                }
            )

            # Step 6: Close connection
            websocket.send_json({"type": WSMessageType.CLOSE.value})

    def test_stream_features_authentication_required(self, ws_client_with_auth):
        """Test that authentication is required when enabled."""
        with ws_client_with_auth.websocket_connect("/ws/stream_features") as websocket:
            # Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()  # Init response

            # Try to subscribe without auth
            websocket.send_json(
                {
                    "type": WSMessageType.SUBSCRIBE.value,
                    "payload": {
                        "stream_type": WSStreamType.STREAM_FEATURES.value,
                        "stream_id": "test-stream",
                        "params": {},
                    },
                }
            )

            # Should receive subscribe failed
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.SUBSCRIBE_FAILED.value
            assert "NOT_AUTHENTICATED" in response["payload"]["error_code"]

    def test_stream_features_with_valid_auth(self, ws_client_with_auth):
        """Test stream with valid authentication."""
        with ws_client_with_auth.websocket_connect("/ws/stream_features") as websocket:
            # Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()

            # Auth with valid key
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {
                        "api_key": "test-ws-key-12345",
                        "timestamp": time.time() * 1000,
                    },
                }
            )

            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_SUCCESS.value

            # Subscribe
            websocket.send_json(
                {
                    "type": WSMessageType.SUBSCRIBE.value,
                    "payload": {
                        "stream_type": WSStreamType.STREAM_FEATURES.value,
                        "stream_id": "auth-test-stream",
                        "params": {"update_interval_ms": 500},
                    },
                }
            )

            response = websocket.receive_json()
            assert response["type"] == WSMessageType.SUBSCRIBE_SUCCESS.value

    def test_stream_features_connection_flow(self, ws_client):
        """Test basic connection, auth, and subscription flow without streaming."""
        with ws_client.websocket_connect("/ws/stream_features") as websocket:
            # Step 1: Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.INIT.value

            # Step 2: Auth
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {"api_key": "test", "timestamp": time.time() * 1000},
                }
            )
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_SUCCESS.value

            # Step 3: Close immediately without subscribing
            websocket.send_json({"type": WSMessageType.CLOSE.value})


class TestWebSocketSimulationLive:
    """Tests for /ws/simulation_live endpoint."""

    @pytest.mark.skip(reason="Streaming tests timeout with TestClient - require async test setup")
    def test_simulation_live_basic_flow(self, ws_client):
        """Test basic simulation streaming."""
        with ws_client.websocket_connect("/ws/simulation_live") as websocket:
            # Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()

            # Auth
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {"api_key": "test", "timestamp": time.time() * 1000},
                }
            )
            websocket.receive_json()

            # Subscribe with simulation params
            stream_id = "sim-test-stream"
            websocket.send_json(
                {
                    "type": WSMessageType.SUBSCRIBE.value,
                    "payload": {
                        "stream_type": WSStreamType.SIMULATION_LIVE.value,
                        "stream_id": stream_id,
                        "params": {
                            "seed": 42,
                            "grid_size": 16,  # Small grid for fast test
                            "steps": 5,  # Few steps
                            "update_interval_steps": 1,  # Update every step
                        },
                    },
                }
            )

            # Receive subscribe success
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.SUBSCRIBE_SUCCESS.value

            # Receive simulation state updates
            state_updates = []
            completion_received = False

            for _ in range(10):  # Expect 5 state updates + 1 completion
                response = websocket.receive_json()

                if response["type"] == WSMessageType.SIMULATION_STATE.value:
                    state_updates.append(response)
                    payload = response["payload"]
                    assert payload["stream_id"] == stream_id
                    assert "step" in payload
                    assert "total_steps" in payload
                    assert payload["total_steps"] == 5
                    assert "state" in payload
                    assert "pot_mean_mV" in payload["state"]

                elif response["type"] == WSMessageType.SIMULATION_COMPLETE.value:
                    completion_received = True
                    payload = response["payload"]
                    assert payload["stream_id"] == stream_id
                    assert "final_metrics" in payload
                    break

            assert len(state_updates) > 0, "Should receive state updates"
            assert completion_received, "Should receive completion message"

    def test_simulation_live_connection_flow(self, ws_client):
        """Test basic connection and auth flow without full simulation."""
        with ws_client.websocket_connect("/ws/simulation_live") as websocket:
            # Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.INIT.value

            # Auth
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {"api_key": "test", "timestamp": time.time() * 1000},
                }
            )
            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_SUCCESS.value

            # Close
            websocket.send_json({"type": WSMessageType.CLOSE.value})


class TestWebSocketHeartbeat:
    """Tests for heartbeat/keepalive functionality."""

    def test_pong_message_handling(self, ws_client):
        """Test that pong messages are accepted."""
        with ws_client.websocket_connect("/ws/stream_features") as websocket:
            # Basic setup
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()

            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {"api_key": "test", "timestamp": time.time() * 1000},
                }
            )
            websocket.receive_json()

            # Send pong (would normally be in response to heartbeat)
            websocket.send_json(
                {
                    "type": WSMessageType.PONG.value,
                    "timestamp": time.time() * 1000,
                }
            )

            # Connection should remain open - close to verify
            websocket.send_json({"type": WSMessageType.CLOSE.value})


class TestWebSocketErrorHandling:
    """Tests for error handling in WebSocket streams."""

    def test_connection_lifecycle(self, ws_client):
        """Test complete connection lifecycle."""
        with ws_client.websocket_connect("/ws/stream_features") as websocket:
            # Init
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()

            # Auth
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {"api_key": "test", "timestamp": time.time() * 1000},
                }
            )

            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_SUCCESS.value

            # Close properly
            websocket.send_json({"type": WSMessageType.CLOSE.value})

    def test_expired_timestamp_auth(self, ws_client_with_auth):
        """Test authentication with expired timestamp."""
        with ws_client_with_auth.websocket_connect("/ws/stream_features") as websocket:
            websocket.send_json(
                {
                    "type": WSMessageType.INIT.value,
                    "payload": {"protocol_version": "1.0"},
                }
            )
            websocket.receive_json()

            # Send auth with very old timestamp (> 5 minutes)
            old_timestamp = (time.time() - 10 * 60) * 1000  # 10 minutes ago
            websocket.send_json(
                {
                    "type": WSMessageType.AUTH.value,
                    "payload": {
                        "api_key": "test-ws-key-12345",
                        "timestamp": old_timestamp,
                    },
                }
            )

            response = websocket.receive_json()
            assert response["type"] == WSMessageType.AUTH_FAILED.value


@pytest.mark.asyncio
class TestWebSocketConnectionManager:
    """Tests for WebSocket connection manager."""

    async def test_connection_manager_stats(self):
        """Test connection manager statistics."""
        from mycelium_fractal_net.integration import WSConnectionManager

        manager = WSConnectionManager()

        stats = manager.get_stats()
        assert stats["total_connections"] == 0
        assert stats["authenticated_connections"] == 0
        assert stats["total_streams"] == 0
        assert stats["backpressure_strategy"] == "drop_oldest"

    async def test_backpressure_strategies(self):
        """Test different backpressure strategies."""
        from mycelium_fractal_net.integration import (
            BackpressureStrategy,
            WSConnectionManager,
        )

        # Test drop_oldest
        manager_drop_oldest = WSConnectionManager(
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
            max_queue_size=10,
        )
        assert manager_drop_oldest.backpressure_strategy == BackpressureStrategy.DROP_OLDEST

        # Test compress
        manager_compress = WSConnectionManager(
            backpressure_strategy=BackpressureStrategy.COMPRESS,
            max_queue_size=10,
        )
        assert manager_compress.backpressure_strategy == BackpressureStrategy.COMPRESS

    async def test_authenticate_missing_api_key(self):
        """Authentication should fail gracefully when the API key is missing."""
        from mycelium_fractal_net.integration import (
            WSConnectionManager,
            WSConnectionState,
        )

        with mock.patch.dict(
            os.environ,
            {
                "MFN_ENV": "staging",
                "MFN_API_KEY_REQUIRED": "true",
                "MFN_API_KEY": "test-ws-key-12345",
            },
            clear=False,
        ):
            manager = WSConnectionManager()
            connection_id = "conn-missing-key"
            manager.connections[connection_id] = WSConnectionState(
                connection_id=connection_id,
                websocket=mock.Mock(),
            )

            timestamp = time.time() * 1000

            assert manager.authenticate(connection_id, None, timestamp) is False
            assert manager.connections[connection_id].authenticated is False

    async def test_optional_authentication_with_missing_key(self):
        """Optional auth must succeed without an API key and not set a masked value."""
        from mycelium_fractal_net.integration import (
            WSConnectionManager,
            WSConnectionState,
        )

        with mock.patch.dict(
            os.environ,
            {
                "MFN_ENV": "staging",
                "MFN_API_KEY_REQUIRED": "false",
                "MFN_RATE_LIMIT_ENABLED": "false",
            },
            clear=False,
        ):
            manager = WSConnectionManager()
            connection_id = "conn-optional-no-key"
            manager.connections[connection_id] = WSConnectionState(
                connection_id=connection_id,
                websocket=mock.Mock(),
            )

            timestamp = time.time() * 1000

            assert manager.authenticate(connection_id, None, timestamp) is True
            assert manager.connections[connection_id].authenticated is True
            assert manager.connections[connection_id].api_key_used is None

    async def test_optional_authentication_with_non_string_key(self):
        """Optional auth should ignore non-string keys instead of crashing."""
        from mycelium_fractal_net.integration import (
            WSConnectionManager,
            WSConnectionState,
        )

        with mock.patch.dict(
            os.environ,
            {
                "MFN_ENV": "staging",
                "MFN_API_KEY_REQUIRED": "false",
                "MFN_RATE_LIMIT_ENABLED": "false",
            },
            clear=False,
        ):
            manager = WSConnectionManager()
            connection_id = "conn-optional-bad-key"
            manager.connections[connection_id] = WSConnectionState(
                connection_id=connection_id,
                websocket=mock.Mock(),
            )

            timestamp = time.time() * 1000

            assert manager.authenticate(connection_id, 12345, timestamp) is True
            assert manager.connections[connection_id].authenticated is True
            assert manager.connections[connection_id].api_key_used is None

    async def test_authenticate_with_invalid_timestamp(self):
        """Authentication should fail cleanly when timestamp cannot be parsed."""
        from mycelium_fractal_net.integration import (
            WSConnectionManager,
            WSConnectionState,
        )

        with mock.patch.dict(
            os.environ,
            {
                "MFN_ENV": "staging",
                "MFN_API_KEY_REQUIRED": "true",
                "MFN_API_KEY": "test-ws-key-12345",
            },
            clear=False,
        ):
            manager = WSConnectionManager()
            connection_id = "conn-invalid-timestamp"
            manager.connections[connection_id] = WSConnectionState(
                connection_id=connection_id,
                websocket=mock.Mock(),
            )

            invalid_timestamp = "not-a-number"

            assert (
                manager.authenticate(connection_id, "test-ws-key-12345", invalid_timestamp) is False
            )
            assert manager.connections[connection_id].authenticated is False
