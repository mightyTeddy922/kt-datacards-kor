from __future__ import annotations

import argparse
import os
from pathlib import Path

UPSTREAM_REPO_ROOT = "https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main"
TARGET_REPO_ROOT = os.environ.get(
    "KT_DATACARDS_REPO_ROOT",
    "https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/{branch}",
).format(branch=os.environ.get("KT_DATACARDS_URL_BRANCH", "main"))


def _rewrite_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = text.replace(UPSTREAM_REPO_ROOT, TARGET_REPO_ROOT)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite generated TTS JSON files to use the current fork raw GitHub root."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="optional file or directory paths to rewrite (default: output)",
    )
    args = parser.parse_args()

    roots = [Path(p) for p in args.paths] if args.paths else [Path("output")]
    changed = 0
    scanned = 0

    for root in roots:
        if root.is_file():
            targets = [root]
        else:
            targets = sorted(root.rglob("*.json"))
        for path in targets:
            scanned += 1
            if _rewrite_file(path):
                changed += 1

    print(f"retargeted {changed} of {scanned} json files to {TARGET_REPO_ROOT}")


if __name__ == "__main__":
    main()
