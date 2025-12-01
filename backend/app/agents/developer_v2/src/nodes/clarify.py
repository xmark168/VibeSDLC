"""Clarify node - Ask for clarification when story is unclear."""
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


async def clarify(state: DeveloperState, agent=None) -> DeveloperState:
    """Ask for clarification when story is unclear."""
    try:
        sys_prompt = _build_system_prompt("clarify", agent)
        user_prompt = _get_prompt("clarify", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(state.get("acceptance_criteria", [])),
            unclear_points=state.get("reason", "Story không rõ ràng"),
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await fast_llm.ainvoke(messages, config=_cfg(state, "clarify"))
        return {**state, "message": response.content, "action": "CLARIFY"}
        
    except Exception as e:
        log("clarify", f"Error: {e}", "error")
        return {**state, "message": "🤔 Cần thêm thông tin. Mô tả chi tiết hơn?", "action": "CLARIFY"}
