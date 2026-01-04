from src.kv_store import InMemoryStore
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def memory_store():
    return InMemoryStore()


@pytest.mark.asyncio
async def test_set_and_get_dict(memory_store):
    """Test setting and getting a dictionary value."""
    test_key = "test:dict:key"
    test_value = {"name": "John", "age": "30", "city": "NYC"}

    # Set the value
    result = await memory_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the value
    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value


@pytest.mark.asyncio
async def test_set_and_get_string(memory_store):
    """Test setting and getting a string value."""
    test_key = "test:string:key"
    test_value = "Hello World"

    # Set the value
    result = await memory_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Get the value
    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value  # InMemoryStore returns the actual string


@pytest.mark.asyncio
async def test_overwrite_dict_with_string(memory_store):
    """Test setting a dict key and then overwriting it with a string."""
    test_key = "test:overwrite:key"
    dict_value = {"name": "John", "age": "30"}
    string_value = "Hello World"

    # Set dict value first
    result = await memory_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Verify it's stored as dict
    retrieved = await memory_store.get(test_key)
    assert retrieved == dict_value

    # Overwrite with string value
    result = await memory_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Get the value - should now be the string
    retrieved = await memory_store.get(test_key)
    assert retrieved == string_value


@pytest.mark.asyncio
async def test_overwrite_string_with_dict(memory_store):
    """Test setting a string key and then overwriting it with a dict."""
    test_key = "test:overwrite:key2"
    string_value = "Hello World"
    dict_value = {"message": "Hello", "count": "1"}

    # Set string value first
    result = await memory_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Verify it's stored as string
    retrieved = await memory_store.get(test_key)
    assert retrieved == string_value

    # Overwrite with dict value
    result = await memory_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Get the value - should now be the dict
    retrieved = await memory_store.get(test_key)
    assert retrieved == dict_value


@pytest.mark.asyncio
async def test_expiration(memory_store):
    """Test that keys expire after TTL."""
    import asyncio
    test_key = "test:expire:key"
    test_value = "This will expire"

    # Set the value with 1 second TTL
    result = await memory_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value

    # Sleep for more than 1 second
    await asyncio.sleep(1.1)

    # Get the value - should now be None (expired)
    retrieved = await memory_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_nonexistent_key(memory_store):
    """Test getting a key that doesn't exist."""
    retrieved = await memory_store.get("nonexistent:key")
    assert retrieved is None


@pytest.mark.asyncio
async def test_set_with_zero_ttl(memory_store):
    """Test setting a value with TTL=0 (no expiration)."""
    test_key = "test:zero:ttl:key"
    test_value = "No expiration"

    # Set the value with 0 TTL (no expiration)
    result = await memory_store.set(test_key, test_value, ttl=0)
    assert result is True

    # Get the value - should persist
    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value

    # Sleep for a bit and check again
    import asyncio
    await asyncio.sleep(0.1)

    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value


@pytest.mark.asyncio
async def test_multiple_keys(memory_store):
    """Test storing multiple keys with different types."""
    # Set different types of values
    await memory_store.set("key1", "string value", ttl=60)
    await memory_store.set("key2", {"dict": "value"}, ttl=60)
    await memory_store.set("key3", [1, 2, 3], ttl=60)
    await memory_store.set("key4", 42, ttl=60)

    # Retrieve and verify all values
    assert await memory_store.get("key1") == "string value"
    assert await memory_store.get("key2") == {"dict": "value"}
    assert await memory_store.get("key3") == [1, 2, 3]
    assert await memory_store.get("key4") == 42


@pytest.mark.asyncio
async def test_set_get_delete_get_other_types(memory_store):
    """Test set -> get -> delete -> get pattern for data types other than string and dict."""
    test_key = "test:other:types:key"

    # Test with integer
    int_value = 42
    result = await memory_store.set(test_key, int_value, ttl=60)
    assert result is True
    retrieved = await memory_store.get(test_key)
    assert retrieved == int_value  # InMemoryStore preserves types

    # Delete the key
    delete_result = await memory_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await memory_store.get(test_key)
    assert retrieved is None

    # Test with float
    float_value = 3.14159
    result = await memory_store.set(test_key, float_value, ttl=60)
    assert result is True
    retrieved = await memory_store.get(test_key)
    assert retrieved == float_value  # InMemoryStore preserves types

    # Delete the key
    delete_result = await memory_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await memory_store.get(test_key)
    assert retrieved is None

    # Test with list
    list_value = [1, 2, 3, "test"]
    result = await memory_store.set(test_key, list_value, ttl=60)
    assert result is True
    retrieved = await memory_store.get(test_key)
    assert retrieved == list_value  # InMemoryStore preserves types

    # Delete the key
    delete_result = await memory_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await memory_store.get(test_key)
    assert retrieved is None
