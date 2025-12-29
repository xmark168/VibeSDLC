"""Confirmation nodes for handling user confirmations about project actions."""

import logging

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.core.prompt_utils import get_task_prompts
from app.agents.team_leader.src.nodes._utils import _PROMPTS

logger = logging.getLogger(__name__)


async def confirm_replace(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Ask user to confirm replacing existing project with new one."""
    try:
        existing_title = state.get("existing_prd_title", "project hiện tại")
        stories_count = state.get("existing_stories_count", 0)

        question = (
            f"Bạn đã có project '{existing_title}' và các tài liệu liên quan. "
            f"Bạn muốn:"
        )

        if agent:
            # IMPORTANT: Include attachments in context so they can be passed to BA after confirmation
            # Note: use "or []" because attachments may be None
            attachments = state.get("attachments") or []
            question_context = {
                "original_user_message": state.get("user_message", ""),
                "attachments": attachments
            }

            logger.info(f"[confirm_replace] Saving context with {len(attachments)} attachment(s)")

            await agent.message_user(
                "question",
                question,
                question_config={
                    "question_type": "multichoice",
                    "options": [
                        "Thay thế bằng project mới",
                        "Giữ nguyên project cũ"
                    ],
                    "allow_multiple": False,
                    "context": question_context
                }
            )

        logger.info(f"[confirm_replace] Asked user to confirm replacing '{existing_title}'")

        return {
            **state,
            "action": "CONFIRM_REPLACE",
            "waiting_for_answer": True
        }
    except Exception as e:
        logger.error(f"[confirm_replace] Error: {e}", exc_info=True)
        if agent:
            await agent.message_user("response", "Có lỗi xảy ra, vui lòng thử lại.")
        return {**state, "action": "RESPOND"}


async def confirm_existing(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Ask user what to do when project with same domain already exists."""
    try:
        existing_title = state.get("existing_prd_title", "project hiện tại")
        stories_count = state.get("existing_stories_count", 0)

        stories_info = f" với {stories_count} user stories" if stories_count > 0 else ""
        question = (
            f"Bạn đã có project '{existing_title}'{stories_info}. "
            f"Bạn muốn làm gì?"
        )

        if agent:
            # IMPORTANT: Include attachments in context so they can be passed to BA after confirmation
            # Note: use "or []" because attachments may be None
            attachments = state.get("attachments") or []
            question_context = {
                "original_user_message": state.get("user_message", ""),
                "existing_prd_title": existing_title,
                "existing_stories_count": stories_count,
                "attachments": attachments
            }

            logger.info(f"[confirm_existing] Saving context with {len(attachments)} attachment(s)")

            await agent.message_user(
                "question",
                question,
                question_config={
                    "question_type": "multichoice",
                    "options": [
                        "Xem PRD và Stories hiện tại",
                        "Cập nhật/Thêm feature mới",
                        "Tạo lại từ đầu"
                    ],
                    "allow_multiple": False,
                    "context": question_context
                }
            )

        logger.info(f"[confirm_existing] Asked user what to do with existing project '{existing_title}'")

        return {
            **state,
            "action": "CONFIRM_EXISTING",
            "waiting_for_answer": True
        }
    except Exception as e:
        logger.error(f"[confirm_existing] Error: {e}", exc_info=True)
        if agent:
            await agent.message_user("response", "Có lỗi xảy ra, vui lòng thử lại.")
        return {**state, "action": "RESPOND"}
