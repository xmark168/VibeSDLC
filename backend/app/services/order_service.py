"""Order Service - Manages payment orders and PayOS integration"""

from uuid import UUID
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models import Order, OrderType, OrderStatus, Plan, User
from app.core.payos_client import payos_client
from payos.types import CreatePaymentLinkRequest, ItemData
import logging
import random

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order management and PayOS payment integration"""

    def __init__(self, session: Session):
        self.session = session

    def generate_order_code(self) -> int:
        """Generate unique PayOS order code (must be int)"""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_suffix = random.randint(1000, 9999)
        return int(f"{timestamp}{random_suffix}")

    def create_subscription_order(
        self,
        user_id: UUID,
        plan: Plan,
        billing_cycle: str,
        auto_renew: bool,
        return_url: str,
        cancel_url: str
    ) -> tuple[Order, dict]:
        """
        Create order and PayOS payment link
        Returns: (Order, payment_link_data)
        """
        # Calculate amount
        amount = plan.monthly_price if billing_cycle == "monthly" else plan.yearly_price
        if not amount:
            raise ValueError(f"Plan {plan.code} has no price for {billing_cycle}")

        # Generate order code
        payos_order_code = self.generate_order_code()

        # Create Order record
        order = Order(
            user_id=user_id,
            order_type=OrderType.SUBSCRIPTION,
            amount=float(amount),
            status=OrderStatus.PENDING,
            payos_order_code=payos_order_code,
            billing_cycle=billing_cycle,
            plan_code=plan.code,
            auto_renew=auto_renew,  # Store auto_renew preference
            is_active=True
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Create PayOS payment link
        try:
            client = payos_client()

            # Create payment request using new SDK v2 API
            payment_request = CreatePaymentLinkRequest(
                order_code=payos_order_code,
                amount=int(amount),
                description=f"{plan.name} - {billing_cycle.capitalize()} subscription",
                items=[
                    ItemData(
                        name=f"{plan.name} ({billing_cycle})",
                        quantity=1,
                        price=int(amount)
                    )
                ],
                return_url=return_url,
                cancel_url=cancel_url
            )

            # Call new SDK v2 method
            response = client.payment_requests.create(payment_request)

            # Update order with PayOS data
            order.payment_link_id = response.payment_link_id
            order.checkout_url = response.checkout_url
            order.qr_code = response.qr_code
            self.session.commit()
            self.session.refresh(order)

            return order, response.model_dump()

        except Exception as e:
            logger.error(f"Failed to create PayOS link: {e}")
            order.status = OrderStatus.FAILED
            self.session.commit()
            raise

    def create_credit_purchase_order(
        self,
        user_id: UUID,
        credit_amount: int,
        return_url: str,
        cancel_url: str
    ) -> tuple[Order, dict]:
        """
        Create order for credit purchase and PayOS payment link
        Returns: (Order, payment_link_data)
        """
        # Get user's current plan to determine credit price
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        # Get user's active subscription to get plan
        from app.models import Subscription
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        subscription = self.session.exec(statement).first()

        if not subscription:
            raise ValueError("No active subscription found. Please subscribe to a plan first.")

        # Get plan details
        plan = self.session.get(Plan, subscription.plan_id)
        if not plan or not plan.additional_credit_price:
            raise ValueError("Plan does not support credit purchases")

        # Calculate total price
        # additional_credit_price is per 100 credits
        price_per_credit = plan.additional_credit_price / 100
        total_amount = int(price_per_credit * credit_amount)

        # Generate order code
        payos_order_code = self.generate_order_code()

        # Create Order record
        order = Order(
            user_id=user_id,
            order_type=OrderType.CREDIT,
            amount=float(total_amount),
            status=OrderStatus.PENDING,
            payos_order_code=payos_order_code,
            credit_amount=credit_amount,  # Store credit amount
            is_active=True
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Create PayOS payment link
        try:
            client = payos_client()

            payment_request = CreatePaymentLinkRequest(
                order_code=payos_order_code,
                amount=total_amount,
                description=f"Purchase {credit_amount} credits",
                items=[
                    ItemData(
                        name=f"{credit_amount} credits",
                        quantity=1,
                        price=total_amount
                    )
                ],
                return_url=return_url,
                cancel_url=cancel_url
            )

            response = client.payment_requests.create(payment_request)

            # Update order with PayOS data
            order.payment_link_id = response.payment_link_id
            order.checkout_url = response.checkout_url
            order.qr_code = response.qr_code
            self.session.commit()
            self.session.refresh(order)

            return order, response.model_dump()

        except Exception as e:
            logger.error(f"Failed to create PayOS link for credit purchase: {e}")
            order.status = OrderStatus.FAILED
            self.session.commit()
            raise

    def get_order_by_id(self, order_id: UUID) -> Order | None:
        """Get order by ID"""
        return self.session.get(Order, order_id)

    def get_order_by_payos_code(self, payos_order_code: int) -> Order | None:
        """Get order by PayOS order code"""
        statement = select(Order).where(Order.payos_order_code == payos_order_code)
        return self.session.exec(statement).first()

    def update_order_status(
        self,
        order: Order,
        status: OrderStatus,
        payos_transaction_id: str | None = None
    ) -> Order:
        """Update order status and transaction details"""
        order.status = status
        if status == OrderStatus.PAID:
            order.paid_at = datetime.now(timezone.utc)
        if payos_transaction_id:
            order.payos_transaction_id = payos_transaction_id

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def check_payment_status(self, order: Order) -> dict:
        """Check payment status from PayOS"""
        try:
            client = payos_client()
            payment_link = client.payment_requests.get(order.payos_order_code)
            return payment_link.model_dump()
        except Exception as e:
            logger.error(f"Failed to check payment status: {e}")
            return {"status": "UNKNOWN", "error": str(e)}
