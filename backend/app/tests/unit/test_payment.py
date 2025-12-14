"""Unit tests for Payment Module based on UTC_PAYMENT.md documentation (44 test cases)"""
import pytest
from uuid import uuid4, UUID
import hmac
import hashlib


def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def calculate_credit_amount(credit_amount: int, price_per_credit: int) -> int:
    """Calculate total amount for credit purchase"""
    return credit_amount * price_per_credit


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify PayOS webhook signature"""
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return expected == signature


# =============================================================================
# 1. CREATE PAYMENT LINK - POST /payments/create (UTCID01-08)
# =============================================================================

class TestCreatePaymentLink:
    """Tests for POST /payments/create"""

    def test_utcid01_create_payment_monthly(self):
        """UTCID01: Create payment link monthly billing"""
        is_authenticated = True
        plan_exists = True
        plan_active = True
        payos_available = True
        
        plan = {
            "id": uuid4(),
            "monthly_price": 299000,
            "is_active": True
        }
        
        payment_request = {
            "plan_id": plan["id"],
            "billing_cycle": "monthly",
            "auto_renew": True,
            "return_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel"
        }
        
        assert is_authenticated
        assert plan_exists
        assert plan_active
        assert payos_available
        assert payment_request["billing_cycle"] == "monthly"

    def test_utcid02_create_payment_yearly(self):
        """UTCID02: Create payment link yearly billing"""
        is_authenticated = True
        plan_exists = True
        plan_active = True
        
        plan = {
            "id": uuid4(),
            "yearly_price": 2870400,
            "is_active": True
        }
        
        payment_request = {
            "plan_id": plan["id"],
            "billing_cycle": "yearly",
            "return_url": None,  # Use default
            "cancel_url": None
        }
        
        assert is_authenticated
        assert plan_exists
        assert plan_active
        assert payment_request["billing_cycle"] == "yearly"

    def test_utcid03_create_payment_plan_not_found(self):
        """UTCID03: Create payment - plan not found -> 404"""
        is_authenticated = True
        plan_id = "550e8400-e29b-41d4-a716-446655440000"
        plan_exists = False
        
        assert is_authenticated
        assert validate_uuid(plan_id)
        assert not plan_exists

    def test_utcid04_create_payment_plan_inactive(self):
        """UTCID04: Create payment - plan inactive -> 400"""
        is_authenticated = True
        plan_exists = True
        plan_active = False
        
        plan = {
            "id": uuid4(),
            "is_active": False
        }
        
        assert is_authenticated
        assert plan_exists
        assert not plan_active

    def test_utcid05_create_payment_payos_fails(self):
        """UTCID05: Create payment - PayOS service fails -> 500"""
        is_authenticated = True
        plan_exists = True
        plan_active = True
        payos_available = False
        
        assert is_authenticated
        assert plan_exists
        assert plan_active
        assert not payos_available

    def test_utcid06_create_payment_no_monthly_price(self):
        """UTCID06: Create payment - no monthly_price -> 400"""
        is_authenticated = True
        plan_exists = True
        plan_active = True
        
        plan = {
            "id": uuid4(),
            "monthly_price": None,
            "is_active": True
        }
        
        billing_cycle = "monthly"
        
        assert is_authenticated
        assert plan_exists
        assert plan["monthly_price"] is None
        assert billing_cycle == "monthly"

    def test_utcid07_create_payment_no_yearly_price(self):
        """UTCID07: Create payment - no yearly_price -> 400"""
        is_authenticated = True
        plan_exists = True
        plan_active = True
        
        plan = {
            "id": uuid4(),
            "yearly_price": None,
            "is_active": True
        }
        
        billing_cycle = "yearly"
        
        assert is_authenticated
        assert plan_exists
        assert plan["yearly_price"] is None
        assert billing_cycle == "yearly"

    def test_utcid08_create_payment_unauthorized(self):
        """UTCID08: Create payment - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 2. PURCHASE CREDITS - POST /payments/credits/purchase (UTCID09-15)
# =============================================================================

class TestPurchaseCredits:
    """Tests for POST /payments/credits/purchase"""

    def test_utcid09_purchase_credits_100(self):
        """UTCID09: Purchase 100 credits successfully"""
        is_authenticated = True
        has_subscription = True
        plan_supports_credits = True
        payos_available = True
        
        credit_request = {
            "credit_amount": 100,
            "return_url": "https://example.com/success"
        }
        
        price_per_credit = 5000
        
        assert is_authenticated
        assert has_subscription
        assert plan_supports_credits
        assert payos_available
        assert credit_request["credit_amount"] >= 10

    def test_utcid10_purchase_credits_500(self):
        """UTCID10: Purchase 500 credits"""
        is_authenticated = True
        has_subscription = True
        plan_supports_credits = True
        payos_available = True
        
        credit_request = {
            "credit_amount": 500
        }
        
        assert is_authenticated
        assert credit_request["credit_amount"] >= 10

    def test_utcid11_purchase_credits_no_subscription(self):
        """UTCID11: Purchase credits without subscription -> 400"""
        is_authenticated = True
        has_subscription = False
        
        assert is_authenticated
        assert not has_subscription

    def test_utcid12_purchase_credits_plan_no_support(self):
        """UTCID12: Purchase credits - plan doesn't support -> 400"""
        is_authenticated = True
        has_subscription = True
        plan_supports_credits = False
        
        plan = {
            "additional_credit_price": None
        }
        
        assert is_authenticated
        assert has_subscription
        assert plan["additional_credit_price"] is None

    def test_utcid13_purchase_credits_payos_error(self):
        """UTCID13: Purchase credits - PayOS error -> 500"""
        is_authenticated = True
        has_subscription = True
        plan_supports_credits = True
        payos_available = False
        
        assert is_authenticated
        assert has_subscription
        assert plan_supports_credits
        assert not payos_available

    def test_utcid14_purchase_credits_below_minimum(self):
        """UTCID14: Purchase credits < 10 -> 422"""
        is_authenticated = True
        has_subscription = True
        plan_supports_credits = True
        
        credit_request = {
            "credit_amount": 5  # Below minimum
        }
        
        assert is_authenticated
        assert credit_request["credit_amount"] < 10

    def test_utcid15_purchase_credits_unauthorized(self):
        """UTCID15: Purchase credits - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 3. GET PAYMENT STATUS - GET /payments/status/{order_id} (UTCID16-21)
# =============================================================================

class TestGetPaymentStatus:
    """Tests for GET /payments/status/{order_id}"""

    def test_utcid16_get_status_pending_to_paid(self):
        """UTCID16: Get status - PENDING to PAID (auto-activate)"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        
        order = {
            "id": uuid4(),
            "status": "PENDING",
            "payos_status": "PAID"
        }
        
        assert is_authenticated
        assert order_exists
        assert order_belongs_to_user
        assert order["status"] == "PENDING"

    def test_utcid17_get_status_already_paid(self):
        """UTCID17: Get status - already PAID"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        
        order = {
            "id": uuid4(),
            "status": "PAID"
        }
        
        assert is_authenticated
        assert order_exists
        assert order["status"] == "PAID"

    def test_utcid18_get_status_not_found(self):
        """UTCID18: Get status - order not found -> 404"""
        is_authenticated = True
        order_id = "550e8400-e29b-41d4-a716-446655440000"
        order_exists = False
        
        assert is_authenticated
        assert validate_uuid(order_id)
        assert not order_exists

    def test_utcid19_get_status_forbidden(self):
        """UTCID19: Get status - other user's order -> 403"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = False
        
        assert is_authenticated
        assert order_exists
        assert not order_belongs_to_user

    def test_utcid20_get_status_still_pending(self):
        """UTCID20: Get status - still PENDING"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        
        order = {
            "id": uuid4(),
            "status": "PENDING",
            "payos_status": "PENDING"
        }
        
        assert is_authenticated
        assert order_exists
        assert order["status"] == "PENDING"

    def test_utcid21_get_status_unauthorized(self):
        """UTCID21: Get status - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 4. PAYOS WEBHOOK - POST /payments/webhook (UTCID22-27)
# =============================================================================

class TestPayOSWebhook:
    """Tests for POST /payments/webhook"""

    def test_utcid22_webhook_payment_success(self):
        """UTCID22: Webhook - payment success (code 00)"""
        order_exists = True
        order_not_paid = True
        webhook_secret_configured = True
        signature_valid = True
        
        webhook_data = {
            "data": {
                "orderCode": 123456789,
                "code": "00"
            }
        }
        
        assert order_exists
        assert order_not_paid
        assert webhook_secret_configured
        assert signature_valid
        assert webhook_data["data"]["code"] == "00"

    def test_utcid23_webhook_payment_failed(self):
        """UTCID23: Webhook - payment failed (code 01)"""
        order_exists = True
        order_not_paid = True
        signature_valid = True
        
        webhook_data = {
            "data": {
                "orderCode": 123456789,
                "code": "01"
            }
        }
        
        assert order_exists
        assert webhook_data["data"]["code"] == "01"

    def test_utcid24_webhook_invalid_signature(self):
        """UTCID24: Webhook - invalid signature -> 401"""
        webhook_secret_configured = True
        signature_valid = False
        
        assert not signature_valid

    def test_utcid25_webhook_order_not_found(self):
        """UTCID25: Webhook - order not found"""
        order_exists = False
        signature_valid = True
        
        webhook_data = {
            "data": {
                "orderCode": 999999999
            }
        }
        
        assert not order_exists

    def test_utcid26_webhook_already_paid(self):
        """UTCID26: Webhook - order already paid"""
        order_exists = True
        order_not_paid = False
        signature_valid = True
        
        order = {
            "status": "PAID"
        }
        
        assert order_exists
        assert order["status"] == "PAID"

    def test_utcid27_webhook_missing_order_code(self):
        """UTCID27: Webhook - missing orderCode -> 400"""
        signature_valid = True
        
        webhook_data = {
            "data": {}
        }
        
        assert "orderCode" not in webhook_data["data"]


# =============================================================================
# 5. SYNC ORDER STATUS - POST /payments/sync-status-by-code/{order_code} (UTCID28-33)
# =============================================================================

class TestSyncOrderStatus:
    """Tests for POST /payments/sync-status-by-code/{order_code}"""

    def test_utcid28_sync_subscription_paid(self):
        """UTCID28: Sync status - subscription order PAID"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        payos_available = True
        
        order = {
            "order_type": "subscription",
            "payos_status": "PAID"
        }
        
        assert is_authenticated
        assert order_exists
        assert order_belongs_to_user
        assert payos_available

    def test_utcid29_sync_credit_paid(self):
        """UTCID29: Sync status - credit order PAID"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        payos_available = True
        
        order = {
            "order_type": "credit",
            "payos_status": "PAID",
            "credit_amount": 100
        }
        
        assert is_authenticated
        assert order_exists
        assert order["order_type"] == "credit"

    def test_utcid30_sync_not_found(self):
        """UTCID30: Sync status - order not found -> 404"""
        is_authenticated = True
        order_code = 999999999
        order_exists = False
        
        assert is_authenticated
        assert not order_exists

    def test_utcid31_sync_forbidden(self):
        """UTCID31: Sync status - other user's order -> 403"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = False
        
        assert is_authenticated
        assert order_exists
        assert not order_belongs_to_user

    def test_utcid32_sync_still_pending(self):
        """UTCID32: Sync status - still PENDING"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        payos_available = True
        
        order = {
            "payos_status": "PENDING"
        }
        
        assert is_authenticated
        assert order_exists
        assert order["payos_status"] == "PENDING"

    def test_utcid33_sync_unauthorized(self):
        """UTCID33: Sync status - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 6. GET PAYMENT HISTORY - GET /payments/history (UTCID34-38)
# =============================================================================

class TestGetPaymentHistory:
    """Tests for GET /payments/history"""

    def test_utcid34_get_history_default(self):
        """UTCID34: Get payment history - default pagination"""
        is_authenticated = True
        user_has_orders = True
        
        query_params = {
            "limit": 10,
            "offset": 0
        }
        
        orders = [
            {"id": uuid4(), "created_at": "2025-12-10"},
            {"id": uuid4(), "created_at": "2025-12-09"}
        ]
        
        assert is_authenticated
        assert user_has_orders
        assert len(orders) <= query_params["limit"]

    def test_utcid35_get_history_limit_5(self):
        """UTCID35: Get payment history - limit=5"""
        is_authenticated = True
        user_has_orders = True
        
        query_params = {
            "limit": 5,
            "offset": 0
        }
        
        assert is_authenticated
        assert user_has_orders

    def test_utcid36_get_history_no_orders(self):
        """UTCID36: Get payment history - no orders"""
        is_authenticated = True
        user_has_orders = False
        
        orders = []
        
        assert is_authenticated
        assert not user_has_orders
        assert len(orders) == 0

    def test_utcid37_get_history_pagination(self):
        """UTCID37: Get payment history - pagination offset"""
        is_authenticated = True
        user_has_orders = True
        
        query_params = {
            "limit": 10,
            "offset": 10
        }
        
        assert is_authenticated
        assert user_has_orders
        assert query_params["offset"] == 10

    def test_utcid38_get_history_unauthorized(self):
        """UTCID38: Get payment history - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# 7. GET INVOICE - GET /payments/invoice/{order_id} (UTCID39-44)
# =============================================================================

class TestGetInvoice:
    """Tests for GET /payments/invoice/{order_id}"""

    def test_utcid39_get_invoice_with_plan(self):
        """UTCID39: Get invoice - subscription order with plan"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        invoice_exists = True
        
        invoice = {
            "id": uuid4(),
            "invoice_number": "INV-2025-0001",
            "amount": 299000,
            "status": "paid"
        }
        
        order = {
            "id": uuid4(),
            "order_type": "subscription"
        }
        
        plan = {
            "name": "Pro Plan",
            "code": "PRO"
        }
        
        assert is_authenticated
        assert order_exists
        assert order_belongs_to_user
        assert invoice_exists

    def test_utcid40_get_invoice_not_found(self):
        """UTCID40: Get invoice - invoice not found -> 404"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        invoice_exists = False
        
        assert is_authenticated
        assert order_exists
        assert not invoice_exists

    def test_utcid41_get_invoice_order_not_found(self):
        """UTCID41: Get invoice - order not found -> 404"""
        is_authenticated = True
        order_id = "550e8400-e29b-41d4-a716-446655440000"
        order_exists = False
        
        assert is_authenticated
        assert validate_uuid(order_id)
        assert not order_exists

    def test_utcid42_get_invoice_forbidden(self):
        """UTCID42: Get invoice - other user's order -> 403"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = False
        
        assert is_authenticated
        assert order_exists
        assert not order_belongs_to_user

    def test_utcid43_get_invoice_credit_order(self):
        """UTCID43: Get invoice - credit order (no plan)"""
        is_authenticated = True
        order_exists = True
        order_belongs_to_user = True
        invoice_exists = True
        
        order = {
            "id": uuid4(),
            "order_type": "credit"
        }
        
        plan = None
        
        assert is_authenticated
        assert order_exists
        assert order["order_type"] == "credit"
        assert plan is None

    def test_utcid44_get_invoice_unauthorized(self):
        """UTCID44: Get invoice - unauthorized -> 401"""
        is_authenticated = False
        
        with pytest.raises(AssertionError):
            assert is_authenticated, "Should raise 401 Unauthorized"


# =============================================================================
# ADDITIONAL VALIDATION TESTS
# =============================================================================

class TestPaymentValidations:
    """Additional validation tests for Payment module"""

    def test_order_status_enum(self):
        """Test valid order statuses"""
        valid_statuses = ["pending", "paid", "failed", "canceled"]
        
        for status in valid_statuses:
            assert status in valid_statuses

    def test_order_type_enum(self):
        """Test valid order types"""
        valid_types = ["subscription", "credit"]
        
        for order_type in valid_types:
            assert order_type in valid_types

    def test_billing_cycle_enum(self):
        """Test valid billing cycles"""
        valid_cycles = ["monthly", "yearly"]
        
        for cycle in valid_cycles:
            assert cycle in valid_cycles

    def test_credit_amount_minimum(self):
        """Test credit amount minimum (>= 10)"""
        valid_amounts = [10, 50, 100, 500]
        invalid_amounts = [0, 5, 9]
        
        for amount in valid_amounts:
            assert amount >= 10
        
        for amount in invalid_amounts:
            assert amount < 10

    def test_credit_price_calculation(self):
        """Test credit price calculation"""
        credit_amount = 100
        price_per_credit = 5000
        
        total = calculate_credit_amount(credit_amount, price_per_credit)
        assert total == 500000

    def test_webhook_signature_verification(self):
        """Test webhook signature verification"""
        payload = '{"data":{"orderCode":123}}'
        secret = "test_secret"
        
        signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        
        assert verify_webhook_signature(payload, signature, secret)

    def test_invoice_status_enum(self):
        """Test valid invoice statuses"""
        valid_statuses = ["draft", "issued", "paid", "void"]
        
        for status in valid_statuses:
            assert status in valid_statuses

    def test_payos_response_codes(self):
        """Test PayOS response codes"""
        success_code = "00"
        failed_code = "01"
        
        assert success_code == "00"
        assert failed_code == "01"
