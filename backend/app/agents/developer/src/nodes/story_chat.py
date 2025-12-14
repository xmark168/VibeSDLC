"""Story Chat node - Reply to user message in story chat context."""

import logging
from uuid import UUID

from langchain_core.messages import SystemMessage, HumanMessage
from sqlmodel import Session, select

from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.nodes._llm import fast_llm
from app.agents.developer.src.schemas import StoryChatResponse
from app.agents.developer.src.utils.story_logger import StoryLogger
from app.agents.developer.src.utils.prompt_utils import build_system_prompt, format_input_template
from app.core.db import engine
from app.models.story import StoryMessage, Story

logger = logging.getLogger(__name__)


async def _load_story_info(story_id: str) -> dict:
    """Load story details from database."""
    try:
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if not story:
                return {}
            return {
                "story_code": story.story_code or "",
                "title": story.title or "Unknown Story",
                "content": story.description or "",
                "status": story.status.value if story.status else "",
                "agent_state": story.agent_state.value if story.agent_state else "",
                "branch_name": story.branch_name or "",
                "pr_url": story.pr_url or "",
            }
    except Exception as e:
        logger.warning(f"[story_chat] Failed to load story info: {e}")
        return {}


async def _load_conversation_history(story_id: str) -> list:
    """Load last 20 messages from story_messages table."""
    try:
        with Session(engine) as session:
            stmt = (
                select(StoryMessage)
                .where(StoryMessage.story_id == UUID(story_id))
                .order_by(StoryMessage.created_at.desc())
                .limit(20)
            )
            messages = session.exec(stmt).all()
            return [
                {"role": m.author_type, "author": m.author_name, "content": m.content}
                for m in reversed(messages)
            ]
    except Exception as e:
        logger.warning(f"[story_chat] Failed to load history: {e}")
        return []


async def _summarize_history(messages: list) -> str:
    """Summarize older messages using fast_llm."""
    messages_text = "\n".join([f"{m['author']}: {m['content']}" for m in messages])
    
    try:
        result = await fast_llm.ainvoke([
            SystemMessage(content="Summarize this conversation briefly in 2-3 sentences. Vietnamese."),
            HumanMessage(content=messages_text)
        ])
        return result.content
    except Exception as e:
        logger.warning(f"[story_chat] Failed to summarize: {e}")
        return "(Could not summarize earlier messages)"


async def _format_conversation_history(story_id: str) -> str:
    """Load and format conversation history, summarizing if too long."""
    conversation_history = await _load_conversation_history(story_id)
    
    if not conversation_history:
        return "(No previous messages)"
    
    # If history > 10, summarize older messages and keep recent 5
    if len(conversation_history) > 10:
        older_messages = conversation_history[:-5]
        recent_messages = conversation_history[-5:]
        
        summary = await _summarize_history(older_messages)
        history_text = f"[Summary of earlier conversation]\n{summary}\n\n[Recent messages]\n"
        history_text += "\n".join([f"{m['author']}: {m['content']}" for m in recent_messages])
    else:
        history_text = "\n".join([
            f"{m['author']}: {m['content']}" 
            for m in conversation_history
        ])
    
    return history_text


async def story_chat(state: DeveloperState, agent=None) -> DeveloperState:
    """Reply to user message in story chat using LLM"""
    story_id = state.get("story_id", "")
    user_message = state.get("user_message", "")
    
    if not story_id:
        logger.warning("[story_chat] No story_id in state")
        return {**state, "response": "Missing story context", "action": "END"}
    
    # Load story info from DB
    story_info = await _load_story_info(story_id)
    story_title = story_info.get("title", "Unknown Story")
    story_code = story_info.get("story_code", "")
    story_content = story_info.get("content", "")
    story_status = story_info.get("status", "")
    story_agent_state = story_info.get("agent_state", "")
    branch_name = story_info.get("branch_name", "")
    pr_url = story_info.get("pr_url", "")
    
    # Create story logger to reply in story chat
    story_logger = StoryLogger(
        story_id=UUID(story_id),
        agent=agent,
        node_name="story_chat"
    )
    
    # Get progress from state (checkpoint)
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    # Load and format conversation history
    conversation_history = await _format_conversation_history(story_id)
    
    # Build prompts from yaml with full context
    system_prompt = build_system_prompt("story_chat", agent=agent, story_title=story_title)
    user_prompt = format_input_template(
        "story_chat", 
        story_code=story_code,
        story_title=story_title,
        story_content=story_content,
        story_status=story_status,
        story_agent_state=story_agent_state,
        branch_name=branch_name,
        pr_url=pr_url,
        current_step=current_step,
        total_steps=total_steps,
        conversation_history=conversation_history,
        user_message=user_message
    )
    
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
