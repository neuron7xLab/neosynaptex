"""
Pydantic schemas for MyceliumFractalNet API.

Provides unified request/response models for CLI, FastAPI, and experiments.
These schemas ensure consistent data validation and serialization across
all entry points (CLI, HTTP API, Python API).

Reference: docs/ARCHITECTURE.md, docs/MFN_SYSTEM_ROLE.md
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# =============================================================================
# Health Check
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    engine_version: str = "0.1.0"
    api_version: str = "v1"
    uptime: float = 0.0


# =============================================================================
# Validation Cycle
# =============================================================================


class ValidateRequest(BaseModel):
    """
    Request parameters for validation cycle.

    Attributes:
        seed: Random seed for reproducibility. Range: [0, ∞). Default: 42.
        epochs: Number of training epochs. Range: [1, 100]. Default: 1.
        batch_size: Batch size for training. Range: [1, 64]. Default: 4.
        grid_size: Size of simulation grid (NxN). Range: [8, 256]. Default: 64.
        steps: Number of simulation steps. Range: [1, 1000]. Default: 64.
        turing_enabled: Enable Turing morphogenesis. Default: True.
        quantum_jitter: Enable quantum noise jitter. Default: False.
    """

    seed: int = Field(default=42, ge=0)
    epochs: int = Field(default=1, ge=1, le=100)
    batch_size: int = Field(default=4, ge=1, le=64)
    grid_size: int = Field(default=64, ge=8, le=256)
    steps: int = Field(default=64, ge=1, le=1000)
    turing_enabled: bool = True
    quantum_jitter: bool = False


class ValidateResponse(BaseModel):
    """
    Response from validation cycle.

    Contains loss metrics, potential statistics, and validation results.

    Attributes:
        loss_start: Initial loss value before training.
        loss_final: Final loss value after training.
        loss_drop: Absolute loss reduction (loss_start - loss_final).
        pot_min_mV: Minimum potential in millivolts.
        pot_max_mV: Maximum potential in millivolts.
        example_fractal_dim: Example fractal dimension from simulation.
        lyapunov_exponent: Lyapunov exponent (negative = stable).
        growth_events: Average growth events per simulation.
        nernst_symbolic_mV: Symbolic Nernst potential (mV).
        nernst_numeric_mV: Numeric Nernst potential (mV).
    """

    loss_start: float
    loss_final: float
    loss_drop: float
    pot_min_mV: float
    pot_max_mV: float
    example_fractal_dim: float
    lyapunov_exponent: float
    growth_events: float
    nernst_symbolic_mV: float
    nernst_numeric_mV: float


# =============================================================================
# Field Simulation
# =============================================================================


class SimulateRequest(BaseModel):
    """
    Request parameters for mycelium field simulation.

    Attributes:
        seed: Random seed for reproducibility. Range: [0, ∞). Default: 42.
        grid_size: Size of simulation grid (NxN). Range: [8, 256]. Default: 64.
        steps: Number of simulation steps. Range: [1, 1000]. Default: 64.
        alpha: Diffusion coefficient (CFL stability requires <= 0.25).
            Range: [0.0, 1.0]. Default: 0.18.
        spike_probability: Probability of growth events per step.
            Range: [0.0, 1.0]. Default: 0.25.
        turing_enabled: Enable Turing morphogenesis. Default: True.
    """

    seed: int = Field(default=42, ge=0)
    grid_size: int = Field(default=64, ge=8, le=256)
    steps: int = Field(default=64, ge=1, le=1000)
    alpha: float = Field(default=0.18, ge=0.0, le=1.0)
    spike_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    turing_enabled: bool = True


class SimulateResponse(BaseModel):
    """
    Response from field simulation.

    Contains growth events, potential statistics, and fractal dimension.

    Attributes:
        growth_events: Number of growth events during simulation.
        pot_min_mV: Minimum potential in millivolts.
        pot_max_mV: Maximum potential in millivolts.
        pot_mean_mV: Mean potential in millivolts.
        pot_std_mV: Standard deviation of potential in millivolts.
        fractal_dimension: Box-counting fractal dimension (D ∈ [0, 2]).
    """

    growth_events: int
    pot_min_mV: float
    pot_max_mV: float
    pot_mean_mV: float
    pot_std_mV: float
    fractal_dimension: float


# =============================================================================
# Nernst Potential
# =============================================================================


class NernstRequest(BaseModel):
    """
    Request parameters for Nernst potential computation.

    Attributes:
        z_valence: Ion valence (K+=1, Ca2+=2, Cl-=1). Range: [1, 3]. Default: 1.
        concentration_out_molar: Extracellular concentration (mol/L). Must be > 0.
        concentration_in_molar: Intracellular concentration (mol/L). Must be > 0.
        temperature_k: Temperature in Kelvin. Range: [273, 373]. Default: 310 (37°C).
    """

    z_valence: int = Field(default=1, ge=1, le=3)
    concentration_out_molar: float = Field(gt=0)
    concentration_in_molar: float = Field(gt=0)
    temperature_k: float = Field(default=310.0, ge=273.0, le=373.0)


class NernstResponse(BaseModel):
    """
    Response from Nernst potential computation.

    Attributes:
        potential_mV: Computed membrane potential in millivolts.
    """

    potential_mV: float


# =============================================================================
# Federated Aggregation
# =============================================================================


class FederatedAggregateRequest(BaseModel):
    """
    Request parameters for federated gradient aggregation.

    Uses Hierarchical Krum aggregation for Byzantine-robust learning.

    Attributes:
        gradients: List of gradient vectors from federated clients.
            Each gradient is a list of float values.
        num_clusters: Number of clusters for hierarchical aggregation.
            Range: [1, 1000]. Default: 10.
        byzantine_fraction: Expected fraction of Byzantine (malicious) clients.
            Range: [0.0, 0.5]. Default: 0.2.
    """

    gradients: list[list[float]]
    num_clusters: int = Field(default=10, ge=1, le=1000)
    byzantine_fraction: float = Field(default=0.2, ge=0.0, le=0.5)


class FederatedAggregateResponse(BaseModel):
    """
    Response from federated aggregation.

    Attributes:
        aggregated_gradient: Aggregated gradient vector after Krum selection.
        num_input_gradients: Number of input gradients processed.
    """

    aggregated_gradient: list[float]
    num_input_gradients: int


# =============================================================================
# Error Response (MFN-API-005)
# =============================================================================


class ErrorDetail(BaseModel):
    """
    Detailed error information for debugging.

    Attributes:
        field: Field name that caused the error (for validation errors).
        message: Detailed error message.
        value: The invalid value (if applicable and safe to log).
    """

    field: str | None = None
    message: str
    value: str | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Provides consistent error format across all API endpoints including:
    - Machine-readable error code
    - Human-readable message
    - Optional detailed error information
    - Request ID for correlation

    Reference: docs/MFN_BACKLOG.md#MFN-API-005

    Attributes:
        error_code: Machine-readable error code (e.g., "VALIDATION_ERROR", "RATE_LIMIT_EXCEEDED").
        message: Human-readable error message.
        detail: Detailed error message (deprecated, use 'message' instead).
        details: List of detailed error information (for validation errors).
        request_id: Request correlation ID for debugging.
        timestamp: ISO 8601 timestamp when error occurred.
    """

    error_code: str = Field(
        description="Machine-readable error code",
        examples=["VALIDATION_ERROR", "AUTHENTICATION_REQUIRED", "RATE_LIMIT_EXCEEDED"],
    )
    message: str = Field(description="Human-readable error message")
    detail: str | None = Field(
        default=None,
        description="Detailed error message (deprecated, for backward compatibility)",
    )
    details: list[ErrorDetail] | None = Field(
        default=None, description="List of detailed errors (for validation errors)"
    )
    request_id: str | None = Field(default=None, description="Request correlation ID")
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")


# =============================================================================
# Error Codes
# =============================================================================


class ErrorCode:
    """Standard error codes for the MFN API."""

    # Authentication errors (401)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_API_KEY = "INVALID_API_KEY"

    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"

    # Rate limiting errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"

    # Internal errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    COMPUTATION_FAILED = "COMPUTATION_FAILED"
    NUMERICAL_INSTABILITY = "NUMERICAL_INSTABILITY"

    # Service errors (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Cryptography errors
    CRYPTO_ERROR = "CRYPTO_ERROR"
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    DECRYPTION_FAILED = "DECRYPTION_FAILED"
    SIGNATURE_FAILED = "SIGNATURE_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    KEY_GENERATION_FAILED = "KEY_GENERATION_FAILED"


# =============================================================================
# Cryptography API Schemas (Step 4: API Integration)
# =============================================================================


class EncryptRequest(BaseModel):
    """
    Request for encrypting data using AES-256-GCM.

    Attributes:
        plaintext: Base64-encoded data to encrypt.
        key_id: Optional key identifier. If not provided, server-managed key is used.
        associated_data: Optional base64-encoded associated data for authenticated encryption.
    """

    plaintext: str = Field(
        description="Base64-encoded plaintext data to encrypt",
        min_length=1,
        max_length=1048576,  # 1 MB limit
    )
    key_id: str | None = Field(
        default=None,
        description="Key identifier for encryption. If not provided, server-managed key is used.",
        max_length=64,
    )
    associated_data: str | None = Field(
        default=None,
        description="Base64-encoded additional authenticated data (AAD)",
        max_length=4096,
    )


class EncryptResponse(BaseModel):
    """
    Response from encryption operation.

    Attributes:
        ciphertext: Base64-encoded encrypted data (includes nonce and auth tag).
        key_id: Identifier of the key used for encryption.
        algorithm: Encryption algorithm used.
    """

    ciphertext: str = Field(description="Base64-encoded ciphertext")
    key_id: str = Field(description="Key identifier used for encryption")
    algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")


class DecryptRequest(BaseModel):
    """
    Request for decrypting AES-256-GCM encrypted data.

    Attributes:
        ciphertext: Base64-encoded ciphertext to decrypt.
        key_id: Optional key identifier. If not provided, server-managed key is used.
        associated_data: Optional base64-encoded associated data used during encryption.
    """

    ciphertext: str = Field(
        description="Base64-encoded ciphertext to decrypt",
        min_length=1,
        max_length=1048576,  # 1 MB limit
    )
    key_id: str | None = Field(
        default=None,
        description="Key identifier for decryption",
        max_length=64,
    )
    associated_data: str | None = Field(
        default=None,
        description="Base64-encoded AAD used during encryption",
        max_length=4096,
    )


class DecryptResponse(BaseModel):
    """
    Response from decryption operation.

    Attributes:
        plaintext: Base64-encoded decrypted data.
        key_id: Identifier of the key used for decryption.
    """

    plaintext: str = Field(description="Base64-encoded plaintext")
    key_id: str = Field(description="Key identifier used for decryption")


class SignRequest(BaseModel):
    """
    Request for signing a message using Ed25519.

    Attributes:
        message: Base64-encoded message or hash to sign.
        key_id: Optional key identifier. If not provided, server-managed key is used.
    """

    message: str = Field(
        description="Base64-encoded message to sign",
        min_length=1,
        max_length=1048576,  # 1 MB limit
    )
    key_id: str | None = Field(
        default=None,
        description="Key identifier for signing",
        max_length=64,
    )


class SignResponse(BaseModel):
    """
    Response from signing operation.

    Attributes:
        signature: Base64-encoded digital signature.
        key_id: Identifier of the key used for signing.
        algorithm: Signature algorithm used.
    """

    signature: str = Field(description="Base64-encoded Ed25519 signature")
    key_id: str = Field(description="Key identifier used for signing")
    algorithm: str = Field(default="Ed25519", description="Signature algorithm")


class VerifyRequest(BaseModel):
    """
    Request for verifying a digital signature.

    Attributes:
        message: Base64-encoded original message.
        signature: Base64-encoded signature to verify.
        public_key: Optional base64-encoded public key. If not provided, key_id must be set.
        key_id: Optional key identifier for looking up the public key.
    """

    message: str = Field(
        description="Base64-encoded original message",
        min_length=1,
        max_length=1048576,
    )
    signature: str = Field(
        description="Base64-encoded signature to verify",
        min_length=1,
        max_length=256,
    )
    public_key: str | None = Field(
        default=None,
        description="Base64-encoded public key for verification",
        max_length=256,
    )
    key_id: str | None = Field(
        default=None,
        description="Key identifier to look up public key",
        max_length=64,
    )


class VerifyResponse(BaseModel):
    """
    Response from signature verification.

    Attributes:
        valid: True if signature is valid, False otherwise.
        key_id: Identifier of the key used for verification (if applicable).
        algorithm: Signature algorithm used for verification.
    """

    valid: bool = Field(description="True if signature is valid")
    key_id: str | None = Field(default=None, description="Key identifier used for verification")
    algorithm: str = Field(default="Ed25519", description="Signature algorithm")


class KeypairRequest(BaseModel):
    """
    Request for generating a new key pair.

    Attributes:
        algorithm: Key type to generate. Either 'ECDH' (X25519) or 'Ed25519'.
        key_id: Optional custom key identifier. Auto-generated if not provided.
    """

    algorithm: str = Field(
        default="Ed25519",
        description="Key algorithm: 'ECDH' for X25519 key exchange, 'Ed25519' for signatures",
        pattern="^(ECDH|Ed25519)$",
    )
    key_id: str | None = Field(
        default=None,
        description="Custom key identifier. Auto-generated if not provided.",
        max_length=64,
    )


class KeypairResponse(BaseModel):
    """
    Response from key pair generation.

    Attributes:
        key_id: Unique identifier for the generated key pair.
        public_key: Base64-encoded public key.
        algorithm: Algorithm of the generated key pair.
    """

    key_id: str = Field(description="Unique key identifier")
    public_key: str = Field(description="Base64-encoded public key")
    algorithm: str = Field(description="Key algorithm (ECDH or Ed25519)")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DecryptRequest",
    "DecryptResponse",
    # Cryptography
    "EncryptRequest",
    "EncryptResponse",
    "ErrorCode",
    "ErrorDetail",
    # Error
    "ErrorResponse",
    # Federated
    "FederatedAggregateRequest",
    "FederatedAggregateResponse",
    # Health
    "HealthResponse",
    "KeypairRequest",
    "KeypairResponse",
    # Nernst
    "NernstRequest",
    "NernstResponse",
    "SignRequest",
    "SignResponse",
    # Simulation
    "SimulateRequest",
    "SimulateResponse",
    # Validation
    "ValidateRequest",
    "ValidateResponse",
    "VerifyRequest",
    "VerifyResponse",
]
