# 🎯 Scrum Master Agents - Architecture & Guide

## Overview

The Scrum Master Agent system is a **Deep Agent** architecture with a **Sprint Planner sub-agent** that automates Agile sprint management workflows. It processes Product Owner output, validates readiness, assigns tasks, and creates detailed sprint plans.

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│         ScrumMasterAgent (Deep Agent)                   │
│         - Main orchestrator                             │
│         - Processes PO output                           │
│         - Manages team assignments                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📥 Tools:                                              │
│  ├─ plan_sprint (calls Sprint Planner sub-agent)        │
│  ├─ process_po_output (main workflow)                   │
│  ├─ get_sprint_status (status tracking)                 │
│  └─ update_sprint_task (task updates)                   │
│                                                         │
│  🔄 Sub-Agent:                                          │
│  └─ SprintPlannerAgent (LangGraph workflow)             │
│     ├─ initialize: Validate inputs & capacity          │
│     ├─ generate: Create daily breakdown                │
│     ├─ evaluate: Check plan quality                    │
│     ├─ refine: Improve based on feedback               │
│     ├─ finalize: Create summary & export               │
│     └─ preview: Show for approval                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Main Agent: ScrumMasterAgent

### Purpose
Orchestrates the entire Scrum Master workflow:
1. Receives Sprint Plan from Product Owner Agent
2. Transforms data to database format
3. Validates Definition of Ready (DoR)
4. Assigns tasks to team members
5. Exports database-ready output

### Key Features

#### 1. **Deep Agent Architecture**
- Uses `deepagents` framework with OpenAI gpt-4o
- Manages complex multi-step workflows
- Integrates with Sprint Planner sub-agent

#### 2. **Tools**

**plan_sprint()**
- Creates detailed sprint plans from backlog items
- Orchestrates entire Sprint Planner workflow
- Returns: sprint_plan, status, plan_score, daily_breakdown, resource_allocation

**process_po_output()**
- Main workflow: receive → validate → assign → export
- Transforms PO output to database format
- Checks Definition of Ready
- Assigns tasks to team members
- Returns: database-ready output with assignments

**get_sprint_status()**
- Retrieves current sprint status
- TODO: Implement sprint status tracking

**update_sprint_task()**
- Updates task status (To Do, In Progress, Done)
- TODO: Implement task status updates

#### 3. **Models**

**SprintDB**
- Sprint record matching database schema
- Fields: id, project_id, name, number, goal, status, start_date, end_date, velocity_plan, velocity_actual

**BacklogItemDB**
- Backlog item record matching database schema
- Fields: id, sprint_id, parent_id, type, title, description, status, assignee_id, reviewer_id, estimate_value, story_point, deadline

**ScrumMasterOutput**
- Final output ready for database insert
- Contains: sprints, backlog_items, assignments, dor_results, summary

### Usage Example

```python
from app.agents.scrum_master import create_scrum_master_agent

# Create agent
agent = create_scrum_master_agent(
    session_id="session-123",
    user_id="user-456"
)

# Run agent
result = agent.chat("Plan sprint-1 with these backlog items...")

# Or use specific tool
sprint_plan = agent.run(
    user_message="Create a sprint plan for sprint-1"
)
```

---

## 🔄 Sub-Agent: SprintPlannerAgent

### Purpose
Creates detailed sprint plans using LangGraph workflow with 6 nodes and conditional branching.

### Workflow Nodes

#### 1. **Initialize Node**
- Validates sprint inputs
- Calculates total effort
- Checks team capacity
- Status: initialized

#### 2. **Generate Node**
- Creates daily breakdown
- Allocates resources
- Uses GENERATE_PROMPT
- Status: generated

#### 3. **Evaluate Node**
- Scores plan quality (0-1)
- Checks capacity issues
- Identifies dependency conflicts
- Validates with tools
- Status: evaluated

#### 4. **Refine Node** (Conditional)
- Improves plan based on feedback
- Addresses capacity issues
- Resolves dependencies
- Uses REFINE_PROMPT
- Status: refined

#### 5. **Finalize Node**
- Creates summary
- Exports to Kanban
- Uses FINALIZE_PROMPT
- Status: finalized

#### 6. **Preview Node**
- Shows plan for approval
- Auto-approves if score >= 0.8
- Auto-edits if score < 0.8
- Status: preview/completed

### Workflow Logic

```
initialize → generate → evaluate ─┐
                           ↑       │
                           └─ refine (if score < 0.8)
                                   │
                                   ↓
                              finalize → preview ─┐
                                           ↑       │
                                           └─ edit (if rejected)
```

### Configuration

- **Max Loops**: 2 (prevent infinite refinement)
- **Quality Threshold**: 0.8 (80% score to finalize)
- **Model**: OpenAI gpt-4o
- **Temperature**: 0.2 (balanced reasoning)

### Usage Example

```python
from app.agents.scrum_master.sprint_planner import SprintPlannerAgent

# Create agent
planner = SprintPlannerAgent(
    session_id="session-123",
    user_id="user-456"
)

# Run workflow
result = planner.run(
    sprint_id="sprint-1",
    sprint_goal="Build authentication system",
    sprint_backlog_items=[
        {
            "id": "TASK-001",
            "title": "Implement login API",
            "effort": 5,
            "type": "development"
        }
    ],
    sprint_duration_days=14,
    team_capacity={"dev_hours": 80, "qa_hours": 40}
)

# Returns
# {
#     "sprint_plan": {...},
#     "status": "completed",
#     "plan_score": 0.85,
#     "daily_breakdown": [...],
#     "resource_allocation": {...}
# }
```

---

## 📊 Data Models

### Enums

**SprintStatus**: Planned, Active, Completed
**ItemType**: Epic, User Story, Task, Sub-task
**ItemStatus**: Backlog, Ready, In Progress, Done
**TaskType**: Development, Testing, Design, Documentation, DevOps

### Key Models

**SprintDB**
```python
{
    "id": "sprint-1",
    "project_id": "project-001",
    "name": "Sprint 1",
    "number": 1,
    "goal": "Build authentication",
    "status": "Planned",
    "start_date": "2025-10-16",
    "end_date": "2025-10-30",
    "velocity_plan": 40,
    "velocity_actual": 0
}
```

**BacklogItemDB**
```python
{
    "id": "TASK-001",
    "sprint_id": "sprint-1",
    "type": "Task",
    "title": "Implement login API",
    "description": "Create REST API for user login",
    "status": "Ready",
    "assignee_id": "user-001",
    "reviewer_id": "user-002",
    "estimate_value": 5.0,
    "deadline": "2025-10-25",
    "acceptance_criteria": ["API returns JWT token", "Handles invalid credentials"],
    "dependencies": ["TASK-002"],
    "labels": ["backend", "authentication"]
}
```

---

## 🔧 Tools

### Sprint Planner Tools

**validate_sprint_capacity()**
- Validates team capacity vs required effort
- Returns: valid, recommendation

**check_task_dependencies()**
- Checks for dependency conflicts
- Returns: valid, conflicts, total_conflicts

**calculate_resource_balance()**
- Calculates resource utilization
- Returns: balance_score, overloaded_resources

**export_to_kanban()**
- Exports sprint plan to Kanban format
- Returns: success, total_cards

### Scrum Master Tools

**receive_po_output()**
- Transforms PO output to database format
- Returns: backlog_items, sprints, summary

**check_definition_of_ready()**
- Validates DoR for all items
- Returns: results, pass_rate

**assign_tasks_to_team()**
- Assigns tasks to team members
- Uses round-robin assignment
- Returns: assignments, updated_items, total_assigned

---

## 📝 Prompts

All prompts are centralized in `app/templates/prompts/scrum_master/`:

- **INITIALIZE_PROMPT**: Validate sprint backlog & team capacity
- **GENERATE_PROMPT**: Create daily breakdown & resource allocation
- **EVALUATE_PROMPT**: Evaluate plan quality against criteria
- **REFINE_PROMPT**: Refine plan based on evaluation feedback
- **FINALIZE_PROMPT**: Finalize and prepare for export

---

## 🚀 Getting Started

### 1. Create Agent
```python
from app.agents.scrum_master import create_scrum_master_agent

agent = create_scrum_master_agent(
    session_id="session-123",
    user_id="user-456"
)
```

### 2. Plan Sprint
```python
result = agent.run(
    user_message="Plan sprint-1 with authentication tasks"
)
```

### 3. Process PO Output
```python
po_output = {
    "metadata": {...},
    "prioritized_backlog": [...],
    "sprints": [...]
}

result = agent.chat(f"Process this sprint plan: {po_output}")
```

---

## 📊 Output Format

### Sprint Plan Output
```python
{
    "sprint_plan": {
        "sprint_id": "sprint-1",
        "daily_breakdown": [...],
        "resource_allocation": {...}
    },
    "status": "completed",
    "plan_score": 0.85,
    "daily_breakdown": [...],
    "resource_allocation": {...}
}
```

### Scrum Master Output
```python
{
    "sprints": [SprintDB, ...],
    "backlog_items": [BacklogItemDB, ...],
    "assignments": [AssignmentResult, ...],
    "dor_results": [DoRCheckResult, ...],
    "summary": {
        "total_sprints": 1,
        "total_items": 10,
        "dor_pass_rate": 0.9,
        "total_assigned": 10,
        "processed_at": "2025-10-16T10:00:00"
    }
}
```

---

## 🔗 File Structure

```
app/agents/scrum_master/
├── __init__.py
├── scrum_master_agent.py (Main Deep Agent)
├── models.py (Pydantic models)
├── tools.py (Scrum Master tools)
├── test_data.py (Mock data)
├── example_usage.py (Usage examples)
│
└── sprint_planner/
    ├── __init__.py
    ├── agent.py (LangGraph workflow)
    ├── state.py (State definition)
    ├── prompts.py (Prompt imports)
    ├── tools.py (Sprint Planner tools)
    └── test_data.py (Test data)
```

---

## 🎓 Key Concepts

### Deep Agent
- Orchestrates complex workflows
- Manages sub-agents
- Integrates multiple tools
- Uses Claude 3.5 Sonnet

### LangGraph
- State machine workflow
- Conditional branching
- Node-based execution
- Supports loops and refinement

### Definition of Ready (DoR)
- Validates backlog items before sprint
- Checks acceptance criteria
- Verifies dependencies
- Ensures clarity and completeness

### Task Assignment
- Round-robin assignment
- Considers team capacity
- Matches task type to role
- Balances workload

---

## 📞 Support

### Questions?
1. Check `example_usage.py` for usage examples
2. Check `models.py` for data structure
3. Check `sprint_planner/agent.py` for workflow details

### Issues?
1. Check test data in `test_data.py`
2. Run example scripts
3. Check logs for error messages

---

## 🔄 Integration Points

### With Product Owner Agent
- Receives Sprint Plan output
- Processes and validates
- Returns database-ready format

### With Database
- Output format matches database schema
- Ready for direct insert
- No transformation needed

### With Kanban Board
- Exports sprint plan to Kanban format
- Creates cards for each task
- Sets up workflow columns

---

**Status:** ✅ Production Ready
**Last Updated:** 2025-10-16
**Framework:** deepagents + LangGraph
**Model:** OpenAI gpt-4o

