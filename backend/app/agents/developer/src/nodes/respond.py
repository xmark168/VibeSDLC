"""Respond node - Reply to @Developer message in main chat."""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer.src.state import DeveloperState
from app.agents.core.llm_factory import get_llm
from app.agents.developer.src.schemas import StoryChatResponse
from app.agents.developer.src.utils.prompt_utils import build_system_prompt, format_input_template

logger = logging.getLogger(__name__)


async def respond(state: DeveloperState, agent=None) -> DeveloperState:
    """
    Reply to @Developer message in main chat.
    """
    user_message = state.get("user_message", "")
    user_message_lower = user_message.lower()
    
    # Quick responses for common queries (no LLM needed)
    if "help" in user_message_lower or "giúp" in user_message_lower:
        reply = """Tôi là Developer, chuyên phụ trách phát triển code! 💻

**Tôi có thể giúp bạn:**
- Triển khai tính năng mới
- Viết code theo User Story/PRD
- Review và cải thiện code
- Tạo module, component

**Cách sử dụng:**
- Kéo story sang In Progress → Tôi tự động bắt đầu
- Hoặc nhắn: "@Developer triển khai chức năng login"
"""
    elif "status" in user_message_lower or "tiến độ" in user_message_lower or "progress" in user_message_lower:
        reply = "📊 Hiện tại chưa có task nào đang xử lý. Bạn có thể kéo story sang In Progress để tôi bắt đầu!"
    else:
        # Use LLM for other messages
        try:
            system_prompt = build_system_prompt("respond", agent=agent)
            user_prompt = format_input_template("respond", user_message=user_message, project_context="")
            
            fast_llm = get_llm("router")
            structured_llm = fast_llm.with_structured_output(StoryChatResponse)
            result = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            reply = result.response
            
            # Check if this is a dev request that should trigger implementation
            if result.action == "implement":
                return {**state, "action": "IMPLEMENT", "response": reply}
                
        except Exception as e:
            logger.warning(f"[respond] LLM error: {e}")
            reply = "📝 Đã nhận yêu cầu. Bạn có thể tạo story và kéo sang In Progress để tôi bắt đầu triển khai."
    
    # Send response to main chat
    if agent and reply:
        await agent.message_user("response", reply)
    
    logger.info(f"[respond] Replied to @Developer message")
    return {**state, "response": reply, "action": "END"}
