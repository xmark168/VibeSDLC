#!/usr/bin/env python
"""
Test script for Business Analyst workflow on terminal.
Run: uv run python test_ba_flow.py
"""

import asyncio
import sys
from uuid import uuid4

from sqlmodel import Session, create_engine

from app.core.config import settings
from app.agents.roles.business_analyst.crew import BusinessAnalystCrew
from app.models import (
    BASession, BASessionStatus, Requirement, ProductBrief,
    BusinessFlow, Epic, Story, Project, User
)


def get_db_session():
    """Create database session."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    return Session(engine)


def create_test_user_and_project(db_session: Session):
    """Create test user and project if not exists."""
    # Check for existing test user
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="test",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        print(f"Created test user: {user.id}")

    # Check for existing test project
    project = db_session.query(Project).filter(
        Project.owner_id == user.id,
        Project.name == "Test BA Project"
    ).first()

    if not project:
        project = Project(
            code="TEST-BA",
            name="Test BA Project",
            owner_id=user.id,
            is_init=True
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        print(f"Created test project: {project.id}")

    return user, project


def display_requirements(db_session: Session, session_id):
    """Display collected requirements."""
    reqs = db_session.query(Requirement).filter(
        Requirement.session_id == session_id
    ).all()

    if not reqs:
        print("\nNo requirements collected yet.")
        return

    print("\n" + "=" * 60)
    print("COLLECTED REQUIREMENTS")
    print("=" * 60)

    # Group by category
    grouped = {}
    for r in reqs:
        cat = r.category.value
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(r.content)

    for cat, items in grouped.items():
        print(f"\n{cat.replace('_', ' ').upper()}:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")

    print(f"\nTotal: {len(reqs)} requirements")
    print("=" * 60)


def display_brief(db_session: Session, session_id):
    """Display Product Brief."""
    brief = db_session.query(ProductBrief).filter(
        ProductBrief.session_id == session_id
    ).first()

    if not brief:
        print("\nNo Product Brief created yet.")
        return

    print("\n" + "=" * 60)
    print("PRODUCT BRIEF")
    print("=" * 60)
    print(f"\nProduct Summary:\n{brief.product_summary}")
    print(f"\nProblem Statement:\n{brief.problem_statement}")
    print(f"\nTarget Users:\n{brief.target_users}")
    print(f"\nProduct Goals:\n{brief.product_goals}")
    print(f"\nScope:\n{brief.scope}")
    print("=" * 60)


def display_flows(db_session: Session, session_id):
    """Display business flows."""
    flows = db_session.query(BusinessFlow).filter(
        BusinessFlow.session_id == session_id
    ).order_by(BusinessFlow.flow_order).all()

    if not flows:
        print("\nNo business flows designed yet.")
        return

    print("\n" + "=" * 60)
    print("BUSINESS FLOWS")
    print("=" * 60)

    for i, flow in enumerate(flows, 1):
        print(f"\n{i}. {flow.name}")
        print(f"   Description: {flow.description}")
        if flow.steps:
            print("   Steps:")
            for j, step in enumerate(flow.steps, 1):
                print(f"     {j}. {step}")
        if flow.actors:
            print(f"   Actors: {', '.join(flow.actors)}")

    print("=" * 60)


def display_backlog(db_session: Session, project_id):
    """Display Epics and Stories."""
    epics = db_session.query(Epic).filter(
        Epic.project_id == project_id
    ).all()

    stories = db_session.query(Story).filter(
        Story.project_id == project_id
    ).all()

    if not epics and not stories:
        print("\nNo backlog created yet.")
        return

    print("\n" + "=" * 60)
    print("PRODUCT BACKLOG")
    print("=" * 60)

    for epic in epics:
        print(f"\nEPIC: {epic.title}")
        print(f"  Domain: {epic.domain or 'N/A'}")
        print(f"  Description: {epic.description or 'N/A'}")

        # Stories for this epic
        epic_stories = [s for s in stories if s.epic_id == epic.id]
        if epic_stories:
            print(f"  Stories ({len(epic_stories)}):")
            for story in epic_stories:
                priority = story.story_priority.value if story.story_priority else "Medium"
                print(f"    - {story.title} [{story.story_point}pts, {priority}]")

    # Independent stories
    independent = [s for s in stories if s.epic_id is None]
    if independent:
        print(f"\nINDEPENDENT STORIES ({len(independent)}):")
        for story in independent:
            priority = story.story_priority.value if story.story_priority else "Medium"
            print(f"  - {story.title} [{story.story_point}pts, {priority}]")

    print("=" * 60)


async def run_analysis_phase(crew, project_id, user_id):
    """Run the analysis phase interactively."""
    print("\n" + "=" * 60)
    print("PHASE 1: ANALYSIS - Requirements Gathering")
    print("=" * 60)
    print("\nTell me about your project. What problem do you want to solve?")
    print("Commands: 'status', 'done', 'quit'")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                print("Session ended.")
                return False

            if user_input.lower() == 'status':
                display_requirements(crew.db_session, crew.ba_session.id)
                continue

            if user_input.lower() == 'done':
                # Check if enough requirements
                req_count = crew.db_session.query(Requirement).filter(
                    Requirement.session_id == crew.ba_session.id
                ).count()

                if req_count < 3:
                    print(f"\nNeed at least 3 requirements to proceed. Current: {req_count}")
                    continue

                print("\nMoving to Product Brief creation...")
                return True

            # Execute analysis
            print("\nAnalyzing your input...")
            result = await crew.execute_analysis(
                user_message=user_input,
                project_id=project_id,
                user_id=user_id
            )

            if result.get("success"):
                response = result.get("assistant_response", "")
                if response:
                    print(f"\nBA: {response}")
                else:
                    print("\nBA: I've noted your requirements. Please continue or type 'done' when finished.")

                # Show extracted requirements
                extracted = result.get("extracted_requirements", {})
                total = sum(len(v) for v in extracted.values())
                if total > 0:
                    print(f"\n[Extracted {total} requirements from this message]")
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            print("\n\nSession interrupted.")
            return False


async def run_brief_phase(crew, project_id, user_id):
    """Run the brief phase."""
    print("\n" + "=" * 60)
    print("PHASE 2: PRODUCT BRIEF Creation")
    print("=" * 60)

    # Create initial brief
    print("\nCreating Product Brief from requirements...")
    result = await crew.execute_brief_phase(
        project_id=project_id,
        user_id=user_id
    )

    if not result.get("success"):
        print(f"\nError creating brief: {result.get('error', 'Unknown error')}")
        return False

    # Review and refinement loop
    while True:
        display_brief(crew.db_session, crew.ba_session.id)

        # Ask for approval
        response = input("\nApprove this brief? (y/refine/quit): ").strip().lower()

        if response in ['y', 'yes']:
            return True
        elif response == 'quit':
            return False
        elif response == 'refine':
            feedback = input("What would you like to change? ").strip()
            if feedback:
                print("\nRefining Product Brief...")
                result = await crew.execute_brief_phase(
                    revision_feedback=feedback,
                    project_id=project_id,
                    user_id=user_id
                )
                if not result.get("success"):
                    print(f"\nError refining brief: {result.get('error', 'Unknown error')}")
                    # Continue loop to show current brief
        else:
            print("Invalid input. Please enter 'y', 'refine', or 'quit'.")


async def run_solution_phase(crew, project_id, user_id):
    """Run the solution phase."""
    print("\n" + "=" * 60)
    print("PHASE 3: SOLUTION DESIGN - Business Flows")
    print("=" * 60)

    # Create initial solution
    print("\nDesigning business flows...")
    result = await crew.execute_solution_phase(
        project_id=project_id,
        user_id=user_id
    )

    if not result.get("success"):
        print(f"\nError designing solution: {result.get('error', 'Unknown error')}")
        return False

    # Review and refinement loop
    while True:
        display_flows(crew.db_session, crew.ba_session.id)

        # Ask for approval
        response = input("\nApprove these flows? (y/refine/quit): ").strip().lower()

        if response in ['y', 'yes']:
            return True
        elif response == 'quit':
            return False
        elif response == 'refine':
            feedback = input("What would you like to change? ").strip()
            if feedback:
                print("\nRefining business flows...")
                result = await crew.execute_solution_phase(
                    revision_feedback=feedback,
                    project_id=project_id,
                    user_id=user_id
                )
                if not result.get("success"):
                    print(f"\nError refining solution: {result.get('error', 'Unknown error')}")
                    # Continue loop to show current flows
        else:
            print("Invalid input. Please enter 'y', 'refine', or 'quit'.")


async def run_backlog_phase(crew, project_id, user_id):
    """Run the backlog phase."""
    print("\n" + "=" * 60)
    print("PHASE 4: BACKLOG Creation - Epics & Stories")
    print("=" * 60)

    # Create initial backlog
    print("\nCreating Epics and User Stories...")
    result = await crew.execute_backlog_phase(
        project_id=project_id,
        user_id=user_id
    )

    if not result.get("success"):
        print(f"\nError creating backlog: {result.get('error', 'Unknown error')}")
        return False

    # Review and refinement loop
    while True:
        display_backlog(crew.db_session, project_id)

        # Ask for approval
        response = input("\nApprove this backlog? (y/refine/quit): ").strip().lower()

        if response in ['y', 'yes']:
            return True
        elif response == 'quit':
            return False
        elif response == 'refine':
            feedback = input("What would you like to change? ").strip()
            if feedback:
                print("\nRefining backlog...")
                result = await crew.execute_backlog_phase(
                    revision_feedback=feedback,
                    project_id=project_id,
                    user_id=user_id
                )
                if not result.get("success"):
                    print(f"\nError refining backlog: {result.get('error', 'Unknown error')}")
                    # Continue loop to show current backlog
        else:
            print("Invalid input. Please enter 'y', 'refine', or 'quit'.")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("BUSINESS ANALYST WORKFLOW TEST")
    print("=" * 60)
    print("\nThis will test the complete BA workflow:")
    print("  1. Analysis - Gather requirements")
    print("  2. Brief - Create Product Brief")
    print("  3. Solution - Design business flows")
    print("  4. Backlog - Create Epics & Stories")
    print("=" * 60)

    # Setup
    db_session = get_db_session()
    user, project = create_test_user_and_project(db_session)

    print(f"\nUsing project: {project.name} ({project.id})")
    print(f"User: {user.email}")

    # Create crew
    crew = BusinessAnalystCrew(db_session=db_session)
    crew.create_session(project.id, user.id)

    print(f"Created BA session: {crew.ba_session.id}")

    try:
        # Phase 1: Analysis
        if not await run_analysis_phase(crew, project.id, user.id):
            print("\nWorkflow cancelled at Analysis phase.")
            return

        # Phase 2: Brief
        if not await run_brief_phase(crew, project.id, user.id):
            print("\nWorkflow cancelled at Brief phase.")
            return

        # Phase 3: Solution
        if not await run_solution_phase(crew, project.id, user.id):
            print("\nWorkflow cancelled at Solution phase.")
            return

        # Phase 4: Backlog
        if not await run_backlog_phase(crew, project.id, user.id):
            print("\nWorkflow cancelled at Backlog phase.")
            return

        # Success
        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nSession ID: {crew.ba_session.id}")
        print(f"Status: {crew.ba_session.status.value}")
        print("\nAll artifacts have been saved to database.")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()


if __name__ == "__main__":
    asyncio.run(main())
