import pytest
from coherent_induction.role_state_engine import RoleStateEngine


def test_role_order_enforced() -> None:
    eng = RoleStateEngine(("A", "B", "C"))
    eng.validate_transition("A", "B")
    with pytest.raises(ValueError):
        eng.validate_transition("A", "C")
