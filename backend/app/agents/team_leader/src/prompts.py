"""Prompt building utilities for Team Leader."""

import json
import logging
import re
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

with open(Path(__file__).parent / "prompts.yaml", "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)


def build_system_prompt(agent) -> str:
    """Build system prompt with agent personality from DB."""
    if not agent:
        return PROMPTS["system_prompt"].format(
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
    
    return PROMPTS["system_prompt"].format(
        name=agent_model.human_name,
        role=persona_meta.get("role", agent_model.role_type),
        goal=persona_meta.get("goal", "Guide users efficiently"),
        backstory=persona_meta.get("backstory", "Experienced team coordinator"),
        personality=personality_text
    )


def build_user_prompt(user_message: str) -> str:
    """Build user prompt for LLM with examples."""
    return PROMPTS["user_prompt_template"].format(user_message=user_message)


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
