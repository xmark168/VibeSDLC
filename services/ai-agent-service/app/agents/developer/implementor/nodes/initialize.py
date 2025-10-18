"""
Initialize Node

Khởi tạo Implementor workflow và validate input từ Planner Agent.
"""

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState


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
        plan = state.implementation_plan
        state.task_id = plan.get("task_id", "")
        state.task_description = plan.get("description", "")

        # Determine project type
        if "files_to_create" in plan and plan["files_to_create"]:
            # Check if this looks like a new project
            create_files = plan["files_to_create"]
            has_main_files = any(
                file_info.get("file_path", "").endswith(
                    ("main.py", "app.py", "index.js", "package.json")
                )
                for file_info in create_files
            )
            state.is_new_project = has_main_files

        # Extract tech stack từ plan hoặc từ file patterns
        tech_stack = plan.get("tech_stack", "")
        if not tech_stack:
            # Infer từ file patterns
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

        # Set boilerplate template path for new projects
        if state.is_new_project and tech_stack:
            template_mapping = {
                "fastapi": "be/python/fastapi-basic",
                "python": "be/python/fastapi-basic",
                "nextjs": "fe/nextjs/nextjs-basic",
                "react-vite": "fe/react/react-vite",
                "react": "fe/react/react-vite",
                "nodejs": "be/nodejs/express-basic",
                "express": "be/nodejs/express-basic",
            }
            state.boilerplate_template = template_mapping.get(tech_stack, "")

        # Parse file changes từ implementation plan
        files_to_create = []
        files_to_modify = []

        for file_info in plan.get("files_to_create", []):
            file_change = FileChange(
                file_path=file_info.get("file_path", ""),
                operation="create",
                content=file_info.get("content", ""),
                change_type="full_file",
                description=file_info.get("description", ""),
            )
            files_to_create.append(file_change)

        for file_info in plan.get("files_to_modify", []):
            file_change = FileChange(
                file_path=file_info.get("file_path", ""),
                operation="modify",
                content=file_info.get("content", ""),
                change_type=file_info.get("change_type", "incremental"),
                target_function=file_info.get("target_function", ""),
                target_class=file_info.get("target_class", ""),
                description=file_info.get("description", ""),
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
            f"- Project Type: {'New Project' if state.is_new_project else 'Existing Project'}\n"
            f"- Tech Stack: {state.tech_stack}\n"
            f"- Files to Create: {len(state.files_to_create)}\n"
            f"- Files to Modify: {len(state.files_to_modify)}\n"
            f"- Feature Branch: {state.feature_branch}"
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
