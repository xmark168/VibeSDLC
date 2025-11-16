"""
Process Tasks Node

Orchestrate Planner → Implementor → Code Reviewer for each task.
"""

from datetime import datetime
from typing import Any

from ..state import DeveloperState, TaskResult


def _invoke_planner_agent(
    task: dict[str, Any], state: DeveloperState
) -> dict[str, Any]:
    """
    Invoke Planner Agent for a task.

    Args:
        task: Task to plan
        state: Current workflow state

    Returns:
        Planner result
    """
    try:
        # Import here to avoid circular imports
        from ..planner.agent import PlannerAgent

        print(f"🧠 Planning task: {task['id']}")

        # Create planner agent
        planner = PlannerAgent(
            model=state.model_name,
            session_id=state.session_id,
            user_id="developer_agent",
        )

        # Run planner with enriched description and scope
        result = planner.run(
            task_description=task["enriched_description"],
            codebase_context="",
            codebase_path=state.working_directory,
            thread_id=f"{state.session_id}_planner_{task['id']}",
            github_repo_url=state.github_repo_url,
            task_scope=task.get("scope", ""),
            task_labels=task.get("labels", []),
        )

        print(f"✅ Planning complete for {task['id']}")

        # 🔍 DEBUG: Print planner state JSON RAW
        if result.get("success", False):
            print("\n" + "=" * 80)
            print("🔍 PLANNER AGENT STATE JSON DEBUG - RAW OUTPUT")
            print("=" * 80)

            # Print full raw JSON structure
            final_plan = result.get("final_plan", {})

            print("\n📋 FULL RAW JSON STRUCTURE:")

            import json

            # Print clean JSON format

            print(json.dumps(final_plan, indent=2, ensure_ascii=False))

            # Quick summary for validation check
            if "file_changes" in final_plan:
                file_changes = final_plan["file_changes"]
                files_to_create = file_changes.get("files_to_create", [])
                files_to_modify = file_changes.get("files_to_modify", [])

                print("\n📊 QUICK SUMMARY:")
                print(f"  - files_to_create: {len(files_to_create)} files")
                print(f"  - files_to_modify: {len(files_to_modify)} files")

                # Check if empty (this is the problem we're debugging)
                if len(files_to_create) == 0 and len(files_to_modify) == 0:
                    print("❌ PROBLEM DETECTED: No file operations specified!")
                    print("This will cause Implementor Agent validation to fail.")
                else:
                    print("✅ File operations found - should pass validation")

            # Save full state to JSON file for detailed inspection
            debug_file = f"debug_planner_state_{task['id']}.json"
            try:
                with open(debug_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False, default=str)
                print(f"\n💾 Full planner state saved to: {debug_file}")
            except Exception as save_error:
                print(f"⚠️ Could not save debug file: {save_error}")

            print("=" * 80 + "\n")

        return result

    except Exception as e:
        error_msg = f"Planner failed for {task['id']}: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def _invoke_implementor_agent(
    task: dict[str, Any], planner_result: dict[str, Any], state: DeveloperState
) -> dict[str, Any]:
    """
    Invoke Implementor Agent for a task.

    Args:
        task: Task to implement
        planner_result: Result from planner
        state: Current workflow state

    Returns:
        Implementor result
    """
    try:
        # Import here to avoid circular imports
        from ..implementor.agent import ImplementorAgent

        print(f"⚙️ Implementing task: {task['id']}")

        # Create implementor agent
        implementor = ImplementorAgent(
            model=state.model_name,
            session_id=state.session_id,
            user_id="developer_agent",
        )

        # Run implementor with plan from planner
        implementor_params = {
            "implementation_plan": planner_result.get("final_plan", {}),
            "task_description": task["enriched_description"],
            "codebase_path": state.working_directory,
            "thread_id": f"{state.session_id}_implementor_{task['id']}",
        }

        # Add source_branch for sequential branching if available
        if hasattr(state, "source_branch") and state.source_branch:
            implementor_params["source_branch"] = state.source_branch
            print(f"🔗 Passing source branch to implementor: {state.source_branch}")

        result = implementor.run(**implementor_params)

        print(f"✅ Implementation complete for {task['id']}")
        return result

    except Exception as e:
        error_msg = f"Implementor failed for {task['id']}: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def _invoke_code_reviewer_agent(
    task: dict[str, Any], implementor_result: dict[str, Any], state: DeveloperState
) -> dict[str, Any]:
    """
    Invoke Code Reviewer Agent for a task (placeholder).

    Args:
        task: Task to review
        implementor_result: Result from implementor
        state: Current workflow state

    Returns:
        Code reviewer result
    """
    print(f"🔍 Code review for task: {task['id']} (placeholder)")

    # Placeholder implementation
    return {
        "success": True,
        "review_status": "placeholder",
        "message": "Code Reviewer Agent not yet implemented",
    }


def _process_single_task(task: dict[str, Any], state: DeveloperState) -> TaskResult:
    """
    Process a single task through the complete workflow.

    Args:
        task: Task to process
        state: Current workflow state

    Returns:
        Task result
    """
    task_id = task["id"]
    start_time = datetime.now()

    print(f"\n🎯 Processing task: {task_id}")
    print(f"📝 Title: {task['title']}")
    print(f"🏷️ Type: {task['task_type']}")

    # Initialize task result
    task_result = TaskResult(
        task_id=task_id,
        task_type=task["task_type"],
        task_title=task["title"],
        task_description=task["description"],
        parent_context=task["parent_context"],
        enriched_description=task["enriched_description"],
        start_time=start_time.isoformat(),
    )

    try:
        # Step 1: Planning Phase
        print("\n📋 Phase 1: Planning")
        planner_result = _invoke_planner_agent(task, state)
        task_result.planner_result = planner_result

        if not planner_result.get("success", False):
            task_result.status = "failed"
            task_result.error_message = (
                f"Planning failed: {planner_result.get('error', 'Unknown error')}"
            )
            return task_result

        # Step 2: Implementation Phase
        print("\n⚙️ Phase 2: Implementation")
        implementor_result = _invoke_implementor_agent(task, planner_result, state)
        task_result.implementor_result = implementor_result

        if not implementor_result.get("success", False):
            task_result.status = "failed"
            task_result.error_message = f"Implementation failed: {implementor_result.get('error', 'Unknown error')}"
            return task_result

        # Auto-commit changes after successful implementation to preserve files for next task
        if implementor_result.get("success", False):
            print("\n💾 Auto-committing changes to preserve for next task...")
            try:
                import json

                from ..implementor.tool.git_tools_gitpython import commit_changes_tool

                commit_message = f"feat: implement {task['title']} ({task['id']})"
                commit_result = commit_changes_tool.invoke(
                    {
                        "message": commit_message,
                        "files": None,  # Commit all changes
                        "working_directory": state.working_directory,
                    }
                )

                commit_data = json.loads(commit_result)
                if commit_data.get("status") == "success":
                    print(
                        f"✅ Auto-committed: {commit_data.get('commit_hash', '')[:8]}"
                    )
                    task_result.auto_commit_hash = commit_data.get("commit_hash", "")
                else:
                    print(
                        f"⚠️ Auto-commit failed: {commit_data.get('message', 'Unknown error')}"
                    )
            except Exception as e:
                print(f"⚠️ Auto-commit error: {e}")
                # Don't fail the task if auto-commit fails

        # Step 3: Code Review Phase
        print("\n🔍 Phase 3: Code Review")
        reviewer_result = _invoke_code_reviewer_agent(task, implementor_result, state)
        task_result.reviewer_result = reviewer_result

        # Mark as successful
        task_result.status = "success"
        print(f"✅ Task {task_id} completed successfully")

    except Exception as e:
        task_result.status = "failed"
        task_result.error_message = f"Unexpected error: {e}"
        print(f"❌ Task {task_id} failed: {e}")

        if not state.continue_on_error:
            raise

    finally:
        # Set end time and duration
        end_time = datetime.now()
        task_result.end_time = end_time.isoformat()
        task_result.duration_seconds = (end_time - start_time).total_seconds()

    return task_result


def process_tasks(state: DeveloperState) -> DeveloperState:
    """
    Process all eligible tasks through Planner → Implementor → Code Reviewer workflow.

    Args:
        state: Current workflow state

    Returns:
        Updated state with task results
    """
    print("🔄 Processing tasks through orchestration workflow...")

    if not state.eligible_tasks:
        print("⚠️ No eligible tasks to process")
        state.current_phase = "finalize"
        return state

    print(f"📋 Processing {len(state.eligible_tasks)} eligible tasks...")

    task_results = []
    previous_task_branch = None  # Track previous task branch for sequential branching

    for i, task in enumerate(state.eligible_tasks):
        state.current_task_index = i

        print(f"\n{'=' * 60}")
        print(f"Task {i + 1}/{len(state.eligible_tasks)}")
        print(f"{'=' * 60}")

        # Set source branch for sequential branching (from previous task)
        if previous_task_branch:
            print(f"🔗 Sequential branching: Will create from '{previous_task_branch}'")
            # Store in state for implementor to use
            state.source_branch = previous_task_branch
        else:
            # First task - no source branch
            state.source_branch = None

        # Process single task
        task_result = _process_single_task(task, state)
        task_results.append(task_result)

        # Track current task branch for next iteration
        if task_result.status == "success" and task_result.implementor_result:
            # Extract feature branch from implementor result
            feature_branch = task_result.implementor_result.get("feature_branch")
            if feature_branch:
                previous_task_branch = feature_branch
                print(f"📝 Tracked branch for next task: {previous_task_branch}")

        # Update execution summary
        state.execution_summary.processed_tasks_count += 1

        if task_result.status == "success":
            state.execution_summary.successful_tasks_count += 1
        elif task_result.status == "failed":
            state.execution_summary.failed_tasks_count += 1
        else:
            state.execution_summary.skipped_tasks_count += 1

    # Store results
    state.execution_summary.task_results = task_results

    print("\n🎉 Task processing complete!")
    print(f"✅ Successful: {state.execution_summary.successful_tasks_count}")
    print(f"❌ Failed: {state.execution_summary.failed_tasks_count}")
    print(f"⏭️ Skipped: {state.execution_summary.skipped_tasks_count}")

    # Move to next phase
    state.current_phase = "finalize"

    return state
