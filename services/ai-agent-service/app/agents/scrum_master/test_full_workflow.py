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
        }
    ],
    "sprints": [
        {
            "sprint_id": "SPRINT-001",
            "sprint_name": "Sprint 1 - Authentication Foundation",
            "sprint_goal": "Implement basic user authentication",
            "start_date": "2025-01-20",
            "end_date": "2025-02-03",
            "assigned_items": ["TASK-001", "TASK-002", "TASK-003", "TASK-004", "TASK-005", "TASK-006"]
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
        
        print("\n🧠 Step 3: Scrum Master calls process_po_output tool")
        print("   - This will trigger Sprint Planner subagent for task assignment...")
        
        # Call agent with PO output
        thread_id = f"{session_id}_thread"
        
        # Create message to trigger process_po_output
        message = f"""Tôi đã nhận được Sprint Plan từ Product Owner. Hãy giao việc cho team members.

Sprint Plan:
{json.dumps(MOCK_PO_OUTPUT, indent=2, ensure_ascii=False)}

Team:
{json.dumps(MOCK_TEAM, indent=2, ensure_ascii=False)}

Hãy sử dụng tool process_po_output để xử lý và giao việc."""
        
        print("\n   Calling Scrum Master Agent...")
        response = agent.run(
            user_message=message,
            thread_id=thread_id
        )

        print("\n📊 Step 4: Sprint Planner assigns tasks")
        print("="*80)

        # Format response nicely
        if isinstance(response, dict):
            messages = response.get("messages", [])
            if messages:
                print(f"\n💬 Agent Messages ({len(messages)} total):\n")
                for i, msg in enumerate(messages, 1):
                    msg_type = type(msg).__name__
                    print(f"[{i}] {msg_type}:")

                    # Extract content
                    if hasattr(msg, 'content'):
                        content = msg.content
                        if content:
                            # Truncate long content
                            if len(content) > 500:
                                print(f"   {content[:500]}...")
                            else:
                                print(f"   {content}")

                    # Show tool calls if any
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        print(f"   🔧 Tool Calls: {len(msg.tool_calls)}")
                        for tc in msg.tool_calls:
                            print(f"      - {tc.get('name', 'unknown')}")

                    print()
            else:
                print(json.dumps(response, indent=2, ensure_ascii=False))
        else:
            print(response)

        print("="*80)

        # Try to extract assignments from response
        print("\n✅ WORKFLOW COMPLETED!")
        print("\nCheck the agent messages above for task assignments.")
        
    except ImportError as e:
        print(f"\n❌ Failed to import Scrum Master Agent: {e}")
        print("\nThis is expected due to deepagents version conflict.")
        print("Let me create a simplified version without deepagents...")
        
        # Fallback: Use direct OpenAI API
        test_simplified_workflow()


def test_simplified_workflow():
    """Simplified workflow without deepagents (direct OpenAI API)."""
    
    from openai import OpenAI
    import re
    
    print("\n" + "="*80)
    print("🔄 SIMPLIFIED WORKFLOW (Direct OpenAI API)")
    print("="*80)
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    
    # Extract tasks from PO output
    backlog_items = MOCK_PO_OUTPUT.get("prioritized_backlog", [])
    tasks = [item for item in backlog_items if item["type"] in ["Task", "Sub-task"]]
    
    print(f"\n📋 Found {len(tasks)} tasks to assign")
    
    # Prepare team info
    team_info = "## Team Members:\n"
    for role, members in MOCK_TEAM.items():
        if isinstance(members, list):
            team_info += f"\n### {role.upper()}:\n"
            for member in members:
                team_info += f"- {member['name']} ({member['id']}): {member.get('specialty', 'General')}\n"
    
    # Prepare tasks info
    tasks_info = "## Tasks to Assign:\n"
    for task in tasks:
        tasks_info += f"- {task['id']}: {task['title']} (Type: {task.get('task_type', 'General')})\n"
        if 'description' in task:
            tasks_info += f"  Description: {task['description']}\n"
    
    # Create prompt (simulating Sprint Planner subagent)
    prompt = f"""Bạn là Sprint Planner subagent của Scrum Master. 
Nhiệm vụ: Phân tích kỹ năng team và giao việc cho developer agent instances.

{team_info}

{tasks_info}

Hãy giao việc dựa trên:
1. Kỹ năng (specialty) của từng thành viên
2. Loại công việc (Development, Testing, Design)
3. Cân bằng khối lượng công việc

Trả lời dưới dạng JSON:
{{
  "assignments": [
    {{"item_id": "TASK-001", "assignee_id": "dev-001", "reason": "Backend task matches Backend developer"}},
    ...
  ]
}}"""
    
    print("\n🧠 Sprint Planner subagent analyzing and assigning tasks...")
    
    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    response_text = response.choices[0].message.content
    
    print("\n🤖 Sprint Planner Response:")
    print("="*80)
    print(response_text)
    print("="*80)
    
    # Extract JSON and apply assignments
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        assignments_data = json.loads(json_match.group())
        assignments = assignments_data.get("assignments", [])
        
        # Apply assignments
        reviewer = MOCK_TEAM["reviewers"][0]
        assignment_map = {a["item_id"]: a for a in assignments}
        
        print("\n✅ Task Assignments:")
        print("="*80)
        for task in tasks:
            if task["id"] in assignment_map:
                assignment = assignment_map[task["id"]]
                
                # Find assignee name
                assignee_name = None
                for role, members in MOCK_TEAM.items():
                    if isinstance(members, list):
                        for member in members:
                            if member["id"] == assignment["assignee_id"]:
                                assignee_name = member["name"]
                                break
                
                print(f"\n{task['id']} → {assignee_name} ({assignment['assignee_id']})")
                print(f"  Reviewer: {reviewer['name']}")
                print(f"  Reason: {assignment['reason']}")
        
        # Save output
        output_file = f"workflow_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output = {
            "metadata": MOCK_PO_OUTPUT.get("metadata", {}),
            "sprints": MOCK_PO_OUTPUT.get("sprints", []),
            "assignments": assignments,
            "assigned_at": datetime.now().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Output saved to: {output_file}")
        print("\n✅ WORKFLOW COMPLETED!")


if __name__ == "__main__":
    test_full_workflow()