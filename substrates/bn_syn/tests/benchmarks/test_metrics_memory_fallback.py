from __future__ import annotations

import importlib

from benchmarks import metrics


def test_process_rss_mb_fallback_without_psutil(monkeypatch) -> None:
    monkeypatch.setattr(metrics.importlib.util, "find_spec", lambda _: None)

    class FakeUsage:
        ru_maxrss = 4096.0

    monkeypatch.setattr(metrics.resource, "getrusage", lambda _: FakeUsage())
    monkeypatch.setattr(metrics.os, "name", "posix")

    rss_mb = metrics._process_rss_mb()

    assert rss_mb == 4.0


def test_process_rss_mb_uses_psutil_when_available(monkeypatch) -> None:
    class FakeProcess:
        def memory_info(self):
            return type("Mem", (), {"rss": 8 * 1024 * 1024})()

    fake_psutil = type("FakePsutil", (), {"Process": lambda self, _pid: FakeProcess()})()

    monkeypatch.setattr(metrics.importlib.util, "find_spec", lambda _: object())
    monkeypatch.setattr(importlib, "import_module", lambda _: fake_psutil)

    rss_mb = metrics._process_rss_mb()

    assert rss_mb == 8.0
