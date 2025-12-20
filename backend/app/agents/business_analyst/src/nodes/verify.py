import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session

from ..state import BAState
from ..schemas import VerifyStoryOutput
from app.core.db import engine
from app.models import Epic, Story, StoryStatus, EpicStatus

from .utils import _invoke_structured, _cfg, _sys_prompt, _user_prompt, _default_llm

logger = logging.getLogger(__name__)

async def verify_story_simple(state: dict, agent=None) -> dict:
    """Verify a newly created story with single LLM call.
    
    Loads PRD + existing stories, then asks LLM to:
    1. Check for duplicates
    2. Evaluate INVEST compliance
    3. Suggest improvements
    
    Args:
        state: Must contain:
            - new_story: Story object to verify
            - project_id: UUID of the project
            - full_prd: PRD dict (optional)
            - existing_stories: List of existing stories (optional)
        agent: BA agent instance for messaging
    
    Returns:
        dict with verification results
    """
    logger.info("[BA] Starting simple story verification...")
    
    new_story = state.get("new_story")
    project_id = state.get("project_id")
    full_prd = state.get("full_prd")
    existing_stories = state.get("existing_stories", [])
    
    if not new_story:
        logger.error("[BA] No new_story in state")
        return {"error": "No story provided", "is_complete": True}
    
    # Build story info
    story_info = {
        "title": new_story.title,
        "description": new_story.description or "(empty)",
        "acceptance_criteria": new_story.acceptance_criteria or "(empty)",
        "type": new_story.type.value if new_story.type else "UserStory"
    }
    
    # Build PRD context
    prd_context = "No PRD available for this project."
    if full_prd:
        prd_context = f"""PROJECT PRD:
- Project Name: {full_prd.get('project_name', 'Unknown')}
- Overview: {full_prd.get('overview', 'N/A')[:500]}
- Target Users: {json.dumps(full_prd.get('target_users', []), ensure_ascii=False)}
- Core Features: {json.dumps(full_prd.get('features', [])[:5], ensure_ascii=False)}
"""
    
    # Build existing stories context
    stories_context = "No existing stories in this project."
    if existing_stories:
        stories_list = []
        for s in existing_stories[:20]:  # Limit to 20 stories
            title = s.title if hasattr(s, 'title') else s.get('title', 'Unknown')
            desc = s.description if hasattr(s, 'description') else s.get('description', '')
            desc_preview = (desc or "")[:100]
            stories_list.append(f"- {title}: {desc_preview}")
        stories_context = f"EXISTING STORIES ({len(existing_stories)} total):\n" + "\n".join(stories_list)
    
    # Build prompts from YAML
    system_prompt = _sys_prompt(agent, "verify_story")
    user_prompt = _user_prompt(
        "verify_story",
        prd_context=prd_context,
        stories_context=stories_context,
        story_title=story_info['title'],
        story_description=story_info['description'],
        story_acceptance_criteria=story_info['acceptance_criteria'],
        story_type=story_info['type']
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_default_llm,
        schema=VerifyStoryOutput,
        messages=messages,
        config=_cfg(state, "verify_story_simple"),
        fallback_data={
            "is_duplicate": False,
            "invest_score": 4,
            "invest_issues": [],
            "summary": "Không thể xác minh story"
        }
    )
    
    logger.info(f"[BA] Story verification complete: invest_score={result.get('invest_score')}, "
                f"is_duplicate={result.get('is_duplicate')}")
    
    # Send suggestions to user (always send, even without agent)
    await _send_verify_message(agent, new_story, result, project_id=project_id)
    
    return {
        "verification_result": result,
        "is_complete": True
    }




async def _send_verify_message(agent, story, result: dict, project_id=None) -> None:
    """Send verification result message to user via Kafka."""
    from uuid import uuid4
    from app.kafka import get_kafka_producer, KafkaTopics
    from app.kafka.event_schemas import AgentEvent
    from app.models import Message, AuthorType
    
    # Extract all fields from result
    is_duplicate = result.get("is_duplicate", False)
    duplicate_of = result.get("duplicate_of")
    duplicate_reason = result.get("duplicate_reason")
    invest_score = result.get("invest_score", 6)
    invest_issues = result.get("invest_issues", [])
    
    # Story content suggestions (all in English)
    suggested_title = result.get("suggested_title")
    suggested_description = result.get("suggested_description")
    suggested_requirements = result.get("suggested_requirements")
    suggested_ac = result.get("suggested_acceptance_criteria")
    
    # Additional suggestions
    suggested_story_point = result.get("suggested_story_point")
    suggested_priority = result.get("suggested_priority")
    should_split = result.get("should_split", False)
    split_suggestions = result.get("split_suggestions")
    
    summary = result.get("summary", "")
    
    # Build natural message based on result
    if is_duplicate:
        content = f"Mình vừa kiểm tra story \"{story.title}\" và thấy có vẻ trùng với story đã có. Bạn xem chi tiết bên dưới nhé!"
    elif invest_score >= 5:
        content = f"Story \"{story.title}\" của bạn đã đạt chuẩn INVEST rồi đó! 👍"
    elif invest_score >= 3:
        content = f"Mình đã review story \"{story.title}\". Có một vài điểm cần cải thiện, bạn xem gợi ý bên dưới nhé!"
    else:
        content = f"Story \"{story.title}\" cần được cải thiện khá nhiều. Mình có một số gợi ý cho bạn!"
    
    # Check if we have any suggestions
    has_suggestions = bool(
        suggested_title or suggested_description or 
        suggested_requirements or suggested_ac or
        suggested_story_point or suggested_priority or
        should_split
    )
    
    details = {
        "message_type": "story_review",
        "story_id": str(story.id),
        "story_title": story.title,
        # Duplicate info
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "duplicate_reason": duplicate_reason,
        # INVEST evaluation
        "invest_score": invest_score,
        "invest_issues": invest_issues,
        # Story content suggestions (English)
        "suggested_title": suggested_title,
        "suggested_description": suggested_description,
        "suggested_requirements": suggested_requirements,
        "suggested_acceptance_criteria": suggested_ac,
        # Additional suggestions
        "suggested_story_point": suggested_story_point,
        "suggested_priority": suggested_priority,
        "should_split": should_split,
        "split_suggestions": split_suggestions,
        # Meta
        "has_suggestions": has_suggestions,
        "summary": summary,
    }
    
    # Get agent info (agent.name is already human_name from base_agent)
    agent_name = agent.name if agent else "Business Analyst"
    agent_id = str(agent.agent_id) if agent else None
    proj_id = str(project_id) if project_id else (str(agent.project_id) if agent else None)
    
    # Save to DB
    message_id = None
    try:
        with Session(engine) as session:
            db_message = Message(
                project_id=project_id or (agent.project_id if agent else None),
                content=content,
                author_type=AuthorType.AGENT,
                agent_id=agent.agent_id if agent else None,
                message_type="story_review",
                structured_data=details,
                message_metadata={"agent_name": agent_name}  # Fallback for agent_name
            )
            session.add(db_message)
            session.commit()
            session.refresh(db_message)
            message_id = db_message.id
            logger.info(f"[BA] Saved story review message to DB: {message_id}")
    except Exception as e:
        logger.error(f"[BA] Failed to save message to DB: {e}")
    
    # Publish to Kafka
    try:
        producer = await get_kafka_producer()
        event = AgentEvent(
            event_type="agent.response",
            agent_name=agent_name,
            agent_id=agent_id or "ba-auto-verify",
            project_id=proj_id,
            content=content,
            details={
                **details,
                "message_id": str(message_id) if message_id else None,
            },
            execution_context={
                "mode": "background",
                "task_type": "story_verify",
                "display_mode": "chat",
            }
        )
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        logger.info(f"[BA] Published story review to Kafka for story {story.id}")
    except Exception as e:
        logger.error(f"[BA] Failed to publish to Kafka: {e}")




async def send_review_action_response(
    story_id: str,
    story_title: str,
    action: str,
    project_id,
    agent = None
) -> None:
    """
    Send natural response message when user takes action on story review.
    Uses LLM to generate personality-driven message.
    """
    from app.models import Message, AuthorType
    from sqlmodel import Session
    from app.core.db import engine
    
    logger.info(f"[BA] Generating review action response for story {story_id}, action: {action}")
    
    # Get agent info
    agent_name = agent.name if agent else "Business Analyst"
    agent_id = str(agent.agent_id) if agent else None
    proj_id = str(project_id) if project_id else (str(agent.project_id) if agent else None)
    
    # Simple confirmation messages (no LLM needed)
    confirmation_messages = {
        "apply": f"Áp dụng gợi ý cho story \"{story_title}\".",
        "keep": f"Giữ nguyên story \"{story_title}\".",
        "remove": f"Loại bỏ story \"{story_title}\"."
    }
    content = confirmation_messages.get(action, f"Đã xử lý story \"{story_title}\".")
    
    # Save to DB
    message_id = None
    try:
        with Session(engine) as session:
            db_message = Message(
                project_id=project_id,
                content=content,
                author_type=AuthorType.AGENT,
                agent_id=agent.agent_id if agent else None,
                message_type="text",
                message_metadata={"agent_name": agent_name}
            )
            session.add(db_message)
            session.commit()
            session.refresh(db_message)
            message_id = db_message.id
            logger.info(f"[BA] Saved review action response to DB: {message_id}")
    except Exception as e:
        logger.error(f"[BA] Failed to save message to DB: {e}")
    
    # Publish to Kafka
    try:
        producer = await get_kafka_producer()
        event = AgentEvent(
            event_type="agent.response",
            agent_name=agent_name,
            agent_id=agent_id or "ba-auto-verify",
            project_id=proj_id,
            content=content,
            details={
                "message_id": str(message_id) if message_id else None,
                "action": action,
                "story_id": story_id,
            },
            execution_context={
                "mode": "background",
                "task_type": "review_action_response",
                "display_mode": "chat",
            }
        )
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        logger.info(f"[BA] Published review action response to Kafka")
    except Exception as e:
        logger.error(f"[BA] Failed to publish to Kafka: {e}")



