from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils.official_korean_team_rules import VERIFIED_DATE

WORKSHOP_JSON = Path(
    r"C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Mods\Workshop\3646032507.json"
)
PATCHED_SAVE_JSON = Path(
    r"C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Saves\KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json"
)
DELIVERABLE_JSON = (
    ROOT / "output" / "_generic-tts-objects" / "KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json"
)
SUMMARY_JSON = ROOT / "output" / "_generic-tts-objects" / "korean-workshop-patch-summary.json"
AUDIT_MD = ROOT / "output" / "_generic-tts-objects" / "korean-workshop-audit.md"

UPSTREAM_REPO = "https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main"
TARGET_REPO = "https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main"
FEATURE_PATTERNS = [
    "Load stats",
    "KTUI",
    "KTUIMiniDatacard",
    'addContextMenuItem("Update"',
    "click_update_single_object",
]
REPRESENTATIVE_TEAMS = ["blades-of-khaine", "chaos-cult", "kasrkin", "angels-of-death"]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def count_feature_patterns(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8-sig")
    return {pattern: text.count(pattern) for pattern in FEATURE_PATTERNS}


def script_repo_counts(data: Any) -> Counter:
    counts: Counter[str] = Counter()
    for node in walk(data):
        if not isinstance(node, dict):
            continue
        script = node.get("LuaScript")
        if not isinstance(script, str) or not script:
            continue
        if TARGET_REPO in script:
            counts["target_repo_scripts"] += 1
        if UPSTREAM_REPO in script:
            counts["upstream_repo_scripts"] += 1
    return counts


def first_matching_box_face_url(team_slug: str) -> str:
    team_file = ROOT / "output" / team_slug / "tts_objects"
    json_files = sorted(team_file.glob("*.json"))
    for path in json_files:
        data = load_json(path)
        contained = data.get("ContainedObjects") or []
        for obj in contained:
            custom_deck = obj.get("CustomDeck")
            if isinstance(custom_deck, dict) and custom_deck:
                first = next(iter(custom_deck.values()))
                if isinstance(first, dict):
                    return str(first.get("FaceURL") or "")
    return ""


def representative_image_sizes() -> list[str]:
    lines: list[str] = []
    for team_slug in REPRESENTATIVE_TEAMS:
        files = sorted((ROOT / "output" / team_slug / "cards").rglob("*-front.jpg"))
        if not files:
            lines.append(f"- `{team_slug}`: no card image found")
            continue
        with Image.open(files[0]) as img:
            lines.append(f"- `{team_slug}`: `{files[0].name}` -> {img.width}x{img.height}")
    return lines


def localized_size_summary(localized_teams: list[str]) -> str:
    sizes: set[str] = set()
    for team_slug in localized_teams:
        files = sorted((ROOT / "output" / team_slug / "cards").rglob("*-front.jpg"))[:3]
        for path in files:
            with Image.open(path) as img:
                sizes.add(f"{img.width}x{img.height}")
    return ", ".join(sorted(sizes))


def build_report() -> str:
    workshop = load_json(WORKSHOP_JSON)
    patched = load_json(PATCHED_SAVE_JSON)
    summary = load_json(SUMMARY_JSON)
    manager_bag = load_json(ROOT / "output" / "_generic-tts-objects" / "Kill Team Card Boxes.json")

    original_features = count_feature_patterns(WORKSHOP_JSON)
    patched_features = count_feature_patterns(PATCHED_SAVE_JSON)
    script_counts = script_repo_counts(patched)

    patched_teams = summary.get("patched_teams", [])
    kept_teams = summary.get("kept_original_teams", [])
    manager_count = len(manager_bag.get("ContainedObjects") or [])

    lines = [
        "# Korean Workshop Patch Audit",
        "",
        "## Official Criterion",
        f"- Verified against Warhammer Community Korean Team Rules on {VERIFIED_DATE}.",
        "- Teams with Korean-language titles on the Korean Team Rules list are treated as officially translated.",
        "- Teams whose Korean-tab entry title remains in English are treated as English fallback.",
        "",
        "## Files",
        f"- Original workshop JSON: `{WORKSHOP_JSON}`",
        f"- Patched TTS save JSON: `{PATCHED_SAVE_JSON}`",
        f"- Upload/deliverable JSON: `{DELIVERABLE_JSON}`",
        f"- Patch summary JSON: `{SUMMARY_JSON}`",
        "",
        "## Script Repo Audit",
        f"- Target repo inside Lua scripts: {script_counts.get('target_repo_scripts', 0)}",
        f"- Upstream repo inside Lua scripts: {script_counts.get('upstream_repo_scripts', 0)}",
        f"- Target repo base: `{TARGET_REPO}`",
        f"- Upstream repo base: `{UPSTREAM_REPO}`",
        "",
        "## Feature Preservation",
    ]

    for pattern in FEATURE_PATTERNS:
        lines.append(
            f"- `{pattern}` original={original_features.get(pattern, 0)} patched={patched_features.get(pattern, 0)}"
        )

    lines.extend(
        [
            "",
            "## Team URL Mode",
            f"- Korean-applied teams ({len(patched_teams)}): {', '.join(patched_teams)}",
            f"- English fallback teams ({len(kept_teams)}): {', '.join(kept_teams)}",
            f"- Manager bag contained team boxes: {manager_count}",
            "",
            "## Representative FaceURL Checks",
            f"- Korean team `blades-of-khaine`: `{first_matching_box_face_url('blades-of-khaine')}`",
            f"- English fallback team `angels-of-death`: `{first_matching_box_face_url('angels-of-death')}`",
            "",
            "## Image Resolution Checks",
            f"- Localized sample front-image sizes seen: {localized_size_summary(patched_teams)}",
        ]
    )
    lines.extend(representative_image_sizes())
    lines.extend(
        [
            "",
            "## Save Integrity",
            "- The patched save is produced by patching the original workshop JSON in place rather than rebuilding a simplified substitute.",
            "- Team boxes keep the original object structure; only repo references in scripts and per-team card image URLs are swapped where localized assets exist.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text(report, encoding="utf-8", newline="\n")
    print(f"Audit written to: {AUDIT_MD}")


if __name__ == "__main__":
    main()
