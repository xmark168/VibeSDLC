"""Payment API Routes - PayOS Integration"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from uuid import UUID
import hmac
import hashlib
import json
import logging

from app.api.deps import CurrentUser, SessionDep
from app.schemas.payment import (
    CreatePaymentRequest,
    PaymentLinkResponse,
    PaymentStatusResponse,
    WebhookRequest
)
from app.services.order_service import OrderService
from app.services.subscription_service import SubscriptionService
from app.services.plan_service import PlanService
from app.models import OrderStatus, Plan, Order, Invoice
from app.core.config import settings
from sqlmodel import select

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


@router.post("/create", response_model=PaymentLinkResponse)
def create_payment_link(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payment_request: CreatePaymentRequest
) -> PaymentLinkResponse:
    """
    Create PayOS payment link for subscription
    """
    # Get plan
    plan_service = PlanService(session)
    plan = plan_service.get_by_id(payment_request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.is_active:
        raise HTTPException(status_code=400, detail="Plan is not active")

    # Validate billing cycle
    if payment_request.billing_cycle == "monthly" and not plan.monthly_price:
        raise HTTPException(status_code=400, detail="Monthly billing not available for this plan")
    if payment_request.billing_cycle == "yearly" and not plan.yearly_price:
        raise HTTPException(status_code=400, detail="Yearly billing not available for this plan")

    # Create order and payment link
    order_service = OrderService(session)

    return_url = payment_request.return_url or f"{settings.FRONTEND_HOST}/upgrade?status=success"
    cancel_url = payment_request.cancel_url or f"{settings.FRONTEND_HOST}/upgrade?status=cancel"

    try:
        order, payment_link = order_service.create_subscription_order(
            user_id=current_user.id,
            plan=plan,
            billing_cycle=payment_request.billing_cycle,
            return_url=return_url,
            cancel_url=cancel_url
        )

        return PaymentLinkResponse(
            order_id=order.id,
            payos_order_code=order.payos_order_code,
            checkout_url=order.checkout_url,
            qr_code=order.qr_code,
            amount=int(order.amount),
            description=f"{plan.name} - {payment_request.billing_cycle.capitalize()} subscription"
        )

    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{order_id}", response_model=PaymentStatusResponse)
def get_payment_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID
) -> PaymentStatusResponse:
    """
    Check payment status for an order and auto-activate subscription if paid
    """
    order_service = OrderService(session)
    order = order_service.get_order_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check latest status from PayOS
    payment_info = order_service.check_payment_status(order)

    # Update local status if changed and activate subscription
    if payment_info.get("status") == "PAID" and order.status != OrderStatus.PAID:
        order = order_service.update_order_status(
            order,
            OrderStatus.PAID,
            payment_info.get("id")
        )

        # Auto-activate subscription if not already done
        if order.plan_code and not order.subscription_id:
            try:
                plan_service = PlanService(session)
                plan = plan_service.get_by_code(order.plan_code)

                if plan:
                    subscription_service = SubscriptionService(session)
                    subscription, wallet, invoice = subscription_service.activate_subscription(
                        user_id=order.user_id,
                        plan=plan,
                        order=order
                    )
                    logger.info(f"Auto-activated subscription {subscription.id} for order {order.id}")
            except Exception as e:
                logger.error(f"Failed to auto-activate subscription: {e}")

    return PaymentStatusResponse(
        order_id=order.id,
        status=order.status.value,
        paid_at=order.paid_at,
        payos_transaction_id=order.payos_transaction_id
    )


@router.post("/webhook")
async def payos_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep
):
    """
    PayOS webhook endpoint for payment notifications
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("x-payos-signature", "")

        # Verify webhook signature
        if not verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse webhook data
        webhook_data = json.loads(body)
        payos_order_code = webhook_data.get("data", {}).get("orderCode")

        if not payos_order_code:
            raise HTTPException(status_code=400, detail="Missing orderCode")

        # Process webhook immediately (not in background to avoid session issues)
        logger.info(f"Processing webhook for order code: {payos_order_code}")
        process_payment_webhook(session, webhook_data)

        return {"success": True, "message": "Webhook processed"}

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify PayOS webhook signature using HMAC-SHA256"""
    if not settings.PAYOS_WEBHOOK_SECRET:
        logger.warning("PAYOS_WEBHOOK_SECRET not configured, skipping signature verification")
        return True  # Skip verification in dev if not configured

    expected_signature = hmac.new(
        settings.PAYOS_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def process_payment_webhook(session: SessionDep, webhook_data: dict):
    """Background task to process payment webhook"""
    try:
        data = webhook_data.get("data", {})
        payos_order_code = data.get("orderCode")
        status_code = data.get("code")
        transaction_id = data.get("reference")

        # Get order
        order_service = OrderService(session)
        order = order_service.get_order_by_payos_code(payos_order_code)

        if not order:
            logger.error(f"Order not found for PayOS code: {payos_order_code}")
            return

        # Skip if already processed
        if order.status == OrderStatus.PAID:
            logger.info(f"Order {order.id} already paid")
            return

        # Update order status
        if status_code == "00":  # Success code
            order = order_service.update_order_status(
                order,
                OrderStatus.PAID,
                transaction_id
            )

            # Activate subscription
            plan_service = PlanService(session)
            plan = plan_service.get_by_code(order.plan_code)

            if plan:
                subscription_service = SubscriptionService(session)
                subscription, wallet, invoice = subscription_service.activate_subscription(
                    user_id=order.user_id,
                    plan=plan,
                    order=order
                )
                logger.info(f"Subscription {subscription.id} activated for order {order.id}")
            else:
                logger.error(f"Plan {order.plan_code} not found")

        else:
            order_service.update_order_status(order, OrderStatus.FAILED)
            logger.warning(f"Payment failed for order {order.id}: {status_code}")

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")


@router.post("/sync-status-by-code/{order_code}")
async def sync_order_status_by_code(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    order_code: int
):
    """
    Manually sync order status with PayOS using orderCode (for local dev when webhook doesn't work)
    """
    logger.info(f"=== SYNC-STATUS BY CODE ENDPOINT CALLED === Order Code: {order_code}")

    order_service = OrderService(session)
    order = order_service.get_order_by_payos_code(order_code)

    if not order:
        logger.error(f"Order not found for PayOS code: {order_code}")
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id:
        logger.warning(f"Unauthorized access attempt to order {order.id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized")

    # Skip if already paid
    if order.status == OrderStatus.PAID:
        logger.info(f"Order {order.id} already paid")
        return {"message": "Order already paid", "status": "PAID"}

    try:
        # Check payment status from PayOS
        payment_info = order_service.check_payment_status(order)
        logger.info(f"PayOS status for order {order.id}: {payment_info}")

        # Update if paid
        if payment_info.get("status") == "PAID":
            order = order_service.update_order_status(
                order,
                OrderStatus.PAID,
                payment_info.get("id")
            )

            # Activate subscription
            if order.plan_code:
                plan_service = PlanService(session)
                plan = plan_service.get_by_code(order.plan_code)

                if plan:
                    subscription_service = SubscriptionService(session)
                    subscription, wallet, invoice = subscription_service.activate_subscription(
                        user_id=order.user_id,
                        plan=plan,
                        order=order
                    )
                    logger.info(f"Activated subscription {subscription.id}")
                    return {
                        "message": "Payment confirmed and subscription activated",
                        "status": "PAID",
                        "subscription_id": str(subscription.id)
                    }

        return {"message": "Payment not completed yet", "status": payment_info.get("status", "UNKNOWN")}

    except Exception as e:
        logger.error(f"Failed to sync order status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_payment_history(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 10,
    offset: int = 0
):
    """
    Get payment history for current user with pagination
    """
    # Get total count
    count_statement = (
        select(Order)
        .where(Order.user_id == current_user.id)
    )
    total = len(session.exec(count_statement).all())

    # Get paginated data
    statement = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = session.exec(statement).all()

    return {
        "data": [
            {
                "id": str(order.id),
                "order_type": order.order_type,
                "amount": order.amount,
                "status": order.status.value,
                "plan_code": order.plan_code,
                "billing_cycle": order.billing_cycle,
                "created_at": order.created_at.isoformat(),
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                "payos_order_code": order.payos_order_code,
            }
            for order in orders
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/invoice/{order_id}")
def get_invoice(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID
):
    """
    Get invoice details for an order
    """
    # Get order
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get invoice
    statement = select(Invoice).where(Invoice.order_id == order_id)
    invoice = session.exec(statement).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get plan details
    plan = None
    if order.plan_code:
        plan_service = PlanService(session)
        plan = plan_service.get_by_code(order.plan_code)

    return {
        "invoice": {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "billing_name": invoice.billing_name,
            "billing_address": invoice.billing_address,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "issue_date": invoice.issue_date.isoformat(),
            "status": invoice.status.value,
        },
        "order": {
            "id": str(order.id),
            "order_type": order.order_type,
            "plan_code": order.plan_code,
            "billing_cycle": order.billing_cycle,
            "amount": order.amount,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "payos_order_code": order.payos_order_code,
            "payos_transaction_id": order.payos_transaction_id,
        },
        "plan": {
            "name": plan.name,
            "code": plan.code,
            "description": plan.description,
            "monthly_credits": plan.monthly_credits,
            "available_project": plan.available_project,
        } if plan else None
    }
