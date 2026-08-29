import pathlib
import platform

import pytest


@pytest.fixture
def tmp_home_dir(monkeypatch, tmp_path_factory):
    """
    A temporary home directory fixture.

    Configures the home directory to a temporary directory,
    hiding the user's dotfiles and other home-bound state.

    Before the fixture is enacted, home resolves to the user's
    usual home dir.

    >>> import pathlib
    >>> orig = pathlib.Path('~').expanduser()

    When the fixture is triggered, it alters the home directory,
    returning the altered directory.

    >>> home = getfixture('tmp_home_dir')

    Home is empty by default (feel free to inject state as needed).

    >>> list(home.iterdir())
    []

    Now ``~`` expands to the temporary home.

    >>> pathlib.Path('~').expanduser() == home
    True
    >>> pathlib.Path('~').expanduser() == orig
    False
    """
    return _set(monkeypatch, tmp_path_factory.mktemp('home'))


def _set(monkeypatch, path: pathlib.Path):
    """
    Set the home dir using a pytest monkeypatch context.
    """
    win = platform.system() == 'Windows'
    vars = ['HOME'] + win * ['USERPROFILE']
    for var in vars:
        monkeypatch.setenv(var, str(path))
    return path
