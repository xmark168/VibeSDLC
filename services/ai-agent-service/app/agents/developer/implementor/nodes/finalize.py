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

        # Import Daytona utilities here to avoid import issues

        # Handle Daytona sandbox cleanup
        _handle_sandbox_cleanup(state)

        # Mark implementation as complete
        state.implementation_complete = True
        state.status = "completed"

        # Generate final summary
        summary = _generate_final_summary(state)
        state.summary = summary

        # Add final message with sandbox cleanup info
        sandbox_info = ""
        if state.sandbox_deletion:
            if state.sandbox_deletion.skipped:
                sandbox_info = f"\n- Sandbox: ⏭️ Cleanup skipped ({state.sandbox_deletion.skip_reason})"
            elif state.sandbox_deletion.success:
                sandbox_info = "\n- Sandbox: ✅ Cleaned up successfully"
            else:
                sandbox_info = f"\n- Sandbox: ⚠️ Cleanup failed ({state.sandbox_deletion.error[:50]}...)"

        message = AIMessage(
            content=f"🎉 Implementation completed successfully!\n\n"
            f"**Summary:**\n"
            f"- Task: {state.task_description}\n"
            f"- Files Created: {len(state.files_created)}\n"
            f"- Files Modified: {len(state.files_modified)}\n"
            f"- Branch: {state.feature_branch}\n"
            f"- Commit: {state.final_commit_hash[:8] if state.final_commit_hash else 'N/A'}\n"
            f"- Tests: {'✅ Passed' if state.tests_passed else '⚠️ Need attention'}"
            f"{sandbox_info}\n"
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
        "implementation_type": "existing_project",
        "tech_stack": state.tech_stack,
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
        # Sandbox management
        "sandbox_cleanup": {
            "attempted": state.sandbox_deletion is not None,
            "success": state.sandbox_deletion.success
            if state.sandbox_deletion
            else False,
            "skipped": state.sandbox_deletion.skipped
            if state.sandbox_deletion
            else False,
            "skip_reason": state.sandbox_deletion.skip_reason
            if state.sandbox_deletion
            else "",
            "error": state.sandbox_deletion.error if state.sandbox_deletion else "",
        }
        if state.sandbox_deletion
        else None,
        # Workflow phases completed
        "phases_completed": [
            "initialize",
            "setup_branch",
            "install_dependencies",
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


def _handle_sandbox_cleanup(state: ImplementorState) -> None:
    """
    Handle Daytona sandbox cleanup after workflow completion.

    Args:
        state: ImplementorState với sandbox information
    """
    # Import here to avoid circular imports
    from ..state import SandboxDeletion
    from ..utils.daytona_client import delete_sandbox_sync, should_delete_sandbox

    print("🧹 Checking for Daytona sandbox cleanup...")

    # Check if we should delete the sandbox
    if not should_delete_sandbox(state.status, state.sandbox_id):
        skip_reason = ""
        if not state.sandbox_id:
            skip_reason = "No sandbox ID provided"
        elif state.status not in ["completed", "pr_ready", "finalized"]:
            skip_reason = (
                f"Workflow not completed successfully (status: {state.status})"
            )
        else:
            skip_reason = "Unknown reason"

        print(f"⏭️  Skipping sandbox deletion: {skip_reason}")

        # Record skipped deletion
        state.sandbox_deletion = SandboxDeletion(
            sandbox_id=state.sandbox_id or "",
            success=False,
            message=f"Sandbox deletion skipped: {skip_reason}",
            skipped=True,
            skip_reason=skip_reason,
        )
        return

    print(f"🗑️  Deleting Daytona sandbox: {state.sandbox_id}")

    try:
        # Attempt to delete the sandbox
        deletion_result = delete_sandbox_sync(state.sandbox_id, max_retries=2)

        # Create SandboxDeletion object from result
        state.sandbox_deletion = SandboxDeletion(
            sandbox_id=deletion_result["sandbox_id"],
            success=deletion_result["success"],
            message=deletion_result["message"],
            retries_used=deletion_result["retries_used"],
            error=deletion_result.get("error", ""),
            skipped=False,
            skip_reason="",
        )

        if deletion_result["success"]:
            print(f"✅ Sandbox deleted successfully: {deletion_result['message']}")
            if deletion_result["retries_used"] > 0:
                print(f"   (Required {deletion_result['retries_used']} retries)")
        else:
            print(f"⚠️  Sandbox deletion failed: {deletion_result['message']}")
            print(f"   Error: {deletion_result.get('error', 'Unknown error')}")
            print(f"   Retries used: {deletion_result['retries_used']}")

    except Exception as e:
        error_msg = f"Exception during sandbox cleanup: {str(e)}"
        print(f"❌ {error_msg}")

        # Record failed deletion
        state.sandbox_deletion = SandboxDeletion(
            sandbox_id=state.sandbox_id or "",
            success=False,
            message=error_msg,
            retries_used=0,
            error=str(e),
            skipped=False,
            skip_reason="",
        )
