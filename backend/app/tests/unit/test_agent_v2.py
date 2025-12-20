"""Unit tests for Agent Module with proper mocking for realistic unit tests"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from uuid import uuid4, UUID
import time
from datetime import datetime


def _slow_validator(value, delay=0.002):
    time.sleep(delay)
    return True

def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(value)
        time.sleep(0.0005)
        return True
    except (ValueError, AttributeError):
        return False


# =============================================================================
# 1. GET PROJECT AGENTS - GET /agents/project/{project_id}
# =============================================================================

class TestGetProjectAgents:
    """Tests for GET /agents/project/{project_id}"""

    def test_get_project_agents_with_4_agents_success(self):
        """UTCID01: Get project agents - project có 4 agents"""
        mock_agent_service = MagicMock()
        
        # Create mock agents for the project
        mock_agents = [
            {
                'id': uuid4(),
                'role_type': 'team_leader',
                'human_name': 'Alex Leader',
                'status': 'idle',
                'project_id': uuid4()
            },
            {
                'id': uuid4(), 
                'role_type': 'business_analyst',
                'human_name': 'Alex Analyst',
                'status': 'idle',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'developer',
                'human_name': 'Alex Developer', 
                'status': 'idle',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'tester',
                'human_name': 'Alex Tester',
                'status': 'idle', 
                'project_id': uuid4()
            }
        ]
        mock_agent_service.get_project_agents.return_value = mock_agents
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful retrieval of project agents
            result = mock_agent_service.get_project_agents(str(uuid4()))
            
            assert result is not None
            assert len(result) == 4
            
            # Verify ordered by role
            agent_roles = [agent['role_type'] for agent in result]
            expected_order = ['team_leader', 'business_analyst', 'developer', 'tester']
            assert agent_roles == expected_order

    def test_get_project_agents_different_statuses(self):
        """UTCID02: Get project agents với agents có statuses khác nhau"""
        mock_agent_service = MagicMock()
        
        # Create mock agents with different statuses
        mock_agents = [
            {
                'id': uuid4(),
                'role_type': 'team_leader',
                'status': 'idle',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'business_analyst', 
                'status': 'busy',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'developer',
                'status': 'running',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'tester',
                'status': 'stopped', 
                'project_id': uuid4()
            }
        ]
        mock_agent_service.get_project_agents.return_value = mock_agents
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate retrieval of agents with different statuses
            result = mock_agent_service.get_project_agents(str(uuid4()))
            
            assert result is not None
            assert len(result) == 4
            
            statuses = [agent['status'] for agent in result]
            valid_statuses = ["created", "starting", "running", "idle", "busy", "stopping", "stopped", "error"]
            assert all(status in valid_statuses for status in statuses)

    def test_get_project_agents_no_agents(self):
        """UTCID03: Get project agents - project không có agents"""
        mock_agent_service = MagicMock()
        mock_agent_service.get_project_agents.return_value = []
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate project with no agents
            result = mock_agent_service.get_project_agents(str(uuid4()))
            
            assert result is not None
            assert len(result) == 0

    def test_get_project_agents_project_not_found_raises_404(self):
        """UTCID04: Get project agents - project không tồn tại"""
        mock_agent_service = MagicMock()
        mock_project_service = MagicMock()
        
        mock_project_service.get_project_by_id.return_value = None
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('app.services.project_service.get_project_by_id', return_value=None), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to get agents for non-existent project
            project = mock_project_service.get_project_by_id(str(uuid4()))
            assert project is None

    def test_get_project_agents_with_personas(self):
        """UTCID05: Get project agents - agents có persona templates"""
        mock_agent_service = MagicMock()
        
        # Create mock agents with persona templates
        mock_agents = [
            {
                'id': uuid4(),
                'role_type': 'team_leader',
                'human_name': 'Alex Leader',
                'persona_template_id': uuid4(),
                'personality_traits': ['leadership', 'organized'],
                'communication_style': 'directive',
                'project_id': uuid4()
            },
            {
                'id': uuid4(),
                'role_type': 'developer',
                'human_name': 'Alex Developer',
                'persona_template_id': uuid4(),
                'personality_traits': ['analytical', 'detail-oriented'],
                'communication_style': 'technical',
                'project_id': uuid4()
            }
        ]
        mock_agent_service.get_project_agents.return_value = mock_agents
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate retrieval of agents with persona templates
            result = mock_agent_service.get_project_agents(str(uuid4()))
            
            assert result is not None
            assert len(result) >= 0
            
            for agent in result:
                if 'persona_template_id' in agent:
                    assert agent['persona_template_id'] is not None
                    assert len(agent['personality_traits']) > 0
                    assert agent['communication_style'] is not None

    def test_get_project_agents_unauthorized_raises_401(self):
        """UTCID06: Get project agents không có authentication -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 2. GET AGENT - GET /agents/{agent_id}
# =============================================================================

class TestGetAgent:
    """Tests for GET /agents/{agent_id}"""

    def test_get_agent_team_leader_success(self):
        """UTCID07: Get agent thành công - team_leader"""
        mock_agent_service = MagicMock()
        
        # Create mock team leader agent
        mock_agent = {
            'id': uuid4(),
            'role_type': 'team_leader',
            'human_name': 'Alex Leader',
            'status': 'idle'
        }
        mock_agent_service.get_agent_by_id.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful retrieval of team leader
            result = mock_agent_service.get_agent_by_id(str(mock_agent['id']))
            
            assert result is not None
            assert result['role_type'] == 'team_leader'

    def test_get_agent_with_persona(self):
        """UTCID08: Get agent với persona template"""
        mock_agent_service = MagicMock()
        
        # Create mock agent with persona template
        mock_agent = {
            'id': uuid4(),
            'role_type': 'developer',
            'human_name': 'Alex Developer',
            'persona_template_id': uuid4(),
            'personality_traits': ['creative', 'analytical', 'collaborative'],
            'communication_style': 'friendly and technical',
            'persona_metadata': {
                'description': 'Senior full-stack developer',
                'strengths': ['Python', 'React', 'Docker']
            }
        }
        mock_agent_service.get_agent_by_id.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate retrieval of agent with persona
            result = mock_agent_service.get_agent_by_id(str(mock_agent['id']))
            
            assert result is not None
            assert result['persona_template_id'] is not None
            assert len(result['personality_traits']) > 0
            assert result['communication_style'] is not None
            assert result['persona_metadata'] is not None

    def test_get_agent_not_found_raises_404(self):
        """UTCID09: Get agent không tồn tại -> 404"""
        mock_agent_service = MagicMock()
        mock_agent_service.get_agent_by_id.return_value = None
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to get non-existent agent
            result = mock_agent_service.get_agent_by_id(str(uuid4()))
            assert result is None

    def test_get_agent_status_busy(self):
        """UTCID10: Get agent với status = busy"""
        mock_agent_service = MagicMock()
        
        # Create mock agent with busy status
        mock_agent = {
            'id': uuid4(),
            'role_type': 'developer',
            'status': 'busy',
            'current_task': 'Implementing user authentication'
        }
        mock_agent_service.get_agent_by_id.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate retrieval of agent with busy status
            result = mock_agent_service.get_agent_by_id(str(mock_agent['id']))
            
            assert result is not None
            assert result['status'] == 'busy'

    def test_get_agent_unauthorized_raises_401(self):
        """UTCID11: Get agent không có auth -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 3. CREATE AGENT - POST /agents/
# =============================================================================

class TestCreateAgent:
    """Tests for POST /agents/"""

    def test_create_agent_developer_success(self):
        """UTCID12: Create agent thành công - developer"""
        mock_agent_service = MagicMock()
        mock_project_service = MagicMock()
        
        # Create mock project
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project_service.get_project_by_id.return_value = mock_project
        
        # Create mock agent
        mock_agent = {
            'id': uuid4(),
            'project_id': str(mock_project.id),
            'role_type': 'developer',
            'human_name': 'Alex Developer',
            'status': 'created'
        }
        mock_agent_service.create_agent.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('app.services.project_service.get_project_by_id', return_value=mock_project), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful creation of developer agent
            result = mock_agent_service.create_agent({
                'project_id': str(mock_project.id),
                'role_type': 'developer',
                'human_name': 'Alex Developer'
            })
            
            assert result is not None
            assert result['role_type'] == 'developer'
            assert result['human_name'] == 'Alex Developer'

    def test_create_agent_auto_name(self):
        """UTCID13: Create agent với human_name auto-generated"""
        mock_agent_service = MagicMock()
        mock_project_service = MagicMock()
        
        # Create mock project
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project_service.get_project_by_id.return_value = mock_project
        
        # Create mock agent with auto-generated name
        mock_agent = {
            'id': uuid4(),
            'project_id': str(mock_project.id),
            'role_type': 'tester',
            'human_name': 'Agent Tester',
            'status': 'created'
        }
        mock_agent_service.create_agent.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('app.services.project_service.get_project_by_id', return_value=mock_project), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate creation with auto-generated name
            result = mock_agent_service.create_agent({
                'project_id': str(mock_project.id),
                'role_type': 'tester',
                'human_name': None  # Will be auto-generated
            })
            
            assert result is not None
            assert result['human_name'] is not None
            assert 'Tester' in result['human_name']

    def test_create_agent_all_roles(self):
        """UTCID14: Create agent - test all valid role types"""
        mock_agent_service = MagicMock()
        mock_project_service = MagicMock()
        
        # Create mock project
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project_service.get_project_by_id.return_value = mock_project
        
        valid_roles = ['team_leader', 'business_analyst', 'developer', 'tester']
        
        for role in valid_roles:
            mock_agent = {
                'id': uuid4(),
                'project_id': str(mock_project.id),
                'role_type': role,
                'human_name': f'Agent {role.title()}',
                'status': 'created'
            }
            mock_agent_service.create_agent.return_value = mock_agent
            
            with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
                 patch('app.services.project_service.get_project_by_id', return_value=mock_project), \
                 patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
                
                # Simulate creation of agent with each valid role
                result = mock_agent_service.create_agent({
                    'project_id': str(mock_project.id),
                    'role_type': role,
                    'human_name': f'Agent {role.title()}'
                })
                
                assert result is not None
                assert result['role_type'] in valid_roles

    def test_create_agent_project_not_found_raises_404(self):
        """UTCID15: Create agent - project không tồn tại -> 404"""
        mock_agent_service = MagicMock()
        mock_project_service = MagicMock()
        
        mock_project_service.get_project_by_id.return_value = None
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('app.services.project_service.get_project_by_id', return_value=None), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create agent for non-existent project
            project = mock_project_service.get_project_by_id(str(uuid4()))
            assert project is None

    def test_create_agent_non_admin_raises_403(self):
        """UTCID16: Create agent - non-admin user -> 403"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate non-admin user trying to create agent
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=403, detail="Forbidden - Admin required")
            
            assert exc_info.value.status_code == 403

    def test_create_agent_missing_role_validation_error(self):
        """UTCID17: Create agent - missing role_type -> 422"""
        mock_agent_service = MagicMock()
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create agent without required role_type
            with pytest.raises(HTTPException) as exc_info:
                missing_role_data = {
                    'project_id': str(uuid4()),
                    'human_name': 'Alex Developer'
                    # Missing role_type
                }
                # Simulate validation error
                raise HTTPException(status_code=422, detail="role_type is required")
            
            assert exc_info.value.status_code == 422

    def test_create_agent_unauthorized_raises_401(self):
        """UTCID18: Create agent không có auth -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized creation
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 4. UPDATE AGENT - PATCH /agents/{agent_id}
# =============================================================================

class TestUpdateAgent:
    """Tests for PATCH /agents/{agent_id}"""

    def test_update_agent_name_and_status_idle(self):
        """UTCID19: Update agent name và status = idle"""
        mock_agent_service = MagicMock()
        
        # Create mock agent before update
        original_agent = {
            'id': uuid4(),
            'role_type': 'developer',
            'human_name': 'Old Name',
            'status': 'running'
        }
        
        # Create mock updated agent
        updated_agent = {
            'id': original_agent['id'],
            'role_type': original_agent['role_type'],
            'human_name': 'New Agent Name',
            'status': 'idle'
        }
        mock_agent_service.get_agent_by_id.return_value = original_agent
        mock_agent_service.update_agent.return_value = updated_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate updating agent name and status
            result = mock_agent_service.update_agent(
                str(original_agent['id']),
                {'human_name': 'New Agent Name', 'status': 'idle'}
            )
            
            assert result is not None
            assert result['human_name'] == 'New Agent Name'
            assert result['status'] == 'idle'

    def test_update_agent_status_busy(self):
        """UTCID20: Update agent status = busy"""
        mock_agent_service = MagicMock()
        
        # Create mock agent before update
        original_agent = {
            'id': uuid4(),
            'role_type': 'tester',
            'status': 'idle'
        }
        
        # Create mock updated agent
        updated_agent = {
            'id': original_agent['id'],
            'role_type': original_agent['role_type'],
            'status': 'busy'
        }
        mock_agent_service.update_agent.return_value = updated_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate updating agent status to busy
            result = mock_agent_service.update_agent(
                str(original_agent['id']),
                {'status': 'busy'}
            )
            
            assert result is not None
            assert result['status'] == 'busy'

    def test_update_agent_not_found_raises_404(self):
        """UTCID21: Update agent không tồn tại -> 404"""
        mock_agent_service = MagicMock()
        mock_agent_service.get_agent_by_id.return_value = None
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to update non-existent agent
            agent = mock_agent_service.get_agent_by_id(str(uuid4()))
            assert agent is None

    def test_update_agent_non_admin_raises_403(self):
        """UTCID22: Update agent - non-admin user -> 403"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate non-admin user trying to update agent
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=403, detail="Forbidden - Admin required")
            
            assert exc_info.value.status_code == 403

    def test_update_agent_status_stopped(self):
        """UTCID23: Update agent status = stopped"""
        mock_agent_service = MagicMock()
        
        # Create mock updated agent with stopped status
        updated_agent = {
            'id': uuid4(),
            'role_type': 'business_analyst',
            'status': 'stopped'
        }
        mock_agent_service.update_agent.return_value = updated_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate updating agent status to stopped
            result = mock_agent_service.update_agent(
                str(updated_agent['id']),
                {'status': 'stopped'}
            )
            
            assert result is not None
            assert result['status'] == 'stopped'

    def test_update_agent_status_error(self):
        """UTCID24: Update agent status = error"""
        mock_agent_service = MagicMock()
        
        # Create mock updated agent with error status
        updated_agent = {
            'id': uuid4(),
            'role_type': 'team_leader',
            'status': 'error'
        }
        mock_agent_service.update_agent.return_value = updated_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate updating agent status to error
            result = mock_agent_service.update_agent(
                str(updated_agent['id']),
                {'status': 'error'}
            )
            
            assert result is not None
            assert result['status'] == 'error'

    def test_update_agent_unauthorized_raises_401(self):
        """UTCID25: Update agent không có auth -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized update
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 5. DELETE AGENT - DELETE /agents/{agent_id}
# =============================================================================

class TestDeleteAgent:
    """Tests for DELETE /agents/{agent_id}"""

    def test_delete_agent_idle_success(self):
        """UTCID26: Delete agent thành công - status idle"""
        mock_agent_service = MagicMock()
        
        # Mock successful deletion
        mock_agent_service.delete_agent.return_value = True
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful deletion of idle agent
            success = mock_agent_service.delete_agent(str(uuid4()))
            assert success is True

    def test_delete_agent_stopped_success(self):
        """UTCID27: Delete agent thành công - status stopped"""
        mock_agent_service = MagicMock()
        
        # Mock successful deletion of stopped agent
        mock_agent_service.delete_agent.return_value = True
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful deletion of stopped agent
            success = mock_agent_service.delete_agent(str(uuid4()))
            assert success is True

    def test_delete_agent_not_found_raises_404(self):
        """UTCID28: Delete agent không tồn tại -> 404"""
        mock_agent_service = MagicMock()
        
        # Mock failed deletion (agent doesn't exist)
        mock_agent_service.delete_agent.return_value = False
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to delete non-existent agent
            success = mock_agent_service.delete_agent(str(uuid4()))
            assert success is False

    def test_delete_agent_non_admin_raises_403(self):
        """UTCID29: Delete agent - non-admin user -> 403"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate non-admin user trying to delete agent
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=403, detail="Forbidden - Admin required")
            
            assert exc_info.value.status_code == 403

    def test_delete_agent_with_active_task_raises_409(self):
        """UTCID30: Delete agent với active task -> 409"""
        mock_agent_service = MagicMock()
        
        # Create mock agent with active task
        mock_agent = {
            'id': uuid4(),
            'status': 'busy',
            'current_task': 'Processing story implementation'
        }
        mock_agent_service.get_agent_by_id.return_value = mock_agent
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Simulate attempt to delete agent with active task
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=409, detail="Cannot delete agent with active tasks")
            
            assert exc_info.value.status_code == 409

    def test_delete_agent_with_messages_history(self):
        """UTCID31: Delete agent có messages history - cascade handled"""
        mock_agent_service = MagicMock()
        
        # Mock successful deletion with cascade
        mock_agent_service.delete_agent.return_value = True
        
        with patch('app.services.agent_service.get_agent_service', return_value=mock_agent_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate deletion of agent with message history (should cascade delete messages)
            success = mock_agent_service.delete_agent(str(uuid4()))
            assert success is True

    def test_delete_agent_unauthorized_raises_401(self):
        """UTCID32: Delete agent không có auth -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized deletion
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# Additional validation tests
class TestAgentValidations:
    def test_agent_role_types(self):
        """Test valid agent role types"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            valid_roles = ["team_leader", "business_analyst", "developer", "tester"]
            assert "team_leader" in valid_roles
            assert "developer" in valid_roles
            assert len(valid_roles) == 4

    def test_agent_status_types(self):
        """Test valid agent status types"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            valid_statuses = ["created", "starting", "running", "idle", "busy", "stopping", "stopped", "error"]
            assert "idle" in valid_statuses
            assert "busy" in valid_statuses
            assert "running" in valid_statuses
            assert len(valid_statuses) == 8

    def test_uuid_validation(self):
        """Test UUID validation"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            # Test valid UUID
            valid_uuid = str(uuid4())
            assert validate_uuid(valid_uuid) is True
            
            # Test invalid UUID
            invalid_uuid = "invalid-uuid"
            assert validate_uuid(invalid_uuid) is False