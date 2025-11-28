"""Prompt building utilities for Business Analyst."""

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
    
    for key, value in PROMPTS["shared_context"].items():
        placeholder = f"{{shared_context.{key}}}"
        if placeholder in template:
            template = template.replace(placeholder, value)
    
    return template


def get_task_prompts(task_name: str) -> dict:
    """
    Get prompts for a specific task.
    
    Args:
        task_name: Name of the task (e.g., 'analyze_intent', 'generate_prd', etc.)
    
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


def build_system_prompt(
    agent_name: str,
    personality_traits: list[str],
    communication_style: str,
    task_name: str
) -> str:
    """
    Build system prompt with agent personality.
    
    Args:
        agent_name: Name of the agent
        personality_traits: List of personality traits
        communication_style: Communication style description
        task_name: Name of the task to get prompts for
    
    Returns:
        Formatted system prompt string
    """
    prompts = get_task_prompts(task_name)
    system_prompt_template = prompts["system_prompt"]
    
    traits_text = ", ".join(personality_traits) if personality_traits else "Professional"
    
    personality_text = "\n".join([
        f"- Traits: {traits_text}",
        f"- Communication style: {communication_style}",
        f"- Language: Vietnamese preferred, English when needed"
    ])
    
    return system_prompt_template.format(
        name=agent_name,
        role="Business Analyst / Requirements Specialist",
        goal="Analyze requirements, create PRD documents, and write user stories",
        backstory="Experienced BA with expertise in software requirements and Agile methodologies",
        personality=personality_text
    )


def build_user_prompt(task_name: str, **kwargs) -> str:
    """
    Build user prompt for LLM.
    
    Args:
        task_name: Name of the task to get prompts for
        **kwargs: Variables to format into the prompt
    
    Returns:
        Formatted user prompt string
    """
    prompts = get_task_prompts(task_name)
    user_prompt_template = prompts["user_prompt"]
    
    return user_prompt_template.format(**kwargs)


def parse_json_response(response: str) -> dict:
    """
    Parse JSON from LLM response.
    
    Handles cases where JSON is wrapped in markdown code blocks.
    
    Args:
        response: Raw LLM response string
    
    Returns:
        Parsed JSON as dict
    
    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response
    
    return json.loads(json_str)


def parse_intent_response(response: str) -> dict:
    """
    Parse intent classification response.
    
    Args:
        response: LLM response string
    
    Returns:
        dict with 'intent' and 'reasoning' keys
    """
    try:
        result = parse_json_response(response)
        
        if "intent" in result:
            return {
                "intent": result["intent"],
                "reasoning": result.get("reasoning", "")
            }
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[parse_intent] Parse error: {e}")
    
    # Default to interview if parsing fails
    return {
        "intent": "interview",
        "reasoning": "Could not parse intent, defaulting to interview"
    }


def parse_questions_response(response: str) -> list[dict]:
    """
    Parse questions from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        List of question dicts with 'text', 'type', 'options', 'allow_multiple' keys
    """
    try:
        result = parse_json_response(response)
        questions_list = result.get("questions", [])
        
        parsed_questions = []
        for q in questions_list:
            if isinstance(q, str):
                # Old format: just string
                parsed_questions.append({
                    "text": q,
                    "type": "open",
                    "options": None,
                    "allow_multiple": False
                })
            elif isinstance(q, dict):
                # New format: dict with text, type, options
                parsed_questions.append({
                    "text": q.get("text", ""),
                    "type": q.get("type", "open"),
                    "options": q.get("options"),
                    "allow_multiple": q.get("allow_multiple", False)
                })
        
        return parsed_questions
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[parse_questions] Parse error: {e}")
        return []


def parse_prd_response(response: str) -> dict:
    """
    Parse PRD from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        PRD dict
    """
    try:
        return parse_json_response(response)
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_prd] Parse error: {e}")
        return {
            "project_name": "Generated PRD",
            "overview": "Error parsing PRD",
            "raw_content": response[:1000]
        }


def parse_prd_update_response(response: str) -> dict:
    """
    Parse PRD update response.
    
    Args:
        response: LLM response string
    
    Returns:
        dict with 'updated_prd' and 'change_summary' keys
    """
    try:
        result = parse_json_response(response)
        return {
            "updated_prd": result.get("updated_prd", {}),
            "change_summary": result.get("change_summary", "PRD updated")
        }
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_prd_update] Parse error: {e}")
        return {
            "updated_prd": None,
            "change_summary": f"Error parsing update: {str(e)}"
        }


def parse_stories_response(response: str) -> list[dict]:
    """
    Parse user stories from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        List of story dicts
    """
    try:
        result = parse_json_response(response)
        return result.get("stories", [])
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_stories] Parse error: {e}")
        return []
