import logging

from sqlmodel import Session, create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings, database_settings
from app.models import Plan, Role, TechStack, User
from app.schemas import UserCreate
from app.services import UserService

logger = logging.getLogger(__name__)

# Main engine for FastAPI master process (sync - for gradual migration)
engine = create_engine(str(database_settings.SQLALCHEMY_DATABASE_URI))

# NEW: Async engine for async operations
async_engine = create_async_engine(
    str(database_settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql+psycopg://",
        "postgresql+asyncpg://"
    ),
    echo=False,
    pool_size=20,
    max_overflow=50,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Async session factory
async_session_maker = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_worker_engine(pool_size: int = 5, max_overflow: int = 10):
    return create_engine(
        str(database_settings.SQLALCHEMY_DATABASE_URI),
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def init_db(session: Session) -> None:
    # 1. Seed superuser if not exists
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
        )
        user_service = UserService(session)
        user = user_service.create(user_in)
        user.role = Role.ADMIN
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Created superuser: {settings.FIRST_SUPERUSER}")

    # 2. Seed default plans if not exists
    default_plans = [
        {
            "code": "FREE",
            "name": "Free Plan",
            "description": "Gói miễn phí dành cho người dùng mới",
            "monthly_price": 0,
            "yearly_discount_percentage": 0,
            "currency": "VND",
            "monthly_credits": 100,
            "additional_credit_price": None,
            "available_project": 1,
            "is_active": True,
            "tier": "free",
            "sort_index": 0,
            "is_featured": False,
            "is_custom_price": False,
            "features_text": "100 credits/tháng, 1 project",
        },
        {
            "code": "PRO",
            "name": "Pro Plan",
            "description": "Gói Pro dành cho cá nhân và team nhỏ",
            "monthly_price": 199000,
            "yearly_discount_percentage": 20,
            "currency": "VND",
            "monthly_credits": 1000,
            "additional_credit_price": 50000,
            "available_project": 5,
            "is_active": True,
            "tier": "pay",
            "sort_index": 1,
            "is_featured": True,
            "is_custom_price": False,
            "features_text": "1000 credits/tháng, 5 projects, Hỗ trợ ưu tiên",
        },
        {
            "code": "ULTRA",
            "name": "Ultra Plan",
            "description": "Gói Ultra dành cho doanh nghiệp",
            "monthly_price": 499000,
            "yearly_discount_percentage": 25,
            "currency": "VND",
            "monthly_credits": 5000,
            "additional_credit_price": 40000,
            "available_project": -1,  # Unlimited
            "is_active": True,
            "tier": "pay",
            "sort_index": 2,
            "is_featured": False,
            "is_custom_price": False,
            "features_text": "5000 credits/tháng, Unlimited projects, Hỗ trợ 24/7",
        },
    ]

    for plan_data in default_plans:
        existing_plan = session.exec(
            select(Plan).where(Plan.code == plan_data["code"])
        ).first()

        if not existing_plan:
            plan = Plan(**plan_data)
            session.add(plan)
            session.commit()
            logger.info(f"Created {plan_data['code']} plan with {plan_data['monthly_credits']} monthly credits")

    # 3. Seed default tech stacks if not exists
    default_tech_stacks = [
        {
            "code": "nextjs",
            "name": "Next.js Full Stack",
            "description": "Modern full-stack framework with React, TypeScript, and Tailwind CSS",
            "image": "https://images.icon-icons.com/3388/PNG/512/nextjs_icon_212861.png",
            "stack_config": {
                "runtime": "bun",
                "framework": "nextjs",
                "language": "typescript",
                "styling": "tailwindcss",
                "database": "prisma",
                "auth": "next-auth",
            },
            "is_active": True,
            "display_order": 0,
        },
    ]

    for stack_data in default_tech_stacks:
        existing_stack = session.exec(
            select(TechStack).where(TechStack.code == stack_data["code"])
        ).first()

        if not existing_stack:
            stack = TechStack(**stack_data)
            session.add(stack)
            session.commit()
            logger.info(f"Created {stack_data['code']} tech stack")
