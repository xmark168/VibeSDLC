"""Prompt building utilities for Team Leader."""

import json
import logging
import re
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

with open(Path(__file__).parent / "prompts.yaml", "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)


def _resolve_shared_context(template: str) -> str:
    """Resolve {shared_context.*} placeholders in templates."""
    if "shared_context" not in PROMPTS:
        return template
    
    # Replace {shared_context.key} with actual values
    for key, value in PROMPTS["shared_context"].items():
        placeholder = f"{{shared_context.{key}}}"
        if placeholder in template:
            template = template.replace(placeholder, value)
    
    return template


def get_task_prompts(task_name: str = "routing_decision") -> dict:
    """
    Get prompts for a specific task.
    
    Args:
        task_name: Name of the task (e.g., 'routing_decision', 'status_check', 'conversation')
    
    Returns:
        dict with 'system_prompt' and 'user_prompt' keys
    
    Raises:
        ValueError: If task_name not found in prompts.yaml
    """
    if "tasks" not in PROMPTS:
        raise ValueError("No 'tasks' section found in prompts.yaml")
    
    if task_name not in PROMPTS["tasks"]:
        available_tasks = list(PROMPTS["tasks"].keys())
        raise ValueError(
            f"Task '{task_name}' not found in prompts.yaml. "
            f"Available tasks: {', '.join(available_tasks)}"
        )
    
    task_prompts = PROMPTS["tasks"][task_name]
    return {
        "system_prompt": _resolve_shared_context(task_prompts.get("system_prompt", "")),
        "user_prompt": _resolve_shared_context(task_prompts.get("user_prompt", ""))
    }


def build_system_prompt(agent, task_name: str = "routing_decision") -> str:
    """
    Build system prompt with agent personality from DB.
    
    Args:
        agent: Agent instance with personality data
        task_name: Name of the task to get prompts for (default: 'routing_decision')
    """
    prompts = get_task_prompts(task_name)
    system_prompt_template = prompts["system_prompt"]
    
    if not agent:
        return system_prompt_template.format(
            name="Team Leader",
            role="Team Leader & Project Coordinator",
            goal="Route requests efficiently",
            backstory="Experienced project coordinator",
            personality="Professional and helpful"
        )
    
    agent_model = agent.agent_model
    persona_meta = agent_model.persona_metadata or {}
    
    personality_traits = agent_model.personality_traits or []
    traits_text = ", ".join(personality_traits) if personality_traits else "Professional"
    
    communication_style = agent_model.communication_style or "Clear and concise"
    
    personality_text = "\n".join([
        f"- Traits: {traits_text}",
        f"- Communication style: {communication_style}",
        f"- Tone: {persona_meta.get('tone', 'Professional yet friendly')}"
    ])
    
    return system_prompt_template.format(
        name=agent_model.human_name,
        role=persona_meta.get("role", agent_model.role_type),
        goal=persona_meta.get("goal", "Guide users efficiently"),
        backstory=persona_meta.get("backstory", "Experienced team coordinator"),
        personality=personality_text
    )


def build_user_prompt(user_message: str, task_name: str = "routing_decision", **kwargs) -> str:
    """
    Build user prompt for LLM.
    
    Args:
        user_message: The user's message
        task_name: Name of the task to get prompts for (default: 'routing_decision')
        **kwargs: Additional variables to format into the prompt (e.g., board_state for status_check)
    """
    prompts = get_task_prompts(task_name)
    user_prompt_template = prompts["user_prompt"]
    
    # Build format kwargs
    format_kwargs = {"user_message": user_message}
    format_kwargs.update(kwargs)
    
    return user_prompt_template.format(**format_kwargs)


def parse_llm_decision(response: str) -> dict:
    """Parse LLM JSON response."""
    
    try:
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group(0))
            
            if "action" in decision and "message" in decision:
                return decision
        
        if "DELEGATE" in response.upper():
            return {
                "action": "DELEGATE",
                "target_role": extract_role(response),
                "message": "Processing your request",
                "reason": "llm_delegate"
            }
        else:
            return {
                "action": "RESPOND",
                "message": response[:200],
                "reason": "llm_respond"
            }
    
    except Exception as e:
        logger.warning(f"[parse_llm_decision] Parse error: {e}")
        return {
            "action": "RESPOND",
            "message": "I need more information. Can you clarify your request?",
            "reason": "parse_error"
        }


def extract_role(response: str) -> str:
    """Extract role from LLM response."""
    
    response_lower = response.lower()
    
    if "business_analyst" in response_lower or "business analyst" in response_lower:
        return "business_analyst"
    elif "developer" in response_lower:
        return "developer"
    elif "tester" in response_lower:
        return "tester"
    else:
        return "business_analyst"
