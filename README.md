# kv-store

[![CI](https://github.com/qaioz/kv-store/actions/workflows/ci.yml/badge.svg)](https://github.com/qaioz/kv-store/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/kv-store-py.svg)](https://pypi.org/project/kv-store-py/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Easy and practical key value store.

- get, set, get_many, set_many methods with handy defaults
- Implemented as Asyncrounous context manager
- Supports distributed locking in all implementations

### Installation

```bash
pip install kv-store-py
```

### Quick Start

```python
from kv_store_py import AbstractStore, RedisStore, PostgresStore

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

### API Reference

All store implementations share the same async interface:

#### Core Operations

```python
# Get a value (returns default if key doesn't exist or is expired)
value = await store.get(key: str, default: Any = None) -> Any

# Set a value with TTL in seconds
success = await store.set(key: str, value: Any, ttl: int) -> bool

# Delete a key
existed = await store.delete(key: str) -> bool

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

#### Distributed Locking

```python
# Acquire a lock for mutual exclusion
async with store.lock("resource:id", timeout=30, blocking_timeout=10):
    # Critical section - only one process can execute this
    await perform_exclusive_operation()
```

#### PostgreSQL Options

When using `PostgresStore.from_url()`, you can customize the connection pool and table name:

```python
store = await PostgresStore.from_url(
    "postgresql://localhost/mydb",
    table_name="custom_kv",  # Default: "kv_store"
    min_size=2,              # Minimum pool connections
    max_size=10              # Maximum pool connections
)
```

PostgreSQL uses **table-based locking** with auto-expiration tokens (not advisory locks).

### Supported Backends

| Backend | Status | Class |
|---------|--------|-------|
| In-Memory | Available | `InMemoryStore` |
| Redis | Available | `RedisStore` |
| PostgreSQL | Available | `PostgresStore` |

> **Note:** PostgreSQL support was tested only on PostgreSQL 16. There is no guarantee it works on other versions.

| Valkey | Planned | - |
| SQLite | Planned | - |
| MySQL | Planned | - |

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### License

MIT License - see [LICENSE](LICENSE) for details.
