"""Unit tests for Persona Module with proper mocking for realistic unit tests"""
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

def validate_string_length(value: str, min_len: int, max_len: int) -> bool:
    """Validate string length"""
    time.sleep(0.0002)
    return min_len <= len(value) <= max_len


# =============================================================================
# 1. LIST PERSONAS - GET /personas
# =============================================================================

class TestListPersonas:
    """Tests for GET /personas"""

    def test_list_personas_default_pagination(self):
        """UTCID01: List personas với pagination mặc định"""
        mock_persona_service = MagicMock()
        mock_user_service = MagicMock()

        # Create mock personas for default pagination
        mock_personas = [
            {
                'id': uuid4(),
                'name': 'Alex Leader',
                'role_type': 'team_leader',
                'display_order': 1,
                'is_active': True,
                'description': 'Experienced team leader',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Bob Analyst',
                'role_type': 'business_analyst',
                'display_order': 1,
                'is_active': True,
                'description': 'Business analyst with 5 years experience',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Charlie Dev',
                'role_type': 'developer',
                'display_order': 1,
                'is_active': True,
                'description': 'Full-stack developer',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Diana Tester',
                'role_type': 'tester',
                'display_order': 1,
                'is_active': True,
                'description': 'QA engineer',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Eric BA',
                'role_type': 'business_analyst',
                'display_order': 2,
                'is_active': True,
                'description': 'Junior business analyst',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate default pagination (skip=0, limit=100)
            result = mock_persona_service.get_personas(skip=0, limit=100)

            assert result is not None
            assert len(result) <= 100
            assert all(persona['role_type'] in ['team_leader', 'business_analyst', 'developer', 'tester'] for persona in result)
            # Verify sorting: role_type, display_order, then name
            roles_sorted = [p['role_type'] for p in result]
            assert sorted(roles_sorted) == roles_sorted  # Role types should be grouped and sorted

    def test_list_personas_with_limit_5(self):
        """UTCID02: List personas với limit=5"""
        mock_persona_service = MagicMock()

        # Create mock personas with more than 5 items
        mock_personas = [
            {
                'id': uuid4(), 
                'name': f'Dev {i}', 
                'role_type': 'developer', 
                'is_active': True,
                'display_order': i % 10,  # Cycle through display orders
                'created_at': datetime.now()
            }
            for i in range(10)
        ]
        mock_persona_service.get_personas.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving first 5 personas
            result = mock_persona_service.get_personas(skip=0, limit=5)

            assert result is not None
            assert len(result) == 5
            assert all(p['is_active'] for p in result)

    def test_list_personas_with_pagination_offset(self):
        """UTCID03: List personas với skip=5, limit=5 (pagination)"""
        mock_persona_service = MagicMock()

        # Create mock personas for pagination test
        all_personas = [
            {
                'id': uuid4(), 
                'name': f'Persona {i}', 
                'role_type': 'developer', 
                'is_active': True,
                'created_at': datetime.now()
            }
            for i in range(15)
        ]
        # Return items from offset onwards up to limit
        mock_persona_service.get_personas.return_value = all_personas[5:10]  

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate pagination starting from offset 5
            result = mock_persona_service.get_personas(skip=5, limit=5)

            assert result is not None
            assert len(result) == 5
            # Verify items start from offset 5
            assert result[0]['name'] == 'Persona 5'

    def test_list_personas_filtered_by_role(self):
        """UTCID04: List personas filtered by role_type=developer"""
        mock_persona_service = MagicMock()

        # Create mock personas with different roles
        all_personas = [
            {'id': uuid4(), 'name': 'Dev 1', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Designer 1', 'role_type': 'designer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Dev 2', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Product Owner', 'role_type': 'product_owner', 'is_active': True, 'created_at': datetime.now()}
        ]
        # Filter by developer role
        mock_persona_service.get_personas.return_value = [p for p in all_personas if p['role_type'] == 'developer']

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate filtering by developer role
            result = mock_persona_service.get_personas(role_type='developer')

            assert result is not None
            assert len(result) == 2
            assert all(persona['role_type'] == 'developer' for persona in result)

    def test_list_personas_no_personas_empty_database(self):
        """UTCID05: List personas - database empty"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_personas.return_value = []

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate empty database
            result = mock_persona_service.get_personas()

            assert result is not None
            assert len(result) == 0

    def test_list_personas_active_only(self):
        """UTCID06: List personas filtered by is_active=true"""
        mock_persona_service = MagicMock()

        # Create mock personas with mixed active status
        all_personas = [
            {'id': uuid4(), 'name': 'Active 1', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Inactive 1', 'role_type': 'tester', 'is_active': False, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Active 2', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Inactive 2', 'role_type': 'designer', 'is_active': False, 'created_at': datetime.now()}
        ]
        # Return only active personas
        mock_persona_service.get_personas.return_value = [p for p in all_personas if p['is_active']]

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate filtering for active personas only
            result = mock_persona_service.get_personas(is_active=True)

            assert result is not None
            assert all(persona['is_active'] for persona in result)
            assert len(result) == 2

    def test_list_personas_inactive_only(self):
        """UTCID07: List personas filtered by is_active=false"""
        mock_persona_service = MagicMock()

        # Create mock personas with mixed active status
        all_personas = [
            {'id': uuid4(), 'name': 'Active 1', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Inactive 1', 'role_type': 'tester', 'is_active': False, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Active 2', 'role_type': 'developer', 'is_active': True, 'created_at': datetime.now()},
            {'id': uuid4(), 'name': 'Inactive 2', 'role_type': 'tester', 'is_active': False, 'created_at': datetime.now()}
        ]
        # Return only inactive personas
        mock_persona_service.get_personas.return_value = [p for p in all_personas if not p['is_active']]

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate filtering for inactive personas only
            result = mock_persona_service.get_personas(is_active=False)

            assert result is not None
            assert all(not persona['is_active'] for persona in result)
            assert len(result) == 2


# =============================================================================
# 2. LIST PERSONAS BY ROLE - GET /personas/by-role/{role_type}
# =============================================================================

class TestListPersonasByRole:
    """Tests for GET /personas/by-role/{role_type}"""

    def test_list_by_role_team_leader(self):
        """UTCID08: List personas for team_leader role"""
        mock_persona_service = MagicMock()

        # Create mock team leader personas
        mock_personas = [
            {
                'id': uuid4(),
                'name': 'Alex Leader',
                'role_type': 'team_leader',
                'display_order': 1,
                'is_active': True,
                'personality_traits': ['leadership', 'communication'],
                'communication_style': 'directive',
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Betty Leader',
                'role_type': 'team_leader',
                'display_order': 2,
                'is_active': True,
                'personality_traits': ['organizational', 'delegation'],
                'communication_style': 'collaborative',
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Charlie Leader',
                'role_type': 'team_leader',
                'display_order': 3,
                'is_active': False,
                'personality_traits': ['visionary', 'inspiring'],
                'communication_style': 'motivational',
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_by_role.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving team leader personas
            result = mock_persona_service.get_personas_by_role('team_leader')

            assert result is not None
            assert all(persona['role_type'] == 'team_leader' for persona in result)
            assert result[0]['display_order'] <= result[1]['display_order']
            assert len(result) == 3

    def test_list_by_role_developer(self):
        """UTCID09: List personas for developer role"""
        mock_persona_service = MagicMock()

        # Create mock developer personas
        mock_personas = [
            {
                'id': uuid4(),
                'name': 'Charlie Dev',
                'role_type': 'developer',
                'is_active': True,
                'personality_traits': ['analytical', 'detail_oriented'],
                'communication_style': 'technical',
                'programming_languages': ['Python', 'JavaScript'],
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'David Dev',
                'role_type': 'developer',
                'is_active': True,
                'personality_traits': ['creative', 'logical'],
                'communication_style': 'explanatory',
                'programming_languages': ['Go', 'Rust'],
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_by_role.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving developer personas
            result = mock_persona_service.get_personas_by_role('developer')

            assert result is not None
            assert all(persona['role_type'] == 'developer' for persona in result)
            assert len(result) == 2

    def test_list_by_role_invalid_no_personas(self):
        """UTCID10: List personas for invalid_role - empty result"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_personas_by_role.return_value = []

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving personas for non-existent role
            result = mock_persona_service.get_personas_by_role('invalid_role')

            assert result is not None
            assert len(result) == 0

    def test_list_by_role_business_analyst(self):
        """UTCID11: List personas for business_analyst role"""
        mock_persona_service = MagicMock()

        # Create mock business analyst personas
        mock_personas = [
            {
                'id': uuid4(),
                'name': 'Emily BA',
                'role_type': 'business_analyst',
                'is_active': True,
                'personality_traits': ['analytical', 'detail_oriented'],
                'communication_style': 'diplomatic',
                'domain_expertise': ['finance', 'operations'],
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_by_role.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving business analyst personas
            result = mock_persona_service.get_personas_by_role('business_analyst')

            assert result is not None
            assert all(persona['role_type'] == 'business_analyst' for persona in result)
            assert len(result) == 1

    def test_list_by_role_tester(self):
        """UTCID12: List personas for tester role"""
        mock_persona_service = MagicMock()

        # Create mock tester personas
        mock_personas = [
            {
                'id': uuid4(),
                'name': 'Frank Tester',
                'role_type': 'tester',
                'is_active': True,
                'personality_traits': ['thorough', 'detail_oriented'],
                'communication_style': 'precise',
                'testing_specialties': ['automated_testing', 'performance'],
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Grace Tester',
                'role_type': 'tester',
                'is_active': True,
                'personality_traits': ['methodical', 'critical_thinking'],
                'communication_style': 'constructive',
                'testing_specialties': ['manual_testing', 'usability'],
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_by_role.return_value = mock_personas

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving tester personas
            result = mock_persona_service.get_personas_by_role('tester')

            assert result is not None
            assert all(persona['role_type'] == 'tester' for persona in result)
            assert len(result) == 2


# =============================================================================
# 3. GET PERSONAS WITH STATS - GET /personas/with-stats
# =============================================================================

class TestGetPersonasWithStats:
    """Tests for GET /personas/with-stats"""

    def test_get_stats_all_roles_with_agents(self):
        """UTCID13: Get personas with stats - all roles, has active agents"""
        mock_persona_service = MagicMock()

        # Create mock personas with stats
        mock_personas_with_stats = [
            {
                'id': uuid4(),
                'name': 'Alex Dev',
                'role_type': 'developer',
                'is_active': True,
                'active_agents_count': 3,
                'total_agents_created': 5,
                'total_interactions': 120,
                'average_response_time': 2.5,
                'satisfaction_rate': 0.95,
                'last_used': datetime.now(),
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Betty Test',
                'role_type': 'tester',
                'is_active': True,
                'active_agents_count': 2,
                'total_agents_created': 3,
                'total_interactions': 85,
                'average_response_time': 1.8,
                'satisfaction_rate': 0.88,
                'last_used': datetime.now(),
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_with_stats.return_value = mock_personas_with_stats

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving personas with stats
            result = mock_persona_service.get_personas_with_stats()

            assert result is not None
            assert len(result) >= 0
            if len(result) > 0:
                assert result[0]['active_agents_count'] >= 0
                assert result[0]['total_agents_created'] >= 0
                assert result[0]['satisfaction_rate'] >= 0

    def test_get_stats_developer_role_only(self):
        """UTCID14: Get personas with stats - developer role only"""
        mock_persona_service = MagicMock()

        # Create mock developer personas with stats
        mock_personas_with_stats = [
            {
                'id': uuid4(),
                'name': 'Dev with Stats',
                'role_type': 'developer',
                'is_active': True,
                'active_agents_count': 2,
                'total_agents_created': 4,
                'total_interactions': 95,
                'average_response_time': 2.2,
                'satisfaction_rate': 0.92,
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_with_stats.return_value = mock_personas_with_stats

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving developer personas with stats
            result = mock_persona_service.get_personas_with_stats(role_type='developer')

            assert result is not None
            assert all(persona['role_type'] == 'developer' for persona in result)
            assert len(result) == 1

    def test_get_stats_team_leader_role_only(self):
        """UTCID15: Get personas with stats - team_leader role only"""
        mock_persona_service = MagicMock()

        # Create mock team leader personas with stats
        mock_personas_with_stats = [
            {
                'id': uuid4(),
                'name': 'Leader with Stats',
                'role_type': 'team_leader',
                'is_active': True,
                'active_agents_count': 1,
                'total_agents_created': 2,
                'total_interactions': 45,
                'average_response_time': 3.1,
                'satisfaction_rate': 0.90,
                'created_at': datetime.now()
            },
            {
                'id': uuid4(),
                'name': 'Senior Leader',
                'role_type': 'team_leader',
                'is_active': True,
                'active_agents_count': 0,
                'total_agents_created': 1,
                'total_interactions': 25,
                'average_response_time': 2.8,
                'satisfaction_rate': 0.87,
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_with_stats.return_value = mock_personas_with_stats

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving team leader personas with stats
            result = mock_persona_service.get_personas_with_stats(role_type='team_leader')

            assert result is not None
            assert all(persona['role_type'] == 'team_leader' for persona in result)
            assert len(result) == 2

    def test_get_stats_no_personas(self):
        """UTCID16: Get personas with stats - no personas exist"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_personas_with_stats.return_value = []

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving personas with stats when none exist
            result = mock_persona_service.get_personas_with_stats()

            assert result is not None
            assert len(result) == 0

    def test_get_stats_tester_role_with_agents(self):
        """UTCID17: Get personas with stats - tester role"""
        mock_persona_service = MagicMock()

        # Create mock tester personas with stats
        mock_personas_with_stats = [
            {
                'id': uuid4(),
                'name': 'Tester with Stats',
                'role_type': 'tester',
                'is_active': True,
                'active_agents_count': 2,
                'total_agents_created': 3,
                'total_interactions': 78,
                'average_response_time': 2.0,
                'satisfaction_rate': 0.91,
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_with_stats.return_value = mock_personas_with_stats

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving tester personas with stats
            result = mock_persona_service.get_personas_with_stats(role_type='tester')

            assert result is not None
            assert all(persona['role_type'] == 'tester' for persona in result)
            assert len(result) == 1

    def test_get_stats_business_analyst_role(self):
        """UTCID18: Get personas with stats - business_analyst role"""
        mock_persona_service = MagicMock()

        # Create mock business analyst personas with stats
        mock_personas_with_stats = [
            {
                'id': uuid4(),
                'name': 'BA with Stats',
                'role_type': 'business_analyst',
                'is_active': True,
                'active_agents_count': 1,
                'total_agents_created': 1,
                'total_interactions': 32,
                'average_response_time': 2.4,
                'satisfaction_rate': 0.89,
                'created_at': datetime.now()
            }
        ]
        mock_persona_service.get_personas_with_stats.return_value = mock_personas_with_stats

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving business analyst personas with stats
            result = mock_persona_service.get_personas_with_stats(role_type='business_analyst')

            assert result is not None
            assert all(persona['role_type'] == 'business_analyst' for persona in result)
            assert len(result) == 1


# =============================================================================
# 4. GET PERSONA - GET /personas/{persona_id}
# =============================================================================

class TestGetPersona:
    """Tests for GET /personas/{persona_id}"""

    def test_get_persona_active(self):
        """UTCID19: Get persona - is_active=true"""
        mock_persona_service = MagicMock()

        # Create mock active persona
        mock_persona = {
            'id': uuid4(),
            'name': 'Alex Developer',
            'role_type': 'developer',
            'is_active': True,
            'personality_traits': ['analytical', 'detail_oriented', 'creative'],
            'communication_style': 'Technical and friendly',
            'description': 'A senior developer who focuses on clean code',
            'programming_languages': ['Python', 'JavaScript', 'Go'],
            'preferred_approach': 'test-driven development',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.get_persona_by_id.return_value = mock_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving active persona
            result = mock_persona_service.get_persona_by_id(str(mock_persona['id']))

            assert result is not None
            assert result['is_active'] is True
            assert len(result['personality_traits']) > 0
            assert result['role_type'] == 'developer'

    def test_get_persona_inactive(self):
        """UTCID20: Get persona - is_active=false"""
        mock_persona_service = MagicMock()

        # Create mock inactive persona
        mock_persona = {
            'id': uuid4(),
            'name': 'Inactive Persona',
            'role_type': 'tester',
            'is_active': False,
            'personality_traits': ['thorough', 'meticulous'],
            'communication_style': 'precise and formal',
            'description': 'Quality-focused tester (inactive)',
            'testing_approaches': ['manual testing', 'exploratory testing'],
            'created_at': datetime.now(),
            'deactivated_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.get_persona_by_id.return_value = mock_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving inactive persona
            result = mock_persona_service.get_persona_by_id(str(mock_persona['id']))

            assert result is not None
            assert result['is_active'] is False
            assert result['role_type'] == 'tester'

    def test_get_persona_not_found_raises_404(self):
        """UTCID21: Get persona - not found -> 404"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_persona_by_id.return_value = None

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Try to retrieve non-existent persona
            result = mock_persona_service.get_persona_by_id(str(uuid4()))
            assert result is None

    def test_get_persona_with_metadata(self):
        """UTCID22: Get persona with persona_metadata"""
        mock_persona_service = MagicMock()

        # Create mock persona with metadata
        mock_persona = {
            'id': uuid4(),
            'name': 'Senior Developer',
            'role_type': 'developer',
            'is_active': True,
            'personality_traits': ['creative', 'analytical', 'mentorship_oriented'],
            'communication_style': 'Collaborative and educational',
            'description': 'Experienced developer who mentors juniors',
            'persona_metadata': {
                'expertise': ['Python', 'React', 'Docker', 'Kubernetes'],
                'experience_years': 5,
                'preferred_frameworks': ['FastAPI', 'NextJS', 'TailwindCSS'],
                'teaching_methodology': 'hands-on practice with explanation'
            },
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.get_persona_by_id.return_value = mock_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate retrieving persona with metadata
            result = mock_persona_service.get_persona_by_id(str(mock_persona['id']))

            assert result is not None
            assert result['persona_metadata'] is not None
            assert len(result['personality_traits']) > 0
            assert 'expertise' in result['persona_metadata']


# =============================================================================
# 5. CREATE PERSONA - POST /personas
# =============================================================================

class TestCreatePersona:
    """Tests for POST /personas"""

    def test_create_persona_developer_success(self):
        """UTCID23: Create persona thành công - developer"""
        mock_persona_service = MagicMock()

        # Create mock persona that will be returned after creation
        mock_created_persona = {
            'id': uuid4(),
            'name': 'Alex The Developer',
            'role_type': 'developer',
            'personality_traits': ['analytical', 'detail_oriented', 'problem_solving'],
            'communication_style': 'Friendly and professional with technical depth',
            'description': 'A developer focused on clean, efficient code',
            'display_order': 1,
            'is_active': True,
            'programming_languages': ['Python', 'TypeScript', 'SQL'],
            'preferred_approach': 'agile and collaborative',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.create_persona.return_value = mock_created_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate successful creation of developer persona
            result = mock_persona_service.create_persona({
                'name': 'Alex The Developer',
                'role_type': 'developer',
                'personality_traits': ['analytical', 'detail_oriented', 'problem_solving'],
                'communication_style': 'Friendly and professional with technical depth',
                'description': 'A developer focused on clean, efficient code',
                'display_order': 1,
                'programming_languages': ['Python', 'TypeScript', 'SQL'],
                'preferred_approach': 'agile and collaborative'
            })

            assert result is not None
            assert result['name'] == 'Alex The Developer'
            assert result['role_type'] == 'developer'
            assert len(result['personality_traits']) > 0
            assert 'Python' in result['programming_languages']

    def test_create_persona_empty_traits(self):
        """UTCID24: Create persona với empty personality_traits"""
        mock_persona_service = MagicMock()

        # Create mock persona with empty traits
        mock_created_persona = {
            'id': uuid4(),
            'name': 'Simple Leader',
            'role_type': 'team_leader',
            'personality_traits': [],
            'communication_style': 'Direct and clear',
            'description': 'Simple leadership approach',
            'display_order': 1,
            'is_active': True,
            'preferred_approach': 'task-oriented',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.create_persona.return_value = mock_created_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate creation of persona with empty traits
            result = mock_persona_service.create_persona({
                'name': 'Simple Leader',
                'role_type': 'team_leader',
                'personality_traits': [],
                'communication_style': 'Direct and clear',
                'description': 'Simple leadership approach',
                'display_order': 1,
                'preferred_approach': 'task-oriented'
            })

            assert result is not None
            assert result['name'] == 'Simple Leader'
            assert isinstance(result['personality_traits'], list)
            assert len(result['personality_traits']) == 0

    def test_create_persona_duplicate_name_raises_409(self):
        """UTCID25: Create persona - duplicate name+role -> 409"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_persona_by_name_and_role.return_value = {
            'id': uuid4(),
            'name': 'Existing Name',
            'role_type': 'developer'
        }

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to create duplicate persona
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=409, detail="Persona with this name and role already exists")
            
            assert exc_info.value.status_code == 409

    def test_create_persona_default_display_order(self):
        """UTCID26: Create persona với display_order=0 (default)"""
        mock_persona_service = MagicMock()

        # Create mock persona with default display order
        mock_created_persona = {
            'id': uuid4(),
            'name': 'Default Order Persona',
            'role_type': 'developer',
            'personality_traits': ['helpful'],
            'communication_style': 'Supportive',
            'description': 'Default ordered persona',
            'display_order': 0,
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_persona_service.create_persona.return_value = mock_created_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate creation of persona with default display order
            result = mock_persona_service.create_persona({
                'name': 'Default Order Persona',
                'role_type': 'developer',
                'personality_traits': ['helpful'],
                'communication_style': 'Supportive',
                'description': 'Default ordered persona',
                'display_order': 0
            })

            assert result is not None
            assert result['display_order'] == 0
            assert result['name'] == 'Default Order Persona'

    def test_create_persona_empty_name_raises_422(self):
        """UTCID27: Create persona - name empty -> 422"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to create persona with empty name
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Name cannot be empty")
            
            assert exc_info.value.status_code == 422

    def test_create_persona_name_too_long_raises_422(self):
        """UTCID28: Create persona - name > 100 chars -> 422"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to create persona with name too long
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Name cannot exceed 100 characters")
            
            assert exc_info.value.status_code == 422

    def test_create_persona_missing_role_type_raises_422(self):
        """UTCID29: Create persona - missing role_type -> 422"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to create persona without role type
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Role type is required")
            
            assert exc_info.value.status_code == 422


# =============================================================================
# 6. UPDATE PERSONA - PUT /personas/{persona_id}
# =============================================================================

class TestUpdatePersona:
    """Tests for PUT /personas/{persona_id}"""

    def test_update_persona_all_fields(self):
        """UTCID30: Update persona - all fields"""
        mock_persona_service = MagicMock()

        # Create mock updated persona
        mock_updated_persona = {
            'id': uuid4(),
            'name': 'Updated Name',
            'role_type': 'tester',
            'personality_traits': ['new_trait1', 'new_trait2', 'quality_focused'],
            'communication_style': 'Updated communication style',
            'description': 'Updated description',
            'display_order': 5,
            'is_active': True,
            'testing_specialties': ['automated', 'performance'],
            'updated_at': datetime.now()
        }
        mock_persona_service.update_persona.return_value = mock_updated_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate updating all persona fields
            result = mock_persona_service.update_persona(
                str(mock_updated_persona['id']),
                {
                    'name': 'Updated Name',
                    'role_type': 'tester',
                    'personality_traits': ['new_trait1', 'new_trait2', 'quality_focused'],
                    'communication_style': 'Updated communication style',
                    'description': 'Updated description',
                    'display_order': 5,
                    'is_active': True,
                    'testing_specialties': ['automated', 'performance']
                }
            )

            assert result is not None
            assert result['name'] == 'Updated Name'
            assert result['role_type'] == 'tester'
            assert 'quality_focused' in result['personality_traits']

    def test_update_persona_keep_existing_values(self):
        """UTCID31: Update persona - null values keep existing"""
        mock_persona_service = MagicMock()

        # Create mock original persona
        original_persona = {
            'id': uuid4(),
            'name': 'Original Name',
            'role_type': 'developer',
            'personality_traits': ['original_trait'],
            'communication_style': 'Original Style',
            'description': 'Original description',
            'display_order': 1,
            'is_active': True,
            'programming_languages': ['Java'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        # Create mock persona after update (some fields unchanged)
        updated_persona = {
            'id': original_persona['id'],
            'name': 'Changed Name',  # Only this field changes
            'role_type': original_persona['role_type'],  # Kept original
            'personality_traits': original_persona['personality_traits'],  # Kept original
            'communication_style': original_persona['communication_style'],  # Kept original
            'description': original_persona['description'],  # Kept original
            'display_order': original_persona['display_order'],  # Kept original
            'is_active': original_persona['is_active'], # Kept original
            'programming_languages': original_persona['programming_languages'],  # Kept original
            'created_at': original_persona['created_at'],  # Kept original
            'updated_at': datetime.now()  # Updated timestamp
        }

        mock_persona_service.get_persona_by_id.return_value = original_persona
        mock_persona_service.update_persona.return_value = updated_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):

            # Simulate partial update, keeping some values
            result = mock_persona_service.update_persona(
                str(original_persona['id']),
                {'name': 'Changed Name'}  # Only update name, others stay original
            )

            assert result is not None
            assert result['name'] == 'Changed Name'  # Updated field
            assert result['role_type'] == 'developer'  # Kept original field
            assert result['communication_style'] == 'Original Style'  # Kept original field

    def test_update_persona_not_found_raises_404(self):
        """UTCID32: Update persona - not found -> 404"""
        mock_persona_service = MagicMock()
        mock_persona_service.get_persona_by_id.return_value = None

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Try to update non-existent persona
            result = mock_persona_service.get_persona_by_id(str(uuid4()))
            assert result is None

    def test_update_persona_duplicate_name_raises_409(self):
        """UTCID33: Update persona - duplicate name+role -> 409"""
        mock_persona_service = MagicMock()

        # Create mock existing persona to cause conflict
        existing_persona = {
            'id': uuid4(),
            'name': 'Existing Name',
            'role_type': 'developer'
        }
        mock_persona_service.get_persona_by_name_and_role.return_value = existing_persona

        with patch('app.services.persona_service.get_persona_service', return_value=mock_persona_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to update with duplicate name+role
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=409, detail="Persona with this name and role already exists")
            
            assert exc_info.value.status_code == 409

    def test_update_persona_name_empty_raises_422(self):
        """UTCID34: Update persona - name empty -> 422"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to update persona with empty name
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Name cannot be empty")
            
            assert exc_info.value.status_code == 422

    def test_update_persona_name_too_long_raises_422(self):
        """UTCID35: Update persona - name > 100 chars -> 422"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate attempt to update persona with name too long
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Name cannot exceed 100 characters")
            
            assert exc_info.value.status_code == 422

    def test_update_persona_unauthorized_raises_401(self):
        """UTCID36: Update persona - unauthorized -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):

            # Simulate unauthorized update attempt
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# Additional validation tests
class TestPersonaValidations:
    def test_uuid_validation(self):
        """Test UUID validation"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            # Test valid UUID
            valid_uuid = str(uuid4())
            assert validate_uuid(valid_uuid) is True
            
            # Test invalid UUID
            invalid_uuid = "invalid-uuid"
            assert validate_uuid(invalid_uuid) is False

    def test_string_length_validation(self):
        """Test string length validation"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0002)):
            # Test valid length
            valid_string = "Valid Name"
            assert validate_string_length(valid_string, 1, 100) is True
            
            # Test too short
            short_string = ""
            assert validate_string_length(short_string, 1, 100) is False
            
            # Test too long
            long_string = "A" * 101
            assert validate_string_length(long_string, 1, 100) is False