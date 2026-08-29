from __future__ import annotations

import urllib.request

import jaraco.functools
import pytest
from jaraco.context import ExceptionTrap


@jaraco.functools.once
@ExceptionTrap().passes
def has_internet() -> None:
    """
    Is this host able to reach the Internet?

    Return True if the internet appears reachable and False
    otherwise.
    """
    urllib.request.urlopen('http://pypi.org')


def check_internet() -> None:
    """
    (pytest) Skip if internet is unavailable.
    """
    if not has_internet():
        pytest.skip('Internet connectivity unavailable')


@pytest.fixture
def needs_internet() -> None:
    """
    Pytest fixture signaling that internet is required.
    """
    check_internet()


def pytest_configure(config: pytest.Config) -> None:
    """
    Register the 'network' marker.
    """
    config.addinivalue_line(
        "markers", "network: the test requires network connectivity"
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    For any tests marked with 'network', install fixture.
    """
    for marker in item.iter_markers(name='network'):
        item.fixturenames.extend({'needs_internet'} - set(item.fixturenames))  # type: ignore[attr-defined]
