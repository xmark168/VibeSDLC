"""Tester Agent - Handles testing tasks with Knowledge Base integration."""

from typing import Optional
from pydantic import BaseModel, Field


class TesterAssignment(BaseModel):
    """Model for tester assignment."""
    item_id: str = Field(description="ID of backlog item")
    tester_id: str = Field(description="ID of assigned tester")
    tester_name: str = Field(description="Name of assigned tester")
    task_title: str = Field(description="Task title")
    test_type: str = Field(description="Type of testing: unit, integration, e2e, manual")
    estimated_hours: float = Field(description="Estimated hours to complete")
    priority: str = Field(description="Priority: high, medium, low")
    status: str = Field(default="pending", description="Status: pending, in_progress, done")


class TesterAgent:
    """Tester Agent with direct Knowledge Base access."""

    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None, project_id: str = "project-001"):
        """Initialize Tester Agent.

        Args:
            session_id: Session ID (optional)
            user_id: User ID (optional)
            project_id: Project ID for Knowledge Base queries (default: project-001)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.project_id = project_id
        # Single tester representing the entire testing team
        self.testers = [
            {"id": "qa-001", "name": "Testing Team", "capacity": 40, "assigned_hours": 0},
        ]

    def get_relevant_rules(self, task_tags: list[str], limit: int = 10) -> list[dict]:
        """Query Knowledge Base for relevant testing/quality rules.

        Args:
            task_tags: Tags from the task (e.g., ["testing", "quality", "e2e"])
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
                category="quality",  # Focus on quality/testing rules
                limit=limit
            )

            return [r.model_dump() for r in rules]
        except Exception as e:
            print(f"⚠️  Warning: Failed to query Knowledge Base: {e}")
            return []

    def assign_test_tasks(self, enriched_items: list[dict]) -> dict:
        """Assign test tasks to testers using round-robin.

        Args:
            enriched_items: List of enriched backlog items

        Returns:
            dict: Assignment results with assignments and updated items
        """
        print("\n" + "="*80)
        print("🧪 TESTER AGENT - ASSIGN TEST TASKS TO TESTERS")
        print("="*80)

        assignments = []
        tester_index = 0

        # Filter only test-related items or all items that need testing
        test_items = [
            item for item in enriched_items
            if item.get("type") in ["User Story", "Task", "Sub-task"]
        ]

        print(f"\n📋 Found {len(test_items)} items to test")

        for item in test_items:
            # Round-robin assignment
            tester = self.testers[tester_index % len(self.testers)]
            tester_index += 1

            # Calculate estimated test hours (usually 30-50% of dev hours)
            story_point = item.get("story_point", 5)
            dev_hours = story_point * 2
            estimated_hours = dev_hours * 0.4  # 40% of dev time for testing

            # Determine priority
            business_value = item.get("business_value", "Medium")
            priority_map = {"High": "high", "Medium": "medium", "Low": "low"}
            priority = priority_map.get(business_value, "medium")

            # Determine test type based on item type
            test_type_map = {
                "Epic": "e2e",
                "User Story": "integration",
                "Task": "unit",
                "Sub-task": "unit"
            }
            test_type = test_type_map.get(item.get("type"), "manual")

            assignment = TesterAssignment(
                item_id=item.get("id"),
                tester_id=tester["id"],
                tester_name=tester["name"],
                task_title=item.get("title"),
                test_type=test_type,
                estimated_hours=estimated_hours,
                priority=priority,
                status="pending"
            )

            assignments.append(assignment)
            tester["assigned_hours"] += estimated_hours

            print(f"   ✅ {item.get('id')}: {item.get('title')[:50]}")
            print(f"      → Assigned to: {tester['name']}")
            print(f"      → Test Type: {test_type}")
            print(f"      → Estimated: {estimated_hours:.1f} hours")

        # Print tester workload
        print(f"\n📊 Tester Workload:")
        for tester in self.testers:
            utilization = (tester["assigned_hours"] / tester["capacity"]) * 100
            status = "✅" if utilization <= 100 else "⚠️"
            print(f"   {status} {tester['name']}: {tester['assigned_hours']:.1f}/{tester['capacity']} hours ({utilization:.0f}%)")

        print("="*80 + "\n")

        return {
            "assignments": [a.model_dump() for a in assignments],
            "total_assigned": len(assignments),
            "testers_workload": self.testers
        }

    def assign_all_test_tasks(self, enriched_items: list[dict], project_rules: Optional[list[dict]] = None) -> dict:
        """Assign ALL test tasks to a single tester team (simplified).

        This method assigns all test tasks to a generic tester team without
        distributing to individual testers. Useful for simplified workflows.

        Args:
            enriched_items: List of enriched backlog items
            project_rules: Optional list of project rules from knowledge base.
                          If None, will query Knowledge Base automatically.

        Returns:
            dict: Assignment results with all test tasks assigned to tester team
        """
        print("\n" + "="*80)
        print("🧪 TESTER AGENT - ASSIGN ALL TEST TASKS TO TESTING TEAM")
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

        # Filter only test-related items or all items that need testing
        test_items = [
            item for item in enriched_items
            if item.get("type") in ["User Story", "Task", "Sub-task"]
        ]

        print(f"\n📋 Found {len(test_items)} items to test")
        print(f"📌 Assigning all test tasks to: Testing Team")

        total_estimated_hours = 0

        for item in test_items:
            # Calculate estimated test hours (usually 30-50% of dev hours)
            story_point = item.get("story_point", 5)
            dev_hours = story_point * 2
            estimated_hours = dev_hours * 0.4  # 40% of dev time for testing

            # Determine priority
            business_value = item.get("business_value", "Medium")
            priority_map = {"High": "high", "Medium": "medium", "Low": "low"}
            priority = priority_map.get(business_value, "medium")

            # Determine test type based on item type
            test_type_map = {
                "Epic": "e2e",
                "User Story": "integration",
                "Task": "unit",
                "Sub-task": "unit"
            }
            test_type = test_type_map.get(item.get("type"), "manual")

            # Find relevant rules for this task
            item_tags = item.get("labels", [])
            relevant_rules = []
            if project_rules and item_tags:
                relevant_rules = [
                    r for r in project_rules
                    if any(tag in r.get("tags", []) for tag in item_tags)
                ]

            # Assign to generic tester team (no specific tester)
            assignment = TesterAssignment(
                item_id=item.get("id"),
                tester_id="qa-team",
                tester_name="Testing Team",
                task_title=item.get("title"),
                test_type=test_type,
                estimated_hours=estimated_hours,
                priority=priority,
                status="pending"
            )
            assignments.append(assignment)
            total_estimated_hours += estimated_hours

            print(f"   ✅ {item.get('id')}: {item.get('title')[:50]}")
            print(f"      → Test Type: {test_type}")
            print(f"      → Estimated: {estimated_hours:.1f} hours")
            if relevant_rules:
                print(f"      → Relevant Rules: {len(relevant_rules)} rules to follow")

        print(f"\n📊 Summary:")
        print(f"   Total Test Tasks: {len(assignments)}")
        print(f"   Total Estimated Hours: {total_estimated_hours:.1f} hours")
        print(f"   Rules Applied: {len(project_rules or [])} rules")
        print("="*80 + "\n")

        return {
            "assignments": [a.model_dump() for a in assignments],
            "total_assigned": len(assignments),
            "total_estimated_hours": total_estimated_hours,
            "rules_applied": len(project_rules or [])
        }

    def get_daily_reports(self) -> dict:
        """Get daily test reports from all testers.

        Returns:
            dict: Daily reports with test status, bugs found, and blockers
        """
        print("\n" + "="*80)
        print("📊 TESTER AGENT - GET DAILY REPORTS")
        print("="*80)

        reports = []

        for tester in self.testers:
            # Mock data - in real scenario, this would query actual test status
            report = {
                "tester_id": tester["id"],
                "tester_name": tester["name"],
                "date": "2024-01-15",  # Mock date
                "tests_completed_yesterday": [
                    {"id": f"TEST-{tester['id']}-001", "title": "Login functionality tests", "status": "passed"},
                    {"id": f"TEST-{tester['id']}-002", "title": "User registration tests", "status": "passed"}
                ],
                "tests_in_progress": [
                    {"id": f"TEST-{tester['id']}-003", "title": "Password reset feature tests", "status": "in_progress", "progress": 50}
                ],
                "tests_planned_today": [
                    {"id": f"TEST-{tester['id']}-003", "title": "Complete password reset tests", "estimated_hours": 3},
                    {"id": f"TEST-{tester['id']}-004", "title": "Integration tests", "estimated_hours": 2}
                ],
                "bugs_found": [
                    {"id": f"BUG-{tester['id']}-001", "title": "Login button not responsive on mobile", "severity": "high"},
                    {"id": f"BUG-{tester['id']}-002", "title": "Error message not displayed correctly", "severity": "medium"}
                ],
                "blockers": [
                    {"type": "dependency", "description": "Waiting for backend API deployment", "severity": "high"},
                ],
                "test_coverage": 85.0,
                "hours_worked_yesterday": 8,
                "estimated_hours_today": 5,
                "capacity_utilization": (tester["assigned_hours"] / tester["capacity"]) * 100 if tester["capacity"] > 0 else 0
            }
            reports.append(report)

            print(f"\n🧪 {tester['name']} ({tester['id']}):")
            print(f"   ✅ Completed: {len(report['tests_completed_yesterday'])} tests")
            print(f"   🔄 In Progress: {len(report['tests_in_progress'])} tests")
            print(f"   📋 Planned Today: {len(report['tests_planned_today'])} tests")
            print(f"   🐛 Bugs Found: {len(report['bugs_found'])} bugs")
            print(f"   ⚠️  Blockers: {len(report['blockers'])} issues")

        print(f"\n📊 Summary:")
        print(f"   Total Testers: {len(reports)}")
        print(f"   Total Bugs Found: {sum(len(r['bugs_found']) for r in reports)}")
        print(f"   Total Blockers: {sum(len(r['blockers']) for r in reports)}")
        print("="*80 + "\n")

        return {
            "reports": reports,
            "total_testers": len(reports),
            "total_bugs": sum(len(r['bugs_found']) for r in reports),
            "total_blockers": sum(len(r['blockers']) for r in reports),
            "report_date": "2024-01-15"
        }

    def get_retrospective_feedback(self, sprint_id: Optional[str] = None) -> dict:
        """Get retrospective feedback from all testers about the sprint.

        Args:
            sprint_id: Sprint ID to get feedback for (optional)

        Returns:
            dict: Retrospective feedback with structure containing what went well,
                  what went wrong, and improvement suggestions
        """
        print("\n" + "="*80)
        print("💭 TESTER AGENT - GET RETROSPECTIVE FEEDBACK")
        print("="*80)

        feedback_items = []

        # Mock retrospective feedback from testing team
        feedback_templates = {
            "Testing Team": {
                "what_went_well": [
                    {
                        "category": "what_went_well",
                        "content": "Comprehensive test coverage caught critical bugs early",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Automated test suite reduced regression testing time",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Good collaboration with developers on bug fixes",
                        "priority": "medium",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_well",
                        "content": "Clear acceptance criteria made test planning easier",
                        "priority": "medium",
                        "impact": "positive"
                    }
                ],
                "what_went_wrong": [
                    {
                        "category": "what_went_wrong",
                        "content": "Test environment was unstable, causing delays",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Late delivery of features left insufficient time for testing",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Frequent API changes broke existing test cases",
                        "priority": "high",
                        "impact": "negative"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Lack of test data made some scenarios hard to verify",
                        "priority": "medium",
                        "impact": "negative"
                    }
                ],
                "improvement": [
                    {
                        "category": "improvement",
                        "content": "Need dedicated test environment with better stability",
                        "priority": "high",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Better API versioning to minimize test maintenance",
                        "priority": "high",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Implement continuous testing throughout sprint",
                        "priority": "medium",
                        "impact": None
                    },
                    {
                        "category": "improvement",
                        "content": "Create comprehensive test data management strategy",
                        "priority": "medium",
                        "impact": None
                    }
                ]
            }
        }

        for tester in self.testers:
            tester_name = tester["name"]
            tester_feedback = feedback_templates.get(tester_name, {})

            # Combine all feedback categories
            for category in ["what_went_well", "what_went_wrong", "improvement"]:
                for item in tester_feedback.get(category, []):
                    feedback_item = {
                        "tester_name": tester_name,
                        **item
                    }
                    feedback_items.append(feedback_item)

            # Print tester feedback summary
            print(f"\n🧪 {tester_name}:")
            print(f"   ✅ What Went Well: {len(tester_feedback.get('what_went_well', []))} items")
            print(f"   ❌ What Went Wrong: {len(tester_feedback.get('what_went_wrong', []))} items")
            print(f"   💡 Improvements: {len(tester_feedback.get('improvement', []))} items")

        print(f"\n📊 Summary:")
        print(f"   Total Testers: {len(self.testers)}")
        print(f"   Total Feedback Items: {len(feedback_items)}")
        print(f"   Sprint ID: {sprint_id or 'N/A'}")
        print("="*80 + "\n")

        return {
            "feedback": feedback_items,
            "total_testers": len(self.testers),
            "total_feedback_items": len(feedback_items),
            "sprint_id": sprint_id or "N/A"
        }

