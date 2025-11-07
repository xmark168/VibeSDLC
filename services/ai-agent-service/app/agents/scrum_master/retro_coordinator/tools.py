"""Tools and utilities for Retro Coordinator Agent."""

from typing import List, Dict, Optional
from collections import defaultdict


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

