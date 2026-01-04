import pytest
import pytest_asyncio
from redis.asyncio import Redis

from src.kv_store import RedisStore


@pytest_asyncio.fixture
async def redis_client():
    client = Redis(host="localhost", port=6379, db=0, password="grunge38")
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def redis_store(redis_client):
    return RedisStore(redis_client)


@pytest.mark.asyncio
async def test_set_and_get_dict(redis_store):
    """Test setting and getting a dictionary value."""
    test_key = "test:dict:key"
    test_value = {"name": "John", "age": "30", "city": "NYC"}

    # Set the value
    result = await redis_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the value
    retrieved = await redis_store.get(test_key)
    assert retrieved == {b"name": b"John", b"age": b"30", b"city": b"NYC"}


@pytest.mark.asyncio
async def test_set_and_get_string(redis_store):
    """Test setting and getting a string value."""
    test_key = "test:string:key"
    test_value = "Hello World"

    # Set the value
    result = await redis_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Get the value
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"Hello World"  # Redis returns bytes for string values


@pytest.mark.asyncio
async def test_overwrite_dict_with_string(redis_store):
    """Test setting a dict key and then overwriting it with a string."""
    test_key = "test:overwrite:key"
    dict_value = {"name": "John", "age": "30"}
    string_value = "Hello World"

    # Set dict value first
    result = await redis_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Verify it's stored as dict
    retrieved = await redis_store.get(test_key)
    assert retrieved == {b"name": b"John", b"age": b"30"}

    # Overwrite with string value
    result = await redis_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Get the value - should now be the string
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"Hello World"


@pytest.mark.asyncio
async def test_overwrite_string_with_dict(redis_store):
    """Test setting a string key and then overwriting it with a dict."""
    test_key = "test:overwrite:key2"
    string_value = "Hello World"
    dict_value = {"message": "Hello", "count": "1"}

    # Set string value first
    result = await redis_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Verify it's stored as string
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"Hello World"

    # Overwrite with dict value
    result = await redis_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Get the value - should now be the dict
    retrieved = await redis_store.get(test_key)
    assert retrieved == {b"message": b"Hello", b"count": b"1"}


@pytest.mark.asyncio
async def test_expiration(redis_store):
    """Test that keys expire after TTL."""
    import asyncio

    test_key = "test:expire:key"
    test_value = "This will expire"

    # Set the value with 1 second TTL
    result = await redis_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"This will expire"

    # Sleep for more than 1 second
    await asyncio.sleep(1.1)

    # Get the value - should now be None (expired)
    retrieved = await redis_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_set_get_delete_get_other_types(redis_store):
    """Test set -> get -> delete -> get pattern for data types other than string and dict."""
    test_key = "test:other:types:key"

    # Test with integer
    int_value = 42
    result = await redis_store.set(test_key, int_value, ttl=60)
    assert result is True
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"42"  # Redis converts to bytes

    # Delete the key
    delete_result = await redis_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await redis_store.get(test_key)
    assert retrieved is None

    # Test with float
    float_value = 3.14159
    result = await redis_store.set(test_key, float_value, ttl=60)
    assert result is True
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"3.14159"  # Redis converts to bytes

    # Delete the key
    delete_result = await redis_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await redis_store.get(test_key)
    assert retrieved is None

    # Test with list (will be converted to string)
    list_value = [1, 2, 3, "test"]
    result = await redis_store.set(test_key, list_value, ttl=60)
    assert result is True
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"[1, 2, 3, 'test']"  # Redis converts to bytes

    # Delete the key
    delete_result = await redis_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await redis_store.get(test_key)
    assert retrieved is None
