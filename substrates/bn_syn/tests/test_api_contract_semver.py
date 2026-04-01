from __future__ import annotations

from scripts.check_api_contract import (
    CONTRACT_SYMBOLS,
    _normalize_signature_text,
    check_api_changes,
    collect_public_api,
    semver_allows_breaking_change,
)


def test_api_contract_detects_breaking_changes() -> None:
    baseline = {"bnsyn.demo": {"f": "(a, b)"}}
    current = {"bnsyn.demo": {"f": "(a)"}}
    ok, breaking = check_api_changes(baseline, current)
    assert not ok
    assert any("Signature changed" in item for item in breaking)


def test_semver_major_bump_allows_breaking_change() -> None:
    assert semver_allows_breaking_change("0.2.0", "1.0.0")
    assert not semver_allows_breaking_change("0.2.0", "0.3.0")


def test_collect_public_api_uses_contract_symbols_only() -> None:
    snapshot = collect_public_api()
    for module_name, symbols in CONTRACT_SYMBOLS.items():
        assert set(snapshot[module_name]) == set(symbols)


def test_signature_normalization_typing_prefix() -> None:
    before = "(*, x: typing.Annotated[float, Gt(gt=0)] = 1.0) -> None"
    after = "(*, x: Annotated[float, Gt(gt=0)] = 1.0) -> None"
    assert _normalize_signature_text(before) == _normalize_signature_text(after)
