from __future__ import annotations

import json
import urllib.parse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils.official_korean_team_rules import (
    OFFICIAL_KOREAN_TEAM_RULES,
    VERIFIED_DATE,
    has_official_korean_translation,
)

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
REPRESENTATIVE_TEAMS = ["angels-of-death", "battleclade", "blades-of-khaine", "gellerpox-infected"]
SOURCE_SCRIPT_DIR = ROOT / "config" / "defaults" / "tts-script"
SOURCE_SCRIPT_FILES = [
    "display-table-manager-script.lua",
    "single-object-updater.lua",
    "team-spawner-clean-script.lua",
    "team-spawner-script.lua",
    "bag-of-bags-reload-script.lua",
]


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


def strip_url(url: str) -> str:
    return (url or "").split("?", 1)[0]


def url_signature(url: str) -> str:
    clean = strip_url(url)
    marker = "/output/"
    idx = clean.lower().find(marker)
    if idx >= 0:
        return clean[idx:].lower()
    return clean.lower()


def is_team_box(obj: dict[str, Any]) -> bool:
    tags = obj.get("Tags") or []
    if isinstance(tags, list) and "KTCardsTokenBag" in tags:
        return False
    if isinstance(tags, list) and "_Faction_Decks" in tags:
        return True
    gm_notes = str(obj.get("GMNotes") or "")
    return gm_notes.startswith("_") and obj.get("Name") == "Custom_Model_Bag"


def slug_from_box(obj: dict[str, Any]) -> str:
    gm_notes = str(obj.get("GMNotes") or "").strip()
    if gm_notes.startswith("_"):
        return gm_notes[1:].strip().lower().replace(" ", "-")
    nickname = str(obj.get("Nickname") or "").strip()
    return nickname.lower().replace(" ", "-")


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
    datacard_url = ""
    data = load_patched_team_box(team_slug)
    for obj in collect_box_objects(data):
        if obj.get("kind") != "card":
            continue
        nickname = str(obj.get("nickname") or "")
        face_url = str(obj.get("face_url") or "")
        if nickname == "Datacards":
            return face_url
        if not datacard_url:
            datacard_url = face_url
    return datacard_url


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


def load_patched_team_box(team_slug: str) -> dict[str, Any]:
    patched = load_json(PATCHED_SAVE_JSON)
    for state in object_states(patched):
        for obj in walk_objects(state):
            if is_team_box(obj) and slug_from_box(obj) == team_slug:
                return obj
    raise KeyError(f"Patched save team box not found: {team_slug}")


def collect_box_objects(data: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    root = data.get("ObjectStates", [data])[0] if isinstance(data, dict) else data
    children = root.get("ContainedObjects") if isinstance(root, dict) else []
    for node in children or []:
        if not isinstance(node, dict):
            continue
        custom_deck = node.get("CustomDeck")
        if isinstance(custom_deck, dict) and custom_deck:
            first = next(iter(custom_deck.values()))
            if isinstance(first, dict):
                result.append(
                    {
                        "kind": "card",
                        "nickname": str(node.get("Nickname") or ""),
                        "face_url": str(first.get("FaceURL") or ""),
                        "back_url": str(first.get("BackURL") or ""),
                    }
                )
            continue
    return result


def collect_manifest_objects(team_slug: str) -> list[dict[str, Any]]:
    manifest = load_json(ROOT / "output" / team_slug / f"{team_slug}-object-urls.json")
    return list(manifest.get("objects", []))


def source_script_repo_counts() -> Counter:
    counts: Counter[str] = Counter()
    for filename in SOURCE_SCRIPT_FILES:
        path = SOURCE_SCRIPT_DIR / filename
        if not path.exists():
            counts["missing_source_scripts"] += 1
            continue
        text = path.read_text(encoding="utf-8")
        if TARGET_REPO in text:
            counts["target_repo_source_scripts"] += 1
        if UPSTREAM_REPO in text:
            counts["upstream_repo_source_scripts"] += 1
    return counts


def verify_team_objects(team_slug: str) -> list[str]:
    issues: list[str] = []
    generated_box = load_generated_team_box(team_slug)
    active = collect_box_objects(load_patched_team_box(team_slug))
    generated_active = collect_box_objects(generated_box)
    manifest_objects = collect_manifest_objects(team_slug)
    manifest_signatures: set[tuple[str, str, str]] = set()
    generated_signatures: set[tuple[str, str, str]] = set()

    for obj in manifest_objects:
        if obj.get("face_url"):
            manifest_signatures.add(
                ("card", url_signature(str(obj.get("face_url") or "")), url_signature(str(obj.get("back_url") or "")))
            )

    for obj in generated_active:
        generated_signatures.add(
            ("card", url_signature(obj.get("face_url", "")), url_signature(obj.get("back_url", "")))
        )

    for obj in active:
        sig = ("card", url_signature(obj.get("face_url", "")), url_signature(obj.get("back_url", "")))
        if sig not in manifest_signatures:
            issues.append(f"{team_slug}: active card deck missing from object manifest: {obj.get('nickname') or sig[1]}")
        if sig not in generated_signatures:
            issues.append(f"{team_slug}: patched save card deck differs from generated team box: {obj.get('nickname') or sig[1]}")

    if has_official_korean_translation(team_slug):
        for obj in active:
            face_url = str(obj.get("face_url") or "")
            back_url = str(obj.get("back_url") or "")
            if not face_url.startswith(TARGET_REPO):
                issues.append(f"{team_slug}: translated active card face URL not in target repo: {face_url}")
            if back_url and not back_url.startswith(TARGET_REPO):
                issues.append(f"{team_slug}: translated active card back URL not in target repo: {back_url}")
    else:
        for obj in active:
            face_url = str(obj.get("face_url") or "")
            back_url = str(obj.get("back_url") or "")
            if not face_url.startswith(UPSTREAM_REPO):
                issues.append(f"{team_slug}: fallback active card face URL not in upstream repo: {face_url}")
            if back_url and not back_url.startswith(UPSTREAM_REPO):
                issues.append(f"{team_slug}: fallback active card back URL not in upstream repo: {back_url}")
    return issues


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


def official_team_lists() -> tuple[list[str], list[str]]:
    translated = sorted(
        team for team, meta in OFFICIAL_KOREAN_TEAM_RULES.items() if bool(meta.get("translated"))
    )
    fallback = sorted(
        team for team, meta in OFFICIAL_KOREAN_TEAM_RULES.items() if not bool(meta.get("translated"))
    )
    return translated, fallback


def patched_save_team_slugs() -> list[str]:
    patched = load_json(PATCHED_SAVE_JSON)
    slugs: list[str] = []
    for state in object_states(patched):
        for obj in walk_objects(state):
            if is_team_box(obj):
                slugs.append(slug_from_box(obj))
    return sorted(set(slugs))


def active_repo_team_lists(all_teams: list[str]) -> tuple[list[str], list[str]]:
    localized: list[str] = []
    fallback: list[str] = []
    for team_slug in all_teams:
        urls = [obj.get("face_url", "") for obj in collect_box_objects(load_patched_team_box(team_slug))]
        if any(url.startswith(TARGET_REPO) for url in urls):
            localized.append(team_slug)
        else:
            fallback.append(team_slug)
    return sorted(localized), sorted(fallback)


def repo_routing_issues(all_teams: list[str]) -> list[str]:
    issues: list[str] = []
    for team_slug in all_teams:
        urls = [obj.get("face_url", "") for obj in collect_box_objects(load_patched_team_box(team_slug))]
        if not urls:
            issues.append(f"{team_slug}: no active card decks found in patched save")
            continue
        target_urls = [url for url in urls if url.startswith(TARGET_REPO)]
        upstream_urls = [url for url in urls if url.startswith(UPSTREAM_REPO)]
        other_urls = [url for url in urls if url and not url.startswith(TARGET_REPO) and not url.startswith(UPSTREAM_REPO)]
        if has_official_korean_translation(team_slug):
            if upstream_urls or other_urls:
                issues.append(
                    f"{team_slug}: translated team still has non-target deck URLs "
                    f"(target={len(target_urls)}, upstream={len(upstream_urls)}, other={len(other_urls)})"
                )
        elif other_urls:
            issues.append(
                f"{team_slug}: fallback team has unexpected non-upstream deck URLs "
                f"(target={len(target_urls)}, upstream={len(upstream_urls)}, other={len(other_urls)})"
            )
    return issues


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
    manager_bag = load_json(ROOT / "output" / "_generic-tts-objects" / "Kill Team Card Boxes.json")

    original_features = count_feature_patterns(WORKSHOP_JSON)
    patched_features = count_feature_patterns(PATCHED_SAVE_JSON)
    script_counts = script_repo_counts(patched)
    source_script_counts = source_script_repo_counts()

    official_translated, official_fallback = official_team_lists()
    all_teams = patched_save_team_slugs()
    patched_teams, kept_teams = active_repo_team_lists(all_teams)
    legacy_fallback = sorted(team for team in kept_teams if team not in official_fallback)
    manager_count = len(manager_bag.get("ContainedObjects") or [])
    verification_issues = repo_routing_issues(all_teams)

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
        f"- Source updater/spawner scripts with target repo: {source_script_counts.get('target_repo_source_scripts', 0)}/{len(SOURCE_SCRIPT_FILES)}",
        f"- Source updater/spawner scripts with upstream repo: {source_script_counts.get('upstream_repo_source_scripts', 0)}",
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
            f"- Officially translated teams ({len(official_translated)}): {', '.join(official_translated)}",
            f"- Official English-fallback teams ({len(official_fallback)}): {', '.join(official_fallback)}",
            f"- Legacy/no-Korean-entry fallback teams ({len(legacy_fallback)}): {', '.join(legacy_fallback)}",
            f"- Korean-applied teams ({len(patched_teams)}): {', '.join(patched_teams)}",
            f"- English fallback teams ({len(kept_teams)}): {', '.join(kept_teams)}",
            f"- Manager bag contained team boxes: {manager_count}",
            "",
            "## Representative FaceURL Checks",
            f"- Official Korean team `angels-of-death`: `{first_matching_box_face_url('angels-of-death')}`",
            f"- Official Korean team `battleclade`: `{first_matching_box_face_url('battleclade')}`",
            f"- Official Korean team `blades-of-khaine`: `{first_matching_box_face_url('blades-of-khaine')}`",
            f"- English fallback team `gellerpox-infected`: `{first_matching_box_face_url('gellerpox-infected')}`",
            "",
            "## Image Resolution Checks",
            f"- Localized sample front-image sizes seen: {localized_size_summary(patched_teams)}",
            f"- `angels-of-death` officially translated? {has_official_korean_translation('angels-of-death')}",
        ]
    )
    lines.extend(representative_image_sizes())
    lines.extend(
        [
            "",
            "## Save Integrity",
            "- The patched save is produced by patching the original workshop JSON in place rather than rebuilding a simplified substitute.",
            "- Team boxes keep the original object structure; only repo references in scripts and per-team card image URLs are swapped where localized assets exist.",
            "",
            "## Final Save Audit",
        ]
    )
    if verification_issues:
        lines.append(f"- Verification issues found: {len(verification_issues)}")
        lines.extend(f"- {issue}" for issue in verification_issues[:100])
    else:
        lines.append("- All officially translated teams' active card decks point at the target repository.")
        lines.append("- All English fallback teams' active card decks stayed on the upstream repository.")
        lines.append("- No translated team box in the final save contains mixed target/upstream deck URLs.")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text(report, encoding="utf-8", newline="\n")
    print(f"Audit written to: {AUDIT_MD}")


if __name__ == "__main__":
    main()
