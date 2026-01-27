from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Optional, Union

import asyncpg

from .base import AbstractStore


class PostgresLock:
    """Advisory lock wrapper for Postgres."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ):
        self._pool = pool
        self._name = name
        self._timeout = timeout
        self._blocking_timeout = blocking_timeout
        self._lock_id = self._name_to_lock_id(name)
        self._conn: Optional[asyncpg.Connection] = None

    @staticmethod
    def _name_to_lock_id(name: str) -> int:
        """Convert lock name to a 64-bit integer for pg_advisory_lock."""
        hash_bytes = hashlib.sha256(name.encode()).digest()[:8]
        return int.from_bytes(hash_bytes, byteorder="big", signed=True)

    async def acquire(self) -> bool:
        """Acquire the advisory lock."""
        self._conn = await self._pool.acquire()
        try:
            if self._blocking_timeout is None:
                # Blocking acquire
                await self._conn.execute(
                    "SELECT pg_advisory_lock($1)", self._lock_id
                )
                return True
            elif self._blocking_timeout == 0:
                # Non-blocking try
                result = await self._conn.fetchval(
                    "SELECT pg_try_advisory_lock($1)", self._lock_id
                )
                if not result:
                    await self._pool.release(self._conn)
                    self._conn = None
                return result
            else:
                # Try with timeout using statement_timeout
                await self._conn.execute(
                    f"SET statement_timeout = '{int(self._blocking_timeout * 1000)}'"
                )
                try:
                    await self._conn.execute(
                        "SELECT pg_advisory_lock($1)", self._lock_id
                    )
                    return True
                except asyncpg.QueryCanceledError:
                    await self._pool.release(self._conn)
                    self._conn = None
                    return False
                finally:
                    if self._conn:
                        await self._conn.execute("SET statement_timeout = '0'")
        except Exception:
            if self._conn:
                await self._pool.release(self._conn)
                self._conn = None
            raise

    async def release(self) -> None:
        """Release the advisory lock."""
        if self._conn:
            try:
                await self._conn.execute(
                    "SELECT pg_advisory_unlock($1)", self._lock_id
                )
            finally:
                await self._pool.release(self._conn)
                self._conn = None

    async def __aenter__(self) -> "PostgresLock":
        acquired = await self.acquire()
        if not acquired:
            raise TimeoutError(f"Could not acquire lock '{self._name}'")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


class PostgresStore(AbstractStore):
    """PostgreSQL-backed key-value store using asyncpg."""

    DEFAULT_TABLE_NAME = "kv_store"

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        table_name: str = DEFAULT_TABLE_NAME,
        _owns_pool: bool = False,
    ):
        """Initialize PostgresStore with a connection pool.

        Args:
            pool: An asyncpg connection pool.
            table_name: Name of the KV store table (default: "kv_store").
            _owns_pool: Internal flag indicating if this store owns the pool
                and should close it. Set automatically by from_url().
        """
        self._pool = pool
        self._table_name = table_name
        self._owns_pool = _owns_pool

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        table_name: str = DEFAULT_TABLE_NAME,
        min_size: int = 2,
        max_size: int = 10,
        **kwargs,
    ) -> "PostgresStore":
        """Create a PostgresStore from a PostgreSQL URL.

        Args:
            url: PostgreSQL URL (e.g., "postgresql://user:pass@localhost:5432/db").
            table_name: Name of the KV store table (default: "kv_store").
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
            **kwargs: Additional arguments passed to asyncpg.create_pool().

        Returns:
            A new PostgresStore instance that owns its connection pool.

        Example:
            store = await PostgresStore.from_url("postgresql://localhost/mydb")
            async with store:
                await store.set("key", "value", ttl=3600)
        """
        pool = await asyncpg.create_pool(
            url, min_size=min_size, max_size=max_size, **kwargs
        )
        return cls(pool, table_name=table_name, _owns_pool=True)

    async def create_table(self) -> None:
        """Create the KV store table if it doesn't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    expires_at TIMESTAMPTZ
                )
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires
                ON {self._table_name}(expires_at)
                WHERE expires_at IS NOT NULL
            """)

    async def close(self) -> None:
        """Close the connection pool if this store owns it."""
        if self._owns_pool:
            await self._pool.close()

    def _serialize(self, value: Any) -> str:
        """Convert Python objects to JSON strings for Postgres JSONB."""
        return json.dumps(value)

    def _deserialize(self, value: Any) -> Any:
        """Convert Postgres JSONB back to Python objects."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        # asyncpg returns JSONB as Python objects already
        return value

    def _compute_expires_at(self, ttl: int) -> datetime:
        """Compute expiration timestamp from TTL in seconds."""
        return datetime.now(timezone.utc) + timedelta(seconds=ttl)

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a value from the store."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT value FROM {self._table_name}
                WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key,
            )
            if row is None:
                return default
            return self._deserialize(row["value"])

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set a value in the store with TTL."""
        expires_at = self._compute_expires_at(ttl)
        serialized = self._serialize(value)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table_name} (key, value, expires_at)
                VALUES ($1, $2::jsonb, $3)
                ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, expires_at = $3
                """,
                key,
                serialized,
                expires_at,
            )
            return True

    async def delete(self, key: str) -> bool:
        """Delete a value from the store."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE key = $1", key
            )
            # result is like "DELETE 1" or "DELETE 0"
            return result.split()[-1] != "0"

    async def get_many(
        self,
        keys: list[str],
        default: Optional[Union[Any, list[Any]]] = None,
    ) -> dict[str, Optional[Any]]:
        """Get multiple values from the store."""
        if not keys:
            return {}

        use_list_defaults = isinstance(default, list) and len(default) == len(keys)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT key, value FROM {self._table_name}
                WHERE key = ANY($1) AND (expires_at IS NULL OR expires_at > NOW())
                """,
                keys,
            )

        found = {row["key"]: self._deserialize(row["value"]) for row in rows}
        results = {}

        for i, key in enumerate(keys):
            if key in found:
                results[key] = found[key]
            else:
                results[key] = default[i] if use_list_defaults else default

        return results

    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        if not items:
            return {}

        expires_at = self._compute_expires_at(ttl)
        results = {key: True for key in items}

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for key, value in items.items():
                    serialized = self._serialize(value)
                    await conn.execute(
                        f"""
                        INSERT INTO {self._table_name} (key, value, expires_at)
                        VALUES ($1, $2::jsonb, $3)
                        ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, expires_at = $3
                        """,
                        key,
                        serialized,
                        expires_at,
                    )

        return results

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the store. Returns count of deleted items."""
        if not keys:
            return 0

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE key = ANY($1)", keys
            )
            # result is like "DELETE 5"
            return int(result.split()[-1])

    async def cleanup_expired(self) -> int:
        """Remove expired entries from the store.

        Returns:
            Number of deleted entries.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE expires_at < NOW()"
            )
            return int(result.split()[-1])

    def lock(
        self,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ) -> PostgresLock:
        """Returns a Postgres advisory lock to be used with `async with`.

        Args:
            name: The name for the lock (will be hashed to a lock ID).
            timeout: Not used for Postgres advisory locks (they don't auto-expire).
            blocking_timeout: How long to wait to acquire the lock. None waits forever.

        Returns:
            A PostgresLock context manager.
        """
        return PostgresLock(
            self._pool,
            name=name,
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Context manager for explicit transactions.

        Example:
            async with store.transaction() as conn:
                # Multiple operations in one transaction
                await conn.execute(...)
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn
