"""Input validation utilities."""

import re
from typing import Tuple


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """Validate password strength.
    
    Requirements:
    - Minimum 8 characters
    - At least 1 letter
    - At least 1 number
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets requirements
    """
    if len(password) < 8:
        return False
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_number = bool(re.search(r"\d", password))
    return has_letter and has_number


def validate_password_detailed(password: str) -> Tuple[bool, str]:
    """Validate password with detailed error message.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    if not has_letter:
        return False, "Password must contain at least one letter"
    
    has_number = bool(re.search(r"\d", password))
    if not has_number:
        return False, "Password must contain at least one number"
    
    return True, ""


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage.
    
    Removes potentially dangerous characters and limits length.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove other dangerous characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length (preserve extension)
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if ext:
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}"
        else:
            filename = filename[:max_length]
    
    return filename or "unnamed"
