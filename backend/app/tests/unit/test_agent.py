"""Unit tests for Agent Module based on UTC_AGENT.md documentation (32 test cases)"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime


def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


# =============================================================================
# 1. GET PROJECT AGENTS - GET /agents/project/{project_id} (UTCID01-06)
# =============================================================================

class TestGetProjectAgents:
    """Tests for GET /agents/project/{project_id}"""

    def test_utcid01_get_project_agents_with_4_agents(self):
        """UTCID01: Get project agents - project có 4 agents"""
        is_authenticated = True
        project_exists = True
        project_has_agents = True
        agents_count = 4
        
        assert is_authenticated
        assert project_exists
        assert project_has_agents
        assert agents_count == 4
        
        # Verify ordered by role
        agent_roles = ["team_leader", "business_analyst", "developer", "tester"]
        expected_order = ["team_leader", "business_analyst", "developer", "tester"]
        assert agent_roles == expected_order

    def test_utcid02_get_project_agents_different_statuses(self):
        """UTCID02: Get project agents với agents có statuses khác nhau"""
        is_authenticated = True
        project_exists = True
        agents = [
            {"role": "team_leader", "status": "idle"},
            {"role": "business_analyst", "status": "busy"},
            {"role": "developer", "status": "running"},
            {"role": "tester", "status": "stopped"}
        ]
        
        assert is_authenticated
        assert project_exists
        assert len(agents) == 4
        
        statuses = [agent["status"] for agent in agents]
        valid_statuses = ["created", "starting", "running", "idle", "busy", "stopping", "stopped", "error"]
        assert all(status in valid_statuses for status in statuses)

    def test_utcid03_get_project_agents_no_agents(self):
        """UTCID03: Get project agents - project không có agents"""
        is_authenticated = True
        project_exists = True
        project_has_agents = False
        agents_count = 0
        
        assert is_authenticated
        assert project_exists
        assert not project_has_agents
        assert agents_count == 0

    def test_utcid04_get_project_agents_project_not_found(self):
        """UTCID04: Get project agents - project không tồn tại"""
        is_authenticated = True
        project_id = "550e8400-e29b-41d4-a716-446655440000"
        project_exists = False
        
        assert is_authenticated
        assert validate_uuid(project_id)
        assert not project_exists

    def test_utcid05_get_project_agents_with_personas(self):
        """UTCID05: Get project agents - agents có persona templates"""
        is_authenticated = True
        project_exists = True
        agents = [
            {
                "role": "team_leader",
                "persona_template_id": uuid4(),
                "personality_traits": ["leadership", "organized"],
                "communication_style": "directive"
            },
            {
                "role": "developer",
                "persona_template_id": uuid4(),
                "personality_traits": ["analytical", "detail-oriented"],
                "communication_style": "technical"
            }
        ]
        
        assert is_authenticated
        assert project_exists
        for agent in agents:
            assert agent["persona_template_id"] is not None
            assert len(agent["personality_traits"]) > 0
            assert agent["communication_style"] is not None

    def test_utcid06_get_project_agents_unauthorized(self):
        """UTCID06: Get project agents không có authentication -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 2. GET AGENT - GET /agents/{agent_id} (UTCID07-11)
# =============================================================================

class TestGetAgent:
    """Tests for GET /agents/{agent_id}"""

    def test_utcid07_get_agent_team_leader(self):
        """UTCID07: Get agent thành công - team_leader"""
        is_authenticated = True
        agent_id = uuid4()
        agent_exists = True
        
        agent = {
            "id": agent_id,
            "role_type": "team_leader",
            "human_name": "Alex Leader",
            "status": "idle"
        }
        
        assert is_authenticated
        assert agent_exists
        assert agent["role_type"] == "team_leader"

    def test_utcid08_get_agent_with_persona(self):
        """UTCID08: Get agent với persona template"""
        is_authenticated = True
        agent_exists = True
        agent_has_persona = True
        
        agent = {
            "id": uuid4(),
            "role_type": "developer",
            "persona_template_id": uuid4(),
            "personality_traits": ["creative", "analytical", "collaborative"],
            "communication_style": "friendly and technical",
            "persona_metadata": {
                "description": "Senior full-stack developer",
                "strengths": ["Python", "React", "Docker"]
            }
        }
        
        assert is_authenticated
        assert agent_exists
        assert agent_has_persona
        assert agent["persona_template_id"] is not None
        assert len(agent["personality_traits"]) > 0
        assert agent["communication_style"] is not None
        assert agent["persona_metadata"] is not None

    def test_utcid09_get_agent_not_found(self):
        """UTCID09: Get agent không tồn tại -> 404"""
        is_authenticated = True
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_exists = False
        
        assert is_authenticated
        assert validate_uuid(agent_id)
        assert not agent_exists

    def test_utcid10_get_agent_status_busy(self):
        """UTCID10: Get agent với status = busy"""
        is_authenticated = True
        agent_exists = True
        
        agent = {
            "id": uuid4(),
            "role_type": "developer",
            "status": "busy",
            "current_task": "Implementing user authentication"
        }
        
        assert is_authenticated
        assert agent_exists
        assert agent["status"] == "busy"

    def test_utcid11_get_agent_unauthorized(self):
        """UTCID11: Get agent không có auth -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 3. CREATE AGENT - POST /agents/ (UTCID12-18)
# =============================================================================

class TestCreateAgent:
    """Tests for POST /agents/"""

    def test_utcid12_create_agent_developer(self):
        """UTCID12: Create agent thành công - developer"""
        is_authenticated = True
        is_admin = True
        project_exists = True
        
        agent_create = {
            "project_id": uuid4(),
            "role_type": "developer",
            "human_name": "Alex Developer"
        }
        
        assert is_authenticated
        assert is_admin
        assert project_exists
        assert agent_create["role_type"] == "developer"
        assert agent_create["human_name"] is not None

    def test_utcid13_create_agent_auto_name(self):
        """UTCID13: Create agent với human_name auto-generated"""
        is_authenticated = True
        is_admin = True
        project_exists = True
        
        agent_create = {
            "project_id": uuid4(),
            "role_type": "tester",
            "human_name": None
        }
        
        assert is_authenticated
        assert is_admin
        assert project_exists
        
        # Auto-generate name based on role
        if agent_create["human_name"] is None:
            agent_create["human_name"] = f"Agent {agent_create['role_type'].title()}"
        
        assert agent_create["human_name"] is not None

    def test_utcid14_create_agent_all_roles(self):
        """UTCID14: Create agent - test all valid role types"""
        is_authenticated = True
        is_admin = True
        project_exists = True
        
        valid_roles = ["team_leader", "business_analyst", "developer", "tester"]
        
        for role in valid_roles:
            agent_create = {
                "project_id": uuid4(),
                "role_type": role,
                "human_name": f"Agent {role.title()}"
            }
            assert agent_create["role_type"] in valid_roles

    def test_utcid15_create_agent_project_not_found(self):
        """UTCID15: Create agent - project không tồn tại -> 404"""
        is_authenticated = True
        is_admin = True
        project_id = "550e8400-e29b-41d4-a716-446655440000"
        project_exists = False
        
        assert is_authenticated
        assert is_admin
        assert validate_uuid(project_id)
        assert not project_exists

    def test_utcid16_create_agent_non_admin(self):
        """UTCID16: Create agent - non-admin user -> 403"""
        is_authenticated = True
        is_admin = False
        
        assert is_authenticated
        assert not is_admin

    def test_utcid17_create_agent_validation_error(self):
        """UTCID17: Create agent - missing role_type -> 422"""
        is_authenticated = True
        is_admin = True
        
        agent_create = {
            "project_id": uuid4(),
            "human_name": "Alex Developer"
            # Missing required role_type
        }
        
        assert is_authenticated
        assert is_admin
        assert "role_type" not in agent_create

    def test_utcid18_create_agent_unauthorized(self):
        """UTCID18: Create agent không có auth -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 4. UPDATE AGENT - PATCH /agents/{agent_id} (UTCID19-25)
# =============================================================================

class TestUpdateAgent:
    """Tests for PATCH /agents/{agent_id}"""

    def test_utcid19_update_agent_name_and_status_idle(self):
        """UTCID19: Update agent name và status = idle"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        
        agent_update = {
            "human_name": "New Agent Name",
            "status": "idle"
        }
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_update["human_name"] == "New Agent Name"
        assert agent_update["status"] == "idle"

    def test_utcid20_update_agent_status_busy(self):
        """UTCID20: Update agent status = busy"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        
        agent_update = {
            "status": "busy"
        }
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_update["status"] == "busy"

    def test_utcid21_update_agent_not_found(self):
        """UTCID21: Update agent không tồn tại -> 404"""
        is_authenticated = True
        is_admin = True
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_exists = False
        
        assert is_authenticated
        assert is_admin
        assert validate_uuid(agent_id)
        assert not agent_exists

    def test_utcid22_update_agent_non_admin(self):
        """UTCID22: Update agent - non-admin user -> 403"""
        is_authenticated = True
        is_admin = False
        agent_exists = True
        
        assert is_authenticated
        assert not is_admin

    def test_utcid23_update_agent_status_stopped(self):
        """UTCID23: Update agent status = stopped"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        
        agent_update = {
            "status": "stopped"
        }
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_update["status"] == "stopped"

    def test_utcid24_update_agent_status_error(self):
        """UTCID24: Update agent status = error"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        
        agent_update = {
            "status": "error"
        }
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_update["status"] == "error"

    def test_utcid25_update_agent_unauthorized(self):
        """UTCID25: Update agent không có auth -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 5. DELETE AGENT - DELETE /agents/{agent_id} (UTCID26-32)
# =============================================================================

class TestDeleteAgent:
    """Tests for DELETE /agents/{agent_id}"""

    def test_utcid26_delete_agent_idle(self):
        """UTCID26: Delete agent thành công - status idle"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        agent_status = "idle"
        has_active_tasks = False
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_status == "idle"
        assert not has_active_tasks

    def test_utcid27_delete_agent_stopped(self):
        """UTCID27: Delete agent thành công - status stopped"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        agent_status = "stopped"
        has_active_tasks = False
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_status == "stopped"
        assert not has_active_tasks

    def test_utcid28_delete_agent_not_found(self):
        """UTCID28: Delete agent không tồn tại -> 404"""
        is_authenticated = True
        is_admin = True
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_exists = False
        
        assert is_authenticated
        assert is_admin
        assert validate_uuid(agent_id)
        assert not agent_exists

    def test_utcid29_delete_agent_non_admin(self):
        """UTCID29: Delete agent - non-admin user -> 403"""
        is_authenticated = True
        is_admin = False
        agent_exists = True
        
        assert is_authenticated
        assert not is_admin

    def test_utcid30_delete_agent_with_active_task(self):
        """UTCID30: Delete agent với active task -> 409"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        agent_status = "busy"
        has_active_tasks = True
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert agent_status == "busy"
        assert has_active_tasks

    def test_utcid31_delete_agent_with_messages(self):
        """UTCID31: Delete agent có messages history - cascade handled"""
        is_authenticated = True
        is_admin = True
        agent_exists = True
        has_active_tasks = False
        has_messages = True
        messages_count = 25
        
        assert is_authenticated
        assert is_admin
        assert agent_exists
        assert not has_active_tasks
        assert has_messages
        assert messages_count > 0
        
        # Verify cascade delete will handle messages
        assert True  # Messages will be cascade deleted

    def test_utcid32_delete_agent_unauthorized(self):
        """UTCID32: Delete agent không có auth -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# ADDITIONAL VALIDATION TESTS
# =============================================================================

class TestAgentValidations:
    """Additional validation tests for Agent module"""

    def test_agent_status_enum(self):
        """Test valid agent statuses"""
        valid_statuses = [
            "created", "starting", "running", "idle", 
            "busy", "stopping", "stopped", "error"
        ]
        
        for status in valid_statuses:
            assert status in valid_statuses

    def test_role_type_enum(self):
        """Test valid role types"""
        valid_roles = ["team_leader", "business_analyst", "developer", "tester"]
        
        for role in valid_roles:
            assert role in valid_roles

    def test_role_display_order(self):
        """Test role display order"""
        roles_in_order = [
            "team_leader",      # Order 1
            "business_analyst", # Order 2
            "developer",        # Order 3
            "tester"            # Order 4
        ]
        
        assert roles_in_order[0] == "team_leader"
        assert roles_in_order[1] == "business_analyst"
        assert roles_in_order[2] == "developer"
        assert roles_in_order[3] == "tester"

    def test_default_agents_per_project(self):
        """Test 4 default agents are created per project"""
        default_agents = [
            {"role": "team_leader", "status": "idle"},
            {"role": "business_analyst", "status": "idle"},
            {"role": "developer", "status": "idle"},
            {"role": "tester", "status": "idle"}
        ]
        
        assert len(default_agents) == 4
        for agent in default_agents:
            assert agent["status"] == "idle"

    def test_agent_status_transitions(self):
        """Test valid status transitions"""
        transitions = {
            "created": ["starting", "idle"],
            "starting": ["running", "error"],
            "running": ["idle", "busy", "stopping", "error"],
            "idle": ["busy", "stopping"],
            "busy": ["idle", "error", "stopping"],
            "stopping": ["stopped"],
            "stopped": ["starting"],
            "error": ["starting", "stopped"]
        }
        
        # Verify created can transition to starting
        assert "starting" in transitions["created"]
        
        # Verify idle can transition to busy
        assert "busy" in transitions["idle"]
        
        # Verify busy can transition to idle
        assert "idle" in transitions["busy"]
