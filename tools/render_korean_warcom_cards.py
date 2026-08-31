from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.steps.build_structure import _classify_warcom_team
from pipeline.steps.generate_card_images import (
    JPEG_QUALITY,
    STABLE_IMAGE_TOLERANCE,
    ZOOM,
    _copy_default_backside,
    _image_base,
)
from pipeline.steps.track_warcom import TEMPLATES_FILE, _team_from_filename
from pipeline.steps.warcom import card_extractor, scraper
from pipeline.utils import paths
from pipeline.utils.stable_io import stable_write

logger = logging.getLogger(__name__)

FALSE_POSITIVE_KOREAN_TEAMS = {
    "pathfinders",
    "novitiates",
    "gellerpox-infected",
}

# As of August 31, 2026, the official Korean Hand of the Archon PDF is missing
# one card page, so the mod should keep the upstream English assets for this team.
BROKEN_KOREAN_TEAMS = {
    "hand-of-the-archon",
}

CARD_TYPE_DIRS = (
    "datacards",
    "equipment",
    "faction_rules",
    "firefight_ploys",
    "operatives_selection",
    "strategy_ploys",
    "token_guide",
)


def _fetch_team_urls(language: str, team_config: dict) -> Dict[str, str]:
    entries = scraper._fetch_download_entries(language)  # noqa: SLF001 - shared pipeline helper
    result: Dict[str, str] = {}
    for entry in entries:
        if not scraper._entry_is_team_rules(entry):  # noqa: SLF001 - shared pipeline helper
            continue
        info = entry.get("id") or {}
        file_name = str(info.get("file") or "").strip()
        if not file_name:
            continue
        url = scraper._absolute_url(file_name)  # noqa: SLF001 - shared pipeline helper
        team = _team_from_filename(Path(file_name), team_config)
        if team:
            result[team] = url
    return result


def _flatten_expected_cards(team: str, structure: dict) -> List[dict]:
    expected: List[dict] = []
    for card_type in CARD_TYPE_DIRS:
        entities = structure.get(card_type) or []
        for entity in entities:
            name = entity.get("name", "UNKNOWN")
            cards = entity.get("cards", [])
            multi = len(cards) > 1
            base_name = _image_base(team, card_type, name)
            for idx, card in enumerate(cards, 1):
                image_base = f"{base_name}-card{idx}" if multi else base_name
                expected.append(
                    {
                        "image_base": image_base,
                        "card_type": card_type,
                        "front": card.get("front"),
                        "back": card.get("back"),
                        "front_name": Path(card.get("front", "")).name if card.get("front") else None,
                        "back_name": Path(card.get("back", "")).name if card.get("back") else None,
                    }
                )
    return expected


def _render_pdf_page(pdf_path: Path, out_path: Path) -> None:
    with fitz.open(pdf_path) as doc:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with stable_write(out_path, image_tolerance=STABLE_IMAGE_TOLERANCE):
            pix.save(out_path, jpg_quality=JPEG_QUALITY)


def _render_team_from_pairs(
    team: str,
    structure: dict,
    english_cards: List[Path],
    korean_cards: List[Path],
) -> Tuple[int, int]:
    expected = _flatten_expected_cards(team, structure)
    english_index = {path.name: idx for idx, path in enumerate(english_cards)}

    written = 0
    referenced_sides = 0
    for item in expected:
        out_dir = paths.team_output(team) / "cards" / item["card_type"]
        front_path = out_dir / f"{item['image_base']}-front.jpg"
        front_name = item["front_name"]
        if front_name not in english_index:
            raise ValueError(f"{team}: missing English source card {front_name}")
        front_idx = english_index[front_name]
        if front_idx >= len(korean_cards):
            raise ValueError(f"{team}: missing Korean card at index {front_idx} for {front_name}")
        _render_pdf_page(korean_cards[front_idx], front_path)
        written += 1
        referenced_sides += 1

        back_path = out_dir / f"{item['image_base']}-back.jpg"
        if item["back"]:
            back_name = item["back_name"]
            if back_name not in english_index:
                raise ValueError(f"{team}: missing English source back card {back_name}")
            back_idx = english_index[back_name]
            if back_idx >= len(korean_cards):
                raise ValueError(f"{team}: missing Korean card at index {back_idx} for {back_name}")
            _render_pdf_page(korean_cards[back_idx], back_path)
            written += 1
            referenced_sides += 1
        else:
            if _copy_default_backside(team, back_path, item["card_type"] != "datacards"):
                written += 1

    return written, referenced_sides


def _download_and_extract(team: str, pdf_url: str, destination: Path, templates: dict) -> List[Path]:
    pdf_path = destination / Path(pdf_url).name
    if not scraper.download_pdf(pdf_url, pdf_path):
        raise RuntimeError(f"{team}: failed to download {pdf_url}")

    cards_dir = destination / "cards"
    result = card_extractor.extract_cards(pdf_path, templates, cards_dir, team_name=team, dpi=150)
    cards = sorted(cards_dir.glob("*.pdf"))
    logger.info(
        "[%s] extracted %s sides from %s pages (%s)",
        team,
        result["total_cards"],
        result["pages_processed"],
        pdf_path.name,
    )
    return cards


def _supported_korean_teams(
    english_urls: Dict[str, str],
    korean_urls: Dict[str, str],
    requested: Optional[Iterable[str]] = None,
) -> List[str]:
    teams = sorted(set(english_urls) & set(korean_urls))
    teams = [team for team in teams if team not in FALSE_POSITIVE_KOREAN_TEAMS]
    teams = [team for team in teams if team not in BROKEN_KOREAN_TEAMS]
    if requested is not None:
        wanted = {team.strip().lower() for team in requested if team.strip()}
        teams = [team for team in teams if team in wanted]
    return teams


def render_korean_cards(teams: Optional[List[str]] = None) -> dict:
    templates = card_extractor.load_templates(TEMPLATES_FILE)
    team_config = card_extractor.load_team_config(paths.TEAM_CONFIG)
    english_urls = _fetch_team_urls("english", team_config)
    korean_urls = _fetch_team_urls("korean", team_config)
    supported_teams = _supported_korean_teams(english_urls, korean_urls, teams)

    logger.info("resolved %s supported Korean teams", len(supported_teams))
    if not supported_teams:
        return {"processed": 0, "failed": 0, "teams": []}

    processed: List[str] = []
    failed: Dict[str, str] = {}

    scratch_root = ROOT / "work"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kt-korean-render-", dir=scratch_root) as temp_root:
        root = Path(temp_root)
        for team in supported_teams:
            try:
                team_root = root / team
                english_dir = team_root / "english"
                korean_dir = team_root / "korean"
                english_cards = _download_and_extract(team, english_urls[team], english_dir, templates)
                korean_cards = _download_and_extract(team, korean_urls[team], korean_dir, templates)

                structure = _classify_warcom_team(team, english_dir / "cards")
                if not structure:
                    raise RuntimeError(f"{team}: english structure classification failed")

                written, side_count = _render_team_from_pairs(team, structure, english_cards, korean_cards)
                logger.info("[%s] wrote %s images from %s localized sides", team, written, side_count)
                processed.append(team)
            except Exception as exc:  # noqa: BLE001
                logger.exception("[%s] failed: %s", team, exc)
                failed[team] = str(exc)

    return {
        "processed": len(processed),
        "failed": len(failed),
        "teams": processed,
        "errors": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render official Korean Warhammer Community card images onto the existing English TTS output structure."
    )
    parser.add_argument(
        "--teams",
        help="comma-separated team slugs to localize (default: all supported Korean teams)",
    )
    parser.add_argument(
        "--report",
        help="optional JSON report output path",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    teams = [item.strip() for item in args.teams.split(",")] if args.teams else None
    report = render_korean_cards(teams)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("done: %s", report)

    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    main()
