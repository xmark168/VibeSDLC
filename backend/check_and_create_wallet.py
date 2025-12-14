"""
Script to check and create wallet for users who don't have one
Run this script to ensure all users have a credit wallet
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.core.db import engine
from app.models import User, CreditWallet, Subscription, Plan
from uuid import uuid4


def check_and_create_wallets():
    """Check all users and create wallets for those who don't have one"""
    
    with Session(engine) as session:
        # Get all users
        users = session.exec(select(User)).all()
        
        print(f"Found {len(users)} users")
        print("-" * 80)
        
        for user in users:
            print(f"\nUser: {user.email} (ID: {user.id})")
            
            # Check if user has any wallet
            wallet_stmt = select(CreditWallet).where(CreditWallet.user_id == user.id)
            wallets = session.exec(wallet_stmt).all()
            
            if wallets:
                print(f"  ✓ Has {len(wallets)} wallet(s)")
                for wallet in wallets:
                    remaining = (wallet.total_credits or 0) - (wallet.used_credits or 0)
                    print(f"    - Wallet {wallet.id}: {remaining}/{wallet.total_credits} credits remaining")
            else:
                print(f"  ✗ No wallet found!")
                
                # Check if user has subscription
                sub_stmt = (
                    select(Subscription)
                    .where(Subscription.user_id == user.id)
                    .where(Subscription.status == "active")
                )
                subscription = session.exec(sub_stmt).first()
                
                if subscription:
                    print(f"    Has active subscription: {subscription.id}")
                    
                    # Create wallet for this subscription
                    plan = session.get(Plan, subscription.plan_id)
                    if plan:
                        wallet = CreditWallet(
                            id=uuid4(),
                            user_id=user.id,
                            subscription_id=subscription.id,
                            wallet_type="subscription",
                            total_credits=plan.monthly_credits or 99999,
                            used_credits=0
                        )
                        session.add(wallet)
                        session.commit()
                        print(f"    ✓ Created wallet with {wallet.total_credits} credits")
                else:
                    print(f"    No active subscription found")
                    
                    # Create a default Free plan wallet
                    wallet = CreditWallet(
                        id=uuid4(),
                        user_id=user.id,
                        subscription_id=None,
                        wallet_type="subscription",
                        total_credits=99999,  # Free plan default credits
                        used_credits=0
                    )
                    session.add(wallet)
                    session.commit()
                    print(f"    ✓ Created default Free plan wallet with {wallet.total_credits} credits")
        
        print("\n" + "=" * 80)
        print("Done!")


if __name__ == "__main__":
    print("Checking and creating wallets for users...")
    print("=" * 80)
    check_and_create_wallets()
