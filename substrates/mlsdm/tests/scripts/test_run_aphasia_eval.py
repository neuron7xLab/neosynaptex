"""
Tests for scripts/run_aphasia_eval.py

This module tests the aphasia evaluation script functionality including
corpus loading, metrics calculation, and failure conditions.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import run_aphasia_eval


def test_run_aphasia_eval_default_corpus(
    tmp_path: Path, monkeypatch: "MonkeyPatch", capsys: "CaptureFixture[str]"
) -> None:
    """Test that run_aphasia_eval.main() runs successfully with a corpus.

    Creates a test corpus file and verifies the evaluation produces
    expected metric output.

    Args:
        tmp_path: Pytest fixture providing temporary directory.
        monkeypatch: Pytest fixture for modifying environment.
        capsys: Pytest fixture for capturing stdout/stderr.
    """
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        """
        {
          "telegraphic": ["This short. No connect. Bad."],
          "normal": ["This is a coherent answer with normal grammar."]
        }
        """,
        encoding="utf-8",
    )

    exit_code = run_aphasia_eval.main(["--corpus", str(corpus)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "AphasiaEvalSuite metrics:" in out
    assert "true_positive_rate:" in out
    assert "true_negative_rate:" in out


def test_run_aphasia_eval_missing_corpus(capsys: "CaptureFixture[str]") -> None:
    """Test that run_aphasia_eval.main() fails gracefully with missing corpus.

    Verifies error handling when corpus file does not exist.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
    """
    exit_code = run_aphasia_eval.main(["--corpus", "/nonexistent/corpus.json"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "Error:" in out or "not found" in out


def test_run_aphasia_eval_fail_on_low_metrics(
    tmp_path: Path, monkeypatch: "MonkeyPatch", capsys: "CaptureFixture[str]"
) -> None:
    """Test that run_aphasia_eval.main() can fail on low metrics.

    Creates a corpus with inverted samples that should produce low
    detection metrics and verifies the --fail-on-low-metrics flag works.

    Args:
        tmp_path: Pytest fixture providing temporary directory.
        monkeypatch: Pytest fixture for modifying environment.
        capsys: Pytest fixture for capturing stdout/stderr.
    """
    corpus = tmp_path / "corpus.json"
    # Create a corpus that will likely have low metrics
    corpus.write_text(
        """
        {
          "telegraphic": ["This is actually a normal sentence with proper grammar."],
          "normal": ["Short. Bad. Fragment."]
        }
        """,
        encoding="utf-8",
    )

    exit_code = run_aphasia_eval.main(["--corpus", str(corpus), "--fail-on-low-metrics"])
    # This should fail because the corpus has inverted samples
    assert exit_code == 1
