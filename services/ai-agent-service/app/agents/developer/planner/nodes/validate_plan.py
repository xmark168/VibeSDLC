"""
Validate Plan Node

Validate implementation plan quality và completeness
"""

import json

from langchain_core.messages import AIMessage

from ..state import PlannerState


def validate_plan(state: PlannerState) -> PlannerState:
    """
    Validate Plan node - Validate implementation plan quality.

    Tasks:
    1. Validate plan completeness và consistency
    2. Check for missing dependencies
    3. Validate effort estimates
    4. Check risk assessment
    5. Determine if plan needs refinement

    Args:
        state: PlannerState với implementation_plan

    Returns:
        Updated PlannerState với validation results
    """
    print("\n" + "=" * 80)
    print("SUCCESS: VALIDATE PLAN NODE - Plan Quality Validation")
    print("=" * 80)

    try:
        implementation_plan = state.implementation_plan
        task_requirements = state.task_requirements

        print(f"🎯 Validating plan for: {implementation_plan.task_id}")

        # Early validation: Check if implementation_plan is empty/invalid
        if not implementation_plan.task_id or not implementation_plan.description:
            print(
                "❌ WARNING: Empty or invalid implementation_plan detected in validation"
            )
            print(f"   Task ID: '{implementation_plan.task_id}'")
            print(f"   Description: '{implementation_plan.description}'")
            print(f"   Steps: {len(implementation_plan.steps)}")
            print(
                "   This indicates generate_plan node failed - cannot validate empty plan"
            )

            # Set validation to fail immediately
            state.validation_score = 0.0
            state.validation_issues = [
                "Empty implementation plan - generate_plan node failed",
                "Cannot validate plan with empty task_id or description",
                "Check generate_plan node for errors",
            ]
            state.can_proceed = False
            state.status = "error_empty_plan_validation"
            state.current_phase = "finalize"  # Force to finalize to handle error

            print("❌ VALIDATION FAILED: Empty implementation plan")
            print("🔄 Forcing to finalize to handle error properly")
            return state

        validation_issues = []
        validation_score = 0.0

        # Validate plan completeness
        completeness_score = validate_completeness(
            implementation_plan, validation_issues
        )

        # Validate consistency
        consistency_score = validate_consistency(
            implementation_plan, state.dependency_mapping, validation_issues
        )

        # Validate effort estimates
        effort_score = validate_effort_estimates(implementation_plan, validation_issues)

        # Validate risk assessment
        risk_score = validate_risk_assessment(implementation_plan, validation_issues)

        # Calculate overall validation score
        validation_score = (
            completeness_score + consistency_score + effort_score + risk_score
        ) / 4.0

        # Update state
        state.validation_score = validation_score
        state.validation_issues = validation_issues

        # Determine if plan can proceed
        can_proceed = validation_score >= 0.7 and len(validation_issues) == 0
        state.can_proceed = can_proceed

        if can_proceed:
            state.current_phase = "finalize"
            state.status = "plan_validated"
        else:
            # Check if we can retry
            if state.current_iteration < state.max_iterations:
                state.current_iteration += 1
                state.current_phase = "analyze_codebase"  # Go back to analysis
                state.status = "plan_needs_refinement"
            else:
                state.status = "plan_validation_failed"
                state.error_message = (
                    f"Plan validation failed after {state.max_iterations} iterations"
                )

        # Add AI message
        validation_result = {
            "phase": "Plan Validation",
            "validation_score": round(validation_score, 2),
            "completeness_score": round(completeness_score, 2),
            "consistency_score": round(consistency_score, 2),
            "effort_score": round(effort_score, 2),
            "risk_score": round(risk_score, 2),
            "issues_count": len(validation_issues),
            "can_proceed": can_proceed,
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Plan Validation - COMPLETED

Validation Results:
{json.dumps(validation_result, indent=2)}

{"SUCCESS: Plan validation PASSED - Ready for finalization" if can_proceed else "ERROR: Plan validation FAILED - Needs refinement"}

{f"Issues Found: {chr(10).join(f'- {issue}' for issue in validation_issues)}" if validation_issues else "No issues found"}

{"Ready to proceed to Finalization." if can_proceed else f"Iteration {state.current_iteration}/{state.max_iterations} - Returning to analysis phase."}"""
        )

        state.messages.append(ai_message)

        print(f"INFO: Validation Score: {validation_score:.2f}/1.0")
        print(f"🔍 Issues Found: {len(validation_issues)}")
        print(f"SUCCESS: Can Proceed: {can_proceed}")
        print(f"ITER: Next Phase: {state.current_phase}")
        if not can_proceed and state.current_iteration < state.max_iterations:
            print(f"🔁 Iteration: {state.current_iteration}/{state.max_iterations}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in plan validation: {e}")
        state.status = "error_plan_validation"
        state.error_message = f"Plan validation failed: {str(e)}"
        return state


def validate_completeness(implementation_plan, validation_issues: list[str]) -> float:
    """Validate plan completeness."""
    score = 1.0

    # Check required fields
    if not implementation_plan.description:
        validation_issues.append("Missing plan description")
        score -= 0.2

    if not implementation_plan.steps:
        validation_issues.append("No implementation steps defined")
        score -= 0.3

    # Handle complexity_score - ensure it's a number
    try:
        complexity_score = (
            float(implementation_plan.complexity_score)
            if implementation_plan.complexity_score
            else 0
        )
        if complexity_score == 0:
            validation_issues.append("Complexity score not calculated")
            score -= 0.1
    except (ValueError, TypeError):
        validation_issues.append("Invalid complexity score format")
        score -= 0.1

    # Check functional requirements (simplified structure)
    if not implementation_plan.functional_requirements:
        validation_issues.append("Functional requirements not defined")
        score -= 0.2

    # Check execution order
    if not implementation_plan.execution_order:
        validation_issues.append("Execution order not specified")
        score -= 0.1

    return max(score, 0.0)


def validate_consistency(
    implementation_plan, dependency_mapping, validation_issues: list[str]
) -> float:
    """Validate plan consistency."""
    score = 1.0

    # Check step count consistency
    plan_steps = len(implementation_plan.steps)
    dependency_steps = len(dependency_mapping.execution_order)

    if plan_steps != dependency_steps:
        validation_issues.append(
            f"Step count mismatch: plan has {plan_steps}, dependencies have {dependency_steps}"
        )
        score -= 0.3

    # Check dependency references
    for step in implementation_plan.steps:
        dependencies = step.dependencies if hasattr(step, "dependencies") else []
        for dep in dependencies:
            if dep > plan_steps:
                validation_issues.append(
                    f"Step {step.step} references non-existent dependency {dep}"
                )
                score -= 0.2

    return max(score, 0.0)


def validate_effort_estimates(
    implementation_plan, validation_issues: list[str]
) -> float:
    """Validate effort estimates."""
    score = 1.0

    # Check story points
    if implementation_plan.story_points == 0:
        validation_issues.append("Story points not estimated")
        score -= 0.5

    return max(score, 0.0)


def validate_risk_assessment(
    implementation_plan, validation_issues: list[str]
) -> float:
    """Validate risk assessment (simplified for new structure)."""
    score = 1.0

    # For simplified structure, we validate based on complexity and step count
    if implementation_plan.complexity_score >= 7:
        step_count = len(implementation_plan.steps)
        if step_count < 3:
            validation_issues.append(
                "High complexity task should have at least 3 implementation steps"
            )
            score -= 0.2

        # Check if high complexity steps have proper sub-steps
        for step in implementation_plan.steps:
            if hasattr(step, "sub_steps") and len(step.sub_steps) < 2:
                validation_issues.append(
                    f"Complex step {step.step} should have multiple sub-steps"
                )
                score -= 0.1
                break

    return max(score, 0.0)
