"""Router node for Team Leader."""

import logging
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.core.llm_factory import get_llm
from app.agents.core.prompt_utils import build_system_prompt, build_user_prompt
from app.agents.team_leader.src.nodes._utils import ROLE_WIP_MAP, get_callback_config, _PROMPTS, _DEFAULTS
from app.agents.team_leader.src.schemas import RoutingDecision
from app.agents.team_leader.src.state import TeamLeaderState

logger = logging.getLogger(__name__)


async def _check_domain_change(user_message: str, existing_prd_title: str, state: dict) -> bool:
    """Use LLM to check if user request is for a different domain than existing PRD."""
    try:
        prompt = f"""So sánh 2 project sau và xác định xem chúng có CÙNG DOMAIN hay KHÁC DOMAIN.

Project hiện tại: "{existing_prd_title}"
Yêu cầu mới của user: "{user_message}"

CÙNG DOMAIN: Nếu user muốn update, sửa đổi, thêm feature cho project hiện tại.
VÍ DỤ: "Website bán sách" + "thêm feature giỏ hàng" = CÙNG DOMAIN

KHÁC DOMAIN: Nếu user muốn tạo một project hoàn toàn mới, khác lĩnh vực.
VÍ DỤ: "Website bán sách" + "tạo website quản lý công việc" = KHÁC DOMAIN

Trả lời CHỈ một từ: SAME hoặc DIFFERENT"""

        response = await get_llm("router").ainvoke(
            [HumanMessage(content=prompt)],
            config=get_callback_config(state, "check_domain_change")
        )
        answer = response.content.strip().upper()
        return "DIFFERENT" in answer
    except Exception as e:
        logger.error(f"[_check_domain_change] Error: {e}")
        return False


async def router(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Route request using structured LLM output."""
    try:
        board_state = ""
        if agent and hasattr(agent, 'context'):
            try:
                _, _, wip = agent.context.get_kanban_context()
                board_state = f"WIP: InProgress={wip.get('InProgress', '?')}, Review={wip.get('Review', '?')}"
            except Exception:
                pass

        user_message = state["user_message"]
        if state.get("attachments"):
            files = [att.get("filename", "file") for att in state["attachments"]]
            user_message = f"{user_message}\n[Đính kèm: {', '.join(files)}]"
            logger.info(f"[router] Message includes {len(files)} attachment(s)")

        messages = [
            SystemMessage(content=build_system_prompt(_PROMPTS, "routing_decision", agent, _DEFAULTS)),
            HumanMessage(content=build_user_prompt(
                _PROMPTS,
                "routing_decision",
                user_message,
                name=agent.name if agent else "Team Leader",
                conversation_history=state.get("conversation_history", ""),
                user_preferences=state.get("user_preferences", ""),
                board_state=board_state,
            ))
        ]

        structured_llm = get_llm("router").with_structured_output(RoutingDecision)
        decision = await structured_llm.ainvoke(messages, config=get_callback_config(state, "router"))
        logger.info(f"[router] Decision: action={decision.action}, target={decision.target_role}")
        result = decision.model_dump()

        if result["action"] == "DELEGATE":
            wip_col = ROLE_WIP_MAP.get(result.get("target_role"))
            if wip_col and agent and hasattr(agent, 'context'):
                _, _, wip_available = agent.context.get_kanban_context()
                if wip_available.get(wip_col, 1) <= 0:
                    return {
                        **state,
                        "action": "RESPOND",
                        "wip_blocked": True,
                        "message": f"Hiện tại {wip_col} đang full. Cần đợi stories hoàn thành.",
                        "confidence": 0.95
                    }

            if result.get("target_role") == "business_analyst" and agent:
                has_attachments = bool(state.get("attachments"))

                if has_attachments:
                    logger.info("[router] User uploaded file(s), skipping domain check.")
                else:
                    domain_check_result = await _handle_domain_check(state, result, agent)
                    if domain_check_result:
                        return domain_check_result

        return {**state, **result, "wip_blocked": False}
    except Exception as e:
        logger.error(f"[router] {e}", exc_info=True)
        return {
            **state,
            "action": "RESPOND",
            "message": "Xin lỗi, có lỗi xảy ra.",
            "confidence": 0.0,
            "wip_blocked": False
        }


async def _handle_domain_check(state: TeamLeaderState, result: dict, agent) -> dict | None:
    """Handle domain change detection for BA delegation."""
    try:
        from sqlmodel import Session, select

        from app.core.db import engine
        from app.models import ArtifactType, Epic, Message, Story
        from app.services.artifact_service import ArtifactService

        project_id = UUID(state["project_id"])

        with Session(engine) as session:
            artifact_service = ArtifactService(session)
            existing_prd = artifact_service.get_latest_version(
                project_id=project_id,
                artifact_type=ArtifactType.PRD
            )

            if not existing_prd:
                return None

            message_count = len(session.exec(
                select(Message).where(
                    Message.project_id == project_id,
                    Message.author_type == "user"
                )
            ).all())

            if message_count <= 1:
                logger.info(f"[router] No previous messages, auto-replacing '{existing_prd.title}'")
                artifact_service.delete_by_type(project_id, ArtifactType.PRD)
                artifact_service.delete_by_type(project_id, ArtifactType.USER_STORIES)

                for epic in session.exec(select(Epic).where(Epic.project_id == project_id)).all():
                    session.delete(epic)
                for story in session.exec(select(Story).where(Story.project_id == project_id)).all():
                    session.delete(story)
                session.commit()

                if agent and hasattr(agent, 'project_files') and agent.project_files:
                    await agent.project_files.archive_docs()

                return None

            is_different = await _check_domain_change(
                state["user_message"],
                existing_prd.title,
                state
            )

            stories_count = len(session.exec(
                select(Story).where(Story.project_id == project_id)
            ).all())

            if is_different:
                logger.info(f"[router] Domain change detected: '{existing_prd.title}' → new request")
                return {
                    **state,
                    "action": "CONFIRM_REPLACE",
                    "existing_prd_title": existing_prd.title,
                    "existing_stories_count": stories_count,
                    "needs_replace_confirm": True,
                    "wip_blocked": False
                }

            is_update_request = result.get("is_update_request", False)
            logger.info(f"[router] LLM decision: is_update_request={is_update_request}")

            if is_update_request:
                logger.info("[router] Same domain with UPDATE request, delegating to BA")
                return None

            logger.info(f"[router] Same domain detected: '{existing_prd.title}', asking user")
            return {
                **state,
                "action": "CONFIRM_EXISTING",
                "existing_prd_title": existing_prd.title,
                "existing_stories_count": stories_count,
                "wip_blocked": False
            }

    except Exception as e:
        logger.error(f"[router] Error checking domain change: {e}", exc_info=True)
        return None
