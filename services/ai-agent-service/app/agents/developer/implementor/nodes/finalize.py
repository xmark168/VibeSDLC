"""
Finalize Node

Hoàn tất Implementor workflow và tạo final summary.
"""

from langchain_core.messages import AIMessage

from ..state import ImplementorState


def finalize(state: ImplementorState) -> ImplementorState:
    """
    Hoàn tất implementor workflow và tạo summary.

    Args:
        state: ImplementorState với completed implementation

    Returns:
        Final ImplementorState với summary
    """
    try:
        print("🏁 Finalizing implementation...")

        # Mark implementation as complete
        state.implementation_complete = True
        state.status = "completed"

        # Generate final summary
        summary = _generate_final_summary(state)
        state.summary = summary

        # Add final message
        message = AIMessage(
            content=f"🎉 Implementation completed successfully!\n\n"
            f"**Summary:**\n"
            f"- Task: {state.task_description}\n"
            f"- Files Created: {len(state.files_created)}\n"
            f"- Files Modified: {len(state.files_modified)}\n"
            f"- Branch: {state.feature_branch}\n"
            f"- Commit: {state.final_commit_hash[:8] if state.final_commit_hash else 'N/A'}\n"
            f"- Tests: {'✅ Passed' if state.tests_passed else '⚠️ Need attention'}\n"
            f"- Status: Ready for review"
        )
        state.messages.append(message)

        print("🎉 Implementation completed successfully!")
        print(
            f"  📊 Summary: {len(state.files_created)} created, {len(state.files_modified)} modified"
        )
        print(f"  🌿 Branch: {state.feature_branch}")
        print(
            f"  💾 Commit: {state.final_commit_hash[:8] if state.final_commit_hash else 'N/A'}"
        )

        return state

    except Exception as e:
        state.error_message = f"Finalization failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Finalization error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Finalization failed: {e}")
        return state


def _generate_final_summary(state: ImplementorState) -> dict:
    """
    Generate comprehensive summary of implementation.

    Args:
        state: ImplementorState với implementation details

    Returns:
        Summary dictionary
    """
    summary = {
        "task_id": state.task_id,
        "task_description": state.task_description,
        "implementation_type": "new_project"
        if state.is_new_project
        else "existing_project",
        "tech_stack": state.tech_stack,
        "boilerplate_template": state.boilerplate_template,
        # File operations
        "files_created": len(state.files_created),
        "files_modified": len(state.files_modified),
        "files_created_list": state.files_created,
        "files_modified_list": state.files_modified,
        # Git operations
        "feature_branch": state.feature_branch,
        "base_branch": state.base_branch,
        "final_commit_hash": state.final_commit_hash,
        "git_operations": len(state.git_operations),
        # Testing
        "tests_run": hasattr(state.test_execution, "test_command")
        and bool(state.test_execution.test_command),
        "tests_passed": state.tests_passed,
        "test_duration": getattr(state.test_execution, "duration", 0.0),
        # Status
        "implementation_complete": state.implementation_complete,
        "status": state.status,
        "has_errors": bool(state.error_message),
        "error_message": state.error_message,
        # Tools used
        "tools_used": list(state.tools_output.keys()),
        # Workflow phases completed
        "phases_completed": [
            "initialize",
            "setup_branch",
            "copy_boilerplate" if state.is_new_project else None,
            "generate_code",
            "implement_files",
            "run_tests",
            "commit_changes",
            "create_pr",
            "finalize",
        ],
        # Next steps for user
        "next_steps": [
            "Visit Git platform to create Pull Request"
            if state.status == "pr_ready"
            else None,
            "Review implementation in feature branch",
            "Run additional tests if needed",
            "Merge PR after review approval",
        ],
    }

    # Remove None values
    summary["phases_completed"] = [
        p for p in summary["phases_completed"] if p is not None
    ]
    summary["next_steps"] = [s for s in summary["next_steps"] if s is not None]

    return summary
