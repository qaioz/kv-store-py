from typing import Optional, Any
import redis.asyncio as redis
import json
from .base import AbstractStore

class RedisStore(AbstractStore):
    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        value = await self.client.get(key)
        if value is None:
            return default

        # Try to deserialize if it's a JSON string
        if isinstance(value, bytes):
            value = value.decode('utf-8')

        try:
            # Check if it looks like JSON (starts with '{' or '[')
            if value.startswith(('{', '[')):
                return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass

        return value

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        # Serialize complex types to JSON
        if isinstance(value, dict):
            value = json.dumps(value)
        elif not isinstance(value, (str, bytes, int, float)):
            value = str(value)

        return await self.client.set(key, value, ex=ttl)


    async def delete(self, key: str) -> bool:
        result = await self.client.delete(key)
        return result > 0

    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> dict[str, Optional[Any]]:
        """Get multiple values from the store."""
        if not keys:
            return {}

        # Get all values at once
        values = await self.client.mget(keys)

        # Initialize results with defaults
        results = {key: default for key in keys}

        # Process each value, attempting deserialization where appropriate
        for key, value in zip(keys, values):
            if value is not None:
                # Try to deserialize if it's a JSON string
                if isinstance(value, bytes):
                    value = value.decode('utf-8')

                try:
                    # Check if it looks like JSON (starts with '{' or '[')
                    if value.startswith(('{', '[')):
                        results[key] = json.loads(value)
                    else:
                        results[key] = value
                except (json.JSONDecodeError, TypeError):
                    results[key] = value

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        pipeline = self.client.pipeline()
        results = {}

        for key, value in items.items():
            # Serialize complex types to JSON
            if isinstance(value, dict):
                value = json.dumps(value)
            elif not isinstance(value, (str, bytes, int, float)):
                value = str(value)

            pipeline.set(key, value, ex=ttl)
            results[key] = True

        await pipeline.execute()
        return results