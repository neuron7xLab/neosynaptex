#!/usr/bin/env python3
"""Check external link reachability with policy exclusions and retries."""

from __future__ import annotations

import argparse
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from governance_contract import EXTERNAL_LINK_EXCLUDE_HOSTS


UA = "kriterion-governance-link-check/1.0"


def extract_links(text: str, md: bool) -> list[str]:
    if md:
        return re.findall(r"\[[^\]]*\]\((https?://[^)\s]+)\)", text)
    return re.findall(r"(?:href|src)=['\"](https?://[^'\"]+)['\"]", text, flags=re.IGNORECASE)


def is_excluded(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == h or host.endswith(f".{h}") for h in EXTERNAL_LINK_EXCLUDE_HOSTS)


def check_url(url: str, timeout: float = 8.0, retries: int = 2) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                code = getattr(r, "status", 200)
                if 200 <= code < 400:
                    return True, str(code)
                return False, f"HTTP_{code}"
        except urllib.error.HTTPError as e:
            if e.code in {403, 405}:
                # fallback GET for servers that reject HEAD
                try:
                    req_get = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
                    with urllib.request.urlopen(req_get, timeout=timeout) as r:
                        code = getattr(r, "status", 200)
                        if 200 <= code < 400:
                            return True, f"GET_{code}"
                        return False, f"GET_HTTP_{code}"
                except Exception as exc:  # pragma: no cover
                    if i == retries:
                        return False, f"GET_ERR_{type(exc).__name__}"
            if i == retries:
                return False, f"HTTP_ERR_{e.code}"
        except Exception as exc:  # pragma: no cover
            if i == retries:
                return False, type(exc).__name__
        time.sleep(0.5 * (i + 1))
    return False, "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = [*root.glob("*.md"), *root.glob("*.html"), *root.glob("docs/*.md"), *root.glob("execution/*.md")]

    urls: set[str] = set()
    for p in files:
        text = p.read_text(encoding="utf-8")
        urls.update(extract_links(text, p.suffix.lower() == ".md"))

    failures: list[str] = []
    checked = 0
    for url in sorted(urls):
        if is_excluded(url):
            continue
        ok, reason = check_url(url)
        checked += 1
        if not ok:
            failures.append(f"EXTERNAL_BROKEN | {url} | {reason}")

    if failures:
        print("\n".join(failures))
        return 2
    print(f"EXTERNAL_LINK_REACHABILITY_OK checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
