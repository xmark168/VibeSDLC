"""
Execute Step Node - REFACTORED with Tool-First Approach

LLM được bind với tools và tự quyết định khi nào sử dụng read_file_tool, write_file_tool, grep_search_tool.
Không còn logic phức tạp để detect create vs modify - LLM tự chịu trách nhiệm.

Flow:
1. Loop qua steps trong plan
2. Với mỗi step, check có sub_steps hay không
3. Nếu có sub_steps: loop qua từng sub_step và call LLM
4. Nếu không có sub_steps: call LLM trực tiếp cho step
5. LLM nhận prompt + tools → tự implement
"""

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ..state import ImplementorState
from ..tool.filesystem_tools import (
    create_directory_tool,
    grep_search_tool,
    list_files_tool,
    read_file_tool,
    str_replace_tool,
    write_file_tool,
)
from ..utils.prompts import BACKEND_PROMPT, FRONTEND_PROMPT


def execute_step(state: ImplementorState) -> ImplementorState:
    """
    Execute ONE sub-step per invocation with tool-first approach.

    Uses state.current_step_index and state.current_sub_step_index to track progress.
    After executing one sub-step, increments indices and returns to routing logic.

    Args:
        state: ImplementorState with implementation plan and current indices

    Returns:
        Updated ImplementorState with execution results
    """
    print("\n" + "=" * 80)
    print("IMPLEMENTOR: EXECUTE STEP NODE (TOOL-FIRST APPROACH)")
    print("=" * 80)

    try:
        # Get plan steps
        plan = state.implementation_plan
        steps = plan.get("steps", [])

        if not steps:
            print("⚠️ No steps found in implementation plan")
            state.status = "error"
            state.error_message = "No steps in plan"
            return state

        # Check if all steps completed
        if state.current_step_index >= len(steps):
            print("✅ All steps already completed")
            state.current_phase = "run_tests"
            state.status = "execution_complete"
            return state

        # Get current step
        current_step = steps[state.current_step_index]
        step_number = state.current_step_index + 1
        total_steps = len(steps)

        print(f"📋 Total steps in plan: {total_steps}")
        print(f"📍 Current position: Step {step_number}/{total_steps}")
        print(f"\n{'=' * 80}")
        print(f"STEP {step_number}/{total_steps}: {current_step.get('title', 'N/A')}")
        print(f"Category: {current_step.get('category', 'backend')}")
        print(f"{'=' * 80}")

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.1,
            timeout=120,
        )

        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(
            [
                read_file_tool,
                write_file_tool,
                grep_search_tool,
                create_directory_tool,
                list_files_tool,
                str_replace_tool,
            ]
        )

        # Working directory
        working_dir = state.codebase_path or "."

        # Check if step has sub_steps
        sub_steps = current_step.get("sub_steps", [])

        if sub_steps:
            # Check if all sub-steps in current step completed
            if state.current_sub_step_index >= len(sub_steps):
                # All sub-steps completed, move to next step
                print(
                    f"✅ All {len(sub_steps)} sub-steps completed for Step {step_number}"
                )
                state.current_step_index += 1
                state.current_sub_step_index = 0

                # Check if that was the last step
                if state.current_step_index >= len(steps):
                    print("✅ All steps completed!")
                    state.current_phase = "run_tests"
                    state.status = "execution_complete"
                else:
                    print(f"📋 Moving to Step {state.current_step_index + 1}...")

                return state

            # Get current sub-step
            current_sub_step = sub_steps[state.current_sub_step_index]
            sub_step_number = state.current_sub_step_index + 1
            total_sub_steps = len(sub_steps)

            print(f"📝 Total sub-steps in this step: {total_sub_steps}")
            print(f"📍 Current sub-step: {sub_step_number}/{total_sub_steps}")
            print(
                f"\n  → Sub-step {sub_step_number}/{total_sub_steps}: {current_sub_step.get('title', 'N/A')}"
            )

            # Execute this ONE sub-step with LLM
            success = _execute_substep_with_llm(
                llm_with_tools=llm_with_tools,
                step=current_step,
                sub_step=current_sub_step,
                state=state,
                working_dir=working_dir,
                step_number=step_number,
                sub_step_number=sub_step_number,
                total_sub_steps=total_sub_steps,
            )

            if success:
                # Increment sub-step index for next iteration
                state.current_sub_step_index += 1
                print(f"  ✅ Sub-step {sub_step_number} completed")
                print(
                    f"  📍 Next iteration will be: Step {state.current_step_index + 1}, Sub-step {state.current_sub_step_index + 1}"
                )
            else:
                print(f"  ❌ Sub-step {sub_step_number} failed")
                state.status = "step_execution_failed"
                state.error_message = f"Sub-step {step_number}.{sub_step_number} failed"

        else:
            # No sub-steps, execute step directly
            print("📝 No sub-steps, executing step directly")

            success = _execute_step_with_llm(
                llm_with_tools=llm_with_tools,
                step=current_step,
                state=state,
                working_dir=working_dir,
            )

            if success:
                # Move to next step
                state.current_step_index += 1
                print(f"✅ Step {step_number} completed, moving to next")

                # Check if that was the last step
                if state.current_step_index >= len(steps):
                    print("✅ All steps completed!")
                    state.current_phase = "run_tests"
                    state.status = "execution_complete"
            else:
                print(f"❌ Step {step_number} failed")
                state.status = "step_execution_failed"
                state.error_message = f"Step {step_number} failed"

        # Progress summary
        print(
            f"\n📊 Progress: Step {state.current_step_index + 1}/{total_steps}, "
            f"Sub-step {state.current_sub_step_index + 1}"
        )
        print(f"📁 Files created so far: {len(state.files_created)}")
        print(f"📝 Files modified so far: {len(state.files_modified)}")

        return state

    except Exception as e:
        print(f"❌ Error in execute_step: {e}")
        import traceback

        traceback.print_exc()
        state.status = "error"
        state.error_message = f"Execute step failed: {str(e)}"
        return state


def _execute_substep_with_llm(
    llm_with_tools: Any,
    step: dict,
    sub_step: dict,
    state: ImplementorState,
    working_dir: str,
    step_number: int = 1,
    sub_step_number: int = 1,
    total_sub_steps: int = 1,
) -> bool:
    """
    Execute a single sub-step using LLM with tools.

    Args:
        llm_with_tools: LLM instance with tools bound
        step: Parent step dict
        sub_step: Sub-step dict to execute
        state: ImplementorState
        working_dir: Working directory
        step_number: Current step number (for display)
        sub_step_number: Current sub-step number (for display)
        total_sub_steps: Total sub-steps in current step (for display)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load AGENTS.md content
        category = step.get("category", "backend")
        print(f"    📂 Loading AGENTS.md for category: {category}")
        agents_md_content = _load_agents_md_content(
            state.codebase_path or ".", category
        )

        # Select prompt based on category
        if category == "frontend":
            prompt_template = FRONTEND_PROMPT
        else:
            prompt_template = BACKEND_PROMPT

        print(
            f"    📝 Selected prompt template: {'FRONTEND' if category == 'frontend' else 'BACKEND'}"
        )

        # Format prompt
        step_info = f"Step {step.get('step', 'N/A')}: {step.get('title', 'N/A')}\n{step.get('description', '')}"
        substep_info = f"Sub-step {sub_step.get('sub_step', 'N/A')}: {sub_step.get('title', 'N/A')}\n{sub_step.get('description', '')}"
        files_affected = (
            ", ".join(sub_step.get("files_affected", [])) or "Not specified"
        )

        print("    🔧 Formatting prompt with placeholders...")
        formatted_prompt = prompt_template.format(
            agent_md=agents_md_content or "No architecture guidelines available.",
            step_info=step_info,
            substep_info=substep_info,
            files_affected=files_affected,
        )
        print(
            f"    ✅ Prompt formatted successfully (length: {len(formatted_prompt)} chars)"
        )

        # Add working directory context
        formatted_prompt += f"\n\n**Working Directory:** {working_dir}\n"
        formatted_prompt += "**IMPORTANT:** All file paths in tool calls must be relative to the working directory.\n"

        # Add strict single sub-step enforcement
        formatted_prompt += f"\n\n{'=' * 80}\n"
        formatted_prompt += "🎯 **CRITICAL EXECUTION CONSTRAINT:**\n"
        formatted_prompt += f"{'=' * 80}\n"
        formatted_prompt += f"You are executing **ONLY Sub-step {sub_step_number}/{total_sub_steps}** of Step {step_number}.\n\n"
        formatted_prompt += "**STRICT RULES:**\n"
        formatted_prompt += f"1. ✅ ONLY implement what is described in Sub-step {sub_step.get('sub_step', 'N/A')}\n"
        formatted_prompt += "2. ❌ DO NOT create files for other sub-steps or steps\n"
        formatted_prompt += (
            "3. ❌ DO NOT implement functionality from future sub-steps\n"
        )
        formatted_prompt += (
            "4. ✅ Focus EXCLUSIVELY on the current sub-step's requirements\n"
        )
        formatted_prompt += "5. ✅ If this sub-step depends on files from previous sub-steps, use read_file_tool to check if they exist\n"
        formatted_prompt += "6. ❌ If dependent files don't exist yet, DO NOT create them - they will be created in their respective sub-steps\n\n"
        formatted_prompt += (
            f"**Current Sub-step Scope:** {sub_step.get('title', 'N/A')}\n"
        )
        formatted_prompt += f"**Description:** {sub_step.get('description', 'N/A')}\n"
        formatted_prompt += f"{'=' * 80}\n"

        print("    🤖 Calling LLM with tools...")

        # Call LLM with tool support
        messages = [HumanMessage(content=formatted_prompt)]
        response = llm_with_tools.invoke(messages)

        # Debug: Log LLM response
        print(f"    📝 LLM Response type: {type(response)}")
        if hasattr(response, "content"):
            content_preview = response.content[:500] if response.content else "(empty)"
            print(f"    📝 LLM Response content: {content_preview}")
        if hasattr(response, "tool_calls"):
            tool_count = len(response.tool_calls) if response.tool_calls else 0
            print(f"    📝 LLM Tool calls: {tool_count}")

        # Check if response has NEITHER content NOR tool calls (this is an error)
        has_content = (
            hasattr(response, "content")
            and response.content
            and response.content.strip()
        )
        has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls

        if not has_content and not has_tool_calls:
            raise Exception(
                "LLM returned empty response (no content and no tool calls)"
            )

        # Process tool calls if any
        tool_calls_made = _process_tool_calls(
            response=response,
            llm_with_tools=llm_with_tools,
            messages=messages,
            state=state,
            working_dir=working_dir,
        )

        if tool_calls_made:
            print(f"    ✅ Sub-step completed with {tool_calls_made} tool calls")
        else:
            print("    ⚠️ Sub-step completed without tool calls")

        return True

    except Exception as e:
        import traceback

        print(f"    ❌ Error executing sub-step: {e}")
        print(f"    📋 Error type: {type(e).__name__}")
        print("    📋 Full traceback:")
        traceback.print_exc()
        return False


def _execute_step_with_llm(
    llm_with_tools: Any,
    step: dict,
    state: ImplementorState,
    working_dir: str,
) -> bool:
    """
    Execute a step directly (no sub-steps) using LLM with tools.

    Args:
        llm_with_tools: LLM instance with tools bound
        step: Step dict to execute
        state: ImplementorState
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load AGENTS.md content
        category = step.get("category", "backend")
        agents_md_content = _load_agents_md_content(
            state.codebase_path or ".", category
        )

        # Select prompt based on category
        if category == "frontend":
            prompt_template = FRONTEND_PROMPT
        else:
            prompt_template = BACKEND_PROMPT

        # Format prompt
        step_info = f"Step {step.get('step', 'N/A')}: {step.get('title', 'N/A')}\n{step.get('description', '')}"
        substep_info = "N/A (no sub-steps)"
        files_affected = "Not specified"

        formatted_prompt = prompt_template.format(
            agent_md=agents_md_content or "No architecture guidelines available.",
            step_info=step_info,
            substep_info=substep_info,
            files_affected=files_affected,
        )

        # Add working directory context
        formatted_prompt += f"\n\n**Working Directory:** {working_dir}\n"
        formatted_prompt += "**IMPORTANT:** All file paths in tool calls must be relative to the working directory.\n"

        print("  🤖 Calling LLM with tools...")

        # Call LLM with tool support
        messages = [HumanMessage(content=formatted_prompt)]
        response = llm_with_tools.invoke(messages)

        # Process tool calls if any
        tool_calls_made = _process_tool_calls(
            response=response,
            llm_with_tools=llm_with_tools,
            messages=messages,
            state=state,
            working_dir=working_dir,
        )

        if tool_calls_made:
            print(f"  ✅ Step completed with {tool_calls_made} tool calls")
        else:
            print("  ⚠️ Step completed without tool calls")

        return True

    except Exception as e:
        print(f"  ❌ Error executing step: {e}")
        return False


def _process_tool_calls(
    response: Any,
    llm_with_tools: Any,
    messages: list,
    state: ImplementorState,
    working_dir: str,
    max_iterations: int = 25,
) -> int:
    """
    Process tool calls from LLM response iteratively until no more tool calls.

    Args:
        response: Initial LLM response
        llm_with_tools: LLM instance with tools bound
        messages: Message history
        state: ImplementorState to track file changes
        working_dir: Working directory
        max_iterations: Maximum iterations to prevent infinite loops (default: 25)
                       Increased from 10 to allow more complex sub-steps with
                       extensive codebase exploration before file creation

    Returns:
        Total number of tool calls made
    """
    import json

    from langchain_core.messages import ToolMessage

    tool_calls_count = 0
    iteration = 0

    while iteration < max_iterations:
        # Check if response has tool calls
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            # No more tool calls, we're done
            break

        # Add AI response to messages
        messages.append(response)

        # Process each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "unknown")

            print(f"      🔧 Tool call: {tool_name}")
            print(f"         Args: {json.dumps(tool_args, indent=2)}")

            # Execute tool
            try:
                # SECURITY: Force override working_directory to prevent LLM from escaping sandbox
                # This ensures all file operations stay within the specified working directory
                tool_args["working_directory"] = working_dir

                # Call the appropriate tool
                if tool_name == "read_file_tool":
                    result = read_file_tool.invoke(tool_args)
                elif tool_name == "write_file_tool":
                    result = write_file_tool.invoke(tool_args)
                    # Track file changes
                    file_path = tool_args.get("file_path", "")
                    _track_file_change(state, file_path, working_dir)
                elif tool_name == "grep_search_tool":
                    result = grep_search_tool.invoke(tool_args)
                elif tool_name == "create_directory_tool":
                    result = create_directory_tool.invoke(tool_args)
                elif tool_name == "list_files_tool":
                    result = list_files_tool.invoke(tool_args)
                elif tool_name == "str_replace_tool":
                    result = str_replace_tool.invoke(tool_args)
                    # Track file changes
                    file_path = tool_args.get("file_path", "")
                    _track_file_change(state, file_path, working_dir)
                else:
                    result = f"Error: Unknown tool '{tool_name}'"

                print(f"      ✅ Tool result: {result[:200]}...")

                # Add tool result to messages
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                )
                messages.append(tool_message)

                tool_calls_count += 1

            except Exception as e:
                print(f"      ❌ Tool execution error: {e}")
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_id,
                )
                messages.append(error_message)

        # Call LLM again with updated messages
        try:
            response = llm_with_tools.invoke(messages)
            iteration += 1
        except Exception as e:
            print(f"      ❌ Error calling LLM: {e}")
            break

    if iteration >= max_iterations:
        print(f"      ⚠️ Reached max iterations ({max_iterations})")
        print("      💡 Tip: If sub-step is incomplete, consider:")
        print("         - Splitting sub-step into smaller tasks")
        print("         - Increasing max_iterations limit")
        print("         - Optimizing discovery phase to reduce tool calls")

    return tool_calls_count


def _track_file_change(
    state: ImplementorState, file_path: str, working_dir: str
) -> None:
    """
    Track file changes in state (created or modified).

    Args:
        state: ImplementorState to update
        file_path: File path that was changed
        working_dir: Working directory
    """
    import os

    if not file_path:
        return

    # Resolve full path
    full_path = os.path.join(working_dir, file_path)

    # Check if file existed before (simple heuristic: if it's in modified list, it existed)
    if file_path in state.files_modified or file_path in state.files_created:
        # Already tracked
        return

    # Check if file exists now
    if os.path.exists(full_path):
        # Assume it was created if not in any list yet
        # (In reality, we'd need to check git status or track before/after)
        # For simplicity, we'll add to created list
        if file_path not in state.files_created:
            state.files_created.append(file_path)
            print(f"      📝 Tracked file creation: {file_path}")
    else:
        # File doesn't exist, might be an error
        print(f"      ⚠️ File not found after write: {file_path}")


def _load_agents_md_content(codebase_path: str, category: str) -> str:
    """
    Load AGENTS.md content from codebase based on category (backend/frontend).

    Args:
        codebase_path: Path to codebase root
        category: "backend" or "frontend"

    Returns:
        AGENTS.md content or empty string if not found
    """
    import os

    if not codebase_path or category not in ["backend", "frontend"]:
        return ""

    # Possible subdirectory names for each category
    category_dirs = {
        "backend": ["backend", "be", "server", "api"],
        "frontend": ["frontend", "fe", "client", "web", "ui"],
    }

    search_dirs = category_dirs.get(category, [])

    # Try to find AGENTS.md in category-specific directories
    for subdir in search_dirs:
        agents_path = os.path.join(codebase_path, subdir, "AGENTS.md")
        try:
            if os.path.exists(agents_path):
                with open(agents_path, encoding="utf-8") as f:
                    content = f.read()
                    print(
                        f"      ✅ Loaded {category.upper()} AGENTS.md from: {agents_path}"
                    )
                    return content
        except Exception as e:
            print(f"      ⚠️ Error loading {agents_path}: {e}")
            continue

    # Fallback: Try root AGENTS.md
    root_agents_path = os.path.join(codebase_path, "AGENTS.md")
    try:
        if os.path.exists(root_agents_path):
            with open(root_agents_path, encoding="utf-8") as f:
                content = f.read()
                print(f"      ✅ Loaded AGENTS.md from root: {root_agents_path}")
                return content
    except Exception as e:
        print(f"      ⚠️ Error loading root AGENTS.md: {e}")

    return ""
