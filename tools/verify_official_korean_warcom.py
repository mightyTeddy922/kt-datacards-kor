#!/usr/bin/env python3
"""Verify latest-upstream outputs for the official Korean/fallback workflow."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils.official_korean_team_rules import OFFICIAL_KOREAN_TEAM_RULES


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_like = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_like = (
        ascii_like.strip()
        .lower()
        .replace("&", " and ")
        .replace("’", "")
        .replace("'", "")
        .replace("‑", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace(":", " ")
        .replace("/", " ")
    )
    while "  " in ascii_like:
        ascii_like = ascii_like.replace("  ", " ")
    return ascii_like.replace(" ", "-")


def canonical_compare_name(value: str) -> str:
    slug = slugify_name(value)
    return slug.removesuffix("-card1").removesuffix("-card2").removesuffix("-card3")


def canonical_datacard_names(team: str) -> set[str]:
    path = ROOT / "layers" / "kt-app" / "classified" / team / "structure.json"
    if not path.exists():
        return set()
    data = load_json(path)
    return {
        canonical_compare_name(str(entry.get("name") or ""))
        for entry in data.get("datacards", [])
        if str(entry.get("name") or "").strip()
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Verify official Korean WarCom output")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--repo", default="mightyTeddy922/kt-datacards-kor")
    parser.add_argument("--teams")
    args = parser.parse_args()

    expected_prefix = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}/output"
    wanted = set(args.teams.split(",")) if args.teams else None
    issues: list[str] = []
    translated = sorted(
        team for team, meta in OFFICIAL_KOREAN_TEAM_RULES.items() if bool(meta.get("translated"))
    )
    fallback = sorted(
        team for team, meta in OFFICIAL_KOREAN_TEAM_RULES.items() if not bool(meta.get("translated"))
    )

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

            object_file = ROOT / "output" / team / f"{team}-object-urls.json"
            if not object_file.exists():
                issues.append(f"Missing team object URL file: {object_file}")
                continue

            object_data = load_json(object_file)
            objects = object_data.get("objects", [])
            datacards = [obj for obj in objects if obj.get("type") == "datacards"]
            names = {
                canonical_compare_name(str(obj.get("name") or ""))
                for obj in datacards
                if str(obj.get("name") or "")
            }

            if team in translated:
                if not datacards:
                    issues.append(f"{team}: no datacards found in object URL manifest")
                canonical = canonical_datacard_names(team)
                if canonical and names != canonical:
                    missing = sorted(canonical - names)
                    extra = sorted(names - canonical)
                    if missing:
                        issues.append(f"{team}: missing canonical datacards: {', '.join(missing[:8])}")
                    if extra:
                        issues.append(f"{team}: unexpected datacards: {', '.join(extra[:8])}")
                for obj in datacards:
                    face = str(obj.get("face_url") or "")
                    back = str(obj.get("back_url") or "")
                    if not face.startswith(expected_prefix):
                        issues.append(f"{team}: translated datacard face URL not in target repo: {face}")
                        break
                    if back and not back.startswith(expected_prefix):
                        issues.append(f"{team}: translated datacard back URL not in target repo: {back}")
                        break
                    name = str(obj.get("name") or "")
                    normalized_name = canonical_compare_name(name)
                    if not normalized_name or name.startswith("-") or normalized_name == "unknown":
                        issues.append(f"{team}: suspicious translated datacard name: {name!r}")
                        break
            elif team in fallback:
                if not datacards:
                    issues.append(f"{team}: no datacards found in fallback object URL manifest")

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
    print(f"Official Korean teams: {len(translated)}")
    print(f"Official fallback teams: {len(fallback)}")
    if issues:
        print("\nVerification failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("\nVerification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
