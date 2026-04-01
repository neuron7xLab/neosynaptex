from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .contracts import AuditResult, InnovationBand, SigmaIndex

AOCStatus = Literal["INIT", "RUNNING", "STABILIZED", "FAILED", "MAX_ITER", "INCONCLUSIVE"]


@dataclass
class AOCState:
    iteration: int
    zeropoint_hash: str
    current_artifact_hash: str | None
    delta_from_zeropoint: float | None
    sigma: SigmaIndex | None
    audit: AuditResult | None
    band: InnovationBand
    status: AOCStatus

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
