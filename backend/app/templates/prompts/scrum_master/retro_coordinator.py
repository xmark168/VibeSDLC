"""Prompts and messages for Retro Coordinator Agent."""

# ============================================================================
# COLLECT PO FEEDBACK
# ============================================================================

COLLECT_PO_FEEDBACK_HEADER = """
================================================================================
📊 COLLECTING PRODUCT OWNER FEEDBACK
================================================================================
"""

COLLECT_PO_FEEDBACK_SUCCESS = """✅ Collected feedback from Product Owner
   - Total feedback items: {total_items}
"""

COLLECT_PO_FEEDBACK_ERROR = """❌ Error collecting PO feedback: {error}"""

# ============================================================================
# COLLECT DEVELOPER FEEDBACK
# ============================================================================

COLLECT_DEV_FEEDBACK_HEADER = """
================================================================================
👨‍💻 COLLECTING DEVELOPER FEEDBACK
================================================================================
"""

COLLECT_DEV_FEEDBACK_SUCCESS = """✅ Collected feedback from {total_developers} developers
   - Total feedback items: {total_items}
"""

COLLECT_DEV_FEEDBACK_ERROR = """❌ Error collecting developer feedback: {error}"""

# ============================================================================
# COLLECT TESTER FEEDBACK
# ============================================================================

COLLECT_TESTER_FEEDBACK_HEADER = """
================================================================================
🧪 COLLECTING TESTER FEEDBACK
================================================================================
"""

COLLECT_TESTER_FEEDBACK_SUCCESS = """✅ Collected feedback from {total_testers} testers
   - Total feedback items: {total_items}
"""

COLLECT_TESTER_FEEDBACK_ERROR = """❌ Error collecting tester feedback: {error}"""

# ============================================================================
# CATEGORIZE ISSUES
# ============================================================================

CATEGORIZE_ISSUES_HEADER = """
================================================================================
📋 CATEGORIZING FEEDBACK INTO ISSUES
================================================================================
"""

CATEGORIZE_ISSUES_SUCCESS = """✅ Categorized feedback into {total_issues} unique issues
   - High severity: {high_severity}
   - Medium severity: {medium_severity}
   - Low severity: {low_severity}
"""

CATEGORIZE_ISSUES_ERROR = """❌ Error categorizing issues: {error}"""

# ============================================================================
# GENERATE IMPROVEMENT IDEAS
# ============================================================================

GENERATE_IDEAS_HEADER = """
================================================================================
💡 GENERATING IMPROVEMENT IDEAS
================================================================================
"""

GENERATE_IDEAS_SUCCESS = """✅ Generated {total_ideas} improvement ideas
   - High priority: {high_priority}
   - Medium priority: {medium_priority}
   - Low priority: {low_priority}
"""

GENERATE_IDEAS_ERROR = """❌ Error generating improvement ideas: {error}"""

# ============================================================================
# DEFINE ACTION ITEMS
# ============================================================================

DEFINE_ACTIONS_HEADER = """
================================================================================
✅ DEFINING ACTION ITEMS FOR NEXT SPRINT
================================================================================
"""

DEFINE_ACTIONS_SUCCESS = """✅ Defined {total_actions} action items
   - High priority: {high_priority}
   - Medium priority: {medium_priority}
   - Low priority: {low_priority}
"""

DEFINE_ACTIONS_ERROR = """❌ Error defining action items: {error}"""

# ============================================================================
# GENERATE SUMMARY REPORT
# ============================================================================

GENERATE_REPORT_HEADER = """
================================================================================
📊 GENERATING RETROSPECTIVE SUMMARY REPORT
================================================================================
"""

GENERATE_REPORT_SUCCESS = """✅ Generated retrospective summary report
   - Sprint: {sprint_name}
   - Date: {date}
   - Total feedback items: {total_feedback}
   - Total issues: {total_issues}
   - Total improvement ideas: {total_ideas}
   - Total action items: {total_actions}
"""

GENERATE_REPORT_ERROR = """❌ Error generating summary report: {error}"""

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_MISSING_PO_FEEDBACK = """Error collecting PO feedback: {error}"""

ERROR_MISSING_DEV_FEEDBACK = """Error collecting developer feedback: {error}"""

ERROR_MISSING_TESTER_FEEDBACK = """Error collecting tester feedback: {error}"""

ERROR_CATEGORIZING_ISSUES = """Error categorizing issues: {error}"""

ERROR_GENERATING_IDEAS = """Error generating improvement ideas: {error}"""

ERROR_DEFINING_ACTIONS = """Error defining action items: {error}"""

ERROR_GENERATING_REPORT = """Error generating retrospective report: {error}"""

ERROR_RETRO_COORDINATOR = """❌ Error running Retro Coordinator Agent: {error}"""
