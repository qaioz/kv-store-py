from .base import AbstractStore
from .memory import InMemoryStore

# We try to import RedisStore, but if the user didn't install redis,
# we don't crash the whole app—we just make RedisStore unavailable.
try:
    from .redis import RedisStore
except ImportError:
    RedisStore = None

__all__ = ["AbstractStore", "InMemoryStore", "RedisStore"]