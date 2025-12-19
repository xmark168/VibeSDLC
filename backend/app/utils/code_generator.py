"""Code and token generation utilities."""

import random
import secrets
import string
from datetime import datetime


def generate_verification_code(length: int = 6) -> str:
    """Generate numeric verification code."""
    return str(random.randint(10**(length-1), 10**length - 1))


def generate_transaction_code() -> str:
    """Generate unique transaction code for payments."""
    now = datetime.now()
    return f"TX{now.strftime('%y%m%d%H%M%S')}"


def generate_state_token(length: int = 32) -> str:
    """Generate secure state token for OAuth/CSRF protection."""
    return secrets.token_urlsafe(length)


def generate_secure_code(length: int = 32, chars: str = None) -> str:
    """Generate cryptographically secure random code.
    
    Args:
        length: Length of code
        chars: Character set to use (default: alphanumeric)
        
    Returns:
        Random code string
    """
    if chars is None:
        chars = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(chars) for _ in range(length))
