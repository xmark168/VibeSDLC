"""Implement Tests node - Generate tests using LLM with tools."""

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.tools.filesystem_tools import get_filesystem_tools, set_tool_context
from app.agents.tester.src.tools.skill_tools import (
    get_skill_tools,
    reset_skill_cache,
    set_skill_context,
)

logger = logging.getLogger(__name__)

# Thread pool for parallel tool execution (I/O bound operations)
_tool_executor = ThreadPoolExecutor(max_workers=6)


async def _execute_tool_async(tool, tool_args: dict) -> str:
    """Execute sync tool in thread pool for parallel execution."""
    loop = asyncio.get_event_loop()
    if hasattr(tool, "invoke"):
        return await loop.run_in_executor(_tool_executor, lambda: tool.invoke(tool_args))
    elif hasattr(tool, "func"):
        return await loop.run_in_executor(_tool_executor, lambda: tool.func(**tool_args))
    else:
        return await loop.run_in_executor(_tool_executor, lambda: tool(**tool_args))


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

        # Execute tool calls IN PARALLEL for better performance
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"[_execute_llm_with_tools] Executing {len(tool_names)} tools in parallel: {tool_names}")

        async def _run_single_tool(tc):
            """Execute a single tool call."""
            nonlocal explore_count
            tool_name = tc["name"]
            tool_args = tc["args"]

            # Count exploration tools
            if tool_name in explore_tools:
                explore_count += 1
                if explore_count > max_explore:
                    logger.warning(
                        f"[_execute_llm_with_tools] Too many explore calls ({explore_count})"
                    )
                    return ToolMessage(
                        content="STOP EXPLORING. You have searched enough. Now use write_file to create the test file using the skill template patterns.",
                        tool_call_id=tc["id"],
                    )

            if tool_name in tool_map:
                try:
                    result = await _execute_tool_async(tool_map[tool_name], tool_args)
                    logger.info(f"[tool] {tool_name} -> OK")
                    return ToolMessage(
                        content=str(result)[:4000], tool_call_id=tc["id"]
                    )
                except Exception as e:
                    logger.warning(f"[tool] {tool_name} -> Error: {e}")
                    return ToolMessage(
                        content=f"Error: {str(e)}", tool_call_id=tc["id"]
                    )
            else:
                return ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tc["id"],
                )

        # Run ALL tools in parallel using asyncio.gather
        tool_messages = await asyncio.gather(
            *[_run_single_tool(tc) for tc in response.tool_calls]
        )
        conversation.extend(tool_messages)

    logger.warning("[_execute_llm_with_tools] Max iterations reached")
    return conversation[-1].content if hasattr(conversation[-1], "content") else ""


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list) -> str:
    """Build pre-loaded dependencies context for the current step (MetaGPT-style)."""
    if not dependencies_content:
        return ""
    
    parts = []
    
    # Add step-specific dependencies first
    if step_dependencies:
        for dep_path in step_dependencies:
            if not isinstance(dep_path, str):
                continue
            if dep_path in dependencies_content:
                content = dependencies_content[dep_path]
                parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    # Add common test files if not already included
    common_files = ["jest.config.ts", "jest.setup.ts", "src/lib/prisma.ts"]
    for dep_path in common_files:
        if dep_path in dependencies_content and dep_path not in (step_dependencies or []):
            content = dependencies_content[dep_path]
            parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    if not parts:
        return ""
    
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


async def implement_tests(state: TesterState, agent=None) -> dict:
    """Implement tests using React Agent with skills (MetaGPT-style).

    This node:
    1. Gets current step from test_plan
    2. Resets review_count for fresh review attempts
    3. Uses pre-loaded dependencies from plan_tests
    4. Initializes skill registry
    5. Creates React Agent with filesystem + skill tools
    6. Executes step (activate_skill -> write_file)

    Output:
    - current_step: NOT incremented (review node handles this on LGTM)
    - review_count: Reset to 0 for fresh review
    - files_created/files_modified: updated lists
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement_tests - step {current_step + 1}/{total_steps}")
    
    # Keep review_count from state (don't reset - review node manages it)
    # review_count is incremented in review node on LBTM, reset on LGTM (step advance)

    test_plan = state.get("test_plan", [])
    project_id = state.get("project_id", "")
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    tech_stack = state.get("tech_stack", "nextjs")
    testing_context = state.get("testing_context", {})

    # Set tool context so tools use workspace_path (worktree) instead of project_path
    set_tool_context(project_id=project_id, workspace_path=workspace_path)
    logger.info(f"[implement_tests] Set tool context: workspace_path={workspace_path}")

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

    # Build pre-loaded dependencies context (MetaGPT-style)
    dependencies_content = state.get("dependencies_content", {})
    step_dependencies = step.get("dependencies", [])
    deps_context = _build_dependencies_context(dependencies_content, step_dependencies)
    if deps_context:
        logger.info(f"[implement_tests] Using {len(step_dependencies)} pre-loaded dependencies")

    # Include feedback from previous review (if LBTM)
    feedback_section = ""
    if state.get("review_feedback"):
        feedback_section = f"\n<feedback>\n{state.get('review_feedback')}\n</feedback>"

    # Build system prompt
    system_prompt = get_system_prompt("implement_tests", skill_catalog=skill_catalog)

    # Build user prompt with pre-loaded context
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
    
    # Append pre-loaded context and feedback
    if deps_context:
        user_prompt += f"\n\n## Pre-loaded Context\n{deps_context}"
    if feedback_section:
        user_prompt += f"\n\n## Previous Review Feedback{feedback_section}"

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

        # NOTE: Don't increment current_step here!
        # current_step is incremented in review node ONLY when LGTM
        # This ensures LBTM re-implements the SAME step
        # NOTE: Don't return review_count - let review node manage it
        return {
            "current_step": current_step,  # Keep same step until review LGTM
            "files_created": files_created,
            "files_modified": files_modified,
            "last_implemented_file": file_path,  # Track for review
            "message": msg,
            "action": "REVIEW",  # Go to review (MetaGPT-style)
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
