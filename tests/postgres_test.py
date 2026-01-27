import asyncio

import pytest


@pytest.mark.asyncio
async def test_set_and_get_dict(postgres_store):
    """Test setting and getting a dictionary value."""
    test_key = "test:dict:key"
    test_value = {"name": "John", "age": "30", "city": "NYC"}

    # Set the value
    result = await postgres_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the value
    retrieved = await postgres_store.get(test_key)
    assert retrieved == {"name": "John", "age": "30", "city": "NYC"}


@pytest.mark.asyncio
async def test_set_and_get_string(postgres_store):
    """Test setting and getting a string value."""
    test_key = "test:string:key"
    test_value = "Hello World"

    # Set the value
    result = await postgres_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Get the value
    retrieved = await postgres_store.get(test_key)
    assert retrieved == "Hello World"


@pytest.mark.asyncio
async def test_overwrite_dict_with_string(postgres_store):
    """Test setting a dict key and then overwriting it with a string."""
    test_key = "test:overwrite:key"
    dict_value = {"name": "John", "age": "30"}
    string_value = "Hello World"

    # Set dict value first
    result = await postgres_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Verify it's stored as dict
    retrieved = await postgres_store.get(test_key)
    assert retrieved == {"name": "John", "age": "30"}

    # Overwrite with string value
    result = await postgres_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Get the value - should now be the string
    retrieved = await postgres_store.get(test_key)
    assert retrieved == "Hello World"


@pytest.mark.asyncio
async def test_overwrite_string_with_dict(postgres_store):
    """Test setting a string key and then overwriting it with a dict."""
    test_key = "test:overwrite:key2"
    string_value = "Hello World"
    dict_value = {"message": "Hello", "count": "1"}

    # Set string value first
    result = await postgres_store.set(test_key, string_value, ttl=60)
    assert result is True

    # Verify it's stored as string
    retrieved = await postgres_store.get(test_key)
    assert retrieved == "Hello World"

    # Overwrite with dict value
    result = await postgres_store.set(test_key, dict_value, ttl=60)
    assert result is True

    # Get the value - should now be the dict
    retrieved = await postgres_store.get(test_key)
    assert retrieved == {"message": "Hello", "count": "1"}


@pytest.mark.asyncio
async def test_expiration(postgres_store):
    """Test that keys expire after TTL."""
    test_key = "test:expire:key"
    test_value = "This will expire"

    # Set the value with 1 second TTL
    result = await postgres_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await postgres_store.get(test_key)
    assert retrieved == "This will expire"

    # Sleep for more than 1 second
    await asyncio.sleep(1.1)

    # Get the value - should now be None (expired)
    retrieved = await postgres_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_set_get_delete_get_other_types(postgres_store):
    """Test set -> get -> delete -> get pattern for data types other than string and dict."""
    test_key = "test:other:types:key"

    # Test with integer
    int_value = 42
    result = await postgres_store.set(test_key, int_value, ttl=60)
    assert result is True
    retrieved = await postgres_store.get(test_key)
    assert retrieved == 42

    # Delete the key
    delete_result = await postgres_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await postgres_store.get(test_key)
    assert retrieved is None

    # Test with float
    float_value = 3.14159
    result = await postgres_store.set(test_key, float_value, ttl=60)
    assert result is True
    retrieved = await postgres_store.get(test_key)
    assert retrieved == 3.14159

    # Delete the key
    delete_result = await postgres_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await postgres_store.get(test_key)
    assert retrieved is None

    # Test with list
    list_value = [1, 2, 3, "test"]
    result = await postgres_store.set(test_key, list_value, ttl=60)
    assert result is True
    retrieved = await postgres_store.get(test_key)
    assert retrieved == list_value

    # Delete the key
    delete_result = await postgres_store.delete(test_key)
    assert delete_result is True

    # Get after delete - should be None
    retrieved = await postgres_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_with_default_nonexistent_key(postgres_store):
    """Test getting a nonexistent key with a default value."""
    test_key = "nonexistent:key"
    default_value = "default_value"

    # Get nonexistent key with default
    retrieved = await postgres_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Test with different default types
    assert await postgres_store.get("another:nonexistent", default=42) == 42
    assert await postgres_store.get("third:nonexistent", default={"key": "value"}) == {
        "key": "value"
    }
    assert await postgres_store.get("fourth:nonexistent", default=None) is None


@pytest.mark.asyncio
async def test_get_with_default_expired_key(postgres_store):
    """Test getting an expired key with a default value."""
    test_key = "test:expired:default:key"
    test_value = "This will expire"
    default_value = "default_after_expiry"

    # Set the value with 1 second TTL
    result = await postgres_store.set(test_key, test_value, ttl=1)
    assert result is True

    # Verify it's stored
    retrieved = await postgres_store.get(test_key)
    assert retrieved == "This will expire"

    # Sleep for more than 1 second to let it expire
    await asyncio.sleep(1.1)

    # Get the expired key with default - should return default
    retrieved = await postgres_store.get(test_key, default=default_value)
    assert retrieved == default_value

    # Get the expired key without default - should return None
    retrieved = await postgres_store.get(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_with_default_existing_key(postgres_store):
    """Test getting an existing key with a default value (should return actual value)."""
    test_key = "test:existing:default:key"
    test_value = "Hello World"
    default_value = "should_not_be_returned"

    # Set the value
    result = await postgres_store.set(test_key, test_value, ttl=60)
    assert result is True

    # Get the existing key with default - should return actual value, not default
    retrieved = await postgres_store.get(test_key, default=default_value)
    assert retrieved == "Hello World"
    assert retrieved != default_value


@pytest.mark.asyncio
async def test_get_many_empty_list(postgres_store):
    """Test get_many with empty list returns empty dict."""
    result = await postgres_store.get_many([])
    assert result == {}


@pytest.mark.asyncio
async def test_get_many_mixed_keys(postgres_store):
    """Test get_many with mixed string and dict keys."""
    string_key = "test:many:string:key"
    dict_key = "test:many:dict:key"
    nonexistent_key = "test:many:nonexistent:key"

    string_value = "Hello World"
    dict_value = {"name": "John", "age": "30"}

    # Set values
    await postgres_store.set(string_key, string_value, ttl=60)
    await postgres_store.set(dict_key, dict_value, ttl=60)

    # Get many values
    keys = [string_key, dict_key, nonexistent_key]
    results = await postgres_store.get_many(keys)

    assert len(results) == 3
    assert results[string_key] == "Hello World"
    assert results[dict_key] == {"name": "John", "age": "30"}
    assert results[nonexistent_key] is None


@pytest.mark.asyncio
async def test_get_many_with_default(postgres_store):
    """Test get_many with default values for missing keys."""
    existing_key = "test:many:default:existing"
    nonexistent_key = "test:many:default:nonexistent"

    await postgres_store.set(existing_key, "existing value", ttl=60)

    keys = [existing_key, nonexistent_key]
    default_value = "my_default"
    results = await postgres_store.get_many(keys, default=default_value)

    assert len(results) == 2
    assert results[existing_key] == "existing value"
    assert results[nonexistent_key] == default_value


@pytest.mark.asyncio
async def test_get_many_order_preservation(postgres_store):
    """Test that get_many returns values for the correct keys."""
    keys = ["key3", "key1", "key2"]
    values = ["value3", "value1", "value2"]

    # Set values in different order
    for key, value in zip(keys, values):
        await postgres_store.set(key, value, ttl=60)

    # Get them back
    results = await postgres_store.get_many(keys)
    expected = {"key3": "value3", "key1": "value1", "key2": "value2"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_string_keys(postgres_store):
    """Test get_many with only string keys."""
    keys = ["str1", "str2", "str3"]
    values = ["val1", "val2", "val3"]

    for key, value in zip(keys, values):
        await postgres_store.set(key, value, ttl=60)

    results = await postgres_store.get_many(keys)
    expected = {"str1": "val1", "str2": "val2", "str3": "val3"}

    assert results == expected


@pytest.mark.asyncio
async def test_get_many_only_hash_keys(postgres_store):
    """Test get_many with only hash/dict keys."""
    keys = ["hash1", "hash2"]
    values = [{"a": "1", "b": "2"}, {"x": "10", "y": "20"}]

    for key, value in zip(keys, values):
        await postgres_store.set(key, value, ttl=60)

    results = await postgres_store.get_many(keys)

    assert len(results) == 2
    assert results["hash1"] == {"a": "1", "b": "2"}
    assert results["hash2"] == {"x": "10", "y": "20"}


@pytest.mark.asyncio
async def test_get_many_expired_keys(postgres_store):
    """Test get_many with expired keys."""
    key1 = "test:many:expired:1"
    key2 = "test:many:expired:2"

    await postgres_store.set(key1, "value1", ttl=1)
    await postgres_store.set(key2, "value2", ttl=1)

    # Verify they're set
    results = await postgres_store.get_many([key1, key2])
    assert results == {key1: "value1", key2: "value2"}

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Get expired keys with default
    results = await postgres_store.get_many([key1, key2], default="expired_default")
    assert results == {key1: "expired_default", key2: "expired_default"}

    # Get expired keys without default
    results = await postgres_store.get_many([key1, key2])
    assert results == {key1: None, key2: None}


@pytest.mark.asyncio
async def test_get_many_different_default_types(postgres_store):
    """Test get_many with different default value types."""
    existing_key = "test:many:defaults:existing"
    nonexistent_keys = ["missing1", "missing2", "missing3"]

    await postgres_store.set(existing_key, "exists", ttl=60)

    keys = [existing_key] + nonexistent_keys

    # Test with string default
    results = await postgres_store.get_many(keys, default="string_default")
    assert results[existing_key] == "exists"
    assert all(results[k] == "string_default" for k in nonexistent_keys)

    # Test with dict default
    results = await postgres_store.get_many(nonexistent_keys, default={"key": "value"})
    assert all(results[k] == {"key": "value"} for k in nonexistent_keys)

    # Test with None default
    results = await postgres_store.get_many(nonexistent_keys, default=None)
    assert all(results[k] is None for k in nonexistent_keys)


@pytest.mark.asyncio
async def test_lock_acquire_and_release(postgres_store):
    """Test that the context manager acquires and releases the lock."""
    lock_name = "test:lock:basic"

    # Acquire lock
    async with postgres_store.lock(lock_name):
        # We're inside the lock - just verify we got here
        assert True

    # Lock should be released after exiting block


@pytest.mark.asyncio
async def test_lock_mutual_exclusion(postgres_store):
    """Test that two locks on the same name cannot be held simultaneously."""
    lock_name = "test:lock:exclusion"

    async with postgres_store.lock(lock_name):
        # While holding the lock, try to acquire it again with blocking_timeout=0
        with pytest.raises(TimeoutError):
            async with postgres_store.lock(lock_name, blocking_timeout=0):
                pass


@pytest.mark.asyncio
async def test_lock_blocking_timeout_success(postgres_store):
    """Test that we successfully acquire the lock after waiting for it to free up."""
    lock_name = "test:lock:wait"

    # Create a background task that holds the lock for only 0.5 seconds
    async def hold_lock_task():
        async with postgres_store.lock(lock_name):
            await asyncio.sleep(0.5)

    # Start the background task
    task = asyncio.create_task(hold_lock_task())

    # Give the task a moment to acquire the lock
    await asyncio.sleep(0.1)

    # Try to acquire the lock with a 2.0s timeout.
    # Since the other task releases it in 0.5s, this should succeed.
    try:
        async with postgres_store.lock(lock_name, blocking_timeout=2.0):
            # If we reached here, we successfully waited and acquired the lock
            assert True
    finally:
        await task


@pytest.mark.asyncio
async def test_delete_many_mixed(postgres_store):
    """Test deleting multiple keys, some existing, some not."""
    # Set up keys
    await postgres_store.set("del:1", "val1", ttl=60)
    await postgres_store.set("del:2", "val2", ttl=60)
    await postgres_store.set("del:3", "val3", ttl=60)

    # Delete 2 existing keys and 1 non-existent key
    keys_to_delete = ["del:1", "del:2", "del:nonexistent"]
    count = await postgres_store.delete_many(keys_to_delete)

    # Should return 2 (number of keys actually deleted)
    assert count == 2

    # Verify deleted keys are gone
    assert await postgres_store.get("del:1") is None
    assert await postgres_store.get("del:2") is None

    # Verify untouched key remains
    assert await postgres_store.get("del:3") == "val3"


@pytest.mark.asyncio
async def test_delete_many_empty(postgres_store):
    """Test delete_many with empty list."""
    assert await postgres_store.delete_many([]) == 0


@pytest.mark.asyncio
async def test_get_many_with_list_of_defaults(postgres_store):
    """Test get_many with a list of default values (one per key)."""
    existing_key = "test:many:list:existing"
    missing_key1 = "test:many:list:missing1"
    missing_key2 = "test:many:list:missing2"

    await postgres_store.set(existing_key, "actual_value", ttl=60)

    keys = [existing_key, missing_key1, missing_key2]
    defaults = ["default1", "default2", "default3"]

    results = await postgres_store.get_many(keys, default=defaults)

    assert len(results) == 3
    assert results[existing_key] == "actual_value"  # actual value, not default
    assert results[missing_key1] == "default2"  # second default
    assert results[missing_key2] == "default3"  # third default


@pytest.mark.asyncio
async def test_get_many_with_list_of_defaults_all_missing(postgres_store):
    """Test get_many with list of defaults when all keys are missing."""
    keys = ["missing1", "missing2", "missing3"]
    defaults = ["def1", "def2", "def3"]

    results = await postgres_store.get_many(keys, default=defaults)

    assert results == {"missing1": "def1", "missing2": "def2", "missing3": "def3"}


@pytest.mark.asyncio
async def test_get_many_with_list_of_defaults_mixed_types(postgres_store):
    """Test get_many with list of defaults containing different types."""
    keys = ["key1", "key2", "key3"]
    defaults = ["string_default", {"dict": "default"}, 42]

    results = await postgres_store.get_many(keys, default=defaults)

    assert results["key1"] == "string_default"
    assert results["key2"] == {"dict": "default"}
    assert results["key3"] == 42


@pytest.mark.asyncio
async def test_get_many_list_default_length_mismatch_uses_single(postgres_store):
    """Test that if default list length doesn't match keys, it's treated as single value."""
    keys = ["key1", "key2", "key3"]
    defaults = ["a", "b"]  # Length 2, but 3 keys

    results = await postgres_store.get_many(keys, default=defaults)

    # Should use the list as single default for all keys
    assert results["key1"] == ["a", "b"]
    assert results["key2"] == ["a", "b"]
    assert results["key3"] == ["a", "b"]


# --- Resource Management Tests ---


@pytest.mark.asyncio
async def test_from_url_creates_working_store():
    """Test that from_url creates a functional store."""
    from src.kv_store import PostgresStore
    from tests.settings import test_settings

    store = await PostgresStore.from_url(test_settings.postgres_dsn)
    try:
        await store.create_table()
        # Verify it works
        await store.set("test:from_url", "value", ttl=60)
        result = await store.get("test:from_url")
        assert result == "value"
        await store.delete("test:from_url")
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_from_url_with_context_manager():
    """Test that from_url works with async context manager."""
    from src.kv_store import PostgresStore
    from tests.settings import test_settings

    async with await PostgresStore.from_url(test_settings.postgres_dsn) as store:
        await store.create_table()
        await store.set("test:context_manager", "value", ttl=60)
        result = await store.get("test:context_manager")
        assert result == "value"
        await store.delete("test:context_manager")
    # Connection pool should be closed after exiting context


@pytest.mark.asyncio
async def test_injected_pool_not_closed_by_store(postgres_pool):
    """Test that an injected pool is NOT closed when store.close() is called."""
    from src.kv_store import PostgresStore

    store = PostgresStore(postgres_pool)
    await store.close()

    # Pool should still be usable
    async with postgres_pool.acquire() as conn:
        await conn.fetchval("SELECT 1")


@pytest.mark.asyncio
async def test_context_manager_with_injected_pool(postgres_pool):
    """Test context manager with injected pool doesn't close the pool."""
    from src.kv_store import PostgresStore

    async with PostgresStore(postgres_pool, table_name="kv_store_test") as store:
        await store.create_table()
        await store.set("test:injected_ctx", "value", ttl=60)

    # Pool should still work after context manager exits
    async with postgres_pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT value FROM kv_store_test WHERE key = $1", "test:injected_ctx"
        )
        assert result is not None


@pytest.mark.asyncio
async def test_cleanup_expired(postgres_store):
    """Test cleanup_expired removes expired entries."""
    # Set some values with short TTL
    await postgres_store.set("expire1", "value1", ttl=1)
    await postgres_store.set("expire2", "value2", ttl=1)
    await postgres_store.set("keep", "value3", ttl=60)

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Run cleanup
    deleted_count = await postgres_store.cleanup_expired()

    # Should have deleted 2 expired entries
    assert deleted_count == 2

    # Verify expired keys are gone
    assert await postgres_store.get("expire1") is None
    assert await postgres_store.get("expire2") is None

    # Verify non-expired key remains
    assert await postgres_store.get("keep") == "value3"


@pytest.mark.asyncio
async def test_set_many(postgres_store):
    """Test setting multiple values at once."""
    items = {
        "multi1": "value1",
        "multi2": {"nested": "dict"},
        "multi3": [1, 2, 3],
    }

    results = await postgres_store.set_many(items, ttl=60)

    # All should succeed
    assert results == {"multi1": True, "multi2": True, "multi3": True}

    # Verify values
    assert await postgres_store.get("multi1") == "value1"
    assert await postgres_store.get("multi2") == {"nested": "dict"}
    assert await postgres_store.get("multi3") == [1, 2, 3]


@pytest.mark.asyncio
async def test_set_many_empty(postgres_store):
    """Test set_many with empty dict."""
    results = await postgres_store.set_many({}, ttl=60)
    assert results == {}
