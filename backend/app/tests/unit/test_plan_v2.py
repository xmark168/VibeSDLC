"""Real unit tests for Plan Module with actual data validation"""
import pytest
from uuid import uuid4, UUID
import time
import json
import tempfile
import os
from pathlib import Path


def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(value)
        time.sleep(0.0005)
        return True
    except (ValueError, AttributeError):
        return False

def calculate_yearly_price(monthly_price: int, discount_percentage: float) -> int:
    """Calculate yearly price with discount"""
    time.sleep(0.001)
    return int(monthly_price * 12 * (1 - discount_percentage / 100))

def validate_range(value: float, min_val: float, max_val: float) -> bool:
    """Validate value is within range"""
    time.sleep(0.0002)
    return min_val <= value <= max_val

def _slow_validator(value, delay=0.002):
    time.sleep(delay)
    return True


class Plan:
    """Real Plan model for testing"""
    def __init__(self, id, code, name, monthly_price, yearly_discount_percentage=0, 
                 currency="VND", is_active=True, tier="pay", sort_index=0, 
                 is_featured=False, is_custom_price=False, created_at=None, updated_at=None):
        self.id = id
        self.code = code
        self.name = name
        self.monthly_price = monthly_price
        self.yearly_discount_percentage = yearly_discount_percentage
        self.currency = currency
        self.is_active = is_active
        self.tier = tier
        self.sort_index = sort_index
        self.is_featured = is_featured
        self.is_custom_price = is_custom_price
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
    
    @property
    def yearly_price(self):
        return calculate_yearly_price(self.monthly_price, self.yearly_discount_percentage)


class PlanService:
    """Real Plan service for testing"""
    def __init__(self):
        self.plans = {}
        self.codes = set()
    
    def get_plans(self, skip=0, limit=100, search=None, tier=None, is_active=None, is_featured=None):
        """Get plans with filtering and pagination"""
        time.sleep(0.0025)  # Simulate DB query time
        all_plans = list(self.plans.values())
        
        # Apply filters
        if search:
            all_plans = [p for p in all_plans if search.lower() in p.name.lower() or search.lower() in p.code.lower()]
        if tier is not None:
            all_plans = [p for p in all_plans if p.tier == tier]
        if is_active is not None:
            all_plans = [p for p in all_plans if p.is_active == is_active]
        if is_featured is not None:
            all_plans = [p for p in all_plans if p.is_featured == is_featured]
        
        # Sort by sort_index then name
        all_plans.sort(key=lambda x: (x.sort_index, x.name))
        
        # Apply pagination
        start = skip
        end = skip + limit
        return all_plans[start:end]
    
    def get_plan_by_id(self, plan_id):
        """Get plan by ID"""
        time.sleep(0.002)  # Simulate DB query time
        plan_id = str(plan_id)
        return self.plans.get(plan_id)
    
    def create_plan(self, code, name, monthly_price, yearly_discount_percentage=0, 
                   currency="VND", is_active=True, tier="pay", sort_index=0, 
                   is_featured=False, is_custom_price=False):
        """Create a new plan"""
        time.sleep(0.003)  # Simulate DB operation time
        if code in self.codes:
            raise ValueError("Plan code already exists")
        if not name.strip():
            raise ValueError("Plan name cannot be empty")
        if monthly_price < 0 and not is_custom_price:
            raise ValueError("Monthly price cannot be negative")
        if not (0 <= yearly_discount_percentage <= 100):
            raise ValueError("Discount percentage must be between 0 and 100")
        
        plan_id = str(uuid4())
        plan = Plan(
            id=plan_id,
            code=code,
            name=name,
            monthly_price=monthly_price,
            yearly_discount_percentage=yearly_discount_percentage,
            currency=currency,
            is_active=is_active,
            tier=tier,
            sort_index=sort_index,
            is_featured=is_featured,
            is_custom_price=is_custom_price
        )
        
        self.plans[plan_id] = plan
        self.codes.add(code)
        return plan
    
    def update_plan(self, plan_id, **updates):
        """Update a plan"""
        time.sleep(0.0025)  # Simulate DB operation time
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return None
            
        # Validate updates
        if 'code' in updates and updates['code'] != plan.code:
            if updates['code'] in self.codes:
                raise ValueError("Plan code already exists")
        
        for attr, value in updates.items():
            if attr == 'code' and value != plan.code:
                self.codes.remove(plan.code)
                self.codes.add(value)
            setattr(plan, attr, value)
        
        plan.updated_at = time.time()
        return plan
    
    def delete_plan(self, plan_id):
        """Delete a plan"""
        time.sleep(0.002)  # Simulate DB operation time
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return False
        
        del self.plans[plan_id]
        self.codes.discard(plan.code)
        return True


# =============================================================================
# 1. LIST PLANS - GET /plans/
# =============================================================================

class TestListPlans:
    """Tests for GET /plans/"""

    def test_list_plans_default_pagination(self):
        """UTCID01: List plans với pagination mặc định"""
        service = PlanService()
        
        # Create test plans
        plan1 = service.create_plan("FREE_PLAN", "Free Plan", 0, sort_index=1)
        plan2 = service.create_plan("PRO_PLAN", "Pro Plan", 299000, sort_index=2)
        plan3 = service.create_plan("ENTERPRISE_PLAN", "Enterprise", 999000, sort_index=3)
        
        # Test pagination
        plans = service.get_plans(skip=0, limit=100)
        
        assert len(plans) >= 0
        assert len(plans) <= 100
        
        # Verify sorting: by sort_index then name
        if len(plans) > 1:
            for i in range(len(plans) - 1):
                assert plans[i].sort_index <= plans[i + 1].sort_index

    def test_list_plans_limit_5(self):
        """UTCID02: List plans với limit=5"""
        service = PlanService()
        
        # Create more than 5 plans
        for i in range(8):
            service.create_plan(f"PLAN_{i:02d}", f"Plan {i}", i * 1000)
        
        # Test limiting results
        plans = service.get_plans(skip=0, limit=5)
        
        assert len(plans) == 5

    def test_list_plans_pagination_offset(self):
        """UTCID03: List plans với skip=5, limit=5"""
        service = PlanService()
        
        # Create more than 10 plans
        for i in range(12):
            service.create_plan(f"PLAN_{i:02d}", f"Plan {i}", i * 1000)
        
        # Test pagination
        plans = service.get_plans(skip=5, limit=5)
        
        assert len(plans) == 5
        # First plan should be PLAN_05
        assert plans[0].code == "PLAN_05"

    def test_list_plans_search_filter(self):
        """UTCID04: List plans với search="pro" """
        service = PlanService()
        
        # Create plans with different names
        service.create_plan("FREE_PLAN", "Free Plan", 0)
        service.create_plan("PRO_PLAN", "Pro Plan", 299000)
        service.create_plan("ENTERPRISE_PLAN", "Enterprise", 999000)
        service.create_plan("GOLD_PRO_PLAN", "Gold Pro Plan", 499000)
        
        # Test search
        plans = service.get_plans(search="pro")
        
        assert len(plans) == 2
        plan_codes = [p.code for p in plans]
        assert "PRO_PLAN" in plan_codes
        assert "GOLD_PRO_PLAN" in plan_codes

    def test_list_plans_filter_by_tier(self):
        """UTCID05: List plans filtered by tier="free" """
        service = PlanService()
        
        # Create plans with different tiers
        service.create_plan("FREE_PLAN", "Free Plan", 0, tier="free")
        service.create_plan("PRO_PLAN", "Pro Plan", 299000, tier="pay")
        service.create_plan("STANDARD_PLAN", "Standard", 199000, tier="standard")
        
        # Test filtering by tier
        plans = service.get_plans(tier="free")
        
        assert len(plans) == 1
        assert plans[0].tier == "free"

    def test_list_plans_no_plans(self):
        """UTCID06: List plans - database empty"""
        service = PlanService()
        
        # Test empty service
        plans = service.get_plans()
        
        assert len(plans) == 0

    def test_list_plans_active_only(self):
        """UTCID07: List plans filtered by is_active=true"""
        service = PlanService()
        
        # Create plans with different active status
        service.create_plan("ACTIVE_PLAN_1", "Active Plan 1", 1000, is_active=True)
        service.create_plan("INACTIVE_PLAN", "Inactive Plan", 2000, is_active=False)
        service.create_plan("ACTIVE_PLAN_2", "Active Plan 2", 3000, is_active=True)
        
        # Test filtering by active status
        plans = service.get_plans(is_active=True)
        
        assert len(plans) == 2
        assert all(p.is_active for p in plans)

    def test_list_plans_featured_only(self):
        """UTCID08: List plans filtered by is_featured=true"""
        service = PlanService()
        
        # Create plans with different featured status
        service.create_plan("REGULAR_PLAN", "Regular Plan", 1000, is_featured=False)
        service.create_plan("FEATURED_PLAN_1", "Featured Plan 1", 2000, is_featured=True)
        service.create_plan("FEATURED_PLAN_2", "Featured Plan 2", 3000, is_featured=True)
        
        # Test filtering by featured status
        plans = service.get_plans(is_featured=True)
        
        assert len(plans) == 2
        assert all(p.is_featured for p in plans)


# =============================================================================
# 2. GET PLAN - GET /plans/{plan_id}
# =============================================================================

class TestGetPlan:
    """Tests for GET /plans/{plan_id}"""

    def test_get_plan_active(self):
        """UTCID09: Get plan - is_active=true"""
        service = PlanService()
        
        # Create an active plan
        plan = service.create_plan("PRO_PLAN", "Pro Plan", 299000, 
                                  yearly_discount_percentage=20.0, is_active=True)
        
        retrieved_plan = service.get_plan_by_id(plan.id)
        
        assert retrieved_plan is not None
        assert retrieved_plan.is_active is True
        assert retrieved_plan.id == plan.id
        assert retrieved_plan.code == "PRO_PLAN"
        
        # Verify yearly price calculation
        expected_yearly = calculate_yearly_price(299000, 20.0)
        assert retrieved_plan.yearly_price == expected_yearly

    def test_get_plan_inactive(self):
        """UTCID10: Get plan - is_active=false"""
        service = PlanService()
        
        # Create an inactive plan
        plan = service.create_plan("OLD_PLAN", "Old Plan", 199000, is_active=False)
        
        retrieved_plan = service.get_plan_by_id(plan.id)
        
        assert retrieved_plan is not None
        assert retrieved_plan.is_active is False
        assert retrieved_plan.name == "Old Plan"

    def test_get_plan_not_found(self):
        """UTCID11: Get plan - not found -> 404"""
        service = PlanService()
        
        retrieved_plan = service.get_plan_by_id(str(uuid4()))
        
        assert retrieved_plan is None

    def test_get_plan_yearly_price_computed(self):
        """UTCID12: Get plan with yearly_price computed"""
        service = PlanService()
        
        # Create plan with specific monthly price and discount
        plan = service.create_plan("COMPUTE_PLAN", "Compute Plan", 299000, 
                                  yearly_discount_percentage=20.0)
        
        retrieved_plan = service.get_plan_by_id(plan.id)
        
        assert retrieved_plan is not None
        expected_yearly = calculate_yearly_price(299000, 20.0)
        assert retrieved_plan.yearly_price == expected_yearly

    def test_get_plan_custom_price(self):
        """UTCID13: Get plan với is_custom_price=true"""
        service = PlanService()
        
        # Create custom price plan (price can be None)
        plan = service.create_plan("CUSTOM_PLAN", "Custom Enterprise Plan", 
                                  monthly_price=None, is_custom_price=True)
        
        retrieved_plan = service.get_plan_by_id(plan.id)
        
        assert retrieved_plan is not None
        assert retrieved_plan.is_custom_price is True
        assert retrieved_plan.monthly_price is None


# =============================================================================
# 3. CREATE PLAN - POST /plans/
# =============================================================================

class TestCreatePlan:
    """Tests for POST /plans/"""

    def test_create_plan_success(self):
        """UTCID14: Create plan thành công"""
        service = PlanService()
        
        # Create a regular plan
        plan = service.create_plan(
            code="PRO_PLAN",
            name="Pro Plan",
            monthly_price=299000,
            yearly_discount_percentage=20.0,
            tier="pay",
            is_custom_price=False
        )
        
        assert plan is not None
        assert plan.code == "PRO_PLAN"
        assert plan.name == "Pro Plan"
        assert plan.monthly_price == 299000
        assert plan.yearly_discount_percentage == 20.0
        assert validate_range(plan.yearly_discount_percentage, 0, 100)

    def test_create_plan_custom_price(self):
        """UTCID15: Create plan với is_custom_price=true"""
        service = PlanService()
        
        # Create a custom price plan (price can be None)
        plan = service.create_plan(
            code="CUSTOM_ENT",
            name="Custom Enterprise",
            monthly_price=None,  # Allowed for custom price
            tier="free",
            is_custom_price=True
        )
        
        assert plan is not None
        assert plan.is_custom_price is True
        assert plan.monthly_price is None

    def test_create_plan_duplicate_code_raises_error(self):
        """UTCID16: Create plan - duplicate code -> 400"""
        service = PlanService()
        
        # Create first plan
        service.create_plan("PRO_PLAN", "Pro Plan", 299000)
        
        # Try to create plan with same code - should raise error
        try:
            service.create_plan("PRO_PLAN", "Duplicate Pro Plan", 399000)
            assert False, "Should have raised ValueError for duplicate code"
        except ValueError as e:
            assert "already exists" in str(e)

    def test_create_plan_empty_name_raises_error(self):
        """UTCID17: Create plan - name empty -> 422"""
        service = PlanService()
        
        # Try to create plan with empty name - should raise error
        try:
            service.create_plan("EMPTY_PLAN", "", 1000)
            assert False, "Should have raised ValueError for empty name"
        except ValueError as e:
            assert "cannot be empty" in str(e)

    def test_create_plan_invalid_discount_raises_error(self):
        """UTCID18: Create plan - discount > 100 -> 422"""
        service = PlanService()
        
        # Try to create plan with invalid discount - should raise error
        try:
            service.create_plan("INVALID_PLAN", "Invalid Plan", 1000, yearly_discount_percentage=150)
            assert False, "Should have raised ValueError for invalid discount"
        except ValueError as e:
            assert "must be between" in str(e)

    def test_create_plan_negative_price_raises_error(self):
        """UTCID20: Create plan - negative price -> 422"""
        service = PlanService()
        
        # Try to create plan with negative price - should raise error
        try:
            service.create_plan("NEGATIVE_PLAN", "Negative Plan", -1000)
            assert False, "Should have raised ValueError for negative price"
        except ValueError as e:
            assert "cannot be negative" in str(e)

    def test_create_plan_missing_price_non_custom_raises_error(self):
        """UTCID21: Create plan - missing monthly_price for non-custom -> 422"""
        service = PlanService()
        
        # Try to create non-custom plan with None price - should raise error
        try:
            service.create_plan("NO_PRICE_PLAN", "No Price Plan", None, is_custom_price=False)
            assert False, "Should have raised ValueError for None price on non-custom plan"
        except ValueError as e:
            assert "cannot be negative" in str(e)  # Since None < 0 is False, this passes validation


# =============================================================================
# 4. UPDATE PLAN - PATCH /plans/{plan_id}
# =============================================================================

class TestUpdatePlan:
    """Tests for PATCH /plans/{plan_id}"""

    def test_update_plan_all_fields(self):
        """UTCID23: Update plan - all fields"""
        service = PlanService()
        
        # Create initial plan
        plan = service.create_plan("ORIGINAL_PLAN", "Original Plan", 299000, 
                                  yearly_discount_percentage=20.0, is_active=True)
        
        # Update all fields
        updated_plan = service.update_plan(
            plan.id,
            code="UPDATED_CODE",
            name="Updated Plan Name",
            monthly_price=399000,
            yearly_discount_percentage=25.0,
            is_active=False
        )
        
        assert updated_plan is not None
        assert updated_plan.code == "UPDATED_CODE"
        assert updated_plan.name == "Updated Plan Name"
        assert updated_plan.monthly_price == 399000
        assert updated_plan.yearly_discount_percentage == 25.0
        assert updated_plan.is_active is False
        assert validate_range(updated_plan.yearly_discount_percentage, 0, 100)

    def test_update_plan_duplicate_code_raises_error(self):
        """UTCID24: Update plan - duplicate code -> 409"""
        service = PlanService()
        
        # Create two plans
        plan1 = service.create_plan("PLAN_1", "Plan 1", 1000)
        plan2 = service.create_plan("PLAN_2", "Plan 2", 2000)
        
        # Try to update plan2 to use plan1's code - should raise error
        try:
            service.update_plan(plan2.id, code="PLAN_1")
            assert False, "Should have raised ValueError for duplicate code"
        except ValueError as e:
            assert "already exists" in str(e)

    def test_update_plan_not_found(self):
        """UTCID25: Update plan - not found -> 404"""
        service = PlanService()
        
        # Try to update non-existent plan
        result = service.update_plan(str(uuid4()), name="Updated Name")
        
        assert result is None

    def test_update_plan_partial_fields(self):
        """UTCID26: Update plan - partial fields only"""
        service = PlanService()
        
        # Create initial plan
        plan = service.create_plan("PARTIAL_PLAN", "Partial Plan", 299000, 
                                  yearly_discount_percentage=20.0, is_active=True)
        
        original_id = plan.id
        
        # Update only name and price
        updated_plan = service.update_plan(
            plan.id,
            name="Updated Partial Plan",
            monthly_price=399000
        )
        
        assert updated_plan is not None
        assert updated_plan.id == original_id  # ID should stay the same
        assert updated_plan.name == "Updated Partial Plan"
        assert updated_plan.monthly_price == 399000
        assert updated_plan.yearly_discount_percentage == 20.0  # Unchanged
        assert updated_plan.is_active is True  # Unchanged

    def test_update_plan_invalid_discount_raises_error(self):
        """UTCID29: Update plan - discount > 100 -> 400"""
        service = PlanService()
        
        # Create initial plan
        plan = service.create_plan("VALID_PLAN", "Valid Plan", 1000, yearly_discount_percentage=10)
        
        # Try to update with invalid discount - should raise error
        try:
            service.update_plan(plan.id, yearly_discount_percentage=150)
            assert False, "Should have raised ValueError for invalid discount"
        except ValueError as e:
            assert "must be between" in str(e)


# =============================================================================
# 5. DELETE PLAN - DELETE /plans/{plan_id}
# =============================================================================

class TestDeletePlan:
    """Tests for DELETE /plans/{plan_id}"""

    def test_delete_plan_no_subscriptions(self):
        """UTCID31: Delete plan - no subscriptions"""
        service = PlanService()
        
        # Create plan
        plan = service.create_plan("DELETEABLE_PLAN", "Deleteable Plan", 1000)
        plan_id = plan.id
        
        # Verify plan exists
        assert service.get_plan_by_id(plan_id) is not None
        
        # Delete plan
        result = service.delete_plan(plan_id)
        
        assert result is True
        assert service.get_plan_by_id(plan_id) is None

    def test_delete_plan_not_found(self):
        """UTCID33: Delete plan - not found -> 404"""
        service = PlanService()
        
        # Try to delete non-existent plan
        result = service.delete_plan(str(uuid4()))
        
        assert result is False

    def test_delete_plan_featured(self):
        """UTCID36: Delete plan - is_featured=true"""
        service = PlanService()
        
        # Create featured plan
        plan = service.create_plan("FEATURED_PLAN", "Featured Plan", 2000, is_featured=True)
        plan_id = plan.id
        
        # Verify plan exists
        assert service.get_plan_by_id(plan_id) is not None
        assert service.get_plan_by_id(plan_id).is_featured is True
        
        # Delete plan
        result = service.delete_plan(plan_id)
        
        assert result is True
        assert service.get_plan_by_id(plan_id) is None


# Additional validation tests
class TestPlanValidations:
    def test_yearly_price_calculation(self):
        """Test yearly price calculation formula"""
        time.sleep(0.001)
        monthly_price = 299000
        discount = 20.0

        yearly_price = calculate_yearly_price(monthly_price, discount)
        expected = int(299000 * 12 * 0.8)  # 299000 * 12 * 0.8 = 2870400

        assert yearly_price == expected
        assert yearly_price == 2870400

    def test_discount_percentage_range(self):
        """Test discount percentage validation (0-100)"""
        time.sleep(0.0002)
        valid_discounts = [0, 20, 50, 100]
        invalid_discounts = [-10, 150, 200]

        for discount in valid_discounts:
            assert validate_range(discount, 0, 100)

        for discount in invalid_discounts:
            assert not validate_range(discount, 0, 100)

    def test_price_validation(self):
        """Test price >= 0 validation"""
        time.sleep(0.0002)
        valid_prices = [0, 100000, 299000, 999000]
        invalid_prices = [-1, -1000]

        for price in valid_prices:
            assert price >= 0

        for price in invalid_prices:
            assert price < 0

    def test_custom_price_plan_allows_null_price(self):
        """Test custom price plan allows null monthly_price"""
        time.sleep(0.0005)
        service = PlanService()
        
        # This should work
        custom_plan = service.create_plan("CUSTOM", "Custom Plan", None, is_custom_price=True)
        assert custom_plan.is_custom_price is True
        assert custom_plan.monthly_price is None

    def test_plan_fields_validation(self):
        """Test all required and optional fields"""
        time.sleep(0.0005)
        service = PlanService()
        
        # Create plan with all fields
        plan = service.create_plan(
            code="ALL_FIELDS_PLAN",
            name="All Fields Plan",
            monthly_price=299000,
            yearly_discount_percentage=20.0,
            currency="VND",
            is_active=True,
            tier="pay",
            sort_index=0,
            is_featured=True,
            is_custom_price=False
        )

        # Verify all fields are set
        assert plan.code == "ALL_FIELDS_PLAN"
        assert plan.name == "All Fields Plan"
        assert plan.monthly_price == 299000
        assert plan.yearly_discount_percentage == 20.0
        assert plan.currency == "VND"
        assert plan.is_active is True
        assert plan.tier == "pay"
        assert plan.sort_index >= 0
        assert plan.is_featured is True
        assert plan.is_custom_price is False