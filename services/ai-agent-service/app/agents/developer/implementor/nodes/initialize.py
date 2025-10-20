"""
Initialize Node

Khởi tạo Implementor workflow và validate input từ Planner Agent.
"""

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState
from ..utils.validators import validate_implementation_plan, validate_tech_stack


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

        # Validate implementation plan quality
        plan_valid, plan_issues = validate_implementation_plan(
            state.implementation_plan
        )
        if not plan_valid:
            state.error_message = (
                f"Invalid implementation plan: {'; '.join(plan_issues[:3])}"
            )
            state.status = "error"
            return state

        # Extract task information từ implementation plan
        # Support both flat format (backward compatibility) and nested format
        plan = state.implementation_plan

        # Try nested format first, then fall back to flat format
        if "task_info" in plan:
            # Nested format from Planner Agent
            task_info = plan["task_info"]
            state.task_id = task_info.get("task_id", "")
            state.task_description = task_info.get("description", "")
        else:
            # Flat format (backward compatibility)
            state.task_id = plan.get("task_id", "")
            state.task_description = plan.get("description", "")

        # Extract file operations - support both nested and flat formats
        if "file_changes" in plan:
            # Nested format from Planner Agent
            file_changes = plan["file_changes"]
            files_to_create_raw = file_changes.get("files_to_create", [])
            files_to_modify_raw = file_changes.get("files_to_modify", [])
        else:
            # Flat format (backward compatibility)
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

        # Parse file changes từ implementation plan với field mapping
        files_to_create = []
        files_to_modify = []

        for file_info in files_to_create_raw:
            # Map fields from nested format to FileChange model
            file_path = file_info.get("file_path") or file_info.get("path", "")
            description = file_info.get("description") or file_info.get("reason", "")

            file_change = FileChange(
                file_path=file_path,
                operation="create",
                content=file_info.get(
                    "content", ""
                ),  # Will be populated by generate_code
                change_type="full_file",
                description=description,
            )
            files_to_create.append(file_change)

        for file_info in files_to_modify_raw:
            # Map fields from nested format to FileChange model
            file_path = file_info.get("file_path") or file_info.get("path", "")
            description = file_info.get("description") or file_info.get("changes", "")

            file_change = FileChange(
                file_path=file_path,
                operation="modify",
                content=file_info.get(
                    "content", ""
                ),  # Will be populated by generate_code
                change_type=file_info.get("change_type", "incremental"),
                target_function=file_info.get("target_function", ""),
                target_class=file_info.get("target_class", ""),
                description=description,
            )
            files_to_modify.append(file_change)

        state.files_to_create = files_to_create
        state.files_to_modify = files_to_modify

        # Generate feature branch name
        task_id_clean = state.task_id.replace(" ", "-").lower()
        if not task_id_clean:
            task_id_clean = "implementation"
        state.feature_branch = f"feature/{task_id_clean}"

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
