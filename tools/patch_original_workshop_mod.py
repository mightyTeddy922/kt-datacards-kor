from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils.official_korean_team_rules import has_official_korean_translation
DEFAULT_WORKSHOP_JSON = Path(
    r"C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Mods\Workshop\3646032507.json"
)
DEFAULT_SAVE_JSON = Path(
    r"C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Saves\KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json"
)
DEFAULT_DELIVERABLE_JSON = (
    ROOT / "output" / "_generic-tts-objects" / "KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json"
)

UPSTREAM_REPO = "https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main"
KOREAN_REPO = "https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main"
TEAM_TAG = "_Faction_Decks"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def object_states(root: dict[str, Any]) -> list[dict[str, Any]]:
    states = root.get("ObjectStates")
    if isinstance(states, list):
        return [state for state in states if isinstance(state, dict)]
    return []


def contained_objects(obj: dict[str, Any]) -> list[dict[str, Any]]:
    items = obj.get("ContainedObjects")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def walk_objects(obj: dict[str, Any]) -> list[dict[str, Any]]:
    result = [obj]
    for child in contained_objects(obj):
        result.extend(walk_objects(child))
    return result


def is_team_box(obj: dict[str, Any]) -> bool:
    tags = obj.get("Tags") or []
    if isinstance(tags, list) and "KTCardsTokenBag" in tags:
        return False
    if isinstance(tags, list) and TEAM_TAG in tags:
        return True
    gm_notes = str(obj.get("GMNotes") or "")
    return gm_notes.startswith("_") and obj.get("Name") == "Custom_Model_Bag"


def slug_from_box(obj: dict[str, Any]) -> str:
    gm_notes = str(obj.get("GMNotes") or "").strip()
    if gm_notes.startswith("_"):
        return gm_notes[1:].strip().lower().replace(" ", "-")
    nickname = str(obj.get("Nickname") or "").strip()
    return nickname.lower().replace(" ", "-")


def collect_custom_deck_objects(obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in contained_objects(obj)
        if isinstance(item.get("CustomDeck"), dict) and item["CustomDeck"]
    ]


def copy_custom_deck_urls(dst: dict[str, Any], src: dict[str, Any]) -> int:
    dst_custom = dst.get("CustomDeck")
    src_custom = src.get("CustomDeck")
    if not isinstance(dst_custom, dict) or not isinstance(src_custom, dict):
        return 0

    changed = 0
    for deck_key, src_info in src_custom.items():
        if deck_key not in dst_custom:
            continue
        dst_info = dst_custom[deck_key]
        if not isinstance(dst_info, dict) or not isinstance(src_info, dict):
            continue
        for field in ("FaceURL", "BackURL"):
            new_value = src_info.get(field)
            if new_value and dst_info.get(field) != new_value:
                dst_info[field] = new_value
                changed += 1
    return changed


def patch_team_box_images(dst_box: dict[str, Any], src_box: dict[str, Any], team_slug: str) -> tuple[int, bool]:
    dst_decks = collect_custom_deck_objects(dst_box)
    src_decks = collect_custom_deck_objects(src_box)
    if len(dst_decks) != len(src_decks):
        return 0, False

    if not has_official_korean_translation(team_slug):
        return 0, True

    changed = 0
    for dst_deck, src_deck in zip(dst_decks, src_decks):
        changed += copy_custom_deck_urls(dst_deck, src_deck)
    return changed, True


def patch_script_strings(node: Any) -> int:
    changed = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "LuaScript" and isinstance(value, str):
                new_value = value.replace(UPSTREAM_REPO, KOREAN_REPO)
                if new_value != value:
                    node[key] = new_value
                    changed += 1
            else:
                changed += patch_script_strings(value)
    elif isinstance(node, list):
        for item in node:
            changed += patch_script_strings(item)
    return changed


def collect_repo_script_matches(node: Any, matches: list[dict[str, Any]], path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}"
            if key == "LuaScript" and isinstance(value, str) and UPSTREAM_REPO in value:
                matches.append({"path": next_path, "contains_upstream_repo": True})
            else:
                collect_repo_script_matches(value, matches, next_path)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            collect_repo_script_matches(item, matches, f"{path}[{index}]")


def load_generated_team_box(team_slug: str) -> dict[str, Any] | None:
    team_dir = ROOT / "output" / team_slug / "tts_objects"
    if not team_dir.exists():
        return None
    json_files = sorted(
        [path for path in team_dir.glob("*.json") if not path.name.endswith(" Box.json")]
    )
    if not json_files:
        return None
    data = load_json(json_files[0])
    return data if isinstance(data, dict) else None


def patch_mod(workshop_json: Path, output_json: Path, deliverable_json: Path | None = None) -> dict[str, Any]:
    mod_data = load_json(workshop_json)
    patched = copy.deepcopy(mod_data)

    repo_script_matches: list[dict[str, Any]] = []
    collect_repo_script_matches(mod_data, repo_script_matches)
    script_changes = patch_script_strings(patched)
    team_changes: list[dict[str, Any]] = []

    for state in object_states(patched):
        for obj in walk_objects(state):
            if not is_team_box(obj):
                continue
            slug = slug_from_box(obj)
            generated = load_generated_team_box(slug)
            if generated is None:
                team_changes.append({"team": slug, "status": "missing-generated-box", "fields": 0})
                continue
            changed_fields, compatible = patch_team_box_images(obj, generated, slug)
            if not compatible:
                team_changes.append({"team": slug, "status": "shape-mismatch", "fields": 0})
                continue
            status = "patched-korean" if changed_fields else "kept-original"
            team_changes.append({"team": slug, "status": status, "fields": changed_fields})

    if isinstance(patched, dict):
        patched["SaveName"] = "KT24 - all team specific cards, tokens & dice (Korean Auto-Updating)"
    save_json(output_json, patched)
    if deliverable_json is not None:
        save_json(deliverable_json, patched)

    patched_teams = sorted(item["team"] for item in team_changes if item["status"] == "patched-korean")
    kept_original_teams = sorted(item["team"] for item in team_changes if item["status"] == "kept-original")
    problem_teams = [item for item in team_changes if item["status"] not in {"patched-korean", "kept-original"}]

    summary = {
        "workshop_json": str(workshop_json),
        "output_json": str(output_json),
        "deliverable_json": str(deliverable_json) if deliverable_json is not None else None,
        "source_repo": UPSTREAM_REPO,
        "target_repo": KOREAN_REPO,
        "script_changes": script_changes,
        "script_repo_match_paths": repo_script_matches,
        "team_changes": team_changes,
        "patched_teams_count": len(patched_teams),
        "kept_original_teams_count": len(kept_original_teams),
        "patched_teams": patched_teams,
        "kept_original_teams": kept_original_teams,
        "problem_teams": problem_teams,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch the original KT24 workshop mod so it keeps its scripts/features and only swaps card image URLs to Korean assets when available."
    )
    parser.add_argument("--workshop-json", type=Path, default=DEFAULT_WORKSHOP_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_SAVE_JSON)
    parser.add_argument("--deliverable-json", type=Path, default=DEFAULT_DELIVERABLE_JSON)
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=ROOT / "output" / "_generic-tts-objects" / "korean-workshop-patch-summary.json",
    )
    args = parser.parse_args()

    summary = patch_mod(args.workshop_json, args.output_json, args.deliverable_json)
    save_json(args.summary_json, summary)

    print(f"Patched save written to: {args.output_json}")
    print(f"Deliverable copy written to: {args.deliverable_json}")
    print(f"Script fields updated: {summary['script_changes']}")
    print(f"Korean teams patched: {summary['patched_teams_count']}")
    print(f"Original English kept: {summary['kept_original_teams_count']}")
    if summary["problem_teams"]:
        print("Problem teams:")
        for item in summary["problem_teams"]:
            print(f"  - {item['team']}: {item['status']}")


if __name__ == "__main__":
    main()
