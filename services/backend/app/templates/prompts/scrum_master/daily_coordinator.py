"""Prompts and messages for Daily Coordinator Agent."""

# ============================================================================
# UI MESSAGES - COLLECT DEV REPORTS
# ============================================================================

COLLECT_DEV_REPORTS_HEADER = """
================================================================================
👨‍💻 COLLECTING DEVELOPER REPORTS
================================================================================"""

COLLECT_DEV_REPORTS_SUCCESS = "\n✅ Collected reports from {total_developers} developers"

COLLECT_DEV_REPORTS_ERROR = "❌ {error}"

# ============================================================================
# UI MESSAGES - COLLECT TESTER REPORTS
# ============================================================================

COLLECT_TESTER_REPORTS_HEADER = """
================================================================================
🧪 COLLECTING TESTER REPORTS
================================================================================"""

COLLECT_TESTER_REPORTS_SUCCESS = "\n✅ Collected reports from {total_testers} testers"

COLLECT_TESTER_REPORTS_ERROR = "❌ {error}"

# ============================================================================
# UI MESSAGES - UPDATE TASK STATUS
# ============================================================================

UPDATE_TASK_STATUS_HEADER = """
================================================================================
📝 UPDATING TASK STATUS
================================================================================"""

UPDATE_TASK_STATUS_SUCCESS = """
✅ Task Status Updated:
   Dev Tasks - Completed: {dev_completed}, In Progress: {dev_in_progress}, Planned: {dev_planned}
   Test Tasks - Completed: {test_completed}, In Progress: {test_in_progress}, Planned: {test_planned}
   Quality - Bugs: {bugs_found}, Coverage: {avg_coverage:.1f}%"""

UPDATE_TASK_STATUS_ERROR = "❌ {error}"

UPDATE_TASK_STATUS_FOOTER = "================================================================================"

# ============================================================================
# UI MESSAGES - GENERATE SUMMARY
# ============================================================================

GENERATE_SUMMARY_HEADER = """
================================================================================
📋 GENERATING DAILY SCRUM SUMMARY
================================================================================"""

GENERATE_SUMMARY_SUCCESS = """
✅ Daily Scrum Summary Generated:
   Status: {status}
   Total Blockers: {total_blockers}
   High Priority: {high_priority}"""

GENERATE_SUMMARY_ERROR = "❌ {error}"

GENERATE_SUMMARY_FOOTER = "================================================================================"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_MISSING_DEV_REPORTS = "Error collecting dev reports: {error}"

ERROR_MISSING_TESTER_REPORTS = "Error collecting tester reports: {error}"

ERROR_AGGREGATING_REPORTS = "Error aggregating reports: {error}"

ERROR_MISSING_AGGREGATED_REPORTS = "Missing aggregated reports"

ERROR_DETECTING_BLOCKERS = "Error detecting blockers: {error}"

ERROR_UPDATING_TASK_STATUS = "Error updating task status: {error}"

ERROR_GENERATING_SUMMARY = "Error generating summary: {error}"

ERROR_DAILY_COORDINATOR = "\n❌ DAILY COORDINATOR: Error: {error}"

# ============================================================================