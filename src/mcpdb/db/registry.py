from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from threading import RLock
from typing import Any

from mcpdb.db.base import Connector, RegistryError

ConnectorFactory = Callable[[], Connector]


def _check(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def wrapper(self: BackendRegistry, backend: str, *args: Any, **kwargs: Any) -> Any:
        normalized = backend.strip().lower()
        if not normalized:
            raise RegistryError("backend key cannot be empty")
        return method(self, normalized, *args, **kwargs)

    return wrapper


class BackendRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._factories: dict[str, ConnectorFactory] = {}

    @_check
    def register(self, backend: str, factory_fn: ConnectorFactory) -> None:
        if not callable(factory_fn):
            raise RegistryError("factory_fn must be callable")

        with self._lock:
            if backend in self._factories:
                raise RegistryError(f"backend '{backend}' is already registered")
            self._factories[backend] = factory_fn

    @_check
    def get(self, backend: str) -> ConnectorFactory:
        with self._lock:
            if backend not in self._factories:
                raise KeyError(f"unknown backend: {backend}")
            return self._factories[backend]
