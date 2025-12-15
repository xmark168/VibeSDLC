"""Interrupt signal checking utility to avoid circular imports."""

import logging

logger = logging.getLogger(__name__)


def check_interrupt_signal(story_id: str, agent=None) -> str | None:
    """Check for interrupt signal ('pause', 'cancel', or None)."""
    if not story_id:
        return None
    
    if agent is not None and hasattr(agent, 'check_signal'):
        signal = agent.check_signal(story_id)
        if signal:
            logger.info(f"[Signal] {signal} found in agent for story {story_id[:8]}...")
            return signal
    return None
