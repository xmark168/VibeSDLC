"""Avatar management utilities."""

from typing import Optional


# Default avatar URL using DiceBear API
DEFAULT_AVATAR_URL = "https://api.dicebear.com/7.x/avataaars/svg?seed=default"


def get_avatar_url(user) -> str:
    """Get avatar URL for user with fallback to default."""
    if user.avatar_url:
        return user.avatar_url
    return DEFAULT_AVATAR_URL


def get_avatar_seed(user_id: str) -> str:
    """Generate deterministic avatar seed from user ID."""
    return f"user-{user_id}"


def generate_default_avatar_url(seed: str) -> str:
    """Generate default avatar URL with custom seed.
    
    Args:
        seed: Seed for avatar generation
        
    Returns:
        DiceBear avatar URL
    """
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}"
