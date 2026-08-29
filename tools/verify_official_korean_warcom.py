#!/usr/bin/env python3
"""Verify generated TTS outputs follow the official Korean/fallback routing."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils.official_korean_team_rules import OFFICIAL_KOREAN_TEAM_RULES

UPSTREAM_PREFIX = "https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main/output"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_url(url: str) -> str:
    return (url or "").split("?", 1)[0]


def url_signature(url: str) -> str:
    clean = strip_url(url)
    marker = "/output/"
    idx = clean.lower().find(marker)
    if idx >= 0:
        return clean[idx:].lower()
    return clean.lower()


def load_team_urls() -> dict[str, Any]:
    summary = load_json(ROOT / "output" / "team-urls.json")
    if isinstance(summary, dict):
        return summary
    result: dict[str, Any] = {}
    for entry in summary:
        if isinstance(entry, dict) and entry.get("team"):
            result[str(entry["team"])] = entry
    return result


def box_filename_from_summary(team_slug: str) -> str | None:
    summary = load_team_urls()
    entry = summary.get(team_slug) or {}
    box = entry.get("box") or {}
    url = str(box.get("url") or "")
    if not url:
        return None
    return Path(urllib.parse.unquote(strip_url(url))).name


def load_generated_team_box(team_slug: str) -> dict[str, Any]:
    team_dir = ROOT / "output" / team_slug / "tts_objects"
    filename = box_filename_from_summary(team_slug)
    if filename:
        path = team_dir / filename
        if path.exists():
            return load_json(path)
    candidates = sorted(path for path in team_dir.glob("*.json") if not path.name.endswith(" Box.json"))
    if not candidates:
        raise FileNotFoundError(f"No generated team box JSON for {team_slug}")
    return load_json(candidates[0])


def collect_box_decks(data: dict[str, Any]) -> list[dict[str, str]]:
    root = data.get("ObjectStates", [data])[0] if isinstance(data, dict) else data
    children = root.get("ContainedObjects") if isinstance(root, dict) else []
    result: list[dict[str, str]] = []
    for node in children or []:
        if not isinstance(node, dict):
            continue
        custom_deck = node.get("CustomDeck")
        if not isinstance(custom_deck, dict) or not custom_deck:
            continue
        first = next(iter(custom_deck.values()))
        if not isinstance(first, dict):
            continue
        result.append(
            {
                "nickname": str(node.get("Nickname") or ""),
                "face_url": str(first.get("FaceURL") or ""),
                "back_url": str(first.get("BackURL") or ""),
            }
        )
    return result


def collect_manifest_signatures(team_slug: str) -> set[tuple[str, str]]:
    manifest = load_json(ROOT / "output" / team_slug / f"{team_slug}-object-urls.json")
    signatures: set[tuple[str, str]] = set()
    for obj in manifest.get("objects", []):
        face = str(obj.get("face_url") or "")
        if not face:
            continue
        signatures.add((url_signature(face), url_signature(str(obj.get("back_url") or ""))))
    return signatures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify official Korean routing in generated TTS outputs")
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

    summary = load_team_urls()
    teams = sorted(team for team in summary if not wanted or team in wanted)
    for team in teams:
        entry = summary.get(team) or {}
        box = entry.get("box") or {}
        box_url = str(box.get("url") or "")
        if not box_url.startswith(expected_prefix):
            issues.append(f"{team}: team box URL not in target repo: {box_url}")

        generated_box = load_generated_team_box(team)
        decks = collect_box_decks(generated_box)
        manifest_signatures = collect_manifest_signatures(team)
        if not decks:
            issues.append(f"{team}: no card decks found in generated team box")
            continue

        for deck in decks:
            face = deck["face_url"]
            back = deck["back_url"]
            sig = (url_signature(face), url_signature(back))
            if manifest_signatures and sig not in manifest_signatures:
                issues.append(f"{team}: generated card deck missing from object manifest: {deck['nickname'] or sig[0]}")
            expected = expected_prefix if team in translated else UPSTREAM_PREFIX
            if not face.startswith(expected):
                issues.append(f"{team}: card face URL not in expected repo: {face}")
            if back and not back.startswith(expected):
                issues.append(f"{team}: card back URL not in expected repo: {back}")

    print(f"Expected localized prefix: {expected_prefix}")
    print(f"Expected fallback prefix: {UPSTREAM_PREFIX}")
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
