"""Mock data for testing Scrum Master Agent without database connection."""

from datetime import datetime, timedelta

# ==================== MOCK TEAM ====================

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


# ==================== MOCK PRODUCT OWNER OUTPUT ====================

MOCK_PO_OUTPUT = {
    "metadata": {
        "product_name": "VibeSDLC Platform",
        "version": "v1.0",
        "total_sprints": 2,
        "sprint_duration_weeks": 2,
        "total_story_points": 34,
        "total_estimate_hours": 120,
        "planning_date": datetime.now().isoformat()
    },
    "prioritized_backlog": [
        # Epic
        {
            "id": "EPIC-001",
            "type": "Epic",
            "parent_id": None,
            "title": "User Authentication System",
            "description": "Complete user authentication system including login, registration, password management",
            "rank": 1,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": None,
            "acceptance_criteria": [],
            "dependencies": [],
            "labels": ["core", "authentication"],
            "task_type": None,
            "business_value": "Enable user identification and secure access"
        },
        
        # User Story 1
        {
            "id": "US-001",
            "type": "User Story",
            "parent_id": "EPIC-001",
            "title": "As a user, I want to login with email and password",
            "description": "User can login using email and password to access the application",
            "rank": 2,
            "status": "Backlog",
            "story_point": 5,
            "estimate_value": None,
            "acceptance_criteria": [
                "Given I am on the login page",
                "When I enter valid email and password",
                "Then I should be redirected to dashboard",
                "And I should see my profile information"
            ],
            "dependencies": [],
            "labels": ["authentication", "frontend", "backend"],
            "task_type": None,
            "business_value": "Allow users to securely access their accounts"
        },
        
        # Task 1 - Development
        {
            "id": "TASK-001",
            "type": "Task",
            "parent_id": "US-001",
            "title": "Implement login API endpoint",
            "description": "Create POST /api/auth/login endpoint with JWT token generation",
            "rank": 3,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": 8.0,
            "acceptance_criteria": [
                "API accepts POST /api/auth/login",
                "Valid credentials return JWT token",
                "Invalid credentials return 401 error"
            ],
            "dependencies": [],
            "labels": ["backend", "api"],
            "task_type": "Development",
            "business_value": None
        },
        
        # Sub-task 1
        {
            "id": "SUB-001",
            "type": "Sub-task",
            "parent_id": "TASK-001",
            "title": "Setup JWT library and configuration",
            "description": "Install and configure JWT library for token generation",
            "rank": 4,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": 2.0,
            "acceptance_criteria": [
                "JWT library installed",
                "Secret key configured",
                "Token expiry set to 24 hours"
            ],
            "dependencies": [],
            "labels": ["backend", "setup"],
            "task_type": "Development",
            "business_value": None
        },
        
        # Sub-task 2
        {
            "id": "SUB-002",
            "type": "Sub-task",
            "parent_id": "TASK-001",
            "title": "Implement password validation with bcrypt",
            "description": "Add bcrypt password hashing and validation",
            "rank": 5,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": 3.0,
            "acceptance_criteria": [
                "Passwords hashed with bcrypt",
                "Password validation works correctly",
                "Invalid passwords rejected"
            ],
            "dependencies": ["SUB-001"],
            "labels": ["backend", "security"],
            "task_type": "Development",
            "business_value": None
        },
        
        # Task 2 - Testing
        {
            "id": "TASK-002",
            "type": "Task",
            "parent_id": "US-001",
            "title": "Write integration tests for login flow",
            "description": "Create comprehensive integration tests for login functionality",
            "rank": 6,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": 5.0,
            "acceptance_criteria": [
                "Test successful login",
                "Test invalid credentials",
                "Test token generation",
                "Test error handling"
            ],
            "dependencies": ["TASK-001"],
            "labels": ["testing", "integration"],
            "task_type": "Testing",
            "business_value": None
        },
        
        # User Story 2
        {
            "id": "US-002",
            "type": "User Story",
            "parent_id": "EPIC-001",
            "title": "As a user, I want to register a new account",
            "description": "User can create a new account with email and password",
            "rank": 7,
            "status": "Backlog",
            "story_point": 8,
            "estimate_value": None,
            "acceptance_criteria": [
                "Given I am on the registration page",
                "When I enter email, password, and confirm password",
                "Then my account should be created",
                "And I should receive a confirmation email"
            ],
            "dependencies": [],
            "labels": ["authentication", "registration"],
            "task_type": None,
            "business_value": "Allow new users to join the platform"
        },
        
        # Task 3 - Development
        {
            "id": "TASK-003",
            "type": "Task",
            "parent_id": "US-002",
            "title": "Implement registration API endpoint",
            "description": "Create POST /api/auth/register endpoint",
            "rank": 8,
            "status": "Backlog",
            "story_point": None,
            "estimate_value": 6.0,
            "acceptance_criteria": [
                "API accepts POST /api/auth/register",
                "Email uniqueness validated",
                "Password strength validated",
                "User created in database"
            ],
            "dependencies": [],
            "labels": ["backend", "api"],
            "task_type": "Development",
            "business_value": None
        }
    ],
    
    "sprints": [
        {
            "sprint_id": "sprint-1",
            "sprint_number": 1,
            "sprint_goal": "Implement user login functionality",
            "start_date": None,
            "end_date": None,
            "velocity_plan": 13,  # 5 + 8 story points
            "velocity_actual": 0,
            "assigned_items": ["US-001", "TASK-001", "SUB-001", "SUB-002", "TASK-002"],
            "status": "Planned",
            "capacity": {
                "total_story_points": 5,
                "total_estimate_hours": 18.0,  # 8 + 2 + 3 + 5
                "capacity_story_points": 20,
                "utilization_percentage": 25.0
            }
        },
        {
            "sprint_id": "sprint-2",
            "sprint_number": 2,
            "sprint_goal": "Implement user registration functionality",
            "start_date": None,
            "end_date": None,
            "velocity_plan": 8,
            "velocity_actual": 0,
            "assigned_items": ["US-002", "TASK-003"],
            "status": "Planned",
            "capacity": {
                "total_story_points": 8,
                "total_estimate_hours": 6.0,
                "capacity_story_points": 20,
                "utilization_percentage": 40.0
            }
        }
    ]
}


def get_mock_po_output():
    """Get mock Product Owner output for testing."""
    return MOCK_PO_OUTPUT


def get_mock_team():
    """Get mock team members for testing."""
    return MOCK_TEAM

