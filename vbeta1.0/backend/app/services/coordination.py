from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Iterator


class LifecycleCoordinator:
    """One process-wide lock for check-and-mutate lifecycle operations."""

    def __init__(self) -> None:
        self._lock = RLock()

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        with self._lock:
            yield
