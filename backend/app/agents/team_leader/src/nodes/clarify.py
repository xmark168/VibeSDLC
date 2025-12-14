"""Clarify node for Team Leader."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agent.llm_factory import get_llm
from app.core.agent.prompt_utils import build_system_prompt
from app.agents.team_leader.src.nodes._utils import get_callback_config, _PROMPTS, _DEFAULTS
from app.agents.team_leader.src.state import TeamLeaderState

logger = logging.getLogger(__name__)


async def clarify(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Ask clarification question using LLM with persona."""
    try:
        reason = state.get("reason", "need more details")
        hint = state.get("clarification_question", "")

        sys_prompt = build_system_prompt(_PROMPTS, "conversational", agent, _DEFAULTS)
        user_prompt = f"""User vừa nói: "{state['user_message']}"

Mình cần hỏi clarification vì: {reason}
{f'Gợi ý câu hỏi: {hint}' if hint else ''}

Hãy viết MỘT câu hỏi clarification thân thiện, tự nhiên để hiểu rõ hơn user muốn gì.
- Giải thích ngắn gọn tại sao cần thêm info
- Gợi ý cụ thể user cần cung cấp gì (feature name, error message, steps...)
- Dùng emoji phù hợp"""

        response = await get_llm("respond").ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)],
            config=get_callback_config(state, "clarify")
        )
        question = response.content
    except Exception as e:
        logger.error(f"[clarify] LLM error: {e}")
        question = state.get("message") or "Hmm, mình cần biết rõ hơn chút! 🤔 Bạn có thể mô tả chi tiết hơn không?"

    if agent:
        await agent.message_user("response", question)

    return {**state, "message": question, "action": "CLARIFY"}
