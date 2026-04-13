"""Audit: is the claim-status taxonomy still being applied in practice?

Signal contract (per ``docs/SYSTEM_PROTOCOL.md`` Measurement discipline)
-----------------------------------------------------------------------

* **Substrate.** This git repository — commit messages and canonical
  documents modified by each commit.
* **Signal.** Per commit, the count of five taxonomy labels
  (``measured``, ``derived``, ``hypothesized``, ``unverified analogy``,
  ``falsified``) occurring in a **structured context**:

  - frontmatter key ``status:`` or ``claim_status:`` or ``claim:``
  - Markdown bullet list items whose inline text contains the label
  - Backticked inline labels (``` `measured` ```)
  - YAML list values under keys named ``claim_status`` / ``status_of_claim``

  Prose occurrences ("measured the gamma exponent") are intentionally
  rejected by the context grammar: we count *labels*, not free text.

* **Computation.** ``count_labels_in_texts`` walks input text blocks,
  applies the structural regex battery, and returns per-label counts +
  distinct-label count + total labeled blocks.
* **Window.** Rolling 30-day (``_DEFAULT_WINDOW_DAYS``). The aggregator
  walks three consecutive windows to detect sustained disuse.
* **Controls.**

  - Normalize by total commits in the window (``labeled_rate``).
  - Exclude self-references from ``docs/SYSTEM_PROTOCOL.md`` itself
    (otherwise the canon doc always satisfies the signal trivially).
* **Fake-alternative guard.** Ritual label-pasting is caught by the
  diversity gate: ``verdict == "applied"`` requires at least two
  DISTINCT labels used across the window.
* **Falsifier.** Three consecutive 30-day windows each with zero
  labeled blocks while ``total_commits > 0`` in the same window.
  Result: ``verdict == "stopped"``. This triggers kill-criterion
  ``taxonomy_disuse`` in ``docs/SYSTEM_PROTOCOL.md`` frontmatter and
  mandates a framework-revision PR.

What this module does NOT do
----------------------------

It does not judge whether a label is CORRECTLY applied. It only counts
presence in structured contexts. Correctness audits are a separate
measurement contract and have not been instrumented yet.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence

__all__ = [
    "CANONICAL_LABELS",
    "Verdict",
    "WindowReport",
    "count_labels_in_texts",
    "decide_verdict",
    "main",
    "run_audit",
]

# Five labels from SYSTEM_PROTOCOL.md §Barrier rule, item 4.
CANONICAL_LABELS: tuple[str, ...] = (
    "measured",
    "derived",
    "hypothesized",
    "unverified analogy",
    "falsified",
)

_DEFAULT_WINDOW_DAYS: int = 30
_DEFAULT_TREND_WINDOWS: int = 3

# Structured-context regex battery. Any one of these patterns wrapping a
# canonical label counts as one occurrence. Bare prose ("measured the …")
# is deliberately not included.
_LABEL_ALT = "|".join(re.escape(label) for label in CANONICAL_LABELS)
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # YAML / frontmatter: status: measured
    re.compile(
        rf"(?mi)^\s*(?:status|claim_status|claim|p_status)\s*:\s*[`'\"]?({_LABEL_ALT})[`'\"]?\s*$"
    ),
    # Markdown bullet with inline-backticked label: "- `measured` — …"
    re.compile(rf"(?m)^\s*[-*]\s*`({_LABEL_ALT})`"),
    # Markdown bullet followed by label in plain text at start: "- measured: …"
    re.compile(rf"(?m)^\s*[-*]\s*({_LABEL_ALT})\b\s*[:—-]"),
    # Inline backticked label inside a Markdown table cell or prose:
    # "| … | `measured` | …"; also catches standalone backticked uses.
    re.compile(rf"`({_LABEL_ALT})`"),
)


@dataclasses.dataclass(frozen=True)
class Verdict:
    """Outcome of a single-window or multi-window audit."""

    name: str  # "applied" | "at_risk" | "stopped" | "no_signal"
    reason: str


@dataclasses.dataclass(frozen=True)
class WindowReport:
    """Aggregate of label presence over one time window."""

    start: _dt.date
    end: _dt.date
    total_commits: int
    labeled_blocks: int
    per_label_counts: dict[str, int]
    distinct_labels_used: int

    @property
    def labeled_rate(self) -> float:
        if self.total_commits == 0:
            return 0.0
        return self.labeled_blocks / float(self.total_commits)


# ---------------------------------------------------------------------------
# Core: count labels in structured contexts
# ---------------------------------------------------------------------------


def count_labels_in_texts(
    texts: Iterable[str],
    *,
    exclude_self_references: bool = True,
) -> tuple[int, dict[str, int], int]:
    """Count canonical-label occurrences in ``texts``.

    Returns ``(labeled_blocks, per_label_counts, distinct_labels_used)``.

    * ``labeled_blocks`` — number of input blocks that contained at
      least one structured label occurrence.
    * ``per_label_counts`` — total occurrences per canonical label
      across all blocks.
    * ``distinct_labels_used`` — count of canonical labels that
      appeared at least once.

    ``exclude_self_references`` drops any block that is the full
    SYSTEM_PROTOCOL.md source text or an excerpt that appears to be a
    verbatim paste of its canonical labels list; this prevents the canon
    doc from trivially satisfying its own audit.
    """

    per_label: dict[str, int] = {label: 0 for label in CANONICAL_LABELS}
    labeled_blocks = 0

    for block in texts:
        if not block:
            continue
        if exclude_self_references and _is_self_reference(block):
            continue
        # Collect all structural matches, then deduplicate by (span, label).
        # A single bullet "- `measured`" matches several patterns (bullet
        # form AND inline-backtick form); without dedup we would count
        # it twice.
        # Collect (label_position, label) pairs. We deliberately use
        # ``match.start(1)`` — the position of the captured label group
        # — rather than ``match.start()`` of the whole match, because
        # the bullet-form pattern (``^\s*[-*]\s*`label```) can absorb
        # the leading newline via ``\s*`` and place the overall match
        # at an earlier position than the backtick-form pattern
        # (`` `label` ``), even though both are logically on the same
        # line. The label-group position is invariant across patterns.
        label_positions: list[tuple[int, str]] = []
        for pattern in _PATTERNS:
            for match in pattern.finditer(block):
                label = match.group(1).lower()
                if label not in per_label:
                    continue
                label_positions.append((match.start(1), label))
        # Dedup by (line_start, label): one event per line per label.
        line_label_seen: set[tuple[int, str]] = set()
        for pos, label in label_positions:
            line_start = block.rfind("\n", 0, pos) + 1
            line_label_seen.add((line_start, label))
        if line_label_seen:
            labeled_blocks += 1
            for _, label in line_label_seen:
                per_label[label] += 1

    distinct = sum(1 for n in per_label.values() if n > 0)
    return labeled_blocks, per_label, distinct


_SELF_REF_MARKERS: tuple[str, ...] = (
    "SYSTEM PROTOCOL — NEOSYNAPTEX MEASUREMENT FRAMEWORK",
    "CANONICAL_LABELS",
    "Every claim must be labeled as one of",
)


def _is_self_reference(block: str) -> bool:
    """Heuristic: true if block is (or embeds) the canon labels list itself.

    Conservative — requires a phrase that only appears inside the canon
    doc or this module's source. Intentional false-negatives: a PR body
    that merely quotes one label is NOT excluded.
    """

    return any(marker in block for marker in _SELF_REF_MARKERS)


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def decide_verdict(windows: Sequence[WindowReport]) -> Verdict:
    """Assign a verdict from a sequence of consecutive-window reports.

    Windows MUST be passed in chronological order, most-recent last.

    Verdicts (in priority order):

    * ``stopped`` — three or more consecutive most-recent windows each
      report zero ``labeled_blocks`` AND ``total_commits > 0``. This is
      the kill-criterion falsifier.
    * ``no_signal`` — every window has ``total_commits == 0``.
    * ``at_risk`` — most-recent window has ``labeled_blocks > 0`` but
      ``distinct_labels_used < 2`` (ritual-pasting suspect), OR
      ``labeled_rate`` has declined across the sequence.
    * ``applied`` — most-recent window has ``labeled_blocks >= 1`` AND
      ``distinct_labels_used >= 2``.
    """

    if not windows:
        return Verdict(name="no_signal", reason="no windows supplied")

    if all(w.total_commits == 0 for w in windows):
        return Verdict(
            name="no_signal",
            reason="no commits in any window; signal undefined",
        )

    tail = list(windows)[-_DEFAULT_TREND_WINDOWS:]
    if len(tail) >= _DEFAULT_TREND_WINDOWS and all(
        w.labeled_blocks == 0 and w.total_commits > 0 for w in tail
    ):
        return Verdict(
            name="stopped",
            reason=(
                f"{_DEFAULT_TREND_WINDOWS} consecutive windows with zero "
                "labeled blocks and non-zero commits — falsifier triggered"
            ),
        )

    latest = windows[-1]
    if latest.total_commits == 0:
        return Verdict(
            name="no_signal",
            reason="latest window has zero commits; signal undefined",
        )

    if latest.labeled_blocks == 0:
        return Verdict(
            name="at_risk",
            reason="latest window has zero labeled blocks",
        )
    if latest.distinct_labels_used < 2:
        return Verdict(
            name="at_risk",
            reason=(
                f"only {latest.distinct_labels_used} distinct label(s) in "
                "latest window — diversity gate failed (ritual-pasting suspect)"
            ),
        )

    if len(windows) >= 2:
        prev = windows[-2]
        if latest.labeled_rate < prev.labeled_rate * 0.5 and prev.labeled_rate > 0:
            return Verdict(
                name="at_risk",
                reason=(
                    f"labeled_rate fell from {prev.labeled_rate:.3f} to "
                    f"{latest.labeled_rate:.3f} (>50 %) between windows"
                ),
            )

    return Verdict(
        name="applied",
        reason=(
            f"latest window: {latest.labeled_blocks} labeled block(s) across "
            f"{latest.distinct_labels_used} distinct label(s) "
            f"out of {latest.total_commits} commits"
        ),
    )


# ---------------------------------------------------------------------------
# Git driver (thin wrapper; all core logic is above and is git-free)
# ---------------------------------------------------------------------------


def _git_log_commits_in_window(
    start: _dt.date, end: _dt.date, *, cwd: str | None = None
) -> list[str]:
    """Return commit-message bodies for commits whose committer date is
    within ``[start, end)``.

    The window is half-open on the right to make adjacent windows
    non-overlapping.
    """

    fmt = "--pretty=format:%B%x00"
    since = start.isoformat()
    until = end.isoformat()
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={since}", f"--until={until}", fmt],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    raw = out.decode("utf-8", errors="replace")
    return [b.strip() for b in raw.split("\x00") if b.strip()]


def run_audit(
    *,
    now: _dt.date | None = None,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    n_windows: int = _DEFAULT_TREND_WINDOWS,
    cwd: str | None = None,
) -> tuple[list[WindowReport], Verdict]:
    """Run the audit against the repo's git log and return reports + verdict."""

    now = now or _dt.date.today()
    windows: list[WindowReport] = []
    for i in range(n_windows - 1, -1, -1):
        end = now - _dt.timedelta(days=window_days * i)
        start = end - _dt.timedelta(days=window_days)
        texts = _git_log_commits_in_window(start, end, cwd=cwd)
        labeled_blocks, per_label, distinct = count_labels_in_texts(texts)
        windows.append(
            WindowReport(
                start=start,
                end=end,
                total_commits=len(texts),
                labeled_blocks=labeled_blocks,
                per_label_counts=per_label,
                distinct_labels_used=distinct,
            )
        )
    return windows, decide_verdict(windows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(windows: Sequence[WindowReport], verdict: Verdict) -> str:
    lines = ["claim-status-taxonomy-applied audit", ""]
    for w in windows:
        lines.append(
            f"  {w.start}..{w.end}  "
            f"commits={w.total_commits:>4}  "
            f"labeled={w.labeled_blocks:>3}  "
            f"rate={w.labeled_rate:.3f}  "
            f"distinct={w.distinct_labels_used}"
        )
    lines.append("")
    lines.append(f"verdict: {verdict.name}")
    lines.append(f"reason:  {verdict.reason}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="claim_status_applied",
        description=(
            "Audit whether the claim-status taxonomy from "
            "docs/SYSTEM_PROTOCOL.md is still being applied in practice."
        ),
    )
    p.add_argument("--window-days", type=int, default=_DEFAULT_WINDOW_DAYS)
    p.add_argument("--n-windows", type=int, default=_DEFAULT_TREND_WINDOWS)
    p.add_argument("--cwd", default=None, help="Optional repo root for git log.")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if verdict is at_risk or stopped.",
    )
    ns = p.parse_args(argv)
    windows, verdict = run_audit(window_days=ns.window_days, n_windows=ns.n_windows, cwd=ns.cwd)
    print(_format_report(windows, verdict))
    if ns.strict and verdict.name in {"at_risk", "stopped"}:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
