"""DialogueAdapter — invariant and protocol tests."""

from __future__ import annotations

import pytest

from probe.dialogue_adapter import DialogueAdapter, Turn


def _t(role: str, content: str, tokens: int) -> Turn:
    return Turn(role=role, content=content, token_count=tokens)


def test_domain_is_dialogue() -> None:
    adapter = DialogueAdapter()
    assert adapter.domain == "dialogue"


def test_state_keys_present() -> None:
    adapter = DialogueAdapter()
    state = adapter.state()
    for key in adapter.state_keys:
        assert key in state, f"missing state key: {key}"


def test_topo_nondecreasing() -> None:
    adapter = DialogueAdapter()
    prev_topo = 0.0
    corpus = [
        "alpha beta gamma",
        "beta delta",  # one new token
        "delta epsilon zeta eta",  # three new
        "alpha beta",  # zero new -> topo stays the same
    ]
    for i, content in enumerate(corpus):
        adapter.push(_t("human", content, tokens=10 + i))
        topo = adapter.topo()
        assert topo >= prev_topo
        prev_topo = topo


def test_cost_strictly_increasing() -> None:
    adapter = DialogueAdapter()
    prev_cost = -1.0
    for i in range(8):
        adapter.push(_t("human", f"word{i}", tokens=5))
        cost = adapter.thermo_cost()
        assert cost > prev_cost
        prev_cost = cost


def test_push_immutable_history() -> None:
    adapter = DialogueAdapter()
    adapter.push(_t("human", "hello world", tokens=3))
    adapter.push(_t("assistant", "goodbye", tokens=2))
    turns = adapter.turns
    assert len(turns) == 2
    # ``turns`` returns a tuple -> cannot mutate list in place.
    with pytest.raises((AttributeError, TypeError)):
        turns.append(_t("human", "nope", tokens=1))  # type: ignore[attr-defined]
    # Each Turn is frozen.
    with pytest.raises(AttributeError):
        turns[0].content = "mutated"  # type: ignore[misc]


def test_zero_tokens_rejected() -> None:
    with pytest.raises(ValueError):
        _t("human", "x", tokens=0)


def test_invalid_role_rejected() -> None:
    with pytest.raises(ValueError):
        _t("system", "x", tokens=1)


def test_state_dict_values_are_floats() -> None:
    adapter = DialogueAdapter()
    adapter.push(_t("human", "a b c", tokens=3))
    state = adapter.state()
    for k, v in state.items():
        assert isinstance(v, float), f"{k} should be float, got {type(v)}"


def test_topo_equals_vocab_size() -> None:
    adapter = DialogueAdapter()
    adapter.push(_t("human", "one two three", tokens=3))
    adapter.push(_t("assistant", "one TWO Three four", tokens=4))
    # Case-insensitive tokenization: only "four" is new.
    assert adapter.topo() == 4.0


def test_thermo_cost_sums_tokens() -> None:
    adapter = DialogueAdapter()
    adapter.push(_t("human", "a", tokens=3))
    adapter.push(_t("human", "b", tokens=7))
    adapter.push(_t("assistant", "c", tokens=11))
    assert adapter.thermo_cost() == 21.0


def test_push_non_turn_rejected() -> None:
    adapter = DialogueAdapter()
    with pytest.raises(TypeError):
        adapter.push({"role": "human", "content": "x", "token_count": 1})  # type: ignore[arg-type]
