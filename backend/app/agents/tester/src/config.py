"""Tester Agent Configuration (aligned with Developer V2)."""

import os
import yaml
from pathlib import Path

_config = None


def load_config() -> dict:
    """Load config from config.yaml if exists."""
    global _config
    if _config is not None:
        return _config
    
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            _config = yaml.safe_load(f) or {}
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


# =============================================================================
# Pre-loaded constants (aligned with Developer V2)
# =============================================================================

# LLM
MAX_RETRIES = get('llm.max_retries', 3)
RETRY_WAIT_MIN = get('llm.retry_wait_min', 1)
RETRY_WAIT_MAX = get('llm.retry_wait_max', 10)

# Parallel execution
MAX_CONCURRENT = get('parallel.max_concurrent', 5)

# Debug/Fix loop
MAX_DEBUG_ATTEMPTS = get('debug.max_attempts', 3)
MAX_DEBUG_REVIEWS = get('debug.max_reviews', 2)

# Review
MAX_REVIEW_CYCLES = get('review.max_cycles', 2)
MAX_LBTM_PER_FILE = get('review.max_lbtm_per_file', 2)

# Test generation
MAX_SCENARIOS_UNIT = get('test.max_scenarios_unit', 2)
MAX_SCENARIOS_INTEGRATION = get('test.max_scenarios_integration', 3)

# Models (can be overridden by env vars)
DEFAULT_MODEL = os.getenv("TESTER_MODEL", "claude-sonnet-4-5-20250929")
FAST_MODEL = os.getenv("TESTER_FAST_MODEL", "claude-haiku-4-5-20251001")
COMPLEX_MODEL = os.getenv("TESTER_COMPLEX_MODEL", "claude-sonnet-4-5-20250929")
