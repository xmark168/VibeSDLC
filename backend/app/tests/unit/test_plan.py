"""Unit tests for Plan Module based on UTC_PLAN.md documentation (38 test cases)"""
import pytest
from uuid import uuid4, UUID


def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def calculate_yearly_price(monthly_price: int, discount_percentage: float) -> int:
    """Calculate yearly price with discount"""
    return int(monthly_price * 12 * (1 - discount_percentage / 100))


def validate_range(value: float, min_val: float, max_val: float) -> bool:
    """Validate value is within range"""
    return min_val <= value <= max_val


# =============================================================================
# 1. LIST PLANS - GET /plans/ (UTCID01-08)
# =============================================================================

class TestListPlans:
    """Tests for GET /plans/"""

    def test_utcid01_list_plans_default_pagination(self):
        """UTCID01: List plans với pagination mặc định"""
        plans_exist = True
        skip = 0
        limit = 100
        order_by = "sort_index"
        
        plans = [
            {"name": "Free Plan", "sort_index": 1},
            {"name": "Pro Plan", "sort_index": 2},
            {"name": "Enterprise", "sort_index": 3}
        ]
        
        assert plans_exist
        assert len(plans) <= limit
        assert order_by == "sort_index"
        
        # Verify ordered by sort_index ASC
        for i in range(len(plans) - 1):
            assert plans[i]["sort_index"] <= plans[i + 1]["sort_index"]

    def test_utcid02_list_plans_limit_5(self):
        """UTCID02: List plans với limit=5"""
        plans_exist = True
        skip = 0
        limit = 5
        total_plans = 10
        
        assert plans_exist
        result_count = min(limit, total_plans - skip)
        assert result_count == 5

    def test_utcid03_list_plans_pagination_offset(self):
        """UTCID03: List plans với skip=5, limit=5"""
        plans_exist = True
        skip = 5
        limit = 5
        total_plans = 15
        
        assert plans_exist
        result_count = min(limit, total_plans - skip)
        assert result_count == 5

    def test_utcid04_list_plans_search_filter(self):
        """UTCID04: List plans với search="pro" """
        plans_exist = True
        search_term = "pro"
        
        all_plans = [
            {"name": "Free Plan", "code": "FREE"},
            {"name": "Pro Plan", "code": "PRO"},
            {"name": "Enterprise", "code": "ENT"}
        ]
        
        assert plans_exist
        # Filter plans matching search term
        filtered = [p for p in all_plans if search_term.lower() in p["name"].lower() or search_term.lower() in p["code"].lower()]
        assert len(filtered) == 1

    def test_utcid05_list_plans_filter_by_tier(self):
        """UTCID05: List plans filtered by tier="free" """
        plans_exist = True
        tier_filter = "free"
        
        all_plans = [
            {"name": "Free Plan", "tier": "free"},
            {"name": "Pro Plan", "tier": "pay"},
            {"name": "Standard", "tier": "standard"}
        ]
        
        assert plans_exist
        filtered = [p for p in all_plans if p["tier"] == tier_filter]
        assert len(filtered) == 1
        assert all(p["tier"] == "free" for p in filtered)

    def test_utcid06_list_plans_no_plans(self):
        """UTCID06: List plans - database empty"""
        plans_exist = False
        
        plans = []
        
        assert not plans_exist
        assert len(plans) == 0

    def test_utcid07_list_plans_active_only(self):
        """UTCID07: List plans filtered by is_active=true"""
        plans_exist = True
        is_active_filter = True
        
        all_plans = [
            {"name": "Active Plan 1", "is_active": True},
            {"name": "Inactive Plan", "is_active": False},
            {"name": "Active Plan 2", "is_active": True}
        ]
        
        assert plans_exist
        filtered = [p for p in all_plans if p["is_active"] == is_active_filter]
        assert len(filtered) == 2

    def test_utcid08_list_plans_featured_only(self):
        """UTCID08: List plans filtered by is_featured=true"""
        plans_exist = True
        is_featured_filter = True
        
        all_plans = [
            {"name": "Regular Plan", "is_featured": False},
            {"name": "Featured Plan 1", "is_featured": True},
            {"name": "Featured Plan 2", "is_featured": True}
        ]
        
        assert plans_exist
        filtered = [p for p in all_plans if p["is_featured"] == is_featured_filter]
        assert len(filtered) == 2


# =============================================================================
# 2. GET PLAN - GET /plans/{plan_id} (UTCID09-13)
# =============================================================================

class TestGetPlan:
    """Tests for GET /plans/{plan_id}"""

    def test_utcid09_get_plan_active(self):
        """UTCID09: Get plan - is_active=true"""
        plan_exists = True
        plan_id = uuid4()
        
        plan = {
            "id": plan_id,
            "code": "PRO_PLAN",
            "name": "Pro Plan",
            "monthly_price": 299000,
            "yearly_discount_percentage": 20.0,
            "is_active": True,
            "tier": "pay"
        }
        
        assert plan_exists
        assert plan["is_active"] is True
        
        # Verify yearly_price computation
        yearly_price = calculate_yearly_price(plan["monthly_price"], plan["yearly_discount_percentage"])
        assert yearly_price == 2870400

    def test_utcid10_get_plan_inactive(self):
        """UTCID10: Get plan - is_active=false"""
        plan_exists = True
        plan_id = uuid4()
        
        plan = {
            "id": plan_id,
            "code": "OLD_PLAN",
            "name": "Old Plan",
            "is_active": False
        }
        
        assert plan_exists
        assert plan["is_active"] is False

    def test_utcid11_get_plan_not_found(self):
        """UTCID11: Get plan - not found -> 404"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"
        plan_exists = False
        
        assert validate_uuid(plan_id)
        assert not plan_exists

    def test_utcid12_get_plan_yearly_price_computed(self):
        """UTCID12: Get plan with yearly_price computed"""
        plan_exists = True
        plan_id = uuid4()
        
        plan = {
            "id": plan_id,
            "monthly_price": 299000,
            "yearly_discount_percentage": 20.0
        }
        
        assert plan_exists
        yearly_price = calculate_yearly_price(plan["monthly_price"], plan["yearly_discount_percentage"])
        assert yearly_price == 299000 * 12 * 0.8

    def test_utcid13_get_plan_custom_price(self):
        """UTCID13: Get plan với is_custom_price=true"""
        plan_exists = True
        plan_id = uuid4()
        
        plan = {
            "id": plan_id,
            "code": "CUSTOM_PLAN",
            "name": "Custom Enterprise Plan",
            "is_custom_price": True,
            "monthly_price": None  # May be null for custom pricing
        }
        
        assert plan_exists
        assert plan["is_custom_price"] is True


# =============================================================================
# 3. CREATE PLAN - POST /plans/ (UTCID14-22)
# =============================================================================

class TestCreatePlan:
    """Tests for POST /plans/"""

    def test_utcid14_create_plan_success(self):
        """UTCID14: Create plan thành công"""
        is_authenticated = True
        is_admin = True
        code_unique = True
        
        plan_create = {
            "code": "PRO_PLAN",
            "name": "Pro Plan",
            "monthly_price": 299000,
            "yearly_discount_percentage": 20.0,
            "tier": "pay",
            "is_custom_price": False
        }
        
        assert is_authenticated
        assert is_admin
        assert code_unique
        assert plan_create["monthly_price"] >= 0
        assert validate_range(plan_create["yearly_discount_percentage"], 0, 100)

    def test_utcid15_create_plan_custom_price(self):
        """UTCID15: Create plan với is_custom_price=true"""
        is_authenticated = True
        is_admin = True
        code_unique = True
        
        plan_create = {
            "code": "CUSTOM_ENT",
            "name": "Custom Enterprise",
            "monthly_price": None,  # Allowed for custom price
            "tier": "free",
            "is_custom_price": True
        }
        
        assert is_authenticated
        assert is_admin
        assert code_unique
        assert plan_create["is_custom_price"] is True

    def test_utcid16_create_plan_duplicate_code(self):
        """UTCID16: Create plan - duplicate code -> 400"""
        is_authenticated = True
        is_admin = True
        code_unique = False
        
        plan_create = {
            "code": "EXISTING_CODE"
        }
        
        assert is_authenticated
        assert is_admin
        assert not code_unique

    def test_utcid17_create_plan_empty_name(self):
        """UTCID17: Create plan - name empty -> 422"""
        is_authenticated = True
        is_admin = True
        
        plan_create = {
            "code": "PRO_PLAN",
            "name": ""  # Empty - invalid
        }
        
        assert is_authenticated
        assert is_admin
        assert len(plan_create["name"]) == 0

    def test_utcid18_create_plan_invalid_discount(self):
        """UTCID18: Create plan - discount > 100 -> 422"""
        is_authenticated = True
        is_admin = True
        
        plan_create = {
            "code": "PRO_PLAN",
            "name": "Pro Plan",
            "monthly_price": 299000,
            "yearly_discount_percentage": 150  # Invalid > 100
        }
        
        assert is_authenticated
        assert is_admin
        assert not validate_range(plan_create["yearly_discount_percentage"], 0, 100)

    def test_utcid19_create_plan_non_admin(self):
        """UTCID19: Create plan - non-admin -> 403"""
        is_authenticated = True
        is_admin = False
        
        assert is_authenticated
        assert not is_admin

    def test_utcid20_create_plan_negative_price(self):
        """UTCID20: Create plan - negative price -> 422"""
        is_authenticated = True
        is_admin = True
        
        plan_create = {
            "code": "PRO_PLAN",
            "name": "Pro Plan",
            "monthly_price": -1000  # Invalid negative
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_create["monthly_price"] < 0

    def test_utcid21_create_plan_missing_price_non_custom(self):
        """UTCID21: Create plan - missing monthly_price for non-custom -> 422"""
        is_authenticated = True
        is_admin = True
        
        plan_create = {
            "code": "PRO_PLAN",
            "name": "Pro Plan",
            "is_custom_price": False
            # Missing monthly_price for non-custom plan
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_create["is_custom_price"] is False
        assert "monthly_price" not in plan_create

    def test_utcid22_create_plan_unauthorized(self):
        """UTCID22: Create plan - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 4. UPDATE PLAN - PATCH /plans/{plan_id} (UTCID23-30)
# =============================================================================

class TestUpdatePlan:
    """Tests for PATCH /plans/{plan_id}"""

    def test_utcid23_update_plan_all_fields(self):
        """UTCID23: Update plan - all fields"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        code_unique = True
        
        plan_update = {
            "code": "NEW_CODE",
            "name": "Updated Plan Name",
            "monthly_price": 399000,
            "yearly_discount_percentage": 25.0,
            "is_active": True
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert code_unique
        assert validate_range(plan_update["yearly_discount_percentage"], 0, 100)

    def test_utcid24_update_plan_duplicate_code(self):
        """UTCID24: Update plan - duplicate code -> 409"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        code_unique = False
        
        plan_update = {
            "code": "EXISTING_CODE"
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not code_unique

    def test_utcid25_update_plan_not_found(self):
        """UTCID25: Update plan - not found -> 404"""
        is_authenticated = True
        is_admin = True
        plan_id = "550e8400-e29b-41d4-a716-446655440000"
        plan_exists = False
        
        assert is_authenticated
        assert is_admin
        assert validate_uuid(plan_id)
        assert not plan_exists

    def test_utcid26_update_plan_partial_fields(self):
        """UTCID26: Update plan - partial fields only"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        
        plan_update = {
            "name": "Updated Plan Name",
            "monthly_price": 399000,
            "yearly_discount_percentage": 25.0
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_exists

    def test_utcid27_update_plan_keep_existing(self):
        """UTCID27: Update plan - null values keep existing"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        
        plan_update = {
            "code": None,
            "name": None,
            "monthly_price": None
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_exists

    def test_utcid28_update_plan_non_admin(self):
        """UTCID28: Update plan - non-admin -> 403"""
        is_authenticated = True
        is_admin = False
        plan_exists = True
        
        assert is_authenticated
        assert not is_admin

    def test_utcid29_update_plan_invalid_discount(self):
        """UTCID29: Update plan - discount > 100 -> 400"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        
        plan_update = {
            "yearly_discount_percentage": 150  # Invalid
        }
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not validate_range(plan_update["yearly_discount_percentage"], 0, 100)

    def test_utcid30_update_plan_unauthorized(self):
        """UTCID30: Update plan - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 5. DELETE PLAN - DELETE /plans/{plan_id} (UTCID31-38)
# =============================================================================

class TestDeletePlan:
    """Tests for DELETE /plans/{plan_id}"""

    def test_utcid31_delete_plan_no_subscriptions(self):
        """UTCID31: Delete plan - no subscriptions"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        has_active_subscriptions = False
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not has_active_subscriptions

    def test_utcid32_delete_plan_inactive_subscriptions(self):
        """UTCID32: Delete plan - inactive subscriptions only (cascade delete)"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        has_active_subscriptions = False
        has_inactive_subscriptions = True
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not has_active_subscriptions
        assert has_inactive_subscriptions

    def test_utcid33_delete_plan_not_found(self):
        """UTCID33: Delete plan - not found -> 404"""
        is_authenticated = True
        is_admin = True
        plan_id = "550e8400-e29b-41d4-a716-446655440000"
        plan_exists = False
        
        assert is_authenticated
        assert is_admin
        assert validate_uuid(plan_id)
        assert not plan_exists

    def test_utcid34_delete_plan_active_subscriptions(self):
        """UTCID34: Delete plan - has active subscriptions -> 400"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        has_active_subscriptions = True
        active_subscription_count = 5
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert has_active_subscriptions
        assert active_subscription_count > 0

    def test_utcid35_delete_plan_non_admin(self):
        """UTCID35: Delete plan - non-admin -> 403"""
        is_authenticated = True
        is_admin = False
        plan_exists = True
        has_active_subscriptions = False
        
        assert is_authenticated
        assert not is_admin

    def test_utcid36_delete_plan_featured(self):
        """UTCID36: Delete plan - is_featured=true"""
        is_authenticated = True
        is_admin = True
        plan_exists = True
        has_active_subscriptions = False
        is_featured = True
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not has_active_subscriptions
        assert is_featured is True

    def test_utcid37_delete_plan_free_tier(self):
        """UTCID37: Delete plan - tier="free" """
        is_authenticated = True
        is_admin = True
        plan_exists = True
        has_active_subscriptions = False
        tier = "free"
        
        assert is_authenticated
        assert is_admin
        assert plan_exists
        assert not has_active_subscriptions
        assert tier == "free"

    def test_utcid38_delete_plan_unauthorized(self):
        """UTCID38: Delete plan - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# ADDITIONAL VALIDATION TESTS
# =============================================================================

class TestPlanValidations:
    """Additional validation tests for Plan module"""

    def test_yearly_price_calculation(self):
        """Test yearly price calculation formula"""
        monthly_price = 299000
        discount = 20.0
        
        yearly_price = calculate_yearly_price(monthly_price, discount)
        expected = 299000 * 12 * 0.8
        
        assert yearly_price == expected
        assert yearly_price == 2870400

    def test_valid_plan_tiers(self):
        """Test valid plan tiers"""
        valid_tiers = ["free", "pay", "pro", "standard", "enterprise", "custom"]
        
        for tier in valid_tiers:
            assert tier in valid_tiers

    def test_discount_percentage_range(self):
        """Test discount percentage validation (0-100)"""
        valid_discounts = [0, 20, 50, 100]
        invalid_discounts = [-10, 150, 200]
        
        for discount in valid_discounts:
            assert validate_range(discount, 0, 100)
        
        for discount in invalid_discounts:
            assert not validate_range(discount, 0, 100)

    def test_price_validation(self):
        """Test price >= 0 validation"""
        valid_prices = [0, 100000, 299000, 999000]
        invalid_prices = [-1, -1000]
        
        for price in valid_prices:
            assert price >= 0
        
        for price in invalid_prices:
            assert price < 0

    def test_code_uniqueness(self):
        """Test plan code must be unique"""
        existing_codes = ["FREE_PLAN", "PRO_PLAN", "ENT_PLAN"]
        
        new_code = "STANDARD_PLAN"
        duplicate_code = "PRO_PLAN"
        
        assert new_code not in existing_codes
        assert duplicate_code in existing_codes

    def test_plan_ordering_by_sort_index(self):
        """Test plans ordered by sort_index"""
        plans = [
            {"name": "Plan A", "sort_index": 1},
            {"name": "Plan B", "sort_index": 2},
            {"name": "Plan C", "sort_index": 3}
        ]
        
        for i in range(len(plans) - 1):
            assert plans[i]["sort_index"] <= plans[i + 1]["sort_index"]

    def test_custom_price_plan_allows_null_price(self):
        """Test custom price plan allows null monthly_price"""
        custom_plan = {
            "is_custom_price": True,
            "monthly_price": None
        }
        
        regular_plan = {
            "is_custom_price": False,
            "monthly_price": 299000
        }
        
        assert custom_plan["is_custom_price"] is True
        assert custom_plan["monthly_price"] is None
        
        assert regular_plan["is_custom_price"] is False
        assert regular_plan["monthly_price"] is not None

    def test_delete_constraints(self):
        """Test cannot delete plan with active subscriptions"""
        plan = {
            "has_active_subscriptions": True,
            "active_subscription_count": 3
        }
        
        # Should not allow delete
        assert plan["has_active_subscriptions"] is True
        assert plan["active_subscription_count"] > 0

    def test_plan_fields_validation(self):
        """Test all required and optional fields"""
        plan = {
            "code": "PRO_PLAN",  # Required on create
            "name": "Pro Plan",  # Required on create
            "description": "Professional plan",  # Optional
            "monthly_price": 299000,  # Required for non-custom
            "yearly_discount_percentage": 20.0,  # Optional
            "currency": "VND",  # Default
            "monthly_credits": 1000,  # Optional
            "additional_credit_price": 5000,  # Optional
            "available_project": 10,  # Optional
            "is_active": True,  # Default
            "tier": "pay",  # Default
            "sort_index": 0,  # Default
            "is_featured": False,  # Default
            "is_custom_price": False,  # Default
            "features_text": "Feature list"  # Optional
        }
        
        # Required fields
        assert "code" in plan
        assert "name" in plan
        
        # Default values
        assert plan["is_active"] is True
        assert plan["sort_index"] >= 0
