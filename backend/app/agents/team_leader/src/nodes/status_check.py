"""Status check node for checking board/project status using tools."""

import logging
from langchain.agents import create_agent

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.core.llm_factory import get_llm
from app.agents.core.prompt_utils import get_task_prompts
from app.agents.team_leader.src.nodes._utils import get_callback_config, _PROMPTS
from app.agents.team_leader.tools import get_team_leader_tools

logger = logging.getLogger(__name__)


async def status_check(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Check board status using tool-calling agent."""
    try:
        prompts = get_task_prompts(_PROMPTS, "status_check")
        
        status_agent = create_agent(
            model=get_llm("respond"),
            tools=get_team_leader_tools(),
            system_prompt=prompts["system_prompt"]
        )
        
        result = await status_agent.ainvoke(
            {"messages": [{"role": "user", "content": f"{state.get('user_message', '')}\n\nproject_id: {state.get('project_id', '')}"}]},
            config=get_callback_config(state, "status_check")
        )
        
        msg = result["messages"][-1].content
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "STATUS_CHECK"}
    except Exception as e:
        logger.error(f"[status_check] {e}")
        return {**state, "message": "", "action": "STATUS_CHECK"}
