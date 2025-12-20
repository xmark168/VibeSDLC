"""Delegate node for Team Leader."""

import logging
from uuid import UUID

from app.agents.team_leader.src.state import TeamLeaderState

logger = logging.getLogger(__name__)


async def delegate(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Delegate task to specialist agent."""
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType

        msg = state.get("message") or f"Chuyển cho @{state['target_role']} nhé!"
        await agent.message_user("response", msg)

        task_context = {}
        if state.get("attachments"):
            task_context["attachments"] = state["attachments"]
            logger.info(f"[delegate] Passing {len(state['attachments'])} attachment(s) to {state['target_role']}")

        if state.get("conversation_history"):
            task_context["conversation_history"] = state["conversation_history"]
            logger.info(f"[delegate] Passing conversation history to {state['target_role']}")

        task = TaskContext(
            task_id=UUID(state["task_id"]),
            task_type=AgentTaskType.MESSAGE,
            priority="high",
            routing_reason=state.get("reason", "team_leader_routing"),
            user_id=UUID(state["user_id"]) if state.get("user_id") else None,
            project_id=UUID(state["project_id"]),
            content=state["user_message"],
            context=task_context,
        )
        await agent.delegate_to_role(
            task=task,
            target_role=state["target_role"],
            delegation_message=msg
        )

    return {**state, "action": "DELEGATE"}
