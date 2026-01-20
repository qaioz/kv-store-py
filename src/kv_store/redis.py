from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio.lock import Lock
import json
from .base import AbstractStore


class RedisStore(AbstractStore):
    def __init__(self, client: redis.Redis):
        self.client = client

    def _serialize(self, value: Any) -> Any:
        """
        Helper: Convert Python objects to JSON strings for Redis.
        """
        if isinstance(value, bytes):
            return value
        return json.dumps(value)

    def _deserialize(self, value: Any) -> Any:
        """
        Helper: Convert Redis strings back to Python objects.
        """
        if value is None:
            return None

        if isinstance(value, bytes):
            value = value.decode('utf-8')

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        value = await self.client.get(key)
        if value is None:
            return default
        return self._deserialize(value)

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        encoded_value = self._serialize(value)
        return await self.client.set(key, encoded_value, ex=ttl)

    async def delete(self, key: str) -> bool:
        result = await self.client.delete(key)
        return result > 0

    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> dict[str, Optional[Any]]:
        if not keys:
            return {}
        
        values = await self.client.mget(keys)
        results = {}

        for key, value in zip(keys, values):
            if value is None:
                results[key] = default
            else:
                results[key] = self._deserialize(value)
        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        if not items:
            return {}

        pipeline = self.client.pipeline()
        results = {}

        for key, value in items.items():
            encoded_value = self._serialize(value)
            pipeline.set(key, encoded_value, ex=ttl)
            results[key] = True

        await pipeline.execute()
        return results

    def lock(self, name: str, timeout: float = 30.0, blocking_timeout: Optional[float] = None) -> Lock:
        """
        Returns an Async Redis Lock object to be used with `async with`.
        
        :param name: The key name for the lock (e.g., 'lock:my_resource').
        :param timeout: Maximum lifespan of the lock in seconds (prevents deadlocks if app crashes).
        :param blocking_timeout: How long to wait to acquire the lock. None waits forever.
        """
        return self.client.lock(name=name, timeout=timeout, blocking_timeout=blocking_timeout)


    async def delete_many(self, keys: list[str]) -> int:
        if not keys:
            return 0
        return await self.client.delete(*keys)
