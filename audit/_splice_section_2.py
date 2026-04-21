"""Splice new §2 into manuscript/arxiv_submission.tex. One-shot."""
from __future__ import annotations

from pathlib import Path

TARGET = Path("manuscript/arxiv_submission.tex")
NEW_BLOCK = Path("audit/_new_section_2.tex")

START_LINE = "% ===================================================================="
SECTION_HDR = r"\section{Theoretical Framework}"
END_SECTION_HDR = r"\section{Methods}"


def main() -> None:
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find line of \section{Theoretical Framework}
    hdr_idx = next(i for i, L in enumerate(lines) if L.strip() == SECTION_HDR)
    # Preamble separator: the comment line directly above \section{Theoretical Framework}
    preamble_end = hdr_idx  # content BEFORE this stays
    # Seek preceding separator (line starting with "% ====") to replace that too
    # Actually we keep everything up to and including the line(s) before preamble_end.
    # The comment separator at hdr_idx-1 is fine to drop since new block starts with its own.
    if lines[hdr_idx - 1].startswith("% ===="):
        preamble_end = hdr_idx - 1

    # Find line of \section{Methods}
    meth_idx = next(i for i, L in enumerate(lines) if L.strip() == END_SECTION_HDR)
    # The comment separator at meth_idx-1 is what bounds §2. Keep everything FROM meth_idx-1 onward
    # (our new block ends with a blank line; Methods separator stays intact).
    methods_start = meth_idx
    if lines[meth_idx - 1].startswith("% ===="):
        methods_start = meth_idx - 1

    new_block = NEW_BLOCK.read_text(encoding="utf-8")
    if not new_block.endswith("\n"):
        new_block += "\n"

    spliced = "".join(lines[:preamble_end]) + new_block + "".join(lines[methods_start:])
    TARGET.write_text(spliced, encoding="utf-8")

    print(f"spliced: preamble_end={preamble_end}  methods_start={methods_start}")
    print(f"old length={len(lines)} lines  new length={spliced.count(chr(10))} lines")


if __name__ == "__main__":
    main()
