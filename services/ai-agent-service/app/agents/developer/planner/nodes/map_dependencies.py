"""
Map Dependencies Node

PHASE 2: Simplified Dependency Mapping for Chain of Vibe methodology
"""

import json

from langchain_core.messages import AIMessage

from ..state import DependencyMapping, PlannerState


def map_dependencies(state: PlannerState) -> PlannerState:
    """
    Map Dependencies node - PHASE 2: Simplified dependency mapping for Chain of Vibe.

    Tasks:
    1. Create basic dependency structure for Chain of Vibe methodology
    2. Set up simple execution order
    3. Prepare for plan generation phase

    Args:
        state: PlannerState with task_requirements

    Returns:
        Updated PlannerState with basic dependency_mapping populated
    """
    print("\n" + "=" * 80)
    print("🔗 MAP DEPENDENCIES NODE - Phase 2: Simplified Dependency Mapping")
    print("=" * 80)

    try:
        task_requirements = state.task_requirements

        print(
            f"🎯 Creating basic dependency mapping for task: {task_requirements.task_id}"
        )

        # Create simplified execution order for Chain of Vibe methodology
        execution_order = [
            {
                "step": 1,
                "action": "Setup and preparation",
                "reason": "Initialize development environment and dependencies",
                "blocking": True,
                "depends_on": [],
                "files": [],
            },
            {
                "step": 2,
                "action": "Core implementation",
                "reason": "Implement main functionality",
                "blocking": True,
                "depends_on": [1],
                "files": [],
            },
            {
                "step": 3,
                "action": "Integration and testing",
                "reason": "Integrate components and validate functionality",
                "blocking": False,
                "depends_on": [2],
                "files": [],
            },
        ]

        # Identify blocking steps
        blocking_steps = [step["step"] for step in execution_order if step["blocking"]]

        # Identify parallel opportunities
        parallel_opportunities = []
        non_blocking_steps = [
            step["step"] for step in execution_order if not step["blocking"]
        ]
        if len(non_blocking_steps) > 1:
            parallel_opportunities.append(non_blocking_steps)

        # Create simplified dependencies structure
        dependencies = {
            "external": [],  # Will be populated by Chain of Vibe planning
            "internal": [],  # Will be populated by Chain of Vibe planning
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
            "phase": "Simplified Dependency Mapping",
            "total_steps": len(execution_order),
            "blocking_steps": len(blocking_steps),
            "parallel_opportunities": len(parallel_opportunities),
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 2: Simplified Dependency Mapping - COMPLETED

Mapping Results:
{json.dumps(mapping_result, indent=2)}

Basic Execution Order:
{chr(10).join(f"{step['step']}. {step['action']} ({'BLOCKING' if step['blocking'] else 'NON-BLOCKING'})" for step in execution_order)}

Parallel Opportunities:
{chr(10).join(f"- Steps {', '.join(map(str, group))} can run in parallel" for group in parallel_opportunities) if parallel_opportunities else "- No parallel opportunities identified"}

Ready to proceed to Phase 3: Chain of Vibe Implementation Planning."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Simplified dependency mapping completed successfully")
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
