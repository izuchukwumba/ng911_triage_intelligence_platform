"""The app closes the store it builds, and only that one."""

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.settings import Settings
from ntip.store import InMemoryEventStore


class Tracked(InMemoryEventStore):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_app_closes_the_store_it_built_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    built = Tracked()
    monkeypatch.setattr(Settings, "build_store", lambda self: built)
    with TestClient(create_app(settings=Settings())):
        assert not built.closed
    assert built.closed


def test_app_leaves_a_store_it_was_given_open() -> None:
    given = Tracked()
    with TestClient(create_app(store=given, settings=Settings())):
        pass
    assert not given.closed
