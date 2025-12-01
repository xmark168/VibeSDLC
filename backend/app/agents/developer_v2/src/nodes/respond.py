"""Respond node - Generate conversational response to user."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.utils.prompt_utils import (
    get_prompt as _get_prompt,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import fast_llm
from app.agents.developer_v2.src.nodes._helpers import log

logger = logging.getLogger(__name__)


async def respond(state: DeveloperState, agent=None) -> DeveloperState:
    """Generate conversational response to user."""
    try:
        existing_msg = state.get("message", "")
        if existing_msg and len(existing_msg) > 100:
            return {**state, "action": "RESPOND"}
        
        sys_prompt = _build_system_prompt("respond", agent)
        user_prompt = _get_prompt("respond", "user_prompt").format(
            story_title=state.get("story_title", ""),
            story_content=state.get("story_content", ""),
            router_reason=state.get("reason", "general response"),
        )
        
        messages = [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)]
        response = await fast_llm.ainvoke(messages, config=_cfg(state, "respond"))
        
        return {**state, "message": response.content, "action": "RESPOND"}
        
    except Exception as e:
        log("respond", f"Error: {e}", "error")
        return {**state, "message": state.get("message") or "Đã nhận tin nhắn! 👋", "action": "RESPOND"}
