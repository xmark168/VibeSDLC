"""OAuth state management utilities."""

import time
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# In-memory state storage with expiry
_oauth_state_store: Dict[str, Dict] = {}


def set_oauth_state(state: str, provider: str, mode: str = "login", user_id: Optional[str] = None):
    """Save OAuth state to in-memory store.
    
    Args:
        state: Unique state token
        provider: OAuth provider (google, github, facebook)
        mode: Operation mode ('login' or 'link')
        user_id: User ID (only for 'link' mode)
    """
    _oauth_state_store[state] = {
        "provider": provider,
        "mode": mode,
        "user_id": user_id,
        "created_at": time.time()
    }
    logger.info(f"Saved OAuth state: {state} for {provider} (mode={mode})")
    
    # Clean up old states
    cleanup_expired_states()


def get_oauth_state_data(state: str) -> Optional[Dict]:
    """Get full OAuth state data from in-memory store.
    
    Args:
        state: State token to retrieve
        
    Returns:
        State data dictionary or None if not found
    """
    state_data = _oauth_state_store.get(state)
    if state_data:
        logger.info(f"Retrieved OAuth state: {state} for {state_data['provider']} (mode={state_data.get('mode', 'login')})")
        return state_data
    logger.warning(f"OAuth state not found: {state}")
    return None


def get_oauth_state(state: str) -> Optional[str]:
    """Get OAuth provider from state (backward compatible).
    
    Args:
        state: State token
        
    Returns:
        Provider name or None
    """
    state_data = get_oauth_state_data(state)
    return state_data["provider"] if state_data else None


def delete_oauth_state(state: str):
    """Delete OAuth state from store.
    
    Args:
        state: State token to delete
    """
    _oauth_state_store.pop(state, None)
    logger.info(f"Deleted OAuth state: {state}")


def cleanup_expired_states(max_age: int = 600):
    """Remove OAuth states older than specified age.
    
    Args:
        max_age: Maximum age in seconds (default 10 minutes)
    """
    current_time = time.time()
    expired_states = [
        state for state, data in _oauth_state_store.items()
        if current_time - data["created_at"] > max_age
    ]
    
    for state in expired_states:
        _oauth_state_store.pop(state, None)
    
    if expired_states:
        logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")


def clear_all_states():
    """Clear all OAuth states (for testing/debugging).
    
    Warning: This will invalidate all pending OAuth flows.
    """
    count = len(_oauth_state_store)
    _oauth_state_store.clear()
    logger.warning(f"Cleared all {count} OAuth states")
