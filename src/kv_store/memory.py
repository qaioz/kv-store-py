from time import time
from typing import Optional, Any
from .base import AbstractStore

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

    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> list[Optional[Any]]:
        """Get multiple values from the store."""
        if not keys:
            return []

        results = []
        for key in keys:
            result = await self.get(key, default)
            results.append(result)

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> list[bool]:
        """Set multiple values in the store with TTL."""
        results = []
        for key, value in items.items():
            result = await self.set(key, value, ttl)
            results.append(result)

        return results