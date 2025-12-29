"""Unified generator"""

import random
import secrets
import string
from datetime import datetime


# =============================================================================
# CODE GENERATION
# =============================================================================

def generate_verification_code(length: int = 6) -> str:
    """Generate numeric verification code.
    
    Args:
        length: Length of verification code (default: 6)
        
    Returns:
        Numeric verification code as string
        
    Example:
        >>> code = generate_verification_code(6)
        >>> len(code) == 6
        True
    """
    return str(random.randint(10**(length-1), 10**length - 1))


def generate_transaction_code() -> str:
    """Generate unique transaction code for payments.
    
    Format: TX + YYMMDDHHmmss
    
    Returns:
        Transaction code string
        
    Example:
        >>> code = generate_transaction_code()
        >>> code.startswith('TX')
        True
    """
    now = datetime.now()
    return f"TX{now.strftime('%y%m%d%H%M%S')}"


def generate_secure_code(length: int = 32, chars: str = None) -> str:
    """Generate cryptographically secure random code.
    
    Args:
        length: Length of code (default: 32)
        chars: Character set to use (default: alphanumeric)
        
    Returns:
        Random code string
        
    Example:
        >>> code = generate_secure_code(16)
        >>> len(code) == 16
        True
    """
    if chars is None:
        chars = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(chars) for _ in range(length))


# =============================================================================
# NAME GENERATION
# =============================================================================

def get_display_name(human_name: str, role_type: str) -> str:
    """Get formatted display name for agent.
    
    Args:
        human_name: Human-friendly agent name
        role_type: Agent role (team_leader, developer, tester, business_analyst)
        
    Returns:
        Formatted display name with role label
        
    Example:
        >>> get_display_name("Alice", "developer")
        'Alice (Developer)'
    """
    role_display = {
        "team_leader": "Team Leader",
        "business_analyst": "Business Analyst",
        "developer": "Developer",
        "tester": "Tester",
    }
    role_label = role_display.get(role_type, role_type.replace("_", " ").title())
    return f"{human_name} ({role_label})"


# =============================================================================
# AVATAR GENERATION
# =============================================================================

# Default avatar URL using DiceBear API
DEFAULT_AVATAR_URL = "https://api.dicebear.com/7.x/avataaars/svg?seed=default"


def get_avatar_url(user) -> str:
    """Get avatar URL for user with fallback to default.
    
    Args:
        user: User object with optional avatar_url attribute
        
    Returns:
        Avatar URL (custom or default)
    """
    if user.avatar_url:
        return user.avatar_url
    return DEFAULT_AVATAR_URL



