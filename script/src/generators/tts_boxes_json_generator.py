"""Generate `tts-card-boxes.json` from the published `tts_objects/` layout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.repo_urls import repo_base_url


def _discover_team_boxes(project_root: Path) -> list[dict]:
    tts_root = project_root / "tts_objects"
    base_url = repo_base_url(project_root=project_root)
    boxes: list[dict] = []

    for team_dir in sorted(p for p in tts_root.iterdir() if p.is_dir() and p.name != "display-table"):
        candidates = sorted(
            path for path in team_dir.glob("*.json")
            if not path.name.endswith("-tokenbag.json")
        )
        if not candidates:
            continue

        box_file = candidates[0]
        display_name = box_file.stem.removesuffix(" Cards")
        boxes.append(
            {
                "team": team_dir.name,
                "name": display_name,
                "url": f"{base_url}/tts_objects/{team_dir.name}/{box_file.name.replace(' ', '%20')}",
            }
        )

    return boxes


def generate_tts_boxes_json(project_root: Path | None = None) -> Path:
    """Generate `output_v2/tts-card-boxes.json` from `tts_objects/{team}/*.json`."""
    root = project_root or Path(__file__).resolve().parents[3]
    boxes = _discover_team_boxes(root)

    output_file = root / "output_v2" / "tts-card-boxes.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(boxes, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {output_file.name} with {len(boxes)} team box entries.")
    return output_file


if __name__ == "__main__":
    generate_tts_boxes_json()
