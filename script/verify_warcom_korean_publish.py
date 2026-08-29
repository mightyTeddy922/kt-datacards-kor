#!/usr/bin/env python3
"""Verify that the live TTS mod layout is publishing the official Korean WarCom build."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.repo_urls import repo_base_url, resolve_repo_slug  # noqa: E402


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_urls(entries: list[dict], expected_prefix: str, field_names: list[str], label: str) -> list[str]:
    issues: list[str] = []
    for entry in entries:
        for field_name in field_names:
            value = entry.get(field_name)
            if value and not str(value).startswith(expected_prefix):
                issues.append(f"{label}: unexpected {field_name} for {entry.get('team', entry.get('name', '?'))}: {value}")
    return issues


def find_korean_pdf_names(project_root: Path) -> tuple[list[str], list[str], list[str]]:
    staging_dir = project_root / "layers" / "warcom" / "staging"
    archive_root = project_root / "layers" / "archive"

    staging_pdf_names = sorted(p.name for p in staging_dir.glob("*.pdf")) if staging_dir.exists() else []

    archived_korean_names: set[str] = set()
    if archive_root.exists():
        for path in archive_root.glob("*/warcom/kor_*.pdf"):
            archived_korean_names.add(path.name)

    available_korean_names = sorted(set(
        [name for name in staging_pdf_names if name.lower().startswith("kor_")] + list(archived_korean_names)
    ))
    return staging_pdf_names, sorted(archived_korean_names), available_korean_names


def find_failed_warcom_cards(project_root: Path) -> list[Path]:
    """Return any WarCom-extracted card PDFs that classification moved to the failed area."""
    failed_root = project_root / "layers" / "warcom" / "failed"
    if not failed_root.exists():
        return []
    return sorted(failed_root.rglob("*.pdf"))


def discover_published_team_dirs(tts_root: Path) -> list[str]:
    teams: list[str] = []
    for team_dir in sorted(p for p in tts_root.iterdir() if p.is_dir() and p.name != "display-table"):
        has_box_json = any(
            path.name.endswith(".json") and not path.name.endswith("-tokenbag.json")
            for path in team_dir.glob("*.json")
        )
        if has_box_json:
            teams.append(team_dir.name)
    return teams


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify published WarCom Korean TTS outputs")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--branch", default="main", help="Expected Git branch in published raw URLs")
    parser.add_argument(
        "--require-korean-pdfs",
        action="store_true",
        help="Fail if layers/warcom/staging does not currently contain kor_*.pdf files",
    )
    parser.add_argument(
        "--min-korean-pdfs",
        type=int,
        default=30,
        help="Minimum kor_*.pdf count required when --require-korean-pdfs is enabled",
    )
    parser.add_argument(
        "--allow-failed-cards",
        action="store_true",
        help="Do not fail verification when layers/warcom/failed contains skipped card PDFs",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    expected_prefix = repo_base_url(project_root=project_root, branch=args.branch)
    repo_slug = resolve_repo_slug(project_root=project_root)

    issues: list[str] = []
    tts_root = project_root / "tts_objects"

    tts_boxes_path = project_root / "output_v2" / "tts-card-boxes.json"
    tts_metadata_path = project_root / "output_v2" / "tts-metadata.json"
    datacards_urls_path = project_root / "output_v2" / "datacards-urls.json"

    for required_path in [tts_boxes_path, tts_metadata_path, datacards_urls_path]:
        if not required_path.exists():
            issues.append(f"Missing required published file: {required_path}")

    if not issues:
        tts_boxes = load_json(tts_boxes_path)
        tts_metadata = load_json(tts_metadata_path)
        datacards_urls = load_json(datacards_urls_path)

        issues.extend(validate_urls(tts_boxes, expected_prefix, ["url"], "tts-card-boxes"))
        issues.extend(
            validate_urls(
                tts_metadata,
                expected_prefix,
                ["cards_url", "tokens_url"],
                "tts-metadata",
            )
        )
        issues.extend(validate_urls(datacards_urls, expected_prefix, ["url"], "datacards-urls"))

        if tts_root.exists():
            expected_teams = discover_published_team_dirs(tts_root)
            box_teams = sorted(entry.get("team") for entry in tts_boxes)
            metadata_teams = sorted(entry.get("team") for entry in tts_metadata)
            if box_teams != expected_teams:
                issues.append(
                    f"tts-card-boxes teams do not match published tts_objects/ teams "
                    f"({len(box_teams)} vs {len(expected_teams)})"
                )
            if metadata_teams and sorted(set(metadata_teams) - set(expected_teams)):
                issues.append("tts-metadata contains teams not present in published tts_objects/")

    staging_dir = project_root / "layers" / "warcom" / "staging"
    staging_pdf_names: list[str] = []
    archived_korean_pdf_names: list[str] = []
    available_korean_pdf_names: list[str] = []
    if staging_dir.exists() or (project_root / "layers" / "archive").exists():
        staging_pdf_names, archived_korean_pdf_names, available_korean_pdf_names = find_korean_pdf_names(project_root)

    if args.require_korean_pdfs:
        if not staging_dir.exists():
            issues.append(f"Missing staging directory: {staging_dir}")
        elif len(available_korean_pdf_names) < args.min_korean_pdfs:
            issues.append(
                f"Expected at least {args.min_korean_pdfs} available kor_*.pdf files across "
                f"layers/warcom/staging and layers/archive/*/warcom, found {len(available_korean_pdf_names)}"
            )

    failed_cards = find_failed_warcom_cards(project_root)
    if failed_cards and not args.allow_failed_cards:
        issues.append(
            f"Found {len(failed_cards)} failed WarCom card PDF(s) under "
            f"{project_root / 'layers' / 'warcom' / 'failed'}"
        )

    print(f"Repository slug: {repo_slug}")
    print(f"Expected raw URL prefix: {expected_prefix}")
    print(f"Published team boxes file: {tts_boxes_path}")
    print(f"Published metadata file: {tts_metadata_path}")
    print(f"Published datacard URL file: {datacards_urls_path}")

    if staging_dir.exists():
        print(f"WarCom staging PDFs: {len(staging_pdf_names)} total")
        print(f"WarCom archived Korean PDFs: {len(archived_korean_pdf_names)}")
        print(f"WarCom available Korean PDFs: {len(available_korean_pdf_names)}")
        if available_korean_pdf_names:
            preview = ", ".join(available_korean_pdf_names[:5])
            print(f"Korean PDF samples: {preview}")
    else:
        print("WarCom staging directory not present in this checkout.")

    print(f"WarCom failed card PDFs: {len(failed_cards)}")
    if failed_cards:
        failed_preview = ", ".join(path.name for path in failed_cards[:5])
        print(f"Failed card samples: {failed_preview}")

    if issues:
        print("\nVerification failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("\nVerification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
