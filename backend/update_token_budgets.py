#!/usr/bin/env python3
"""
One-time script to update token budget limits for existing projects.
Increases daily limit from 100K to 10M and monthly limit from 2M to 200M.
"""
import asyncio
from sqlmodel import Session, select
from app.core.db import engine
from app.models import Project

async def main():
    print("Updating token budget limits for existing projects...")
    
    with Session(engine) as session:
        # Get all projects
        stmt = select(Project)
        projects = session.exec(stmt).all()
        
        updated_count = 0
        for project in projects:
            needs_update = False
            
            # Update daily budget if it's still at old default
            if project.token_budget_daily == 100000:
                project.token_budget_daily = 10000000
                needs_update = True
                print(f"  Project {project.name}: Daily 100K → 10M")
            
            # Update monthly budget if it's still at old default
            if project.token_budget_monthly == 2000000:
                project.token_budget_monthly = 200000000
                needs_update = True
                print(f"  Project {project.name}: Monthly 2M → 200M")
            
            if needs_update:
                session.add(project)
                updated_count += 1
        
        # Commit all changes
        session.commit()
        
        print(f"\n✅ Updated {updated_count} projects")
        print(f"   Total projects: {len(projects)}")

if __name__ == "__main__":
    asyncio.run(main())
