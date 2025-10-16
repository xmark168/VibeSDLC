"""Prompts for Sprint Planner Agent - LangGraph workflow.

This module contains all prompts used in the Sprint Planner Agent workflow:
- INITIALIZE_PROMPT: Validate sprint backlog and team capacity
- GENERATE_PROMPT: Create detailed sprint plan with daily breakdown
- EVALUATE_PROMPT: Evaluate plan quality against criteria
- REFINE_PROMPT: Refine plan based on evaluation feedback
- FINALIZE_PROMPT: Finalize and prepare for export
"""

INITIALIZE_PROMPT = """Bạn đang khởi tạo sprint planning.

Sprint Information:
- Sprint ID: {sprint_id}
- Sprint Goal: {sprint_goal}
- Sprint Duration: {sprint_duration_days} days
- Team Capacity: {team_capacity}

Sprint Backlog Items:
{sprint_backlog_items}

Nhiệm vụ của bạn:
1. Validate rằng sprint backlog sẵn sàng để planning
2. Check team capacity so với total effort cần thiết
3. Xác định bất kỳ initial concerns hoặc blockers nào
4. Setup initial planning state

Trả về JSON với:
- validation_passed: bool
- capacity_status: str (ví dụ: "adequate", "tight", "overloaded")
- initial_concerns: list[str]
- planning_ready: bool
"""

GENERATE_PROMPT = """Bạn đang tạo detailed sprint plan.

Sprint Information:
- Sprint ID: {sprint_id}
- Sprint Goal: {sprint_goal}
- Duration: {sprint_duration_days} days
- Start Date: {sprint_start_date}
- Team Capacity: {team_capacity}

Sprint Backlog Items (đã được prioritized):
{sprint_backlog_items}

Nhiệm vụ của bạn:
1. **Daily Breakdown**: Phân phối tasks trên các ngày sprint
   - Consider dependencies giữa các tasks
   - Balance workload trên các team members
   - Để lại buffer cho reviews và blockers

2. **Resource Allocation**: Assign tasks cho các team members
   - Match task types với skills (dev, qa, design)
   - Respect capacity limits
   - Consider parallel work nếu có thể

3. **Task Enrichment**: Tính toán thêm các fields cho mỗi task
   - **rank**: Thứ tự ưu tiên (1, 2, 3, ...) dựa trên dependencies và priority
   - **story_point**: Độ phức tạp (Fibonacci: 1, 2, 3, 5, 8, 13, 21)
   - **deadline**: Deadline cụ thể (YYYY-MM-DD) dựa trên daily breakdown
   - **status**: Initial status ("TODO", "READY", "BACKLOG")

4. **Risk Identification**: Xác định potential risks
   - Complex tasks có thể overflow
   - Dependencies có thể gây delays
   - Capacity constraints

Trả về JSON với:
{{
  "daily_breakdown": [
    {{
      "day": 1,
      "date": "2024-01-15",
      "planned_tasks": [
        {{
          "task_id": "TASK-001",
          "task_title": "...",
          "assigned_to": "developer",
          "estimated_hours": 4,
          "status": "TODO"
        }}
      ],
      "total_hours": 8,
      "notes": "Sprint kickoff day"
    }},
    ...
  ],
  "resource_allocation": {{
    "developer": {{
      "total_hours": 80,
      "allocated_hours": 75,
      "tasks": ["TASK-001", "TASK-002", ...]
    }},
    "qa": {{
      "total_hours": 40,
      "allocated_hours": 38,
      "tasks": ["TASK-005", ...]
    }}
  }},
  "enriched_tasks": [
    {{
      "task_id": "TASK-001",
      "rank": 1,
      "story_point": 5,
      "deadline": "2024-01-17",
      "status": "TODO",
      "reasoning": "Foundation task, must complete first. Medium complexity (5 points). Due day 3."
    }},
    {{
      "task_id": "TASK-002",
      "rank": 2,
      "story_point": 3,
      "deadline": "2024-01-19",
      "status": "TODO",
      "reasoning": "Depends on TASK-001. Simple CRUD (3 points). Due day 5."
    }}
  ],
  "identified_risks": [
    "TASK-003 depends on TASK-001, potential bottleneck",
    "Limited QA capacity for integration testing"
  ]
}}
"""

EVALUATE_PROMPT = """Bạn đang evaluate quality của sprint plan.

Sprint Plan:
{sprint_plan}

Evaluate plan dựa trên các criteria này:

1. **Capacity Management** (0-10 points)
   - Team capacity có được respected không?
   - Có overloaded days không?
   - Có reasonable buffer time không?

2. **Dependency Handling** (0-10 points)
   - Task dependencies có được properly sequenced không?
   - Dependent tasks có gây delays không?
   - Có circular dependencies không?

3. **Workload Balance** (0-10 points)
   - Work có được evenly distributed trên sprint không?
   - Team members có được fairly balanced không?
   - Có work cho mọi người throughout không?

4. **Risk Coverage** (0-10 points)
   - Risks có được identified không?
   - Có mitigation plans không?
   - Có contingency time không?

Trả về JSON với:
{{
  "plan_score": 0.85,  // 0-1 normalized score
  "can_proceed": true,
  "capacity_issues": [
    {{
      "issue_type": "overload",
      "description": "Day 5 có 12 hours planned cho 8-hour capacity",
      "severity": "high",
      "affected_resource": "developer"
    }}
  ],
  "dependency_conflicts": [
    {{
      "issue_type": "sequencing",
      "description": "TASK-003 scheduled trước khi TASK-001 completes",
      "affected_tasks": ["TASK-001", "TASK-003"]
    }}
  ],
  "recommendations": [
    "Move TASK-007 từ day 5 đến day 6 để balance capacity",
    "Add 1-day buffer sau TASK-001 trước khi start TASK-003"
  ]
}}
"""

REFINE_PROMPT = """Bạn đang refine sprint plan dựa trên evaluation feedback.

Current Sprint Plan:
{sprint_plan}

Issues to Fix:
{issues}

Recommendations:
{recommendations}

Nhiệm vụ của bạn:
1. Address mỗi capacity issue bằng cách:
   - Redistribute tasks để balance load
   - Adjust time estimates nếu unrealistic
   - Move tasks across days

2. Resolve dependency conflicts bằng cách:
   - Resequence tasks properly
   - Add buffer time giữa dependencies
   - Identify tasks có thể run in parallel

3. Improve resource allocation bằng cách:
   - Balance work trên team members
   - Ensure continuous work throughout sprint
   - Avoid idle time hoặc overload

Trả về REFINED sprint plan trong cùng JSON format như original:
{{
  "daily_breakdown": [...],
  "resource_allocation": {{...}},
  "identified_risks": [...],
  "changes_made": [
    "Moved TASK-007 từ day 5 đến day 6",
    "Added 0.5 day buffer sau TASK-001",
    "Redistributed QA tasks để balance workload"
  ]
}}
"""

FINALIZE_PROMPT = """Bạn đang finalize sprint plan.

Sprint Plan:
{sprint_plan}

Nhiệm vụ của bạn:
1. **Final Validation**: Ensure tất cả issues được resolved
2. **Summary Creation**: Tạo executive summary
3. **Export Preparation**: Format cho Kanban/Jira export
4. **Communication Plan**: Prepare messaging cho team

Trả về JSON với:
{{
  "sprint_plan": {{
    "sprint_id": "{sprint_id}",
    "sprint_goal": "...",
    "duration_days": 14,
    "start_date": "2024-01-15",
    "end_date": "2024-01-28",
    "daily_breakdown": [...],
    "resource_allocation": {{...}},
    "summary": {{
      "total_tasks": 15,
      "total_story_points": 34,
      "total_hours": 120,
      "team_members": ["developer", "qa", "designer"],
      "key_milestones": [
        {{"day": 3, "milestone": "API endpoints complete"}},
        {{"day": 7, "milestone": "Sprint review checkpoint"}},
        {{"day": 14, "milestone": "Sprint demo ready"}}
      ]
    }},
    "export_format": "kanban_ready",
    "export_status": "success"
  }},
  "team_communication": {{
    "kickoff_message": "Sprint starts Monday với focus trên authentication features...",
    "daily_standup_focus": ["Check TASK-001 progress", "Review blockers"],
    "review_prep": "Demo ready vào day 13 cho day 14 review"
  }}
}}
"""
