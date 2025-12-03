"""Implement Tests node - Generate tests using LLM with tools."""

import json
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.tools.filesystem_tools import get_filesystem_tools
from app.agents.tester.src.tools.skill_tools import (
    get_skill_tools,
    reset_skill_cache,
    set_skill_context,
)

logger = logging.getLogger(__name__)

# Use custom API endpoint if configured
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = (
    ChatOpenAI(
        model=_model,
        temperature=0,
        api_key=_api_key,
        base_url=_base_url,
    )
    if _base_url
    else ChatOpenAI(model=_model, temperature=0)
)


async def _execute_llm_with_tools(
    llm: ChatOpenAI,
    tools: list,
    messages: list,
    state: dict,
    name: str,
    max_iterations: int = 10,
) -> str:
    """Execute LLM with ReAct tool calling pattern."""
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}
    conversation = list(messages)

    handler = state.get("langfuse_handler")
    config = (
        {"callbacks": [handler], "run_name": name} if handler else {"run_name": name}
    )

    # Track exploration tool calls to prevent infinite loops
    explore_tools = {"list_directory", "glob_files", "grep_files"}
    explore_count = 0
    max_explore = 4

    for i in range(max_iterations):
        response = await llm_with_tools.ainvoke(conversation, config=config)
        conversation.append(response)

        if not response.tool_calls:
            logger.info(f"[_execute_llm_with_tools] Completed after {i + 1} iterations")
            return response.content or ""

        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Count exploration tools
            if tool_name in explore_tools:
                explore_count += 1
                if explore_count > max_explore:
                    logger.warning(
                        f"[_execute_llm_with_tools] Too many explore calls ({explore_count})"
                    )
                    conversation.append(
                        ToolMessage(
                            content="STOP EXPLORING. You have searched enough. Now use write_file to create the test file using the skill template patterns.",
                            tool_call_id=tool_call["id"],
                        )
                    )
                    continue

            if tool_name in tool_map:
                try:
                    tool = tool_map[tool_name]
                    if hasattr(tool, "invoke"):
                        result = tool.invoke(tool_args)
                    elif hasattr(tool, "func"):
                        result = tool.func(**tool_args)
                    else:
                        result = tool(**tool_args)

                    conversation.append(
                        ToolMessage(
                            content=str(result)[:4000], tool_call_id=tool_call["id"]
                        )
                    )
                    logger.info(f"[tool] {tool_name} -> OK")
                except Exception as e:
                    conversation.append(
                        ToolMessage(
                            content=f"Error: {str(e)}", tool_call_id=tool_call["id"]
                        )
                    )
                    logger.warning(f"[tool] {tool_name} -> Error: {e}")
            else:
                conversation.append(
                    ToolMessage(
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tool_call["id"],
                    )
                )

    logger.warning("[_execute_llm_with_tools] Max iterations reached")
    return conversation[-1].content if hasattr(conversation[-1], "content") else ""


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


async def implement_tests(state: TesterState, agent=None) -> dict:
    """Implement tests using React Agent with skills.

    This node:
    1. Gets current step from test_plan
    2. Initializes skill registry
    3. Creates React Agent with filesystem + skill tools
    4. Executes step (activate_skill -> write_file)

    Output:
    - current_step: incremented
    - files_created/files_modified: updated lists
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement_tests - step {current_step + 1}/{total_steps}")

    test_plan = state.get("test_plan", [])
    project_id = state.get("project_id", "")
    tech_stack = state.get("tech_stack", "nextjs")
    testing_context = state.get("testing_context", {})

    # Check if all steps done
    if current_step >= total_steps or current_step >= len(test_plan):
        logger.info("[implement_tests] All steps completed")
        return {
            "message": "Hoàn thành tất cả steps.",
            "action": "RUN",
        }

    # Get current step
    step = test_plan[current_step]
    test_type = step.get("type", "integration")
    file_path = step.get("file_path", "")
    story_title = step.get("story_title", "Unknown")
    description = step.get("description", "")
    scenarios = step.get("scenarios", [])

    # Reset skill cache for each step
    reset_skill_cache()

    # Initialize skill registry
    skill_registry = SkillRegistry.load(tech_stack)
    set_skill_context(skill_registry)

    # Combine tools
    tools = get_filesystem_tools() + get_skill_tools()

    # Get skill catalog for prompt
    skill_catalog = skill_registry.get_skill_catalog_for_prompt()

    # Format testing context
    testing_context_str = ""
    if testing_context:
        testing_context_str = json.dumps(testing_context, indent=2, ensure_ascii=False)

    # Format scenarios
    scenarios_str = "\n".join(f"- {s}" for s in scenarios) if scenarios else "N/A"

    # Build system prompt
    system_prompt = get_system_prompt("implement_tests", skill_catalog=skill_catalog)

    # Build user prompt
    user_prompt = get_user_prompt(
        "implement_tests",
        step_number=current_step + 1,
        total_steps=total_steps,
        test_type=test_type,
        file_path=file_path,
        story_title=story_title,
        description=description,
        scenarios=scenarios_str,
        files_modified=", ".join(state.get("files_modified", [])) or "None",
        testing_context=testing_context_str or "N/A",
        project_id=project_id,
    )

    try:
        # Build messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Execute with tools
        logger.info(f"[implement_tests] Step {current_step + 1}: {description[:50]}...")

        last_message = await _execute_llm_with_tools(
            llm=_llm,
            tools=tools,
            messages=messages,
            state=state,
            name=f"implement_tests_step_{current_step + 1}",
            max_iterations=15,
        )

        # Track files
        files_created = state.get("files_created", []).copy()
        files_modified = state.get("files_modified", []).copy()

        if file_path and file_path not in files_created:
            files_created.append(file_path)

        # Update progress message
        msg = f"✅ Step {current_step + 1}/{total_steps}: {description}"
        if agent:
            await agent.message_user("response", msg)

        logger.info(f"[implement_tests] Completed step {current_step + 1}")

        # Determine next action
        next_step = current_step + 1
        next_action = "IMPLEMENT" if next_step < total_steps else "RUN"

        return {
            "current_step": next_step,
            "files_created": files_created,
            "files_modified": files_modified,
            "message": msg,
            "action": next_action,
        }

    except Exception as e:
        logger.error(f"[implement_tests] Error: {e}", exc_info=True)
        error_msg = f"Lỗi khi implement step {current_step + 1}: {str(e)}"
        if agent:
            await agent.message_user("response", error_msg)
        return {
            "error": str(e),
            "message": error_msg,
            "action": "RESPOND",
        }
