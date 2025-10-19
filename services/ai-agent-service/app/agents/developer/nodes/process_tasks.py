"""
Process Tasks Node

Orchestrate Planner → Implementor → Code Reviewer for each task.
"""

import time
from datetime import datetime
from typing import Dict, Any

from ..state import DeveloperState, TaskResult


def _invoke_planner_agent(task: Dict[str, Any], state: DeveloperState) -> Dict[str, Any]:
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
            user_id="developer_agent"
        )
        
        # Run planner with enriched description
        result = planner.run(
            task_description=task["enriched_description"],
            codebase_context="",
            codebase_path=state.working_directory,
            thread_id=f"{state.session_id}_planner_{task['id']}"
        )
        
        print(f"✅ Planning complete for {task['id']}")
        return result
        
    except Exception as e:
        error_msg = f"Planner failed for {task['id']}: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def _invoke_implementor_agent(task: Dict[str, Any], planner_result: Dict[str, Any], state: DeveloperState) -> Dict[str, Any]:
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
            user_id="developer_agent"
        )
        
        # Run implementor with plan from planner
        result = implementor.run(
            implementation_plan=planner_result.get("final_plan", {}),
            task_description=task["enriched_description"],
            codebase_path=state.working_directory,
            thread_id=f"{state.session_id}_implementor_{task['id']}"
        )
        
        print(f"✅ Implementation complete for {task['id']}")
        return result
        
    except Exception as e:
        error_msg = f"Implementor failed for {task['id']}: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def _invoke_code_reviewer_agent(task: Dict[str, Any], implementor_result: Dict[str, Any], state: DeveloperState) -> Dict[str, Any]:
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
        "message": "Code Reviewer Agent not yet implemented"
    }


def _process_single_task(task: Dict[str, Any], state: DeveloperState) -> TaskResult:
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
        start_time=start_time.isoformat()
    )
    
    try:
        # Step 1: Planning Phase
        print(f"\n📋 Phase 1: Planning")
        planner_result = _invoke_planner_agent(task, state)
        task_result.planner_result = planner_result
        
        if not planner_result.get("success", False):
            task_result.status = "failed"
            task_result.error_message = f"Planning failed: {planner_result.get('error', 'Unknown error')}"
            return task_result
        
        # Step 2: Implementation Phase
        print(f"\n⚙️ Phase 2: Implementation")
        implementor_result = _invoke_implementor_agent(task, planner_result, state)
        task_result.implementor_result = implementor_result
        
        if not implementor_result.get("success", False):
            task_result.status = "failed"
            task_result.error_message = f"Implementation failed: {implementor_result.get('error', 'Unknown error')}"
            return task_result
        
        # Step 3: Code Review Phase
        print(f"\n🔍 Phase 3: Code Review")
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
    
    for i, task in enumerate(state.eligible_tasks):
        state.current_task_index = i
        
        print(f"\n{'='*60}")
        print(f"Task {i+1}/{len(state.eligible_tasks)}")
        print(f"{'='*60}")
        
        # Process single task
        task_result = _process_single_task(task, state)
        task_results.append(task_result)
        
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
    
    print(f"\n🎉 Task processing complete!")
    print(f"✅ Successful: {state.execution_summary.successful_tasks_count}")
    print(f"❌ Failed: {state.execution_summary.failed_tasks_count}")
    print(f"⏭️ Skipped: {state.execution_summary.skipped_tasks_count}")
    
    # Move to next phase
    state.current_phase = "finalize"
    
    return state
