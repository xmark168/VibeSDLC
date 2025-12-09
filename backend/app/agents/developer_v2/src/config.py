"""Developer V2 Configuration Loader."""

import os
import yaml
from pathlib import Path

_config = None

def load_config() -> dict:
    """Load config from config.yaml."""
    global _config
    if _config is not None:
        return _config
    
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            _config = yaml.safe_load(f)
    else:
        _config = {}
    return _config

def get(key: str, default=None):
    """Get config value by dot-notation key (e.g., 'llm.max_retries')."""
    config = load_config()
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    return value if value is not None else default

# Pre-loaded constants for performance
MAX_RETRIES = get('llm.max_retries', 3)
RETRY_WAIT_MIN = get('llm.retry_wait_min', 1)
RETRY_WAIT_MAX = get('llm.retry_wait_max', 10)
MAX_CONCURRENT = get('parallel.max_concurrent', 5)
MAX_DEBUG_ATTEMPTS = get('debug.max_attempts', 3)
MAX_DEBUG_REVIEWS = get('debug.max_reviews', 3)
