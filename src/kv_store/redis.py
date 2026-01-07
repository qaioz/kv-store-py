from typing import Optional, Any
import redis.asyncio as redis
from .base import AbstractStore

class RedisStore(AbstractStore):
    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        key_type = await self.client.type(key)

        if key_type == b'hash':
            return await self.client.hgetall(key)
        elif key_type == b'string':
            return await self.client.get(key)
        else:
            return default

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        if isinstance(value, dict):
            key_type = await self.client.type(key)
            if key_type != b'hash' and key_type != b'none':
                await self.client.delete(key)
            await self.client.hset(key, mapping=value)
            return await self.client.expire(key, ttl)
        else:
            key_type = await self.client.type(key)
            if key_type != b'string' and key_type != b'none':
                await self.client.delete(key)
            return await self._set_non_dict(key, value, ttl)

    async def _set_non_dict(self, key: str, value: Any, ttl: int) -> bool:
        if not isinstance(value, (str, bytes, int, float)):
            value = str(value)
        return await self.client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> bool:
        result = await self.client.delete(key)
        return result > 0

    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> dict[str, Optional[Any]]:
        """Get multiple values from the store."""
        if not keys:
            return {}

        # Get types for all keys first
        pipeline = self.client.pipeline()
        for key in keys:
            pipeline.type(key)

        # Execute to get all key types
        types_results = await pipeline.execute()

        # Separate keys by type
        string_keys = []
        hash_keys = []
        key_to_type = {}

        for key, key_type in zip(keys, types_results):
            key_to_type[key] = key_type
            if key_type == b'string':
                string_keys.append(key)
            elif key_type == b'hash':
                hash_keys.append(key)

        # Initialize results with defaults
        results = {key: default for key in keys}

        # Batch get string values using MGET
        if string_keys:
            string_values = await self.client.mget(string_keys)
            for key, value in zip(string_keys, string_values):
                results[key] = value

        # Batch get hash values using pipelined HGETALL
        if hash_keys:
            hash_pipeline = self.client.pipeline()
            for key in hash_keys:
                hash_pipeline.hgetall(key)
            hash_results = await hash_pipeline.execute()

            for key, hash_value in zip(hash_keys, hash_results):
                results[key] = hash_value if hash_value else default

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        results = {}
        pipeline = self.client.pipeline()

        for key, value in items.items():
            if isinstance(value, dict):
                # Handle dict values with hset
                key_type = await self.client.type(key)
                if key_type != b'hash' and key_type != b'none':
                    pipeline.delete(key)
                pipeline.hset(key, mapping=value)
                pipeline.expire(key, ttl)
                results[key] = True  # We'll check this after execution
            else:
                # Handle simple values - convert to string if needed
                if not isinstance(value, (str, bytes, int, float)):
                    value = str(value)
                # Use set command for each simple value with TTL
                pipeline.set(key, value, ex=ttl)
                results[key] = True

        await pipeline.execute()
        return results