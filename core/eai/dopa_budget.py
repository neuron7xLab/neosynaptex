from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext

getcontext().prec = 28
_SCALE = Decimal("0.000001")


@dataclass(frozen=True)
class BudgetStep:
    before: float
    action_cost: float
    after: float
    overspend: bool


@dataclass
class BudgetLedger:
    envelope: Decimal
    probe_tax: Decimal
    remaining: Decimal

    @classmethod
    def create(cls, envelope: float, probe_tax: float) -> "BudgetLedger":
        e = Decimal(str(envelope))
        p = Decimal(str(probe_tax))
        return cls(envelope=e, probe_tax=p, remaining=e)

    def apply(self, requested_cost: float, quarantine_cost: float) -> BudgetStep:
        cost = Decimal(str(requested_cost)) + self.probe_tax
        before = self.remaining
        overspend = cost > self.remaining
        if overspend:
            q = Decimal(str(quarantine_cost)) + self.probe_tax
            cost = min(self.remaining, q)
        self.remaining -= cost
        return BudgetStep(float(before), float(cost), float(self.remaining), overspend)

    def snapshot(self) -> dict[str, float | bool]:
        spent = self.envelope - self.remaining
        eq = (spent + self.remaining).quantize(_SCALE) == self.envelope.quantize(_SCALE)
        return {"envelope": float(self.envelope), "probe_tax": float(self.probe_tax), "spent": float(spent), "remaining": float(self.remaining), "conserved": eq}
