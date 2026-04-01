"""
MLSDM Utility modules.

Provides common utilities for the MLSDM framework including:
- Bulkhead pattern for fault isolation
- Rate limiting
- Embedding cache for performance optimization
- Array pool for numpy array reuse
- Configuration management with caching
- Error handling
- Input validation
- Security logging
- Mathematical constants and safe operations
- Time provider abstraction for deterministic testing
"""

from .array_pool import (
    ArrayPool,
    ArrayPoolConfig,
    ArrayPoolStats,
    clear_default_pool,
    get_default_pool,
)
from .bulkhead import (
    Bulkhead,
    BulkheadCompartment,
    BulkheadConfig,
    BulkheadFullError,
    BulkheadStats,
)
from .config_loader import (
    ConfigCache,
    ConfigLoader,
    get_config_cache,
)
from .embedding_cache import (
    EmbeddingCache,
    EmbeddingCacheConfig,
    EmbeddingCacheStats,
    clear_default_cache,
    get_default_cache,
)
from .errors import (
    StateCorruptError,
    StateFileNotFoundError,
    StateIncompleteError,
    StateVersionMismatchError,
)
from .math_constants import (
    EPSILON_ABS,
    EPSILON_DIV,
    EPSILON_LOG,
    EPSILON_NORM,
    EPSILON_REL,
    batch_cosine_similarity,
    cosine_similarity,
    is_finite_array,
    is_finite_scalar,
    safe_divide,
    safe_entropy,
    safe_log,
    safe_log2,
    safe_normalize,
    validate_finite,
)
from .rate_limiter import RateLimiter
from .time_provider import (
    DefaultTimeProvider,
    FakeTimeProvider,
    TimeProvider,
    get_default_time_provider,
    reset_default_time_provider,
    set_default_time_provider,
)

__all__ = [
    # Array pool
    "ArrayPool",
    "ArrayPoolConfig",
    "ArrayPoolStats",
    "get_default_pool",
    "clear_default_pool",
    # Bulkhead pattern
    "Bulkhead",
    "BulkheadCompartment",
    "BulkheadConfig",
    "BulkheadFullError",
    "BulkheadStats",
    # Config loader
    "ConfigCache",
    "ConfigLoader",
    "get_config_cache",
    # Embedding cache
    "EmbeddingCache",
    "EmbeddingCacheConfig",
    "EmbeddingCacheStats",
    "get_default_cache",
    "clear_default_cache",
    # State persistence errors
    "StateFileNotFoundError",
    "StateCorruptError",
    "StateVersionMismatchError",
    "StateIncompleteError",
    # Rate limiting
    "RateLimiter",
    # Time provider
    "TimeProvider",
    "DefaultTimeProvider",
    "FakeTimeProvider",
    "get_default_time_provider",
    "set_default_time_provider",
    "reset_default_time_provider",
    # Math constants and utilities
    "EPSILON_NORM",
    "EPSILON_DIV",
    "EPSILON_LOG",
    "EPSILON_REL",
    "EPSILON_ABS",
    "is_finite_scalar",
    "is_finite_array",
    "validate_finite",
    "safe_divide",
    "safe_normalize",
    "safe_log",
    "safe_log2",
    "safe_entropy",
    "cosine_similarity",
    "batch_cosine_similarity",
]
