"""Conversational node for handling general chat with user."""

import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.core.llm_factory import get_llm
from app.agents.core.prompt_utils import get_task_prompts
from app.agents.team_leader.src.nodes._utils import detect_specialist_completion, get_callback_config, _PROMPTS

logger = logging.getLogger(__name__)


async def conversational(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Generate conversational response."""
    try:
        conversation_history = state.get("conversation_history", "")

        # Detect if specialist just completed a task
        specialist_role = detect_specialist_completion(conversation_history)

        # Build context for LLM
        prompts = get_task_prompts(_PROMPTS, "conversational")
        sys_prompt = prompts["system_prompt"]

        # Add specialist completion context if detected
        specialist_context = ""
        if specialist_role:
            role_names = {
                "business_analyst": "Business Analyst",
                "developer": "Developer",
                "tester": "Tester"
            }
            role_display = role_names.get(specialist_role, specialist_role)
            specialist_context = f"""
**LƯU Ý QUAN TRỌNG:** {role_display} vừa hoàn thành task. Bạn đang tiếp quản cuộc hội thoại.
- Hãy chào đón user trở lại một cách tự nhiên
- Có thể hỏi user cần gì tiếp theo
- Đừng lặp lại những gì {role_display} đã nói"""

        if conversation_history:
            sys_prompt += f"""

---

**Cuộc trò chuyện gần đây:**
{conversation_history}
{specialist_context}

**Lưu ý:** Dựa vào context trên để trả lời tự nhiên và liên quan. Đừng lặp lại những gì đã nói."""

        response = await get_llm("respond").ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=state["user_message"])],
            config=get_callback_config(state, "conversational")
        )
        if agent:
            await agent.message_user("response", response.content)
        return {**state, "message": response.content, "action": "CONVERSATION"}
    except Exception as e:
        logger.error(f"[conversational] {e}")
        msg = "Hmm, có gì đó không ổn. Bạn thử lại được không? 😅"
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "CONVERSATION"}
