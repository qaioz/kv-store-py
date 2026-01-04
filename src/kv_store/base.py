from abc import ABC, abstractmethod
from typing import Optional, Any

class AbstractStore(ABC):
    """Abstract base class for key-value stores (Async)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
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

