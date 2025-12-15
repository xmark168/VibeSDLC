"""Signal utilities for interrupt handling."""
from typing import Optional


def check_interrupt_signal(story_id: str, agent=None) -> Optional[str]:
    """Check for interrupt signal. Returns 'pause', 'cancel', or None."""
    if agent is not None and hasattr(agent, 'check_signal'):
        signal = agent.check_signal(story_id)
        if signal:
            return signal
    return None
