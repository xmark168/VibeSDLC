"""Tools for Scrum Master Agent.

Tools này không kết nối database - chỉ transform và validate data.
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool

from .models import (
    SprintDB, BacklogItemDB, DoRCheckResult, AssignmentResult,
    ItemType, ItemStatus, TaskType, SprintStatus
)
from .test_data import MOCK_TEAM


# ==================== TOOL 1: RECEIVE PO OUTPUT ====================

@tool
def receive_po_output(sprint_plan: dict) -> dict:
    """Receive Sprint Plan từ Product Owner và transform sang database format.
    
    Args:
        sprint_plan: Sprint Plan JSON từ Priority Agent với structure:
            - metadata: Product info
            - prioritized_backlog: List of backlog items
            - sprints: List of sprints with assigned items
    
    Returns:
        dict: Transformed data với:
            - sprints: List[SprintDB] - Ready for DB insert
            - backlog_items: List[BacklogItemDB] - Ready for DB insert
            - summary: Statistics
    """
    print("\n" + "="*80)
    print("📥 RECEIVE PO OUTPUT - Transform to Database Format")
    print("="*80)
    
    try:
        # Extract data
        metadata = sprint_plan.get("metadata", {})
        prioritized_backlog = sprint_plan.get("prioritized_backlog", [])
        sprints_data = sprint_plan.get("sprints", [])
        
        print(f"\n📊 Input Summary:")
        print(f"  - Product: {metadata.get('product_name', 'Unknown')}")
        print(f"  - Total Items: {len(prioritized_backlog)}")
        print(f"  - Total Sprints: {len(sprints_data)}")
        
        # Transform sprints
        sprints_db = []
        for idx, sprint_data in enumerate(sprints_data, start=1):
            # Extract sprint number from sprint_id (e.g., "SPRINT-001" -> 1) or use index
            sprint_number = sprint_data.get("sprint_number")
            if sprint_number is None:
                # Try to extract from sprint_id
                sprint_id = sprint_data.get("sprint_id", "")
                if "-" in sprint_id:
                    try:
                        sprint_number = int(sprint_id.split("-")[-1])
                    except ValueError:
                        sprint_number = idx
                else:
                    sprint_number = idx

            # Use sprint_name if available, otherwise generate from number
            sprint_name = sprint_data.get("sprint_name", f"Sprint {sprint_number}")

            sprint = SprintDB(
                id=sprint_data["sprint_id"],
                project_id="project-001",  # Hardcoded
                name=sprint_name,
                number=sprint_number,
                goal=sprint_data["sprint_goal"],
                status=SprintStatus.PLANNED,
                start_date=None,  # Will be set later
                end_date=None,
                velocity_plan=sprint_data.get("velocity_plan", 0),
                velocity_actual=0
            )
            sprints_db.append(sprint)
        
        # Transform backlog items
        backlog_items_db = []
        for item in prioritized_backlog:
            # Find which sprint this item belongs to
            sprint_id = None
            for sprint_data in sprints_data:
                if item["id"] in sprint_data.get("assigned_items", []):
                    sprint_id = sprint_data["sprint_id"]
                    break
            
            # Create BacklogItemDB
            backlog_item = BacklogItemDB(
                id=item["id"],
                sprint_id=sprint_id,
                parent_id=item.get("parent_id"),
                type=ItemType(item["type"]),
                title=item["title"],
                description=item.get("description", ""),
                status=ItemStatus.BACKLOG,  # Initial status
                reviewer_id=None,  # Will be assigned by Scrum Master
                assignee_id=None,  # Will be assigned by Scrum Master
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
        
        # Summary
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
        
        print(f"\n✅ Transformation Complete:")
        print(f"  - Sprints: {summary['total_sprints']}")
        print(f"  - Items: {summary['total_items']}")
        print(f"  - Story Points: {summary['total_story_points']}")
        print(f"  - Estimate Hours: {summary['total_estimate_hours']}")
        
        return {
            "success": True,
            "sprints": [s.model_dump() for s in sprints_db],
            "backlog_items": [i.model_dump() for i in backlog_items_db],
            "summary": summary
        }
        
    except Exception as e:
        print(f"\n❌ Error transforming PO output: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sprints": [],
            "backlog_items": [],
            "summary": {}
        }


# ==================== TOOL 2: CHECK DEFINITION OF READY ====================

@tool
def check_definition_of_ready(backlog_items: list[dict]) -> dict:
    """Check Definition of Ready (DoR) cho các backlog items.
    
    DoR Criteria:
    - Has title and description
    - Has acceptance criteria (for User Story/Task)
    - Has estimate (story_point for US, estimate_value for Task/Sub-task)
    - Dependencies resolved (all dependency items exist)
    
    Args:
        backlog_items: List of backlog items (dict format)
    
    Returns:
        dict: DoR check results với:
            - results: List[DoRCheckResult]
            - passed_count: Number of items that passed
            - failed_count: Number of items that failed
    """
    print("\n" + "="*80)
    print("✅ CHECK DEFINITION OF READY (DoR)")
    print("="*80)
    
    results = []
    
    for item in backlog_items:
        issues = []
        recommendations = []
        
        # Check 1: Title and description
        if not item.get("title"):
            issues.append("Missing title")
        if not item.get("description"):
            issues.append("Missing description")
            recommendations.append("Add detailed description")
        
        # Check 2: Acceptance criteria (for User Story and Task)
        if item["type"] in ["User Story", "Task"]:
            ac = item.get("acceptance_criteria", [])
            if not ac or len(ac) == 0:
                issues.append("Missing acceptance criteria")
                recommendations.append("Add acceptance criteria in Given-When-Then format")
        
        # Check 3: Estimate
        if item["type"] == "User Story":
            if not item.get("story_point"):
                issues.append("Missing story_point estimate")
                recommendations.append("Estimate story points (Fibonacci: 1,2,3,5,8,13,21)")
        elif item["type"] in ["Task", "Sub-task"]:
            if not item.get("estimate_value"):
                issues.append("Missing estimate_value (hours)")
                recommendations.append("Estimate hours needed for this task")
        
        # Check 4: Dependencies
        dependencies = item.get("dependencies", [])
        if dependencies:
            # Check if dependency items exist
            all_item_ids = [i["id"] for i in backlog_items]
            for dep_id in dependencies:
                if dep_id not in all_item_ids:
                    issues.append(f"Dependency {dep_id} not found in backlog")
                    recommendations.append(f"Add {dep_id} to backlog or remove dependency")
        
        # Create result
        result = DoRCheckResult(
            item_id=item["id"],
            passed=len(issues) == 0,
            issues=issues,
            recommendations=recommendations
        )
        results.append(result)
        
        # Print result
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status} {item['id']} - {item['title']}")
        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
    
    passed_count = len([r for r in results if r.passed])
    failed_count = len([r for r in results if not r.passed])
    
    print(f"\n📊 DoR Summary:")
    print(f"  - Passed: {passed_count}/{len(results)}")
    print(f"  - Failed: {failed_count}/{len(results)}")
    
    return {
        "results": [r.model_dump() for r in results],
        "passed_count": passed_count,
        "failed_count": failed_count,
        "pass_rate": passed_count / len(results) if results else 0
    }


# ==================== TOOL 3: CALCULATE ACCEPTANCE CRITERIA & ESTIMATES ====================

@tool
def calculate_acceptance_criteria_and_estimates(backlog_items: list[dict]) -> dict:
    """Calculate acceptance criteria và estimated_value cho các backlog items bằng LLM.

    Công cụ này sẽ:
    1. Phân tích từng backlog item (Task, Sub-task, User Story)
    2. Generate acceptance criteria dựa trên title và description
    3. Estimate effort (hours cho Task, story points cho User Story)
    4. Cập nhật items với thông tin đã calculate

    Args:
        backlog_items: List of backlog items cần calculate

    Returns:
        dict: Updated items với acceptance_criteria và estimates
    """
    print("\n" + "="*80)
    print("🧮 CALCULATE ACCEPTANCE CRITERIA & ESTIMATES")
    print("="*80)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import os
    import json

    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    updated_items = []

    for item in backlog_items:
        # Skip Epic (không cần acceptance criteria)
        if item["type"] == "Epic":
            updated_items.append(item)
            continue

        print(f"\n📝 Processing: {item['id']} - {item['title']}")

        # Validate description
        description = item.get('description', '').strip()
        if not description:
            print(f"  ⚠️ Warning: No description provided for {item['id']}")
            print(f"  → Using default acceptance criteria and estimates")

            # Set default values
            item["acceptance_criteria"] = [
                f"Complete {item['title']}",
                "Code review passed",
                "Unit tests written and passing"
            ]

            if item["type"] == "User Story":
                item["story_point"] = 3  # Default medium complexity
                print(f"  ✅ Default Story Points: 3")
            else:  # Task or Sub-task
                item["estimate_value"] = 3  # Default 3 hours
                item["estimate_unit"] = "hours"
                print(f"  ✅ Default Estimate: 3 hours")

            print(f"  ✅ Default Acceptance Criteria: {len(item['acceptance_criteria'])} items")
            updated_items.append(item)
            continue

        # Prepare prompt for LLM
        prompt = f"""Bạn là Product Owner. Hãy tạo acceptance criteria và estimate cho backlog item sau:

**ID:** {item['id']}
**Type:** {item['type']}
**Title:** {item['title']}
**Description:** {description}
**Task Type:** {item.get('task_type', 'General')}

Yêu cầu:
1. **Acceptance Criteria**: Tạo 3-5 criteria rõ ràng, đo lường được (INVEST principles)
2. **Estimate**:
   - Nếu là Task/Sub-task: Estimate hours (1-8 hours, Fibonacci-like: 1, 2, 3, 5, 8)
   - Nếu là User Story: Estimate story points (Fibonacci: 1, 2, 3, 5, 8, 13, 21)

Trả về JSON format:
{{
  "acceptance_criteria": ["criterion 1", "criterion 2", ...],
  "estimate_value": <number>,
  "estimate_unit": "hours" hoặc "story_points"
}}

CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM."""

        try:
            # Call LLM
            response = llm.invoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()

            # Parse JSON (remove markdown code blocks if present)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # Update item
            item["acceptance_criteria"] = result["acceptance_criteria"]

            if item["type"] == "User Story":
                item["story_point"] = result["estimate_value"]
                print(f"  ✅ Story Points: {result['estimate_value']}")
            else:  # Task or Sub-task
                item["estimate_value"] = result["estimate_value"]
                item["estimate_unit"] = "hours"
                print(f"  ✅ Estimate: {result['estimate_value']} hours")

            print(f"  ✅ Acceptance Criteria: {len(result['acceptance_criteria'])} items")

        except Exception as e:
            print(f"  ⚠️ Error calculating for {item['id']}: {e}")
            # Set default values
            item["acceptance_criteria"] = ["To be defined"]
            if item["type"] == "User Story":
                item["story_point"] = 3  # Default
            else:
                item["estimate_value"] = 4  # Default 4 hours
                item["estimate_unit"] = "hours"

        updated_items.append(item)

    print(f"\n📊 Calculation Summary:")
    print(f"  - Total Items Processed: {len(updated_items)}")
    print(f"  - Items with Acceptance Criteria: {len([i for i in updated_items if i.get('acceptance_criteria')])}")

    return {
        "updated_items": updated_items,
        "total_processed": len(updated_items)
    }


# ==================== TOOL 4: ASSIGN TASKS TO TEAM ====================

@tool
def assign_tasks_to_team(backlog_items: list[dict], team: dict = None) -> dict:
    """Assign tasks to team members based on task_type.
    
    Assignment Logic:
    - Development tasks → Developers (round-robin)
    - Testing tasks → Testers (round-robin)
    - Design tasks → Designers
    - All tasks → Reviewer (Tech Lead)
    
    Args:
        backlog_items: List of backlog items (dict format)
        team: Team members dict (default: MOCK_TEAM)
    
    Returns:
        dict: Assignment results với:
            - assignments: List[AssignmentResult]
            - updated_items: List of items with assignee_id and reviewer_id set
    """
    print("\n" + "="*80)
    print("👥 ASSIGN TASKS TO TEAM")
    print("="*80)
    
    if team is None:
        team = MOCK_TEAM
    
    assignments = []
    updated_items = []
    
    # Round-robin counters
    dev_counter = 0
    qa_counter = 0
    
    for item in backlog_items:
        # Only assign Task and Sub-task (not Epic or User Story)
        if item["type"] not in ["Task", "Sub-task"]:
            updated_items.append(item)
            continue
        
        task_type = item.get("task_type")
        assignee = None
        reviewer = team["reviewers"][0]  # Always assign to Tech Lead
        
        # Assign based on task_type
        if task_type == "Development":
            assignee = team["developers"][dev_counter % len(team["developers"])]
            dev_counter += 1
            reason = f"Development task assigned to developer"
        elif task_type == "Testing":
            assignee = team["testers"][qa_counter % len(team["testers"])]
            qa_counter += 1
            reason = f"Testing task assigned to tester"
        elif task_type == "Design":
            assignee = team["designers"][0]
            reason = "Design task assigned to designer"
        else:
            # No specific type, assign to developer (round-robin)
            assignee = team["developers"][dev_counter % len(team["developers"])]
            dev_counter += 1
            reason = "General task assigned to developer"
        
        # Update item
        item["assignee_id"] = assignee["id"]
        item["reviewer_id"] = reviewer["id"]
        item["status"] = "Ready"  # Change status to Ready after assignment
        updated_items.append(item)
        
        # Create assignment result
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
        
        print(f"\n✅ {item['id']} - {item['title']}")
        print(f"  👤 Assignee: {assignee['name']} ({assignee['role']})")
        print(f"  👁️  Reviewer: {reviewer['name']} ({reviewer['role']})")
        print(f"  📝 Reason: {reason}")
    
    print(f"\n📊 Assignment Summary:")
    print(f"  - Total Assigned: {len(assignments)}")
    print(f"  - Developers: {dev_counter}")
    print(f"  - Testers: {qa_counter}")
    
    return {
        "assignments": [a.model_dump() for a in assignments],
        "updated_items": updated_items,
        "total_assigned": len(assignments)
    }

