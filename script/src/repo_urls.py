"""Helpers for resolving the current repository's raw GitHub URLs."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

DEFAULT_GITHUB_REPO = "mightyTeddy922/kt-datacards-kor"


def resolve_repo_slug(project_root: Path | None = None) -> str:
    """Resolve the current GitHub repo slug, preferring CI environment data."""
    env_value = os.environ.get("KT_GITHUB_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if env_value:
        return env_value.strip().removeprefix("https://github.com/").removesuffix(".git").strip("/")

    root = project_root or Path(__file__).resolve().parents[2]
    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="ignore",
        ).strip()
    except Exception:
        return DEFAULT_GITHUB_REPO

    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/]+?)(?:\.git)?$", remote_url)
    return match.group("slug") if match else DEFAULT_GITHUB_REPO


def repo_base_url(project_root: Path | None = None, branch: str = "main") -> str:
    """Return the raw GitHub base URL for this repository and branch."""
    return f"https://raw.githubusercontent.com/{resolve_repo_slug(project_root)}/{branch}"


def output_base_url(
    project_root: Path | None = None,
    branch: str = "main",
    output_dir: str = "output_v2",
) -> str:
    """Return the raw GitHub URL for a published output directory."""
    return f"{repo_base_url(project_root=project_root, branch=branch)}/{output_dir.strip('/')}"
