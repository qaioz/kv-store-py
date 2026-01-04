from typing import Optional, Any
import redis.asyncio as redis
from .base import AbstractStore

class RedisStore(AbstractStore):
    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str) -> Optional[Any]:
        key_type = await self.client.type(key)

        if key_type == b'hash':
            return await self.client.hgetall(key)
        elif key_type == b'string':
            return await self.client.get(key)
        else:
            return None

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