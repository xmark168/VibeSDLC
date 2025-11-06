"""Prompts for Sprint Planner Agent - LangGraph workflow.

This module contains all prompts used in the Sprint Planner Agent workflow:
- ENRICH_VALIDATION_PROMPT: Validate and enrich backlog items
- VERIFY_VALIDATION_PROMPT: Verify enriched data validity
- FEEDBACK_PROMPT: Handle user feedback when verification fails
"""

# ============================================================================
# ENRICH VALIDATION PROMPT - Phase 1: Validate and Enrich Data
# ============================================================================

ENRICH_VALIDATION_PROMPT = """Bạn là Sprint Planner Expert. Nhiệm vụ của bạn là validate và enrich backlog items.

**Backlog Items:**
{backlog_items}

**Sprints:**
{sprints}

**Current Issues (nếu có từ loop trước):**
{current_issues}

**Nhiệm vụ của bạn:**

1. **Validate mỗi item:**
   - Check title không trống
   - Check description không trống
   - Check acceptance_criteria không trống (nếu là User Story hoặc Task)
   - Check story_point hoặc estimate_value không null
   - Check dependencies tồn tại trong backlog
   - Check không có circular dependencies
   - Check parent_id tồn tại (nếu có)

2. **Enrich null/empty fields:**
   - Nếu acceptance_criteria trống → tạo AC dựa trên title và description
   - Nếu story_point null → estimate dựa trên complexity
   - Nếu estimate_value null → estimate dựa trên task type
   - Nếu labels trống → suggest labels dựa trên task type

3. **Identify issues:**
   - Severity: critical (blocking), high (important), medium (should fix), low (nice to have)
   - Mỗi issue phải có: item_id, issue_type, field_name, current_value, expected_value, message, severity

**Output Format (ONLY JSON, no markdown):**
```json
{{
  "validation_issues": [
    {{
      "item_id": "ITEM-001",
      "issue_type": "null_field",
      "field_name": "acceptance_criteria",
      "current_value": null,
      "expected_value": ["AC 1", "AC 2"],
      "message": "Missing acceptance criteria for User Story",
      "severity": "high"
    }}
  ],
  "enriched_items": [
    {{
      "item_id": "ITEM-001",
      "enriched_fields": {{
        "acceptance_criteria": ["AC 1", "AC 2"],
        "story_point": 5,
        "labels": ["backend", "api"]
      }}
    }}
  ]
}}
```

**IMPORTANT:**
- Return ONLY valid JSON
- No markdown code blocks
- No explanations outside JSON
- enriched_items MUST contain ALL items from backlog
"""

# ============================================================================
# VERIFY VALIDATION PROMPT - Phase 2: Verify Data Validity
# ============================================================================

VERIFY_VALIDATION_PROMPT = """Bạn là Sprint Planner Expert. Nhiệm vụ của bạn là verify tính hợp lệ của enriched data.

**Enriched Items:**
{enriched_items}

**Validation Issues:**
{validation_issues}

**Sprints:**
{sprints}

**Nhiệm vụ của bạn:**

1. **Check Critical Issues:**
   - Có critical issues nào chưa được fix không?
   - Có blocking issues nào không?
   - Có circular dependencies không?

2. **Assess Data Quality:**
   - Tất cả items có đủ thông tin không?
   - Acceptance criteria có rõ ràng không?
   - Estimates có hợp lý không?
   - Dependencies có valid không?

3. **Calculate Readiness Score (0.0 - 1.0):**

   **Công thức tính:**
   - Bắt đầu với base_score = 1.0
   - Trừ điểm cho mỗi vấn đề:
     * Critical issue: -0.15 mỗi issue
     * High severity issue: -0.10 mỗi issue
     * Medium severity issue: -0.05 mỗi issue
     * Low severity issue: -0.02 mỗi issue
   - Minimum score = 0.0

   **Ví dụ:**
   - 0 issues → score = 1.0 (perfect)
   - 1 medium issue → score = 0.95 (excellent)
   - 2 medium issues → score = 0.90 (very good)
   - 1 high + 2 medium → score = 0.80 (good, can proceed)
   - 2 high + 3 medium → score = 0.65 (needs improvement)
   - 1 critical + 2 high → score = 0.55 (not ready)

   **Ngưỡng quyết định:**
   - 0.85-1.0: Excellent - Ready to proceed
   - 0.75-0.84: Good - Ready with minor issues
   - 0.50-0.74: Fair - Needs more enrichment
   - 0.0-0.49: Poor - Many critical issues

4. **Identify Blocking Issues:**
   - Issues that MUST be fixed before proceeding (critical/high severity)
   - Issues that CAN be fixed later (medium/low severity)

**Output Format (ONLY JSON, no markdown):**
```json
{{
  "is_valid": true,
  "can_proceed": true,
  "readiness_score": 0.88,
  "critical_issues_count": 0,
  "blocking_issues": [],
  "recommendations": [
    "Consider adding more acceptance criteria to ITEM-005",
    "Review dependencies for ITEM-008 - might be too complex"
  ]
}}
```

**IMPORTANT - DECISION RULES:**

1. **Tính readiness_score CHÍNH XÁC:**
   - Đếm số lượng issues theo severity
   - Áp dụng công thức trừ điểm như trên
   - Đảm bảo score nằm trong khoảng 0.0 - 1.0

2. **Quyết định can_proceed:**
   - Set `can_proceed: true` if readiness_score >= 0.75 AND critical_issues_count == 0
     * Cho phép proceed với minor/medium issues (sẽ fix trong sprint)
     * Chỉ critical issues mới block
   - Set `can_proceed: false` if readiness_score < 0.75 OR critical_issues_count > 0
     * Cần enrichment loop khác để fix issues

3. **Lưu ý:**
   - Nếu KHÔNG có validation_issues → readiness_score = 1.0, can_proceed = true
   - Nếu chỉ có low/medium issues → score cao (0.8-0.95), can_proceed = true
   - Return ONLY valid JSON, no markdown, no explanations
"""

# ============================================================================
# FEEDBACK PROMPT - Phase 3: Handle User Feedback
# ============================================================================

FEEDBACK_PROMPT = """Bạn là Sprint Planner Expert. Nhiệm vụ của bạn là xử lý feedback từ user.

**Current State:**
- Status: {status}
- Total Issues: {total_issues}
- Critical Issues: {critical_issues_count}

**Validation Issues:**
{validation_issues}

**User Feedback:**
{user_feedback}

**Nhiệm vụ của bạn:**

1. **Analyze Feedback:**
   - User muốn approve hay fix?
   - Nếu fix, user muốn fix cái gì?
   - Có suggestions từ user không?

2. **Generate Action Plan:**
   - Nếu approve: Proceed to assignment
   - Nếu fix: Suggest fixes cho từng issue
   - Nếu unclear: Ask for clarification

3. **Update Issues:**
   - Mark issues as "acknowledged"
   - Suggest resolutions
   - Prioritize fixes

**Output Format (ONLY JSON, no markdown):**
```json
{{
  "action": "proceed" | "fix" | "clarify",
  "reasoning": "User approved despite minor issues",
  "suggested_fixes": [
    {{
      "issue_id": "ITEM-001",
      "suggested_fix": "Add more specific acceptance criteria",
      "priority": "high"
    }}
  ],
  "next_step": "proceed_to_assignment"
}}
```

**IMPORTANT:**
- Return ONLY valid JSON
- No markdown code blocks
- No explanations outside JSON
"""

# ============================================================================
# LEGACY PROMPTS (kept for backward compatibility)
# ============================================================================

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

⚠️ **QUAN TRỌNG**:
- CHỈ được làm việc với các tasks đã có trong Sprint Backlog Items ở trên
- KHÔNG ĐƯỢC tự ý tạo thêm tasks mới
- KHÔNG ĐƯỢC thêm hoặc bỏ bất kỳ task nào
- CHỈ được enrich metadata cho các tasks hiện có

Nhiệm vụ của bạn:
1. **Daily Breakdown**: Phân phối tasks trên các ngày sprint
   - Consider dependencies giữa các tasks
   - Balance workload trên các team members
   - Để lại buffer cho reviews và blockers

2. **Resource Allocation**: Assign tasks cho các team members
   - Match task types với skills (dev, qa, design)
   - Respect capacity limits
   - Consider parallel work nếu có thể

3. **Task Enrichment**: Tính toán thêm các fields cho mỗi task HIỆN CÓ
   - **rank**: Thứ tự ưu tiên (1, 2, 3, ...) dựa trên dependencies và priority
   - **story_point**: Độ phức tạp (Fibonacci: 1, 2, 3, 5, 8, 13, 21)
   - **deadline**: Deadline cụ thể (YYYY-MM-DD) dựa trên daily breakdown
   - **status**: Initial status ("TODO", "READY", "BACKLOG")
   - ⚠️ enriched_tasks PHẢI chứa TẤT CẢ và CHỈ các task_id từ Sprint Backlog Items

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