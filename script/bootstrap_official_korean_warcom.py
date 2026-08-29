#!/usr/bin/env python3
"""Bootstrap a local Python runtime for the official Korean WarCom pipeline."""

from __future__ import annotations

import json
import argparse
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP_SITE = PROJECT_ROOT / "work" / ".bootstrap-site"
BOOTSTRAP_CACHE = PROJECT_ROOT / "work" / ".bootstrap-cache"
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/{version}/json"


def run_bootstrap_packages() -> None:
    cmd = [
        sys.executable,
        "script/tools/bootstrap_site_packages.py",
        "requests",
        "pyyaml",
        "beautifulsoup4",
        "pillow",
        "pypdf2",
        "numpy",
        "opencv-python",
        "playwright",
        "--target",
        str(BOOTSTRAP_SITE),
        "--cache-dir",
        str(BOOTSTRAP_CACHE),
    ]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def install_exact_wheel(package: str, version: str, filename: str) -> None:
    BOOTSTRAP_SITE.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_CACHE.mkdir(parents=True, exist_ok=True)

    payload = json.load(urllib.request.urlopen(PYPI_JSON_URL.format(name=package, version=version)))
    url = next(item["url"] for item in payload["urls"] if item["filename"] == filename)
    wheel_path = BOOTSTRAP_CACHE / filename
    if not wheel_path.exists():
        wheel_path.write_bytes(urllib.request.urlopen(url).read())
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(BOOTSTRAP_SITE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a local Python runtime for the official Korean WarCom pipeline"
    )
    parser.parse_args()

    run_bootstrap_packages()
    install_exact_wheel("PyMuPDF", "1.23.8", "PyMuPDF-1.23.8-cp312-none-win_amd64.whl")
    install_exact_wheel("PyMuPDFb", "1.23.7", "PyMuPDFb-1.23.7-py3-none-win_amd64.whl")

    print(f"Bootstrapped WarCom runtime into {BOOTSTRAP_SITE}")
    print("The sync script will automatically use this runtime when it is present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
