from concurrent.futures import ThreadPoolExecutor

import pytest

from mcpdb.db.base import RegistryError
from mcpdb.db.fake import FakeConnector
from mcpdb.db.registry import BackendRegistry


def test_registry_register_then_get() -> None:
    registry = BackendRegistry()
    registry.register("sqlite", lambda: FakeConnector())

    factory = registry.get("sqlite")

    assert isinstance(factory(), FakeConnector)


def test_registry_duplicate_backend_raises() -> None:
    registry = BackendRegistry()
    registry.register("sqlite", lambda: FakeConnector())

    with pytest.raises(RegistryError):
        registry.register("sqlite", lambda: FakeConnector())


def test_registry_get_unknown_raises() -> None:
    registry = BackendRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown")


def test_registry_concurrent_register_is_safe() -> None:
    registry = BackendRegistry()

    def register_backend(index: int) -> None:
        registry.register(f"b{index}", lambda: FakeConnector())

    with ThreadPoolExecutor(max_workers=16) as executor:
        for index in range(1000):
            executor.submit(register_backend, index)

    for index in range(1000):
        factory = registry.get(f"b{index}")
        assert isinstance(factory(), FakeConnector)
