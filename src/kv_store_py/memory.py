import asyncio
from contextlib import AbstractAsyncContextManager
from time import time
from typing import Any, Optional, Union

from .base import AbstractStore


class InMemoryLock(AbstractAsyncContextManager):
    """Simple in-memory async lock."""

    _locks: dict[str, asyncio.Lock] = {}

    def __init__(
        self,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ):
        self._name = name
        self._timeout = timeout
        self._blocking_timeout = blocking_timeout
        if name not in InMemoryLock._locks:
            InMemoryLock._locks[name] = asyncio.Lock()
        self._lock = InMemoryLock._locks[name]

    async def acquire(self) -> bool:
        """Acquire the lock."""
        try:
            if self._blocking_timeout == 0:
                # Non-blocking: return immediately if locked
                if self._lock.locked():
                    return False
                # Try to acquire with minimal timeout
                await asyncio.wait_for(self._lock.acquire(), timeout=0.001)
                return True
            elif self._blocking_timeout is None:
                await self._lock.acquire()
                return True
            else:
                await asyncio.wait_for(
                    self._lock.acquire(), timeout=self._blocking_timeout
                )
                return True
        except asyncio.TimeoutError:
            return False

    async def release(self) -> None:
        """Release the lock."""
        try:
            self._lock.release()
        except RuntimeError:
            pass

    async def __aenter__(self) -> "InMemoryLock":
        acquired = await self.acquire()
        if not acquired:
            raise TimeoutError(f"Could not acquire lock '{self._name}'")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


class InMemoryStore(AbstractStore):
    """
    In-memory implementation of the store using a dictionary.
    """

    def __init__(self):
        self._store = {}  # key -> (value, expiration_timestamp)

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if key not in self._store:
            return default

        value, expiration = self._store[key]
        current_time = time()

        if expiration is not None and current_time > expiration:
            del self._store[key]
            return default

        return value

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        current_time = time()
        expiration = current_time + ttl if ttl > 0 else None
        self._store[key] = (value, expiration)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def get_many(
        self,
        keys: list[str],
        default: Optional[Union[Any, list[Any]]] = None,
    ) -> dict[str, Optional[Any]]:
        """Get multiple values from the store.

        Args:
            keys: List of keys to retrieve.
            default: Either a single default value (used for all missing keys)
                or a list of default values (one per key, must match len(keys)).
        """
        if not keys:
            return {}

        # Check if default is a list with same length as keys
        use_list_defaults = isinstance(default, list) and len(default) == len(keys)

        results = {}
        for i, key in enumerate(keys):
            key_default = default[i] if use_list_defaults else default
            result = await self.get(key, key_default)
            results[key] = result

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        results = {}
        for key, value in items.items():
            result = await self.set(key, value, ttl)
            results[key] = result

        return results

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the store."""
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count

    def lock(
        self,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ) -> InMemoryLock:
        """Get an in-memory lock.

        Args:
            name: The lock name/key.
            timeout: Not used for in-memory locks (kept for interface compatibility).
            blocking_timeout: How long to wait to acquire the lock.
                None = wait forever, 0 = fail immediately if not available.

        Returns:
            An InMemoryLock context manager.
        """
        return InMemoryLock(name, timeout=timeout, blocking_timeout=blocking_timeout)
