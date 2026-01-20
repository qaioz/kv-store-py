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


@pytest.mark.asyncio
async def test_get_with_default_nonexistent_key(memory_store):
    """Test getting a nonexistent key with a default value."""
    test_key = "nonexistent:key"
    default_value = "default_value"

    # Get nonexistent key with default
    retrieved = await memory_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Test with different default types
    assert await memory_store.get("another:nonexistent", default=42) == 42
    assert await memory_store.get("third:nonexistent", default={"key": "value"}) == {"key": "value"}
    assert await memory_store.get("fourth:nonexistent", default=None) is None


@pytest.mark.asyncio
async def test_get_with_default_expired_key(memory_store):
    """Test getting an expired key with a default value."""
    import asyncio
    test_key = "test:expired:default:key"
    test_value = "This will expire"
    default_value = "default_after_expiry"

    # Set the value with 1 second TTL
    result = await memory_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await memory_store.get(test_key)
    assert retrieved == test_value

    # Sleep for more than 1 second to let it expire
    await asyncio.sleep(1.1)

    # Get the expired key with default - should return default
    retrieved = await memory_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Get the expired key without default - should return None
    retrieved = await memory_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_with_default_existing_key(memory_store):
    """Test getting an existing key with a default value (should return actual value)."""
    test_key = "test:existing:default:key"
    test_value = "actual_value"
    default_value = "should_not_be_returned"

    # Set the value
    result = await memory_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the existing key with default - should return actual value, not default
    retrieved = await memory_store.get(test_key, default=default_value)
    assert retrieved == test_value
    assert retrieved != default_value


@pytest.mark.asyncio
async def test_get_many_empty_list(memory_store):
    """Test get_many with empty list returns empty dict."""
    result = await memory_store.get_many([])
    assert result == {}


@pytest.mark.asyncio
async def test_get_many_mixed_keys(memory_store):
    """Test get_many with mixed string and dict keys."""
    string_key = "test:many:string:key"
    dict_key = "test:many:dict:key"
    nonexistent_key = "test:many:nonexistent:key"

    string_value = "Hello World"
    dict_value = {"name": "John", "age": "30"}

    # Set values
    await memory_store.set(string_key, string_value, ttl=60)
    await memory_store.set(dict_key, dict_value, ttl=60)

    # Get many values
    keys = [string_key, dict_key, nonexistent_key]
    results = await memory_store.get_many(keys)

    assert len(results) == 3
    assert results[string_key] == string_value
    assert results[dict_key] == dict_value
    assert results[nonexistent_key] is None


@pytest.mark.asyncio
async def test_get_many_with_default(memory_store):
    """Test get_many with default values for missing keys."""
    existing_key = "test:many:default:existing"
    nonexistent_key = "test:many:default:nonexistent"

    await memory_store.set(existing_key, "existing value", ttl=60)

    keys = [existing_key, nonexistent_key]
    default_value = "my_default"
    results = await memory_store.get_many(keys, default=default_value)

    assert len(results) == 2
    assert results[existing_key] == "existing value"
    assert results[nonexistent_key] == default_value


@pytest.mark.asyncio
async def test_get_many_order_preservation(memory_store):
    """Test that get_many returns values for the correct keys."""
    keys = ["key3", "key1", "key2"]
    values = ["value3", "value1", "value2"]

    # Set values in different order
    for key, value in zip(keys, values):
        await memory_store.set(key, value, ttl=60)

    # Get them back
    results = await memory_store.get_many(keys)
    expected = {"key3": "value3", "key1": "value1", "key2": "value2"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_string_keys(memory_store):
    """Test get_many with only string keys."""
    keys = ["str1", "str2", "str3"]
    values = ["val1", "val2", "val3"]

    for key, value in zip(keys, values):
        await memory_store.set(key, value, ttl=60)

    results = await memory_store.get_many(keys)
    expected = {"str1": "val1", "str2": "val2", "str3": "val3"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_hash_keys(memory_store):
    """Test get_many with only hash/dict keys."""
    keys = ["hash1", "hash2"]
    values = [
        {"a": "1", "b": "2"},
        {"x": "10", "y": "20"}
    ]

    for key, value in zip(keys, values):
        await memory_store.set(key, value, ttl=60)

    results = await memory_store.get_many(keys)

    assert len(results) == 2
    assert results["hash1"] == {"a": "1", "b": "2"}
    assert results["hash2"] == {"x": "10", "y": "20"}


@pytest.mark.asyncio
async def test_get_many_expired_keys(memory_store):
    """Test get_many with expired keys."""
    import asyncio

    key1 = "test:many:expired:1"
    key2 = "test:many:expired:2"

    await memory_store.set(key1, "value1", ttl=1)
    await memory_store.set(key2, "value2", ttl=1)

    # Verify they're set
    results = await memory_store.get_many([key1, key2])
    assert results == {key1: "value1", key2: "value2"}

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Get expired keys with default
    results = await memory_store.get_many([key1, key2], default="expired_default")
    assert results == {key1: "expired_default", key2: "expired_default"}

    # Get expired keys without default
    results = await memory_store.get_many([key1, key2])
    assert results == {key1: None, key2: None}


@pytest.mark.asyncio
async def test_get_many_different_default_types(memory_store):
    """Test get_many with different default value types."""
    existing_key = "test:many:defaults:existing"
    nonexistent_keys = ["missing1", "missing2", "missing3"]

    await memory_store.set(existing_key, "exists", ttl=60)

    keys = [existing_key] + nonexistent_keys

    # Test with string default
    results = await memory_store.get_many(keys, default="string_default")
    assert results[existing_key] == "exists"
    assert all(results[k] == "string_default" for k in nonexistent_keys)

    # Test with dict default
    results = await memory_store.get_many(nonexistent_keys, default={"key": "value"})
    assert all(results[k] == {"key": "value"} for k in nonexistent_keys)

    # Test with None default
    results = await memory_store.get_many(nonexistent_keys, default=None)
    assert all(results[k] is None for k in nonexistent_keys)


@pytest.mark.asyncio
async def test_get_many_mixed_types(memory_store):
    """Test get_many with various data types."""
    keys = ["str", "dict", "list", "int", "float", "missing"]
    values = ["string", {"key": "value"}, [1, 2, 3], 42, 3.14]

    # Set values for existing keys
    for key, value in zip(keys[:-1], values):
        await memory_store.set(key, value, ttl=60)

    results = await memory_store.get_many(keys)

    assert len(results) == 6
    assert results["str"] == "string"
    assert results["dict"] == {"key": "value"}
    assert results["list"] == [1, 2, 3]
    assert results["int"] == 42
    assert results["float"] == 3.14
    assert results["missing"] is None  # missing key


@pytest.mark.asyncio
async def test_set_many_empty_dict(memory_store):
    """Test set_many with empty dictionary."""
    result = await memory_store.set_many({}, ttl=60)
    assert result == {}


@pytest.mark.asyncio
async def test_set_many_mixed_types(memory_store):
    """Test set_many with various data types."""
    items = {
        "string_key": "hello world",
        "dict_key": {"name": "John", "age": 30},
        "list_key": [1, 2, 3, "test"],
        "int_key": 42,
        "float_key": 3.14159
    }

    results = await memory_store.set_many(items, ttl=60)

    # All operations should succeed
    assert all(results.values())
    assert len(results) == 5

    # Verify values were stored correctly
    assert await memory_store.get("string_key") == "hello world"
    assert await memory_store.get("dict_key") == {"name": "John", "age": 30}
    assert await memory_store.get("list_key") == [1, 2, 3, "test"]
    assert await memory_store.get("int_key") == 42
    assert await memory_store.get("float_key") == 3.14159


@pytest.mark.asyncio
async def test_set_many_with_ttl(memory_store):
    """Test set_many with TTL expiration."""
    import asyncio

    items = {
        "key1": "value1",
        "key2": "value2"
    }

    results = await memory_store.set_many(items, ttl=1)

    # All operations should succeed
    assert all(results.values())

    # Verify values are set
    assert await memory_store.get("key1") == "value1"
    assert await memory_store.get("key2") == "value2"

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Verify values are expired
    assert await memory_store.get("key1") is None
    assert await memory_store.get("key2") is None


@pytest.mark.asyncio
async def test_set_many_zero_ttl(memory_store):
    """Test set_many with zero TTL (no expiration)."""
    items = {
        "key1": "value1",
        "key2": "value2"
    }

    results = await memory_store.set_many(items, ttl=0)

    # All operations should succeed
    assert all(results.values())

    # Verify values persist
    assert await memory_store.get("key1") == "value1"
    assert await memory_store.get("key2") == "value2"

    # Wait a bit and check again
    import asyncio
    await asyncio.sleep(0.1)

    assert await memory_store.get("key1") == "value1"
    assert await memory_store.get("key2") == "value2"


@pytest.mark.asyncio
async def test_set_many_overwrite_existing(memory_store):
    """Test set_many overwriting existing keys."""
    # Set initial values
    await memory_store.set("key1", "original1", ttl=60)
    await memory_store.set("key2", "original2", ttl=60)

    # Overwrite with set_many
    items = {
        "key1": "new1",
        "key2": "new2",
        "key3": "new3"
    }

    results = await memory_store.set_many(items, ttl=60)

    # All operations should succeed
    assert all(results.values())
    assert len(results) == 3

    # Verify values were overwritten
    assert await memory_store.get("key1") == "new1"
    assert await memory_store.get("key2") == "new2"
    assert await memory_store.get("key3") == "new3"


@pytest.mark.asyncio
async def test_set_many_return_values(memory_store):
    """Test that set_many returns correct boolean dict."""
    items = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }

    results = await memory_store.set_many(items, ttl=60)

    # Should return dict of True values, one for each item
    assert results == {"key1": True, "key2": True, "key3": True}
    assert len(results) == len(items)


@pytest.mark.asyncio
async def test_delete_many_mixed(memory_store):
    """Test deleting multiple keys, some existing, some not."""
    # Set up keys
    await memory_store.set("del:1", "val1", ttl=60)
    await memory_store.set("del:2", "val2", ttl=60)
    await memory_store.set("del:3", "val3", ttl=60)

    # Delete 2 existing keys and 1 non-existent key
    keys_to_delete = ["del:1", "del:2", "del:nonexistent"]
    count = await memory_store.delete_many(keys_to_delete)

    # Should return 2 (number of keys actually deleted)
    assert count == 2

    # Verify deleted keys are gone
    assert await memory_store.get("del:1") is None
    assert await memory_store.get("del:2") is None
    
    # Verify untouched key remains
    assert await memory_store.get("del:3") == "val3"

@pytest.mark.asyncio
async def test_delete_many_empty(memory_store):
    """Test delete_many with empty list."""
    assert await memory_store.delete_many([]) == 0