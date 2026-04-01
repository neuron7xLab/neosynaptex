"""
MLSDM Service: HTTP API endpoints for NeuroCognitiveEngine.

This module provides FastAPI-based HTTP services for the NeuroCognitiveEngine.
"""

from mlsdm.service.neuro_engine_service import create_app

__all__ = ["create_app"]
