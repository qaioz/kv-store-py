from abc import ABC, abstractmethod
from typing import Any, Optional


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
    async def get_many(self, keys: list[str], default: Optional[Any] = None) -> dict[str, Optional[Any]]:
        """Get multiple values from the store."""
        pass

    @abstractmethod
    async def set_many(self, items: dict[str, Any], ttl: int) -> dict[str, bool]:
        """Set multiple values in the store with TTL."""
        pass

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the store. Returns count of deleted items."""
        pass

