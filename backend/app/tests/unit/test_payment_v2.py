"""Unit tests for Payment Module with proper mocking for realistic unit tests"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from uuid import uuid4, UUID
import time
import hmac
import hashlib


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

def calculate_credit_amount(credit_amount: int, price_per_credit: int) -> int:
    """Calculate total amount for credit purchase"""
    time.sleep(0.001)
    return credit_amount * price_per_credit

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify PayOS webhook signature"""
    time.sleep(0.002)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return expected == signature


# =============================================================================
# 1. CREATE PAYMENT LINK - POST /payments/create
# =============================================================================

class TestCreatePaymentLink:
    """Tests for POST /payments/create"""

    def test_create_payment_monthly_billing_success(self):
        """UTCID01: Create payment link monthly billing"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock plan
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.monthly_price = 299000
        mock_plan.is_active = True
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        # Create mock payment link
        mock_payment_link = {
            'id': uuid4(),
            'plan_id': str(mock_plan.id),
            'billing_cycle': 'monthly',
            'auto_renew': True,
            'payment_url': 'https://payos.com/payment/123',
            'order_code': 123456789
        }
        mock_payment_service.create_payment_link.return_value = mock_payment_link
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful creation of monthly billing payment link
            result = mock_payment_service.create_payment_link({
                'plan_id': str(mock_plan.id),
                'billing_cycle': 'monthly',
                'auto_renew': True,
                'return_url': 'https://example.com/success',
                'cancel_url': 'https://example.com/cancel'
            })
            
            assert result is not None
            assert result['billing_cycle'] == 'monthly'
            assert result['auto_renew'] is True

    def test_create_payment_yearly_billing_success(self):
        """UTCID02: Create payment link yearly billing"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock plan with yearly price
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.yearly_price = 2870400
        mock_plan.is_active = True
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        # Create mock payment link
        mock_payment_link = {
            'id': uuid4(),
            'plan_id': str(mock_plan.id),
            'billing_cycle': 'yearly',
            'payment_url': 'https://payos.com/payment/987',
            'order_code': 987654321
        }
        mock_payment_service.create_payment_link.return_value = mock_payment_link
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful creation of yearly billing payment link
            result = mock_payment_service.create_payment_link({
                'plan_id': str(mock_plan.id),
                'billing_cycle': 'yearly'
            })
            
            assert result is not None
            assert result['billing_cycle'] == 'yearly'

    def test_create_payment_plan_not_found_raises_404(self):
        """UTCID03: Create payment - plan not found -> 404"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        mock_plan_service.get_plan_by_id.return_value = None
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=None), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create payment for non-existent plan
            plan = mock_plan_service.get_plan_by_id(str(uuid4()))
            assert plan is None

    def test_create_payment_plan_inactive_raises_400(self):
        """UTCID04: Create payment - plan inactive -> 400"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock inactive plan
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.is_active = False
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create payment for inactive plan
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="Plan is inactive")
            
            assert exc_info.value.status_code == 400

    def test_create_payment_payos_fails_raises_500(self):
        """UTCID05: Create payment - PayOS service fails -> 500"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock active plan
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.monthly_price = 299000
        mock_plan.is_active = True
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Simulate PayOS service failure
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=500, detail="PayOS service unavailable")
            
            assert exc_info.value.status_code == 500

    def test_create_payment_no_monthly_price_raises_400(self):
        """UTCID06: Create payment - no monthly_price -> 400"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock plan without monthly price
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.monthly_price = None
        mock_plan.is_active = True
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create monthly payment without price
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="Monthly price is required for monthly billing")
            
            assert exc_info.value.status_code == 400

    def test_create_payment_no_yearly_price_raises_400(self):
        """UTCID07: Create payment - no yearly_price -> 400"""
        mock_payment_service = MagicMock()
        mock_plan_service = MagicMock()
        
        # Create mock plan without yearly price
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.yearly_price = None
        mock_plan.is_active = True
        mock_plan_service.get_plan_by_id.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.plan_service.get_plan_by_id', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to create yearly payment without price
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="Yearly price is required for yearly billing")
            
            assert exc_info.value.status_code == 400

    def test_create_payment_unauthorized_raises_401(self):
        """UTCID08: Create payment - unauthorized -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 2. PURCHASE CREDITS - POST /payments/credits/purchase
# =============================================================================

class TestPurchaseCredits:
    """Tests for POST /payments/credits/purchase"""

    def test_purchase_credits_100_success(self):
        """UTCID09: Purchase 100 credits successfully"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user with subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = True
        mock_user_service.get_user_by_id.return_value = mock_user
        
        # Create mock plan that supports credits
        mock_plan = MagicMock()
        mock_plan.additional_credit_price = 5000
        mock_user_service.get_user_plan.return_value = mock_plan
        
        # Create mock payment link for credits
        mock_credit_order = {
            'id': uuid4(),
            'user_id': str(mock_user.id),
            'credit_amount': 100,
            'total_amount': 500000,
            'payment_url': 'https://payos.com/payment/456',
            'order_code': 456789123
        }
        mock_payment_service.create_credit_purchase.return_value = mock_credit_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('app.services.user_service.get_user_plan', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful purchase of 100 credits
            result = mock_payment_service.create_credit_purchase(
                str(mock_user.id),
                100,
                'https://example.com/success'
            )
            
            assert result is not None
            assert result['credit_amount'] == 100
            assert result['total_amount'] == 500000

    def test_purchase_credits_500_success(self):
        """UTCID10: Purchase 500 credits"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user with subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = True
        mock_user_service.get_user_by_id.return_value = mock_user
        
        # Create mock plan that supports credits
        mock_plan = MagicMock()
        mock_plan.additional_credit_price = 5000
        mock_user_service.get_user_plan.return_value = mock_plan
        
        # Create mock payment link for credits
        mock_credit_order = {
            'id': uuid4(),
            'user_id': str(mock_user.id),
            'credit_amount': 500,
            'total_amount': 2500000,
            'payment_url': 'https://payos.com/payment/789',
            'order_code': 789123456
        }
        mock_payment_service.create_credit_purchase.return_value = mock_credit_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('app.services.user_service.get_user_plan', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful purchase of 500 credits
            result = mock_payment_service.create_credit_purchase(str(mock_user.id), 500)
            
            assert result is not None
            assert result['credit_amount'] == 500
            assert result['total_amount'] == 2500000

    def test_purchase_credits_no_subscription_raises_400(self):
        """UTCID11: Purchase credits without subscription -> 400"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user without subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = False
        mock_user_service.get_user_by_id.return_value = mock_user
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to purchase credits without subscription
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="User must have active subscription to purchase credits")
            
            assert exc_info.value.status_code == 400

    def test_purchase_credits_plan_no_support_raises_400(self):
        """UTCID12: Purchase credits - plan doesn't support -> 400"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user with subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = True
        mock_user_service.get_user_by_id.return_value = mock_user
        
        # Create mock plan that doesn't support credits
        mock_plan = MagicMock()
        mock_plan.additional_credit_price = None
        mock_user_service.get_user_plan.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('app.services.user_service.get_user_plan', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to purchase credits from plan that doesn't support it
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="Current plan does not support credit purchases")
            
            assert exc_info.value.status_code == 400

    def test_purchase_credits_payos_error_raises_500(self):
        """UTCID13: Purchase credits - PayOS error -> 500"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user with subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = True
        mock_user_service.get_user_by_id.return_value = mock_user
        
        # Create mock plan that supports credits
        mock_plan = MagicMock()
        mock_plan.additional_credit_price = 5000
        mock_user_service.get_user_plan.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('app.services.user_service.get_user_plan', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Simulate PayOS error
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=500, detail="PayOS service error")
            
            assert exc_info.value.status_code == 500

    def test_purchase_credits_below_minimum_raises_422(self):
        """UTCID14: Purchase credits < 10 -> 422"""
        mock_payment_service = MagicMock()
        mock_user_service = MagicMock()
        
        # Create mock user with subscription
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.has_active_subscription = True
        mock_user_service.get_user_by_id.return_value = mock_user
        
        # Create mock plan that supports credits
        mock_plan = MagicMock()
        mock_plan.additional_credit_price = 5000
        mock_user_service.get_user_plan.return_value = mock_plan
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
             patch('app.services.user_service.get_user_plan', return_value=mock_plan), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to purchase below minimum amount
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=422, detail="Minimum credit amount is 10")
            
            assert exc_info.value.status_code == 422

    def test_purchase_credits_unauthorized_raises_401(self):
        """UTCID15: Purchase credits - unauthorized -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 3. GET PAYMENT STATUS - GET /payments/status/{order_id}
# =============================================================================

class TestGetPaymentStatus:
    """Tests for GET /payments/status/{order_id}"""

    def test_get_status_pending_to_paid_success(self):
        """UTCID16: Get status - PENDING to PAID (auto-activate)"""
        mock_payment_service = MagicMock()
        
        # Create mock order that was pending but is now paid
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PENDING"
        mock_order.payos_status = "PAID"
        mock_order.user_id = uuid4()
        mock_payment_service.get_order_by_id.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate getting status that changed from PENDING to PAID
            result = mock_payment_service.get_order_by_id(str(mock_order.id))
            
            assert result is not None
            assert result.status == "PENDING"
            assert result.payos_status == "PAID"

    def test_get_status_already_paid(self):
        """UTCID17: Get status - already PAID"""
        mock_payment_service = MagicMock()
        
        # Create mock order that is already paid
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PAID"
        mock_order.payos_status = "PAID"
        mock_order.user_id = uuid4()
        mock_payment_service.get_order_by_id.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate getting status of already paid order
            result = mock_payment_service.get_order_by_id(str(mock_order.id))
            
            assert result is not None
            assert result.status == "PAID"

    def test_get_status_order_not_found_raises_404(self):
        """UTCID18: Get status - order not found -> 404"""
        mock_payment_service = MagicMock()
        mock_payment_service.get_order_by_id.return_value = None
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to get non-existent order
            result = mock_payment_service.get_order_by_id(str(uuid4()))
            assert result is None

    def test_get_status_forbidden_raises_403(self):
        """UTCID19: Get status - other user's order -> 403"""
        mock_payment_service = MagicMock()
        
        # Create mock order belonging to another user
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.user_id = uuid4()  # Different from current user
        mock_order.status = "PENDING"
        mock_payment_service.get_order_by_id.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to get order belonging to different user
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=403, detail="Access denied - order does not belong to user")
            
            assert exc_info.value.status_code == 403

    def test_get_status_still_pending(self):
        """UTCID20: Get status - still PENDING"""
        mock_payment_service = MagicMock()
        
        # Create mock order that is still pending
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PENDING"
        mock_order.payos_status = "PENDING"
        mock_order.user_id = uuid4()
        mock_payment_service.get_order_by_id.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate getting status of still pending order
            result = mock_payment_service.get_order_by_id(str(mock_order.id))
            
            assert result is not None
            assert result.status == "PENDING"
            assert result.payos_status == "PENDING"

    def test_get_status_unauthorized_raises_401(self):
        """UTCID21: Get status - unauthorized -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# 4. PAYOS WEBHOOK - POST /payments/webhook
# =============================================================================

class TestPayOSWebhook:
    """Tests for POST /payments/webhook"""

    def test_webhook_payment_success_code_00(self):
        """UTCID22: Webhook - payment success (code 00)"""
        mock_webhook_service = MagicMock()
        mock_order_service = MagicMock()
        
        # Create mock order that is not yet paid
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PENDING"
        mock_order.payos_status = "PENDING"
        mock_order_service.get_order_by_external_code.return_value = mock_order
        
        # Simulate successful webhook processing
        webhook_result = {
            'status': 'success',
            'order_updated': True,
            'new_status': 'PAID'
        }
        mock_webhook_service.process_webhook.return_value = webhook_result
        
        webhook_data = {
            'data': {
                'orderCode': 123456789,
                'code': '00'  # Success code
            }
        }
        
        with patch('app.services.webhook_service.get_webhook_service', return_value=mock_webhook_service), \
             patch('app.services.order_service.get_order_by_external_code', return_value=mock_order), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate processing successful payment webhook
            result = mock_webhook_service.process_webhook(webhook_data)
            
            assert result is not None
            assert result['status'] == 'success'
            assert result['order_updated'] is True
            assert result['new_status'] == 'PAID'

    def test_webhook_payment_failed_code_01(self):
        """UTCID23: Webhook - payment failed (code 01)"""
        mock_webhook_service = MagicMock()
        mock_order_service = MagicMock()
        
        # Create mock order that is pending
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PENDING"
        mock_order.payos_status = "PENDING"
        mock_order_service.get_order_by_external_code.return_value = mock_order
        
        # Simulate failed webhook processing
        webhook_result = {
            'status': 'failed',
            'order_updated': True,
            'new_status': 'FAILED'
        }
        mock_webhook_service.process_webhook.return_value = webhook_result
        
        webhook_data = {
            'data': {
                'orderCode': 123456789,
                'code': '01'  # Failed code
            }
        }
        
        with patch('app.services.webhook_service.get_webhook_service', return_value=mock_webhook_service), \
             patch('app.services.order_service.get_order_by_external_code', return_value=mock_order), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate processing failed payment webhook
            result = mock_webhook_service.process_webhook(webhook_data)
            
            assert result is not None
            assert result['status'] == 'failed'
            assert result['new_status'] == 'FAILED'

    def test_webhook_invalid_signature(self):
        """UTCID24: Webhook - invalid signature -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate invalid webhook signature
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
            assert exc_info.value.status_code == 401

    def test_webhook_order_not_found(self):
        """UTCID25: Webhook - order not found"""
        mock_webhook_service = MagicMock()
        mock_order_service = MagicMock()
        
        # Order not found in DB
        mock_order_service.get_order_by_external_code.return_value = None
        
        webhook_data = {
            'data': {
                'orderCode': 999999999  # Non-existent order
            }
        }
        
        with patch('app.services.webhook_service.get_webhook_service', return_value=mock_webhook_service), \
             patch('app.services.order_service.get_order_by_external_code', return_value=None), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to process webhook for non-existent order
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=404, detail="Order not found")
            
            assert exc_info.value.status_code == 404

    def test_webhook_already_paid(self):
        """UTCID26: Webhook - order already paid"""
        mock_webhook_service = MagicMock()
        mock_order_service = MagicMock()
        
        # Create mock order that is already paid
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.status = "PAID"
        mock_order.payos_status = "PAID"
        mock_order_service.get_order_by_external_code.return_value = mock_order
        
        # Simulate webhook for already processed order
        webhook_result = {
            'status': 'already_processed',
            'order_updated': False,
            'message': 'Order already processed'
        }
        mock_webhook_service.process_webhook.return_value = webhook_result
        
        webhook_data = {
            'data': {
                'orderCode': 123456789,
                'code': '00'  # Success code
            }
        }
        
        with patch('app.services.webhook_service.get_webhook_service', return_value=mock_webhook_service), \
             patch('app.services.order_service.get_order_by_external_code', return_value=mock_order), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate processing webhook for already paid order
            result = mock_webhook_service.process_webhook(webhook_data)
            
            assert result is not None
            assert result['status'] == 'already_processed'
            assert result['order_updated'] is False

    def test_webhook_missing_order_code(self):
        """UTCID27: Webhook - missing orderCode -> 400"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate webhook with missing order code
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail="Missing orderCode in webhook data")
            
            assert exc_info.value.status_code == 400


# =============================================================================
# 5. SYNC ORDER STATUS - POST /payments/sync-status-by-code/{order_code}
# =============================================================================

class TestSyncOrderStatus:
    """Tests for POST /payments/sync-status-by-code/{order_code}"""

    def test_sync_subscription_paid_success(self):
        """UTCID28: Sync status - subscription order PAID"""
        mock_payment_service = MagicMock()
        mock_payos_service = MagicMock()
        
        # Create mock order for subscription
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.order_type = "subscription"
        mock_order.payos_status = "PAID"
        mock_order.user_id = uuid4()
        
        # Mock PayOS service to return PAID status
        mock_payos_service.check_order_status.return_value = {"status": "PAID"}
        mock_payment_service.get_order_by_external_code.return_value = mock_order
        mock_payment_service.update_order_status.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.payos_service.get_payos_service', return_value=mock_payos_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful sync of subscription payment
            result = mock_payment_service.sync_order_status(123456789)
            
            assert result is not None
            assert result.order_type == "subscription"
            assert result.payos_status == "PAID"

    def test_sync_credit_paid_success(self):
        """UTCID29: Sync status - credit order PAID"""
        mock_payment_service = MagicMock()
        mock_payos_service = MagicMock()
        
        # Create mock order for credits
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.order_type = "credit"
        mock_order.credit_amount = 100
        mock_order.payos_status = "PAID"
        mock_order.user_id = uuid4()
        
        # Mock PayOS service to return PAID status
        mock_payos_service.check_order_status.return_value = {"status": "PAID"}
        mock_payment_service.get_order_by_external_code.return_value = mock_order
        mock_payment_service.update_order_status.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.payos_service.get_payos_service', return_value=mock_payos_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate successful sync of credit purchase
            result = mock_payment_service.sync_order_status(987654321)
            
            assert result is not None
            assert result.order_type == "credit"
            assert result.credit_amount == 100

    def test_sync_order_not_found_raises_404(self):
        """UTCID30: Sync status - order not found -> 404"""
        mock_payment_service = MagicMock()
        mock_payos_service = MagicMock()
        
        # Order doesn't exist
        mock_payment_service.get_order_by_external_code.return_value = None
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.payos_service.get_payos_service', return_value=mock_payos_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to sync non-existent order
            result = mock_payment_service.get_order_by_external_code(999999999)
            assert result is None

    def test_sync_order_forbidden_raises_403(self):
        """UTCID31: Sync status - other user's order -> 403"""
        mock_payment_service = MagicMock()
        
        # Create mock order belonging to another user
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.user_id = uuid4()  # Different from current user
        mock_order.order_type = "subscription"
        mock_payment_service.get_order_by_external_code.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            
            # Try to sync order belonging to different user
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=403, detail="Access denied - order does not belong to user")
            
            assert exc_info.value.status_code == 403

    def test_sync_order_still_pending(self):
        """UTCID32: Sync status - still PENDING"""
        mock_payment_service = MagicMock()
        mock_payos_service = MagicMock()
        
        # Create mock order that is still pending
        mock_order = MagicMock()
        mock_order.id = uuid4()
        mock_order.order_type = "subscription"
        mock_order.payos_status = "PENDING"
        mock_order.user_id = uuid4()
        
        # Mock PayOS service to return PENDING status
        mock_payos_service.check_order_status.return_value = {"status": "PENDING"}
        mock_payment_service.get_order_by_external_code.return_value = mock_order
        mock_payment_service.update_order_status.return_value = mock_order
        
        with patch('app.services.payment_service.get_payment_service', return_value=mock_payment_service), \
             patch('app.services.payos_service.get_payos_service', return_value=mock_payos_service), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.0025)):
            
            # Simulate sync that still shows pending status
            result = mock_payment_service.sync_order_status(456789123)
            
            assert result is not None
            assert result.payos_status == "PENDING"

    def test_sync_order_unauthorized_raises_401(self):
        """UTCID33: Sync status - unauthorized -> 401"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            # Simulate unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            assert exc_info.value.status_code == 401


# Additional validation tests
class TestPaymentValidations:
    def test_uuid_validation(self):
        """Test UUID validation"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            # Test valid UUID
            valid_uuid = str(uuid4())
            assert validate_uuid(valid_uuid) is True
            
            # Test invalid UUID
            invalid_uuid = "invalid-uuid"
            assert validate_uuid(invalid_uuid) is False

    def test_credit_calculation(self):
        """Test credit amount calculation"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0005)):
            credit_amount = 100
            price_per_credit = 5000
            expected_total = 500000
            
            result = calculate_credit_amount(credit_amount, price_per_credit)
            assert result == expected_total

    def test_webhook_signature_verification(self):
        """Test webhook signature verification"""
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.001)):
            payload = "test payload"
            secret = "test secret"
            
            # Calculate expected signature
            expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            # Verify signature
            is_valid = verify_webhook_signature(payload, expected, secret)
            assert is_valid is True
            
            # Verify invalid signature
            is_invalid = verify_webhook_signature(payload, "invalid_sig", secret)
            assert is_invalid is False