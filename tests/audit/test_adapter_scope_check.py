"""Deterministic tests for the adapter-scope drift detector.

The detector is a minimal-surface tool: one regex, one import, one
path-existence sweep. Tests cover parsing, mismatch, path-existence,
and the repo's own current invariant.
"""

from __future__ import annotations

import pathlib
import textwrap

import pytest

from tools.audit.adapter_scope_check import (
    SCOPE_DECLARATION_REGEX,
    WORD_TO_COUNT,
    count_declared_scope,
    extract_prereg_paths,
    run_check,
)

# ---------------------------------------------------------------------------
# Regex + word map
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word,expected",
    [
        ("Two", 2),
        ("Three", 3),
        ("Four", 4),
        ("Five", 5),
        ("Six", 6),
    ],
)
def test_count_declared_scope_recognises_all_supported_words(word, expected):
    text = f"Substrates in scope after audit. {word} — foo, bar."
    assert count_declared_scope(text) == expected


def test_count_declared_scope_is_case_insensitive():
    text = "substrates IN SCOPE AFTER audit. three — a, b, c."
    assert count_declared_scope(text) == 3


def test_count_declared_scope_rejects_missing_declaration():
    with pytest.raises(ValueError, match="Substrates in scope after audit"):
        count_declared_scope("# Some doc with no scope declaration\n")


def test_word_to_count_covers_regex_alternation():
    pattern_words = SCOPE_DECLARATION_REGEX.pattern
    for word in WORD_TO_COUNT:
        assert word in pattern_words.lower(), f"regex missing alternation for {word!r}"


# ---------------------------------------------------------------------------
# Prereg table parsing
# ---------------------------------------------------------------------------


def test_extract_prereg_paths_ignores_header_alignment_and_scoped_out():
    md = textwrap.dedent(
        """
        ## Pre-registration block

        | Substrate | Knob(s) | Adapter code location | Pre-registration commit SHA |
        |---|---|---|---|
        | MFN+ | alpha | substrates/mfn/src/mycelium_fractal_net/core/engine.py | *(tba)* |
        | Kuramoto (proxy) | window, ema_alpha | substrates/kuramoto/a.py | *(tba)* |
        | BN-Syn | p_conn | substrates/bn_syn/src/bnsyn/sim/network.py | *(tba)* |
        | LLM multi-agent | — | scoped out | — |
        """
    ).strip()
    paths = extract_prereg_paths(md)
    assert paths == [
        "substrates/mfn/src/mycelium_fractal_net/core/engine.py",
        "substrates/kuramoto/a.py",
        "substrates/bn_syn/src/bnsyn/sim/network.py",
    ]


def test_extract_prereg_paths_handles_backticks_and_whitespace():
    md = (
        "## Pre-registration block\n\n"
        "| X | y | `  substrates/x/a.py  ` | *(tba)* |\n"
        "| Y | y | scoped out | — |\n"
    )
    paths = extract_prereg_paths(md)
    assert paths == ["`  substrates/x/a.py  `"]


def test_extract_prereg_paths_on_empty_returns_empty():
    assert extract_prereg_paths("") == []


def test_extract_prereg_paths_ignores_other_four_column_tables():
    """Regime tables share the row shape but must not be parsed as paths."""

    md = textwrap.dedent(
        """
        ## 2. Kuramoto

        | Regime | `window` | `ema_alpha` | Code-ground |
        |---|---|---|---|
        | Compressed | 21 | 0.05 | short |
        | Expanded | 252 | 0.30 | annual default |

        ## Pre-registration block

        | Substrate | Knob(s) | Adapter code location | SHA |
        |---|---|---|---|
        | X | y | substrates/x/a.py | tba |
        """
    ).strip()
    paths = extract_prereg_paths(md)
    assert paths == ["substrates/x/a.py"]


def test_extract_prereg_paths_stops_at_next_heading():
    md = textwrap.dedent(
        """
        ## Pre-registration block

        | Substrate | Knob(s) | Adapter code location | SHA |
        |---|---|---|---|
        | X | y | substrates/x/a.py | tba |

        ## Some later section

        | A | b | substrates/should/not/match.py | c |
        """
    ).strip()
    paths = extract_prereg_paths(md)
    assert paths == ["substrates/x/a.py"]


# ---------------------------------------------------------------------------
# run_check on synthetic fixtures
# ---------------------------------------------------------------------------


def _write_synthetic_knobs(tmp_path: pathlib.Path, scope_word: str, rows: str) -> pathlib.Path:
    content = textwrap.dedent(
        f"""
        # Synthetic horizon_knobs.md for testing.

        Substrates in scope after audit. {scope_word} — foo, bar, baz.

        ## Pre-registration block

        | Substrate | Knob(s) | Adapter code location | Pre-registration commit SHA |
        |---|---|---|---|
        {rows}
        """
    ).strip()
    path = tmp_path / "knobs.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_run_check_reports_drift_when_declared_count_mismatches(tmp_path, monkeypatch):
    # Declare "Five" in prose but the real ADAPTERS has 3.
    rows = "| X | y | tools/audit/__init__.py | tba |"
    knobs = _write_synthetic_knobs(tmp_path, "Five", rows)
    code, msg = run_check(knobs_path=knobs, repo_root=tmp_path.parent)
    assert code == 2
    assert "DRIFT" in msg and "5" in msg


def test_run_check_reports_drift_on_missing_path(tmp_path):
    # Declared matches ADAPTERS, but table points at a bogus path.
    from substrates.bridge.levin_runner import ADAPTERS

    word = next(w for w, c in WORD_TO_COUNT.items() if c == len(ADAPTERS))
    rows = "| X | y | substrates/this/does/not/exist.py | tba |"
    knobs = _write_synthetic_knobs(tmp_path, word.capitalize(), rows)
    code, msg = run_check(knobs_path=knobs, repo_root=tmp_path)
    assert code == 2
    assert "non-existent" in msg


def test_run_check_missing_declaration_is_drift(tmp_path):
    # horizon_knobs.md without the canonical sentence.
    path = tmp_path / "knobs.md"
    path.write_text("# no declaration here\n", encoding="utf-8")
    code, msg = run_check(knobs_path=path, repo_root=tmp_path)
    assert code == 2
    assert "Substrates in scope after audit" in msg


def test_run_check_missing_file_is_drift(tmp_path):
    code, msg = run_check(knobs_path=tmp_path / "does_not_exist.md", repo_root=tmp_path)
    assert code == 2
    assert "not found" in msg


# ---------------------------------------------------------------------------
# The canonical repo state itself
# ---------------------------------------------------------------------------


def test_repo_canonical_state_passes_drift_check():
    """The repo HEAD MUST satisfy the adapter-scope invariant.

    If this test fails, a PR has landed that declared one scope count
    in prose while the runtime adapter tuple declared another (or
    pointed at a path that was since removed). Fix the canon or the
    runner before merging.
    """

    code, msg = run_check()
    assert code == 0, msg
