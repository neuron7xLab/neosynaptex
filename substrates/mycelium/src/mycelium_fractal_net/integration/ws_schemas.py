"""
WebSocket schemas for MyceliumFractalNet streaming API.

Provides schemas for WebSocket communication including:
- Connection lifecycle (init, auth, subscribe, heartbeat, close)
- Stream features (fractal features streaming)
- Simulation live updates (state-by-state simulation)

Reference: docs/MFN_BACKLOG.md#MFN-API-STREAMING
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# WebSocket Message Types
# =============================================================================


class WSMessageType(str, Enum):
    """WebSocket message types."""

    # Connection lifecycle
    INIT = "init"
    AUTH = "auth"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    SUBSCRIBE = "subscribe"
    SUBSCRIBE_SUCCESS = "subscribe_success"
    SUBSCRIBE_FAILED = "subscribe_failed"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    CLOSE = "close"
    ERROR = "error"

    # Data streams
    FEATURE_UPDATE = "feature_update"
    SIMULATION_STATE = "simulation_state"
    SIMULATION_COMPLETE = "simulation_complete"


class WSStreamType(str, Enum):
    """WebSocket stream subscription types."""

    STREAM_FEATURES = "stream_features"
    SIMULATION_LIVE = "simulation_live"


# =============================================================================
# Base WebSocket Message
# =============================================================================


class WSMessage(BaseModel):
    """
    Base WebSocket message.

    All WebSocket messages follow this structure with a type and optional payload.

    Attributes:
        type: Message type identifying the purpose of the message.
        stream_id: Optional stream identifier for tracking.
        timestamp: Unix timestamp in milliseconds.
        payload: Optional message payload (type-specific).
    """

    type: WSMessageType
    stream_id: str | None = None
    timestamp: float | None = None
    payload: dict[str, Any] | None = None


# =============================================================================
# Connection Lifecycle Messages
# =============================================================================


class WSInitRequest(BaseModel):
    """
    WebSocket initialization request.

    First message from client to initiate connection.

    Attributes:
        protocol_version: Protocol version (currently "1.0").
        client_info: Optional client identification.
    """

    protocol_version: str = "1.0"
    client_info: str | None = None


class WSAuthRequest(BaseModel):
    """
    WebSocket authentication request.

    Authenticates the WebSocket connection using API key and signed timestamp.

    Attributes:
        api_key: API key for authentication.
        timestamp: Unix timestamp in milliseconds (for replay attack prevention).
        signature: HMAC signature of timestamp (optional, for enhanced security).
    """

    api_key: str
    timestamp: float
    signature: str | None = None


class WSSubscribeRequest(BaseModel):
    """
    WebSocket subscription request.

    Subscribes to a specific stream type with optional parameters.

    Attributes:
        stream_type: Type of stream to subscribe to.
        stream_id: Unique identifier for this stream.
        params: Stream-specific parameters.
    """

    stream_type: WSStreamType
    stream_id: str
    params: dict[str, Any] | None = None


class WSUnsubscribeRequest(BaseModel):
    """
    WebSocket unsubscribe request.

    Unsubscribes from a stream.

    Attributes:
        stream_id: Stream identifier to unsubscribe from.
    """

    stream_id: str


class WSHeartbeatRequest(BaseModel):
    """
    WebSocket heartbeat request.

    Sent periodically to keep connection alive.

    Attributes:
        timestamp: Unix timestamp in milliseconds.
    """

    timestamp: float


# =============================================================================
# Stream-Specific Messages
# =============================================================================


class WSFeatureUpdate(BaseModel):
    """
    Feature stream update message.

    Real-time fractal features and metrics.

    Attributes:
        stream_id: Stream identifier.
        sequence: Sequence number for ordering.
        features: Dictionary of fractal features.
        timestamp: Unix timestamp in milliseconds.
    """

    stream_id: str
    sequence: int
    features: dict[str, float] = Field(
        description="Fractal features: fractal_dimension, lyapunov_exponent, growth_events, etc."
    )
    timestamp: float


class WSSimulationState(BaseModel):
    """
    Simulation state update message.

    State-by-state updates during simulation.

    Attributes:
        stream_id: Stream identifier.
        step: Current simulation step.
        total_steps: Total number of steps in simulation.
        state: Current state data (compressed if enabled).
        metrics: Step-level metrics.
        timestamp: Unix timestamp in milliseconds.
    """

    stream_id: str
    step: int
    total_steps: int
    state: dict[str, Any] = Field(
        description="State data: pot_mean_mV, pot_std_mV, active_nodes, field_shape, etc."
    )
    metrics: dict[str, float] | None = None
    timestamp: float


class WSSimulationComplete(BaseModel):
    """
    Simulation completion message.

    Final message when simulation is complete.

    Attributes:
        stream_id: Stream identifier.
        final_metrics: Final simulation metrics.
        timestamp: Unix timestamp in milliseconds.
    """

    stream_id: str
    final_metrics: dict[str, float]
    timestamp: float


# =============================================================================
# Error Messages
# =============================================================================


class WSErrorMessage(BaseModel):
    """
    WebSocket error message.

    Sent when an error occurs during stream processing.

    Attributes:
        error_code: Machine-readable error code.
        message: Human-readable error message.
        stream_id: Optional stream identifier if error is stream-specific.
        timestamp: Unix timestamp in milliseconds.
    """

    error_code: str
    message: str
    stream_id: str | None = None
    timestamp: float


# =============================================================================
# Stream Configuration
# =============================================================================


class StreamFeaturesParams(BaseModel):
    """
    Parameters for stream_features subscription.

    Attributes:
        update_interval_ms: Minimum interval between updates (milliseconds). Default: 100ms.
        features: List of specific features to stream. If None, streams all features.
        compression: Enable compression for large feature sets. Default: False.
    """

    update_interval_ms: int = Field(default=100, ge=10, le=10000)
    features: list[str] | None = None
    compression: bool = False


class SimulationLiveParams(BaseModel):
    """
    Parameters for simulation_live subscription.

    Attributes:
        seed: Random seed for reproducibility. Range: [0, ∞). Default: 42.
        grid_size: Size of simulation grid (NxN). Range: [8, 256]. Default: 64.
        steps: Number of simulation steps. Range: [1, 1000]. Default: 64.
        alpha: Diffusion coefficient. Range: [0.0, 1.0]. Default: 0.18.
        spike_probability: Probability of growth events. Range: [0.0, 1.0]. Default: 0.25.
        turing_enabled: Enable Turing morphogenesis. Default: True.
        update_interval_steps: Send update every N steps. Default: 1.
        include_full_state: Include full grid state in updates. Default: False.
    """

    seed: int = Field(default=42, ge=0)
    grid_size: int = Field(default=64, ge=8, le=256)
    steps: int = Field(default=64, ge=1, le=1000)
    alpha: float = Field(default=0.18, ge=0.0, le=1.0)
    spike_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    turing_enabled: bool = True
    update_interval_steps: int = Field(default=1, ge=1, le=100)
    include_full_state: bool = False
