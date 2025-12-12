"""Circuit Breaker pattern for agent failure handling.

Provides self-healing capabilities by temporarily blocking tasks to failing agents,
allowing them time to recover before resuming normal operation.

States:
- CLOSED: Normal operation, all tasks allowed
- OPEN: Blocking all tasks, agent is failing
- HALF_OPEN: Testing recovery with limited tasks
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for individual agent failure handling.
    
    Tracks consecutive failures and blocks tasks when threshold exceeded.
    After recovery timeout, allows limited test calls to verify recovery.
    """
    
    def __init__(
        self,
        agent_id: UUID,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 2,
    ):
        """Initialize circuit breaker.
        
        Args:
            agent_id: Agent UUID this breaker protects
            failure_threshold: Consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            half_open_max_calls: Successful calls needed to close circuit
        """
        self.agent_id = agent_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now(timezone.utc)
        self.half_open_successes = 0
        
        self._total_failures = 0
        self._total_opens = 0
    
    def record_success(self) -> None:
        """Record successful task execution."""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            logger.debug(
                f"[CIRCUIT_BREAKER] Agent {self.agent_id} half-open success "
                f"({self.half_open_successes}/{self.half_open_max_calls})"
            )
            
            if self.half_open_successes >= self.half_open_max_calls:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record failed task execution.
        
        Args:
            error: Optional exception that caused failure
        """
        self.failure_count += 1
        self._total_failures += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        error_msg = str(error) if error else "unknown error"
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"[CIRCUIT_BREAKER] Agent {self.agent_id} failed during recovery test: {error_msg}"
            )
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            logger.warning(
                f"[CIRCUIT_BREAKER] Agent {self.agent_id} hit failure threshold "
                f"({self.failure_count}/{self.failure_threshold}): {error_msg}"
            )
            self._transition_to_open()
        else:
            logger.debug(
                f"[CIRCUIT_BREAKER] Agent {self.agent_id} failure "
                f"({self.failure_count}/{self.failure_threshold}): {error_msg}"
            )
    
    def can_execute(self) -> bool:
        """Check if agent can accept tasks.
        
        Returns:
            True if tasks are allowed, False if circuit is blocking
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._recovery_timeout_elapsed():
                self._transition_to_half_open()
                return True
            return False
        
        # HALF_OPEN: Allow limited test calls
        return True
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status.
        
        Returns:
            Status dictionary with state and metrics
        """
        return {
            "agent_id": str(self.agent_id),
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_failures": self._total_failures,
            "total_opens": self._total_opens,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "time_in_state_seconds": (datetime.now(timezone.utc) - self.last_state_change).total_seconds(),
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        logger.info(f"[CIRCUIT_BREAKER] Agent {self.agent_id} manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_successes = 0
        self.last_state_change = datetime.now(timezone.utc)
    
    def _recovery_timeout_elapsed(self) -> bool:
        """Check if recovery timeout has elapsed since last failure."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state - block all tasks."""
        logger.warning(
            f"[CIRCUIT_BREAKER] Agent {self.agent_id} circuit OPEN - "
            f"blocking tasks for {self.recovery_timeout}s"
        )
        self.state = CircuitState.OPEN
        self.half_open_successes = 0
        self.last_state_change = datetime.now(timezone.utc)
        self._total_opens += 1
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state - testing recovery."""
        logger.info(
            f"[CIRCUIT_BREAKER] Agent {self.agent_id} circuit HALF_OPEN - "
            f"testing recovery ({self.half_open_max_calls} calls needed)"
        )
        self.state = CircuitState.HALF_OPEN
        self.half_open_successes = 0
        self.last_state_change = datetime.now(timezone.utc)
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state - normal operation."""
        logger.info(
            f"[CIRCUIT_BREAKER] Agent {self.agent_id} circuit CLOSED - "
            f"recovered successfully!"
        )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_successes = 0
        self.last_state_change = datetime.now(timezone.utc)


class CircuitBreakerManager:
    """Manage circuit breakers for all agents in the system.
    
    Provides centralized access to circuit breakers and system-wide statistics.
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 2,
    ):
        """Initialize circuit breaker manager.
        
        Args:
            failure_threshold: Default failure threshold for new breakers
            recovery_timeout: Default recovery timeout for new breakers
            half_open_max_calls: Default half-open calls for new breakers
        """
        self._breakers: Dict[UUID, CircuitBreaker] = {}
        self._default_failure_threshold = failure_threshold
        self._default_recovery_timeout = recovery_timeout
        self._default_half_open_max_calls = half_open_max_calls
        
        logger.info(
            f"CircuitBreakerManager initialized "
            f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )
    
    def get_or_create(
        self,
        agent_id: UUID,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        half_open_max_calls: Optional[int] = None,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one.
        
        Args:
            agent_id: Agent UUID
            failure_threshold: Override default threshold
            recovery_timeout: Override default timeout
            half_open_max_calls: Override default half-open calls
            
        Returns:
            CircuitBreaker instance for the agent
        """
        if agent_id not in self._breakers:
            self._breakers[agent_id] = CircuitBreaker(
                agent_id=agent_id,
                failure_threshold=failure_threshold or self._default_failure_threshold,
                recovery_timeout=recovery_timeout or self._default_recovery_timeout,
                half_open_max_calls=half_open_max_calls or self._default_half_open_max_calls,
            )
            logger.debug(f"[CIRCUIT_BREAKER] Created breaker for agent {agent_id}")
        
        return self._breakers[agent_id]
    
    def get(self, agent_id: UUID) -> Optional[CircuitBreaker]:
        """Get circuit breaker for agent if exists.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            CircuitBreaker or None if not found
        """
        return self._breakers.get(agent_id)
    
    def remove(self, agent_id: UUID) -> bool:
        """Remove circuit breaker for terminated agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            True if removed, False if not found
        """
        if agent_id in self._breakers:
            del self._breakers[agent_id]
            logger.debug(f"[CIRCUIT_BREAKER] Removed breaker for agent {agent_id}")
            return True
        return False
    
    def get_open_circuits(self) -> List[UUID]:
        """Get list of agents with open circuits.
        
        Returns:
            List of agent UUIDs with OPEN state
        """
        return [
            agent_id 
            for agent_id, cb in self._breakers.items()
            if cb.state == CircuitState.OPEN
        ]
    
    def get_half_open_circuits(self) -> List[UUID]:
        """Get list of agents in recovery testing.
        
        Returns:
            List of agent UUIDs with HALF_OPEN state
        """
        return [
            agent_id 
            for agent_id, cb in self._breakers.items()
            if cb.state == CircuitState.HALF_OPEN
        ]
    
    def get_all_status(self) -> List[Dict]:
        """Get status of all circuit breakers.
        
        Returns:
            List of status dictionaries
        """
        return [cb.get_status() for cb in self._breakers.values()]
    
    def get_summary(self) -> Dict:
        """Get summary statistics across all breakers.
        
        Returns:
            Summary dictionary with counts and states
        """
        total = len(self._breakers)
        closed = sum(1 for cb in self._breakers.values() if cb.state == CircuitState.CLOSED)
        open_count = sum(1 for cb in self._breakers.values() if cb.state == CircuitState.OPEN)
        half_open = sum(1 for cb in self._breakers.values() if cb.state == CircuitState.HALF_OPEN)
        
        total_failures = sum(cb._total_failures for cb in self._breakers.values())
        total_opens = sum(cb._total_opens for cb in self._breakers.values())
        
        return {
            "total_breakers": total,
            "closed": closed,
            "open": open_count,
            "half_open": half_open,
            "total_failures": total_failures,
            "total_opens": total_opens,
            "health_percentage": (closed / total * 100) if total > 0 else 100.0,
        }
    
    def reset_all(self) -> int:
        """Reset all circuit breakers to closed state.
        
        Returns:
            Number of breakers reset
        """
        count = 0
        for cb in self._breakers.values():
            if cb.state != CircuitState.CLOSED:
                cb.reset()
                count += 1
        
        logger.info(f"[CIRCUIT_BREAKER] Reset {count} circuit breakers")
        return count


# Singleton instance
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get singleton CircuitBreakerManager instance.
    
    Returns:
        CircuitBreakerManager instance
    """
    global _circuit_breaker_manager
    
    if _circuit_breaker_manager is None:
        from app.core.config import settings
        
        _circuit_breaker_manager = CircuitBreakerManager(
            failure_threshold=getattr(settings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 3),
            recovery_timeout=getattr(settings, 'CIRCUIT_BREAKER_RECOVERY_TIMEOUT', 60),
            half_open_max_calls=getattr(settings, 'CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS', 2),
        )
    
    return _circuit_breaker_manager
