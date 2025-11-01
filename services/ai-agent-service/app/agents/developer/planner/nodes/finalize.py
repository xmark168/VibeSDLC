"""
Finalize Node

Prepare final output for implementor subagent
"""

import json

from langchain_core.messages import AIMessage

from ..state import PlannerState


def finalize(state: PlannerState) -> PlannerState:
    """
    Finalize node - Prepare final output for implementor subagent.

    Tasks:
    1. Create structured final plan output
    2. Include all necessary information for implementor
    3. Set ready_for_implementation flag
    4. Create summary message

    Args:
        state: PlannerState với validated implementation_plan

    Returns:
        Updated PlannerState với final_plan ready for implementor
    """
    print("\n" + "=" * 80)
    print("🎯 FINALIZE NODE - Prepare Output for Implementor")
    print("=" * 80)

    try:
        implementation_plan = state.implementation_plan
        task_requirements = state.task_requirements
        dependency_mapping = state.dependency_mapping

        print(f"🎯 Finalizing plan for: {implementation_plan.task_id}")

        # Validate implementation_plan before creating final_plan
        if not implementation_plan.task_id or not implementation_plan.description:
            print("❌ ERROR: Empty or invalid implementation_plan detected")
            print(f"   Task ID: '{implementation_plan.task_id}'")
            print(f"   Description: '{implementation_plan.description}'")
            print(f"   Steps: {len(implementation_plan.steps)}")
            print("   This indicates generate_plan node failed to create valid plan")

            state.status = "error_empty_implementation_plan"
            state.error_message = "Cannot finalize: implementation_plan is empty or invalid. Check generate_plan node for errors."
            state.ready_for_implementation = False

            # Create empty final_plan to indicate failure
            state.final_plan = {}

            print("❌ FINALIZE FAILED: Empty implementation plan")
            return state

        # Create simplified final plan with flat structure
        final_plan = {
            # Top-level simplified structure
            "task_id": implementation_plan.task_id,
            "description": implementation_plan.description,
            "complexity_score": implementation_plan.complexity_score,
            "plan_type": implementation_plan.plan_type,
            # Functional requirements
            "functional_requirements": implementation_plan.functional_requirements,
            # Implementation steps with simplified structure
            "steps": [
                {
                    "step": step.step,
                    "title": step.title,
                    "description": step.description,
                    "category": step.category,
                    "sub_steps": step.sub_steps,
                }
                for step in implementation_plan.steps
            ],
            # Infrastructure changes as simple objects
            "database_changes": implementation_plan.database_changes,
            "external_dependencies": implementation_plan.external_dependencies,
            "internal_dependencies": implementation_plan.internal_dependencies,
            # Metadata
            "story_points": implementation_plan.story_points,
            "execution_order": implementation_plan.execution_order,
        }

        # Update state
        state.final_plan = final_plan
        state.ready_for_implementation = True
        state.status = "finalized"
        state.current_phase = "finalize"

        # Create summary statistics
        summary_stats = {
            "implementation_steps": len(implementation_plan.steps),
            "estimated_effort": f"{implementation_plan.story_points} story points",
            "complexity_level": get_complexity_level(
                implementation_plan.complexity_score
            ),
            "validation_score": f"{state.validation_score:.1%}",
        }

        # Add final AI message
        ai_message = AIMessage(
            content=f"""🎯 CHAIN OF VIBE PLANNING COMPLETED - Ready for Implementation

Plan Summary:
{json.dumps(summary_stats, indent=2)}

Key Implementation Steps (Chain of Vibe):
{chr(10).join(f"{step.step}. {step.title}" for step in implementation_plan.steps[:5]) if implementation_plan.steps else "No implementation steps defined"}
{f"... and {len(implementation_plan.steps) - 5} more steps" if len(implementation_plan.steps) > 5 else ""}

Infrastructure Changes:
- Database: {len(implementation_plan.database_changes)} changes
- Dependencies: {len(implementation_plan.external_dependencies)} external

Effort Estimate: {implementation_plan.story_points} story points

SUCCESS: Chain of Vibe plan is ready for handoff to Implementor Agent"""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Chain of Vibe plan finalization completed successfully")
        print(
            f"INFO: Complexity: {implementation_plan.complexity_score}/10 ({get_complexity_level(implementation_plan.complexity_score)})"
        )
        print(f"PLAN: Implementation steps: {len(implementation_plan.steps)}")
        print(f"TIME:  Estimated effort: {summary_stats['estimated_effort']}")
        print(f"🎯 Ready for Implementation: {state.ready_for_implementation}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in plan finalization: {e}")
        state.status = "error_finalization"
        state.error_message = f"Plan finalization failed: {str(e)}"
        return state


def get_complexity_level(complexity_score: int) -> str:
    """Get human-readable complexity level."""
    if complexity_score <= 2:
        return "Low"
    elif complexity_score <= 4:
        return "Medium-Low"
    elif complexity_score <= 6:
        return "Medium"
    elif complexity_score <= 8:
        return "Medium-High"
    else:
        return "High"


# Removed get_risk_level function - not used in simplified Chain of Vibe structure
