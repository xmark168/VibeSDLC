"""Conversation nodes - test_status and general Q&A."""

import logging

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt
from app.agents.tester.src.nodes.helpers import get_llm_config, send_message
from app.agents.core.llm_factory import get_llm

logger = logging.getLogger(__name__)

_chat_llm = get_llm("default")


async def test_status(state: TesterState, agent=None) -> dict:
    """Report test status using tools."""
    try:
        from langgraph.prebuilt import create_react_agent
        from app.agents.tester.src.tools import get_tester_tools

        tools = get_tester_tools()
        react_agent = create_react_agent(_chat_llm, tools)

        system_msg = get_system_prompt("conversation")
        user_msg = f"{state.get('user_message', 'test status')}\n\nproject_id: {state.get('project_id', '')}"

        result = await react_agent.ainvoke(
            {"messages": [("system", system_msg), ("user", user_msg)]},
            config=get_llm_config(state, "test_status"),
        )

        msg = result["messages"][-1].content
        await send_message(state, agent, msg)

        return {"message": msg, "result": {"action": "test_status"}}
    except Exception as e:
        logger.error(f"[test_status] {e}")
        msg = f"Lỗi khi kiểm tra test status: {e}"
        await send_message(state, agent, msg, "error")
        return {"message": msg, "error": str(e)}


async def conversation(state: TesterState, agent=None) -> dict:
    """Handle conversation about testing using tools."""
    try:
        from langgraph.prebuilt import create_react_agent
        from app.agents.tester.src.tools import get_tester_tools

        tools = get_tester_tools()
        react_agent = create_react_agent(_chat_llm, tools)

        system_msg = get_system_prompt("conversation")
        user_msg = f"{state.get('user_message', '')}\n\nproject_id: {state.get('project_id', '')}"

        result = await react_agent.ainvoke(
            {"messages": [("system", system_msg), ("user", user_msg)]},
            config=get_llm_config(state, "conversation"),
        )

        msg = result["messages"][-1].content
        await send_message(state, agent, msg)

        return {"message": msg, "result": {"action": "conversation"}}
    except Exception as e:
        logger.error(f"[conversation] {e}")
        msg = f"Xin lỗi, có lỗi xảy ra: {e}"
        await send_message(state, agent, msg, "error")
        return {"message": msg, "error": str(e)}
