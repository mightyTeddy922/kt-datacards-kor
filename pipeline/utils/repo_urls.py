"""Helpers for resolving raw GitHub URLs for the current repository."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

DEFAULT_GITHUB_REPO = "mightyTeddy922/kt-datacards-kor"
UPSTREAM_GITHUB_REPO = "Wen-Qualtu/kt-datacards"


def resolve_repo_slug(project_root: Path | None = None) -> str:
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
    return f"https://raw.githubusercontent.com/{resolve_repo_slug(project_root)}/{branch}"


def output_base_url(project_root: Path | None = None, branch: str = "main") -> str:
    return f"{repo_base_url(project_root=project_root, branch=branch)}/output"


def repo_base_url_for_slug(repo_slug: str, branch: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{repo_slug}/{branch}"


def output_base_url_for_slug(repo_slug: str, branch: str = "main") -> str:
    return f"{repo_base_url_for_slug(repo_slug=repo_slug, branch=branch)}/output"
