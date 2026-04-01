"""
Integration layer for MyceliumFractalNet.

Provides unified schemas, service context, and adapters for consistent
operation across CLI, HTTP API, and experiment entry points.

Components:
    - schemas: Pydantic models for request/response validation
    - service_context: Unified context with config, RNG, and engine handles
    - adapters: Thin bridge between integration layer and numerical core
    - api_config: Configuration management for API features
    - crypto_config: Configuration management for cryptographic features
    - crypto_adapters: Adapters for cryptographic API endpoints
    - auth: API key authentication middleware
    - rate_limiter: Rate limiting middleware
    - metrics: Prometheus metrics collection
    - logging_config: Structured JSON logging
    - data_integrations: 77 data integrations for iteration optimization
    - ws_schemas: WebSocket message schemas for streaming
    - ws_manager: WebSocket connection manager
    - ws_adapters: Adapters for streaming simulation data
    - connectors: Upstream data connectors (REST, File, Kafka)
    - publishers: Downstream event publishers (Webhook, Kafka, File)

Usage:
    >>> from mycelium_fractal_net.integration import (
    ...     ValidateRequest,
    ...     ValidateResponse,
    ...     ServiceContext,
    ...     run_validation_adapter,
    ...     get_integration,
    ...     INTEGRATION_COUNT,
    ...     RESTConnector,
    ...     WebhookPublisher,
    ... )
    >>> ctx = ServiceContext(seed=42)
    >>> request = ValidateRequest(seed=42, epochs=1)
    >>> response = run_validation_adapter(request, ctx)

Reference: docs/ARCHITECTURE.md, docs/MFN_SYSTEM_ROLE.md, docs/MFN_INTEGRATION_GAPS.md
"""

from .adapters import (
    aggregate_gradients_adapter,
    compute_nernst_adapter,
    run_simulation_adapter,
    run_validation_adapter,
)
from .api_config import (
    APIConfig,
    AuthConfig,
    Environment,
    LoggingConfig,
    MetricsConfig,
    RateLimitConfig,
    get_api_config,
    reset_config,
)
from .auth import (
    API_KEY_HEADER,
    APIKeyMiddleware,
    require_api_key,
)
from .connectors import (
    BaseConnector,
    ConnectorConfig,
    ConnectorMetrics,
    ConnectorStatus,
    FileConnector,
    KafkaConnectorAdapter,
    RESTConnector,
)
from .connectors import RetryStrategy as ConnectorRetryStrategy
from .crypto_adapters import (
    CryptoAPIError,
    decrypt_data_adapter,
    encrypt_data_adapter,
    generate_keypair_adapter,
    sign_message_adapter,
    verify_signature_adapter,
)
from .crypto_config import (
    CryptoConfig,
    KeyStore,
    get_crypto_config,
    get_key_store,
    reset_crypto_config,
    reset_key_store,
)
from .data_integrations import (
    CORE_ITERATION_INTEGRATIONS,
    ENCRYPTION_OPTIMIZATION_INTEGRATIONS,
    HASH_FUNCTION_INTEGRATIONS,
    INTEGRATION_COUNT,
    KEY_DERIVATION_INTEGRATIONS,
    MEMORY_OPTIMIZATION_INTEGRATIONS,
    PARALLELIZATION_INTEGRATIONS,
    SALT_GENERATION_INTEGRATIONS,
    VALIDATION_AUDIT_INTEGRATIONS,
    DataIntegration,
    DataIntegrationConfig,
    IntegrationCategory,
    get_data_integration_config,
    get_integration,
    get_integration_categories,
    list_all_integrations,
    reset_data_integration_config,
)
from .logging_config import (
    REQUEST_ID_HEADER,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    get_logger,
    get_request_id,
    set_request_id,
    setup_logging,
)
from .metrics import (
    MetricsMiddleware,
    is_prometheus_available,
    metrics_endpoint,
)
from .publishers import (
    BasePublisher,
    FilePublisher,
    KafkaPublisherAdapter,
    PublisherConfig,
    PublisherMetrics,
    PublisherStatus,
    WebhookPublisher,
)
from .publishers import RetryStrategy as PublisherRetryStrategy
from .rate_limiter import (
    RateLimiter,
    RateLimitMiddleware,
)
from .schemas import (
    DecryptRequest,
    DecryptResponse,
    EncryptRequest,
    EncryptResponse,
    ErrorResponse,
    FederatedAggregateRequest,
    FederatedAggregateResponse,
    HealthResponse,
    KeypairRequest,
    KeypairResponse,
    NernstRequest,
    NernstResponse,
    SignRequest,
    SignResponse,
    SimulateRequest,
    SimulateResponse,
    ValidateRequest,
    ValidateResponse,
    VerifyRequest,
    VerifyResponse,
)
from .service_context import (
    ExecutionMode,
    ServiceContext,
    create_context_from_request,
)
from .ws_adapters import (
    stream_features_adapter,
    stream_simulation_live_adapter,
)
from .ws_manager import (
    BackpressureStrategy,
    WSConnectionManager,
    WSConnectionState,
)
from .ws_schemas import (
    SimulationLiveParams,
    StreamFeaturesParams,
    WSAuthRequest,
    WSErrorMessage,
    WSFeatureUpdate,
    WSHeartbeatRequest,
    WSInitRequest,
    WSMessage,
    WSMessageType,
    WSSimulationComplete,
    WSSimulationState,
    WSStreamType,
    WSSubscribeRequest,
    WSUnsubscribeRequest,
)

__all__ = [
    # Authentication
    "API_KEY_HEADER",
    "CORE_ITERATION_INTEGRATIONS",
    "ENCRYPTION_OPTIMIZATION_INTEGRATIONS",
    "HASH_FUNCTION_INTEGRATIONS",
    # Data Integrations (77 integrations for iteration optimization)
    "INTEGRATION_COUNT",
    "KEY_DERIVATION_INTEGRATIONS",
    "MEMORY_OPTIMIZATION_INTEGRATIONS",
    "PARALLELIZATION_INTEGRATIONS",
    # Logging
    "REQUEST_ID_HEADER",
    "SALT_GENERATION_INTEGRATIONS",
    "VALIDATION_AUDIT_INTEGRATIONS",
    "APIConfig",
    "APIKeyMiddleware",
    "AuthConfig",
    "BackpressureStrategy",
    # Connectors (upstream data sources)
    "BaseConnector",
    # Publishers (downstream event publishing)
    "BasePublisher",
    "ConnectorConfig",
    "ConnectorMetrics",
    "ConnectorRetryStrategy",
    "ConnectorStatus",
    # Crypto Adapters
    "CryptoAPIError",
    # Crypto Configuration
    "CryptoConfig",
    "DataIntegration",
    "DataIntegrationConfig",
    "DecryptRequest",
    "DecryptResponse",
    # Crypto Schemas
    "EncryptRequest",
    "EncryptResponse",
    # API Configuration
    "Environment",
    "ErrorResponse",
    # Service Context
    "ExecutionMode",
    "FederatedAggregateRequest",
    "FederatedAggregateResponse",
    "FileConnector",
    "FilePublisher",
    # Schemas
    "HealthResponse",
    "IntegrationCategory",
    "KafkaConnectorAdapter",
    "KafkaPublisherAdapter",
    "KeyStore",
    "KeypairRequest",
    "KeypairResponse",
    "LoggingConfig",
    "MetricsConfig",
    # Metrics
    "MetricsMiddleware",
    "NernstRequest",
    "NernstResponse",
    "PublisherConfig",
    "PublisherMetrics",
    "PublisherRetryStrategy",
    "PublisherStatus",
    "RESTConnector",
    "RateLimitConfig",
    "RateLimitMiddleware",
    # Rate Limiting
    "RateLimiter",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "ServiceContext",
    "SignRequest",
    "SignResponse",
    "SimulateRequest",
    "SimulateResponse",
    "SimulationLiveParams",
    "StreamFeaturesParams",
    "ValidateRequest",
    "ValidateResponse",
    "VerifyRequest",
    "VerifyResponse",
    "WSAuthRequest",
    "WSConnectionManager",
    "WSConnectionState",
    "WSErrorMessage",
    "WSFeatureUpdate",
    "WSHeartbeatRequest",
    "WSInitRequest",
    "WSMessage",
    # WebSocket Components
    "WSMessageType",
    "WSSimulationComplete",
    "WSSimulationState",
    "WSStreamType",
    "WSSubscribeRequest",
    "WSUnsubscribeRequest",
    "WebhookPublisher",
    "aggregate_gradients_adapter",
    "compute_nernst_adapter",
    "create_context_from_request",
    "decrypt_data_adapter",
    "encrypt_data_adapter",
    "generate_keypair_adapter",
    "get_api_config",
    "get_crypto_config",
    "get_data_integration_config",
    "get_integration",
    "get_integration_categories",
    "get_key_store",
    "get_logger",
    "get_request_id",
    "is_prometheus_available",
    "list_all_integrations",
    "metrics_endpoint",
    "require_api_key",
    "reset_config",
    "reset_crypto_config",
    "reset_data_integration_config",
    "reset_key_store",
    "run_simulation_adapter",
    # Adapters
    "run_validation_adapter",
    "set_request_id",
    "setup_logging",
    "sign_message_adapter",
    "stream_features_adapter",
    "stream_simulation_live_adapter",
    "verify_signature_adapter",
]
