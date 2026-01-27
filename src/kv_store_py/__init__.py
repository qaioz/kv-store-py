from .base import AbstractStore
from .memory import InMemoryStore

# We try to import RedisStore, but if the user didn't install redis,
# we don't crash the whole app—we just make RedisStore unavailable.
try:
    from .redis import RedisStore
except ImportError:
    RedisStore = None

# We try to import PostgresStore, but if the user didn't install asyncpg,
# we don't crash the whole app—we just make PostgresStore unavailable.
try:
    from .postgres import PostgresStore
except ImportError:
    PostgresStore = None

__all__ = ["AbstractStore", "InMemoryStore", "RedisStore", "PostgresStore"]
