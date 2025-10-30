"""Developer Agent - Handles development tasks with Knowledge Base integration."""

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


class DeveloperAgent:
    """Developer Agent with direct Knowledge Base access."""

    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None, project_id: str = "project-001"):
        """Initialize Developer Agent.

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
                app_path = Path(__file__).parent.parent.parent
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

    def assign_tasks(self, enriched_items: list[dict]) -> dict:
        """Assign development tasks to developers using round-robin.

        Args:
            enriched_items: List of enriched backlog items

        Returns:
            dict: Assignment results with assignments and updated items
        """
        print("\n" + "="*80)
        print("👨‍💻 DEVELOPER AGENT - ASSIGN TASKS TO DEVELOPERS")
        print("="*80)

        assignments = []
        dev_index = 0

        # Filter only development-related items
        dev_items = [
            item for item in enriched_items
            if item.get("type") in ["User Story", "Task", "Sub-task"]
            and "test" not in (item.get("task_type") or "").lower()
        ]

        print(f"\n📋 Found {len(dev_items)} development tasks to assign")

        for item in dev_items:
            # Round-robin assignment
            developer = self.developers[dev_index % len(self.developers)]
            dev_index += 1

            # Calculate estimated hours from story points
            story_point = item.get("story_point", 5)
            estimated_hours = story_point * 2  # 1 story point = ~2 hours

            # Determine priority
            business_value = item.get("business_value", "Medium")
            priority_map = {"High": "high", "Medium": "medium", "Low": "low"}
            priority = priority_map.get(business_value, "medium")

            assignment = DeveloperAssignment(
                item_id=item.get("id"),
                developer_id=developer["id"],
                developer_name=developer["name"],
                task_title=item.get("title"),
                estimated_hours=estimated_hours,
                priority=priority,
                status="pending"
            )

            assignments.append(assignment)
            developer["assigned_hours"] += estimated_hours

            print(f"   ✅ {item.get('id')}: {item.get('title')[:50]}")
            print(f"      → Assigned to: {developer['name']}")
            print(f"      → Estimated: {estimated_hours} hours")

        # Print developer workload
        print(f"\n📊 Developer Workload:")
        for dev in self.developers:
            utilization = (dev["assigned_hours"] / dev["capacity"]) * 100
            status = "✅" if utilization <= 100 else "⚠️"
            print(f"   {status} {dev['name']}: {dev['assigned_hours']}/{dev['capacity']} hours ({utilization:.0f}%)")

        print("="*80 + "\n")

        return {
            "assignments": [a.model_dump() for a in assignments],
            "total_assigned": len(assignments),
            "developers_workload": self.developers
        }

    def assign_all_tasks(self, enriched_items: list[dict], project_rules: Optional[list[dict]] = None) -> dict:
        """Assign ALL development tasks to a single developer team (simplified).

        This method assigns all tasks to a generic developer team without
        distributing to individual developers. Useful for simplified workflows.

        Args:
            enriched_items: List of enriched backlog items
            project_rules: Optional list of project rules from knowledge base.
                          If None, will query Knowledge Base automatically.

        Returns:
            dict: Assignment results with all tasks assigned to developer team
        """
        print("\n" + "="*80)
        print("👨‍💻 DEVELOPER AGENT - ASSIGN ALL TASKS TO DEVELOPMENT TEAM")
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

        print(f"\n📋 Found {len(dev_items)} development tasks to assign")
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
        print(f"   Total Tasks: {len(assignments)}")
        print(f"   Total Estimated Hours: {total_estimated_hours} hours")
        print(f"   Rules Applied: {len(project_rules or [])} rules")
        print("="*80 + "\n")

        return {
            "assignments": [a.model_dump() for a in assignments],
            "total_assigned": len(assignments),
            "total_estimated_hours": total_estimated_hours,
            "rules_applied": len(project_rules or [])
        }

    def get_daily_reports(self) -> dict:
        """Get daily progress reports from all developers.

        Returns:
            dict: Daily reports with progress, current tasks, and blockers
        """
        print("\n" + "="*80)
        print("📊 DEVELOPER AGENT - GET DAILY REPORTS")
        print("="*80)

        reports = []

        for dev in self.developers:
            # Mock data - in real scenario, this would query actual task status
            report = {
                "developer_id": dev["id"],
                "developer_name": dev["name"],
                "date": "2024-01-15",  # Mock date
                "tasks_completed_yesterday": [
                    {"id": f"TASK-{dev['id']}-001", "title": "Implement user authentication", "status": "done"},
                    {"id": f"TASK-{dev['id']}-002", "title": "Fix login bug", "status": "done"}
                ],
                "tasks_in_progress": [
                    {"id": f"TASK-{dev['id']}-003", "title": "Add password reset feature", "status": "in_progress", "progress": 60}
                ],
                "tasks_planned_today": [
                    {"id": f"TASK-{dev['id']}-003", "title": "Complete password reset feature", "estimated_hours": 4},
                    {"id": f"TASK-{dev['id']}-004", "title": "Write unit tests", "estimated_hours": 2}
                ],
                "blockers": [
                    {"type": "technical", "description": "Waiting for API documentation from backend team", "severity": "medium"},
                ],
                "hours_worked_yesterday": 8,
                "estimated_hours_today": 6,
                "capacity_utilization": (dev["assigned_hours"] / dev["capacity"]) * 100 if dev["capacity"] > 0 else 0
            }
            reports.append(report)

            print(f"\n👨‍💻 {dev['name']} ({dev['id']}):")
            print(f"   ✅ Completed: {len(report['tasks_completed_yesterday'])} tasks")
            print(f"   🔄 In Progress: {len(report['tasks_in_progress'])} tasks")
            print(f"   📋 Planned Today: {len(report['tasks_planned_today'])} tasks")
            print(f"   ⚠️  Blockers: {len(report['blockers'])} issues")

        print(f"\n📊 Summary:")
        print(f"   Total Developers: {len(reports)}")
        print(f"   Total Blockers: {sum(len(r['blockers']) for r in reports)}")
        print("="*80 + "\n")

        return {
            "reports": reports,
            "total_developers": len(reports),
            "total_blockers": sum(len(r['blockers']) for r in reports),
            "report_date": "2024-01-15"
        }

    def get_retrospective_feedback(self, sprint_id: Optional[str] = None) -> dict:
        """Get retrospective feedback from all developers about the sprint.

        Args:
            sprint_id: Sprint ID to get feedback for (optional)

        Returns:
            dict: Retrospective feedback with structure containing what went well,
                  what went wrong, and improvement suggestions
        """
        print("\n" + "="*80)
        print("💭 DEVELOPER AGENT - GET RETROSPECTIVE FEEDBACK")
        print("="*80)

        feedback_items = []

        # Mock retrospective feedback from development team
        feedback_templates = {
            "Development Team": {
                "what_went_well": [
                    {
                        "category": "what_went_well",
                        "content": "Great collaboration with the team, especially during code reviews",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Successfully implemented complex authentication features on time",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Effective pair programming sessions improved code quality",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Good sprint planning helped maintain steady velocity",
                        "priority": "medium",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Clear task breakdown made estimation more accurate",
                        "priority": "medium",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Daily standups kept everyone aligned on progress",
                        "priority": "medium",
                        "impact": "positive"
                    }
                ],
                "what_went_wrong": [
                    {
                        "category": "what_went_wrong",
                        "content": "Frequent API changes caused rework and delays",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Test environment instability blocked development",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Unclear requirements led to multiple iterations",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Insufficient documentation for third-party libraries",
                        "priority": "medium",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Late feedback from stakeholders required last-minute changes",
                        "priority": "medium",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Limited access to production logs hindered debugging",
                        "priority": "medium",
                        "impact": "negative"
                    }
                ],
                "improvement": [
                    {
                        "category": "improvement",
                        "content": "Need better API versioning and change management process",
                        "priority": "high",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Invest in more stable test infrastructure",
                        "priority": "high",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Implement requirement refinement sessions before sprint",
                        "priority": "high",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Should allocate time for technical documentation",
                        "priority": "medium",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Schedule regular stakeholder demos during sprint",
                        "priority": "medium",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Provide developers with read-only production access",
                        "priority": "medium",
                        "impact": None
                    }
                ]
            }
        }

        for dev in self.developers:
            dev_name = dev["name"]
            dev_feedback = feedback_templates.get(dev_name, {})

            # Combine all feedback categories
            for category in ["what_went_well", "what_went_wrong", "improvement"]:
                for item in dev_feedback.get(category, []):
                    feedback_item = {
                        "developer_name": dev_name,
                        **item
                    }
                    feedback_items.append(feedback_item)

            # Print developer feedback summary
            print(f"\n👨‍💻 {dev_name}:")
            print(f"   ✅ What Went Well: {len(dev_feedback.get('what_went_well', []))} items")
            print(f"   ❌ What Went Wrong: {len(dev_feedback.get('what_went_wrong', []))} items")
            print(f"   💡 Improvements: {len(dev_feedback.get('improvement', []))} items")

        print(f"\n📊 Summary:")
        print(f"   Total Developers: {len(self.developers)}")
        print(f"   Total Feedback Items: {len(feedback_items)}")
        print(f"   Sprint ID: {sprint_id or 'N/A'}")
        print("="*80 + "\n")

        return {
            "feedback": feedback_items,
            "total_developers": len(self.developers),
            "total_feedback_items": len(feedback_items),
            "sprint_id": sprint_id or "N/A"
        }

