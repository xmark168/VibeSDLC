"""Utility functions for Team Leader nodes."""

import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agent.llm_factory import get_llm
from app.core.agent.prompt_utils import build_system_prompt, build_user_prompt, get_task_prompts, load_prompts_yaml

logger = logging.getLogger(__name__)

# Load prompts and defaults for Team Leader
_PROMPTS = load_prompts_yaml(Path(__file__).parent.parent / "prompts.yaml")
_DEFAULTS = {
    "name": "Team Leader",
    "role": "Team Leader & Project Coordinator",
    "personality": "Professional and helpful"
}

ROLE_WIP_MAP = {
    "developer": "InProgress",
    "tester": "Review",
    "business_analyst": None
}

SPECIALIST_COMPLETION_PATTERNS = {
    "business_analyst": [
        "đã thêm",
        "stories vào backlog",
        "đã phê duyệt",
    ],
    "developer": [
        "implement xong",
        "code xong",
        "đã merge",
        "pull request đã được merge",
    ],
    "tester": [
        "test xong",
        "qa xong",
        "all tests passed",
        "đã test xong",
    ],
}

_FALLBACK_MESSAGES = {
    "replace": "Đã thay thế project cũ, xóa dữ liệu liên quan và chuyển cho BA phân tích yêu cầu mới nhé! 📋",
    "keep": "OK, giữ nguyên project hiện tại nhé! 😊",
    "view": "Đây là thông tin project của bạn! 📄",
    "update": "Đã ghi nhận yêu cầu cập nhật và chuyển cho BA xử lý nhé! 📝",
    "default": "Đã nhận yêu cầu của bạn! 👍",
}


def detect_specialist_completion(conversation_history: str) -> str | None:
    """Detect if a specialist JUST completed a task (check LAST assistant message only)."""
    if not conversation_history:
        return None

    lines = conversation_history.strip().split('\n')
    last_assistant_msg = None
    
    for line in reversed(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('Assistant:'):
            last_assistant_msg = line_stripped[len('Assistant:'):].strip()
            break

    if not last_assistant_msg:
        return None

    last_msg_lower = last_assistant_msg.lower()

    for role, patterns in SPECIALIST_COMPLETION_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in last_msg_lower:
                return role

    return None


async def generate_response_message(
    action: str,
    context: str,
    extra_info: str = "",
    agent=None
) -> str:
    """Generate natural response message using LLM."""
    if action == "keep":
        logger.info("[generate_response_message] Using static message for action='keep'")
        return _FALLBACK_MESSAGES["keep"]

    try:
        sys_prompt = build_system_prompt(_PROMPTS, "response_generation", agent, _DEFAULTS)
        user_prompt = build_user_prompt(
            _PROMPTS,
            "response_generation",
            "",
            action=action,
            context=context,
            extra_info=extra_info or "N/A"
        )

        response = await get_llm("respond").ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)]
        )
        return response.content.strip()
    except Exception as e:
        logger.warning(f"[generate_response_message] LLM failed: {e}, using fallback")
        return _FALLBACK_MESSAGES.get(action, _FALLBACK_MESSAGES["default"])


async def check_cancel_intent(user_message: str, agent=None) -> bool:
    """Check if user wants to cancel an action using LLM."""
    try:
        prompts = get_task_prompts(_PROMPTS, "cancel_intent_check")
        system_prompt = prompts["system_prompt"]
        user_prompt = prompts["user_prompt"].replace("{user_message}", user_message)

        response = await get_llm("router").ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        result = response.content.strip().upper()
        is_cancel = "CANCEL" in result

        agent_name = agent.name if agent else "TeamLeader"
        logger.info(f"[{agent_name}] Cancel intent check: '{user_message[:50]}...' -> {result}")

        return is_cancel
    except Exception as e:
        logger.error(f"[check_cancel_intent] Error: {e}")
        return False


def get_callback_config(state: dict, name: str) -> dict[str, Any] | None:
    """Get callback config for LangFuse tracing."""
    handler = state.get("langfuse_handler")
    return {"callbacks": [handler], "run_name": name} if handler else None
