"""Tools for Daily Coordinator Agent."""

from datetime import datetime


def aggregate_dev_and_tester_reports(dev_reports: dict, tester_reports: dict) -> dict:
    """Aggregate developer and tester reports into unified view.

    Args:
        dev_reports: Developer reports from DeveloperAgent
        tester_reports: Tester reports from TesterAgent

    Returns:
        dict: Aggregated reports with combined metrics
    """
    print("\n" + "="*80)
    print("📊 AGGREGATING REPORTS")
    print("="*80)

    dev_list = dev_reports.get("reports", [])
    tester_list = tester_reports.get("reports", [])

    # Calculate team metrics
    total_tasks_completed = sum(len(r.get("tasks_completed_yesterday", [])) for r in dev_list)
    total_tasks_in_progress = sum(len(r.get("tasks_in_progress", [])) for r in dev_list)
    total_tasks_planned = sum(len(r.get("tasks_planned_today", [])) for r in dev_list)

    total_tests_completed = sum(len(r.get("tests_completed_yesterday", [])) for r in tester_list)
    total_tests_in_progress = sum(len(r.get("tests_in_progress", [])) for r in tester_list)
    total_bugs = sum(len(r.get("bugs_found", [])) for r in tester_list)

    avg_test_coverage = sum(r.get("test_coverage", 0) for r in tester_list) / max(1, len(tester_list))

    aggregated = {
        "timestamp": datetime.now().isoformat(),
        "team_metrics": {
            "developers": {
                "count": len(dev_list),
                "tasks_completed_yesterday": total_tasks_completed,
                "tasks_in_progress": total_tasks_in_progress,
                "tasks_planned_today": total_tasks_planned,
                "total_blockers": dev_reports.get("total_blockers", 0),
            },
            "testers": {
                "count": len(tester_list),
                "tests_completed_yesterday": total_tests_completed,
                "tests_in_progress": total_tests_in_progress,
                "bugs_found": total_bugs,
                "avg_test_coverage": avg_test_coverage,
                "total_blockers": tester_reports.get("total_blockers", 0),
            }
        },
        "dev_reports": dev_list,
        "tester_reports": tester_list,
    }

    print(f"\n✅ Aggregated {len(dev_list)} developer reports")
    print(f"✅ Aggregated {len(tester_list)} tester reports")
    print(f"\n📈 Team Metrics:")
    print(f"   - Tasks Completed: {total_tasks_completed}")
    print(f"   - Tasks In Progress: {total_tasks_in_progress}")
    print(f"   - Tasks Planned: {total_tasks_planned}")
    print(f"   - Tests Completed: {total_tests_completed}")
    print(f"   - Bugs Found: {total_bugs}")
    print(f"   - Avg Test Coverage: {avg_test_coverage:.1f}%")

    print("="*80 + "\n")

    return aggregated


def detect_blockers_from_reports(aggregated_reports: dict) -> dict:
    """Detect and analyze blockers from aggregated reports.

    Args:
        aggregated_reports: Aggregated reports from both teams

    Returns:
        dict: Detected blockers with analysis
    """
    print("\n" + "="*80)
    print("🚨 DETECTING BLOCKERS")
    print("="*80)

    all_blockers = []
    blocker_summary = {
        "high": [],
        "medium": [],
        "low": []
    }

    # Extract blockers from dev reports
    for dev_report in aggregated_reports.get("dev_reports", []):
        for blocker in dev_report.get("blockers", []):
            blocker_with_owner = {
                **blocker,
                "owner": dev_report.get("developer_name"),
                "owner_type": "developer"
            }
            all_blockers.append(blocker_with_owner)
            severity = blocker.get("severity", "medium")
            blocker_summary[severity].append(blocker_with_owner)

    # Extract blockers from tester reports
    for tester_report in aggregated_reports.get("tester_reports", []):
        for blocker in tester_report.get("blockers", []):
            blocker_with_owner = {
                **blocker,
                "owner": tester_report.get("tester_name"),
                "owner_type": "tester"
            }
            all_blockers.append(blocker_with_owner)
            severity = blocker.get("severity", "medium")
            blocker_summary[severity].append(blocker_with_owner)

    print(f"\n🚨 Total Blockers Found: {len(all_blockers)}")
    print(f"   - High Severity: {len(blocker_summary['high'])}")
    print(f"   - Medium Severity: {len(blocker_summary['medium'])}")
    print(f"   - Low Severity: {len(blocker_summary['low'])}")

    for blocker in blocker_summary["high"]:
        print(f"\n   🔴 HIGH: {blocker.get('description')}")
        print(f"      Owner: {blocker.get('owner')} ({blocker.get('owner_type')})")

    print("="*80 + "\n")

    return {
        "all_blockers": all_blockers,
        "blocker_summary": blocker_summary,
        "total_blockers": len(all_blockers),
        "high_priority_count": len(blocker_summary["high"]),
        "medium_priority_count": len(blocker_summary["medium"]),
        "low_priority_count": len(blocker_summary["low"]),
    }
