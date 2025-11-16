"""
Initialize Node

Khởi tạo Implementor workflow và validate input từ Planner Agent.
"""

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState
from ..utils.validators import validate_tech_stack


def initialize(state: ImplementorState) -> ImplementorState:
    """
    Initialize implementor workflow và validate input.

    Args:
        state: ImplementorState với implementation plan từ Planner

    Returns:
        Updated ImplementorState với initial setup
    """
    try:
        print("🚀 Initializing Implementor Agent...")

        # Validate required inputs
        if not state.implementation_plan:
            state.error_message = "No implementation plan provided"
            state.status = "error"
            return state

        if not state.sandbox_id and not state.codebase_path:
            state.error_message = "No sandbox_id or codebase_path provided"
            state.status = "error"
            return state
        print("plan:")
        # Validate implementation plan quality (now guaranteed to be dict)
        # plan_valid, plan_issues = validate_implementation_plan(
        #     state.implementation_plan
        # )
        # if not plan_valid:
        #     state.error_message = (
        #         f"Invalid implementation plan: {'; '.join(plan_issues[:3])}"
        #     )
        #     state.status = "error"
        #     return state

        # Extract task information từ implementation plan
        # Support both simplified flat format and legacy nested format
        plan = state.implementation_plan
        print("plan:", plan)
        # Try simplified flat format first (new format from Planner)
        if "task_id" in plan and "steps" in plan:
            # Simplified flat format from updated Planner Agent
            state.task_id = plan.get("task_id", "")
            state.task_description = plan.get("description", "")

            # Parse steps and execution order
            state.plan_steps = plan.get("steps", [])
            state.execution_order = plan.get("execution_order", [])

            print(f"✅ Parsed simplified plan: {len(state.plan_steps)} steps")

        elif "task_info" in plan:
            # Legacy nested format from old Planner Agent
            task_info = plan["task_info"]
            state.task_id = task_info.get("task_id", "")
            state.task_description = task_info.get("description", "")

            # Extract steps from nested implementation structure
            implementation = plan.get("implementation", {})
            state.plan_steps = implementation.get("steps", [])
            state.execution_order = []

            print(f"✅ Parsed legacy nested plan: {len(state.plan_steps)} steps")

        else:
            # Fallback for very old format
            state.task_id = plan.get("task_id", "")
            state.task_description = plan.get("description", "")
            state.plan_steps = []
            state.execution_order = []

        # Extract file operations from steps (simplified format) or legacy format
        files_to_create_raw = []
        files_to_modify_raw = []

        if state.plan_steps:
            # NEW FORMAT: Steps don't have action_type or files_affected anymore
            # LLM will determine what files to create/modify using tools
            # We just track files that get created/modified during execution
            print(
                f"✅ Using new format: {len(state.plan_steps)} steps with sub-steps (files determined by LLM)"
            )

        elif "file_changes" in plan:
            # Legacy nested format from old Planner Agent
            file_changes = plan["file_changes"]
            files_to_create_raw = file_changes.get("files_to_create", [])
            files_to_modify_raw = file_changes.get("files_to_modify", [])
        else:
            # Legacy flat format (backward compatibility)
            files_to_create_raw = plan.get("files_to_create", [])
            files_to_modify_raw = plan.get("files_to_modify", [])

        # Note: Source code is always cloned to sandbox before workflow runs
        # No need to determine project type - always working with existing codebase

        # Extract tech stack từ plan hoặc detect từ codebase
        tech_stack = plan.get("tech_stack", "")
        if not tech_stack and state.codebase_path:
            # Use detect_stack_tool để phân tích codebase thực tế
            try:
                import json

                from ..tool.stack_tools import detect_stack_tool

                print(f"🔍 Detecting tech stack from codebase: {state.codebase_path}")
                stack_result = detect_stack_tool.invoke(
                    {"project_path": state.codebase_path}
                )

                if stack_result and not stack_result.startswith("Error"):
                    stack_info = json.loads(stack_result)
                    primary_language = stack_info.get("primary_language", "").lower()
                    frameworks = stack_info.get("frameworks", [])

                    # Map detected info to tech stack
                    if primary_language == "javascript":
                        if "Express.js" in frameworks:
                            tech_stack = "nodejs"
                        elif "Next.js" in frameworks:
                            tech_stack = "nextjs"
                        elif "React" in frameworks:
                            tech_stack = "react-vite"
                        else:
                            tech_stack = "nodejs"  # Default for JavaScript
                    elif primary_language == "python":
                        if "FastAPI" in frameworks:
                            tech_stack = "fastapi"
                        elif "Django" in frameworks:
                            tech_stack = "django"
                        elif "Flask" in frameworks:
                            tech_stack = "flask"
                        else:
                            tech_stack = "python"
                    else:
                        tech_stack = primary_language or "unknown"

                    print(
                        f"✅ Detected tech stack: {tech_stack} (language: {primary_language}, frameworks: {frameworks})"
                    )
                else:
                    print(f"⚠️ Stack detection failed: {stack_result}")
            except Exception as e:
                print(f"⚠️ Error detecting stack: {e}")

        # Fallback: Infer từ file patterns nếu vẫn không có tech stack
        if not tech_stack:
            files_to_create = plan.get("files_to_create", [])
            files_to_modify = plan.get("files_to_modify", [])
            all_files = files_to_create + files_to_modify

            file_patterns = [f.get("file_path", "") for f in all_files]

            if any(".py" in f for f in file_patterns):
                if any(
                    "requirements.txt" in f or "pyproject.toml" in f
                    for f in file_patterns
                ):
                    tech_stack = "fastapi"  # Default Python web framework
                else:
                    tech_stack = "python"
            elif any(".js" in f or ".ts" in f for f in file_patterns):
                if any("package.json" in f for f in file_patterns):
                    if any("next" in f.lower() for f in file_patterns):
                        tech_stack = "nextjs"
                    elif any("react" in f.lower() for f in file_patterns):
                        tech_stack = "react-vite"
                    else:
                        tech_stack = "nodejs"

        state.tech_stack = tech_stack

        # Validate tech stack
        if tech_stack:
            tech_valid, tech_issues = validate_tech_stack(tech_stack)
            if not tech_valid:
                print(f"⚠️  Tech stack validation issues: {'; '.join(tech_issues)}")

        # Note: Boilerplate templates no longer used
        # Repository creation from template handled by GitHub Template Repository API

        # NEW FORMAT: Files are determined dynamically by LLM during execution
        # We don't pre-populate files_to_create/files_to_modify anymore
        # Instead, files are tracked as they're created/modified by tools
        files_to_create = []
        files_to_modify = []

        # Only populate if using legacy format
        if files_to_create_raw or files_to_modify_raw:
            for file_info in files_to_create_raw:
                # Map fields from simplified format to FileChange model
                file_path = file_info.get("file_path") or file_info.get("path", "")
                description = file_info.get("description") or file_info.get("reason", "")

                # Include step/sub_step metadata for sequential execution
                step_info = ""
                if "step" in file_info and "sub_step" in file_info:
                    step_info = f"Step {file_info['step']}.{file_info['sub_step']}: "

                full_description = f"{step_info}{description}"
                if "test" in file_info and file_info["test"]:
                    full_description += f" | Test: {file_info['test']}"

                file_change = FileChange(
                    file_path=file_path,
                    operation="create",
                    content=file_info.get(
                        "content", ""
                    ),  # Will be populated by generate_code
                    change_type="full_file",
                    description=full_description,
                )
                files_to_create.append(file_change)

            for file_info in files_to_modify_raw:
                # Map fields from simplified format to FileChange model
                file_path = file_info.get("file_path") or file_info.get("path", "")
                description = file_info.get("description") or file_info.get("changes", "")

                # Include step/sub_step metadata for sequential execution
                step_info = ""
                if "step" in file_info and "sub_step" in file_info:
                    step_info = f"Step {file_info['step']}.{file_info['sub_step']}: "

                full_description = f"{step_info}{description}"
                if "test" in file_info and file_info["test"]:
                    full_description += f" | Test: {file_info['test']}"

                file_change = FileChange(
                    file_path=file_path,
                    operation="modify",
                    content=file_info.get(
                        "content", ""
                    ),  # Will be populated by generate_code
                    change_type=file_info.get("change_type", "incremental"),
                    target_function=file_info.get("target_function", ""),
                    target_class=file_info.get("target_class", ""),
                    description=full_description,
                )
                files_to_modify.append(file_change)

        state.files_to_create = files_to_create
        state.files_to_modify = files_to_modify

        # Generate feature branch name
        task_id_clean = state.task_id.replace(" ", "-").lower()
        if not task_id_clean:
            task_id_clean = "implementation"
        state.feature_branch = f"feature/{task_id_clean}"

        # Initialize step tracking indices
        state.current_step_index = 0
        state.current_sub_step_index = 0
        print(f"📍 Initialized step tracking: Step {state.current_step_index + 1}, Sub-step {state.current_sub_step_index + 1}")

        # Update status
        state.current_phase = "setup_branch"
        state.status = "initialized"

        # Add message
        message = AIMessage(
            content=f"✅ Implementor initialized successfully\n"
            f"- Task ID: {state.task_id}\n"
            f"- Tech Stack: {state.tech_stack}\n"
            f"- Files to Create: {len(state.files_to_create)}\n"
            f"- Files to Modify: {len(state.files_to_modify)}\n"
            f"- Feature Branch: {state.feature_branch}\n"
            f"- Working with existing codebase in sandbox"
        )
        state.messages.append(message)

        print(
            f"✅ Implementor initialized - {len(files_to_create)} files to create, {len(files_to_modify)} files to modify"
        )

        return state

    except Exception as e:
        state.error_message = f"Initialization failed: {str(e)}"
        state.status = "error"
        print(f"❌ Initialization failed: {e}")
        return state
