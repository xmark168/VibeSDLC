"""Router node - Entry point for Tester workflow."""

import logging
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.schemas import RoutingDecision
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.nodes.helpers import get_llm_config, query_stories_from_db
from app.agents.core.llm_factory import create_fast_llm, create_medium_llm
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)

_llm = create_fast_llm()  # Fast model (Haiku)


async def router(state: TesterState, agent=None) -> dict:
    """Hybrid routing: rule-based for WRITE_TESTS, LLM for MESSAGE."""
    project_id = state.get("project_id")
    story_ids = state.get("story_ids", [])
    task_type = state.get("task_type", "")
    is_auto = state.get("is_auto", False)
    user_message = state.get("user_message", "")
    
    logger.info(f"[router] task_type={task_type}, is_auto={is_auto}, story_ids={len(story_ids)}")

    # Get tech_stack
    tech_stack = state.get("tech_stack", "nextjs")
    try:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            if project:
                tech_stack = project.tech_stack or tech_stack
    except Exception as e:
        logger.warning(f"[router] Could not query project: {e}")

    # Route 1: WRITE_TESTS (rule-based)
    if task_type == "write_tests" or is_auto or story_ids:
        logger.info("[router] WRITE_TESTS → PLAN_TESTS (rule-based)")
        stories = state.get("stories", [])
        if not stories:
            stories = await query_stories_from_db(project_id, story_ids, agent)
        
        if stories:
            return {"action": "PLAN_TESTS", "stories": stories, "tech_stack": tech_stack}
        
        return {
            "action": "CONVERSATION",
            "tech_stack": tech_stack,
            "message": "Không có stories nào trong REVIEW cần tạo tests.",
        }
    
    # Route 2: MESSAGE (LLM-based)
    if task_type == "message" and user_message:
        try:
            logger.info("[router] MESSAGE → analyzing with LLM")
            structured_llm = _llm.with_structured_output(RoutingDecision)
            result = await structured_llm.ainvoke(
                [
                    SystemMessage(content=get_system_prompt("routing")),
                    HumanMessage(content=get_user_prompt("routing", user_message=user_message)),
                ],
                config=get_llm_config(state, "router"),
            )

            action = result.action
            logger.info(f"[router] LLM decision: {action}, reason: {result.reason}")

            if action == "PLAN_TESTS":
                stories = await query_stories_from_db(project_id, story_ids, agent)
                return {"action": action, "stories": stories, "tech_stack": tech_stack}

            return {"action": action, "tech_stack": tech_stack}
        except Exception as e:
            logger.error(f"[router] LLM error: {e}, fallback to CONVERSATION")
            return {"action": "CONVERSATION", "tech_stack": tech_stack}
    
    # Fallback
    logger.warning(f"[router] Unknown task_type='{task_type}' → CONVERSATION")
    return {"action": "CONVERSATION", "tech_stack": tech_stack}
