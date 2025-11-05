"""Sprint Persistence Service - Lưu sprint plan & backlog items vào database."""

from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select

from app.models import Sprint, BacklogItem, Project
from app.schemas import SprintCreate, BacklogItemCreate


class SprintPersistenceService:
    """Service để lưu sprint plan & backlog items từ PO Agent vào database."""

    @staticmethod
    def save_sprint_plan(
        session: Session,
        project_id: UUID,
        sprint_plan: dict,
        backlog_items: list[dict]
    ) -> dict:
        """Save sprint plan & backlog items to database.

        Args:
            session: Database session
            project_id: Project ID
            sprint_plan: Sprint plan data từ PO Agent
            backlog_items: Backlog items data từ PO Agent

        Returns:
            dict: Saved data với database IDs
        """
        print("\n" + "=" * 80)
        print("💾 SPRINT PERSISTENCE - Saving to Database")
        print("=" * 80)
        print(f"   Project ID: {project_id}")
        print(f"   Sprint Plan Keys: {list(sprint_plan.keys())}")
        print(f"   Sprints in plan: {len(sprint_plan.get('sprints', []))}")
        print(f"   Backlog Items: {len(backlog_items)}")
        print("=" * 80 + "\n")

        try:
            # Validate project exists
            print(f"[1/3] Validating project {project_id}...")
            project = session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            print(f"   ✓ Project found: {project.name}")

            # Extract sprints from sprint_plan
            print(f"\n[2/3] Extracting sprints from sprint_plan...")
            sprints_data = sprint_plan.get("sprints", [])
            print(f"   Found {len(sprints_data)} sprints")
            if not sprints_data:
                raise ValueError("No sprints in sprint_plan")

            saved_sprints = []
            saved_backlog_items = []

            # Map sprint_id (from PO Agent) to database ID
            sprint_id_map = {}

            # Save each sprint
            for sprint_data in sprints_data:
                print(f"\n[Sprint] Saving {sprint_data.get('sprint_id')}...")

                # Create Sprint object
                sprint = Sprint(
                    project_id=project_id,
                    name=sprint_data.get("sprint_goal", f"Sprint {sprint_data.get('sprint_number')}"),
                    number=sprint_data.get("sprint_number", 1),
                    goal=sprint_data.get("sprint_goal", ""),
                    status=sprint_data.get("status", "Planned"),
                    start_date=datetime.fromisoformat(sprint_data["start_date"]) if sprint_data.get("start_date") else datetime.now(),
                    end_date=datetime.fromisoformat(sprint_data["end_date"]) if sprint_data.get("end_date") else datetime.now(),
                    velocity_plan=str(sprint_data.get("velocity_plan", 0)),
                    velocity_actual=str(sprint_data.get("velocity_actual", 0))
                )

                # Map sprint_id to database ID
                sprint_id_map[sprint_data.get("sprint_id")] = sprint

                session.add(sprint)
                session.flush()  # Get the ID without committing

                print(f"   ✓ Sprint saved with ID: {sprint.id}")
                saved_sprints.append({
                    "id": str(sprint.id),
                    "sprint_id": sprint_data.get("sprint_id"),
                    "name": sprint.name,
                    "number": sprint.number
                })

            # Now save backlog items (after all sprints are created)
            print(f"\n[3/3] Saving backlog items...")
            # Map item_id (from PO Agent) to database ID
            item_id_map = {}

            for sprint_data in sprints_data:
                assigned_items = sprint_data.get("assigned_items", [])
                sprint_db_obj = sprint_id_map[sprint_data.get("sprint_id")]

                for item_data in backlog_items:
                    if item_data.get("id") in assigned_items:
                        print(f"   [Item] Saving {item_data.get('id')}...")

                        # Resolve parent_id if exists
                        parent_id = None
                        if item_data.get("parent_id"):
                            parent_id = item_id_map.get(item_data.get("parent_id"))

                        backlog_item = BacklogItem(
                            sprint_id=sprint_db_obj.id,
                            parent_id=parent_id,
                            type=item_data.get("type", "Task"),
                            title=item_data.get("title", ""),
                            description=item_data.get("description", ""),
                            status=item_data.get("status", "Backlog"),
                            reviewer_id=None,
                            assignee_id=None,
                            rank=item_data.get("rank"),
                            estimate_value=item_data.get("estimate_value"),
                            story_point=item_data.get("story_point"),
                            pause=False,
                            deadline=None
                        )

                        session.add(backlog_item)
                        session.flush()

                        # Map item_id to database ID
                        item_id_map[item_data.get("id")] = backlog_item.id

                        print(f"      ✓ Item saved with ID: {backlog_item.id}")
                        saved_backlog_items.append({
                            "id": str(backlog_item.id),
                            "item_id": item_data.get("id"),
                            "title": backlog_item.title,
                            "sprint_id": str(sprint_db_obj.id),
                            "status": backlog_item.status
                        })

            # Commit all changes
            session.commit()

            print(f"\n✅ Saved {len(saved_sprints)} sprints and {len(saved_backlog_items)} backlog items")
            print("=" * 80 + "\n")

            return {
                "sprints": saved_sprints,
                "backlog_items": saved_backlog_items,
                "total_sprints": len(saved_sprints),
                "total_items": len(saved_backlog_items)
            }

        except Exception as e:
            session.rollback()
            print(f"\n❌ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            raise

