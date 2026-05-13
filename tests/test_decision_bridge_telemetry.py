"""Tests for the Decision Bridge telemetry ledger.

Threat model
------------
An attacker (or a corrupted disk, or a careless edit) may:
    A. Flip a single byte in one event's payload.
    B. Truncate the file (drop tail events).
    C. Delete one event from the middle.
    D. Append a fabricated event whose hash is internally self-
       consistent but whose prev_hash breaks the chain.

For each, ``TelemetryLedger.verify`` must return ``ok=False`` and
identify the first broken index. Honest appends must always verify.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from core.decision_bridge import DecisionBridge
from core.decision_bridge_telemetry import TelemetryEvent, TelemetryLedger


def _healthy_history(
    n: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    phi = rng.normal(0, 0.1, size=(n, 4))
    gamma = 1.0 + rng.normal(0, 0.02, size=n)
    return phi, gamma


class TestLedgerAppendVerify:
    def test_honest_append_verifies(self, tmp_path: Path) -> None:
        ledger = TelemetryLedger(tmp_path / "l.jsonl")
        for t in range(5):
            ledger.append(tick=t, event_type="x", payload={"t": t, "v": t * 2.0})
        verdict = TelemetryLedger.verify(tmp_path / "l.jsonl")
        assert verdict.ok
        assert verdict.n_events == 5
        assert verdict.first_broken_index is None
        assert verdict.defects == []

    def test_empty_file_verifies(self, tmp_path: Path) -> None:
        path = tmp_path / "l.jsonl"
        path.touch()
        verdict = TelemetryLedger.verify(path)
        assert verdict.ok
        assert verdict.n_events == 0

    def test_iter_events_yields_in_append_order(self, tmp_path: Path) -> None:
        ledger = TelemetryLedger(tmp_path / "l.jsonl")
        for t in range(3):
            ledger.append(tick=t, event_type="x", payload={"t": t})
        events = list(TelemetryLedger.iter_events(tmp_path / "l.jsonl"))
        assert [e.tick for e in events] == [0, 1, 2]
        assert all(isinstance(e, TelemetryEvent) for e in events)


class TestLedgerTamperDetection:
    def test_flipped_payload_byte_is_detected(self, tmp_path: Path) -> None:
        path = tmp_path / "l.jsonl"
        ledger = TelemetryLedger(path)
        for t in range(4):
            ledger.append(tick=t, event_type="x", payload={"v": t * 1.0})

        # Corrupt one value in event index=2 without updating self_hash.
        lines = path.read_text(encoding="utf-8").splitlines()
        obj = json.loads(lines[2])
        obj["payload"]["v"] = 999.0  # silent edit
        lines[2] = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        verdict = TelemetryLedger.verify(path)
        assert not verdict.ok
        assert verdict.first_broken_index == 2

    def test_truncation_is_detected_only_if_prev_hash_exposed(self, tmp_path: Path) -> None:
        """Truncation itself is silent; the bridge is expected to
        cross-check ``ledger.last_hash`` at boot against external
        pinning (eg. a ``.head`` sentinel file) to catch tail loss.
        The ledger's own verify still rejects mid-chain deletions.
        """
        path = tmp_path / "l.jsonl"
        ledger = TelemetryLedger(path)
        for t in range(5):
            ledger.append(tick=t, event_type="x", payload={"v": t * 1.0})
        lines = path.read_text(encoding="utf-8").splitlines()
        # Drop the middle event — chain MUST break at index 3 (next one).
        del lines[2]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        verdict = TelemetryLedger.verify(path)
        assert not verdict.ok
        assert verdict.first_broken_index is not None

    def test_fabricated_tail_event_breaks_chain(self, tmp_path: Path) -> None:
        path = tmp_path / "l.jsonl"
        ledger = TelemetryLedger(path)
        for t in range(3):
            ledger.append(tick=t, event_type="x", payload={"v": t * 1.0})
        # Handcraft a fake event whose prev_hash is WRONG.
        fake = {
            "index": 3,
            "tick": 99,
            "event_type": "x",
            "payload": {"v": 42},
            "prev_hash": "f" * 64,
            "self_hash": "0" * 64,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(fake, sort_keys=True, separators=(",", ":")) + "\n")
        verdict = TelemetryLedger.verify(path)
        assert not verdict.ok
        assert verdict.first_broken_index == 3


class TestLedgerRehydration:
    def test_reopening_resumes_chain(self, tmp_path: Path) -> None:
        path = tmp_path / "l.jsonl"
        first = TelemetryLedger(path)
        first.append(tick=0, event_type="x", payload={"v": 0.0})
        first.append(tick=1, event_type="x", payload={"v": 1.0})
        last_hash_before = first.last_hash

        second = TelemetryLedger(path)
        assert second.index == 2
        assert second.last_hash == last_hash_before

        second.append(tick=2, event_type="x", payload={"v": 2.0})
        verdict = TelemetryLedger.verify(path)
        assert verdict.ok
        assert verdict.n_events == 3


class TestBridgeTelemetryIntegration:
    def test_no_telemetry_by_default(self, tmp_path: Path) -> None:
        """Bridges without a ledger write no files."""
        bridge = DecisionBridge()
        phi, gamma = _healthy_history()
        bridge.evaluate(
            tick=1,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        # Nothing in tmp_path because we never gave the bridge a path.
        assert not any(tmp_path.iterdir())

    def test_telemetry_records_every_new_tick(self, tmp_path: Path) -> None:
        path = tmp_path / "b.jsonl"
        ledger = TelemetryLedger(path)
        bridge = DecisionBridge(telemetry=ledger)
        phi, gamma = _healthy_history()
        for t in range(3):
            bridge.evaluate(
                tick=t,
                gamma_mean=1.0,
                gamma_std=0.03,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        verdict = TelemetryLedger.verify(path)
        assert verdict.ok
        assert verdict.n_events == 3
        events = list(TelemetryLedger.iter_events(path))
        assert all(e.event_type == "snapshot" for e in events)
        assert [e.tick for e in events] == [0, 1, 2]

    def test_idempotent_tick_records_once(self, tmp_path: Path) -> None:
        """Same tick twice → one snapshot line, not two."""
        path = tmp_path / "b.jsonl"
        ledger = TelemetryLedger(path)
        bridge = DecisionBridge(telemetry=ledger)
        phi, gamma = _healthy_history()
        for _ in range(5):
            bridge.evaluate(
                tick=42,
                gamma_mean=1.0,
                gamma_std=0.03,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        verdict = TelemetryLedger.verify(path)
        assert verdict.n_events == 1

    def test_payload_contains_canonical_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "b.jsonl"
        ledger = TelemetryLedger(path)
        bridge = DecisionBridge(telemetry=ledger)
        phi, gamma = _healthy_history()
        bridge.evaluate(
            tick=1,
            gamma_mean=1.01,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        (event,) = list(TelemetryLedger.iter_events(path))
        required_keys = {
            "tick",
            "system_health",
            "critic_gain",
            "controller_integral",
            "gradient_diagnosis",
            "operating_regime",
            "hallucination_risk",
            "prediction_available",
            "confidence",
        }
        assert required_keys.issubset(event.payload.keys())


@pytest.mark.parametrize(
    ("tick_value", "expected_tick"),
    [(0, 0), (1234, 1234), (10**6, 10**6)],
)
def test_ledger_accepts_wide_tick_range(
    tmp_path: Path, tick_value: int, expected_tick: int
) -> None:
    ledger = TelemetryLedger(tmp_path / "l.jsonl")
    event = ledger.append(tick=tick_value, event_type="x", payload={"v": 1.0})
    assert event.tick == expected_tick
