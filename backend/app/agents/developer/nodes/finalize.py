"""
Finalize Node

Generate final execution report and cleanup.
"""

import json
from datetime import datetime
from pathlib import Path

from ..state import DeveloperState


def _generate_execution_report(state: DeveloperState) -> dict:
    """
    Generate comprehensive execution report.
    
    Args:
        state: Current workflow state
        
    Returns:
        Execution report dictionary
    """
    summary = state.execution_summary
    
    # Calculate success rate
    total_processed = summary.processed_tasks_count
    success_rate = (summary.successful_tasks_count / total_processed * 100) if total_processed > 0 else 0
    
    # Build report
    report = {
        "sprint_execution_summary": {
            "sprint_id": summary.sprint_id,
            "sprint_goal": summary.sprint_goal,
            "execution_metadata": {
                "start_time": summary.start_time,
                "end_time": summary.end_time,
                "total_duration_seconds": summary.total_duration_seconds,
                "session_id": state.session_id
            },
            "task_statistics": {
                "total_assigned_items": summary.total_assigned_items,
                "eligible_tasks_count": summary.eligible_tasks_count,
                "processed_tasks_count": summary.processed_tasks_count,
                "successful_tasks_count": summary.successful_tasks_count,
                "failed_tasks_count": summary.failed_tasks_count,
                "skipped_tasks_count": summary.skipped_tasks_count,
                "success_rate_percentage": round(success_rate, 2)
            }
        },
        "task_results": []
    }
    
    # Add detailed task results
    for task_result in summary.task_results:
        task_report = {
            "task_id": task_result.task_id,
            "task_title": task_result.task_title,
            "task_type": task_result.task_type,
            "status": task_result.status,
            "execution_metadata": {
                "start_time": task_result.start_time,
                "end_time": task_result.end_time,
                "duration_seconds": task_result.duration_seconds
            }
        }
        
        # Add error message if failed
        if task_result.error_message:
            task_report["error_message"] = task_result.error_message
        
        # Add subagent results summary
        subagent_results = {}
        
        if task_result.planner_result:
            subagent_results["planner"] = {
                "success": task_result.planner_result.get("success", False),
                "ready_for_implementation": task_result.planner_result.get("ready_for_implementation", False),
                "complexity_score": task_result.planner_result.get("complexity_score", 0),
                "estimated_hours": task_result.planner_result.get("estimated_hours", 0)
            }
        
        if task_result.implementor_result:
            subagent_results["implementor"] = {
                "success": task_result.implementor_result.get("success", False),
                "feature_branch": task_result.implementor_result.get("feature_branch", ""),
                "files_created": len(task_result.implementor_result.get("files_created", [])),
                "files_modified": len(task_result.implementor_result.get("files_modified", []))
            }
        
        if task_result.reviewer_result:
            subagent_results["code_reviewer"] = {
                "success": task_result.reviewer_result.get("success", False),
                "review_status": task_result.reviewer_result.get("review_status", "")
            }
        
        task_report["subagent_results"] = subagent_results
        report["task_results"].append(task_report)
    
    return report


def _save_execution_report(report: dict, state: DeveloperState) -> str:
    """
    Save execution report to file.
    
    Args:
        report: Execution report
        state: Current workflow state
        
    Returns:
        Path to saved report file
    """
    # Create reports directory
    reports_dir = Path(state.working_directory) / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sprint_execution_report_{state.execution_summary.sprint_id}_{timestamp}.json"
    report_path = reports_dir / filename
    
    # Save report
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return str(report_path)


def finalize(state: DeveloperState) -> DeveloperState:
    """
    Finalize workflow execution and generate report.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with finalization complete
    """
    print("🏁 Finalizing Developer Agent execution...")
    
    # Set end time and calculate duration
    end_time = datetime.now()
    state.execution_summary.end_time = end_time.isoformat()
    
    if state.execution_summary.start_time:
        start_time = datetime.fromisoformat(state.execution_summary.start_time)
        duration = (end_time - start_time).total_seconds()
        state.execution_summary.total_duration_seconds = duration
    
    # Generate execution report
    print("📊 Generating execution report...")
    report = _generate_execution_report(state)
    
    # Save report to file
    try:
        report_path = _save_execution_report(report, state)
        print(f"💾 Execution report saved: {report_path}")
    except Exception as e:
        print(f"⚠️ Failed to save report: {e}")
        report_path = None
    
    # Print summary
    summary = state.execution_summary
    print(f"\n{'='*60}")
    print(f"🎯 SPRINT EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Sprint ID: {summary.sprint_id}")
    print(f"Sprint Goal: {summary.sprint_goal}")
    print(f"Session ID: {state.session_id}")
    print(f"Duration: {summary.total_duration_seconds:.1f} seconds")
    print(f"\n📊 TASK STATISTICS:")
    print(f"Total Assigned Items: {summary.total_assigned_items}")
    print(f"Eligible Tasks: {summary.eligible_tasks_count}")
    print(f"Processed Tasks: {summary.processed_tasks_count}")
    print(f"✅ Successful: {summary.successful_tasks_count}")
    print(f"❌ Failed: {summary.failed_tasks_count}")
    print(f"⏭️ Skipped: {summary.skipped_tasks_count}")
    
    if summary.processed_tasks_count > 0:
        success_rate = summary.successful_tasks_count / summary.processed_tasks_count * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if report_path:
        print(f"\n📄 Full report: {report_path}")
    
    print(f"{'='*60}")
    print("✅ Developer Agent execution complete!")
    
    return state
