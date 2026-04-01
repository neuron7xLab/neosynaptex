"""
MLSDM SDK: Public Python SDK for NeuroCognitiveEngine.

This module provides a high-level client interface for interacting with
the NeuroCognitiveEngine, supporting multiple backends and configurations.

CORE-09 Contract:
- GenerateResponseDTO is the typed response DTO (stable contract)
- MLSDMClientError, MLSDMServerError, MLSDMTimeoutError for error handling
- GENERATE_RESPONSE_DTO_KEYS for contract validation
"""

from mlsdm.sdk.neuro_engine_client import (
    GENERATE_RESPONSE_DTO_KEYS,
    CognitiveStateDTO,
    GenerateResponseDTO,
    MLSDMClientError,
    MLSDMError,
    MLSDMServerError,
    MLSDMTimeoutError,
    NeuroCognitiveClient,
)

__all__ = [
    "NeuroCognitiveClient",
    "GenerateResponseDTO",
    "CognitiveStateDTO",
    "MLSDMError",
    "MLSDMClientError",
    "MLSDMServerError",
    "MLSDMTimeoutError",
    "GENERATE_RESPONSE_DTO_KEYS",
]
