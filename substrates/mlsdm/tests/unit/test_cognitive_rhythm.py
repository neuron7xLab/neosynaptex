from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm


def test_cognitive_rhythm_transitions_between_wake_and_sleep() -> None:
    rhythm = CognitiveRhythm(wake_duration=2, sleep_duration=1)

    assert rhythm.is_wake() is True
    assert rhythm.is_sleep() is False
    assert rhythm.get_current_phase() == "wake"

    rhythm.step()
    assert rhythm.get_current_phase() == "wake"
    assert rhythm.is_wake() is True

    rhythm.step()
    assert rhythm.get_current_phase() == "sleep"
    assert rhythm.is_sleep() is True

    rhythm.step()
    assert rhythm.get_current_phase() == "wake"
    assert rhythm.is_wake() is True


def test_cognitive_rhythm_rejects_non_positive_durations() -> None:
    for wake_duration, sleep_duration in ((0, 1), (1, 0), (-1, 2)):
        try:
            CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)
        except ValueError:
            continue
        raise AssertionError("Expected ValueError for non-positive durations")
