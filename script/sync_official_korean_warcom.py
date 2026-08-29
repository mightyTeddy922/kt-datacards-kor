#!/usr/bin/env python3
"""Run the full official Korean WarCom sync flow for the live TTS mod layout."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def build_runtime_env(project_root: Path) -> dict[str, str]:
    """Build a subprocess environment, preferring the bootstrapped local runtime when present."""
    env = os.environ.copy()
    bootstrap_site = project_root / "work" / ".bootstrap-site"
    if not bootstrap_site.exists():
        return env

    pythonpath_parts = [str(bootstrap_site)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    path_parts = [
        str(bootstrap_site),
        str(bootstrap_site / "fitz"),
        str(bootstrap_site / "fitz_new"),
        str(bootstrap_site / "cv2"),
        str(bootstrap_site / "numpy.libs"),
    ]
    if env.get("PATH"):
        path_parts.append(env["PATH"])
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def run_step(project_root: Path, cmd: list[str], env: dict[str, str]) -> None:
    print(f"> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=project_root, check=True, env=env)


def count_staged_korean_pdfs(project_root: Path) -> int:
    staging_dir = project_root / "layers" / "warcom" / "staging"
    return sum(1 for _ in staging_dir.glob("kor_*.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync official Korean WarCom downloads into the live TTS mod layout"
    )
    parser.add_argument("--branch", default="main", help="Git branch to use in published raw URLs")
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip final published-output verification",
    )
    parser.add_argument(
        "--require-korean-pdfs",
        action="store_true",
        help="Require kor_*.pdf files in layers/warcom/staging during verification",
    )
    parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Always run the WarCom scrape step even when Korean PDFs are already staged",
    )
    parser.add_argument(
        "--min-korean-pdfs",
        type=int,
        default=30,
        help="Minimum staged kor_*.pdf count required before reusing cached staging without scraping",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    python = sys.executable
    env = build_runtime_env(project_root)

    staged_korean_pdfs = count_staged_korean_pdfs(project_root)
    if args.force_scrape or staged_korean_pdfs < args.min_korean_pdfs:
        run_step(
            project_root,
            [
                python,
                "pipelines/warcom/steps/1_scrape_warcom_killteam_downloads.py",
                "--locale",
                "ko-kr",
            ],
            env,
        )
    else:
        print(
            f"> Skipping scrape step because {staged_korean_pdfs} staged Korean PDFs meet the "
            f"minimum reuse threshold ({args.min_korean_pdfs})."
        )

    run_step(
        project_root,
        [
            python,
            "pipelines/warcom/steps/2a_extract_icons_and_artwork.py",
            "--input-dir",
            "layers/warcom/staging",
            "--output-dir",
            "layers/warcom/extracted",
        ],
        env,
    )
    run_step(
        project_root,
        [
            python,
            "pipelines/warcom/steps/2b_card_extractor.py",
            "--input",
            "layers/warcom/staging",
            "--output",
            "layers/warcom/extracted",
            "--templates",
            "config/pipelines/warcom/card_templates.json",
        ],
        env,
    )
    run_step(
        project_root,
        [
            python,
            "pipelines/warcom/steps/3_card_classification.py",
            "--extracted-dir",
            "layers/warcom/extracted",
            "--archive-dir",
            "layers/archive",
            "--output-dir",
            "output",
            "--config",
            "config/team-config.yaml",
        ],
        env,
    )
    run_step(
        project_root,
        [
            python,
            "pipelines/warcom/steps/4_token_extraction.py",
        ],
        env,
    )
    run_step(
        project_root,
        [
            python,
            "pipelines/warcom/steps/5_generate_tts_objects.py",
            "--branch",
            args.branch,
        ],
        env,
    )
    run_step(
        project_root,
        [
            python,
            "script/publish_warcom_mod.py",
            "--branch",
            args.branch,
        ],
        env,
    )

    if not args.skip_verify:
        verify_cmd = [
            python,
            "script/verify_warcom_korean_publish.py",
            "--branch",
            args.branch,
        ]
        if args.require_korean_pdfs:
            verify_cmd.append("--require-korean-pdfs")
        run_step(project_root, verify_cmd, env)

    print("Official Korean WarCom sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
