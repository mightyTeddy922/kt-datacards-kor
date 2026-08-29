#!/usr/bin/env python3
"""Verify latest-upstream outputs for the official Korean/fallback workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify official Korean WarCom output")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--repo", default="mightyTeddy922/kt-datacards-kor")
    parser.add_argument("--teams")
    args = parser.parse_args()

    expected_prefix = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}/output"
    wanted = set(args.teams.split(",")) if args.teams else None
    issues: list[str] = []

    summary_file = ROOT / "output" / "team-urls.json"
    manager_file = ROOT / "output" / "_generic-tts-objects" / "Kill Team Card Boxes.json"
    spawner_file = ROOT / "output" / "_generic-tts-objects" / "Kill Team Spawner.json"

    for path in (summary_file, manager_file, spawner_file):
        if not path.exists():
            issues.append(f"Missing required file: {path}")

    teams = []
    if summary_file.exists():
        summary = load_json(summary_file)
        entries = summary.values() if isinstance(summary, dict) else summary
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            team = entry.get("team")
            if wanted and team not in wanted:
                continue
            teams.append(team)
            box = entry.get("box") or {}
            url = str(box.get("url") or "")
            if not url.startswith(expected_prefix):
                issues.append(f"Unexpected team URL for {team}: {url}")

    if manager_file.exists():
        manager = load_json(manager_file)
        if manager.get("ObjectStates"):
            contained = manager.get("ObjectStates", [{}])[0].get("ContainedObjects", [])
        else:
            contained = manager.get("ContainedObjects", [])
        names = [obj.get("Nickname", "") for obj in contained]
        if not any(name in {"Exodite Dragon Masters", "Exodite Dragon Masters Cards"} for name in names):
            issues.append("Manager bag does not contain Exodite Dragon Masters")

    if spawner_file.exists():
        spawner_text = spawner_file.read_text(encoding="utf-8")
        if args.repo not in spawner_text:
            issues.append("Spawner is not pointing at the target repository")

    print(f"Expected output prefix: {expected_prefix}")
    print(f"Verified teams: {len(teams)}")
    if issues:
        print("\nVerification failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("\nVerification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
