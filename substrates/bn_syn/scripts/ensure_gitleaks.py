from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

GITLEAKS_VERSION = "8.24.3"
BASE_URL = f"https://github.com/gitleaks/gitleaks/releases/download/v{GITLEAKS_VERSION}"
TOOLS_ROOT = Path(".tools") / "gitleaks" / f"v{GITLEAKS_VERSION}"

ASSET_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("linux", "x86_64"): (
        f"gitleaks_{GITLEAKS_VERSION}_linux_x64.tar.gz",
        "9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c",
    ),
    ("linux", "aarch64"): (
        f"gitleaks_{GITLEAKS_VERSION}_linux_arm64.tar.gz",
        "5f2edbe1f49f7b920f9e06e90759947d3c5dfc16f752fb93aaafc17e9d14cf07",
    ),
    ("darwin", "x86_64"): (
        f"gitleaks_{GITLEAKS_VERSION}_darwin_x64.tar.gz",
        "41c44ae8ad1d6eef57d4526ad0fd67d8129eee9a856f55c2b3b9395fd3d9ec0f",
    ),
    ("darwin", "arm64"): (
        f"gitleaks_{GITLEAKS_VERSION}_darwin_arm64.tar.gz",
        "b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013",
    ),
}


def _platform_key() -> tuple[str, str]:
    os_name = platform.system().lower()
    machine = platform.machine().lower()
    aliases = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64"}
    return os_name, aliases.get(machine, machine)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dst: Path) -> None:
    with urlopen(url, timeout=60) as response, dst.open("wb") as out:
        shutil.copyfileobj(response, out)


def _install_binary() -> Path:
    key = _platform_key()
    if key not in ASSET_MAP:
        known = ", ".join(f"{k[0]}/{k[1]}" for k in sorted(ASSET_MAP))
        raise SystemExit(f"Unsupported platform {key[0]}/{key[1]}; supported: {known}")

    asset_name, expected_sha = ASSET_MAP[key]
    bin_name = "gitleaks.exe" if key[0] == "windows" else "gitleaks"
    binary_path = TOOLS_ROOT / bin_name
    if binary_path.exists():
        return binary_path

    TOOLS_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gitleaks-bootstrap-") as temp_dir:
        archive_path = Path(temp_dir) / asset_name
        _download(f"{BASE_URL}/{asset_name}", archive_path)
        actual_sha = _sha256(archive_path)
        if actual_sha != expected_sha:
            raise SystemExit(
                f"Checksum mismatch for {asset_name}: expected {expected_sha}, got {actual_sha}"
            )

        with tarfile.open(archive_path, "r:gz") as archive:
            member = next((m for m in archive.getmembers() if Path(m.name).name == bin_name), None)
            if member is None:
                raise SystemExit(f"{bin_name} not found in archive: {asset_name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise SystemExit(f"Failed to extract {bin_name} from archive: {asset_name}")
            with binary_path.open("wb") as out:
                shutil.copyfileobj(extracted, out)

    mode = binary_path.stat().st_mode
    binary_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure pinned gitleaks binary is available.")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to gitleaks")
    parsed = parser.parse_args()

    binary = _install_binary()
    version_cmd = [str(binary), "version"]
    print(f"[gitleaks] binary={binary}")
    subprocess.run(version_cmd, check=True)

    cli_args = parsed.args if parsed.args else ["detect", "--redact", "--verbose", "--source=."]
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    cmd = [str(binary), *cli_args]
    print(f"[gitleaks] cmd={' '.join(cmd)}")
    completed = subprocess.run(cmd)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
