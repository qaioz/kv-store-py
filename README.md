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
from kv_store import AbstractStore, RedisStore, PostgresStore

# Use Redis
store: AbstractStore = await RedisStore.from_url("redis://localhost:6379/0")
await store.set("key", "value", ttl=3600)
await store.get("key")

# Swap to Postgres - same interface
store: AbstractStore = await PostgresStore.from_url("postgresql://localhost/mydb")
await store.set_many({"k1": "v1", "k2": "v2"}, ttl=3600)
await store.get_many(["k1", "k2"])

# Distributed locking (supported by both Redis and Postgres)
async with store.lock("my-resource", timeout=30):
    # critical section
    pass
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

### Distributed Locking

```python
# Acquire a lock for mutual exclusion
async with store.lock("resource:id", timeout=30, blocking_timeout=10):
    # Critical section - only one process can execute this
    await perform_exclusive_operation()
```

## Supported Backends

| Backend | Status | Class |
|---------|--------|-------|
| In-Memory | Available | `InMemoryStore` |
| Redis | Available | `RedisStore` |
| PostgreSQL | Available | `PostgresStore` |
| Valkey | Planned | - |
| SQLite | Planned | - |
| MySQL | Planned | - |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.
