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

            # Debug: Print what we received
            print(f"\n[DEBUG] Sprint plan structure:")
            print(f"   - prioritized_backlog: {len(backlog_items)} items")
            print(f"   - unassigned_items: {len(sprint_plan.get('unassigned_items', []))} items")
            print(f"   - Total items in input: {len(backlog_items) + len(sprint_plan.get('unassigned_items', []))}")

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

            # First pass: Save parent items (items without parent_id or type != Sub-task)
            # This ensures parent items exist before we try to link sub-tasks
            for sprint_data in sprints_data:
                assigned_items = sprint_data.get("assigned_items", [])
                sprint_db_obj = sprint_id_map[sprint_data.get("sprint_id")]

                for item_data in backlog_items:
                    item_id = item_data.get("id")

                    # Only process items assigned to this sprint
                    if item_id not in assigned_items:
                        continue

                    # Skip sub-tasks in first pass (they have parent_id)
                    if item_data.get("parent_id"):
                        continue

                    # Skip if already saved
                    if item_id in item_id_map:
                        continue

                    item_type = item_data.get("type", "Task")
                    print(f"   [Parent Item] Saving {item_id} (type={item_type})...")

                    backlog_item = BacklogItem(
                        sprint_id=sprint_db_obj.id,
                        parent_id=None,  # No parent for parent items
                        type=item_type,
                        title=item_data.get("title", ""),
                        description=item_data.get("description", ""),
                        status="Todo",
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
                    item_id_map[item_id] = backlog_item.id

                    print(f"      ✓ Parent item saved with ID: {backlog_item.id}")
                    saved_backlog_items.append({
                        "id": str(backlog_item.id),
                        "item_id": item_id,
                        "title": backlog_item.title,
                        "sprint_id": str(sprint_db_obj.id),
                        "status": backlog_item.status,
                        "type": backlog_item.type
                    })

            # Second pass: Save sub-tasks (items with parent_id)
            # Now parent items are in item_id_map, so we can link correctly
            print(f"\n   [Second Pass] Saving sub-tasks...")
            for sprint_data in sprints_data:
                assigned_items = sprint_data.get("assigned_items", [])
                sprint_db_obj = sprint_id_map[sprint_data.get("sprint_id")]

                for item_data in backlog_items:
                    item_id = item_data.get("id")

                    # Only process items assigned to this sprint
                    if item_id not in assigned_items:
                        continue

                    # Only process sub-tasks in second pass (they have parent_id)
                    if not item_data.get("parent_id"):
                        continue

                    # Skip if already saved
                    if item_id in item_id_map:
                        continue

                    # Resolve parent_id from map
                    parent_agent_id = item_data.get("parent_id")
                    parent_db_id = item_id_map.get(parent_agent_id)

                    if not parent_db_id:
                        print(f"      ⚠️ Warning: Parent {parent_agent_id} not found in map, skipping sub-task {item_id}")
                        continue

                    item_type = item_data.get("type", "Sub-task")
                    print(f"   [Child Item] Saving {item_id} (type={item_type}, parent={parent_agent_id})...")

                    backlog_item = BacklogItem(
                        sprint_id=sprint_db_obj.id,
                        parent_id=parent_db_id,  # Link to parent
                        type=item_type,
                        title=item_data.get("title", ""),
                        description=item_data.get("description", ""),
                        status="Todo",
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
                    item_id_map[item_id] = backlog_item.id

                    print(f"      ✓ Sub-task saved with ID: {backlog_item.id}, parent_id: {parent_db_id}")
                    saved_backlog_items.append({
                        "id": str(backlog_item.id),
                        "item_id": item_id,
                        "title": backlog_item.title,
                        "sprint_id": str(sprint_db_obj.id),
                        "status": backlog_item.status,
                        "type": backlog_item.type,
                        "parent_id": str(parent_db_id)
                    })

            # Third pass: Save unassigned items (child items only - they should inherit parent's sprint)
            unassigned_items = sprint_plan.get("unassigned_items", [])
            if unassigned_items:
                print(f"\n   [Third Pass] Saving {len(unassigned_items)} unassigned items (mostly Sub-tasks)...")

                # Save child items (with parent_id) - they inherit parent's sprint
                for item_data in unassigned_items:
                    item_id = item_data.get("id")

                    # Skip if already saved
                    if item_id in item_id_map:
                        continue

                    # Only process child items (items with parent_id)
                    parent_agent_id = item_data.get("parent_id")
                    if not parent_agent_id:
                        # Parent items without assignment - this shouldn't happen
                        print(f"      ⚠️ Warning: Unassigned parent item {item_id} - skipping (should be assigned to a sprint)")
                        continue

                    parent_db_id = item_id_map.get(parent_agent_id)
                    if not parent_db_id:
                        print(f"      ⚠️ Warning: Parent {parent_agent_id} not found for unassigned item {item_id}")
                        continue

                    # Get parent item from database to find its sprint_id
                    parent_item = session.get(BacklogItem, parent_db_id)
                    if not parent_item:
                        print(f"      ⚠️ Warning: Parent item {parent_db_id} not found in database for {item_id}")
                        continue

                    # Use parent's sprint_id - child inherits parent's sprint
                    target_sprint_id = parent_item.sprint_id

                    item_type = item_data.get("type", "Sub-task")
                    print(f"      [Child Item] Saving {item_id} (type={item_type}, parent={parent_agent_id}, sprint=inherited from parent)...")

                    backlog_item = BacklogItem(
                        sprint_id=target_sprint_id,  # ← Inherit parent's sprint!
                        parent_id=parent_db_id,
                        type=item_type,
                        title=item_data.get("title", ""),
                        description=item_data.get("description", ""),
                        status="Todo",
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

                    item_id_map[item_id] = backlog_item.id

                    print(f"         ✓ Saved with ID: {backlog_item.id}, parent_id: {parent_db_id}, sprint_id: {target_sprint_id}")
                    saved_backlog_items.append({
                        "id": str(backlog_item.id),
                        "item_id": item_id,
                        "title": backlog_item.title,
                        "sprint_id": str(target_sprint_id),
                        "status": backlog_item.status,
                        "type": backlog_item.type,
                        "parent_id": str(parent_db_id)
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

    @staticmethod
    def save_product_backlog(
        session: Session,
        project_id: UUID,
        backlog_items: list[dict]
    ) -> dict:
        """Save product backlog items to database (unassigned to sprints).

        Args:
            session: Database session
            project_id: Project ID
            backlog_items: Backlog items data từ PO Agent

        Returns:
            dict: Saved data with database IDs
        """
        print("\n" + "=" * 80)
        print("💾 PRODUCT BACKLOG PERSISTENCE - Saving to Database")
        print("=" * 80)
        print(f"   Project ID: {project_id}")
        print(f"   Backlog Items: {len(backlog_items)}")
        print("=" * 80 + "\n")

        try:
            # Validate project exists
            print(f"[1/2] Validating project {project_id}...")
            project = session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            print(f"   ✓ Project found: {project.name}")

            saved_backlog_items = []
            # Map item_id (from PO Agent) to database ID
            item_id_map = {}

            print(f"\n[2/2] Saving backlog items (unassigned)...")

            for item_data in backlog_items:
                print(f"   [Item] Saving {item_data.get('id')}...")

                # Resolve parent_id if exists
                parent_id = None
                if item_data.get("parent_id"):
                    parent_id = item_id_map.get(item_data.get("parent_id"))

                # Create a placeholder sprint for unassigned items
                # We can create a "Backlog" sprint that holds unassigned items
                placeholder_sprint_name = "Backlog"
                placeholder_sprint = session.exec(
                    select(Sprint)
                    .where(Sprint.project_id == project_id)
                    .where(Sprint.name == placeholder_sprint_name)
                    .where(Sprint.status == "Backlog")
                ).first()

                if not placeholder_sprint:
                    placeholder_sprint = Sprint(
                        project_id=project_id,
                        name=placeholder_sprint_name,
                        number=0,
                        goal="Unassigned backlog items",
                        status="Backlog",
                        start_date=datetime.now(),
                        end_date=datetime.now(),
                        velocity_plan="0",
                        velocity_actual="0"
                    )
                    session.add(placeholder_sprint)
                    session.flush()
                    print(f"   ✓ Created placeholder 'Backlog' sprint with ID: {placeholder_sprint.id}")

                backlog_item = BacklogItem(
                    sprint_id=placeholder_sprint.id,
                    parent_id=parent_id,
                    type=item_data.get("type", "Task"),
                    title=item_data.get("title", ""),
                    description=item_data.get("description", ""),
                    status="Todo",
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
                    "sprint_id": str(placeholder_sprint.id),
                    "status": backlog_item.status
                })

            # Commit all changes
            session.commit()

            print(f"\n✅ Saved {len(saved_backlog_items)} backlog items to database")
            print("=" * 80 + "\n")

            return {
                "backlog_items": saved_backlog_items,
                "total_items": len(saved_backlog_items)
            }

        except Exception as e:
            session.rollback()
            print(f"\n❌ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            raise

