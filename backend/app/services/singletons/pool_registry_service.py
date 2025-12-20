"""Pool Registry Service - Centralized management for agent pool managers."""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PoolRegistryService:
    """Centralized registry for agent pool managers."""

    def __init__(self):
        self._registry: Dict[str, "AgentPoolManager"] = {}
        logger.info("PoolRegistryService initialized")

    def register(self, pool_name: str, manager: "AgentPoolManager") -> None:
        """Register a pool manager."""
        if pool_name in self._registry:
            logger.warning(f"Pool '{pool_name}' already registered, overwriting")
        self._registry[pool_name] = manager
        logger.info(f"Registered pool '{pool_name}'")

    def unregister(self, pool_name: str) -> Optional["AgentPoolManager"]:
        """Unregister and return a pool manager."""
        manager = self._registry.pop(pool_name, None)
        if manager:
            logger.info(f"Unregistered pool '{pool_name}'")
        return manager

    def get(self, pool_name: str) -> Optional["AgentPoolManager"]:
        """Get a pool manager by name."""
        return self._registry.get(pool_name)

    def get_all(self) -> Dict[str, "AgentPoolManager"]:
        """Get all registered managers as a dictionary copy."""
        return self._registry.copy()

    def list_pools(self) -> list[str]:
        """List all registered pool names."""
        return list(self._registry.keys())

    def clear(self) -> None:
        """Clear all registered managers."""
        self._registry.clear()

    def __len__(self) -> int:
        """Get number of registered pools."""
        return len(self._registry)

    def __contains__(self, pool_name: str) -> bool:
        """Check if a pool is registered."""
        return pool_name in self._registry

    def __iter__(self):
        """Iterate over (pool_name, manager) pairs."""
        return iter(self._registry.items())

    def items(self):
        """Get items view of registry."""
        return self._registry.items()

    def values(self):
        """Get values view of registry."""
        return self._registry.values()

    def keys(self):
        """Get keys view of registry."""
        return self._registry.keys()


# Singleton instance
_pool_registry: Optional[PoolRegistryService] = None


def get_pool_registry() -> PoolRegistryService:
    """Get singleton pool registry instance."""
    global _pool_registry
    if _pool_registry is None:
        _pool_registry = PoolRegistryService()
    return _pool_registry


def init_pool_registry() -> PoolRegistryService:
    """Initialize pool registry (idempotent)."""
    return get_pool_registry()
