from src.kv_store import RedisStore
from redis.asyncio import Redis
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def redis_client():
    client = Redis(host="localhost", port=6379, db=0, password='grunge38')
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


@pytest.mark.asyncio
async def test_get_with_default_nonexistent_key(redis_store):
    """Test getting a nonexistent key with a default value."""
    test_key = "nonexistent:key"
    default_value = "default_value"

    # Get nonexistent key with default
    retrieved = await redis_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Test with different default types
    assert await redis_store.get("another:nonexistent", default=42) == 42
    assert await redis_store.get("third:nonexistent", default={"key": "value"}) == {"key": "value"}
    assert await redis_store.get("fourth:nonexistent", default=None) is None


@pytest.mark.asyncio
async def test_get_with_default_expired_key(redis_store):
    """Test getting an expired key with a default value."""
    import asyncio
    test_key = "test:expired:default:key"
    test_value = "This will expire"
    default_value = "default_after_expiry"

    # Set the value with 1 second TTL
    result = await redis_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await redis_store.get(test_key)
    assert retrieved == b"This will expire"

    # Sleep for more than 1 second to let it expire
    await asyncio.sleep(1.1)

    # Get the expired key with default - should return default
    retrieved = await redis_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Get the expired key without default - should return None
    retrieved = await redis_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_with_default_existing_key(redis_store):
    """Test getting an existing key with a default value (should return actual value)."""
    test_key = "test:existing:default:key"
    test_value = "Hello World"
    default_value = "should_not_be_returned"

    # Set the value
    result = await redis_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the existing key with default - should return actual value, not default
    retrieved = await redis_store.get(test_key, default=default_value)
    assert retrieved == b"Hello World"  # Redis returns bytes
    assert retrieved != default_value


@pytest.mark.asyncio
async def test_get_many_empty_list(redis_store):
    """Test get_many with empty list returns empty dict."""
    result = await redis_store.get_many([])
    assert result == {}


@pytest.mark.asyncio
async def test_get_many_mixed_keys(redis_store):
    """Test get_many with mixed string and dict keys."""
    string_key = "test:many:string:key"
    dict_key = "test:many:dict:key"
    nonexistent_key = "test:many:nonexistent:key"

    string_value = "Hello World"
    dict_value = {"name": "John", "age": "30"}

    # Set values
    await redis_store.set(string_key, string_value, ttl=60)
    await redis_store.set(dict_key, dict_value, ttl=60)

    # Get many values
    keys = [string_key, dict_key, nonexistent_key]
    results = await redis_store.get_many(keys)

    assert len(results) == 3
    assert results[string_key] == b"Hello World"
    assert results[dict_key] == {b"name": b"John", b"age": b"30"}
    assert results[nonexistent_key] is None


@pytest.mark.asyncio
async def test_get_many_with_default(redis_store):
    """Test get_many with default values for missing keys."""
    existing_key = "test:many:default:existing"
    nonexistent_key = "test:many:default:nonexistent"

    await redis_store.set(existing_key, "existing value", ttl=60)

    keys = [existing_key, nonexistent_key]
    default_value = "my_default"
    results = await redis_store.get_many(keys, default=default_value)

    assert len(results) == 2
    assert results[existing_key] == b"existing value"
    assert results[nonexistent_key] == default_value


@pytest.mark.asyncio
async def test_get_many_order_preservation(redis_store):
    """Test that get_many returns values for the correct keys."""
    keys = ["key3", "key1", "key2"]
    values = ["value3", "value1", "value2"]

    # Set values in different order
    for key, value in zip(keys, values):
        await redis_store.set(key, value, ttl=60)

    # Get them back
    results = await redis_store.get_many(keys)
    expected = {"key3": b"value3", "key1": b"value1", "key2": b"value2"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_string_keys(redis_store):
    """Test get_many with only string keys."""
    keys = ["str1", "str2", "str3"]
    values = ["val1", "val2", "val3"]

    for key, value in zip(keys, values):
        await redis_store.set(key, value, ttl=60)

    results = await redis_store.get_many(keys)
    expected = {"str1": b"val1", "str2": b"val2", "str3": b"val3"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_hash_keys(redis_store):
    """Test get_many with only hash/dict keys."""
    keys = ["hash1", "hash2"]
    values = [
        {"a": "1", "b": "2"},
        {"x": "10", "y": "20"}
    ]

    for key, value in zip(keys, values):
        await redis_store.set(key, value, ttl=60)

    results = await redis_store.get_many(keys)

    assert len(results) == 2
    assert results["hash1"] == {b"a": b"1", b"b": b"2"}
    assert results["hash2"] == {b"x": b"10", b"y": b"20"}


@pytest.mark.asyncio
async def test_get_many_expired_keys(redis_store):
    """Test get_many with expired keys."""
    import asyncio

    key1 = "test:many:expired:1"
    key2 = "test:many:expired:2"

    await redis_store.set(key1, "value1", ttl=1)
    await redis_store.set(key2, "value2", ttl=1)

    # Verify they're set
    results = await redis_store.get_many([key1, key2])
    assert results == {key1: b"value1", key2: b"value2"}

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Get expired keys with default
    results = await redis_store.get_many([key1, key2], default="expired_default")
    assert results == {key1: "expired_default", key2: "expired_default"}

    # Get expired keys without default
    results = await redis_store.get_many([key1, key2])
    assert results == {key1: None, key2: None}


@pytest.mark.asyncio
async def test_get_many_different_default_types(redis_store):
    """Test get_many with different default value types."""
    existing_key = "test:many:defaults:existing"
    nonexistent_keys = ["missing1", "missing2", "missing3"]

    await redis_store.set(existing_key, "exists", ttl=60)

    keys = [existing_key] + nonexistent_keys

    # Test with string default
    results = await redis_store.get_many(keys, default="string_default")
    assert results[existing_key] == b"exists"
    assert all(results[k] == "string_default" for k in nonexistent_keys)

    # Test with dict default
    results = await redis_store.get_many(nonexistent_keys, default={"key": "value"})
    assert all(results[k] == {"key": "value"} for k in nonexistent_keys)

    # Test with None default
    results = await redis_store.get_many(nonexistent_keys, default=None)
    assert all(results[k] is None for k in nonexistent_keys)


