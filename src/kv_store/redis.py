from typing import Optional, Any
import redis.asyncio as redis
import json
from .base import AbstractStore

class RedisStore(AbstractStore):
    def __init__(self, client: redis.Redis):
        self.client = client

    def _serialize(self, value: Any) -> Any:
        """
        Helper: Convert Python objects to JSON strings for Redis.
        All types are JSON encoded to preserve their original Python types.
        """
        if isinstance(value, bytes):
            return value
        else:
            # JSON encode everything to preserve types
            return json.dumps(value)

    def _deserialize(self, value: Any) -> Any:
        """
        Helper: Convert Redis strings back to Python objects.
        All values are JSON decoded to restore their original Python types.
        """
        if value is None:
            return None

        # Redis returns bytes by default.
        if isinstance(value, bytes):
            value = value.decode('utf-8')

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Fallback: If data in Redis wasn't JSON (maybe created by another app),
            # return it as a raw string so the app doesn't crash.
            return value

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        value = await self.client.get(key)
        
        if value is None:
            return default
            
        return self._deserialize(value)

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        # Serialize first
        encoded_value = self._serialize(value)
        
        # Save to Redis
        return await self.client.set(key, encoded_value, ex=ttl)

    async def delete(self, key: str) -> bool:
        result = await self.client.delete(key)
        return result > 0

    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> dict[str, Optional[Any]]:
        if not keys:
            return {}

        # Get all raw values from Redis
        values = await self.client.mget(keys)
        results = {}

        for key, value in zip(keys, values):
            if value is None:
                results[key] = default
            else:
                # Reuse the exact same logic as get()
                results[key] = self._deserialize(value)

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        if not items:
            return {}

        pipeline = self.client.pipeline()
        results = {}

        for key, value in items.items():
            # Reuse the exact same logic as set()
            encoded_value = self._serialize(value)
            
            pipeline.set(key, encoded_value, ex=ttl)
            results[key] = True

        await pipeline.execute()
        return results