"""Respond and extract preferences nodes for Team Leader."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agent.llm_factory import get_llm
from app.core.agent.prompt_utils import get_task_prompts
from app.agents.team_leader.src.nodes._utils import get_callback_config, _PROMPTS
from app.agents.team_leader.src.schemas import ExtractedPreferences
from app.agents.team_leader.src.state import TeamLeaderState

logger = logging.getLogger(__name__)


async def extract_preferences(state: TeamLeaderState, agent=None) -> dict:
    """Extract and save user preferences. Returns empty dict (no state update)."""
    msg = state.get("user_message", "")
    if len(msg.strip()) < 10:
        return {}

    try:
        prompts = get_task_prompts(_PROMPTS, "preference_extraction")
        structured_llm = get_llm("router").with_structured_output(ExtractedPreferences)
        result = await structured_llm.ainvoke(
            [
                SystemMessage(content=prompts["system_prompt"]),
                HumanMessage(content=f'Analyze: "{msg}"')
            ],
            config=get_callback_config(state, "extract_preferences")
        )
        detected = {k: v for k, v in result.model_dump().items() if v and k != "additional"}
        
        if result.additional:
            detected.update(result.additional)
        
        if detected and agent:
            for k, v in detected.items():
                await agent.update_preference(k, v)
    except Exception as e:
        logger.debug(f"[extract_preferences] {e}")

    return {}


async def respond(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Send direct response to user."""
    msg = state.get("message", "Mình có thể giúp gì?")
    if agent:
        await agent.message_user("response", msg)
    return {**state, "action": "RESPOND"}
