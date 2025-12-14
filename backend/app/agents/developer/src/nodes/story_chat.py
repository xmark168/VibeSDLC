"""Story Chat node - Reply to user message in story chat context."""

import logging
from uuid import UUID

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.nodes._llm import fast_llm
from app.agents.developer.src.schemas import StoryChatResponse
from app.agents.developer.src.utils.story_logger import StoryLogger

logger = logging.getLogger(__name__)


async def story_chat(state: DeveloperState, agent=None) -> DeveloperState:
    """Reply to user message in story chat using LLM.
    
    This node handles STORY_MESSAGE task type - when user sends message
    in story detail chat while story is being processed.
    """
    story_id = state.get("story_id", "")
    story_title = state.get("story_title", "Unknown Story")
    user_message = state.get("user_message", "")
    
    if not story_id:
        logger.warning("[story_chat] No story_id in state")
        return {**state, "response": "Missing story context", "action": "END"}
    
    # Create story logger to reply in story chat
    story_logger = StoryLogger(
        story_id=UUID(story_id),
        agent=agent,
        node_name="story_chat"
    )
    
    system_prompt = f"""Bạn là Developer Agent đang xử lý story "{story_title}".
User vừa gửi tin nhắn trong story chat. Hãy trả lời ngắn gọn, thân thiện.

Quy tắc:
- Nếu user hỏi về tiến độ → Thông báo đang xử lý
- Nếu user muốn dừng/pause → Hướng dẫn dùng nút Pause
- Nếu user muốn hủy → Hướng dẫn dùng nút Cancel  
- Nếu user có yêu cầu thay đổi → Khuyên pause trước khi thay đổi
- Trả lời bằng tiếng Việt, ngắn gọn (1-3 câu)"""

    user_prompt = f"User message: {user_message}"
    
    try:
        structured_llm = fast_llm.with_structured_output(StoryChatResponse)
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        reply = result.response
        
        # Handle special actions if needed
        if result.action == "pause":
            reply += "\n\n💡 Tip: Nhấn nút ⏸️ Pause để tạm dừng task."
        elif result.action == "cancel":
            reply += "\n\n💡 Tip: Nhấn nút ❌ Cancel để hủy task."
            
    except Exception as e:
        logger.warning(f"[story_chat] LLM error: {e}")
        reply = f"📝 Đã nhận tin nhắn. Tôi đang xử lý story '{story_title}'."
    
    await story_logger.message(reply)
    
    logger.info(f"[story_chat] Replied to message for story {story_id[:8]}")
    return {**state, "response": reply, "action": "END"}
