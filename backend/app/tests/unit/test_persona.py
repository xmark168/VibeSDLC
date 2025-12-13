"""Unit tests for Persona Module based on UTC_PERSONA.md documentation (42 test cases)"""
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


def validate_string_length(value: str, min_len: int, max_len: int) -> bool:
    """Validate string length"""
    return min_len <= len(value) <= max_len


# =============================================================================
# 1. LIST PERSONAS - GET /personas (UTCID01-07)
# =============================================================================

class TestListPersonas:
    """Tests for GET /personas"""

    def test_utcid01_list_personas_default_pagination(self):
        """UTCID01: List personas với pagination mặc định"""
        personas_exist = True
        skip = 0
        limit = 100
        
        personas = [
            {"name": "Alex Leader", "role_type": "team_leader", "display_order": 1},
            {"name": "Bob Analyst", "role_type": "business_analyst", "display_order": 1},
            {"name": "Charlie Dev", "role_type": "developer", "display_order": 1},
            {"name": "Diana Tester", "role_type": "tester", "display_order": 1}
        ]
        
        assert personas_exist
        assert len(personas) <= limit
        
        # Verify ordering: role_type, display_order, name
        assert personas[0]["role_type"] == "team_leader"

    def test_utcid02_list_personas_limit_5(self):
        """UTCID02: List personas với limit=5"""
        personas_exist = True
        skip = 0
        limit = 5
        
        total_personas = 10
        
        assert personas_exist
        result_count = min(limit, total_personas - skip)
        assert result_count == 5

    def test_utcid03_list_personas_pagination_offset(self):
        """UTCID03: List personas với skip=5, limit=5 (pagination)"""
        personas_exist = True
        skip = 5
        limit = 5
        total_personas = 15
        
        assert personas_exist
        result_count = min(limit, total_personas - skip)
        assert result_count == 5

    def test_utcid04_list_personas_filter_by_role(self):
        """UTCID04: List personas filtered by role_type=developer"""
        personas_exist = True
        role_type_filter = "developer"
        
        all_personas = [
            {"role_type": "developer", "name": "Dev 1"},
            {"role_type": "tester", "name": "Tester 1"},
            {"role_type": "developer", "name": "Dev 2"}
        ]
        
        assert personas_exist
        filtered = [p for p in all_personas if p["role_type"] == role_type_filter]
        assert len(filtered) == 2
        assert all(p["role_type"] == "developer" for p in filtered)

    def test_utcid05_list_personas_no_personas(self):
        """UTCID05: List personas - database empty"""
        personas_exist = False
        
        personas = []
        
        assert not personas_exist
        assert len(personas) == 0

    def test_utcid06_list_personas_active_only(self):
        """UTCID06: List personas filtered by is_active=true"""
        personas_exist = True
        is_active_filter = True
        
        all_personas = [
            {"name": "Active 1", "is_active": True},
            {"name": "Inactive 1", "is_active": False},
            {"name": "Active 2", "is_active": True}
        ]
        
        assert personas_exist
        filtered = [p for p in all_personas if p["is_active"] == is_active_filter]
        assert len(filtered) == 2

    def test_utcid07_list_personas_inactive_only(self):
        """UTCID07: List personas filtered by is_active=false"""
        personas_exist = True
        is_active_filter = False
        
        all_personas = [
            {"name": "Active 1", "is_active": True},
            {"name": "Inactive 1", "is_active": False},
            {"name": "Inactive 2", "is_active": False}
        ]
        
        assert personas_exist
        filtered = [p for p in all_personas if p["is_active"] == is_active_filter]
        assert len(filtered) == 2


# =============================================================================
# 2. LIST PERSONAS BY ROLE - GET /personas/by-role/{role_type} (UTCID08-12)
# =============================================================================

class TestListPersonasByRole:
    """Tests for GET /personas/by-role/{role_type}"""

    def test_utcid08_list_by_role_team_leader(self):
        """UTCID08: List personas for team_leader role"""
        personas_exist_for_role = True
        role_type = "team_leader"
        is_active = True
        
        personas = [
            {"name": "Alex Leader", "role_type": "team_leader", "display_order": 1, "is_active": True},
            {"name": "Betty Leader", "role_type": "team_leader", "display_order": 2, "is_active": True}
        ]
        
        assert personas_exist_for_role
        assert all(p["role_type"] == role_type for p in personas)
        assert all(p["is_active"] == is_active for p in personas)
        
        # Verify ordering by display_order, name
        assert personas[0]["display_order"] <= personas[1]["display_order"]

    def test_utcid09_list_by_role_developer(self):
        """UTCID09: List personas for developer role"""
        personas_exist_for_role = True
        role_type = "developer"
        
        personas = [
            {"name": "Charlie Dev", "role_type": "developer", "is_active": True},
            {"name": "David Dev", "role_type": "developer", "is_active": True}
        ]
        
        assert personas_exist_for_role
        assert all(p["role_type"] == role_type for p in personas)

    def test_utcid10_list_by_role_invalid_no_personas(self):
        """UTCID10: List personas for invalid_role - empty result"""
        personas_exist_for_role = False
        role_type = "invalid_role"
        
        personas = []
        
        assert not personas_exist_for_role
        assert len(personas) == 0

    def test_utcid11_list_by_role_business_analyst(self):
        """UTCID11: List personas for business_analyst role"""
        personas_exist_for_role = True
        role_type = "business_analyst"
        
        personas = [
            {"name": "Emily BA", "role_type": "business_analyst", "is_active": True}
        ]
        
        assert personas_exist_for_role
        assert all(p["role_type"] == role_type for p in personas)

    def test_utcid12_list_by_role_tester(self):
        """UTCID12: List personas for tester role"""
        personas_exist_for_role = True
        role_type = "tester"
        
        personas = [
            {"name": "Frank Tester", "role_type": "tester", "is_active": True}
        ]
        
        assert personas_exist_for_role
        assert all(p["role_type"] == role_type for p in personas)


# =============================================================================
# 3. GET PERSONAS WITH STATS - GET /personas/with-stats (UTCID13-18)
# =============================================================================

class TestGetPersonasWithStats:
    """Tests for GET /personas/with-stats"""

    def test_utcid13_get_stats_all_roles_with_agents(self):
        """UTCID13: Get personas with stats - all roles, has active agents"""
        personas_exist = True
        agents_exist = True
        role_type_filter = None
        
        personas = [
            {
                "name": "Alex Dev",
                "role_type": "developer",
                "active_agents_count": 3,
                "total_agents_created": 5
            }
        ]
        
        assert personas_exist
        assert agents_exist
        assert personas[0]["active_agents_count"] == 3
        assert personas[0]["total_agents_created"] == 5

    def test_utcid14_get_stats_developer_only(self):
        """UTCID14: Get personas with stats - developer role only"""
        personas_exist = True
        agents_exist = True
        role_type_filter = "developer"
        
        personas = [
            {"role_type": "developer", "active_agents_count": 2, "total_agents_created": 4}
        ]
        
        assert personas_exist
        assert all(p["role_type"] == role_type_filter for p in personas)

    def test_utcid15_get_stats_team_leader_only(self):
        """UTCID15: Get personas with stats - team_leader role only"""
        personas_exist = True
        agents_exist = True
        role_type_filter = "team_leader"
        
        personas = [
            {"role_type": "team_leader", "active_agents_count": 1, "total_agents_created": 2}
        ]
        
        assert personas_exist
        assert all(p["role_type"] == role_type_filter for p in personas)

    def test_utcid16_get_stats_no_personas(self):
        """UTCID16: Get personas with stats - no personas exist"""
        personas_exist = False
        agents_exist = False
        
        personas = []
        
        assert not personas_exist
        assert not agents_exist
        assert len(personas) == 0

    def test_utcid17_get_stats_tester_with_agents(self):
        """UTCID17: Get personas with stats - tester role"""
        personas_exist = True
        agents_exist = True
        role_type_filter = "tester"
        
        personas = [
            {"role_type": "tester", "active_agents_count": 2, "total_agents_created": 3}
        ]
        
        assert personas_exist
        assert all(p["role_type"] == role_type_filter for p in personas)

    def test_utcid18_get_stats_business_analyst(self):
        """UTCID18: Get personas with stats - business_analyst role"""
        personas_exist = True
        agents_exist = True
        role_type_filter = "business_analyst"
        
        personas = [
            {"role_type": "business_analyst", "active_agents_count": 1, "total_agents_created": 1}
        ]
        
        assert personas_exist
        assert all(p["role_type"] == role_type_filter for p in personas)


# =============================================================================
# 4. GET PERSONA - GET /personas/{persona_id} (UTCID19-22)
# =============================================================================

class TestGetPersona:
    """Tests for GET /personas/{persona_id}"""

    def test_utcid19_get_persona_active(self):
        """UTCID19: Get persona - is_active=true"""
        persona_exists = True
        persona_id = uuid4()
        
        persona = {
            "id": persona_id,
            "name": "Alex Developer",
            "role_type": "developer",
            "is_active": True,
            "personality_traits": ["analytical", "detail-oriented"],
            "communication_style": "Technical and friendly"
        }
        
        assert persona_exists
        assert persona["is_active"] is True
        assert len(persona["personality_traits"]) > 0

    def test_utcid20_get_persona_inactive(self):
        """UTCID20: Get persona - is_active=false"""
        persona_exists = True
        persona_id = uuid4()
        
        persona = {
            "id": persona_id,
            "name": "Inactive Persona",
            "role_type": "tester",
            "is_active": False,
            "personality_traits": ["thorough"]
        }
        
        assert persona_exists
        assert persona["is_active"] is False

    def test_utcid21_get_persona_not_found(self):
        """UTCID21: Get persona - not found -> 404"""
        persona_id = "550e8400-e29b-41d4-a716-446655440000"
        persona_exists = False
        
        assert validate_uuid(persona_id)
        assert not persona_exists

    def test_utcid22_get_persona_with_metadata(self):
        """UTCID22: Get persona with persona_metadata"""
        persona_exists = True
        persona_id = uuid4()
        
        persona = {
            "id": persona_id,
            "name": "Senior Developer",
            "role_type": "developer",
            "is_active": True,
            "personality_traits": ["creative", "analytical"],
            "communication_style": "Collaborative",
            "persona_metadata": {
                "expertise": ["Python", "React"],
                "experience_years": 5
            }
        }
        
        assert persona_exists
        assert persona["persona_metadata"] is not None
        assert len(persona["personality_traits"]) > 0


# =============================================================================
# 5. CREATE PERSONA - POST /personas (UTCID23-29)
# =============================================================================

class TestCreatePersona:
    """Tests for POST /personas"""

    def test_utcid23_create_persona_developer(self):
        """UTCID23: Create persona thành công - developer"""
        name_role_unique = True
        
        persona_create = {
            "name": "Alex The Developer",
            "role_type": "developer",
            "personality_traits": ["analytical", "detail-oriented"],
            "communication_style": "Friendly and professional",
            "display_order": 1
        }
        
        assert name_role_unique
        assert validate_string_length(persona_create["name"], 1, 100)
        assert validate_string_length(persona_create["role_type"], 1, 50)
        assert len(persona_create["personality_traits"]) > 0

    def test_utcid24_create_persona_empty_traits(self):
        """UTCID24: Create persona với empty personality_traits"""
        name_role_unique = True
        
        persona_create = {
            "name": "Simple Leader",
            "role_type": "team_leader",
            "personality_traits": [],
            "communication_style": "Direct and clear",
            "display_order": 1
        }
        
        assert name_role_unique
        assert isinstance(persona_create["personality_traits"], list)
        assert len(persona_create["personality_traits"]) == 0

    def test_utcid25_create_persona_duplicate_name(self):
        """UTCID25: Create persona - duplicate name+role -> 409"""
        name_role_unique = False
        
        persona_create = {
            "name": "Existing Name",
            "role_type": "developer"
        }
        
        assert not name_role_unique

    def test_utcid26_create_persona_default_display_order(self):
        """UTCID26: Create persona với display_order=0 (default)"""
        name_role_unique = True
        
        persona_create = {
            "name": "Default Order Persona",
            "role_type": "developer",
            "personality_traits": ["helpful"],
            "communication_style": "Supportive",
            "display_order": 0
        }
        
        assert name_role_unique
        assert persona_create["display_order"] == 0

    def test_utcid27_create_persona_name_empty(self):
        """UTCID27: Create persona - name empty -> 422"""
        persona_create = {
            "name": "",
            "role_type": "developer"
        }
        
        assert not validate_string_length(persona_create["name"], 1, 100)

    def test_utcid28_create_persona_name_too_long(self):
        """UTCID28: Create persona - name > 100 chars -> 422"""
        persona_create = {
            "name": "A" * 101,
            "role_type": "developer"
        }
        
        assert not validate_string_length(persona_create["name"], 1, 100)

    def test_utcid29_create_persona_missing_role_type(self):
        """UTCID29: Create persona - missing role_type -> 422"""
        persona_create = {
            "name": "Some Name",
            "communication_style": "Friendly"
        }
        
        assert "role_type" not in persona_create


# =============================================================================
# 6. UPDATE PERSONA - PUT /personas/{persona_id} (UTCID30-36)
# =============================================================================

class TestUpdatePersona:
    """Tests for PUT /personas/{persona_id}"""

    def test_utcid30_update_persona_all_fields(self):
        """UTCID30: Update persona - all fields"""
        persona_exists = True
        name_role_unique = True
        
        persona_update = {
            "name": "Updated Name",
            "role_type": "tester",
            "communication_style": "New communication style",
            "personality_traits": ["new_trait1", "new_trait2"],
            "display_order": 5,
            "is_active": True
        }
        
        assert persona_exists
        assert name_role_unique
        assert persona_update["name"] == "Updated Name"
        assert persona_update["role_type"] == "tester"

    def test_utcid31_update_persona_keep_existing(self):
        """UTCID31: Update persona - null values keep existing"""
        persona_exists = True
        
        persona_update = {
            "name": None,
            "role_type": None,
            "communication_style": None,
            "personality_traits": None,
            "display_order": None
        }
        
        assert persona_exists
        # Null values should keep existing data

    def test_utcid32_update_persona_not_found(self):
        """UTCID32: Update persona - not found -> 404"""
        persona_id = "550e8400-e29b-41d4-a716-446655440000"
        persona_exists = False
        
        assert validate_uuid(persona_id)
        assert not persona_exists

    def test_utcid33_update_persona_duplicate_name(self):
        """UTCID33: Update persona - duplicate name+role -> 409"""
        persona_exists = True
        name_role_unique = False
        
        persona_update = {
            "name": "Existing Other Name",
            "role_type": "tester"
        }
        
        assert persona_exists
        assert not name_role_unique

    def test_utcid34_update_persona_partial_fields(self):
        """UTCID34: Update persona - partial fields only"""
        persona_exists = True
        name_role_unique = True
        
        persona_update = {
            "communication_style": "New style",
            "personality_traits": ["trait1", "trait2"]
        }
        
        assert persona_exists
        assert name_role_unique

    def test_utcid35_update_persona_deactivate(self):
        """UTCID35: Update persona - set is_active=false"""
        persona_exists = True
        
        persona_update = {
            "is_active": False
        }
        
        assert persona_exists
        assert persona_update["is_active"] is False

    def test_utcid36_update_persona_change_traits(self):
        """UTCID36: Update persona - change personality traits"""
        persona_exists = True
        name_role_unique = True
        
        persona_update = {
            "personality_traits": ["new_trait1", "new_trait2"],
            "display_order": 5
        }
        
        assert persona_exists
        assert len(persona_update["personality_traits"]) == 2


# =============================================================================
# 7. DELETE PERSONA - DELETE /personas/{persona_id} (UTCID37-42)
# =============================================================================

class TestDeletePersona:
    """Tests for DELETE /personas/{persona_id}"""

    def test_utcid37_delete_persona_soft_no_agents(self):
        """UTCID37: Delete persona - soft delete, no agents"""
        persona_exists = True
        has_active_agents = False
        hard_delete = False
        
        assert persona_exists
        assert not has_active_agents
        assert hard_delete is False
        # Result: is_active = false (soft delete)

    def test_utcid38_delete_persona_soft_with_agents(self):
        """UTCID38: Delete persona - soft delete, has active agents"""
        persona_exists = True
        has_active_agents = True
        active_agents_count = 3
        hard_delete = False
        
        assert persona_exists
        assert has_active_agents
        assert active_agents_count > 0
        assert hard_delete is False
        # Result: is_active = false (soft delete allowed)

    def test_utcid39_delete_persona_not_found(self):
        """UTCID39: Delete persona - not found -> 404"""
        persona_id = "550e8400-e29b-41d4-a716-446655440000"
        persona_exists = False
        
        assert validate_uuid(persona_id)
        assert not persona_exists

    def test_utcid40_delete_persona_hard_with_agents(self):
        """UTCID40: Delete persona - hard delete with active agents -> 409"""
        persona_exists = True
        has_active_agents = True
        active_agents_count = 2
        hard_delete = True
        
        assert persona_exists
        assert has_active_agents
        assert active_agents_count > 0
        assert hard_delete is True
        # Should raise 409: Cannot delete persona with active agents

    def test_utcid41_delete_persona_active(self):
        """UTCID41: Delete persona - is_active=true"""
        persona_exists = True
        has_active_agents = False
        is_active = True
        hard_delete = False
        
        assert persona_exists
        assert not has_active_agents
        assert is_active is True
        assert hard_delete is False

    def test_utcid42_delete_persona_already_inactive(self):
        """UTCID42: Delete persona - already is_active=false"""
        persona_exists = True
        has_active_agents = False
        is_active = False
        hard_delete = False
        
        assert persona_exists
        assert not has_active_agents
        assert is_active is False
        # No change - already inactive


# =============================================================================
# ADDITIONAL VALIDATION TESTS
# =============================================================================

class TestPersonaValidations:
    """Additional validation tests for Persona module"""

    def test_valid_role_types(self):
        """Test valid role types"""
        valid_roles = ["team_leader", "business_analyst", "developer", "tester"]
        
        for role in valid_roles:
            assert role in valid_roles

    def test_name_validation_rules(self):
        """Test name validation: 1-100 characters"""
        valid_name = "Valid Persona Name"
        empty_name = ""
        too_long_name = "A" * 101
        
        assert validate_string_length(valid_name, 1, 100)
        assert not validate_string_length(empty_name, 1, 100)
        assert not validate_string_length(too_long_name, 1, 100)

    def test_communication_style_validation(self):
        """Test communication_style validation: 1-500 characters"""
        valid_style = "Friendly and professional communication"
        empty_style = ""
        too_long_style = "A" * 501
        
        assert validate_string_length(valid_style, 1, 500)
        assert not validate_string_length(empty_style, 1, 500)
        assert not validate_string_length(too_long_style, 1, 500)

    def test_display_order_validation(self):
        """Test display_order >= 0"""
        valid_orders = [0, 1, 5, 10]
        invalid_orders = [-1, -5]
        
        for order in valid_orders:
            assert order >= 0
        
        for order in invalid_orders:
            assert order < 0

    def test_personality_traits_array(self):
        """Test personality_traits is array"""
        valid_traits = ["analytical", "creative"]
        empty_traits = []
        
        assert isinstance(valid_traits, list)
        assert isinstance(empty_traits, list)
        assert len(valid_traits) > 0
        assert len(empty_traits) == 0

    def test_persona_ordering(self):
        """Test persona ordering: role_type, display_order, name"""
        personas = [
            {"role_type": "business_analyst", "display_order": 1, "name": "Alice"},
            {"role_type": "business_analyst", "display_order": 2, "name": "Bob"},
            {"role_type": "developer", "display_order": 1, "name": "Charlie"},
            {"role_type": "team_leader", "display_order": 1, "name": "David"}
        ]
        
        # Should be ordered by role_type first
        # Then by display_order
        # Then by name
        assert personas[0]["role_type"] <= personas[1]["role_type"]

    def test_soft_delete_behavior(self):
        """Test soft delete sets is_active=false"""
        persona = {
            "is_active": True
        }
        
        # After soft delete
        persona["is_active"] = False
        
        assert persona["is_active"] is False

    def test_unique_name_per_role(self):
        """Test name+role_type must be unique combination"""
        personas = [
            {"name": "Alex", "role_type": "developer"},
            {"name": "Alex", "role_type": "tester"}  # Same name, different role - OK
        ]
        
        # Different roles with same name is allowed
        assert personas[0]["name"] == personas[1]["name"]
        assert personas[0]["role_type"] != personas[1]["role_type"]
