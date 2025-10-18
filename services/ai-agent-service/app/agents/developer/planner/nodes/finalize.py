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
        codebase_analysis = state.codebase_analysis
        dependency_mapping = state.dependency_mapping

        print(f"🎯 Finalizing plan for: {implementation_plan.task_id}")

        # Create comprehensive final plan
        final_plan = {
            # Task Information
            "task_info": {
                "task_id": implementation_plan.task_id,
                "description": implementation_plan.description,
                "complexity_score": implementation_plan.complexity_score,
                "plan_type": implementation_plan.plan_type,
            },
            # Requirements Summary
            "requirements": {
                "functional_requirements": task_requirements.requirements,
                "acceptance_criteria": task_requirements.acceptance_criteria,
                "business_rules": task_requirements.business_rules,
                "technical_specs": task_requirements.technical_specs,
                "constraints": task_requirements.constraints,
            },
            # Implementation Guidance
            "implementation": {
                "approach": implementation_plan.approach,
                "steps": implementation_plan.implementation_steps,
                "execution_order": dependency_mapping.execution_order,
                "parallel_opportunities": dependency_mapping.parallel_opportunities,
            },
            # File Changes
            "file_changes": {
                "files_to_create": codebase_analysis.files_to_create,
                "files_to_modify": codebase_analysis.files_to_modify,
                "affected_modules": codebase_analysis.affected_modules,
            },
            # Database & API Changes
            "infrastructure": {
                "database_changes": codebase_analysis.database_changes,
                "api_endpoints": codebase_analysis.api_endpoints,
                "external_dependencies": codebase_analysis.external_dependencies,
                "internal_dependencies": codebase_analysis.internal_dependencies,
            },
            # Testing & Quality
            "quality_assurance": {
                "testing_requirements": implementation_plan.testing_requirements,
                "validation_score": state.validation_score,
                "rollback_plan": implementation_plan.rollback_plan,
            },
            # Project Management
            "project_info": {
                "estimated_hours": implementation_plan.total_estimated_hours,
                "story_points": implementation_plan.story_points,
                "risks": implementation_plan.risks,
                "assumptions": implementation_plan.assumptions,
            },
            # Metadata
            "metadata": {
                "planner_version": "1.0",
                "planning_iterations": state.current_iteration,
                "validation_passed": state.can_proceed,
                "created_by": "planner_subagent",
            },
        }

        # Add subtasks for complex plans
        if implementation_plan.plan_type == "complex":
            final_plan["implementation"]["subtasks"] = implementation_plan.subtasks
            final_plan["implementation"]["execution_strategy"] = (
                implementation_plan.execution_strategy
            )

        # Update state
        state.final_plan = final_plan
        state.ready_for_implementation = True
        state.status = "finalized"
        state.current_phase = "finalize"

        # Create summary statistics
        summary_stats = {
            "total_files_affected": len(codebase_analysis.files_to_create)
            + len(codebase_analysis.files_to_modify),
            "implementation_steps": len(implementation_plan.implementation_steps),
            "estimated_effort": f"{implementation_plan.total_estimated_hours} hours ({implementation_plan.story_points} story points)",
            "complexity_level": get_complexity_level(
                implementation_plan.complexity_score
            ),
            "risk_level": get_risk_level(implementation_plan.risks),
            "validation_score": f"{state.validation_score:.1%}",
        }

        # Add final AI message
        ai_message = AIMessage(
            content=f"""🎯 PLANNING COMPLETED - Ready for Implementation

Plan Summary:
{json.dumps(summary_stats, indent=2)}

Implementation Approach:
{implementation_plan.approach.get("strategy", "Standard implementation approach") if isinstance(implementation_plan.approach, dict) else "Standard implementation approach"}

Key Implementation Steps:
{chr(10).join(f"{i + 1}. {step.get('title', step.get('action', f'Step {i + 1}'))}" for i, step in enumerate(implementation_plan.implementation_steps[:5])) if implementation_plan.implementation_steps else "No implementation steps defined"}
{f"... and {len(implementation_plan.implementation_steps) - 5} more steps" if len(implementation_plan.implementation_steps) > 5 else ""}

Files to be Changed:
- Create: {len(codebase_analysis.files_to_create)} files
- Modify: {len(codebase_analysis.files_to_modify)} files

Effort Estimate: {implementation_plan.total_estimated_hours} hours ({implementation_plan.story_points} story points)

SUCCESS: Plan is ready for handoff to Implementor Agent"""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Plan finalization completed successfully")
        print(
            f"INFO: Complexity: {implementation_plan.complexity_score}/10 ({get_complexity_level(implementation_plan.complexity_score)})"
        )
        print(f"📁 Files affected: {summary_stats['total_files_affected']}")
        print(
            f"PLAN: Implementation steps: {len(implementation_plan.implementation_steps)}"
        )
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


def get_risk_level(risks: list) -> str:
    """Get overall risk level assessment."""
    if not risks:
        return "Low"

    high_impact_risks = [r for r in risks if r.get("impact") == "high"]
    if high_impact_risks:
        return "High"

    medium_impact_risks = [r for r in risks if r.get("impact") == "medium"]
    if len(medium_impact_risks) > 1:
        return "Medium-High"
    elif medium_impact_risks:
        return "Medium"

    return "Low"
