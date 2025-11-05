"""Task Receiver Agent - Receives and processes task assignments from Scrum Master."""

from typing import Optional
from pydantic import BaseModel, Field


class DeveloperAssignment(BaseModel):
    """Model for developer assignment."""
    item_id: str = Field(description="ID of backlog item")
    developer_id: str = Field(description="ID of assigned developer")
    developer_name: str = Field(description="Name of assigned developer")
    task_title: str = Field(description="Task title")
    estimated_hours: float = Field(description="Estimated hours to complete")
    priority: str = Field(description="Priority: high, medium, low")
    status: str = Field(default="pending", description="Status: pending, in_progress, done")


class TaskReceiverAgent:
    """Task Receiver Agent - Receives task assignments from Scrum Master.
    
    This agent acts as an interface between Scrum Master and Developer Agent.
    It receives tasks, validates them, and prepares them for execution.
    """

    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None, project_id: str = "project-001"):
        """Initialize Task Receiver Agent.

        Args:
            session_id: Session ID (optional)
            user_id: User ID (optional)
            project_id: Project ID for Knowledge Base queries (default: project-001)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.project_id = project_id
        # Single developer representing the entire development team
        self.developers = [
            {"id": "dev-001", "name": "Development Team", "capacity": 40, "assigned_hours": 0},
        ]

    def get_relevant_rules(self, task_tags: list[str], limit: int = 10) -> list[dict]:
        """Query Knowledge Base for relevant development rules.

        Args:
            task_tags: Tags from the task (e.g., ["api", "testing", "security"])
            limit: Max number of rules to retrieve (default: 10)

        Returns:
            List of relevant rules from Knowledge Base
        """
        try:
            # Try relative import first
            try:
                from ...services.rule_service import RuleService
            except ImportError:
                # Fallback for direct script execution
                import sys
                from pathlib import Path
                app_path = Path(__file__).parent.parent.parent.parent
                sys.path.insert(0, str(app_path))
                from services.rule_service import RuleService

            rules = RuleService.get_project_rules(
                project_id=self.project_id,
                tags=task_tags if task_tags else None,
                category="technical",
                limit=limit
            )

            return [r.model_dump() for r in rules]
        except Exception as e:
            print(f"⚠️  Warning: Failed to query Knowledge Base: {e}")
            return []

    def assign_all_tasks(self, enriched_items: list[dict], project_rules: Optional[list[dict]] = None) -> dict:
        """Receive ALL development tasks from Scrum Master.

        This method receives all tasks assigned to the development team.
        Tasks are validated and prepared for Developer Agent execution.

        Args:
            enriched_items: List of enriched backlog items from Scrum Master
            project_rules: Optional list of project rules from knowledge base.
                          If None, will query Knowledge Base automatically.

        Returns:
            dict: Assignment results with all tasks assigned to developer team
        """
        print("\n" + "="*80)
        print("📥 TASK RECEIVER - RECEIVE TASKS FROM SCRUM MASTER")
        print("="*80)

        # Auto-query Knowledge Base if rules not provided
        if project_rules is None:
            print("\n🔍 Querying Knowledge Base for relevant rules...")

            # Extract all tags from items
            all_tags = set()
            for item in enriched_items:
                all_tags.update(item.get("labels", []))

            # Query KB
            project_rules = self.get_relevant_rules(list(all_tags), limit=20)

            if project_rules:
                print(f"✅ Retrieved {len(project_rules)} rules from Knowledge Base")
            else:
                print("ℹ️  No relevant rules found in Knowledge Base")

        # Display applicable rules
        if project_rules:
            print(f"\n📚 Applicable Project Rules: {len(project_rules)}")
            for rule in project_rules[:5]:  # Show top 5
                print(f"   • {rule['title']} ({rule['severity']})")
                print(f"     Tags: {', '.join(rule['tags'][:3])}")
                print(f"     💡 {rule['description'][:80]}...")
        else:
            print("\nℹ️  No project rules available")

        assignments = []

        # Filter only development-related items
        dev_items = [
            item for item in enriched_items
            if item.get("type") in ["User Story", "Task", "Sub-task"]
            and "test" not in (item.get("task_type") or "").lower()
        ]

        print(f"\n📋 Received {len(dev_items)} development tasks from Scrum Master")
        print(f"📌 Assigning all tasks to: Development Team")

        total_estimated_hours = 0

        for item in dev_items:
            # Calculate estimated hours from story points
            story_point = item.get("story_point", 5)
            estimated_hours = story_point * 2  # 1 story point = ~2 hours

            # Determine priority
            business_value = item.get("business_value", "Medium")
            priority_map = {"High": "high", "Medium": "medium", "Low": "low"}
            priority = priority_map.get(business_value, "medium")

            # Find relevant rules for this task
            item_tags = item.get("labels", [])
            relevant_rules = []
            if project_rules and item_tags:
                relevant_rules = [
                    r for r in project_rules
                    if any(tag in r.get("tags", []) for tag in item_tags)
                ]

            # Assign to generic developer team (no specific developer)
            assignment = DeveloperAssignment(
                item_id=item.get("id"),
                developer_id="dev-team",
                developer_name="Development Team",
                task_title=item.get("title"),
                estimated_hours=estimated_hours,
                priority=priority,
                status="pending"
            )
            assignments.append(assignment)
            total_estimated_hours += estimated_hours

            print(f"   ✅ {item.get('id')}: {item.get('title')[:50]}")
            print(f"      → Estimated: {estimated_hours} hours")
            if relevant_rules:
                print(f"      → Relevant Rules: {len(relevant_rules)} rules to follow")

        print(f"\n📊 Summary:")
        print(f"   Total Tasks Received: {len(assignments)}")
        print(f"   Total Estimated Hours: {total_estimated_hours} hours")
        print(f"   Rules Applied: {len(project_rules or [])} rules")
        print("="*80 + "\n")

        return {
            "assignments": [a.model_dump() for a in assignments],
            "total_assigned": len(assignments),
            "total_estimated_hours": total_estimated_hours,
            "rules_applied": len(project_rules or [])
        }

