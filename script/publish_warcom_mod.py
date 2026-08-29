#!/usr/bin/env python3
"""Publish WarCom pipeline outputs to the current TTS mod layout.

The legacy WarCom pipeline writes generated assets under:
  - output/{team}/...

The live TTS mod in this repository expects public update endpoints at:
  - tts_objects/{team}/...
  - output_v2/datacards-urls.json
  - output_v2/tts-card-boxes.json
  - output_v2/tts-metadata.json

This script bridges those layouts so the repository can keep using the
official WarCom PDFs while preserving the existing auto-update behavior in TTS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

import yaml

CARD_TYPE_MAP = {
    "datacards": "datacards",
    "equipment": "equipment",
    "faction_rules": "faction-rules",
    "firefight_ploys": "firefight-ploys",
    "operatives_selection": "operative-selection",
    "strategy_ploys": "strategy-ploys",
    "token_guide": "token-guide",
}

DEFAULT_GITHUB_REPO = "mightyTeddy922/kt-datacards-kor"


def resolve_repo_slug(workspace_root: Path) -> str:
    env_value = os.environ.get("KT_GITHUB_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if env_value:
        return env_value.strip().removeprefix("https://github.com/").removesuffix(".git").strip("/")

    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=workspace_root,
            text=True,
            encoding="utf-8",
            errors="ignore",
        ).strip()
    except Exception:
        return DEFAULT_GITHUB_REPO

    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/]+?)(?:\.git)?$", remote_url)
    return match.group("slug") if match else DEFAULT_GITHUB_REPO


def repo_base_url(workspace_root: Path, branch: str) -> str:
    return f"https://raw.githubusercontent.com/{resolve_repo_slug(workspace_root)}/{branch}"


def encode_raw_path(path: str) -> str:
    """Percent-encode a repo-relative path for use in raw GitHub URLs."""
    return quote(path, safe="/-_.~")


def rewrite_repo_urls(text: str, base_url: str) -> str:
    pattern = r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/"
    return re.sub(pattern, f"{base_url}/", text)


def load_team_config(config_path: Path) -> dict:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data.get("teams", {})


def copy_tree_contents(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if not src.exists():
        return
    shutil.copytree(src, dst)


def read_box_state_timestamps(box_json: Path) -> tuple[str, str]:
    try:
        data = json.loads(box_json.read_text(encoding="utf-8"))
        object_states = data.get("ObjectStates") or []
        if not object_states:
            return "", ""
        script_state = object_states[0].get("LuaScriptState") or ""
        if not script_state:
            return "", ""
        state = json.loads(script_state)
        return state.get("lastCardUpdate", ""), state.get("lastTokenUpdate", "") or state.get("lastUpdate", "")
    except Exception:
        return "", ""


def publish_team_tts_objects(
    team_slug: str,
    canonical_name: str,
    source_dir: Path,
    target_dir: Path,
    base_url: str,
) -> tuple[Path, Path | None, str, str]:
    target_dir.mkdir(parents=True, exist_ok=True)

    # Clear the published team directory so removed token files do not linger.
    for child in target_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    box_json = next(source_dir.glob("*.json"), None)
    if box_json is None:
        raise FileNotFoundError(f"Could not find top-level TTS box JSON in {source_dir}")

    preview_png = next(source_dir.glob("*.png"), None)

    published_box = target_dir / f"{canonical_name} Cards.json"
    box_text = rewrite_repo_urls(box_json.read_text(encoding="utf-8"), base_url)
    published_box.write_text(box_text, encoding="utf-8")

    published_preview = None
    if preview_png is not None:
        published_preview = target_dir / f"{canonical_name} Cards.png"
        shutil.copy2(preview_png, published_preview)

    tokens_src = source_dir / "tokens"
    if tokens_src.exists():
        shutil.copytree(tokens_src, target_dir / "tokens")
        for token_json in (target_dir / "tokens").glob("*.json"):
            token_json.write_text(
                rewrite_repo_urls(token_json.read_text(encoding="utf-8"), base_url),
                encoding="utf-8",
            )

    cards_timestamp, tokens_timestamp = read_box_state_timestamps(published_box)
    return published_box, published_preview, cards_timestamp, tokens_timestamp


def build_datacards_entries(team_slug: str, faction: str, team_output: Path, base_url: str) -> list[dict]:
    entries: list[dict] = []
    cards_root = team_output / "cards"
    if not cards_root.exists():
        return entries

    for card_dir in sorted(p for p in cards_root.iterdir() if p.is_dir()):
        public_type = CARD_TYPE_MAP.get(card_dir.name, card_dir.name.replace("_", "-"))
        for image_file in sorted(card_dir.glob("*.jpg")):
            cache_bust = f"?v={int(image_file.stat().st_mtime)}"
            rel_path = encode_raw_path(image_file.relative_to(team_output.parent).as_posix())
            entries.append(
                {
                    "faction": faction,
                    "team": team_slug,
                    "type": public_type,
                    "name": image_file.stem,
                    "url": f"{base_url}/{rel_path}{cache_bust}",
                }
            )

    return entries


def publish(team_filter: list[str] | None = None, branch: str = "main") -> None:
    workspace_root = Path(__file__).parent.parent
    team_config = load_team_config(workspace_root / "config" / "team-config.yaml")
    base_url = repo_base_url(workspace_root, branch)

    output_root = workspace_root / "output"
    tts_root = workspace_root / "tts_objects"
    output_v2_root = workspace_root / "output_v2"
    tts_root.mkdir(parents=True, exist_ok=True)
    output_v2_root.mkdir(parents=True, exist_ok=True)

    datacards_entries: list[dict] = []
    tts_boxes: list[dict] = []
    tts_metadata: list[dict] = []

    for team_output in sorted(p for p in output_root.iterdir() if p.is_dir()):
        team_slug = team_output.name
        if team_filter and team_slug not in team_filter:
            continue

        team_meta = team_config.get(team_slug, {})
        canonical_name = team_meta.get("canonical_name", team_slug.replace("-", " ").title())
        faction = team_meta.get("faction", "uncategorized")

        source_tts_dir = team_output / "tts_objects"
        if not source_tts_dir.exists():
            continue

        published_box, _, cards_timestamp, tokens_timestamp = publish_team_tts_objects(
            team_slug,
            canonical_name,
            source_tts_dir,
            tts_root / team_slug,
            base_url,
        )

        cards_url = f"{base_url}/tts_objects/{team_slug}/{encode_raw_path(published_box.name)}"
        cards_last_modified = cards_timestamp or str(published_box.stat().st_mtime)

        datacards_entries.extend(build_datacards_entries(team_slug, faction, team_output, base_url))
        datacards_entries.append(
            {
                "faction": "",
                "team": team_slug,
                "type": "tts_card_box_object",
                "name": canonical_name,
                "url": cards_url,
            }
        )

        tts_boxes.append(
            {
                "team": team_slug,
                "name": canonical_name,
                "url": cards_url,
            }
        )

        metadata_entry = {
            "team": team_slug,
            "name": canonical_name,
            "cards_url": cards_url,
            "cards_last_modified": cards_last_modified,
        }

        token_bag = tts_root / team_slug / "tokens" / f"{team_slug}-tokenbag.json"
        if token_bag.exists():
            metadata_entry["tokens_url"] = (
                f"{base_url}/tts_objects/{team_slug}/tokens/{encode_raw_path(token_bag.name)}"
            )
            metadata_entry["tokens_last_modified"] = tokens_timestamp or str(token_bag.stat().st_mtime)

        tts_metadata.append(metadata_entry)

    datacards_entries.sort(key=lambda item: (item["team"], item["type"], item["name"]))
    tts_boxes.sort(key=lambda item: item["team"])
    tts_metadata.sort(key=lambda item: item["team"])

    (output_v2_root / "datacards-urls.json").write_text(
        json.dumps(datacards_entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_v2_root / "tts-card-boxes.json").write_text(
        json.dumps(tts_boxes, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_v2_root / "tts-metadata.json").write_text(
        json.dumps(tts_metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Published {len(tts_boxes)} team box(es) from WarCom output")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish WarCom output to the live TTS mod layout")
    parser.add_argument("--branch", default="main", help="Git branch used in raw GitHub URLs")
    parser.add_argument("--teams", nargs="+", metavar="TEAM", help="Only publish these team slugs")
    args = parser.parse_args()
    publish(team_filter=args.teams, branch=args.branch)


if __name__ == "__main__":
    main()
