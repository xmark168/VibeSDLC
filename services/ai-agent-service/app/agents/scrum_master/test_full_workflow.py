"""
SCRUM MASTER WORKFLOW: Product Owner → Scrum Master → Sprint Planner → Task Assignment

Workflow:
1. Product Owner tạo Sprint Plan (mock data)
2. Scrum Master nhận Sprint Plan
3. Scrum Master gọi Sprint Planner subagent
4. Sprint Planner phân tích kỹ năng team và giao việc cho developer agent instances
5. Output: Tasks với assignee_id và reviewer_id

Chạy:
    python app/agents/scrum_master/test_full_workflow.py
    # hoặc từ thư mục scrum_master:
    cd app/agents/scrum_master && python test_full_workflow.py
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path (3 levels up from app/agents/scrum_master/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Check if API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY not found in environment variables!")
    sys.exit(1)

# Mock team data (Generic roles: developer, tester, designer, reviewer)
MOCK_TEAM = {
    "developers": [
        {"id": "dev-001", "name": "Alice Nguyen", "role": "developer"},
        {"id": "dev-002", "name": "Bob Tran", "role": "developer"},
        {"id": "dev-003", "name": "Charlie Le", "role": "developer"},
    ],
    "testers": [
        {"id": "qa-001", "name": "David Pham", "role": "tester"},
        {"id": "qa-002", "name": "Eve Vo", "role": "tester"},
    ],
    "designers": [
        {"id": "design-001", "name": "Frank Hoang", "role": "designer"},
    ],
    "reviewers": [
        {"id": "rev-001", "name": "Grace Nguyen", "role": "reviewer"},
    ]
}

# Mock Product Owner output (Sprint Plan đã được tạo)
MOCK_PO_OUTPUT = {
  "metadata": {
    "project_name": "E-commerce Platform",
    "created_at": "2025-01-16T10:00:00Z",
    "created_by": "Product Owner Agent"
  },
  "prioritized_backlog": [
    {
      "id": "EPIC-001",
      "type": "Epic",
      "title": "User Authentication System",
      "priority": 1
    },
    {
      "id": "US-001",
      "type": "User Story",
      "title": "As a user, I want to login to the system",
      "parent_id": "EPIC-001",
      "priority": 1
    },
    {
      "id": "TASK-001",
      "type": "Task",
      "title": "Implement login API endpoint",
      "parent_id": "US-001",
      "task_type": "Development",
      "description": "Create POST /api/auth/login endpoint with JWT token generation",
      "effort_estimate": 5
    },
    {
      "id": "TASK-002",
      "type": "Task",
      "title": "Create login UI component",
      "parent_id": "US-001",
      "task_type": "Development",
      "description": "Build React login form with email and password fields",
      "effort_estimate": 3
    },
    {
      "id": "TASK-003",
      "type": "Task",
      "title": "Write API integration tests",
      "parent_id": "US-001",
      "task_type": "Testing",
      "description": "Test login API with valid and invalid credentials",
      "effort_estimate": 2
    },
    {
      "id": "TASK-004",
      "type": "Task",
      "title": "Design login page mockup",
      "parent_id": "US-001",
      "task_type": "Design",
      "description": "Create UI/UX design for login page",
      "effort_estimate": 3
    },
    {
      "id": "US-002",
      "type": "User Story",
      "title": "As a user, I want to reset my password",
      "parent_id": "EPIC-001",
      "priority": 2
    },
    {
      "id": "TASK-005",
      "type": "Task",
      "title": "Implement password reset API",
      "parent_id": "US-002",
      "task_type": "Development",
      "description": "Create POST /api/auth/reset-password endpoint",
      "effort_estimate": 4
    },
    {
      "id": "TASK-006",
      "type": "Task",
      "title": "Write E2E tests for login flow",
      "parent_id": "US-001",
      "task_type": "Testing",
      "description": "Automated E2E tests using Playwright",
      "effort_estimate": 3
    },
    {
      "id": "TASK-007",
      "type": "Task",
      "title": "Validate user input on login form",
      "parent_id": "US-001",
      "task_type": "Development",
      "description": "Implement client-side and server-side validation for email and password fields",
      "effort_estimate": 2
    },
    {
      "id": "TASK-008",
      "type": "Task",
      "title": "Create password reset UI component",
      "parent_id": "US-002",
      "task_type": "Development",
      "description": "Build React form for entering email to receive password reset link",
      "effort_estimate": 3
    },
    {
      "id": "TASK-009",
      "type": "Task",
      "title": "Test password reset flow",
      "parent_id": "US-002",
      "task_type": "Testing",
      "description": "Write integration and E2E tests for the password reset process",
      "effort_estimate": 3
    },
    {
      "id": "TASK-010",
      "type": "Task",
      "title": "View Home Page",
      "parent_id": "EPIC-001",
      "task_type": "Design",
      "description": "Design home page layout and components",
      "effort_estimate": 2
    }
  ],
  "sprints": [
    {
      "sprint_id": "SPRINT-001",
      "sprint_name": "Sprint 1 - Authentication Foundation",
      "sprint_goal": "Implement basic user authentication",
      "start_date": "2025-01-20",
      "end_date": "2025-02-03",
      "assigned_items": [
        "TASK-001",
        "TASK-002",
        "TASK-003",
        "TASK-004",
        "TASK-005",
        "TASK-006",
        "TASK-007",
        "TASK-008",
        "TASK-009",
        "TASK-010"
      ]
    }
  ]
}



def test_full_workflow():
    """Test full workflow: PO → Scrum Master → Sprint Planner → Task Assignment."""
    
    print("\n" + "="*80)
    print("🚀 FULL WORKFLOW TEST")
    print("="*80)
    
    print("\n📋 Step 1: Product Owner creates Sprint Plan")
    print(f"   - Project: {MOCK_PO_OUTPUT['metadata']['project_name']}")
    print(f"   - Sprints: {len(MOCK_PO_OUTPUT['sprints'])}")
    print(f"   - Backlog items: {len(MOCK_PO_OUTPUT['prioritized_backlog'])}")
    
    # Extract sprint info
    sprint = MOCK_PO_OUTPUT['sprints'][0]
    print(f"\n   Sprint: {sprint['sprint_name']}")
    print(f"   Goal: {sprint['sprint_goal']}")
    print(f"   Items: {len(sprint['assigned_items'])} tasks")
    
    print("\n🤖 Step 2: Scrum Master receives Sprint Plan")
    print("   - Initializing Scrum Master Agent...")
    
    # Import Scrum Master Agent
    try:
        # Import using absolute path (works from any location)
        from app.agents.scrum_master.scrum_master_agent import create_scrum_master_agent
        
        # Create Scrum Master Agent
        session_id = f"test_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        agent = create_scrum_master_agent(
            session_id=session_id,
            user_id="test_user"
        )
        
        print("   ✅ Scrum Master Agent initialized")

        print("\n🧠 Step 3: Scrum Master processes PO output")
        print("   - Delegating to Sprint Planner...")

        # Call process_po_output directly (no more Deep Agent)
        result = agent.process_po_output(
            po_output=MOCK_PO_OUTPUT,
            team=MOCK_TEAM
        )

        print("\n📊 Step 4: Results")
        print("="*80)

        # Format response nicely
        if isinstance(result, dict):
            if result.get("success"):
                output = result.get("output", {})
                summary = result.get("summary", {})

                print(f"\n✅ Processing successful!")
                print(f"\n📈 Summary:")
                print(f"   - Sprints: {summary.get('total_sprints', 0)}")
                print(f"   - Items: {summary.get('total_items', 0)}")
                print(f"   - Assigned: {summary.get('total_assigned', 0)}")
                print(f"   - DoR Pass Rate: {summary.get('dor_pass_rate', 0):.1%}")

                # Show assignments
                assignments = output.get("assignments", [])
                if assignments:
                    print(f"\n👥 Task Assignments ({len(assignments)} total):")
                    for assignment in assignments[:10]:  # Show first 10
                        print(f"   - {assignment.get('item_id')}: {assignment.get('assignee_name')} ({assignment.get('assignee_role')})")
                    if len(assignments) > 10:
                        print(f"   ... and {len(assignments) - 10} more")
            else:
                print(f"\n❌ Processing failed: {result.get('error')}")

        print("\n" + "="*80)
        print("✅ WORKFLOW COMPLETED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()





if __name__ == "__main__":
    test_full_workflow()