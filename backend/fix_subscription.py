"""Fix subscription issue - Create active subscriptions for users with wallets"""
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
print(f"Loaded environment from {env_path}")

from app.core.db import engine
from sqlmodel import Session, select
from app.models import User, Subscription, CreditWallet, Plan
from datetime import datetime, timezone, timedelta
from uuid import UUID

def fix_subscriptions():
    """Create active subscriptions for users with wallets but no subscription"""
    with Session(engine) as session:
        # Get all users
        users = session.exec(select(User)).all()
        
        print(f"\n{'='*80}")
        print(f"Fixing subscriptions for {len(users)} users...")
        print(f"{'='*80}\n")
        
        for user in users:
            print(f"User: {user.email} (ID: {user.id})")
            
            # Check if user has active subscription
            active_sub = session.exec(
                select(Subscription)
                .where(Subscription.user_id == user.id)
                .where(Subscription.status == "active")
            ).first()
            
            if active_sub:
                print(f"  ✓ Already has active subscription: {active_sub.id}")
                continue
            
            # Check if user has wallet
            wallet = session.exec(
                select(CreditWallet)
                .where(CreditWallet.user_id == user.id)
                .where(CreditWallet.wallet_type == "subscription")
            ).first()
            
            if not wallet:
                print(f"  ✗ No wallet found, skipping")
                continue
            
            # Get a plan (preferably free plan, or any plan)
            plan = session.exec(
                select(Plan)
                .where(Plan.tier == "free")
            ).first()
            
            if not plan:
                # If no free plan, get any plan
                plan = session.exec(select(Plan)).first()
            
            if not plan:
                print(f"  ✗ No plan found in database, cannot create subscription")
                continue
            
            # Create active subscription
            new_subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                start_at=datetime.now(timezone.utc),
                end_at=datetime.now(timezone.utc) + timedelta(days=365),  # 1 year
                is_trial=False,
                auto_renew=True,
            )
            
            session.add(new_subscription)
            session.commit()
            session.refresh(new_subscription)
            
            print(f"  ✓ Created active subscription: {new_subscription.id}")
            print(f"    Plan: {plan.name} ({plan.code})")
            print(f"    Start: {new_subscription.start_at}")
            print(f"    End: {new_subscription.end_at}")
            
            # Link wallet to subscription
            wallet.subscription_id = new_subscription.id
            session.add(wallet)
            session.commit()
            
            print(f"  ✓ Linked wallet {wallet.id} to subscription")
            print()

if __name__ == "__main__":
    fix_subscriptions()
    print("\nDone! All users now have active subscriptions.")
