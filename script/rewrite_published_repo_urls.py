#!/usr/bin/env python3
"""Rewrite published raw GitHub URLs in checked-in JSON artifacts to this repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.repo_urls import repo_base_url  # noqa: E402

RAW_URL_PATTERN = re.compile(r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/")


def rewrite_text(text: str, base_url: str) -> str:
    return RAW_URL_PATTERN.sub(f"{base_url}/", text)


def rewrite_json_file(path: Path, base_url: str) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = rewrite_text(original, base_url)
    if updated == original:
        return False

    try:
        parsed = json.loads(updated)
        path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite published JSON URLs to the current repository")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--branch", default="main")
    parser.add_argument(
        "--include-tts-objects",
        action="store_true",
        help="Also rewrite checked-in JSON files under tts_objects/",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    base_url = repo_base_url(project_root=project_root, branch=args.branch)

    candidates = [
        project_root / "output_v2" / "datacards-urls.json",
        project_root / "output_v2" / "tts-card-boxes.json",
        project_root / "output_v2" / "tts-metadata.json",
        project_root / "output_v2" / "tts-manager.json",
    ]

    if args.include_tts_objects:
        candidates.extend((project_root / "tts_objects").rglob("*.json"))

    changed = 0
    scanned = 0
    for path in candidates:
        if not path.exists():
            continue
        scanned += 1
        if rewrite_json_file(path, base_url):
            changed += 1
            print(f"Rewrote: {path}")

    print(f"Scanned {scanned} file(s), updated {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
