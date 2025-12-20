"""Prompt building utilities for Developer V2."""

from pathlib import Path
from app.agents.core.prompt_utils import load_prompts_yaml

_PROMPTS = load_prompts_yaml(Path(__file__).parent.parent / "prompts.yaml")


def get_prompt(task: str, key: str) -> str:
    return _PROMPTS.get("tasks", {}).get(task, {}).get(key, "")


def format_input_template(task: str, **kwargs) -> str:
    template = get_prompt(task, "input_template")
    if not template:
        return ""
    for key, value in kwargs.items():
        template = template.replace("{" + key + "}", str(value) if value else "")
    return template.strip()


def build_system_prompt(task: str, agent=None, **kwargs) -> str:
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
    
    for key, value in kwargs.items():
        prompt = prompt.replace("{" + key + "}", str(value) if value else "")
    return prompt
