#!/usr/bin/env python3
"""
Sync generated team boxes into a local Tabletop Simulator save/object file.

What it does:
- Rebuilds `output/_generic-tts-objects/Kill Team Card Boxes.json` so it contains
  the current 48 generated team boxes.
- Replaces the `KT Display Manager` bag contents inside one or more TTS save JSONs
  with those same generated team boxes.

This is the final local step after:
    python -m pipeline.main --step generate_tts --force

Usage:
    python tools/sync_local_tts_save.py
    python tools/sync_local_tts_save.py --save "C:/.../My Save.json"
    python tools/sync_local_tts_save.py --saved-object "C:/.../Saved Object.json"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
MANAGER_PATH = OUTPUT_DIR / "_generic-tts-objects" / "Kill Team Card Boxes.json"


def _default_tts_paths() -> tuple[list[Path], list[Path]]:
    home = Path.home()
    bases = [
        home / "OneDrive" / "문서" / "My Games" / "Tabletop Simulator",
        home / "Documents" / "My Games" / "Tabletop Simulator",
    ]
    save_paths: list[Path] = []
    object_paths: list[Path] = []
    for base in bases:
        save_paths.append(base / "Saves" / "KT24_Korean_Auto_Updating_Mod.json")
        object_paths.append(base / "Saves" / "Saved Objects" / "KT24_Korean_Auto_Updating_Objects.json")
    return save_paths, object_paths


def _load_team_boxes() -> list[dict]:
    team_boxes: list[dict] = []
    for team_dir in sorted(p for p in OUTPUT_DIR.iterdir() if p.is_dir() and p.name != "_generic-tts-objects"):
        display_name = team_dir.name.replace("-", " ").title()
        box_path = team_dir / "tts_objects" / f"{display_name}.json"
        if not box_path.exists():
            continue
        with open(box_path, "r", encoding="utf-8") as fh:
            team_boxes.append(json.load(fh))
    return team_boxes


def _write_manager_bag(team_boxes: list[dict]) -> None:
    with open(MANAGER_PATH, "r", encoding="utf-8") as fh:
        manager_data = json.load(fh)
    manager_data["ContainedObjects"] = json.loads(json.dumps(team_boxes))
    with open(MANAGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(manager_data, fh, indent=2, ensure_ascii=False)


def _patch_tts_file(path: Path, team_boxes: list[dict]) -> bool:
    if not path.exists():
        return False
    with open(path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)

    updated = False
    for obj in data.get("ObjectStates", []) or []:
        if obj.get("Nickname") == "KT Display Manager" and obj.get("Name") == "Bag":
            obj["ContainedObjects"] = json.loads(json.dumps(team_boxes))
            updated = True

    if updated:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync generated TTS team boxes into local TTS save files")
    parser.add_argument("--save", action="append", default=[], help="Explicit TTS save JSON path")
    parser.add_argument("--saved-object", action="append", default=[], help="Explicit TTS saved object JSON path")
    args = parser.parse_args()

    team_boxes = _load_team_boxes()
    if not team_boxes:
        raise SystemExit("No generated team boxes found under output/*/tts_objects/")

    _write_manager_bag(team_boxes)
    print(f"Rebuilt manager bag with {len(team_boxes)} teams: {MANAGER_PATH}")

    default_saves, default_objects = _default_tts_paths()
    save_paths = [Path(p) for p in args.save] or default_saves
    object_paths = [Path(p) for p in args.saved_object] or default_objects

    patched = 0
    for path in save_paths + object_paths:
        if _patch_tts_file(path, team_boxes):
            print(f"Patched: {path}")
            patched += 1
        else:
            print(f"Skipped: {path}")

    print(f"Done. Patched {patched} local TTS file(s).")


if __name__ == "__main__":
    main()
