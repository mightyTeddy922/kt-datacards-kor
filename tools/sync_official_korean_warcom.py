#!/usr/bin/env python3
"""Run the latest upstream pipeline against official Korean WarCom PDFs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(cmd: list[str], env: dict[str, str]) -> None:
    print("> " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync official Korean WarCom rules into latest TTS outputs")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--teams", help="Comma-separated team slugs")
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument(
        "--archive-root",
        action="append",
        default=[],
        help="Team archive root(s) used for English full-rules fallback when Korean only has online_rules",
    )
    parser.add_argument("--recent", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--repo", default=os.environ.get("KT_GITHUB_REPO", "mightyTeddy922/kt-datacards-kor"))
    args = parser.parse_args()

    env = os.environ.copy()
    env["KT_WARCOM_LOCALE"] = "ko-kr"
    env["KT_GITHUB_REPO"] = args.repo
    env["KT_DATACARDS_URL_BRANCH"] = args.branch
    env["KT_DATACARDS_URL_BASE"] = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}/output"
    archive_roots = [str(Path(root).resolve()) for root in args.archive_root]
    default_archive_root = ROOT / "layers" / "archive"
    if default_archive_root.exists():
        archive_roots.append(str(default_archive_root.resolve()))
    if archive_roots:
        env["KT_WARCOM_ARCHIVE_ROOTS"] = os.pathsep.join(dict.fromkeys(archive_roots))

    common = [sys.executable, "-m", "pipeline.main", "--source", "warcom", "--jobs", str(args.jobs)]
    if args.teams:
        common.extend(["--teams", args.teams])
    if args.recent:
        common.append("--recent")
    if args.force:
        common.append("--force")

    run_step(common, env)

    if not args.skip_verify:
        verify_cmd = [sys.executable, "tools/verify_official_korean_warcom.py", "--branch", args.branch, "--repo", args.repo]
        if args.teams:
            verify_cmd.extend(["--teams", args.teams])
        run_step(verify_cmd, env)

    print("Official Korean WarCom sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
