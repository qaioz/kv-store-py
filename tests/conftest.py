import pytest
import pytest_asyncio
from redis.asyncio import Redis

from src.kv_store import InMemoryStore, RedisStore
from tests.settings import test_settings


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Create a Redis client once per test session."""
    client = Redis(
        host=test_settings.redis_host,
        port=test_settings.redis_port,
        db=0,
        password=test_settings.redis_password or None,
        decode_responses=False,
    )

    try:
        await client.ping()
    except Exception as e:
        pytest.fail(f"Could not connect to Redis: {e}")

    yield client

    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def redis_store(redis_client):
    """Returns an instance of RedisStore, cleared after each test."""
    yield RedisStore(redis_client)
    await redis_client.flushdb()


@pytest_asyncio.fixture
async def memory_store():
    return InMemoryStore()
