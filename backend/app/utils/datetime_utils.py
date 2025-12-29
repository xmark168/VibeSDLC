"""DateTime utility functions for consistent serialization."""

from datetime import datetime


def to_utc_isoformat(dt: datetime | None) -> str | None:
    """
    Convert timezone-naive UTC datetime to ISO format with Z indicator.
    
    Database datetimes are stored as TIMESTAMP WITHOUT TIME ZONE in UTC
    (after asyncpg timezone fix). This function adds the 'Z' suffix to 
    indicate UTC timezone when serializing to JSON.
    
    Args:
        dt: Timezone-naive UTC datetime from database, or None
        
    Returns:
        ISO 8601 string with 'Z' suffix (e.g. "2025-12-20T10:00:00Z"), or None
        
    Example:
        >>> dt = datetime(2025, 12, 20, 10, 0, 0)  # From database (UTC, no tzinfo)
        >>> to_utc_isoformat(dt)
        '2025-12-20T10:00:00Z'
    """
    if dt is None:
        return None
    
    # Database datetimes are always UTC but stored timezone-naive
    # Add 'Z' suffix to indicate UTC (RFC 3339 / ISO 8601)
    return dt.isoformat() + 'Z'
