import asyncpg
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from src.kv_store_py import InMemoryStore, PostgresStore, RedisStore
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


@pytest_asyncio.fixture(scope="function")
async def postgres_pool():
    """Create a Postgres connection pool for testing."""
    try:
        pool = await asyncpg.create_pool(
            test_settings.postgres_dsn,
            min_size=2,
            max_size=5,
        )
    except Exception as e:
        pytest.fail(f"Could not connect to PostgreSQL: {e}")

    yield pool

    await pool.close()


@pytest_asyncio.fixture(scope="function")
async def postgres_store(postgres_pool):
    """Returns an instance of PostgresStore, with table created and cleared after each test."""
    store = PostgresStore(postgres_pool, table_name="kv_store_test")
    await store.create_table()

    yield store

    # Clean up tables after test
    async with postgres_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE kv_store_test")
        await conn.execute("TRUNCATE TABLE kv_store_test_locks")
