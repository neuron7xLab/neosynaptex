"""Memory subpackage for trace storage and consolidation ledger.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports MemoryTrace for pattern storage/recall, MemoryConsolidator for
high-level consolidation API, and ConsolidationLedger for audit trail.

References
----------
docs/SPEC.md
"""

from .consolidator import MemoryConsolidator as MemoryConsolidator
from .ledger import ConsolidationLedger as ConsolidationLedger
from .trace import MemoryTrace as MemoryTrace

__all__ = ["MemoryTrace", "MemoryConsolidator", "ConsolidationLedger"]
