from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetStep:
    before: float
    action_cost: float
    after: float
    overspend: bool


@dataclass
class BudgetLedger:
    envelope: float
    probe_tax: float
    remaining: float

    @classmethod
    def create(cls, envelope: float, probe_tax: float) -> "BudgetLedger":
        return cls(envelope=envelope, probe_tax=probe_tax, remaining=envelope)

    def apply(self, requested_cost: float, quarantine_cost: float) -> BudgetStep:
        cost = requested_cost + self.probe_tax
        before = self.remaining
        overspend = cost > self.remaining
        if overspend:
            cost = min(self.remaining, quarantine_cost + self.probe_tax)
        self.remaining -= cost
        return BudgetStep(before=before, action_cost=cost, after=self.remaining, overspend=overspend)

    def snapshot(self) -> dict[str, float | bool]:
        spent = self.envelope - self.remaining
        return {
            "envelope": round(self.envelope, 6),
            "probe_tax": round(self.probe_tax, 6),
            "spent": round(spent, 6),
            "remaining": round(self.remaining, 6),
            "conserved": round(spent + self.remaining, 6) == round(self.envelope, 6),
        }
