"""Prompt utilities for Tester graph."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Load prompts from YAML
with open(Path(__file__).parent / "prompts.yaml", "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)


def _resolve_shared_context(template: str) -> str:
    """Resolve {shared_context.*} placeholders in templates."""
    if "shared_context" not in PROMPTS:
        return template
    
    for key, value in PROMPTS["shared_context"].items():
        placeholder = f"{{shared_context.{key}}}"
        if placeholder in template:
            template = template.replace(placeholder, value)
    
    return template


def get_prompt(task_name: str, prompt_type: str = "user_prompt", **kwargs) -> str:
    """Get a prompt for a specific task.
    
    Args:
        task_name: Name of the task (e.g., 'analyze_stories', 'generate_test_cases')
        prompt_type: 'system_prompt' or 'user_prompt'
        **kwargs: Variables to format into the prompt
        
    Returns:
        Formatted prompt string
    """
    if "tasks" not in PROMPTS:
        raise ValueError("No 'tasks' section in prompts.yaml")
    
    if task_name not in PROMPTS["tasks"]:
        available = list(PROMPTS["tasks"].keys())
        raise ValueError(f"Task '{task_name}' not found. Available: {available}")
    
    task = PROMPTS["tasks"][task_name]
    template = task.get(prompt_type, "")
    
    # Resolve shared context first
    template = _resolve_shared_context(template)
    
    # Then format with kwargs
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing key {e} in prompt kwargs for {task_name}")
        return template


def get_system_prompt(task_name: str) -> str:
    """Get system prompt for a task."""
    return get_prompt(task_name, "system_prompt")


def get_user_prompt(task_name: str, **kwargs) -> str:
    """Get user prompt for a task with variables."""
    return get_prompt(task_name, "user_prompt", **kwargs)
