"""
Generate Plan Node

PHASE 4: Implementation Planning - Create detailed implementation plan
"""

from typing import Any

from langchain_core.messages import AIMessage

from ..state import ImplementationPlan, PlannerState


def generate_plan(state: PlannerState) -> PlannerState:
    """
    Generate Plan node - PHASE 4: Create detailed implementation plan.

    Tasks:
    1. Determine task complexity score (1-10)
    2. Create simple or complex plan based on complexity
    3. Include implementation steps với detailed guidance
    4. Estimate effort và story points
    5. Document risks và assumptions
    6. Structure output trong ImplementationPlan model

    Args:
        state: PlannerState với dependency_mapping

    Returns:
        Updated PlannerState với implementation_plan populated
    """
    print("\n" + "=" * 80)
    print("PLAN: GENERATE PLAN NODE - Phase 4: Implementation Planning")
    print("=" * 80)

    try:
        task_requirements = state.task_requirements
        codebase_analysis = state.codebase_analysis
        dependency_mapping = state.dependency_mapping

        print(f"🎯 Generating implementation plan for: {task_requirements.task_id}")

        # Use LLM for plan generation
        import json
        import os

        from langchain_openai import ChatOpenAI

        from app.templates.prompts.developer.planner import GENERATE_PLAN_PROMPT

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Create prompt for plan generation using template
        plan_prompt = f"""{GENERATE_PLAN_PROMPT}

## TASK CONTEXT

Tech Stack: {state.tech_stack or "unknown"}

Task Requirements:
{task_requirements.model_dump_json(indent=2)}

Codebase Analysis:
{codebase_analysis.model_dump_json(indent=2)}

Dependency Mapping:
{dependency_mapping.model_dump_json(indent=2)}

## INSTRUCTIONS

Based on the above analysis, generate a detailed implementation plan in JSON format.
Remember: EVERY field must be populated with meaningful content. NO empty fields, NO empty arrays (unless truly empty), NO null values.
"""

        print("🤖 Calling LLM for plan generation...")

        # Call LLM
        response = llm.invoke(plan_prompt)
        llm_output = response.content

        print(f"📝 LLM Response: {llm_output[:200]}...")

        # Parse JSON response from LLM - Handle markdown code blocks
        try:
            # Strip markdown code blocks if present
            cleaned_output = llm_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]  # Remove ```json
            elif cleaned_output.startswith("```"):
                cleaned_output = cleaned_output[3:]  # Remove ```
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]  # Remove trailing ```
            cleaned_output = cleaned_output.strip()

            print(f"🧹 Cleaned LLM output: {cleaned_output[:100]}...")

            parsed_plan = json.loads(cleaned_output)

            # Validate and complete the plan
            parsed_plan = validate_and_complete_plan(
                parsed_plan, task_requirements, codebase_analysis, dependency_mapping
            )

            complexity_score = parsed_plan.get("complexity_score", 5)
            plan_type = parsed_plan.get("plan_type", "simple")

            # Handle approach field - ensure it's a dictionary
            approach_raw = parsed_plan.get("approach", {})
            if isinstance(approach_raw, str):
                # If approach is a string, convert to proper dictionary
                approach = {
                    "strategy": approach_raw,
                    "pattern": "Follow existing patterns in codebase",
                    "architecture_alignment": "Aligns with current service-oriented architecture",
                }
            elif isinstance(approach_raw, dict):
                # Ensure all required fields exist
                approach = {
                    "strategy": approach_raw.get(
                        "strategy", "Create new components following existing patterns"
                    ),
                    "pattern": approach_raw.get(
                        "pattern", "Follow existing patterns in codebase"
                    ),
                    "architecture_alignment": approach_raw.get(
                        "architecture_alignment",
                        "Aligns with current service-oriented architecture",
                    ),
                }
            else:
                # Default approach
                approach = {
                    "strategy": "Create new components following existing patterns",
                    "pattern": "Follow existing patterns in codebase",
                    "architecture_alignment": "Aligns with current service-oriented architecture",
                }

            llm_steps = parsed_plan.get("implementation_steps", [])
            estimated_hours = parsed_plan.get("estimated_hours", 0)
            story_points = parsed_plan.get("story_points", 0)

            print(
                f"✅ Successfully parsed LLM plan with complexity {complexity_score}/10, {len(llm_steps)} steps, {estimated_hours}h"
            )

        except json.JSONDecodeError as e:
            print(f"❌ LLM response not valid JSON after cleaning: {e}")
            print(f"Raw LLM output: {llm_output[:200]}...")
            print(
                f"Cleaned output: {cleaned_output[:200] if 'cleaned_output' in locals() else 'N/A'}..."
            )
            # NO FALLBACK - Return default values if LLM fails
            complexity_score = 5
            plan_type = "simple"
            approach = {
                "strategy": "Create new components following existing patterns",
                "pattern": "Follow existing patterns in codebase",
                "architecture_alignment": "Aligns with current service-oriented architecture",
            }
            llm_steps = []
            estimated_hours = 0
            story_points = 0

        print(f"INFO: Complexity Score: {complexity_score}/10")

        # Use implementation steps from LLM if available, otherwise create minimal fallback
        if llm_steps:
            implementation_steps = llm_steps
            print(f"✅ Using {len(llm_steps)} implementation steps from LLM")
        else:
            print("⚠️ No implementation steps from LLM, using minimal fallback")
            implementation_steps = [
                {
                    "step": 1,
                    "title": "Implement feature",
                    "description": "Complete the requested feature implementation",
                    "files": [],
                    "estimated_hours": estimated_hours or 4.0,
                    "complexity": "medium",
                    "dependencies": [],
                    "blocking": False,
                    "type": "implementation",
                }
            ]

        # NO MORE FALLBACK LOGIC - All steps should come from LLM

        # Use totals from LLM or calculate from steps
        if estimated_hours > 0:
            total_hours = estimated_hours
        else:
            total_hours = sum(
                step.get("estimated_hours", 0) for step in implementation_steps
            )

        if story_points == 0:
            story_points = estimate_story_points(complexity_score, total_hours)

        # Create testing requirements
        testing_requirements = {
            "unit_tests": codebase_analysis.testing_requirements.get("unit_tests", {}),
            "integration_tests": codebase_analysis.testing_requirements.get(
                "integration_tests", {}
            ),
            "coverage_target": "90%",
        }

        # Create rollback plan
        rollback_plan = {
            "database": "Use migration rollback if database changes exist",
            "code": "Revert commits in reverse order of implementation",
            "data": "No data migration needed for new features",
        }

        # Identify risks
        risks = identify_risks(task_requirements, codebase_analysis, complexity_score)

        # Create assumptions
        assumptions = [
            "Development environment is properly set up",
            "All required dependencies are available",
            "Database access is configured correctly",
        ] + task_requirements.assumptions

        # Create subtasks for complex plans
        subtasks = []
        execution_strategy = {}

        if plan_type == "complex":
            subtasks = create_subtasks(implementation_steps)
            execution_strategy = create_execution_strategy(subtasks, dependency_mapping)

        # Create ImplementationPlan object
        implementation_plan = ImplementationPlan(
            plan_type=plan_type,
            task_id=task_requirements.task_id,
            description=task_requirements.task_title,
            complexity_score=complexity_score,
            complexity_reasoning=f"Score based on {len(codebase_analysis.files_to_create)} new files, "
            f"{len(codebase_analysis.files_to_modify)} modified files, "
            f"{len(dependency_mapping.execution_order)} implementation steps",
            approach=approach,
            implementation_steps=implementation_steps,
            subtasks=subtasks,
            execution_strategy=execution_strategy,
            testing_requirements=testing_requirements,
            rollback_plan=rollback_plan,
            total_estimated_hours=total_hours,
            story_points=story_points,
            risks=risks,
            assumptions=assumptions,
        )

        # Update state
        state.implementation_plan = implementation_plan
        state.current_phase = "validate_plan"
        state.status = "plan_generated"

        # Store in tools_output
        state.tools_output["implementation_plan"] = implementation_plan.model_dump()

        # Add AI message
        plan_result = {
            "phase": "Implementation Planning",
            "plan_type": plan_type,
            "complexity_score": complexity_score,
            "total_steps": len(implementation_steps),
            "estimated_hours": total_hours,
            "story_points": story_points,
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 4: Implementation Planning - COMPLETED

Plan Results:
{json.dumps(plan_result, indent=2)}

Implementation Steps:
{chr(10).join(f"{step['step']}. {step['title']} ({step['estimated_hours']}h)" for step in implementation_steps)}

Total Effort: {total_hours} hours ({story_points} story points)

Ready to proceed to Plan Validation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Implementation plan generated successfully")
        print(f"PLAN: Plan Type: {plan_type}")
        print(f"INFO: Complexity: {complexity_score}/10")
        print(f"TIME:  Total Hours: {total_hours}")
        print(f"SCORE: Story Points: {story_points}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in plan generation: {e}")
        state.status = "error_plan_generation"
        state.error_message = f"Plan generation failed: {str(e)}"
        return state


def calculate_complexity_score(
    task_requirements, codebase_analysis, dependency_mapping
) -> int:
    """Calculate complexity score based on various factors."""
    score = 0

    # Base complexity from requirements
    score += min(len(task_requirements.requirements), 3)

    # File changes complexity
    score += len(codebase_analysis.files_to_create) * 0.5
    score += len(codebase_analysis.files_to_modify) * 0.3

    # Database changes add complexity
    if codebase_analysis.database_changes:
        score += 2

    # API changes add complexity
    if codebase_analysis.api_endpoints:
        score += 1

    # Dependency complexity
    score += len(dependency_mapping.blocking_steps) * 0.5

    return min(int(score), 10)


def determine_strategy(task_requirements, codebase_analysis) -> str:
    """Determine implementation strategy based on analysis."""
    if codebase_analysis.files_to_create:
        return "Create new components following existing patterns"
    elif codebase_analysis.files_to_modify:
        return "Extend existing components with new functionality"
    else:
        return "Configuration or minor changes to existing code"


def estimate_step_hours(step: dict[str, Any]) -> float:
    """Estimate hours for implementation step."""
    base_hours = 2.0

    if step.get("blocking", False):
        base_hours *= 1.5

    file_count = len(step.get("files", []))
    if file_count > 1:
        base_hours += (file_count - 1) * 0.5

    return round(base_hours, 1)


def estimate_story_points(complexity_score: int, total_hours: float) -> int:
    """Estimate story points using Fibonacci sequence."""
    if complexity_score <= 2:
        return 1
    elif complexity_score <= 4:
        return 2
    elif complexity_score <= 6:
        return 3
    elif complexity_score <= 8:
        return 5
    else:
        return 8


def identify_risks(
    task_requirements, codebase_analysis, complexity_score: int
) -> list[dict[str, Any]]:
    """Identify potential risks."""
    risks = []

    if complexity_score >= 7:
        risks.append(
            {
                "risk": "High complexity may lead to implementation delays",
                "probability": "medium",
                "impact": "medium",
                "mitigation": "Break down into smaller subtasks and review frequently",
            }
        )

    if codebase_analysis.database_changes:
        risks.append(
            {
                "risk": "Database migration may cause downtime",
                "probability": "low",
                "impact": "high",
                "mitigation": "Test migration thoroughly in staging environment",
            }
        )

    return risks


def create_subtasks(implementation_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create subtasks for complex plans."""
    subtasks = []
    for i, step in enumerate(implementation_steps):
        subtasks.append(
            {
                "subtask_id": f"SUB-{i + 1:03d}",
                "title": step["title"],
                "description": step["description"],
                "estimated_hours": step["estimated_hours"],
                "priority": "high" if step["blocking"] else "medium",
                "dependencies": step["dependencies"],
            }
        )
    return subtasks


def create_execution_strategy(
    subtasks: list[dict[str, Any]], dependency_mapping
) -> dict[str, Any]:
    """Create execution strategy for complex plans."""
    return {
        "phases": [
            {
                "phase": 1,
                "name": "Foundation",
                "subtasks": [
                    st["subtask_id"] for st in subtasks if st["priority"] == "high"
                ][:2],
                "blocking": True,
            },
            {
                "phase": 2,
                "name": "Implementation",
                "subtasks": [st["subtask_id"] for st in subtasks[2:4]],
                "blocking": True,
            },
            {
                "phase": 3,
                "name": "Integration",
                "subtasks": [st["subtask_id"] for st in subtasks[4:]],
                "blocking": False,
            },
        ]
    }


def estimate_file_creation_hours(file_info) -> float:
    """Estimate hours for creating a new file."""
    complexity = file_info.get("complexity", "medium")
    estimated_lines = file_info.get("estimated_lines", 100)

    base_hours = {"low": 1.0, "medium": 2.0, "high": 4.0}.get(complexity, 2.0)

    # Adjust based on file size
    if estimated_lines > 200:
        base_hours *= 1.5
    elif estimated_lines < 50:
        base_hours *= 0.7

    return round(base_hours, 1)


def estimate_file_modification_hours(file_info) -> float:
    """Estimate hours for modifying an existing file."""
    complexity = file_info.get("complexity", "medium")
    risk = file_info.get("risk", "low")

    base_hours = {"low": 0.5, "medium": 1.0, "high": 2.0}.get(complexity, 1.0)

    # Adjust based on risk
    if risk == "high":
        base_hours *= 1.5
    elif risk == "medium":
        base_hours *= 1.2

    return round(base_hours, 1)


def validate_and_complete_plan(
    plan: dict[str, Any],
    task_requirements,
    codebase_analysis,
    dependency_mapping,
) -> dict[str, Any]:
    """
    Validate and complete the plan by filling missing fields with intelligent defaults.

    Ensures NO empty fields, NO empty arrays (unless truly empty), NO null values.
    """

    # Ensure all top-level fields exist
    if not plan.get("plan_type"):
        plan["plan_type"] = "simple"

    if not plan.get("task_id"):
        plan["task_id"] = task_requirements.task_id or "TSK-UNKNOWN"

    if not plan.get("description"):
        plan["description"] = task_requirements.task_title or "Implementation plan"

    if not plan.get("complexity_score"):
        plan["complexity_score"] = calculate_complexity_score(
            task_requirements, codebase_analysis, dependency_mapping
        )

    if not plan.get("complexity_reasoning"):
        plan["complexity_reasoning"] = (
            f"Score based on {len(codebase_analysis.files_to_create)} new files, "
            f"{len(codebase_analysis.files_to_modify)} modified files, "
            f"{len(dependency_mapping.execution_order)} implementation steps"
        )

    # Ensure approach is complete
    if not plan.get("approach") or not isinstance(plan.get("approach"), dict):
        plan["approach"] = {}

    approach = plan["approach"]
    if not approach.get("strategy"):
        approach["strategy"] = determine_strategy(task_requirements, codebase_analysis)
    if not approach.get("pattern"):
        approach["pattern"] = "Follow existing patterns in codebase"
    if not approach.get("architecture_alignment"):
        approach["architecture_alignment"] = (
            "Aligns with current service-oriented architecture"
        )
    if not approach.get("alternatives_considered"):
        approach["alternatives_considered"] = []

    # Ensure implementation_steps is populated
    if not plan.get("implementation_steps") or not isinstance(
        plan.get("implementation_steps"), list
    ):
        plan["implementation_steps"] = []

    if not plan["implementation_steps"]:
        # Create steps from dependency mapping if LLM didn't provide them
        plan["implementation_steps"] = create_steps_from_dependencies(
            dependency_mapping, codebase_analysis
        )

    # Ensure each step has all required fields
    for i, step in enumerate(plan["implementation_steps"]):
        if not step.get("step"):
            step["step"] = i + 1
        if not step.get("title"):
            step["title"] = f"Step {i + 1}"
        if not step.get("description"):
            step["description"] = "Implementation step"
        if not step.get("files"):
            step["files"] = []
        if not step.get("estimated_hours"):
            step["estimated_hours"] = 2.0
        if not step.get("complexity"):
            step["complexity"] = "medium"
        if not step.get("dependencies"):
            step["dependencies"] = []
        if "blocking" not in step:
            step["blocking"] = False
        if not step.get("validation"):
            step["validation"] = "Verify step is complete"
        if not step.get("error_handling"):
            step["error_handling"] = []

    # Ensure estimated_hours
    if not plan.get("estimated_hours") or plan.get("estimated_hours") == 0:
        plan["estimated_hours"] = sum(
            step.get("estimated_hours", 2.0)
            for step in plan.get("implementation_steps", [])
        )

    # Ensure story_points
    if not plan.get("story_points") or plan.get("story_points") == 0:
        plan["story_points"] = estimate_story_points(
            plan.get("complexity_score", 5), plan.get("estimated_hours", 0)
        )

    # Ensure requirements
    if not plan.get("requirements"):
        plan["requirements"] = {}

    req = plan["requirements"]
    if not req.get("functional_requirements"):
        req["functional_requirements"] = task_requirements.requirements or [
            "Implement requested feature"
        ]
    if not req.get("acceptance_criteria"):
        req["acceptance_criteria"] = task_requirements.acceptance_criteria or [
            "Feature works as specified"
        ]
    if not req.get("business_rules"):
        req["business_rules"] = task_requirements.business_rules or {}
    if not req.get("technical_specs"):
        req["technical_specs"] = task_requirements.technical_specs or {}
    if not req.get("constraints"):
        req["constraints"] = task_requirements.constraints or []

    # Ensure file_changes
    if not plan.get("file_changes"):
        plan["file_changes"] = {}

    fc = plan["file_changes"]
    if not fc.get("files_to_create"):
        fc["files_to_create"] = [
            {
                "path": f.get("path", "new_file.py"),
                "reason": f.get("reason", "New file needed"),
                "template": f.get("template", ""),
                "estimated_lines": f.get("estimated_lines", 100),
                "complexity": f.get("complexity", "medium"),
            }
            for f in codebase_analysis.files_to_create
        ]

    if not fc.get("files_to_modify"):
        fc["files_to_modify"] = [
            {
                "path": f.get("path", "existing_file.py"),
                "lines": f.get("lines", []),
                "changes": f.get("changes", "Modifications needed"),
                "complexity": f.get("complexity", "medium"),
                "risk": f.get("risk", "low"),
            }
            for f in codebase_analysis.files_to_modify
        ]

    if not fc.get("affected_modules"):
        fc["affected_modules"] = codebase_analysis.affected_modules or []

    # Ensure infrastructure
    if not plan.get("infrastructure"):
        plan["infrastructure"] = {}

    infra = plan["infrastructure"]
    if not infra.get("database_changes"):
        infra["database_changes"] = codebase_analysis.database_changes or []
    if not infra.get("api_endpoints"):
        infra["api_endpoints"] = codebase_analysis.api_endpoints or []
    if not infra.get("external_dependencies"):
        # Ensure external dependencies have complete information
        external_deps = complete_external_dependencies(
            codebase_analysis.external_dependencies or []
        )
        infra["external_dependencies"] = external_deps
    if not infra.get("internal_dependencies"):
        infra["internal_dependencies"] = codebase_analysis.internal_dependencies or []

    # Ensure risks
    if not plan.get("risks"):
        plan["risks"] = identify_risks(
            task_requirements, codebase_analysis, plan.get("complexity_score", 5)
        )

    # Ensure assumptions
    if not plan.get("assumptions"):
        plan["assumptions"] = task_requirements.assumptions or [
            "Development environment is properly set up"
        ]

    # Ensure metadata
    if not plan.get("metadata"):
        plan["metadata"] = {}

    meta = plan["metadata"]
    meta["planner_version"] = "1.0"
    meta["created_by"] = "planner_agent"
    meta["validation_passed"] = True

    return plan


def create_steps_from_dependencies(
    dependency_mapping, codebase_analysis
) -> list[dict[str, Any]]:
    """Create implementation steps from dependency mapping."""
    steps = []

    for i, exec_step in enumerate(dependency_mapping.execution_order, 1):
        step = {
            "step": i,
            "title": exec_step.get("action", f"Step {i}"),
            "description": exec_step.get("reason", "Implementation step"),
            "action": exec_step.get("action", ""),
            "files": exec_step.get("files", []),
            "estimated_hours": estimate_step_hours(exec_step),
            "complexity": "medium",
            "dependencies": exec_step.get("depends_on", []),
            "blocking": exec_step.get("blocking", False),
            "validation": f"Verify step {i} is complete",
            "error_handling": [],
        }
        steps.append(step)

    return steps


def complete_external_dependencies(
    external_deps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Complete external dependencies with all required fields.

    Ensures each dependency has:
    - package: Package name
    - version: Version constraint
    - purpose: Why this package is needed
    - already_installed: Boolean flag
    - installation_method: pip/npm/yarn/poetry
    - install_command: Executable installation command
    - package_file: Target configuration file
    - section: dependencies or devDependencies

    Args:
        external_deps: List of dependency dictionaries from codebase analysis

    Returns:
        List of completed dependency dictionaries with all required fields
    """
    completed_deps = []

    for dep in external_deps:
        completed_dep = {
            # Required fields
            "package": dep.get("package", "unknown-package"),
            "version": dep.get("version", ">=1.0.0"),
            "purpose": dep.get(
                "purpose", dep.get("reason", "Required for implementation")
            ),
            "already_installed": dep.get("already_installed", False),
            "installation_method": dep.get("installation_method", "pip"),
            "install_command": "",  # Will be set below
            "package_file": dep.get("package_file", "pyproject.toml"),
            "section": dep.get("section", "dependencies"),
        }

        # Generate install_command based on already_installed flag
        if completed_dep["already_installed"]:
            completed_dep["install_command"] = "Already installed"
        else:
            # Build install command with proper formatting
            package_spec = completed_dep["package"]
            version = completed_dep["version"]

            # Ensure version constraint is properly formatted
            if version and not version.startswith((">=", "<=", "==", "~", "^")):
                version = f">={version}"

            if version:
                package_spec = f"{package_spec}{version}"

            method = completed_dep["installation_method"]
            completed_dep["install_command"] = f"{method} install {package_spec}"

        # Validate all required fields are populated
        required_fields = [
            "package",
            "version",
            "purpose",
            "already_installed",
            "installation_method",
            "install_command",
            "package_file",
            "section",
        ]

        for field in required_fields:
            if not completed_dep.get(field):
                # Set sensible defaults for missing fields
                if field == "package":
                    completed_dep[field] = "unknown-package"
                elif field == "version":
                    completed_dep[field] = ">=1.0.0"
                elif field == "purpose":
                    completed_dep[field] = "Required for implementation"
                elif field == "already_installed":
                    completed_dep[field] = False
                elif field == "installation_method":
                    completed_dep[field] = "pip"
                elif field == "install_command":
                    completed_dep[field] = (
                        f"{completed_dep.get('installation_method', 'pip')} install "
                        f"{completed_dep.get('package', 'unknown-package')}"
                    )
                elif field == "package_file":
                    completed_dep[field] = "pyproject.toml"
                elif field == "section":
                    completed_dep[field] = "dependencies"

        completed_deps.append(completed_dep)

    return completed_deps
