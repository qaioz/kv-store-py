# kv-store

[![CI](https://github.com/qaioz/kv-store/actions/workflows/ci.yml/badge.svg)](https://github.com/qaioz/kv-store/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/kv-store-py.svg)](https://pypi.org/project/kv-store-py/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified async interface for key-value stores in Python. Write your caching logic once, swap backends without changing code.

## Installation

```bash
pip install kv-store-py
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add kv-store-py
```

For Redis support:

```bash
pip install kv-store-py redis
```

## Quick Start

```python
import asyncio
from kv_store import RedisStore

async def main():
    # Simple: create from URL with automatic resource management
    async with await RedisStore.from_url("redis://localhost:6379/0") as store:
        await store.set("user:1", {"name": "Alice", "email": "alice@example.com"}, ttl=3600)
        user = await store.get("user:1")
        print(user)  # {'name': 'Alice', 'email': 'alice@example.com'}

asyncio.run(main())
```

### Alternative: Inject Your Own Client

```python
from redis.asyncio import Redis
from kv_store import RedisStore

async def main():
    # Advanced: manage the Redis client yourself
    client = Redis(host="localhost", port=6379)
    store = RedisStore(client)

    await store.set("key", "value", ttl=3600)

    # You manage the client lifecycle
    await client.aclose()
```

## API Reference

All store implementations share the same async interface:

### Single Key Operations

```python
# Get a value (returns default if key doesn't exist or is expired)
value = await store.get(key: str, default: Any = None) -> Any

# Set a value with TTL in seconds
success = await store.set(key: str, value: Any, ttl: int) -> bool

# Delete a key
existed = await store.delete(key: str) -> bool
```

### Batch Operations

```python
# Get multiple keys at once
results = await store.get_many(
    keys: list[str],
    default: Any = None  # Single value or list of defaults per key
) -> dict[str, Any]

# Set multiple keys atomically
results = await store.set_many(items: dict[str, Any], ttl: int) -> dict[str, bool]

# Delete multiple keys
count = await store.delete_many(keys: list[str]) -> int
```

### Distributed Locking (Redis only)

```python
# Acquire a lock for mutual exclusion
async with store.lock("resource:id", timeout=30, blocking_timeout=10):
    # Critical section - only one process can execute this
    await perform_exclusive_operation()
```

## Supported Backends

| Backend | Status | Class |
|---------|--------|-------|
| Redis | Available | `RedisStore` |
| In-Memory | Available | `InMemoryStore` |
| Valkey | Planned | - |
| SQLite | Planned | - |
| PostgreSQL | Planned | - |
| MySQL | Planned | - |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.
