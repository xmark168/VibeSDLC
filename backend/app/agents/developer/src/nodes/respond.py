"""Respond node - Reply to @Developer message in main chat."""

import logging

from app.agents.developer.src.state import DeveloperState

logger = logging.getLogger(__name__)


async def respond(state: DeveloperState, agent=None) -> DeveloperState:
    """Reply to @Developer message in main chat.
    
    This node handles MESSAGE task type - when user mentions @Developer
    in the main workspace chat.
    """
    user_message = state.get("user_message", "").lower()
    
    # Determine response based on message content
    if "help" in user_message or "giúp" in user_message:
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
    elif "status" in user_message or "tiến độ" in user_message or "progress" in user_message:
        reply = "📊 Hiện tại chưa có task nào đang xử lý. Bạn có thể kéo story sang In Progress để tôi bắt đầu!"
    else:
        # Default: treat as dev request - signal to start story processing
        reply = None  # Will be handled by returning action=IMPLEMENT
        return {**state, "action": "IMPLEMENT", "response": ""}
    
    # Send response to main chat
    if agent and reply:
        await agent.message_user("response", reply)
    
    logger.info(f"[respond] Replied to @Developer message")
    return {**state, "response": reply or "", "action": "END"}
