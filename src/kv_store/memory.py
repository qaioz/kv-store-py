from time import time
from typing import Optional, Any
from .base import AbstractStore

class InMemoryStore(AbstractStore):
    """
    In-memory implementation of the store using a dictionary.
    """

    def __init__(self):
        self._store = {}  # key -> (value, expiration_timestamp)

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None

        value, expiration = self._store[key]
        current_time = time()

        if expiration is not None and current_time > expiration:
            del self._store[key]
            return None

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