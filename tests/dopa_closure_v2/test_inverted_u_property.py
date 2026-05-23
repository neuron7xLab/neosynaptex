from core.eai.dopa_closure_v2 import DopaClosureV2Allocator
from core.eai.dopa_types import ClaimSignal


def test_inverted_u_peak_property_sweep() -> None:
    a = DopaClosureV2Allocator("configs/dopa_closure_v2/allocator.yaml")
    base = dict(prediction_error=0.7, uncertainty=0.6, novelty=0.5, evidence_risk=0.4, reversibility=0.7)
    mid = a.priority_of_verification(ClaimSignal("m", load=0.55, **base))
    for i in range(0, 101):
        l = i / 100
        p = a.priority_of_verification(ClaimSignal(f"c{i}", load=l, **base))
        assert p <= mid + 1e-12
