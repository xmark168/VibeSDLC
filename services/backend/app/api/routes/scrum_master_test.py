"""Test endpoint for Scrum Master Sprint Planner - Mock PO Agent output."""

from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.models import Project

router = APIRouter(prefix="/scrum-master-test", tags=["scrum-master-test"])


class TestSprintPlannerRequest(BaseModel):
    project_id: UUID


class TestSprintPlannerResponse(BaseModel):
    status: str
    message: str


# Mock PO Agent output data
MOCK_PO_OUTPUT = {
    "sprint_plan": {
        "sprints": [
            {
                "id": "sprint-1",
                "name": "Sprint 1 - Foundation",
                "goal": "Build core authentication and user management",
                "duration_days": 14,
                "start_date": "2025-02-01",
                "end_date": "2025-02-14"
            }
        ],
        "metadata": {
            "total_sprints": 1,
            "total_story_points": 34
        }
    },
    "backlog_items": [
        {
            "id": "ITEM-001",
            "type": "User Story",
            "parent_id": None,
            "title": "User Registration",
            "description": "As a user, I want to register an account so that I can access the platform",
            "rank": 1,
            "status": "Backlog",
            "story_point": 5,
            "estimate_value": 8.0,
            "acceptance_criteria": [
                "User can enter email and password",
                "Email validation is performed",
                "Password strength requirements are enforced",
                "Confirmation email is sent"
            ],
            "dependencies": [],
            "labels": ["backend", "authentication"],
            "task_type": "development",
            "business_value": "high"
        },
        {
            "id": "ITEM-002",
            "type": "User Story",
            "parent_id": None,
            "title": "User Login",
            "description": "As a user, I want to login to my account so that I can access my data",
            "rank": 2,
            "status": "Backlog",
            "story_point": 3,
            "estimate_value": 5.0,
            "acceptance_criteria": [
                "User can enter email and password",
                "Invalid credentials show error message",
                "Successful login redirects to dashboard",
                "Session is maintained"
            ],
            "dependencies": ["ITEM-001"],
            "labels": ["backend", "authentication"],
            "task_type": "development",
            "business_value": "high"
        },
        {
            "id": "ITEM-003",
            "type": "Task",
            "parent_id": "ITEM-001",
            "title": "Create User Database Schema",
            "description": "Design and implement user table with necessary fields",
            "rank": 3,
            "status": "Backlog",
            "story_point": 2,
            "estimate_value": 3.0,
            "acceptance_criteria": [
                "User table created with id, email, password_hash, created_at",
                "Indexes added for email lookup",
                "Migration script created"
            ],
            "dependencies": [],
            "labels": ["database", "backend"],
            "task_type": "development",
            "business_value": "medium"
        },
        {
            "id": "ITEM-004",
            "type": "Task",
            "parent_id": "ITEM-001",
            "title": "Implement Registration API",
            "description": "Create REST API endpoint for user registration",
            "rank": 4,
            "status": "Backlog",
            "story_point": 3,
            "estimate_value": 5.0,
            "acceptance_criteria": [
                "POST /api/register endpoint created",
                "Input validation implemented",
                "Password hashing implemented",
                "Returns JWT token on success"
            ],
            "dependencies": ["ITEM-003"],
            "labels": ["backend", "api"],
            "task_type": "development",
            "business_value": "high"
        },
        {
            "id": "ITEM-005",
            "type": "Task",
            "parent_id": "ITEM-002",
            "title": "Implement Login API",
            "description": "Create REST API endpoint for user login",
            "rank": 5,
            "status": "Backlog",
            "story_point": 2,
            "estimate_value": 3.0,
            "acceptance_criteria": [
                "POST /api/login endpoint created",
                "Credentials validation implemented",
                "JWT token generation on success",
                "Error handling for invalid credentials"
            ],
            "dependencies": ["ITEM-003"],
            "labels": ["backend", "api"],
            "task_type": "development",
            "business_value": "high"
        }
    ]
}


async def test_sprint_planner_background(
    project_id: UUID,
    user_id: UUID,
):
    """Test Sprint Planner with mock PO output in background."""
    from app.agents.scrum_master.scrum_master_agent import ScrumMasterAgent
    from app.api.routes.chat_ws import manager
    import traceback

    try:
        print(f"\n[TEST] Starting Sprint Planner test for project {project_id}")

        # Broadcast start message
        await manager.broadcast_to_project({
            "type": "agent_step",
            "step": "test_started",
            "agent": "Scrum Master Test",
            "message": "🧪 Testing Sprint Planner with mock PO output..."
        }, str(project_id))

        # Create Scrum Master Agent
        session_id = f"sm_test_{project_id}_{user_id}"
        scrum_master = ScrumMasterAgent(
            session_id=session_id,
            user_id=str(user_id)
        )

        # Call persist_sprint_plan with mock data
        result = await scrum_master.persist_sprint_plan(
            sprint_plan_data=MOCK_PO_OUTPUT["sprint_plan"],
            project_id=str(project_id),
            websocket_broadcast_fn=manager.broadcast_to_project
        )

        print(f"[TEST] Sprint Planner completed: {result}")

        # Broadcast completion
        await manager.broadcast_to_project({
            "type": "agent_step",
            "step": "test_completed",
            "agent": "Scrum Master Test",
            "message": f"✅ Test completed! Saved {result.get('total_sprints', 0)} sprints and {result.get('total_items', 0)} items."
        }, str(project_id))

    except Exception as e:
        error_msg = f"Sprint Planner test failed: {str(e)}\n{traceback.format_exc()}"
        print(f"[TEST ERROR] {error_msg}")

        # Broadcast error
        await manager.broadcast_to_project({
            "type": "agent_step",
            "step": "test_error",
            "agent": "Scrum Master Test",
            "message": f"❌ Test failed: {str(e)}"
        }, str(project_id))


@router.post("/test-sprint-planner", response_model=TestSprintPlannerResponse)
async def test_sprint_planner(
    request: TestSprintPlannerRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Test Sprint Planner with mock PO Agent output.
    This endpoint simulates receiving output from PO Agent and triggers Sprint Planner.
    """
    # Validate project
    project = session.get(Project, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Add background task
    background_tasks.add_task(
        test_sprint_planner_background,
        project_id=request.project_id,
        user_id=current_user.id,
    )

    return TestSprintPlannerResponse(
        status="started",
        message="Sprint Planner test started. Check WebSocket for updates."
    )
