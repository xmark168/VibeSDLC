"""SePay Payment API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import httpx
import logging

from app.api.deps import CurrentUser, SessionDep
from app.schemas.sepay import (
    SePayCreateRequest,
    SePayCreditPurchaseRequest,
    SePayQRResponse,
    SePayStatusResponse,
)
from app.services.plan_service import PlanService
from app.services.subscription_service import SubscriptionService
from app.models import Order, OrderStatus, OrderType
from app.core.config import settings
from sqlmodel import select

router = APIRouter(prefix="/sepay", tags=["sepay"])
logger = logging.getLogger(__name__)

# QR code base URL
SEPAY_QR_BASE = "https://qr.sepay.vn/img"


def generate_transaction_code() -> str:
    """Generate unique transaction code for SePay"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    unique_id = str(uuid4())[:6].upper()
    return f"VS{timestamp}{unique_id}"


def build_qr_url(amount: int, transaction_code: str) -> str:
    """Build SePay QR code URL"""
    return (
        f"{SEPAY_QR_BASE}?"
        f"bank={settings.SEPAY_BANK_CODE}&"
        f"acc={settings.SEPAY_ACCOUNT_NUMBER}&"
        f"template=&"
        f"amount={amount}&"
        f"des={transaction_code}"
    )


@router.post("/create", response_model=SePayQRResponse)
def create_sepay_payment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: SePayCreateRequest
) -> SePayQRResponse:
    """Create SePay payment QR code for subscription"""
    
    # Get plan
    plan_service = PlanService(session)
    plan = plan_service.get_by_id(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if not plan.is_active:
        raise HTTPException(status_code=400, detail="Plan is not active")
    
    # Get amount based on billing cycle
    if request.billing_cycle == "monthly":
        if not plan.monthly_price:
            raise HTTPException(status_code=400, detail="Monthly billing not available")
        amount = plan.monthly_price
    else:
        if not plan.yearly_price:
            raise HTTPException(status_code=400, detail="Yearly billing not available")
        amount = plan.yearly_price
    
    # Generate transaction code
    transaction_code = generate_transaction_code()
    
    # Create order
    order = Order(
        user_id=current_user.id,
        order_type=OrderType.SUBSCRIPTION,
        plan_code=plan.code,
        billing_cycle=request.billing_cycle,
        amount=amount,
        status=OrderStatus.PENDING,
        auto_renew=request.auto_renew,
        sepay_transaction_code=transaction_code,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    
    # Build QR URL
    qr_url = build_qr_url(amount, transaction_code)
    
    # Expires in 15 minutes
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    return SePayQRResponse(
        order_id=order.id,
        transaction_code=transaction_code,
        qr_url=qr_url,
        amount=amount,
        description=f"{plan.name} - {request.billing_cycle.capitalize()}",
        expires_at=expires_at
    )


@router.post("/credits/purchase", response_model=SePayQRResponse)
def create_sepay_credit_purchase(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: SePayCreditPurchaseRequest
) -> SePayQRResponse:
    """Create SePay payment QR for credit purchase"""
    
    # Get current subscription to get credit price
    subscription_service = SubscriptionService(session)
    subscription = subscription_service.get_active_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    plan_service = PlanService(session)
    plan = plan_service.get_by_id(subscription.plan_id)
    
    if not plan or not plan.additional_credit_price:
        raise HTTPException(status_code=400, detail="Credit purchase not available")
    
    # Calculate amount (price per 100 credits)
    credit_packs = request.credit_amount // 100
    if credit_packs < 1:
        raise HTTPException(status_code=400, detail="Minimum purchase is 100 credits")
    
    amount = credit_packs * plan.additional_credit_price
    
    # Generate transaction code
    transaction_code = generate_transaction_code()
    
    # Create order
    order = Order(
        user_id=current_user.id,
        order_type=OrderType.CREDIT,
        credit_amount=request.credit_amount,
        amount=amount,
        status=OrderStatus.PENDING,
        sepay_transaction_code=transaction_code,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    
    # Build QR URL
    qr_url = build_qr_url(amount, transaction_code)
    
    # Expires in 15 minutes
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    return SePayQRResponse(
        order_id=order.id,
        transaction_code=transaction_code,
        qr_url=qr_url,
        amount=amount,
        description=f"Purchase {request.credit_amount} credits",
        expires_at=expires_at
    )


@router.get("/status/{order_id}", response_model=SePayStatusResponse)
async def check_sepay_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID
) -> SePayStatusResponse:
    """Check SePay payment status by polling SePay API"""
    
    # Get order
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not order.sepay_transaction_code:
        raise HTTPException(status_code=400, detail="Not a SePay order")
    
    # If already paid, return immediately
    if order.status == OrderStatus.PAID:
        return SePayStatusResponse(
            order_id=order.id,
            transaction_code=order.sepay_transaction_code,
            status="paid",
            paid_at=order.paid_at
        )
    
    # Check if order expired (15 minutes)
    if order.created_at < datetime.utcnow() - timedelta(minutes=15):
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.EXPIRED
            session.add(order)
            session.commit()
        return SePayStatusResponse(
            order_id=order.id,
            transaction_code=order.sepay_transaction_code,
            status="expired",
            paid_at=None
        )
    
    # Poll SePay API to check transaction
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SEPAY_API_URL}/transactions/list",
                params={
                    "account_number": settings.SEPAY_ACCOUNT_NUMBER,
                    "limit": 20
                },
                headers={
                    "Authorization": f"Bearer {settings.SEPAY_API_KEY}"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"SePay API error: {response.status_code}")
                return SePayStatusResponse(
                    order_id=order.id,
                    transaction_code=order.sepay_transaction_code,
                    status="pending",
                    paid_at=None
                )
            
            data = response.json()
            logger.info(f"SePay API response: {data}")
            
            # Handle both formats: {"transactions": [...]} or direct list
            if isinstance(data, list):
                transactions = data
            else:
                transactions = data.get("transactions", [])
            
            logger.info(f"Found {len(transactions)} transactions, looking for code: {order.sepay_transaction_code}")
            
            # Check if transaction code exists in recent transactions
            for tx in transactions:
                content = tx.get("transaction_content", "") or ""
                if order.sepay_transaction_code in content:
                    # Verify amount matches (convert to float for comparison)
                    tx_amount_raw = tx.get("amount_in", 0) or 0
                    tx_amount = float(tx_amount_raw) if tx_amount_raw else 0
                    if tx_amount >= float(order.amount):
                        # Payment confirmed!
                        order.status = OrderStatus.PAID
                        order.paid_at = datetime.utcnow()
                        order.sepay_transaction_id = str(tx.get("id", ""))
                        session.add(order)
                        session.commit()
                        
                        # Activate subscription or add credits
                        await _activate_order(session, order)
                        
                        return SePayStatusResponse(
                            order_id=order.id,
                            transaction_code=order.sepay_transaction_code,
                            status="paid",
                            paid_at=order.paid_at
                        )
            
            # Not found yet
            return SePayStatusResponse(
                order_id=order.id,
                transaction_code=order.sepay_transaction_code,
                status="pending",
                paid_at=None
            )
            
    except Exception as e:
        logger.error(f"Error checking SePay status: {e}")
        return SePayStatusResponse(
            order_id=order.id,
            transaction_code=order.sepay_transaction_code,
            status="pending",
            paid_at=None
        )


async def _activate_order(session: SessionDep, order: Order):
    """Activate subscription or add credits after successful payment"""
    try:
        if order.order_type == OrderType.SUBSCRIPTION and order.plan_code:
            plan_service = PlanService(session)
            plan = plan_service.get_by_code(order.plan_code)
            
            if plan:
                subscription_service = SubscriptionService(session)
                subscription, wallet, invoice = subscription_service.activate_subscription(
                    user_id=order.user_id,
                    plan=plan,
                    order=order,
                    auto_renew=order.auto_renew
                )
                logger.info(f"Activated subscription {subscription.id} for order {order.id}")
        
        elif order.order_type == OrderType.CREDIT and order.credit_amount:
            subscription_service = SubscriptionService(session)
            wallet, invoice = subscription_service.add_credits_to_wallet(
                user_id=order.user_id,
                credit_amount=order.credit_amount,
                order=order
            )
            logger.info(f"Added {order.credit_amount} credits for order {order.id}")
    
    except Exception as e:
        logger.error(f"Error activating order {order.id}: {e}")


@router.post("/cancel/{order_id}")
def cancel_sepay_payment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID
):
    """Cancel a pending SePay payment"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only cancel pending orders")
    
    order.status = OrderStatus.CANCELED
    session.add(order)
    session.commit()
    
    return {"message": "Payment cancelled"}
