from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any, Optional, Union


class AbstractStore(ABC):
    """Abstract base class for key-value stores (Async)."""

    @abstractmethod
    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a value from the store."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set a value in the store with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the store."""
        pass

    @abstractmethod
    async def get_many(
        self,
        keys: list[str],
        default: Optional[Union[Any, list[Any]]] = None,
    ) -> dict[str, Optional[Any]]:
        """Get multiple values from the store.

        Args:
            keys: List of keys to retrieve.
            default: Either a single default value (used for all missing keys)
                or a list of default values (one per key, must match len(keys)).
        """
        pass

    @abstractmethod
    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        pass

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the store. Returns count of deleted items."""
        pass

    @abstractmethod
    def lock(
        self,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: Optional[float] = None,
    ) -> AbstractAsyncContextManager:
        """Get a distributed lock.

        Args:
            name: The lock name/key.
            timeout: Lock auto-expires after this many seconds (prevents deadlocks).
            blocking_timeout: How long to wait to acquire the lock.
                None = wait forever, 0 = fail immediately if not available.

        Returns:
            An async context manager for the lock.

        Example:
            async with store.lock("my-resource", timeout=30.0):
                # Lock held
                do_work()
            # Lock released
        """
        pass

    async def close(self) -> None:
        """Close the store and release resources. Override in subclasses if needed."""
        pass

    async def __aenter__(self) -> "AbstractStore":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - closes the store."""
        await self.close()
