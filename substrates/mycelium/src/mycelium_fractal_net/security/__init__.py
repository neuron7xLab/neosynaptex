"""
Security module for MyceliumFractalNet.

Provides security utilities including:
    - Data encryption for sensitive data at rest
    - Input validation and sanitization
    - Audit logging for security-relevant operations
    - Secrets management utilities
    - Security iteration configuration (6 levels)

Security Standards:
    - Follows OWASP security best practices
    - Supports GDPR compliance requirements
    - SOC 2 compatible audit logging

Usage:
    >>> from mycelium_fractal_net.security import (
    ...     encrypt_data,
    ...     decrypt_data,
    ...     validate_input,
    ...     audit_log,
    ...     SecurityLevel,
    ...     get_iteration_count,
    ... )

Reference: docs/MFN_SECURITY.md
"""

from .audit import (
    AuditEvent,
    AuditLogger,
    AuditSeverity,
    audit_log,
    get_audit_logger,
)
from .encryption import (
    DataEncryptor,
    decrypt_data,
    encrypt_data,
    generate_key,
)
from .input_validation import (
    InputValidator,
    ValidationError,
    sanitize_string,
    validate_api_key_format,
    validate_numeric_range,
)
from .iterations import (
    ADAPTIVE_MAX_ITERATIONS,
    ADAPTIVE_MIN_ITERATIONS,
    BASE_ITERATIONS,
    ENHANCED_ITERATIONS,
    HIGH_SECURITY_ITERATIONS,
    MAXIMUM_ITERATIONS,
    QUANTUM_RESISTANT_ITERATIONS,
    SecurityIterationConfig,
    SecurityLevel,
    get_iteration_count,
    get_security_iteration_config,
    reset_security_iteration_config,
    validate_iteration_count,
)
from .secrets_manager import (
    SecretManager,
    SecretManagerConfig,
    SecretRetrievalError,
    SecretsBackend,
)

__all__ = (
    "ADAPTIVE_MAX_ITERATIONS",
    "ADAPTIVE_MIN_ITERATIONS",
    "BASE_ITERATIONS",
    "ENHANCED_ITERATIONS",
    "HIGH_SECURITY_ITERATIONS",
    "MAXIMUM_ITERATIONS",
    "QUANTUM_RESISTANT_ITERATIONS",
    # Audit
    "AuditEvent",
    "AuditLogger",
    "AuditSeverity",
    # Encryption
    "DataEncryptor",
    # Input Validation
    "InputValidator",
    # Secrets management
    "SecretManager",
    "SecretManagerConfig",
    "SecretRetrievalError",
    "SecretsBackend",
    "SecurityIterationConfig",
    # Security Iterations (6 levels)
    "SecurityLevel",
    "ValidationError",
    "audit_log",
    "decrypt_data",
    "encrypt_data",
    "generate_key",
    "get_audit_logger",
    "get_iteration_count",
    "get_security_iteration_config",
    "reset_security_iteration_config",
    "sanitize_string",
    "validate_api_key_format",
    "validate_iteration_count",
    "validate_numeric_range",
)
