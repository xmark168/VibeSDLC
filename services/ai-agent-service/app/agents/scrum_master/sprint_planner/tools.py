"""Tools for Sprint Planner Agent."""

from langchain_core.tools import tool
from typing import Annotated


@tool
def validate_sprint_capacity(
    team_capacity: dict,
    required_effort: float
) -> Annotated[dict, "Validation result for sprint capacity"]:
    """Validate if team capacity is sufficient for planned work.

    Args:
        team_capacity: Dictionary with capacity in hours per role
            Example: {"dev_hours": 80, "qa_hours": 40, "design_hours": 20}
        required_effort: Total effort required in hours

    Returns:
        dict: Validation result with status and details
    """
    try:
        total_capacity = sum(team_capacity.values())
        utilization = (required_effort / total_capacity) if total_capacity > 0 else 0

        # Calculate status
        if utilization <= 0.7:
            status = "underutilized"
            recommendation = "Consider adding more work or reducing sprint length"
        elif utilization <= 0.85:
            status = "optimal"
            recommendation = "Capacity utilization is good"
        elif utilization <= 1.0:
            status = "tight"
            recommendation = "Consider adding buffer or removing low-priority items"
        else:
            status = "overloaded"
            recommendation = "Reduce scope - team is overcommitted"

        return {
            "valid": utilization <= 1.0,
            "status": status,
            "total_capacity": total_capacity,
            "required_effort": required_effort,
            "utilization": round(utilization, 2),
            "available_buffer": max(0, total_capacity - required_effort),
            "recommendation": recommendation
        }

    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@tool
def check_task_dependencies(
    tasks: list[dict],
    daily_breakdown: list[dict]
) -> Annotated[dict, "Dependency validation result"]:
    """Check if task dependencies are properly sequenced in the plan.

    Args:
        tasks: List of tasks with dependencies field
        daily_breakdown: Daily breakdown showing when tasks are scheduled

    Returns:
        dict: Dependency validation result
    """
    try:
        conflicts = []

        # Build schedule map: task_id -> day_number
        task_schedule = {}
        for day_item in daily_breakdown:
            day = day_item.get("day")
            for planned_task in day_item.get("planned_tasks", []):
                task_id = planned_task.get("task_id")
                task_schedule[task_id] = day

        # Check each task's dependencies
        for task in tasks:
            task_id = task.get("id")
            dependencies = task.get("dependencies", [])

            if not dependencies:
                continue

            task_day = task_schedule.get(task_id)
            if task_day is None:
                conflicts.append({
                    "task_id": task_id,
                    "issue": "Task not found in schedule",
                    "severity": "high"
                })
                continue

            # Check each dependency
            for dep_id in dependencies:
                dep_day = task_schedule.get(dep_id)

                if dep_day is None:
                    conflicts.append({
                        "task_id": task_id,
                        "dependency_id": dep_id,
                        "issue": "Dependency not found in schedule",
                        "severity": "high"
                    })
                elif dep_day >= task_day:
                    conflicts.append({
                        "task_id": task_id,
                        "dependency_id": dep_id,
                        "issue": f"Task scheduled on day {task_day} but depends on task on day {dep_day}",
                        "severity": "critical"
                    })

        return {
            "valid": len(conflicts) == 0,
            "conflicts": conflicts,
            "total_conflicts": len(conflicts)
        }

    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@tool
def calculate_resource_balance(
    resource_allocation: dict
) -> Annotated[dict, "Resource balance analysis"]:
    """Calculate how well resources are balanced.

    Args:
        resource_allocation: Dictionary with resource allocations
            Example: {"developer": {"total_hours": 80, "allocated_hours": 75}}

    Returns:
        dict: Balance analysis with scores
    """
    try:
        balances = []
        total_utilization = 0
        overloaded_resources = []
        underutilized_resources = []

        for resource_name, allocation in resource_allocation.items():
            total = allocation.get("total_hours", 0)
            allocated = allocation.get("allocated_hours", 0)

            if total == 0:
                continue

            utilization = allocated / total
            total_utilization += utilization

            balance_info = {
                "resource": resource_name,
                "total_hours": total,
                "allocated_hours": allocated,
                "utilization": round(utilization, 2),
                "available": total - allocated
            }

            if utilization > 1.0:
                balance_info["status"] = "overloaded"
                overloaded_resources.append(resource_name)
            elif utilization < 0.6:
                balance_info["status"] = "underutilized"
                underutilized_resources.append(resource_name)
            else:
                balance_info["status"] = "balanced"

            balances.append(balance_info)

        avg_utilization = total_utilization / len(resource_allocation) if resource_allocation else 0

        # Calculate balance score (0-1)
        # Score is high when resources are evenly utilized between 70-90%
        variance = sum(
            abs(b["utilization"] - avg_utilization) for b in balances
        ) / len(balances) if balances else 0

        balance_score = max(0, 1 - variance)

        return {
            "balance_score": round(balance_score, 2),
            "average_utilization": round(avg_utilization, 2),
            "balances": balances,
            "overloaded_resources": overloaded_resources,
            "underutilized_resources": underutilized_resources,
            "recommendations": _generate_balance_recommendations(
                overloaded_resources,
                underutilized_resources
            )
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def _generate_balance_recommendations(
    overloaded: list[str],
    underutilized: list[str]
) -> list[str]:
    """Generate recommendations for resource balancing."""
    recommendations = []

    if overloaded:
        recommendations.append(
            f"Consider redistributing work from overloaded resources: {', '.join(overloaded)}"
        )

    if underutilized:
        recommendations.append(
            f"Assign more work to underutilized resources: {', '.join(underutilized)}"
        )

    if overloaded and underutilized:
        recommendations.append(
            "Move tasks from overloaded to underutilized resources where skills match"
        )

    if not overloaded and not underutilized:
        recommendations.append("Resource allocation is well balanced")

    return recommendations


@tool
def export_to_kanban(
    sprint_plan: dict
) -> Annotated[dict, "Kanban board export"]:
    """Export sprint plan to Kanban board format.

    Args:
        sprint_plan: Complete sprint plan

    Returns:
        dict: Kanban board structure
    """
    try:
        kanban_board = {
            "sprint_id": sprint_plan.get("sprint_id"),
            "sprint_goal": sprint_plan.get("sprint_goal"),
            "columns": {
                "To Do": [],
                "In Progress": [],
                "Done": []
            }
        }

        # Extract all tasks from daily breakdown
        daily_breakdown = sprint_plan.get("daily_breakdown", [])
        for day_item in daily_breakdown:
            for task in day_item.get("planned_tasks", []):
                card = {
                    "id": task.get("task_id"),
                    "title": task.get("task_title"),
                    "assigned_to": task.get("assigned_to"),
                    "estimated_hours": task.get("estimated_hours"),
                    "planned_day": day_item.get("day"),
                    "status": "To Do"
                }
                kanban_board["columns"]["To Do"].append(card)

        return {
            "success": True,
            "kanban_board": kanban_board,
            "total_cards": len(kanban_board["columns"]["To Do"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
