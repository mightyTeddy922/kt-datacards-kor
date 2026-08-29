"""Download and install Python wheels into a local site-packages directory.

This bypasses `pip install` for environments where pip can read from the
network but fails while creating its temporary wheel metadata files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import sysconfig
import urllib.request
import zipfile
from pathlib import Path

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"
DEFAULT_TARGET = Path(".bootstrap-site")
DEFAULT_CACHE = Path(".bootstrap-cache")

PROJECT_PRESETS = {
    "warcom-scrape": [
        "requests",
        "pyyaml",
        "playwright",
        "beautifulsoup4",
    ],
    "warcom-core": [
        "requests",
        "pyyaml",
        "playwright",
        "beautifulsoup4",
        "pillow",
        "pymupdf",
        "pypdf2",
        "numpy",
        "opencv-python",
    ],
}


def normalize_name(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def current_tags() -> tuple[str, str]:
    version = sys.version_info
    py_tag = f"cp{version.major}{version.minor}"
    platform = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    return py_tag, platform


def _cpython_tag_version(tag: str) -> int | None:
    match = re.fullmatch(r"cp(\d{2,})", tag)
    return int(match.group(1)) if match else None


def is_compatible_wheel(filename: str, py_tag: str, platform_tag: str) -> bool:
    if not filename.endswith(".whl"):
        return False

    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return False

    wheel_py_tag, wheel_abi_tag, wheel_platform_tag = parts[-3:]
    py_tags = wheel_py_tag.split(".")
    abi_tags = wheel_abi_tag.split(".")
    platform_tags = wheel_platform_tag.split(".")

    current_cp = _cpython_tag_version(py_tag)
    abi3_compatible = False
    if "abi3" in abi_tags and current_cp is not None:
        for candidate in py_tags:
            candidate_cp = _cpython_tag_version(candidate)
            if candidate_cp is not None and candidate_cp <= current_cp:
                abi3_compatible = True
                break

    py_ok = py_tag in py_tags or "py3" in py_tags or "py2.py3" in wheel_py_tag or abi3_compatible
    abi_ok = "abi3" in abi_tags or "none" in abi_tags or py_tag in abi_tags
    platform_ok = "any" in platform_tags or platform_tag in platform_tags

    return py_ok and abi_ok and platform_ok


def score_wheel(filename: str, py_tag: str, platform_tag: str) -> tuple[int, int, int]:
    parts = filename[:-4].split("-")
    wheel_py_tag, wheel_abi_tag, wheel_platform_tag = parts[-3:]
    py_score = 0 if py_tag == wheel_py_tag else 1
    abi_score = 0 if py_tag == wheel_abi_tag else (1 if "abi3" in wheel_abi_tag else 2)
    platform_score = 0 if wheel_platform_tag == platform_tag else 1
    return py_score, abi_score, platform_score


def fetch_json(package: str) -> dict:
    with urllib.request.urlopen(PYPI_JSON_URL.format(package=package)) as response:
        return json.load(response)


def choose_wheel(package: str, version: str | None, py_tag: str, platform_tag: str) -> tuple[str, str]:
    payload = fetch_json(package)
    releases = payload["releases"]
    if version:
        candidates = releases.get(version, [])
        if not candidates:
            raise RuntimeError(f"No release found for {package}=={version}")
    else:
        version = payload["info"]["version"]
        candidates = releases.get(version, [])

    wheels: list[tuple[tuple[int, int, int], str, str]] = []
    for file_info in candidates:
        filename = file_info.get("filename", "")
        if is_compatible_wheel(filename, py_tag, platform_tag):
            wheels.append((score_wheel(filename, py_tag, platform_tag), filename, file_info["url"]))

    if not wheels:
        raise RuntimeError(f"No compatible wheel found for {package} ({py_tag}, {platform_tag})")

    wheels.sort(key=lambda item: item[0])
    _, filename, url = wheels[0]
    return filename, url


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, open(dest, "wb") as out:
        out.write(response.read())


def install_wheel(wheel_path: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(target)


def parse_requirements(requires_dist: list[str] | None) -> list[str]:
    result: list[str] = []
    for entry in requires_dist or []:
        requirement, _, marker = entry.partition(";")
        requirement = requirement.strip()
        marker = marker.strip().lower()
        if not requirement:
            continue
        if marker and 'extra ==' in marker:
            continue
        match = re.match(r"^\s*([A-Za-z0-9_.-]+)", requirement)
        package = match.group(1) if match else ""
        package = package.split("[", 1)[0].strip()
        if package:
            result.append(normalize_name(package))
    return result


def bootstrap(packages: list[str], target: Path, cache_dir: Path) -> None:
    py_tag, platform_tag = current_tags()
    queue = [normalize_name(pkg) for pkg in packages]
    root_packages = set(queue)
    seen: set[str] = set()

    while queue:
        package = queue.pop(0)
        if package in seen:
            continue
        print(f"[bootstrap] resolving {package}")
        try:
            payload = fetch_json(package)
            version = payload["info"]["version"]
            filename, url = choose_wheel(package, version, py_tag, platform_tag)
            wheel_path = cache_dir / filename
            if not wheel_path.exists():
                print(f"[bootstrap] downloading {filename}")
                download(url, wheel_path)
            else:
                print(f"[bootstrap] cached {filename}")

            install_wheel(wheel_path, target)
            seen.add(package)
            for dep in parse_requirements(payload["info"].get("requires_dist")):
                if dep not in seen:
                    queue.append(dep)
        except Exception as exc:
            if package in root_packages:
                raise
            print(f"[bootstrap] warning: skipping optional dependency {package}: {exc}")

    print(f"[bootstrap] installed {len(seen)} package(s) into {target}")
    print(f"[bootstrap] set PYTHONPATH={target.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap local site-packages from PyPI wheels")
    parser.add_argument("packages", nargs="*", help="Packages to install")
    parser.add_argument("--preset", choices=sorted(PROJECT_PRESETS), help="Install a predefined package set")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="Target directory for site-packages")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help="Directory to cache wheels")
    args = parser.parse_args()

    packages = list(args.packages)
    if args.preset:
        packages.extend(PROJECT_PRESETS[args.preset])
    if not packages:
        parser.error("Provide packages or --preset")

    bootstrap(packages, target=args.target, cache_dir=args.cache_dir)


if __name__ == "__main__":
    main()
