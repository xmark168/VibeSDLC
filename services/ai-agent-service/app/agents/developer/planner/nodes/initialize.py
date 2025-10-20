"""
Initialize Node

Setup initial state, validate input và chuẩn bị cho planning workflow.
"""

from langchain_core.messages import HumanMessage

from ..state import PlannerState


def initialize(state: PlannerState) -> PlannerState:
    """
    Initialize node - Setup initial state và validate input.

    Tasks:
    1. Validate task_description input
    2. Setup initial state values
    3. Create initial message for workflow
    4. Set current_phase to parse_task

    Args:
        state: PlannerState với task_description

    Returns:
        Updated PlannerState ready for task parsing
    """
    print("\n" + "=" * 80)
    print("🚀 INITIALIZE NODE - Setup Planning Workflow")
    print("=" * 80)

    # Validate input
    if not state.task_description.strip():
        print("❌ Error: Empty task description")
        state.status = "error_empty_task"
        state.error_message = "Task description cannot be empty"
        return state

    print(f"📝 Task Description: {state.task_description[:200]}...")

    # Detect tech stack from codebase if path is provided
    if state.codebase_path:
        tech_stack = detect_tech_stack(state.codebase_path)
        state.tech_stack = tech_stack
        print(f"🔍 Detected tech stack: {tech_stack}")
    else:
        print("⚠️ No codebase path provided - tech stack detection skipped")

    # Reset state for fresh planning
    state.current_iteration = 0
    state.validation_score = 0.0
    state.validation_issues = []
    state.can_proceed = False
    state.ready_for_implementation = False
    state.status = "initialized"
    state.error_message = ""

    # Clear previous outputs
    state.tools_output = {}
    state.final_plan = {}

    # Create initial message for workflow
    initial_message = HumanMessage(
        content=f"""Planning Request:

Task Description: {state.task_description}

Codebase Context: {state.codebase_context if state.codebase_context else "No additional context provided"}

Please analyze this task and create a detailed implementation plan following the 4-phase planning process:
1. Task Parsing - Extract requirements and constraints
2. Codebase Analysis - Analyze existing code and dependencies  
3. Dependency Mapping - Map execution order and dependencies
4. Implementation Planning - Create detailed implementation plan

Begin with Phase 1: Task Parsing."""
    )

    # Add to messages if not already present
    if not state.messages or state.messages[-1].content != initial_message.content:
        state.messages.append(initial_message)

    # Set next phase
    state.current_phase = "parse_task"

    print("✅ Initialization complete")
    print(f"🔄 Next Phase: {state.current_phase}")
    print("=" * 80 + "\n")

    return state


def detect_tech_stack(codebase_path: str) -> str:
    """
    Detect tech stack from codebase path.

    Args:
        codebase_path: Path to codebase for analysis

    Returns:
        Detected tech stack string (e.g., "nodejs", "fastapi", "react-vite")
    """
    try:
        # Try using detect_stack_tool first (if available)
        try:
            # Import detect_stack_tool from implementor
            import sys

            sys.path.append(
                os.path.join(os.path.dirname(__file__), "..", "..", "implementor")
            )
            from tool.stack_tools import detect_stack_tool

            print(f"🔍 Using detect_stack_tool for: {codebase_path}")
            stack_result = detect_stack_tool.invoke({"project_path": codebase_path})

            if stack_result and not stack_result.startswith("Error"):
                stack_info = json.loads(stack_result)
                primary_language = stack_info.get("primary_language", "").lower()
                frameworks = stack_info.get("frameworks", [])

                # Map detected info to tech stack (same logic as Implementor)
                if primary_language == "javascript":
                    if "Express.js" in frameworks:
                        return "nodejs"
                    elif "Next.js" in frameworks:
                        return "nextjs"
                    elif "React" in frameworks:
                        return "react-vite"
                    else:
                        return "nodejs"  # Default for JavaScript
                elif primary_language == "python":
                    if "FastAPI" in frameworks:
                        return "fastapi"
                    elif "Django" in frameworks:
                        return "django"
                    elif "Flask" in frameworks:
                        return "flask"
                    else:
                        return "python"
                else:
                    return primary_language or "unknown"

        except Exception as e:
            print(f"⚠️ detect_stack_tool failed: {e}")

        # Fallback: Simple file-based detection
        print(f"🔍 Using fallback detection for: {codebase_path}")

        # Check for package.json (Node.js)
        package_json_path = os.path.join(codebase_path, "package.json")
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path) as f:
                    package_data = json.load(f)
                dependencies = {
                    **package_data.get("dependencies", {}),
                    **package_data.get("devDependencies", {}),
                }

                if "express" in dependencies:
                    return "nodejs"
                elif "next" in dependencies:
                    return "nextjs"
                elif "react" in dependencies:
                    return "react-vite"
                else:
                    return "nodejs"  # Default for JavaScript projects
            except Exception as e:
                print(f"⚠️ Error parsing package.json: {e}")

        # Check for Python files
        for root, dirs, files in os.walk(codebase_path):
            if any(f.endswith(".py") for f in files):
                # Check for requirements.txt or pyproject.toml
                if os.path.exists(
                    os.path.join(codebase_path, "requirements.txt")
                ) or os.path.exists(os.path.join(codebase_path, "pyproject.toml")):
                    return "fastapi"  # Default Python web framework
                else:
                    return "python"
            break  # Only check first level

        # Default fallback
        return "unknown"

    except Exception as e:
        print(f"⚠️ Tech stack detection error: {e}")
        return "unknown"
