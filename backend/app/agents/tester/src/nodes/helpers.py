"""Helper utilities for Tester nodes."""

import json
import logging
from pathlib import Path
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select
from sqlalchemy import or_

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt, build_system_prompt_with_persona
from app.agents.tester.src.state import TesterState
from app.core.agent.llm_factory import get_llm
from app.core.db import engine
from app.models import Story, StoryStatus
from app.models.base import StoryAgentState

logger = logging.getLogger(__name__)

FALLBACK_MESSAGES = {
    "plan_created": "📋 Đã tạo test plan! Bắt đầu implement nhé~",
    "tests_running": "🧪 Đang chạy tests, đợi mình chút nhé...",
    "tests_passed": "🎉 Tuyệt vời! All tests passed!",
    "tests_failed": "❌ Có tests fail rồi, để mình xem...",
    "analyzing": "🔍 Đang phân tích lỗi...",
    "fixing": "🔧 Đang fix, đợi mình chút nhé!",
    "implement_done": "✅ Đã implement xong tests!",
    "max_retries": "⚠️ Đã thử nhiều lần nhưng vẫn fail. Cần review manual.",
    "typecheck_error": "❌ Có lỗi TypeScript, để mình xem...",
    "default": "Đã nhận! 👍",
}


def get_llm_config(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


async def generate_user_message(
    action: str,
    context: str,
    agent=None,
    extra_info: str = "",
) -> str:
    """Generate natural message with persona using LLM."""
    try:
        sys_prompt = build_system_prompt_with_persona("response_generation", agent)
        user_prompt = get_user_prompt(
            "response_generation",
            action=action,
            context=context,
            extra_info=extra_info or "N/A"
        )
        
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.debug(f"[generate_user_message] LLM failed: {e}, using fallback")
        return FALLBACK_MESSAGES.get(action, FALLBACK_MESSAGES["default"])


async def send_message(state: TesterState, agent, content: str, message_type: str = "update"):
    """Send message to main chat (user mention) or log for auto tasks."""
    if not agent:
        logger.warning("[send_message] No agent provided, skipping message")
        return
    
    is_auto = state.get("is_auto", False)
    story_ids = state.get("story_ids", [])
    
    logger.debug(f"[send_message] is_auto={is_auto}, story_ids={story_ids}, content={content[:50]}...")
    
    if is_auto and story_ids:
        logger.info(f"[send_message] Auto task message: {content[:100]}...")
    elif not is_auto:
        await agent.message_user("response", content)
    else:
        logger.warning(f"[send_message] is_auto={is_auto} but no story_ids, message dropped: {content[:50]}...")


async def query_stories_from_db(project_id: str, story_ids: list, agent) -> list:
    """Query stories in REVIEW status from database."""
    logger.info(f"[query_stories_from_db] project_id={project_id}, story_ids={story_ids}")

    try:
        with Session(engine) as session:
            query = select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW,
            )
            
            if story_ids:
                query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
            else:
                query = query.where(
                    or_(
                        Story.agent_state.is_(None),
                        Story.agent_state.in_([StoryAgentState.PENDING, StoryAgentState.CANCELED]),
                    )
                )

            stories = session.exec(query).all()
            logger.info(f"[query_stories_from_db] Found {len(stories)} stories")

            if not stories:
                return []

            stories_data = [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "description": s.description,
                    "acceptance_criteria": s.acceptance_criteria,
                }
                for s in stories
            ]

        if agent and stories_data:
            for story in stories_data:
                try:
                    await agent.update_story_agent_state(
                        story_id=UUID(story["id"]),
                        new_state="PROCESSING",
                        progress_message="Đang phân tích và tạo test cases...",
                    )
                except Exception as e:
                    logger.warning(f"[query_stories_from_db] Failed to update state: {e}")

        return stories_data

    except Exception as e:
        logger.error(f"[query_stories_from_db] Error: {e}")
        return []


def detect_testing_context(project_path: str) -> dict:
    """Detect auth library, ORM, existing mocks, and ESM warnings."""
    workspace = Path(project_path)
    context = {
        "auth_library": None,
        "auth_pattern": "",
        "orm": None,
        "existing_mocks": [],
        "esm_warning": "",
        "prisma_mock_pattern": "",
        "import_alias": "@/",
    }

    if not workspace.exists():
        return context

    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            if "next-auth" in deps:
                context["auth_library"] = "nextauth"
                context["auth_pattern"] = "NEXTAUTH: Test authorize() directly, mock Prisma"
            elif "clerk" in deps or "@clerk/nextjs" in deps:
                context["auth_library"] = "clerk"
                context["auth_pattern"] = "Clerk: mock @clerk/nextjs hooks"

            if "@prisma/client" in deps or "prisma" in deps:
                context["orm"] = "prisma"
                context["prisma_mock_pattern"] = "jest.mock('@/lib/prisma', () => ({ prisma: {...} }))"
            elif "drizzle-orm" in deps:
                context["orm"] = "drizzle"

        except Exception as e:
            logger.warning(f"[detect_testing_context] Failed to parse package.json: {e}")

    jest_setup = workspace / "jest.setup.ts"
    if not jest_setup.exists():
        jest_setup = workspace / "jest.setup.js"

    if jest_setup.exists():
        try:
            setup_content = jest_setup.read_text(encoding="utf-8")
            mock_patterns = [
                ("next/navigation", "useRouter, usePathname, useSearchParams"),
                ("next/router", "useRouter"),
                ("matchMedia", "window.matchMedia"),
                ("IntersectionObserver", "IntersectionObserver"),
                ("ResizeObserver", "ResizeObserver"),
            ]

            for module, description in mock_patterns:
                if module in setup_content:
                    context["existing_mocks"].append(f"{module} ({description})")

        except Exception as e:
            logger.warning(f"[detect_testing_context] Failed to read jest.setup: {e}")

    context["esm_warning"] = "ESM PACKAGES TO AVOID: uuid, nanoid, node-fetch, chalk"

    return context
