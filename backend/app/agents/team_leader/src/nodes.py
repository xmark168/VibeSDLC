"""Team Leader graph nodes."""

import logging
import os
import re
from pathlib import Path
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.core.prompt_utils import (
    build_system_prompt as _build_system_prompt,
)
from app.agents.core.prompt_utils import (
    build_user_prompt as _build_user_prompt,
)
from app.agents.core.prompt_utils import (
    get_task_prompts as _get_task_prompts,
)
from app.agents.core.prompt_utils import (
    load_prompts_yaml,
)
from app.agents.team_leader.src.schemas import ExtractedPreferences, RoutingDecision
from app.agents.team_leader.src.state import TeamLeaderState
from app.core.config import settings

logger = logging.getLogger(__name__)

_PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")
_DEFAULTS = {"name": "Team Leader", "role": "Team Leader & Project Coordinator", "personality": "Professional and helpful"}

# LLM config - uses Anthropic API from settings
_base_url = settings.ANTHROPIC_API_BASE or os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
_api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
_model = os.getenv("TEAM_LEADER_MODEL", "claude-sonnet-4-5-20250929")

_llm_kwargs = {
    "model": _model,
    "max_tokens": 8192,
    "max_retries": 3,
    "base_url": _base_url,
    "api_key": _api_key,
}

_fast_llm = ChatAnthropic(**_llm_kwargs, temperature=0.1, timeout=60)
_chat_llm = ChatAnthropic(**_llm_kwargs, temperature=0.3, timeout=90)

ROLE_WIP_MAP = {"developer": "InProgress", "tester": "Review", "business_analyst": None}

# Patterns to detect specialist task completion - must be specific completion messages
# Format: (role, [(pattern, is_completion_message)])
SPECIALIST_COMPLETION_PATTERNS = {
    "business_analyst": [
        "đã thêm",  # "Đã thêm X User Stories vào backlog"
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


def _detect_specialist_completion(conversation_history: str) -> str | None:
    """Detect if a specialist JUST completed a task (check LAST assistant message only).
    
    Conversation history format from ProjectContext.format_memory():
    ```
    ## Gần đây:
    User: message
    Assistant: message
    ```
    
    Returns:
        specialist_role if detected, None otherwise
    """
    if not conversation_history:
        return None

    # Parse conversation to get LAST Assistant message only
    lines = conversation_history.strip().split('\n')

    # Find last Assistant message (format: "Assistant: message")
    last_assistant_msg = None
    for line in reversed(lines):
        line_stripped = line.strip()
        # Match "Assistant: ..." format from format_memory()
        if line_stripped.startswith('Assistant:'):
            last_assistant_msg = line_stripped[len('Assistant:'):].strip()
            break

    if not last_assistant_msg:
        return None

    last_msg_lower = last_assistant_msg.lower()

    # Check each role's completion patterns
    for role, patterns in SPECIALIST_COMPLETION_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in last_msg_lower:
                return role

    return None


def _clean_json(text: str) -> str:
    """Strip markdown code blocks from LLM response."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    return match.group(1).strip() if match else text.strip()


def _cfg(state: dict, name: str) -> dict | None:
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else None


def _prompts(task: str = "routing_decision") -> dict:
    return _get_task_prompts(_PROMPTS, task)


def _sys_prompt(agent, task: str = "routing_decision") -> str:
    return _build_system_prompt(_PROMPTS, task, agent, _DEFAULTS)


def _user_prompt(msg: str, task: str = "routing_decision", **kw) -> str:
    return _build_user_prompt(_PROMPTS, task, msg, **kw)


# Fallback messages when LLM fails
_FALLBACK_MESSAGES = {
    "replace": "Đã thay thế project cũ, xóa dữ liệu liên quan và chuyển cho BA phân tích yêu cầu mới nhé! 📋",
    "keep": "OK, giữ nguyên project hiện tại nhé! 😊",
    "view": "Đây là thông tin project của bạn! 📄",
    "update": "Đã ghi nhận yêu cầu cập nhật và chuyển cho BA xử lý nhé! 📝",
    "default": "Đã nhận yêu cầu của bạn! 👍",
}


async def generate_response_message(action: str, context: str, extra_info: str = "", agent=None) -> str:
    """Generate natural response message using LLM.
    
    Args:
        action: The action that was performed (replace, keep, view, update)
        context: Description of the situation
        extra_info: Additional context info
        agent: Agent instance for prompt building
        
    Returns:
        Generated message string
    """
    # Skip LLM for simple "keep" action - use static message for instant response
    # Note: "view" still uses LLM because it has extra_info with PRD title/story count
    if action == "keep":
        logger.info("[generate_response_message] Using static message for action='keep' (no LLM needed)")
        return _FALLBACK_MESSAGES["keep"]

    try:
        sys_prompt = _sys_prompt(agent, "response_generation")
        user_prompt = _user_prompt(
            "",  # Not used for this task
            task="response_generation",
            action=action,
            context=context,
            extra_info=extra_info or "N/A"
        )

        response = await _chat_llm.ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)]
        )
        return response.content.strip()
    except Exception as e:
        logger.warning(f"[generate_response_message] LLM failed: {e}, using fallback")
        return _FALLBACK_MESSAGES.get(action, _FALLBACK_MESSAGES["default"])


async def extract_preferences(state: TeamLeaderState, agent=None) -> dict:
    """Extract and save user preferences. Returns empty dict (no state update)."""
    msg = state.get("user_message", "")
    if len(msg.strip()) < 10:
        return {}
    try:
        prompts = _prompts("preference_extraction")
        response = await _fast_llm.ainvoke(
            [SystemMessage(content=prompts["system_prompt"]), HumanMessage(content=f'Analyze: "{msg}"')],
            config=_cfg(state, "extract_preferences")
        )
        clean_json = _clean_json(response.content)
        result = ExtractedPreferences.model_validate_json(clean_json)
        detected = {k: v for k, v in result.model_dump().items() if v and k != "additional"}
        if result.additional:
            detected.update(result.additional)
        if detected and agent:
            for k, v in detected.items():
                await agent.update_preference(k, v)
    except Exception as e:
        logger.debug(f"[extract_preferences] {e}")
    return {}


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

        response = await _fast_llm.ainvoke(
            [HumanMessage(content=prompt)],
            config=_cfg(state, "check_domain_change")
        )
        answer = response.content.strip().upper()
        return "DIFFERENT" in answer
    except Exception as e:
        logger.error(f"[_check_domain_change] Error: {e}")
        return False


async def router(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Route request using structured LLM output."""
    try:
        # Get actual board state
        board_state = ""
        if agent and hasattr(agent, 'context'):
            try:
                _, _, wip = agent.context.get_kanban_context()
                board_state = f"WIP: InProgress={wip.get('InProgress', '?')}, Review={wip.get('Review', '?')}"
            except Exception:
                pass

        # Build user message with attachment info for routing
        user_message = state["user_message"]
        if state.get("attachments"):
            files = [att.get("filename", "file") for att in state["attachments"]]
            user_message = f"{user_message}\n[Đính kèm: {', '.join(files)}]"
            logger.info(f"[router] Message includes {len(files)} attachment(s): {files}")

        messages = [
            SystemMessage(content=_sys_prompt(agent)),
            HumanMessage(content=_user_prompt(
                user_message,
                name=agent.name if agent else "Team Leader",
                conversation_history=state.get("conversation_history", ""),
                user_preferences=state.get("user_preferences", ""),
                board_state=board_state,
            ))
        ]

        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "router"))
        clean_json = _clean_json(response.content)
        decision = RoutingDecision.model_validate_json(clean_json)
        logger.info(f"[router] Decision: action={decision.action}, target={decision.target_role}")
        result = decision.model_dump()

        if result["action"] == "DELEGATE":
            wip_col = ROLE_WIP_MAP.get(result.get("target_role"))
            if wip_col and agent and hasattr(agent, 'context'):
                _, _, wip_available = agent.context.get_kanban_context()
                if wip_available.get(wip_col, 1) <= 0:
                    return {**state, "action": "RESPOND", "wip_blocked": True,
                            "message": f"Hiện tại {wip_col} đang full. Cần đợi stories hoàn thành.", "confidence": 0.95}

            # Check for domain change when delegating to BA (only if no attachments)
            if result.get("target_role") == "business_analyst" and agent:
                # IMPORTANT: If user uploaded a file (attachment), skip domain check
                # "Phân tích tài liệu" should UPDATE existing PRD, not trigger replacement
                has_attachments = bool(state.get("attachments"))

                if has_attachments:
                    logger.info(
                        "[router] User uploaded file(s), skipping domain check. "
                        "Will delegate to BA for document analysis/update."
                    )
                    # Skip domain check - just delegate to BA
                    # BA will analyze document and update existing PRD
                else:
                    # No attachments - proceed with normal domain check
                    try:
                        from sqlmodel import Session

                        from app.core.db import engine
                        from app.models import ArtifactType, Epic, Story
                        from app.services.artifact_service import ArtifactService

                        project_id = UUID(state["project_id"])

                        with Session(engine) as session:
                            artifact_service = ArtifactService(session)
                            existing_prd = artifact_service.get_latest_version(
                                project_id=project_id,
                                artifact_type=ArtifactType.PRD
                            )

                            if existing_prd:
                                # Check if there are any previous user messages
                                # If no messages (project was reset), skip domain check and auto-replace
                                from sqlmodel import select

                                from app.models import Message

                                message_count = len(session.exec(
                                    select(Message).where(
                                        Message.project_id == project_id,
                                        Message.author_type == "user"
                                    )
                                ).all())

                                # If only 1 message (current one) or no messages, skip domain check
                                # This handles the case where user cleared messages via API
                                if message_count <= 1:
                                    logger.info(
                                        f"[router] No previous messages found, skipping domain check. "
                                        f"Will auto-replace old PRD '{existing_prd.title}'"
                                    )
                                    # Auto-delete old data and proceed
                                    from app.services.artifact_service import (
                                        ArtifactService,
                                    )
                                    artifact_service.delete_by_type(project_id, ArtifactType.PRD)
                                    artifact_service.delete_by_type(project_id, ArtifactType.USER_STORIES)

                                    # Delete epics and stories
                                    epics = session.exec(select(Epic).where(Epic.project_id == project_id)).all()
                                    for epic in epics:
                                        session.delete(epic)
                                    stories = session.exec(select(Story).where(Story.project_id == project_id)).all()
                                    for story in stories:
                                        session.delete(story)
                                    session.commit()

                                    # Archive docs if available
                                    if agent and hasattr(agent, 'project_files') and agent.project_files:
                                        await agent.project_files.archive_docs()

                                    # Continue with normal delegation (no confirmation needed)
                                else:
                                    # Check if domains are different
                                    is_different = await _check_domain_change(
                                        state["user_message"],
                                        existing_prd.title,
                                        state
                                    )

                                    # Count existing stories
                                    stories_count = session.exec(
                                        select(Story).where(Story.project_id == project_id)
                                    ).all()

                                    if is_different:
                                        # Different domain → ask to replace
                                        logger.info(
                                            f"[router] Domain change detected: '{existing_prd.title}' → new request. "
                                            f"Asking for confirmation."
                                        )

                                        return {
                                            **state,
                                            "action": "CONFIRM_REPLACE",
                                            "existing_prd_title": existing_prd.title,
                                            "existing_stories_count": len(stories_count),
                                            "needs_replace_confirm": True,
                                            "wip_blocked": False
                                        }
                                    else:
                                        # Same domain - check if user explicitly wants to UPDATE
                                        is_update_request = result.get("is_update_request", False)
                                        
                                        # DEBUG: Log LLM decision for diagnosis
                                        logger.info(f"[router] LLM decision: is_update_request={is_update_request}, user_message='{state['user_message']}'")
                                        
                                        if is_update_request:
                                            # User explicitly wants to update/edit something
                                            # Skip CONFIRM_EXISTING and delegate directly to BA
                                            logger.info(
                                                f"[router] Same domain with explicit UPDATE request. "
                                                f"Delegating directly to BA without confirmation."
                                            )
                                            # Continue to normal delegation (don't return here)
                                        else:
                                            # Vague request on same domain → ask what to do
                                            logger.info(
                                                f"[router] Same domain detected: '{existing_prd.title}'. "
                                                f"Asking user what to do with existing project."
                                            )

                                            return {
                                                **state,
                                                "action": "CONFIRM_EXISTING",
                                                "existing_prd_title": existing_prd.title,
                                                "existing_stories_count": len(stories_count),
                                                "wip_blocked": False
                                            }
                    except Exception as e:
                        logger.error(f"[router] Error checking domain change: {e}", exc_info=True)

        return {**state, **result, "wip_blocked": False}
    except Exception as e:
        logger.error(f"[router] {e}", exc_info=True)
        return {**state, "action": "RESPOND", "message": "Xin lỗi, có lỗi xảy ra.", "confidence": 0.0, "wip_blocked": False}


async def delegate(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Delegate task to specialist agent."""
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType

        msg = state.get("message") or f"Chuyển cho @{state['target_role']} nhé!"
        await agent.message_user("response", msg)

        # Build context with attachments and conversation history
        task_context = {}
        if state.get("attachments"):
            task_context["attachments"] = state["attachments"]
            logger.info(f"[delegate] Passing {len(state['attachments'])} attachment(s) to {state['target_role']}")
        
        # Pass conversation history to specialist agent for context
        if state.get("conversation_history"):
            task_context["conversation_history"] = state["conversation_history"]
            logger.info(f"[delegate] Passing conversation history ({len(state['conversation_history'])} chars) to {state['target_role']}")

        task = TaskContext(
            task_id=UUID(state["task_id"]), task_type=AgentTaskType.MESSAGE, priority="high",
            routing_reason=state.get("reason", "team_leader_routing"),
            user_id=UUID(state["user_id"]) if state.get("user_id") else None,
            project_id=UUID(state["project_id"]), content=state["user_message"],
            context=task_context,
        )
        await agent.delegate_to_role(task=task, target_role=state["target_role"], delegation_message=msg)
    return {**state, "action": "DELEGATE"}


async def respond(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Send direct response to user."""
    msg = state.get("message", "Mình có thể giúp gì?")
    if agent:
        await agent.message_user("response", msg)
    return {**state, "action": "RESPOND"}


async def clarify(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Ask clarification question using LLM with persona."""
    try:
        reason = state.get("reason", "need more details")
        hint = state.get("clarification_question", "")

        sys_prompt = _sys_prompt(agent, "conversational")
        user_prompt = f"""User vừa nói: "{state['user_message']}"

Mình cần hỏi clarification vì: {reason}
{f'Gợi ý câu hỏi: {hint}' if hint else ''}

Hãy viết MỘT câu hỏi clarification thân thiện, tự nhiên để hiểu rõ hơn user muốn gì.
- Giải thích ngắn gọn tại sao cần thêm info
- Gợi ý cụ thể user cần cung cấp gì (feature name, error message, steps...)
- Dùng emoji phù hợp"""

        response = await _chat_llm.ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)],
            config=_cfg(state, "clarify")
        )
        question = response.content
    except Exception as e:
        logger.error(f"[clarify] LLM error: {e}")
        question = state.get("message") or "Hmm, mình cần biết rõ hơn chút! 🤔 Bạn có thể mô tả chi tiết hơn không?"

    if agent:
        await agent.message_user("response", question)
    return {**state, "message": question, "action": "CLARIFY"}


async def conversational(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Generate conversational response."""
    try:
        conversation_history = state.get("conversation_history", "")

        # Detect if specialist just completed a task
        specialist_role = _detect_specialist_completion(conversation_history)

        # Build context for LLM
        sys_prompt = _sys_prompt(agent, "conversational")

        # Add specialist completion context if detected
        specialist_context = ""
        if specialist_role:
            role_names = {
                "business_analyst": "Business Analyst",
                "developer": "Developer",
                "tester": "Tester"
            }
            role_display = role_names.get(specialist_role, specialist_role)
            specialist_context = f"""
**LƯU Ý QUAN TRỌNG:** {role_display} vừa hoàn thành task. Bạn đang tiếp quản cuộc hội thoại.
- Hãy chào đón user trở lại một cách tự nhiên
- Có thể hỏi user cần gì tiếp theo
- Đừng lặp lại những gì {role_display} đã nói"""

        if conversation_history:
            sys_prompt += f"""

---

**Cuộc trò chuyện gần đây:**
{conversation_history}
{specialist_context}

**Lưu ý:** Dựa vào context trên để trả lời tự nhiên và liên quan. Đừng lặp lại những gì đã nói."""

        response = await _chat_llm.ainvoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=state["user_message"])],
            config=_cfg(state, "conversational")
        )
        if agent:
            await agent.message_user("response", response.content)
        return {**state, "message": response.content, "action": "CONVERSATION"}
    except Exception as e:
        logger.error(f"[conversational] {e}")
        msg = "Hmm, có gì đó không ổn. Bạn thử lại được không? 😅"
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "CONVERSATION"}


async def status_check(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Check board status using tool-calling agent."""
    try:
        from langchain.agents import create_agent

        from app.agents.team_leader.tools import get_team_leader_tools

        status_agent = create_agent(model=_chat_llm, tools=get_team_leader_tools(), system_prompt=_sys_prompt(agent, "status_check"))
        result = await status_agent.ainvoke(
            {"messages": [{"role": "user", "content": f"{state.get('user_message', '')}\n\nproject_id: {state.get('project_id', '')}"}]},
            config=_cfg(state, "status_check")
        )
        msg = result["messages"][-1].content
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "STATUS_CHECK"}
    except Exception as e:
        logger.error(f"[status_check] {e}")
        return {**state, "message": "", "action": "STATUS_CHECK"}


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


async def check_cancel_intent(user_message: str, agent=None) -> bool:
    """Check if user wants to cancel an action using LLM.
    
    Args:
        user_message: The user's response
        agent: Optional agent for logging
        
    Returns:
        True if user wants to cancel, False if they want to proceed
    """
    try:
        prompts = _get_task_prompts(_PROMPTS, "cancel_intent_check")
        system_prompt = prompts["system_prompt"]
        user_prompt = prompts["user_prompt"].replace("{user_message}", user_message)

        response = await _fast_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        result = response.content.strip().upper()
        is_cancel = "CANCEL" in result

        agent_name = agent.name if agent else "TeamLeader"
        logger.info(f"[{agent_name}] Cancel intent check: '{user_message[:50]}...' -> {result} (is_cancel={is_cancel})")

        return is_cancel

    except Exception as e:
        logger.error(f"[check_cancel_intent] Error: {e}")
        return False


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
