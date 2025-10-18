"""
Map Dependencies Node

PHASE 3: Dependency Mapping - Map execution order, dependencies, blocking steps
"""

import json
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from ..state import PlannerState, DependencyMapping


def map_dependencies(state: PlannerState) -> PlannerState:
    """
    Map Dependencies node - PHASE 3: Map execution order và dependencies.

    Tasks:
    1. Analyze dependencies between implementation steps
    2. Create execution order với blocking relationships
    3. Identify parallel execution opportunities
    4. Map internal và external dependencies
    5. Structure output trong DependencyMapping model

    Args:
        state: PlannerState với codebase_analysis

    Returns:
        Updated PlannerState với dependency_mapping populated
    """
    print("\n" + "=" * 80)
    print("🔗 MAP DEPENDENCIES NODE - Phase 3: Dependency Mapping")
    print("=" * 80)

    try:
        codebase_analysis = state.codebase_analysis
        task_requirements = state.task_requirements

        print(f"🎯 Mapping dependencies for task: {task_requirements.task_id}")

        # Create execution order based on analysis
        execution_order = []
        step_counter = 1

        # Database changes first (if any)
        if codebase_analysis.database_changes:
            execution_order.append(
                {
                    "step": step_counter,
                    "action": "Create database migration",
                    "reason": "Database schema changes must be applied first",
                    "blocking": True,
                    "depends_on": [],
                    "files": ["migrations/add_new_feature_tables.py"],
                }
            )
            step_counter += 1

        # Model changes next
        model_files = [
            f for f in codebase_analysis.files_to_modify if "models" in f["path"]
        ]
        if model_files:
            depends_on = [1] if codebase_analysis.database_changes else []
            execution_order.append(
                {
                    "step": step_counter,
                    "action": "Update data models",
                    "reason": "Services depend on updated models",
                    "blocking": True,
                    "depends_on": depends_on,
                    "files": [f["path"] for f in model_files],
                }
            )
            step_counter += 1

        # Service layer changes
        service_files = [
            f for f in codebase_analysis.files_to_create if "services" in f["path"]
        ]
        if service_files:
            depends_on = []
            if model_files:
                depends_on.append(step_counter - 1)
            elif codebase_analysis.database_changes:
                depends_on.append(1)

            execution_order.append(
                {
                    "step": step_counter,
                    "action": "Implement service layer",
                    "reason": "Business logic implementation",
                    "blocking": True,
                    "depends_on": depends_on,
                    "files": [f["path"] for f in service_files],
                }
            )
            step_counter += 1

        # API endpoints
        api_files = [
            f
            for f in codebase_analysis.files_to_modify
            if "api" in f["path"] or "routes" in f["path"]
        ]
        if api_files or codebase_analysis.api_endpoints:
            depends_on = []
            if service_files:
                depends_on.append(step_counter - 1)
            elif model_files:
                depends_on.append(step_counter - 2)

            execution_order.append(
                {
                    "step": step_counter,
                    "action": "Add API endpoints",
                    "reason": "External interface implementation",
                    "blocking": False,
                    "depends_on": depends_on,
                    "files": [f["path"] for f in api_files],
                }
            )
            step_counter += 1

        # Testing (can be parallel with API)
        if codebase_analysis.testing_requirements:
            depends_on = [step_counter - 1] if execution_order else []
            execution_order.append(
                {
                    "step": step_counter,
                    "action": "Write tests",
                    "reason": "Validation of implementation",
                    "blocking": False,
                    "depends_on": depends_on,
                    "files": codebase_analysis.testing_requirements.get(
                        "unit_tests", {}
                    ).get("files", []),
                }
            )

        # Identify blocking steps
        blocking_steps = [step["step"] for step in execution_order if step["blocking"]]

        # Identify parallel opportunities
        parallel_opportunities = []
        non_blocking_steps = [
            step["step"] for step in execution_order if not step["blocking"]
        ]
        if len(non_blocking_steps) > 1:
            parallel_opportunities.append(non_blocking_steps)

        # Create dependencies structure
        dependencies = {
            "external": codebase_analysis.external_dependencies,
            "internal": codebase_analysis.internal_dependencies,
            "execution_flow": {
                "sequential_steps": blocking_steps,
                "parallel_steps": parallel_opportunities,
                "total_steps": len(execution_order),
            },
        }

        # Create DependencyMapping object
        dependency_mapping = DependencyMapping(
            execution_order=execution_order,
            dependencies=dependencies,
            blocking_steps=blocking_steps,
            parallel_opportunities=parallel_opportunities,
        )

        # Update state
        state.dependency_mapping = dependency_mapping
        state.current_phase = "generate_plan"
        state.status = "dependencies_mapped"

        # Store in tools_output
        state.tools_output["dependency_mapping"] = dependency_mapping.model_dump()

        # Add AI message
        mapping_result = {
            "phase": "Dependency Mapping",
            "total_steps": len(execution_order),
            "blocking_steps": len(blocking_steps),
            "parallel_opportunities": len(parallel_opportunities),
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 3: Dependency Mapping - COMPLETED

Mapping Results:
{json.dumps(mapping_result, indent=2)}

Execution Order:
{chr(10).join(f"{step['step']}. {step['action']} ({'BLOCKING' if step['blocking'] else 'NON-BLOCKING'})" for step in execution_order)}

Parallel Opportunities:
{chr(10).join(f"- Steps {', '.join(map(str, group))} can run in parallel" for group in parallel_opportunities)}

Ready to proceed to Phase 4: Implementation Planning."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Dependency mapping completed successfully")
        print(f"PLAN: Total steps: {len(execution_order)}")
        print(f"🚫 Blocking steps: {len(blocking_steps)}")
        print(f"⚡ Parallel opportunities: {len(parallel_opportunities)}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in dependency mapping: {e}")
        state.status = "error_dependency_mapping"
        state.error_message = f"Dependency mapping failed: {str(e)}"
        return state
