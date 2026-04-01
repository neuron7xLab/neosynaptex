"""
FastAPI server for MyceliumFractalNet v4.1.

Provides REST API for validation, simulation, and federated learning.
Uses the integration layer for consistent schema handling and service context.

Production Features:
    - API key authentication (X-API-Key header)
    - Rate limiting (configurable per endpoint)
    - Prometheus metrics endpoint (/metrics)
    - Structured JSON logging with request IDs
    - WebSocket streaming for real-time simulation data

Usage:
    uvicorn api:app --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health          - Health check (public)
    GET  /metrics         - Prometheus metrics (public)
    POST /validate        - Run validation cycle
    POST /simulate        - Simulate mycelium field
    POST /nernst          - Compute Nernst potential
    POST /federated/aggregate - Aggregate gradients (Krum)
    WS   /ws/stream_features - Real-time fractal features streaming
    WS   /ws/simulation_live - Live simulation state updates

Environment Variables:
    MFN_ENV              - Environment name: dev, staging, prod (default: dev)
    MFN_CORS_ORIGINS     - Comma-separated list of allowed CORS origins
    MFN_API_KEY_REQUIRED - Whether API key auth is required (default: false in dev)
    MFN_API_KEY          - Primary API key for authentication
    MFN_API_KEYS         - Comma-separated list of valid API keys
    MFN_RATE_LIMIT_REQUESTS - Max requests per minute (default: 100)
    MFN_RATE_LIMIT_ENABLED  - Enable rate limiting (default: false in dev)
    MFN_LOG_LEVEL        - Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    MFN_LOG_FORMAT       - Log format: json or text (default: text in dev)
    MFN_METRICS_ENABLED  - Enable Prometheus metrics (default: true)

Reference: docs/MFN_BACKLOG.md#MFN-API-001, MFN-API-002, MFN-OBS-001, MFN-LOG-001, MFN-API-STREAMING
"""

from __future__ import annotations

import asyncio
import os
import time

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

# Import schemas and adapters from integration layer
from mycelium_fractal_net.integration import (
    API_KEY_HEADER,
    REQUEST_ID_HEADER,
    APIKeyMiddleware,
    BackpressureStrategy,
    CryptoAPIError,
    DecryptRequest,
    DecryptResponse,
    EncryptRequest,
    EncryptResponse,
    ExecutionMode,
    FederatedAggregateRequest,
    FederatedAggregateResponse,
    HealthResponse,
    KeypairRequest,
    KeypairResponse,
    MetricsMiddleware,
    NernstRequest,
    NernstResponse,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    ServiceContext,
    SignRequest,
    SignResponse,
    SimulateRequest,
    SimulateResponse,
    SimulationLiveParams,
    StreamFeaturesParams,
    ValidateRequest,
    ValidateResponse,
    VerifyRequest,
    VerifyResponse,
    WSAuthRequest,
    WSConnectionManager,
    WSInitRequest,
    WSMessageType,
    WSSubscribeRequest,
    WSUnsubscribeRequest,
    aggregate_gradients_adapter,
    compute_nernst_adapter,
    decrypt_data_adapter,
    encrypt_data_adapter,
    generate_keypair_adapter,
    get_api_config,
    get_crypto_config,
    get_logger,
    metrics_endpoint,
    run_simulation_adapter,
    run_validation_adapter,
    setup_logging,
    sign_message_adapter,
    stream_features_adapter,
    stream_simulation_live_adapter,
    verify_signature_adapter,
)
from mycelium_fractal_net.integration.api_server import health_payload

# Initialize logging
setup_logging()
logger = get_logger("api")


def _get_cors_origins() -> list[str]:
    """
    Get CORS origins from environment or defaults.

    In development (MFN_ENV=dev), allows all origins.
    In production (MFN_ENV=prod), requires explicit configuration via MFN_CORS_ORIGINS.

    Returns:
        List of allowed origin strings.
    """
    env = os.getenv("MFN_ENV", "dev").lower()
    cors_origins = os.getenv("MFN_CORS_ORIGINS", "")

    if cors_origins:
        # Explicit configuration takes precedence
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    # Environment-based defaults
    if env == "dev":
        return ["*"]  # Allow all in development
    elif env == "staging":
        return ["http://localhost:3000", "http://localhost:8080"]
    else:
        # Production: no default origins; must be explicitly configured
        return []


app = FastAPI(
    title="MyceliumFractalNet API",
    description="Bio-inspired adaptive network with fractal dynamics",
    version="0.1.0",
)

# Get API configuration
api_config = get_api_config()

# Configure CORS middleware
# Reference: docs/MFN_BACKLOG.md#MFN-API-003
_cors_origins = _get_cors_origins()
if _cors_origins:
    _allow_all = "*" in _cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if _allow_all else _cors_origins,
        allow_credentials=not _allow_all,  # Cannot use credentials with "*"
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*", API_KEY_HEADER],
        expose_headers=[
            REQUEST_ID_HEADER,
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
    )

# Security hardening middleware (Anthropic-level defense-in-depth)
from mycelium_fractal_net.security.hardening import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

# Add production middleware (order matters: last added = first executed)
# Desired execution order: SecurityHeaders → RequestID → RequestLogging → Metrics → RateLimit → APIKey → SizeLimit
# Add in reverse so Starlette wraps them correctly.
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Initialize WebSocket connection manager
ws_manager = WSConnectionManager(
    backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    max_queue_size=1000,
    heartbeat_interval=30.0,
    heartbeat_timeout=60.0,
)


@app.on_event("startup")
async def startup_event() -> None:
    """Start background tasks on application startup."""
    await ws_manager.start_heartbeat_monitor()
    logger.info("Application started, heartbeat monitor running")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    await ws_manager.stop_heartbeat_monitor()
    logger.info("Application shutdown, heartbeat monitor stopped")


# Backward compatibility aliases for external consumers
# These re-export the integration layer schemas under the original names
ValidationRequest = ValidateRequest
ValidationResponse = ValidateResponse
SimulationRequest = SimulateRequest
SimulationResponse = SimulateResponse
AggregationRequest = FederatedAggregateRequest
AggregationResponse = FederatedAggregateResponse


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint (public, no auth required)."""
    return HealthResponse(**health_payload())


@app.get("/metrics")
async def get_metrics_default(request: Request) -> Response:
    """
    Default Prometheus metrics endpoint (public, no auth required).

    Returns metrics in Prometheus text format including:
    - mfn_http_requests_total: Total HTTP requests
    - mfn_http_request_duration_seconds: Request latency histogram
    - mfn_http_requests_in_progress: Currently processing requests
    """
    current_config = get_api_config()
    if current_config.metrics.endpoint == "/metrics":
        return await metrics_endpoint(request)
    raise HTTPException(status_code=404, detail="Not Found")


@app.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def metrics_fallback(path: str, request: Request) -> Response:
    """
    Catch-all GET handler to serve metrics when configured dynamically.

    This keeps metrics routing in sync with runtime configuration while
    returning 404 for unrelated paths.
    """
    current_config = get_api_config()
    normalized_path = f"/{path}" if not path.startswith("/") else path

    if normalized_path == current_config.metrics.endpoint:
        return await metrics_endpoint(request)

    if normalized_path == "/metrics" and current_config.metrics.endpoint != "/metrics":
        raise HTTPException(status_code=404, detail="Not Found")

    raise HTTPException(status_code=404, detail="Not Found")


@app.post("/validate", response_model=ValidateResponse)
async def validate(request: ValidateRequest) -> ValidateResponse:
    """Run validation cycle and return metrics.

    CPU-bound validation runs in a thread pool to avoid blocking the event loop.
    """
    import asyncio

    try:
        ctx = ServiceContext(seed=request.seed, mode=ExecutionMode.API)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_validation_adapter, request, ctx)
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/simulate", response_model=SimulateResponse)
async def simulate(request: SimulateRequest) -> SimulateResponse:
    """Simulate mycelium field.

    CPU-bound simulation runs in a thread pool to avoid blocking the event loop.
    """
    import asyncio

    try:
        ctx = ServiceContext(seed=request.seed, mode=ExecutionMode.API)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_simulation_adapter, request, ctx)
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/nernst", response_model=NernstResponse)
async def nernst(request: NernstRequest) -> NernstResponse:
    """Compute Nernst potential."""
    try:
        ctx = ServiceContext(mode=ExecutionMode.API)
        return compute_nernst_adapter(request, ctx)
    except Exception as e:
        logger.error(f"Nernst computation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/federated/aggregate", response_model=FederatedAggregateResponse)
async def aggregate_gradients(
    request: FederatedAggregateRequest,
) -> FederatedAggregateResponse:
    """Aggregate gradients using hierarchical Krum."""
    try:
        ctx = ServiceContext(mode=ExecutionMode.API)
        return aggregate_gradients_adapter(request, ctx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Federated aggregation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Cryptographic API Endpoints (Step 4: API Integration)
# Reference: docs/MFN_CRYPTOGRAPHY.md
# =============================================================================


@app.post("/api/encrypt", response_model=EncryptResponse)
async def encrypt(request: EncryptRequest) -> EncryptResponse:
    """
    Encrypt data using AES-256-GCM.

    Accepts base64-encoded plaintext and returns encrypted ciphertext.
    Uses server-managed keys or a specified key_id.
    """
    crypto_config = get_crypto_config()
    if not crypto_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Cryptographic operations are disabled",
        )

    try:
        return encrypt_data_adapter(request)
    except CryptoAPIError as e:
        logger.warning(f"Encryption failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Encryption failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Encryption failed") from e


@app.post("/api/decrypt", response_model=DecryptResponse)
async def decrypt(request: DecryptRequest) -> DecryptResponse:
    """
    Decrypt AES-256-GCM encrypted data.

    Accepts base64-encoded ciphertext and returns decrypted plaintext.
    Requires the same key_id that was used for encryption.
    """
    crypto_config = get_crypto_config()
    if not crypto_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Cryptographic operations are disabled",
        )

    try:
        return decrypt_data_adapter(request)
    except CryptoAPIError as e:
        logger.warning(f"Decryption failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Decryption failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Decryption failed") from e


@app.post("/api/sign", response_model=SignResponse)
async def sign(request: SignRequest) -> SignResponse:
    """
    Sign a message using Ed25519.

    Accepts base64-encoded message and returns digital signature.
    Uses server-managed signing keys.
    """
    crypto_config = get_crypto_config()
    if not crypto_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Cryptographic operations are disabled",
        )

    try:
        return sign_message_adapter(request)
    except CryptoAPIError as e:
        logger.warning(f"Signing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Signing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signing failed") from e


@app.post("/api/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest) -> VerifyResponse:
    """
    Verify a digital signature.

    Accepts base64-encoded message, signature, and optionally a public key.
    Returns whether the signature is valid.
    """
    crypto_config = get_crypto_config()
    if not crypto_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Cryptographic operations are disabled",
        )

    try:
        return verify_signature_adapter(request)
    except CryptoAPIError as e:
        logger.warning(f"Verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verification failed") from e


@app.post("/api/keypair", response_model=KeypairResponse)
async def keypair(request: KeypairRequest) -> KeypairResponse:
    """
    Generate a new key pair.

    Creates either an Ed25519 signature key pair or an ECDH (X25519) key pair.
    Returns the public key and key ID. Private key is stored securely on server.
    """
    crypto_config = get_crypto_config()
    if not crypto_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Cryptographic operations are disabled",
        )

    try:
        return generate_keypair_adapter(request)
    except CryptoAPIError as e:
        logger.warning(f"Key generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Key generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Key generation failed") from e


# =============================================================================
# WebSocket Streaming Endpoints (MFN-API-STREAMING)
# Reference: docs/MFN_BACKLOG.md#MFN-API-STREAMING
# =============================================================================


@app.websocket("/ws/stream_features")
async def stream_features(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time fractal features streaming.

    Protocol:
        1. Client sends: init message
        2. Client sends: auth message (API key + timestamp)
        3. Server sends: auth_success or auth_failed
        4. Client sends: subscribe message with stream parameters
        5. Server sends: subscribe_success or subscribe_failed
        6. Server streams: feature_update messages
        7. Server/Client exchanges: heartbeat/pong messages
        8. Client sends: close message (optional)

    Backpressure: drop_oldest strategy applied when queue is full.
    """
    connection_id = await ws_manager.connect(websocket)

    try:
        # Connection lifecycle
        authenticated = False
        stream_id = None
        stream_task = None

        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # Handle init
            if msg_type == WSMessageType.INIT.value:
                try:
                    init_req = WSInitRequest(**data.get("payload", {}))
                    ws_manager.connections[connection_id].client_info = init_req.client_info
                    await websocket.send_json(
                        {
                            "type": WSMessageType.INIT.value,
                            "timestamp": time.time() * 1000,
                            "payload": {"protocol_version": "1.0"},
                        }
                    )
                except Exception as e:
                    logger.error(f"Init failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.ERROR.value,
                            "payload": {
                                "error_code": "INIT_FAILED",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle authentication
            elif msg_type == WSMessageType.AUTH.value:
                try:
                    auth_req = WSAuthRequest(**data.get("payload", {}))
                    authenticated = ws_manager.authenticate(
                        connection_id, auth_req.api_key, auth_req.timestamp
                    )
                    if authenticated:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.AUTH_SUCCESS.value,
                                "timestamp": time.time() * 1000,
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.AUTH_FAILED.value,
                                "timestamp": time.time() * 1000,
                                "payload": {
                                    "error_code": "AUTH_FAILED",
                                    "message": "Invalid API key or timestamp",
                                },
                            }
                        )
                except Exception as e:
                    logger.error(f"Auth failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.AUTH_FAILED.value,
                            "payload": {
                                "error_code": "AUTH_ERROR",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle subscription
            elif msg_type == WSMessageType.SUBSCRIBE.value:
                if not authenticated:
                    await websocket.send_json(
                        {
                            "type": WSMessageType.SUBSCRIBE_FAILED.value,
                            "payload": {
                                "error_code": "NOT_AUTHENTICATED",
                                "message": "Must authenticate before subscribing",
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )
                    continue

                try:
                    sub_req = WSSubscribeRequest(**data.get("payload", {}))
                    stream_id = sub_req.stream_id
                    params = StreamFeaturesParams(**(sub_req.params or {}))

                    # Subscribe
                    success = await ws_manager.subscribe(
                        connection_id, stream_id, sub_req.stream_type, sub_req.params
                    )

                    if success:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.SUBSCRIBE_SUCCESS.value,
                                "stream_id": stream_id,
                                "timestamp": time.time() * 1000,
                            }
                        )

                        # Start streaming task
                        ctx = ServiceContext(mode=ExecutionMode.API)
                        stream_task = asyncio.create_task(
                            _stream_features_task(connection_id, stream_id, params, ctx, ws_manager)
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.SUBSCRIBE_FAILED.value,
                                "payload": {
                                    "error_code": "SUBSCRIBE_FAILED",
                                    "message": "Failed to subscribe",
                                    "timestamp": time.time() * 1000,
                                },
                            }
                        )

                except Exception as e:
                    logger.error(f"Subscribe failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.SUBSCRIBE_FAILED.value,
                            "payload": {
                                "error_code": "SUBSCRIBE_ERROR",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle unsubscribe
            elif msg_type == WSMessageType.UNSUBSCRIBE.value:
                try:
                    unsub_req = WSUnsubscribeRequest(**data.get("payload", {}))
                    await ws_manager.unsubscribe(connection_id, unsub_req.stream_id)
                    if stream_task:
                        stream_task.cancel()
                    await websocket.send_json(
                        {
                            "type": WSMessageType.UNSUBSCRIBE.value,
                            "stream_id": unsub_req.stream_id,
                            "timestamp": time.time() * 1000,
                        }
                    )
                except Exception as e:
                    logger.error(f"Unsubscribe failed: {e}", exc_info=True)

            # Handle pong (heartbeat response)
            elif msg_type == WSMessageType.PONG.value:
                await ws_manager.handle_pong(connection_id)

            # Handle close
            elif msg_type == WSMessageType.CLOSE.value:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        if stream_task:
            stream_task.cancel()
        await ws_manager.disconnect(connection_id)


@app.websocket("/ws/simulation_live")
async def simulation_live(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for live simulation state updates.

    Protocol:
        1. Client sends: init message
        2. Client sends: auth message (API key + timestamp)
        3. Server sends: auth_success or auth_failed
        4. Client sends: subscribe message with simulation parameters
        5. Server sends: subscribe_success or subscribe_failed
        6. Server streams: simulation_state messages
        7. Server sends: simulation_complete message
        8. Server/Client exchanges: heartbeat/pong messages

    Backpressure: drop_oldest strategy applied when queue is full.
    """
    connection_id = await ws_manager.connect(websocket)

    try:
        authenticated = False
        stream_id = None
        stream_task = None

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # Handle init
            if msg_type == WSMessageType.INIT.value:
                try:
                    init_req = WSInitRequest(**data.get("payload", {}))
                    ws_manager.connections[connection_id].client_info = init_req.client_info
                    await websocket.send_json(
                        {
                            "type": WSMessageType.INIT.value,
                            "timestamp": time.time() * 1000,
                            "payload": {"protocol_version": "1.0"},
                        }
                    )
                except Exception as e:
                    logger.error(f"Init failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.ERROR.value,
                            "payload": {
                                "error_code": "INIT_FAILED",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle authentication
            elif msg_type == WSMessageType.AUTH.value:
                try:
                    auth_req = WSAuthRequest(**data.get("payload", {}))
                    authenticated = ws_manager.authenticate(
                        connection_id, auth_req.api_key, auth_req.timestamp
                    )
                    if authenticated:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.AUTH_SUCCESS.value,
                                "timestamp": time.time() * 1000,
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.AUTH_FAILED.value,
                                "timestamp": time.time() * 1000,
                                "payload": {
                                    "error_code": "AUTH_FAILED",
                                    "message": "Invalid API key or timestamp",
                                },
                            }
                        )
                except Exception as e:
                    logger.error(f"Auth failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.AUTH_FAILED.value,
                            "payload": {
                                "error_code": "AUTH_ERROR",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle subscription
            elif msg_type == WSMessageType.SUBSCRIBE.value:
                if not authenticated:
                    await websocket.send_json(
                        {
                            "type": WSMessageType.SUBSCRIBE_FAILED.value,
                            "payload": {
                                "error_code": "NOT_AUTHENTICATED",
                                "message": "Must authenticate before subscribing",
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )
                    continue

                try:
                    sub_req = WSSubscribeRequest(**data.get("payload", {}))
                    stream_id = sub_req.stream_id
                    params = SimulationLiveParams(**(sub_req.params or {}))

                    # Subscribe
                    success = await ws_manager.subscribe(
                        connection_id, stream_id, sub_req.stream_type, sub_req.params
                    )

                    if success:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.SUBSCRIBE_SUCCESS.value,
                                "stream_id": stream_id,
                                "timestamp": time.time() * 1000,
                            }
                        )

                        # Start streaming task
                        ctx = ServiceContext(seed=params.seed, mode=ExecutionMode.API)
                        stream_task = asyncio.create_task(
                            _stream_simulation_task(
                                connection_id, stream_id, params, ctx, ws_manager
                            )
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.SUBSCRIBE_FAILED.value,
                                "payload": {
                                    "error_code": "SUBSCRIBE_FAILED",
                                    "message": "Failed to subscribe",
                                    "timestamp": time.time() * 1000,
                                },
                            }
                        )

                except Exception as e:
                    logger.error(f"Subscribe failed: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": WSMessageType.SUBSCRIBE_FAILED.value,
                            "payload": {
                                "error_code": "SUBSCRIBE_ERROR",
                                "message": str(e),
                                "timestamp": time.time() * 1000,
                            },
                        }
                    )

            # Handle unsubscribe
            elif msg_type == WSMessageType.UNSUBSCRIBE.value:
                try:
                    unsub_req = WSUnsubscribeRequest(**data.get("payload", {}))
                    await ws_manager.unsubscribe(connection_id, unsub_req.stream_id)
                    if stream_task:
                        stream_task.cancel()
                    await websocket.send_json(
                        {
                            "type": WSMessageType.UNSUBSCRIBE.value,
                            "stream_id": unsub_req.stream_id,
                            "timestamp": time.time() * 1000,
                        }
                    )
                except Exception as e:
                    logger.error(f"Unsubscribe failed: {e}", exc_info=True)

            # Handle pong
            elif msg_type == WSMessageType.PONG.value:
                await ws_manager.handle_pong(connection_id)

            # Handle close
            elif msg_type == WSMessageType.CLOSE.value:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        if stream_task:
            stream_task.cancel()
        await ws_manager.disconnect(connection_id)


async def _stream_features_task(
    connection_id: str,
    stream_id: str,
    params: StreamFeaturesParams,
    ctx: ServiceContext,
    manager: WSConnectionManager,
) -> None:
    """Background task for streaming features."""
    try:
        async for update in stream_features_adapter(stream_id, params, ctx):
            message = {
                "type": WSMessageType.FEATURE_UPDATE.value,
                "payload": update.model_dump(),
            }
            await manager.send_message(connection_id, message)
    except asyncio.CancelledError:
        logger.info(f"Feature stream task cancelled: {stream_id}")
    except Exception as e:
        logger.error(f"Feature stream error: {e}", exc_info=True)
        error_msg = {
            "type": WSMessageType.ERROR.value,
            "payload": {
                "error_code": "STREAM_ERROR",
                "message": str(e),
                "stream_id": stream_id,
                "timestamp": time.time() * 1000,
            },
        }
        await manager.send_message(connection_id, error_msg)


async def _stream_simulation_task(
    connection_id: str,
    stream_id: str,
    params: SimulationLiveParams,
    ctx: ServiceContext,
    manager: WSConnectionManager,
) -> None:
    """Background task for streaming simulation."""
    try:
        async for update in stream_simulation_live_adapter(stream_id, params, ctx):
            if hasattr(update, "step"):
                # Simulation state update
                message = {
                    "type": WSMessageType.SIMULATION_STATE.value,
                    "payload": update.model_dump(),
                }
            else:
                # Simulation complete
                message = {
                    "type": WSMessageType.SIMULATION_COMPLETE.value,
                    "payload": update.model_dump(),
                }
            await manager.send_message(connection_id, message)
    except asyncio.CancelledError:
        logger.info(f"Simulation stream task cancelled: {stream_id}")
    except Exception as e:
        logger.error(f"Simulation stream error: {e}", exc_info=True)
        error_msg = {
            "type": WSMessageType.ERROR.value,
            "payload": {
                "error_code": "STREAM_ERROR",
                "message": str(e),
                "stream_id": stream_id,
                "timestamp": time.time() * 1000,
            },
        }
        await manager.send_message(connection_id, error_msg)


# === Canonical v1 structural analytics endpoints ===


# V1 endpoints extracted to api_v1.py
from mycelium_fractal_net.api_v1 import v1_router

app.include_router(v1_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
