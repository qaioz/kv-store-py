from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Optional, Union

import asyncpg

from .base import AbstractStore


class PostgresLock:
    """Table-based distributed lock for Postgres with auto-expiration."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        table_name: str,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ):
        """Initialize a PostgresLock.

        Args:
            pool: asyncpg connection pool.
            table_name: Name of the locks table.
            name: The lock name/key.
            timeout: Lock auto-expires after this many seconds (prevents deadlocks).
            blocking_timeout: How long to wait to acquire. None waits forever, 0 fails immediately.
        """
        self._pool = pool
        self._table_name = table_name
        self._name = name
        self._timeout = timeout
        self._blocking_timeout = blocking_timeout
        self._token: Optional[str] = None

    async def _try_acquire(self) -> bool:
        """Attempt to acquire the lock once. Returns True if successful."""
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._timeout)

        async with self._pool.acquire() as conn:
            # Try to insert new lock, or take over if expired
            result = await conn.fetchval(
                f"""
                INSERT INTO {self._table_name} (name, token, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO UPDATE
                SET token = $2, expires_at = $3
                WHERE {self._table_name}.expires_at < NOW()
                RETURNING token
                """,
                self._name,
                token,
                expires_at,
            )

            if result == token:
                self._token = token
                return True
            return False

    async def acquire(self) -> bool:
        """Acquire the lock, optionally waiting up to blocking_timeout."""
        # Non-blocking: try once
        if self._blocking_timeout == 0:
            return await self._try_acquire()

        # Blocking with optional timeout
        start_time = asyncio.get_event_loop().time()
        poll_interval = 0.1  # 100ms between attempts

        while True:
            if await self._try_acquire():
                return True

            # Check if we've exceeded blocking_timeout
            if self._blocking_timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= self._blocking_timeout:
                    return False

            await asyncio.sleep(poll_interval)

    async def release(self) -> bool:
        """Release the lock. Only succeeds if we hold it (matching token)."""
        if not self._token:
            return False

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE name = $1 AND token = $2",
                self._name,
                self._token,
            )
            self._token = None
            return result.split()[-1] != "0"

    async def extend(self, additional_time: Optional[float] = None) -> bool:
        """Extend the lock's expiration time.

        Args:
            additional_time: Seconds to add. Defaults to the original timeout.

        Returns:
            True if extended, False if we no longer hold the lock.
        """
        if not self._token:
            return False

        extension = additional_time if additional_time is not None else self._timeout
        new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=extension)

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE {self._table_name}
                SET expires_at = $1
                WHERE name = $2 AND token = $3
                """,
                new_expires_at,
                self._name,
                self._token,
            )
            return result.split()[-1] != "0"

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

    @property
    def _lock_table_name(self) -> str:
        """Name of the locks table, derived from the main table name."""
        return f"{self._table_name}_locks"

    async def create_table(self) -> None:
        """Create the KV store and locks tables if they don't exist."""
        async with self._pool.acquire() as conn:
            # KV store table
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

            # Locks table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._lock_table_name} (
                    name TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL
                )
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._lock_table_name}_expires
                ON {self._lock_table_name}(expires_at)
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
        """Returns a table-based distributed lock with auto-expiration.

        Args:
            name: The lock name/key.
            timeout: Lock auto-expires after this many seconds (prevents deadlocks
                if the holder crashes without releasing).
            blocking_timeout: How long to wait to acquire the lock.
                None = wait forever, 0 = fail immediately if not available.

        Returns:
            A PostgresLock context manager.

        Example:
            async with store.lock("my-resource", timeout=30.0):
                # Lock held, auto-expires after 30s if not released
                do_work()
            # Lock released
        """
        return PostgresLock(
            self._pool,
            table_name=self._lock_table_name,
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
