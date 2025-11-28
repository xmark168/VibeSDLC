"""Team Leader graph nodes."""

import logging
import re
from pathlib import Path
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.schemas import ExtractedPreferences, RoutingDecision
from app.agents.core.prompt_utils import (
    load_prompts_yaml, get_task_prompts as _get_task_prompts,
    build_system_prompt as _build_system_prompt, build_user_prompt as _build_user_prompt,
)

logger = logging.getLogger(__name__)

_PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")
_DEFAULTS = {"name": "Team Leader", "role": "Team Leader & Project Coordinator", "personality": "Professional and helpful"}
_fast_llm = ChatOpenAI(model="claude-haiku-4-5-20251001", temperature=0.1, timeout=15)
_chat_llm = ChatOpenAI(model="claude-haiku-4-5-20251001", temperature=0.7, timeout=30)

ROLE_WIP_MAP = {"developer": "InProgress", "tester": "Review", "business_analyst": None}


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
        
        messages = [
            SystemMessage(content=_sys_prompt(agent)),
            HumanMessage(content=_user_prompt(
                state["user_message"],
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
        
        task = TaskContext(
            task_id=UUID(state["task_id"]), task_type=AgentTaskType.MESSAGE, priority="high",
            routing_reason=state.get("reason", "team_leader_routing"),
            user_id=UUID(state["user_id"]) if state.get("user_id") else None,
            project_id=UUID(state["project_id"]), content=state["user_message"],
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
        sys_prompt = _sys_prompt(agent, "conversational")
        if state.get("conversation_history"):
            sys_prompt += f"""

---

**Cuộc trò chuyện gần đây:**
{state['conversation_history']}

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
