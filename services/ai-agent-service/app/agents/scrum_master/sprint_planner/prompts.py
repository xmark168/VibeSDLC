"""Prompts for Sprint Planner Agent."""

# ==================== INITIALIZE PROMPT ====================
INITIALIZE_PROMPT = """
Validate sprint planning inputs:
- Sprint ID: {sprint_id}
- Sprint Goal: {sprint_goal}
- Duration: {sprint_duration_days} days
- Team Capacity: {team_capacity}
- Backlog Items: {sprint_backlog_items}

Check if inputs are valid and sufficient for sprint planning.
"""

# ==================== GENERATE PROMPT ====================
GENERATE_PROMPT = """
Create a detailed sprint plan with the following information:

Sprint ID: {sprint_id}
Sprint Goal: {sprint_goal}
Duration: {sprint_duration_days} days
Start Date: {sprint_start_date}
Team Capacity: {team_capacity}

Backlog Items:
{sprint_backlog_items}

IMPORTANT: For each item, fill in NULL/empty fields with reasonable values:
- rank: Priority order (1-12)
- story_point: Fibonacci points (1, 2, 3, 5, 8, 13)
- estimate_value: Estimated hours (4-40)
- task_type: One of [Development, Testing, Design, Documentation, DevOps]
- acceptance_criteria: List of acceptance criteria (at least 2-3 items)
- dependencies: List of item IDs that MUST be completed before this item.
  * For User Stories: add their parent Epic as dependency
  * For Tasks: add related items as dependencies
  * For Testing tasks: add Development tasks they depend on
  * Example: US-001 depends on EPIC-001, TASK-002 depends on US-001
- deadline: Sprint end date or earlier

Generate a JSON response with:
1. daily_breakdown: Array of daily tasks (one per day)
2. resource_allocation: Resource usage by role
3. enriched_items: Items enriched with ALL fields filled (no nulls)

Return ONLY valid JSON, no markdown or extra text.

Example format:
{{
  "daily_breakdown": [
    {{"day": 1, "tasks": ["TASK-001", "TASK-002"], "total_hours": 8}},
    {{"day": 2, "tasks": ["TASK-003"], "total_hours": 8}}
  ],
  "resource_allocation": {{"dev_hours": 80, "qa_hours": 40}},
  "enriched_items": [
    {{
      "id": "TASK-001",
      "rank": 1,
      "story_point": 5,
      "estimate_value": 10,
      "task_type": "Development",
      "acceptance_criteria": ["User can login with email", "Password is encrypted", "Session persists"],
      "dependencies": [],
      "deadline": "2025-10-20",
      "status": "planned"
    }}
  ]
}}
"""

# ==================== EVALUATE PROMPT ====================
EVALUATE_PROMPT = """
Evaluate the following sprint plan:

{sprint_plan}

Provide evaluation in JSON format with:
1. plan_score: Score from 0 to 1
2. capacity_issues: List of capacity problems
3. dependency_conflicts: List of dependency issues
4. recommendations: List of improvement suggestions

Return ONLY valid JSON.

Example format:
{{
  "plan_score": 0.85,
  "capacity_issues": [],
  "dependency_conflicts": [],
  "recommendations": ["Consider adding more QA resources"]
}}
"""

# ==================== REFINE PROMPT ====================
REFINE_PROMPT = """
Refine the sprint plan based on evaluation feedback:

{sprint_plan}

Evaluation Results:
{evaluation_results}

Provide refined plan in JSON format with same structure as generate_prompt.
Return ONLY valid JSON.
"""

# ==================== FINALIZE PROMPT ====================
FINALIZE_PROMPT = """
Finalize the sprint plan:

{sprint_plan}

Create final sprint plan JSON with all details.
Return ONLY valid JSON.
"""

# ==================== ASSIGN PROMPT ====================
ASSIGN_PROMPT = """
Assign tasks to team members based on their roles and capacity.

Enriched Items:
{enriched_items}

Team Members:
{team_members}

Assign each item to appropriate team member based on:
1. Task type (Development, Testing, Design, Documentation, DevOps)
2. Team member role and capacity
3. Story points and estimated hours

Return JSON with task_assignments array:
{{
  "task_assignments": [
    {{"item_id": "US-001", "assignee": "Alice", "role": "Developer", "estimated_hours": 16}},
    {{"item_id": "US-002", "assignee": "Bob", "role": "Developer", "estimated_hours": 10}}
  ]
}}

Return ONLY valid JSON.
"""

__all__ = [
    "INITIALIZE_PROMPT",
    "GENERATE_PROMPT",
    "EVALUATE_PROMPT",
    "REFINE_PROMPT",
    "FINALIZE_PROMPT",
    "ASSIGN_PROMPT"
]
