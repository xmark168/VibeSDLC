"""Singleton services for centralized state management.

This package contains singleton services that manage global application state:
- PoolRegistryService: Centralized agent pool registry
- SystemStatusService: System-wide operational status
- AgentPoolService: Agent pool operations and utilities

All services use singleton pattern for consistent state across the application.
"""

from .pool_registry_service import (
    PoolRegistryService,
    get_pool_registry,
    init_pool_registry,
)
from .system_status_service import (
    SystemStatus,
    SystemStatusService,
    get_system_status_service,
    init_system_status_service,
)
from .minio_service import MinIOService, get_minio_service
from .token_budget_service import (
    TokenBudgetService,
    TokenBudget,
    get_token_budget_service,
    TOKENS_PER_CREDIT,
)
from .scheduler_service import SchedulerService, get_scheduler_service

__all__ = [
    # Pool Registry
    "PoolRegistryService",
    "get_pool_registry",
    "init_pool_registry",
    # System Status
    "SystemStatus",
    "SystemStatusService",
    "get_system_status_service",
    "init_system_status_service",
    # MinIO Storage
    "MinIOService",
    "get_minio_service",
    # Token Budget
    "TokenBudgetService",
    "TokenBudget",
    "get_token_budget_service",
    "TOKENS_PER_CREDIT",
    # Scheduler
    "SchedulerService",
    "get_scheduler_service",
]
