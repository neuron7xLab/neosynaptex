"""DCVP append-only γ-channel tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from formal.dcvp.channel import ChannelTampered, GammaChannel


def test_channel_roundtrip_verifies(tmp_path: Path) -> None:
    ch = GammaChannel(tmp_path / "ch.ndjson")
    for t in range(10):
        ch.append(t, 1.0 + 0.01 * t)
    assert ch.length == 10
    assert ch.verify() is True
    samples = GammaChannel(tmp_path / "ch.ndjson").read()
    assert len(samples) == 10
    assert [s.t for s in samples] == list(range(10))


def test_channel_tamper_detected(tmp_path: Path) -> None:
    path = tmp_path / "ch.ndjson"
    ch = GammaChannel(path)
    for t in range(5):
        ch.append(t, float(t))
    # Mutate a middle line in-place — should break the chain.
    lines = path.read_text().splitlines()
    lines[2] = lines[2].replace('"gamma": 2.0', '"gamma": 99.0')
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ChannelTampered):
        GammaChannel(path).read()


def test_channel_reopen_preserves_chain(tmp_path: Path) -> None:
    path = tmp_path / "ch.ndjson"
    ch1 = GammaChannel(path)
    for t in range(3):
        ch1.append(t, float(t))
    ch2 = GammaChannel(path)  # reopen
    ch2.append(3, 3.0)
    assert ch2.verify() is True
    samples = ch2.read()
    assert len(samples) == 4
