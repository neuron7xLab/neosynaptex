import numpy as np

from mlsdm.core.cognitive_controller import CognitiveController


def test_basic_flow():
    # Use fixed seed for reproducibility
    np.random.seed(42)

    controller = CognitiveController(dim=384)
    vec = np.random.randn(384).astype(np.float32)
    vec = vec / np.linalg.norm(vec)

    # Test 1: Normal
    state = controller.process_event(vec, moral_value=0.9)
    assert state["rejected"] is False
    print("✓ Test 1: Normal flow PASS")

    # Test 2: Moral reject
    state = controller.process_event(vec, moral_value=0.1)
    assert state["rejected"] is True
    print("✓ Test 2: Moral reject PASS")

    # Test 3: Sleep phase - step enough times to enter sleep phase
    for _ in range(7):
        controller.rhythm_step()
    assert controller.rhythm.is_wake() is False, "Should be in sleep phase"
    state = controller.process_event(vec, moral_value=0.9)
    assert "sleep" in state["note"]
    print("✓ Test 3: Sleep phase PASS")

    print("\n✅ ALL TESTS PASSED")


if __name__ == "__main__":
    test_basic_flow()
