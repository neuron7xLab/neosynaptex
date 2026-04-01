"""
AI Integration Module for Hippocampal CA1

Implements CA1-inspired memory for LLMs:
- Phase-coded key storage
- Plastic storage with Ca²⁺-based updates
- Replay-based consolidation
- Homeostatic capacity control
- HippoRAG-inspired retrieval
"""

from .memory_module import (
    CA1MemoryModule,
    LLMWithCA1Memory,
    MemoryEntry,
    evaluate_retrieval_quality,
)

__all__ = [
    "CA1MemoryModule",
    "LLMWithCA1Memory",
    "MemoryEntry",
    "evaluate_retrieval_quality",
]
