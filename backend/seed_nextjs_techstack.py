"""Seed Next.js tech stack into database."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, select
from app.core.db import engine
from app.models.tech_stack import TechStack


def seed_nextjs_techstack():
    """Seed Next.js tech stack."""
    with Session(engine) as session:
        # Check if Next.js already exists
        existing = session.exec(
            select(TechStack).where(TechStack.code == "nextjs")
        ).first()
        
        if existing:
            print(f"✅ Next.js tech stack already exists (ID: {existing.id})")
            print(f"   Name: {existing.name}")
            print(f"   Active: {existing.is_active}")
            return existing
        
        # Create new Next.js tech stack
        nextjs_stack = TechStack(
            code="nextjs",
            name="Next.js",
            description="Next.js 16 with React 19, TypeScript, Tailwind CSS, and Prisma",
            image=None,  # Optional: add image URL if needed
            stack_config={
                "runtime": "node",
                "package_manager": "pnpm",
                "framework": "nextjs",
                "version": "16",
                "language": "typescript",
                "styling": "tailwindcss",
                "database": "prisma",
                "testing": "jest",
            },
            is_active=True,
            display_order=0,
        )
        
        session.add(nextjs_stack)
        session.commit()
        session.refresh(nextjs_stack)
        
        print(f"✅ Created Next.js tech stack (ID: {nextjs_stack.id})")
        print(f"   Code: {nextjs_stack.code}")
        print(f"   Name: {nextjs_stack.name}")
        print(f"   Description: {nextjs_stack.description}")
        print(f"   Config: {nextjs_stack.stack_config}")
        
        return nextjs_stack


def list_all_techstacks():
    """List all tech stacks in database."""
    with Session(engine) as session:
        stacks = session.exec(select(TechStack)).all()
        
        print(f"\n📊 Total tech stacks in database: {len(stacks)}")
        print("=" * 60)
        
        for stack in stacks:
            print(f"\nID: {stack.id}")
            print(f"Code: {stack.code}")
            print(f"Name: {stack.name}")
            print(f"Active: {stack.is_active}")
            print(f"Display Order: {stack.display_order}")
            if stack.description:
                print(f"Description: {stack.description}")
            if stack.stack_config:
                print(f"Config: {stack.stack_config}")
            print("-" * 60)


if __name__ == "__main__":
    print("🌱 Seeding Next.js Tech Stack\n")
    
    try:
        seed_nextjs_techstack()
        list_all_techstacks()
        print("\n✅ Seeding completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
