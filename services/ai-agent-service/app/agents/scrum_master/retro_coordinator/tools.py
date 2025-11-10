"""Tools and utilities for Retro Coordinator Agent."""

from typing import List, Dict, Optional
from collections import defaultdict
from uuid import UUID
from sqlmodel import Session, select

# TraDS ============= New tools for Blocker & ProjectRules integration
def get_sprint_blockers(session: Session, sprint_id: UUID) -> List[Dict]:
    """Get all blockers for a sprint from database.

    Args:
        session: Database session
        sprint_id: Sprint UUID

    Returns:
        List of blockers with details
    """
    try:
        from ....models import Blocker, BacklogItem, User
        from ....crud import blocker as crud_blocker

        blockers = crud_blocker.get_blockers_by_sprint(session=session, sprint_id=sprint_id)

        result = []
        for blocker in blockers:
            # Get backlog item and user details
            backlog_item = session.get(BacklogItem, blocker.backlog_item_id)
            user = session.get(User, blocker.reported_by_user_id)

            result.append({
                "id": str(blocker.id),
                "type": blocker.blocker_type,
                "description": blocker.description,
                "backlog_item_title": backlog_item.title if backlog_item else "Unknown",
                "reported_by": user.full_name if user else "Unknown",
                "created_at": blocker.created_at.isoformat()
            })

        return result
    except Exception as e:
        print(f"Error getting blockers: {e}")
        return []


def get_sprint_metrics(session: Session, sprint_id: UUID) -> Dict:
    """Calculate sprint metrics from database.

    Args:
        session: Database session
        sprint_id: Sprint UUID

    Returns:
        Dict with sprint metrics
    """
    try:
        from ....models import BacklogItem, Sprint

        sprint = session.get(Sprint, sprint_id)
        if not sprint:
            return {}

        # Get all backlog items for sprint
        statement = select(BacklogItem).where(BacklogItem.sprint_id == sprint_id)
        items = list(session.exec(statement).all())

        total_points = sum(item.story_point or 0 for item in items)
        completed_items = [item for item in items if item.status == "Done"]
        completed_points = sum(item.story_point or 0 for item in completed_items)

        return {
            "total_tasks": len(items),
            "completed_tasks": len(completed_items),
            "total_points": total_points,
            "completed_points": completed_points,
            "velocity": completed_points,
            "completion_rate": round(len(completed_items) / len(items) * 100) if items else 0
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {}


def update_project_rules(session: Session, project_id: UUID, po_prompt: str, dev_prompt: str, tester_prompt: str) -> bool:
    """Update or create project rules in database.

    Args:
        session: Database session
        project_id: Project UUID
        po_prompt: Rules for Product Owner
        dev_prompt: Rules for Developer
        tester_prompt: Rules for Tester

    Returns:
        True if successful
    """
    try:
        from ....crud import project_rules as crud_rules
        from ....schemas import ProjectRulesCreate, ProjectRulesUpdate

        # Check if rules exist
        existing_rules = crud_rules.get_project_rules(session=session, project_id=project_id)

        if existing_rules:
            # Update existing rules
            rules_update = ProjectRulesUpdate(
                po_prompt=po_prompt,
                dev_prompt=dev_prompt,
                tester_prompt=tester_prompt
            )
            crud_rules.update_project_rules(
                session=session,
                db_rules=existing_rules,
                rules_in=rules_update
            )
        else:
            # Create new rules
            rules_create = ProjectRulesCreate(
                project_id=project_id,
                po_prompt=po_prompt,
                dev_prompt=dev_prompt,
                tester_prompt=tester_prompt
            )
            crud_rules.create_project_rules(session=session, rules_in=rules_create)

        return True
    except Exception as e:
        print(f"Error updating project rules: {e}")
        return False
# ==============================


def categorize_feedback(all_feedback: List[Dict]) -> List[Dict]:
    """Categorize feedback into issues.

    Args:
        all_feedback: List of feedback items

    Returns:
        List of categorized issues
    """
    print("\n" + "="*80)
    print("📊 CATEGORIZING FEEDBACK INTO ISSUES")
    print("="*80)

    # Group feedback by category and content
    issue_map = defaultdict(lambda: {
        "frequency": 0,
        "sources": set(),
        "severity": "low"
    })

    for feedback in all_feedback:
        key = f"{feedback.get('category')}_{feedback.get('content')[:50]}"
        issue_map[key]["frequency"] += 1
        issue_map[key]["sources"].add(feedback.get("source_name"))
        issue_map[key]["category"] = feedback.get("category")
        issue_map[key]["content"] = feedback.get("content")
        issue_map[key]["source"] = feedback.get("source")

        # Determine severity based on frequency and priority
        if feedback.get("priority") == "high" or issue_map[key]["frequency"] >= 2:
            issue_map[key]["severity"] = "high"
        elif feedback.get("priority") == "medium":
            issue_map[key]["severity"] = "medium"

    # Convert to list
    issues = []
    for idx, (key, data) in enumerate(issue_map.items(), 1):
        issue = {
            "id": f"ISSUE-{idx:03d}",
            "category": data.get("category"),
            "description": data.get("content"),
            "frequency": data.get("frequency"),
            "severity": data.get("severity"),
            "sources": list(data.get("sources", [])),
            "impact": None
        }
        issues.append(issue)

    print(f"\n✅ Categorized {len(issues)} unique issues")
    for issue in issues:
        print(f"   - {issue['id']}: {issue['description'][:60]} (Severity: {issue['severity']})")

    print("="*80 + "\n")
    return issues


# DEPRECATED: These functions are no longer used.
# The retro_coordinator now uses LLM structured output with Pydantic models.
# See schemas.py for the new approach.
#
# def generate_improvement_ideas(issues: List[Dict]) -> List[Dict]:
#     """Generate improvement ideas from issues.
#
#     Args:
#         issues: List of categorized issues
#
#     Returns:
#         List of improvement ideas
#     """
#     print("\n" + "="*80)
#     print("💡 GENERATING IMPROVEMENT IDEAS")
#     print("="*80)
#
#     ideas = []
#
#     # Generate ideas based on issue categories
#     for idx, issue in enumerate(issues, 1):
#         category = issue.get("category", "")
#         description = issue.get("description", "")
#
#         # Create improvement idea
#         idea = {
#             "id": f"IDEA-{idx:03d}",
#             "title": f"Improve {category.replace('_', ' ')}",
#             "description": f"Address issue: {description}",
#             "related_issues": [issue.get("id")],
#             "expected_benefit": "Increase team productivity and satisfaction",
#             "effort_estimate": "medium" if issue.get("severity") == "high" else "low",
#             "priority": "high" if issue.get("severity") == "high" else "medium"
#         }
#         ideas.append(idea)
#
#     print(f"\n✅ Generated {len(ideas)} improvement ideas")
#     for idea in ideas:
#         print(f"   - {idea['id']}: {idea['title']} (Priority: {idea['priority']})")
#
#     print("="*80 + "\n")
#     return ideas
#
#
# def define_action_items(improvement_ideas: List[Dict], sprint_name: str) -> List[Dict]:
#     """Define action items for next sprint.
#
#     Args:
#         improvement_ideas: List of improvement ideas
#         sprint_name: Name of next sprint
#
#     Returns:
#         List of action items
#     """
#     print("\n" + "="*80)
#     print("✅ DEFINING ACTION ITEMS FOR NEXT SPRINT")
#     print("="*80)
#
#     action_items = []
#
#     for idx, idea in enumerate(improvement_ideas, 1):
#         action_item = {
#             "id": f"ACTION-{idx:03d}",
#             "title": idea.get("title"),
#             "description": idea.get("description"),
#             "owner": "Scrum Master",  # Default owner
#             "due_date": f"End of {sprint_name}",
#             "priority": idea.get("priority"),
#             "related_improvement": idea.get("id"),
#             "status": "pending"
#         }
#         action_items.append(action_item)
#
#     print(f"\n✅ Defined {len(action_items)} action items")
#     for item in action_items:
#         print(f"   - {item['id']}: {item['title']} (Owner: {item['owner']})")
#
#     print("="*80 + "\n")
#     return action_items


def aggregate_all_feedback(po_feedback: Optional[dict], dev_feedback: Optional[dict], 
                          tester_feedback: Optional[dict]) -> List[Dict]:
    """Aggregate feedback from all sources.

    Args:
        po_feedback: Product Owner feedback
        dev_feedback: Developer feedback
        tester_feedback: Tester feedback

    Returns:
        List of all feedback items
    """
    print("\n" + "="*80)
    print("📋 AGGREGATING FEEDBACK FROM ALL SOURCES")
    print("="*80)

    all_feedback = []

    # Process PO feedback
    if po_feedback and po_feedback.get("feedback"):
        for item in po_feedback.get("feedback", []):
            feedback = {
                "source": "po",
                "source_name": po_feedback.get("po_name", "Product Owner"),
                "category": item.get("category", "improvement"),
                "content": item.get("content", ""),
                "priority": item.get("priority", "medium"),
                "impact": item.get("impact")
            }
            all_feedback.append(feedback)

    # Process Dev feedback
    if dev_feedback and dev_feedback.get("feedback"):
        for item in dev_feedback.get("feedback", []):
            feedback = {
                "source": "developer",
                "source_name": item.get("developer_name", "Developer"),
                "category": item.get("category", "improvement"),
                "content": item.get("content", ""),
                "priority": item.get("priority", "medium"),
                "impact": item.get("impact")
            }
            all_feedback.append(feedback)

    # Process Tester feedback
    if tester_feedback and tester_feedback.get("feedback"):
        for item in tester_feedback.get("feedback", []):
            feedback = {
                "source": "tester",
                "source_name": item.get("tester_name", "Tester"),
                "category": item.get("category", "improvement"),
                "content": item.get("content", ""),
                "priority": item.get("priority", "medium"),
                "impact": item.get("impact")
            }
            all_feedback.append(feedback)

    print(f"\n✅ Aggregated {len(all_feedback)} feedback items")
    print(f"   - From PO: {len([f for f in all_feedback if f['source'] == 'po'])}")
    print(f"   - From Developers: {len([f for f in all_feedback if f['source'] == 'developer'])}")
    print(f"   - From Testers: {len([f for f in all_feedback if f['source'] == 'tester'])}")

    print("="*80 + "\n")
    return all_feedback

