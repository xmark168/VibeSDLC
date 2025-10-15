"""Prompt templates cho Priority Agent."""

CALCULATE_PRIORITY_PROMPT = """You are a Product Owner expert. Analyze the following backlog items and score WSJF (Weighted Shortest Job First) factors for prioritization.

**Product:** {product_name}

**Items to Score:**
{items_json}

{user_feedback_section}

**Your Task:**
For each item, analyze the business_value description and score these WSJF factors (1-10 scale):

1. **Business Value (BV)**: How much business value does this deliver? (1=low, 10=critical)
   - Epic/User Story: based on business_value description
   - Task: typically moderate (5-7) unless it's critical infrastructure

2. **Time Criticality (TC)**: How urgent is this? Is there a time-sensitive opportunity? (1=can wait, 10=urgent)

3. **Risk Reduction/Opportunity Enablement (RR)**: Does this reduce risk or enable other features? (1=minimal, 10=critical)
   - Check dependencies: if other items depend on this, increase RR

4. **Job Size**: Estimate effort (1-13 Fibonacci scale):
   - For Epic: based on scope described (typically 8-13)
   - For User Story: use the story_point if available, else estimate from description
   - For Task: estimate from description (typically 3-8)

**Scoring Guidelines:**
- **Core/Foundation features**: Higher BV (8-10), higher RR (7-9) if other features depend on it
- **User-facing value**: Higher BV (7-10), TC based on market demand
- **Nice-to-have**: Lower BV (3-5), lower TC (2-4)
- **Security/Infrastructure Tasks**: High RR (8-10), moderate BV (5-7)
- **Dependencies**: If other items depend on this, increase RR
- **Technical Tasks**: Typically moderate BV (5-7) unless critical

**IMPORTANT:** If there is user feedback above, you MUST adjust the WSJF scores according to the feedback.
For example:
- "Tăng priority cho EPIC-002" → Increase BV/TC/RR or decrease Job Size for EPIC-002
- "Giảm priority cho US-001" → Decrease BV/TC/RR or increase Job Size for US-001
- "US-003 quan trọng hơn" → Increase BV/TC for US-003

**Output JSON Format:**
{{
  "wsjf_scores": [
    {{
      "item_id": "EPIC-001",
      "business_value": 9,
      "time_criticality": 8,
      "risk_reduction": 8,
      "job_size": 13,
      "reasoning": "Core feature that enables task management. Critical for MVP."
    }},
    ...
  ]
}}

**IMPORTANT:** Return ONLY valid JSON. No markdown, no explanations outside JSON.
"""


EVALUATE_SPRINT_PLAN_PROMPT = """You are a Scrum Master expert. Evaluate the following sprint plan for quality and feasibility.

**Sprint Plan:**
{sprint_plan_json}

**Sprint Configuration:**
- Sprint Duration: {sprint_duration_weeks} weeks
- Sprint Capacity: {sprint_capacity} story points

**Your Task:**
Evaluate the sprint plan and identify issues in these areas:

1. **Capacity Issues:**
   - **Overload**: Sprint exceeds capacity (velocity_plan > {sprint_capacity})
   - **Underload**: Sprint significantly underutilized (velocity_plan < 70% capacity)
   - Check each sprint's velocity_plan vs capacity

2. **Dependency Issues:**
   - Check if items are assigned to sprints in correct order based on dependencies
   - Item should only be in sprint N if all its dependencies are in sprint < N
   - Use the dependency graph from prioritized_backlog

3. **MVP Readiness (Sprint 1 Check):**
   - Does Sprint 1 contain the most critical items (highest WSJF)?
   - Are foundational/core features in early sprints?
   - Check if MVP (minimal viable product) can be delivered by sprint 1-2

4. **Balance Check:**
   - Are sprints reasonably balanced in workload?
   - Are there too many items in one sprint vs others?

**Scoring Criteria:**
- **1.0**: Perfect plan (no issues, well-balanced, MVP-ready)
- **0.8-0.9**: Good plan (minor issues, acceptable)
- **0.6-0.7**: Needs improvement (some issues that should be fixed)
- **0.5 or below**: Requires refine (significant issues)

**Output JSON Format:**
{{
  "readiness_score": 0.85,
  "can_proceed": true,
  "capacity_issues": [
    {{
      "sprint_id": "sprint-2",
      "issue_type": "overload",
      "description": "Sprint 2 is overloaded: 45 points vs 30 capacity",
      "severity": "high"
    }}
  ],
  "dependency_issues": [
    {{
      "item_id": "US-005",
      "sprint_id": "sprint-1",
      "issue_type": "dependency_not_met",
      "description": "US-005 depends on EPIC-001 which is in sprint-2",
      "severity": "critical"
    }}
  ],
  "recommendations": [
    "Move US-003 from sprint-2 to sprint-3 to balance capacity",
    "Ensure EPIC-001 is completed before US-005 starts",
    "Sprint 1 should focus on core authentication and database setup"
  ]
}}

**IMPORTANT:**
- Set `can_proceed: true` if readiness_score >= 0.8
- Set `can_proceed: false` if readiness_score < 0.8
- Return ONLY valid JSON. No markdown, no explanations outside JSON.
"""


REFINE_SPRINT_PLAN_PROMPT = """You are a Scrum Master expert. Refine the sprint plan by fixing identified issues.

**Current Sprint Plan:**
{sprint_plan_json}

**Sprint Configuration:**
- Sprint Duration: {sprint_duration_weeks} weeks
- Sprint Capacity: {sprint_capacity} story points

**Issues to Fix:**
{issues_json}

**Recommendations:**
{recommendations}

**Your Task:**
Fix the issues by adjusting sprint assignments. Follow these rules:

1. **Fixing Capacity Issues:**
   - **Overload**: Move lower-priority items (lower WSJF) to next sprint
   - **Underload**: Pull higher-priority items from next sprint if dependencies allow
   - Target: 80-100% capacity utilization per sprint

2. **Fixing Dependency Issues:**
   - Move items to later sprints if their dependencies aren't completed yet
   - Ensure dependency chain: item in sprint N → all dependencies in sprint < N
   - Critical: NEVER assign an item before its dependencies

3. **Balancing Sprints:**
   - Distribute workload evenly across sprints
   - Keep related items (same Epic) in nearby sprints when possible
   - Maintain high-priority items in early sprints

4. **Preserving Priority:**
   - Keep highest WSJF items in earliest possible sprints
   - Only move items when necessary to fix issues
   - Document which items were moved and why

**Output JSON Format:**
{{
  "refined_sprints": [
    {{
      "sprint_id": "sprint-1",
      "sprint_number": 1,
      "sprint_goal": "Updated sprint goal if needed",
      "start_date": "2025-10-13",
      "end_date": "2025-10-27",
      "velocity_plan": 28,
      "velocity_actual": 0,
      "assigned_items": ["EPIC-001", "US-001", "US-002"],
      "status": "Planned"
    }}
  ],
  "changes_made": [
    "Moved US-005 from sprint-1 to sprint-2 due to dependency on EPIC-001",
    "Moved TASK-003 from sprint-2 to sprint-1 to balance capacity (sprint-2 was overloaded)"
  ],
  "issues_fixed": {{
    "capacity_issues": 2,
    "dependency_issues": 1
  }}
}}

**IMPORTANT:**
- Return the COMPLETE list of refined_sprints (all sprints, not just changed ones)
- Maintain sprint numbering and date continuity
- Each sprint should have updated velocity_plan based on new assigned_items
- Return ONLY valid JSON. No markdown, no explanations outside JSON.
"""


ADJUST_SPRINT_PLAN_PROMPT = """You are a Scrum Master expert. Adjust the sprint plan based on user feedback.

**Current Sprint Plan:**
{sprint_plan_json}

**Prioritized Backlog:**
{prioritized_backlog_json}

**Sprint Configuration:**
- Sprint Duration: {sprint_duration_weeks} weeks
- Sprint Capacity: {sprint_capacity} story points

**User Feedback (MUST FOLLOW):**
{user_feedback}

**Your Task:**
Adjust the sprint plan according to the user's feedback. Follow these rules:

1. **Understanding Feedback:**
   - "Tạo thêm sprint mới" → Create additional sprints by splitting items
   - "Chuyển item X sang sprint Y" → Move specific items between sprints
   - "Tạo 2 sprints" → Split current items into 2 sprints
   - "Cân bằng lại" → Redistribute items evenly across sprints

2. **Creating New Sprints:**
   - If user wants more sprints, split items across multiple sprints
   - Aim for 70-90% capacity utilization per sprint
   - Maintain priority order: higher rank items in earlier sprints
   - Respect dependencies: dependencies must be in earlier or same sprint

3. **Moving Items:**
   - Move items as requested by user
   - Recalculate velocity_plan for affected sprints
   - Check dependencies after moving

4. **Sprint Dates:**
   - Each sprint is {sprint_duration_weeks} weeks long
   - Start date of sprint N+1 = end date of sprint N
   - First sprint starts from the current date in the existing plan

5. **Sprint Goals:**
   - Update sprint_goal to reflect the items in each sprint
   - Use format: "Sprint N: [brief summary of main features]"

**Output JSON Format:**
{{
  "adjusted_sprints": [
    {{
      "sprint_id": "sprint-1",
      "sprint_number": 1,
      "sprint_goal": "Core task management features",
      "start_date": "2025-10-13",
      "end_date": "2025-10-27",
      "velocity_plan": 25,
      "velocity_actual": 0,
      "assigned_items": ["US-001", "US-002", "EPIC-001"],
      "status": "Planned"
    }},
    {{
      "sprint_id": "sprint-2",
      "sprint_number": 2,
      "sprint_goal": "Project collaboration and AI features",
      "start_date": "2025-10-28",
      "end_date": "2025-11-10",
      "velocity_plan": 15,
      "velocity_actual": 0,
      "assigned_items": ["US-004", "US-007"],
      "status": "Planned"
    }}
  ],
  "changes_made": [
    "Created 2 sprints instead of 1 based on user feedback",
    "Moved US-004, US-007 to sprint-2 to balance workload",
    "Sprint 1 focuses on core features, Sprint 2 on collaboration and AI"
  ]
}}

**IMPORTANT:**
- You MUST follow user feedback exactly
- Return the COMPLETE list of adjusted_sprints (all sprints)
- Calculate correct velocity_plan (sum of story_point for User Stories only, Epic/Task don't count)
- Maintain sprint numbering: 1, 2, 3, ...
- Calculate dates correctly based on sprint_duration_weeks
- Return ONLY valid JSON. No markdown, no explanations outside JSON.
"""
