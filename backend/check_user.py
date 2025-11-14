"""
Script to check user status in database
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User

async def check_user():
    async with AsyncSessionLocal() as db:
        # Get all users
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()

        print(f"\n{'='*60}")
        print(f"Total users: {len(users)}")
        print(f"{'='*60}\n")

        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Fullname: {user.fullname}")
            print(f"✅ is_active: {user.is_active}")
            print(f"Failed login attempts: {user.failed_login_attempts}")
            print(f"Locked until: {user.locked_until}")
            print(f"Created at: {user.created_at}")
            print(f"{'-'*60}\n")

if __name__ == "__main__":
    asyncio.run(check_user())
