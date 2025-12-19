"""System Status Service - Centralized system-wide status management."""

from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SystemStatus(str, Enum):
    """System-wide status for emergency controls."""
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    STOPPED = "stopped"


class SystemStatusService:
    """Centralized system status management.
    
    Manages system-wide operational state for emergency controls,
    maintenance modes, and graceful degradation.
    """

    def __init__(self):
        self._status: SystemStatus = SystemStatus.RUNNING
        self._status_changed_at: Optional[datetime] = None
        self._maintenance_message: Optional[str] = None
        logger.info("SystemStatusService initialized")

    @property
    def status(self) -> SystemStatus:
        """Get current system status."""
        return self._status

    @property
    def status_changed_at(self) -> Optional[datetime]:
        """Get timestamp when status last changed."""
        return self._status_changed_at

    @property
    def maintenance_message(self) -> Optional[str]:
        """Get maintenance message if in maintenance mode."""
        return self._maintenance_message

    def is_running(self) -> bool:
        """Check if system is in running state."""
        return self._status == SystemStatus.RUNNING

    def is_paused(self) -> bool:
        """Check if system is paused."""
        return self._status == SystemStatus.PAUSED

    def is_maintenance(self) -> bool:
        """Check if system is in maintenance mode."""
        return self._status == SystemStatus.MAINTENANCE

    def is_stopped(self) -> bool:
        """Check if system is stopped."""
        return self._status == SystemStatus.STOPPED

    def pause(self) -> dict:
        """Pause system - stop accepting new tasks.
        
        Returns:
            Status info dict
        """
        if self._status == SystemStatus.PAUSED:
            logger.warning("System already paused")
            return self.get_status_info()
        
        previous_status = self._status
        self._status = SystemStatus.PAUSED
        self._status_changed_at = datetime.now()
        logger.warning(f"System paused (previous: {previous_status.value})")
        return self.get_status_info()

    def resume(self) -> dict:
        """Resume system - start accepting tasks again.
        
        Returns:
            Status info dict
        """
        if self._status == SystemStatus.RUNNING:
            logger.info("System already running")
            return self.get_status_info()
        
        if self._status == SystemStatus.STOPPED:
            logger.error("Cannot resume stopped system - use restart instead")
            raise ValueError("Cannot resume stopped system. Use restart to bring system back online.")
        
        previous_status = self._status
        self._status = SystemStatus.RUNNING
        self._status_changed_at = datetime.now()
        self._maintenance_message = None
        logger.info(f"System resumed from {previous_status.value}")
        return self.get_status_info()

    def stop(self) -> dict:
        """Stop system completely.
        
        Returns:
            Status info dict
        """
        previous_status = self._status
        self._status = SystemStatus.STOPPED
        self._status_changed_at = datetime.now()
        logger.critical(f"System stopped (previous: {previous_status.value})")
        return self.get_status_info()

    def enter_maintenance(self, message: str) -> dict:
        """Enter maintenance mode with custom message.
        
        Args:
            message: Maintenance message to display
            
        Returns:
            Status info dict
        """
        previous_status = self._status
        self._status = SystemStatus.MAINTENANCE
        self._status_changed_at = datetime.now()
        self._maintenance_message = message
        logger.warning(f"Maintenance mode entered (previous: {previous_status.value}): {message}")
        return self.get_status_info()

    def get_status_info(self) -> dict:
        """Get complete status information.
        
        Returns:
            Dict with status, timestamp, and maintenance message
        """
        return {
            "status": self._status,
            "status_changed_at": self._status_changed_at,
            "maintenance_message": self._maintenance_message,
        }


# Singleton instance
_system_status_service: Optional[SystemStatusService] = None


def get_system_status_service() -> SystemStatusService:
    """Get singleton system status service.
    
    Returns:
        SystemStatusService singleton instance
    """
    global _system_status_service
    if _system_status_service is None:
        _system_status_service = SystemStatusService()
    return _system_status_service


def init_system_status_service() -> SystemStatusService:
    """Initialize system status service (idempotent).
    
    Returns:
        SystemStatusService instance
    """
    return get_system_status_service()
