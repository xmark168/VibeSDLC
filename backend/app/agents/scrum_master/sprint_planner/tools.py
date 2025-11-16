"""Tools for Sprint Planner Agent.

These tools handle the complete sprint planning workflow:
- Receive and transform PO output
- Calculate acceptance criteria and estimates
- Check Definition of Ready
- Assign tasks to team members
- Validate sprint capacity
- Check task dependencies
- Calculate resource balance
- Export to Kanban
"""

from langchain_core.tools import tool
from typing import Annotated, Dict, List
from datetime import datetime

# Try to import models, with fallback for script execution
try:
    from ..models import (
        SprintDB, BacklogItemDB, DoRCheckResult, AssignmentResult,
        ItemType, ItemStatus, TaskType, SprintStatus
    )
    from ..test_data import MOCK_TEAM
except (ImportError, ValueError):
    # Fallback: define minimal stubs for script execution
    class SprintDB:
        pass
    class BacklogItemDB:
        pass
    class DoRCheckResult:
        pass
    class AssignmentResult:
        pass
    class ItemType:
        pass
    class ItemStatus:
        pass
    class TaskType:
        pass
    class SprintStatus:
        pass
    MOCK_TEAM = {}


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


# ==================== PLANNING WORKFLOW TOOLS ====================
# These tools were moved from scrum_master/tools.py
# They belong to Sprint Planner, not Scrum Master


@tool
def receive_po_output(sprint_plan: dict) -> Annotated[dict, "Transform PO output to database format"]:
    """Receive Sprint Plan from Product Owner and transform to database format.

    This is a Sprint Planner responsibility - receiving and transforming planning data.

    Args:
        sprint_plan: Sprint Plan JSON from PO with:
            - metadata: Product info
            - prioritized_backlog: List of backlog items
            - sprints: List of sprints with assigned items

    Returns:
        dict: Transformed data with sprints, backlog_items, summary
    """
    print("\n" + "="*80)
    print("📥 SPRINT PLANNER: Receive PO Output")
    print("="*80)

    try:
        metadata = sprint_plan.get("metadata", {})
        prioritized_backlog = sprint_plan.get("prioritized_backlog", [])
        sprints_data = sprint_plan.get("sprints", [])

        print(f"\n📊 Input:")
        print(f"  - Product: {metadata.get('product_name', 'Unknown')}")
        print(f"  - Items: {len(prioritized_backlog)}")
        print(f"  - Sprints: {len(sprints_data)}")

        # Transform sprints
        sprints_db = []
        for idx, sprint_data in enumerate(sprints_data, start=1):
            sprint_number = sprint_data.get("sprint_number")
            if sprint_number is None:
                sprint_id = sprint_data.get("sprint_id", "")
                if "-" in sprint_id:
                    try:
                        sprint_number = int(sprint_id.split("-")[-1])
                    except ValueError:
                        sprint_number = idx
                else:
                    sprint_number = idx

            sprint_name = sprint_data.get("sprint_name", f"Sprint {sprint_number}")

            sprint = SprintDB(
                id=sprint_data["sprint_id"],
                project_id="project-001",
                name=sprint_name,
                number=sprint_number,
                goal=sprint_data["sprint_goal"],
                status=SprintStatus.PLANNED,
                start_date=None,
                end_date=None,
                velocity_plan=sprint_data.get("velocity_plan", 0),
                velocity_actual=0
            )
            sprints_db.append(sprint)

        # Transform backlog items
        backlog_items_db = []
        for item in prioritized_backlog:
            sprint_id = None
            for sprint_data in sprints_data:
                if item["id"] in sprint_data.get("assigned_items", []):
                    sprint_id = sprint_data["sprint_id"]
                    break

            backlog_item = BacklogItemDB(
                id=item["id"],
                sprint_id=sprint_id,
                parent_id=item.get("parent_id"),
                type=ItemType(item["type"]),
                title=item["title"],
                description=item.get("description", ""),
                status=ItemStatus.BACKLOG,
                reviewer_id=None,
                assignee_id=None,
                rank=item.get("rank", 0),
                estimate_value=item.get("estimate_value"),
                story_point=item.get("story_point"),
                pause=False,
                deadline=None,
                acceptance_criteria=item.get("acceptance_criteria", []),
                dependencies=item.get("dependencies", []),
                labels=item.get("labels", []),
                task_type=TaskType(item["task_type"]) if item.get("task_type") else None
            )
            backlog_items_db.append(backlog_item)

        summary = {
            "total_sprints": len(sprints_db),
            "total_items": len(backlog_items_db),
            "items_by_type": {
                "Epic": len([i for i in backlog_items_db if i.type == ItemType.EPIC]),
                "User Story": len([i for i in backlog_items_db if i.type == ItemType.USER_STORY]),
                "Task": len([i for i in backlog_items_db if i.type == ItemType.TASK]),
                "Sub-task": len([i for i in backlog_items_db if i.type == ItemType.SUB_TASK])
            },
            "total_story_points": sum(i.story_point or 0 for i in backlog_items_db),
            "total_estimate_hours": sum(i.estimate_value or 0 for i in backlog_items_db)
        }

        print(f"\n✅ Transformed:")
        print(f"  - Sprints: {summary['total_sprints']}")
        print(f"  - Items: {summary['total_items']}")

        return {
            "success": True,
            "sprints": [s.model_dump() for s in sprints_db],
            "backlog_items": [i.model_dump() for i in backlog_items_db],
            "summary": summary
        }

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sprints": [],
            "backlog_items": [],
            "summary": {}
        }


@tool
def calculate_acceptance_criteria_and_estimates(
    backlog_items: list[dict]
) -> Annotated[dict, "Calculate AC and estimates with LLM"]:
    """Calculate acceptance criteria and estimates using LLM.

    This is Sprint Planner logic - enriching backlog items.

    Args:
        backlog_items: List of items to enrich

    Returns:
        dict: Updated items with AC and estimates
    """
    print("\n" + "="*80)
    print("🧮 SPRINT PLANNER: Calculate AC & Estimates")
    print("="*80)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import os
    import json

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    updated_items = []

    for item in backlog_items:
        if item["type"] == "Epic":
            updated_items.append(item)
            continue

        print(f"\n📝 {item['id']}: {item['title']}")

        description = item.get('description', '').strip()
        if not description:
            print(f"  ⚠️ No description - using defaults")
            item["acceptance_criteria"] = [
                f"Complete {item['title']}",
                "Code review passed",
                "Tests passing"
            ]
            if item["type"] == "User Story":
                item["story_point"] = 3
            else:
                item["estimate_value"] = 3
                item["estimate_unit"] = "hours"
            updated_items.append(item)
            continue

        prompt = f"""Create acceptance criteria and estimate for:

**Type:** {item['type']}
**Title:** {item['title']}
**Description:** {description}

Return JSON:
{{
  "acceptance_criteria": ["criterion 1", "criterion 2", ...],
  "estimate_value": <number>,
  "estimate_unit": "hours" or "story_points"
}}"""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            item["acceptance_criteria"] = result["acceptance_criteria"]

            if item["type"] == "User Story":
                item["story_point"] = result["estimate_value"]
                print(f"  ✅ SP: {result['estimate_value']}")
            else:
                item["estimate_value"] = result["estimate_value"]
                item["estimate_unit"] = "hours"
                print(f"  ✅ Est: {result['estimate_value']}h")

        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            item["acceptance_criteria"] = ["To be defined"]
            if item["type"] == "User Story":
                item["story_point"] = 3
            else:
                item["estimate_value"] = 4
                item["estimate_unit"] = "hours"

        updated_items.append(item)

    print(f"\n📊 Processed: {len(updated_items)} items")

    return {
        "updated_items": updated_items,
        "total_processed": len(updated_items)
    }


@tool
def check_definition_of_ready(
    backlog_items: list[dict]
) -> Annotated[dict, "Check DoR for all items"]:
    """Check Definition of Ready for backlog items.

    This is Sprint Planner validation logic.

    Args:
        backlog_items: Items to validate

    Returns:
        dict: DoR check results
    """
    print("\n" + "="*80)
    print("✅ SPRINT PLANNER: Check Definition of Ready")
    print("="*80)

    results = []

    for item in backlog_items:
        issues = []
        recommendations = []

        if not item.get("title"):
            issues.append("Missing title")
        if not item.get("description"):
            issues.append("Missing description")
            recommendations.append("Add description")

        if item["type"] in ["User Story", "Task"]:
            ac = item.get("acceptance_criteria", [])
            if not ac:
                issues.append("Missing acceptance criteria")
                recommendations.append("Add AC")

        if item["type"] == "User Story":
            if not item.get("story_point"):
                issues.append("Missing story_point")
        elif item["type"] in ["Task", "Sub-task"]:
            if not item.get("estimate_value"):
                issues.append("Missing estimate")

        dependencies = item.get("dependencies", [])
        if dependencies:
            all_ids = [i["id"] for i in backlog_items]
            for dep_id in dependencies:
                if dep_id not in all_ids:
                    issues.append(f"Dependency {dep_id} not found")

        result = DoRCheckResult(
            item_id=item["id"],
            passed=len(issues) == 0,
            issues=issues,
            recommendations=recommendations
        )
        results.append(result)

        status = "✅" if result.passed else "❌"
        print(f"{status} {item['id']}")
        if issues:
            for issue in issues:
                print(f"  ⚠️ {issue}")

    passed = len([r for r in results if r.passed])
    failed = len([r for r in results if not r.passed])

    print(f"\n📊 DoR: {passed}/{len(results)} passed")

    return {
        "results": [r.model_dump() for r in results],
        "passed_count": passed,
        "failed_count": failed,
        "pass_rate": passed / len(results) if results else 0
    }


@tool
def assign_tasks_to_team(
    backlog_items: list[dict],
    team: dict = None
) -> Annotated[dict, "Assign tasks to team members"]:
    """Assign tasks to team members based on task_type.

    This is Sprint Planner assignment logic.

    Args:
        backlog_items: Items to assign
        team: Team members (default: MOCK_TEAM)

    Returns:
        dict: Assignment results
    """
    print("\n" + "="*80)
    print("👥 SPRINT PLANNER: Assign Tasks")
    print("="*80)

    if team is None:
        team = MOCK_TEAM

    assignments = []
    updated_items = []

    dev_counter = 0
    qa_counter = 0

    for item in backlog_items:
        if item["type"] not in ["Task", "Sub-task"]:
            updated_items.append(item)
            continue

        task_type = item.get("task_type")
        reviewer = team["reviewers"][0]

        if task_type == "Development":
            assignee = team["developers"][dev_counter % len(team["developers"])]
            dev_counter += 1
            reason = "Development task"
        elif task_type == "Testing":
            assignee = team["testers"][qa_counter % len(team["testers"])]
            qa_counter += 1
            reason = "Testing task"
        elif task_type == "Design":
            assignee = team["designers"][0]
            reason = "Design task"
        else:
            assignee = team["developers"][dev_counter % len(team["developers"])]
            dev_counter += 1
            reason = "General task"

        item["assignee_id"] = assignee["id"]
        item["reviewer_id"] = reviewer["id"]
        item["status"] = "Ready"
        updated_items.append(item)

        assignment = AssignmentResult(
            item_id=item["id"],
            assignee_id=assignee["id"],
            assignee_name=assignee["name"],
            reviewer_id=reviewer["id"],
            reviewer_name=reviewer["name"],
            status=ItemStatus.READY,
            reason=reason
        )
        assignments.append(assignment)

        print(f"\n✅ {item['id']}")
        print(f"  👤 {assignee['name']}")
        print(f"  👁️  {reviewer['name']}")

    print(f"\n📊 Assigned: {len(assignments)} tasks")

    return {
        "assignments": [a.model_dump() for a in assignments],
        "updated_items": updated_items,
        "total_assigned": len(assignments)
    }