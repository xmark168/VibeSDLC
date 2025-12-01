"""Prompt building utilities for Developer V2."""

from pathlib import Path
from app.agents.core.prompt_utils import load_prompts_yaml

_PROMPTS = load_prompts_yaml(Path(__file__).parent.parent / "prompts.yaml")


def get_prompt(task: str, key: str) -> str:
    """Get prompt from YAML config."""
    return _PROMPTS.get("tasks", {}).get(task, {}).get(key, "")


def format_input_template(task: str, **kwargs) -> str:
    """Format input template from prompts.yaml with provided values."""
    template = get_prompt(task, "input_template")
    if not template:
        return ""
    
    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, str(value) if value else "")
    
    return template.strip()


def get_shared_context(key: str) -> str:
    """Get value from shared_context in prompts.yaml."""
    return _PROMPTS.get("shared_context", {}).get(key, "")


def build_system_prompt(task: str, agent=None) -> str:
    """Build system prompt with shared context."""
    prompt = get_prompt(task, "system_prompt")
    shared = _PROMPTS.get("shared_context", {})
    
    for key, value in shared.items():
        prompt = prompt.replace(f"{{shared_context.{key}}}", value)
    
    if agent:
        prompt = prompt.replace("{name}", agent.name or "Developer")
        prompt = prompt.replace("{role}", agent.role_type or "Software Developer")
    else:
        prompt = prompt.replace("{name}", "Developer")
        prompt = prompt.replace("{role}", "Software Developer")
    
    return prompt
