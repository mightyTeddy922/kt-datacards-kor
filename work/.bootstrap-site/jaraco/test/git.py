from __future__ import annotations

import shutil
import subprocess

import pytest
from jaraco.context import ExceptionTrap


def _resolve_git() -> str | None:
    """Locate a functional git executable if available."""
    try:
        subprocess.run(
            ['git', '--version'],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    return shutil.which('git')


@pytest.fixture
def ensure_git() -> None:
    """
    Require a working git executable for the test.

    >>> getfixture('ensure_git')
    """
    _resolve_git() or pytest.skip("'git' command unavailable")


@ExceptionTrap((OSError, subprocess.CalledProcessError)).passes
def _has_origin() -> None:
    """
    Is the current directory a git checkout with an 'origin' remote?
    """
    subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        check=True,
    )


@pytest.fixture
def ensure_checkout() -> None:
    """
    Skip the test unless a git checkout with an 'origin' remote is present.

    Useful for doctests and tests that shell out to git and would
    otherwise fail when run from a source tarball.

    >>> getfixture('ensure_checkout')
    """
    _has_origin() or pytest.skip("requires a git checkout with an 'origin' remote")
