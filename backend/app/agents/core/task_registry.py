"""
TaskRegistry - Lightweight signal management for pause/cancel.

Keep it simple:
- Signals are ephemeral (lost on restart is OK - user can click again)
- Story.agent_state is the persistent source of truth
- This just coordinates in-memory signals between Router and Agent

Architecture:
    Router --[request_pause/cancel]--> _signals dict
    Agent  --[check_interrupt_signal]--> consumes signal, triggers LangGraph interrupt
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Simple in-memory signal storage
_signals: Dict[str, str] = {}  # story_id -> 'pause' | 'cancel'


def request_pause(story_id: str) -> None:
    """Request pause for a story. Called by Router when user clicks Pause."""
    _signals[story_id] = 'pause'
    logger.info(f"[Signal] Pause requested: {story_id}")


def request_cancel(story_id: str) -> None:
    """Request cancel for a story. Called by Router when user clicks Cancel."""
    _signals[story_id] = 'cancel'
    logger.info(f"[Signal] Cancel requested: {story_id}")


def check_interrupt_signal(story_id: str) -> Optional[str]:
    """
    Check and consume signal for a story.
    
    Called by graph nodes to check if they should interrupt.
    Signal is consumed (removed) after checking.
    
    Returns:
        'pause', 'cancel', or None
    """
    signal = _signals.pop(story_id, None)
    if signal:
        logger.info(f"[Signal] {signal} consumed for story {story_id}")
    return signal


def clear_signals(story_id: str) -> None:
    """Clear signal for a story. Called on restart/resume."""
    if story_id in _signals:
        _signals.pop(story_id, None)
        logger.info(f"[Signal] Cleared for story {story_id}")


def has_signal(story_id: str) -> bool:
    """Check if signal exists without consuming it."""
    return story_id in _signals


def get_signal_type(story_id: str) -> Optional[str]:
    """Get signal type without consuming it."""
    return _signals.get(story_id)


def get_all_signals() -> Dict[str, str]:
    """Get all pending signals (for debugging)."""
    return _signals.copy()
