"""Generic prompt building utilities for all agents."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


def load_prompts_yaml(yaml_path: Path | str) -> dict:
    """Load prompts configuration from YAML file."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_shared_context(template: str, prompts_config: dict) -> str:
    """Resolve {shared_context.*} placeholders in templates."""
    if "shared_context" not in prompts_config:
        return template
    
    for key, value in prompts_config["shared_context"].items():
        placeholder = f"{{shared_context.{key}}}"
        if placeholder in template:
            template = template.replace(placeholder, value)
    
    return template


def get_task_prompts(prompts_config: dict, task_name: str) -> dict:
    """
    Get prompts for a specific task from config.
    
    Args:
        prompts_config: Loaded prompts configuration dict
        task_name: Name of the task (e.g., 'routing_decision', 'status_check')
    
    Returns:
        dict with 'system_prompt' and 'user_prompt' keys
    """
    if "tasks" not in prompts_config:
        raise ValueError("No 'tasks' section found in prompts config")
    
    if task_name not in prompts_config["tasks"]:
        available_tasks = list(prompts_config["tasks"].keys())
        raise ValueError(
            f"Task '{task_name}' not found. Available: {', '.join(available_tasks)}"
        )
    
    task_prompts = prompts_config["tasks"][task_name]
    return {
        "system_prompt": resolve_shared_context(
            task_prompts.get("system_prompt", ""), prompts_config
        ),
        "user_prompt": resolve_shared_context(
            task_prompts.get("user_prompt", ""), prompts_config
        ),
    }


def extract_agent_personality(agent) -> dict:
    """Extract personality info from agent model."""
    if not agent:
        return {
            "name": "Agent",
            "role": "Assistant",
            "goal": "Help users efficiently",
            "backstory": "Experienced assistant",
            "personality": "Professional and helpful",
            "description": "A helpful assistant",
            "strengths": "",
            "communication_style": "Clear and concise",
        }
    
    agent_model = agent.agent_model
    persona_meta = agent_model.persona_metadata or {}
    
    personality_traits = agent_model.personality_traits or []
    traits_text = ", ".join(personality_traits) if personality_traits else "Professional"
    
    communication_style = agent_model.communication_style or "Clear and concise"
    
    # Extract strengths and description
    strengths = persona_meta.get("strengths", [])
    strengths_text = ", ".join(strengths) if strengths else ""
    description = persona_meta.get("description", "A helpful team member")
    
    personality_text = "\n".join([
        f"- Tính cách: {traits_text}",
        f"- Phong cách giao tiếp: {communication_style}",
        f"- Giọng điệu: {persona_meta.get('tone', 'Thân thiện và chuyên nghiệp')}",
        f"- Điểm mạnh: {strengths_text}" if strengths_text else "",
    ])
    
    return {
        "name": agent_model.human_name,
        "role": persona_meta.get("role", agent_model.role_type),
        "goal": persona_meta.get("goal", "Help users efficiently"),
        "backstory": persona_meta.get("backstory", "Experienced assistant"),
        "personality": personality_text,
        "description": description,
        "strengths": strengths_text,
        "communication_style": communication_style,
    }


def build_system_prompt(
    prompts_config: dict,
    task_name: str,
    agent: Optional[Any] = None,
    defaults: Optional[dict] = None,
) -> str:
    """
    Build system prompt with agent personality.
    
    Args:
        prompts_config: Loaded prompts configuration
        task_name: Task name to get prompts for
        agent: Optional agent instance with personality data
        defaults: Optional default values for formatting
    """
    prompts = get_task_prompts(prompts_config, task_name)
    template = prompts["system_prompt"]
    
    format_kwargs = extract_agent_personality(agent)
    if defaults:
        for key, value in defaults.items():
            if key not in format_kwargs or not format_kwargs[key]:
                format_kwargs[key] = value
    
    return template.format(**format_kwargs)


def build_user_prompt(
    prompts_config: dict,
    task_name: str,
    user_message: str,
    **kwargs,
) -> str:
    """
    Build user prompt for LLM.
    
    Args:
        prompts_config: Loaded prompts configuration
        task_name: Task name to get prompts for
        user_message: The user's message
        **kwargs: Additional variables for formatting
    """
    prompts = get_task_prompts(prompts_config, task_name)
    template = prompts["user_prompt"]
    
    format_kwargs = {"user_message": user_message, **kwargs}
    return template.format(**format_kwargs)
