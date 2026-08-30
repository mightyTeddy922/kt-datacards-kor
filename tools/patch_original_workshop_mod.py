from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import defaultdict, deque
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
GLOBAL_OBJECT_URLS_PATH = ROOT / "output" / "object-urls.json"
MANUAL_NAME_MAPS: dict[str, dict[str, str]] = {
    "blades-of-khaine": {
        "blades-of-khaine-aspect-techniques": "blades-of-khaine-일면-기술",
        "blades-of-khaine-dire-avenger-card1": "blades-of-khaine-절박한-복수자",
        "blades-of-khaine-dire-avenger-card2": "blades-of-khaine-절박한-복수자-2",
        "blades-of-khaine-dire-avenger-card3": "blades-of-khaine-절박한-복수자-3",
        "blades-of-khaine-dire-avenger-card4": "blades-of-khaine-절박한-복수자-4",
        "blades-of-khaine-dire-avenger-card5": "blades-of-khaine-절박한-복수자-5",
        "blades-of-khaine-howling-banshee-card1": "blades-of-khaine-울부짖는-밴시",
        "blades-of-khaine-howling-banshee-card2": "blades-of-khaine-울부짖는-밴시-2",
        "blades-of-khaine-howling-banshee-card3": "blades-of-khaine-울부짖는-밴시-3",
        "blades-of-khaine-howling-banshee-card4": "blades-of-khaine-울부짖는-밴시-4",
        "blades-of-khaine-howling-banshee-card5": "blades-of-khaine-울부짖는-밴시-5",
        "blades-of-khaine-striking-scorpion-card1": "blades-of-khaine-엄습하는-전갈",
        "blades-of-khaine-striking-scorpion-card2": "blades-of-khaine-엄습하는-전갈-2",
        "blades-of-khaine-striking-scorpion-card3": "blades-of-khaine-엄습하는-전갈-3",
        "blades-of-khaine-striking-scorpion-card4": "blades-of-khaine-엄습하는-전갈-4",
        "blades-of-khaine-striking-scorpion-card5": "blades-of-khaine-엄습하는-전갈-5",
    },
    "exodite-dragon-masters": {
        "exodite-dragon-masters-bladed-stance": "exodite-dragon-masters-날-선-자세",
        "exodite-dragon-masters-cleansing-of-the-pale-moon": "exodite-dragon-masters-창백한-달의-정화",
        "dragon-master-clanblade": "exodite-dragon-masters-용의-달인-부족검",
        "drakolithe": "exodite-dragon-masters-달음룡붙이",
        "exodite-dragon-masters-clan-talismans": "exodite-dragon-masters-부족-액막이",
        "exodite-dragon-masters-draconic-cavalry-tactics": "exodite-dragon-masters-용기병-전술",
        "exodite-dragon-masters-draconic-fury": "exodite-dragon-masters-용의-분노",
        "exodite-dragon-masters-drakesteed-agility": "exodite-dragon-masters-달음룡-민첩성",
        "exodite-dragon-masters-dragonscale-mesh": "exodite-dragon-masters-용비늘-그물망",
        "exodite-dragon-masters-earthen-wrath": "exodite-dragon-masters-대지가-빚은-분노",
        "exodite-dragon-masters-elusive-phantasm": "exodite-dragon-masters-닿지-않는-환영",
        "exodite-dragon-masters-fated-shot": "exodite-dragon-masters-운명이-깃든-한-발",
        "exodite-dragon-masters-feral-hunger": "exodite-dragon-masters-야생의-허기",
        "exodite-dragon-masters-focused-reflection": "exodite-dragon-masters-초점-반사",
        "exodite-dragon-masters-friendly-operative-has-speed-4-you-can-retain": "exodite-dragon-masters-기민한-속도",
        "exodite-dragon-masters-gloaming-mantle": "exodite-dragon-masters-땅거미-망토",
        "exodite-dragon-masters-leap": "exodite-dragon-masters-뜀뛰기",
        "exodite-dragon-masters-lileathan-crystal-matrices": "exodite-dragon-masters-릴리아산-수정-매트릭스",
        "exodite-dragon-masters-mercurial-speed": "exodite-dragon-masters-기민한-속도",
        "exodite-dragon-masters-moonsong-cull": "exodite-dragon-masters-말살의-달노래",
        "exodite-dragon-masters-nexus-sentinel": "exodite-dragon-masters-연결체-파수꾼",
        "exodite-dragon-masters-nomad-executioner": "exodite-dragon-masters-방랑하는-처단자",
        "exodite-dragon-masters-ride-them-down": "exodite-dragon-masters-짓밟고-달려가라",
        "exodite-dragon-masters-riding-mastery": "exodite-dragon-masters-기마술-대가",
        "exodite-dragon-masters-sinuous-flux": "exodite-dragon-masters-유연한-흐름",
        "exodite-dragon-masters-sow-the-seeds": "exodite-dragon-masters-파종",
        "exodite-dragon-masters-speartip-of-the-clan": "exodite-dragon-masters-부족의-창끝",
        "exodite-dragon-masters-spirit-stones": "exodite-dragon-masters-혼백석",
        "exodite-dragon-masters-spectral-nimbus": "exodite-dragon-masters-영적-후광",
        "dragon-master-leystalker": "exodite-dragon-masters-용의-달인-지맥추적자",
        "dragon-master-stonesinger": "exodite-dragon-masters-용의-달인-돌노래꾼",
        "exodite-dragon-masters-survivalist-spirit": "exodite-dragon-masters-생존주의-정신",
        "exodite-dragon-masters-wails-of-the-world": "exodite-dragon-masters-세계의-곡성",
        "exodite-dragon-masters-wind-swift-precision": "exodite-dragon-masters-질풍-속-정밀함",
        "exodite-dragon-masters-winds-grace": "exodite-dragon-masters-바람의-은혜",
        "exodite-dragon-masters-token-guide-card1": "exodite-dragon-masters-token-guide",
        "exodite-dragon-masters-token-guide-card2": "exodite-dragon-masters-token-guide-2",
    },
    "imperial-navy-breachers": {
        "navis-cat-unit": "cat",
        "navis-gheistskull": "imperial-navy-breachers-해군-가이스트스컬",
    },
    "inquisitorial-agents": {
        "inquisitorial-agents-death-korps": "inquisitorial-agents-bruiser",
        "inquisitorial-agents-exaction-squad": "inquisitorial-agents-castigator",
        "inquisitorial-agents-imperial-navy-breachers": "inquisitorial-agents-armsman",
        "inquisitorial-agents-kasrkin": "inquisitorial-agents-combat-medic",
        "inquisitorial-agents-sisters-of-silence": "inquisitorial-agents-prosecutor",
        "inquisitorial-agents-tempestus-scions": "inquisitorial-agents-medic",
        "tome-skull": "inquisitorial-agents-톰스컬",
    },
    "kasrkin": {
        "kasrkin-rapid-fire": "kasrkin-속사",
    },
    "spectre-squad": {
        "spectre-vox-relay-beacon": "spectre-squad-유령-분대-복스중계-신호기",
    },
}


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


def copy_custom_entry_urls(dst_info: dict[str, Any], src_info: dict[str, Any]) -> int:
    if not isinstance(dst_info, dict) or not isinstance(src_info, dict):
        return 0
    changed = 0
    for field in ("FaceURL", "BackURL"):
        new_value = src_info.get(field)
        if new_value and dst_info.get(field) != new_value:
            dst_info[field] = new_value
            changed += 1
    return changed


def first_custom_entry(obj: dict[str, Any]) -> dict[str, Any] | None:
    custom = obj.get("CustomDeck")
    if not isinstance(custom, dict) or not custom:
        return None
    first = next(iter(custom.values()))
    return first if isinstance(first, dict) else None


def object_nickname(obj: dict[str, Any]) -> str:
    return str(obj.get("Nickname") or "").strip().lower()


def object_state_root(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict) and isinstance(data.get("ObjectStates"), list) and data["ObjectStates"]:
        first = data["ObjectStates"][0]
        if isinstance(first, dict):
            return first
    return data if isinstance(data, dict) else None


def load_generated_card_urls(team_slug: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    sources: list[dict[str, Any]] = []
    path = ROOT / "output" / team_slug / f"{team_slug}-object-urls.json"
    if path.exists():
        sources.append(load_json(path))

    if GLOBAL_OBJECT_URLS_PATH.exists():
        global_data = load_json(GLOBAL_OBJECT_URLS_PATH)
        team_data = global_data.get(team_slug)
        if isinstance(team_data, dict):
            sources.append(team_data)

    for data in sources:
        for entry in data.get("objects", []):
            if not isinstance(entry, dict):
                continue
            face_url = str(entry.get("face_url") or "")
            if not face_url:
                continue
            name = str(entry.get("name") or "").strip().lower()
            if name:
                result[name] = {
                    "FaceURL": face_url,
                    "BackURL": str(entry.get("back_url") or ""),
                }

    cards_root = ROOT / "output" / team_slug / "cards"
    if cards_root.exists():
        grouped: dict[str, dict[str, str]] = {}
        for front_path in cards_root.rglob("*-front.jpg"):
            rel = front_path.relative_to(ROOT / "output").as_posix()
            back_path = front_path.with_name(front_path.name.replace("-front.jpg", "-back.jpg"))
            back_rel = back_path.relative_to(ROOT / "output").as_posix() if back_path.exists() else ""
            name = front_path.stem.removesuffix("-front").lower()
            grouped[name] = {
                "FaceURL": f"{KOREAN_REPO}/output/{rel}",
                "BackURL": f"{KOREAN_REPO}/output/{back_rel}" if back_rel else "",
            }
        result.update(grouped)

    tts_cards_root = ROOT / "output" / team_slug / "tts_objects" / "cards"
    if tts_cards_root.exists():
        for path in tts_cards_root.rglob("*.json"):
            try:
                data = load_json(path)
            except Exception:
                continue

            obj = object_state_root(data)
            if not obj:
                continue

            custom_entry = first_custom_entry(obj)
            if not custom_entry:
                continue

            face_url = str(custom_entry.get("FaceURL") or "")
            if not face_url:
                continue

            url_info = {
                "FaceURL": face_url,
                "BackURL": str(custom_entry.get("BackURL") or ""),
            }
            keys = {object_nickname(obj), path.stem.strip().lower()}
            for key in keys:
                if key:
                    result[key] = url_info

    tts_decks_root = ROOT / "output" / team_slug / "tts" / "cardbox" / "decks"
    if tts_decks_root.exists():
        for path in tts_decks_root.rglob("*.json"):
            try:
                data = load_json(path)
            except Exception:
                continue

            obj = object_state_root(data)
            if not obj:
                continue

            custom_entry = first_custom_entry(obj)
            if not custom_entry:
                continue

            face_url = str(custom_entry.get("FaceURL") or "")
            if not face_url:
                continue

            url_info = {
                "FaceURL": face_url,
                "BackURL": str(custom_entry.get("BackURL") or ""),
            }
            nickname = object_nickname(obj)
            keys = {nickname, path.stem.strip().lower()}
            if nickname and not nickname.startswith(team_slug):
                keys.add(f"{team_slug}-{nickname}")
            for key in keys:
                if key:
                    result[key] = url_info
    return result


def normalize_name(value: str) -> str:
    text = re.sub(r"[^0-9a-z가-힣]+", "", value.strip().lower())
    return text


def load_team_card_aliases(team_slug: str) -> dict[str, set[str]]:
    cards_root = ROOT / "output" / team_slug / "tts_objects" / "cards"
    if not cards_root.exists():
        return {}

    grouped_names: dict[tuple[str, int], set[str]] = defaultdict(set)
    for path in cards_root.rglob("*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue

        nickname = object_nickname(data)
        guid = str(data.get("GUID") or "").strip().lower()
        card_id = int(data.get("CardID") or 0)
        if not nickname or not guid or not card_id:
            continue
        grouped_names[(guid, card_id)].add(nickname)

    aliases: dict[str, set[str]] = defaultdict(set)
    for names in grouped_names.values():
        if len(names) < 2:
            continue
        for name in names:
            aliases[name].update(other for other in names if other != name)
    return {name: values for name, values in aliases.items() if values}


def generic_name_variants(name: str) -> list[str]:
    variants: list[str] = []

    def add(value: str) -> None:
        value = value.strip().lower()
        if value and value not in variants:
            variants.append(value)

    add(name)
    add(name.replace("markertoken-guide", "token-guide"))
    add(name.replace("-operatives", "-operative-selection"))
    add(name.replace("-operatives", "-operative-selection-card1"))
    add(name.replace("navis-cat-unit", "navis-c.a.t.-unit"))
    add(name.replace("kaboom", "kaboom!"))
    add(name.replace("waaagh", "waaagh!"))
    add(name.replace("-mutation", "-abhorrent-mutation"))

    forward_scout = re.match(r"^(scout-squad-forward-scouting)-card([1-4])$", name)
    if forward_scout:
        add(f"{forward_scout.group(1)}-options-are-presented-card{forward_scout.group(2)}")

    return variants


def lookup_generated_card_url(
    direct_urls: dict[str, dict[str, str]],
    aliases: dict[str, set[str]],
    normalized_direct: dict[str, str],
    name: str,
    team_slug: str | None = None,
) -> dict[str, str] | None:
    if team_slug:
        manual_target = (MANUAL_NAME_MAPS.get(team_slug) or {}).get(name)
        if manual_target:
            if manual_target in direct_urls:
                return direct_urls[manual_target]
            normalized_match = normalized_direct.get(normalize_name(manual_target))
            if normalized_match:
                return direct_urls[normalized_match]

    queue = deque(generic_name_variants(name))
    seen: set[str] = set()

    while queue:
        candidate = queue.popleft()
        if candidate in seen:
            continue
        seen.add(candidate)

        if candidate in direct_urls:
            return direct_urls[candidate]

        normalized_match = normalized_direct.get(normalize_name(candidate))
        if normalized_match:
            return direct_urls[normalized_match]

        for alias in aliases.get(candidate, set()):
            if alias not in seen:
                queue.append(alias)
        for variant in generic_name_variants(candidate):
            if variant not in seen:
                queue.append(variant)

    return None


def resolve_generated_card_urls(team_slug: str) -> dict[str, dict[str, str]]:
    direct_urls = load_generated_card_urls(team_slug)
    aliases = load_team_card_aliases(team_slug)
    normalized_direct = {normalize_name(name): name for name in direct_urls}

    resolved = dict(direct_urls)
    original_names = list({*direct_urls.keys(), *aliases.keys()})

    for name in original_names:
        if name in resolved:
            continue
        match = lookup_generated_card_url(direct_urls, aliases, normalized_direct, name, team_slug)
        if match:
            resolved[name] = match

    return resolved


def apply_urls_from_generated(dst_obj: dict[str, Any], src_obj: dict[str, str]) -> int:
    dst_entry = first_custom_entry(dst_obj)
    if dst_entry is None:
        return 0
    return copy_custom_entry_urls(dst_entry, src_obj)


def apply_deck_urls_from_generated_cards(dst_deck: dict[str, Any], generated_cards: dict[str, dict[str, str]]) -> int:
    dst_custom = dst_deck.get("CustomDeck")
    if not isinstance(dst_custom, dict) or not dst_custom:
        return 0

    dst_cards = contained_objects(dst_deck)
    if not dst_cards:
        nickname = object_nickname(dst_deck)
        src_obj = generated_cards.get(nickname)
        return apply_urls_from_generated(dst_deck, src_obj) if src_obj else 0

    changed = 0
    for dst_card in dst_cards:
        src_obj = generated_cards.get(object_nickname(dst_card))
        if src_obj is None:
            return 0
        card_id = int(dst_card.get("CardID") or 0)
        deck_key = str(card_id // 100) if card_id else ""
        dst_info = dst_custom.get(deck_key)
        if not isinstance(dst_info, dict):
            return 0
        changed += copy_custom_entry_urls(dst_info, src_obj)
    return changed


def apply_deck_urls_from_generated_cards_with_lookup(
    dst_deck: dict[str, Any],
    *,
    direct_urls: dict[str, dict[str, str]],
    aliases: dict[str, set[str]],
    normalized_direct: dict[str, str],
    team_slug: str,
) -> int:
    dst_custom = dst_deck.get("CustomDeck")
    if not isinstance(dst_custom, dict) or not dst_custom:
        return 0

    dst_cards = contained_objects(dst_deck)
    if not dst_cards:
        nickname = object_nickname(dst_deck)
        src_obj = lookup_generated_card_url(direct_urls, aliases, normalized_direct, nickname, team_slug)
        return apply_urls_from_generated(dst_deck, src_obj) if src_obj else 0

    changed = 0
    for dst_card in dst_cards:
        src_obj = lookup_generated_card_url(
            direct_urls,
            aliases,
            normalized_direct,
            object_nickname(dst_card),
            team_slug,
        )
        if src_obj is None:
            return 0
        card_id = int(dst_card.get("CardID") or 0)
        deck_key = str(card_id // 100) if card_id else ""
        dst_info = dst_custom.get(deck_key)
        if not isinstance(dst_info, dict):
            return 0
        changed += copy_custom_entry_urls(dst_info, src_obj)
    return changed


def patch_team_box_images(dst_box: dict[str, Any], team_slug: str) -> tuple[int, bool]:
    if not has_official_korean_translation(team_slug):
        return 0, True

    direct_urls = load_generated_card_urls(team_slug)
    if not direct_urls:
        return 0, False
    aliases = load_team_card_aliases(team_slug)
    normalized_direct = {normalize_name(name): name for name in direct_urls}

    changed = 0
    for dst_obj in contained_objects(dst_box):
        if not isinstance(dst_obj.get("CustomDeck"), dict) or not dst_obj["CustomDeck"]:
            continue
        delta = apply_deck_urls_from_generated_cards_with_lookup(
            dst_obj,
            direct_urls=direct_urls,
            aliases=aliases,
            normalized_direct=normalized_direct,
            team_slug=team_slug,
        )
        if delta == 0:
            return 0, False
        changed += delta
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
            changed_fields, compatible = patch_team_box_images(obj, slug)
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
