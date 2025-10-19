"""
Developer Agent

Main Developer Agent orchestrator that coordinates Planner, Implementor, and Code Reviewer
subagents to execute sprint tasks from Product Owner Agent output.

This agent:
1. Reads sprint.json and backlog.json from Product Owner Agent
2. Filters tasks by task_type (Infrastructure/Development only)
3. Resolves parent_id to enrich task context with Epic/User Story information
4. Orchestrates Planner → Implementor → Code Reviewer workflow for each task
5. Generates comprehensive sprint execution report

Architecture:
```
Developer Agent (Main Orchestrator)
├── Sprint Parser - Load and validate sprint/backlog data
├── Task Filter - Filter by task_type and resolve parent context
├── Task Processor - Orchestrate subagents for each task
│   ├── Planner Agent - Generate implementation plan
│   ├── Implementor Agent - Execute implementation
│   └── Code Reviewer Agent - Review code quality (placeholder)
└── Report Generator - Generate execution summary
```
"""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import (
    filter_tasks,
    finalize,
    initialize,
    parse_sprint,
    process_tasks,
)
from .state import DeveloperState

# Load environment variables
load_dotenv()


class DeveloperAgent:
    """
    Developer Agent - Main orchestrator for sprint task execution.

    Coordinates Planner, Implementor, and Code Reviewer subagents to execute
    Development and Infrastructure tasks from Product Owner Agent sprint planning.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        session_id: str | None = None,
        user_id: str | None = None,
        enable_langfuse: bool = True,
    ):
        """
        Initialize Developer Agent.

        Args:
            model: LLM model to use
            session_id: Session ID for tracking
            user_id: User ID for tracking
            enable_langfuse: Enable Langfuse tracing
        """
        self.model = model
        self.session_id = session_id
        self.user_id = user_id
        self.enable_langfuse = enable_langfuse

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Setup Langfuse callback if enabled
        self.langfuse_handler = None
        if enable_langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
            try:
                self.langfuse_handler = CallbackHandler(
                    session_id=session_id,
                    user_id=user_id,
                )
            except Exception as e:
                print(f"⚠️ Langfuse initialization failed: {e}")

        # Create workflow
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph workflow for Developer Agent.

        Returns:
            Configured StateGraph workflow
        """
        # Create state graph
        workflow = StateGraph(DeveloperState)

        # Add nodes
        workflow.add_node("initialize", initialize)
        workflow.add_node("parse_sprint", parse_sprint)
        workflow.add_node("filter_tasks", filter_tasks)
        workflow.add_node("process_tasks", process_tasks)
        workflow.add_node("finalize", finalize)

        # Add edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "parse_sprint")
        workflow.add_edge("parse_sprint", "filter_tasks")
        workflow.add_edge("filter_tasks", "process_tasks")
        workflow.add_edge("process_tasks", "finalize")
        workflow.add_edge("finalize", END)

        # Compile workflow
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def run(
        self,
        sprint_id: str = "sprint-1",
        backlog_path: str = "",
        sprint_path: str = "",
        working_directory: str = ".",
        thread_id: str | None = None,
        continue_on_error: bool = True,
    ) -> dict[str, Any]:
        """
        Run Developer Agent workflow to execute sprint tasks.

        Args:
            sprint_id: Sprint ID to execute (used for filtering if multiple sprints)
            backlog_path: Path to backlog.json file (empty = auto-detect)
            sprint_path: Path to sprint.json file (empty = auto-detect)
            working_directory: Working directory for code operations
            thread_id: Thread ID for checkpointer (to resume)
            continue_on_error: Continue execution when individual tasks fail

        Returns:
            Execution results with sprint summary and task details
        """
        try:
            print("🚀 Starting Developer Agent...")

            # Create initial state
            initial_state = DeveloperState(
                backlog_path=backlog_path,
                sprint_path=sprint_path,
                working_directory=working_directory,
                model_name=self.model,
                session_id=self.session_id or "default",
                continue_on_error=continue_on_error,
            )

            # Setup thread config
            thread_config = {"configurable": {"thread_id": thread_id or "default"}}

            # Run workflow
            print("📊 Executing Developer Agent workflow...")
            final_state = None

            for step in self.workflow.stream(initial_state, thread_config):
                node_name = list(step.keys())[0]
                node_state = step[node_name]
                final_state = node_state

                print(f"✅ Completed: {node_name}")

                # Add Langfuse tracing if enabled
                if self.langfuse_handler:
                    try:
                        self.langfuse_handler.on_chain_end(
                            outputs={
                                "node": node_name,
                                "phase": node_state.current_phase,
                            }
                        )
                    except Exception:
                        pass  # Ignore Langfuse errors

            if final_state is None:
                raise RuntimeError("Workflow execution failed - no final state")

            # Build result
            summary = final_state.execution_summary
            result = {
                "success": True,
                "sprint_id": summary.sprint_id,
                "session_id": final_state.session_id,
                "execution_summary": {
                    "total_assigned_items": summary.total_assigned_items,
                    "eligible_tasks_count": summary.eligible_tasks_count,
                    "processed_tasks_count": summary.processed_tasks_count,
                    "successful_tasks_count": summary.successful_tasks_count,
                    "failed_tasks_count": summary.failed_tasks_count,
                    "skipped_tasks_count": summary.skipped_tasks_count,
                    "success_rate": (
                        summary.successful_tasks_count
                        / summary.processed_tasks_count
                        * 100
                        if summary.processed_tasks_count > 0
                        else 0
                    ),
                    "total_duration_seconds": summary.total_duration_seconds,
                },
                "task_results": [
                    {
                        "task_id": task.task_id,
                        "status": task.status,
                        "task_title": task.task_title,
                        "task_type": task.task_type,
                        "duration_seconds": task.duration_seconds,
                        "error_message": task.error_message,
                    }
                    for task in summary.task_results
                ],
                "metadata": {
                    "model": self.model,
                    "working_directory": final_state.working_directory,
                    "thread_id": thread_id,
                },
            }

            print("✅ Developer Agent execution completed successfully!")
            return result

        except Exception as e:
            error_msg = f"Developer Agent execution failed: {e}"
            print(f"❌ {error_msg}")

            # Add Langfuse error tracing if enabled
            if self.langfuse_handler:
                try:
                    self.langfuse_handler.on_chain_error(error=e)
                except Exception:
                    pass  # Ignore Langfuse errors

            return {
                "success": False,
                "error": error_msg,
                "sprint_id": sprint_id,
                "session_id": self.session_id,
            }


# Convenience function for direct usage
def run_developer_agent(
    sprint_id: str = "sprint-1",
    backlog_path: str = "",
    sprint_path: str = "",
    working_directory: str = ".",
    model_name: str = "gpt-4o",
    session_id: str | None = None,
    thread_id: str | None = None,
    continue_on_error: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to run Developer Agent.

    Args:
        sprint_id: Sprint ID to execute
        backlog_path: Path to backlog.json file
        sprint_path: Path to sprint.json file
        working_directory: Working directory for code operations
        model_name: LLM model to use
        session_id: Session ID for tracking
        thread_id: Thread ID for checkpointer
        continue_on_error: Continue execution when individual tasks fail

    Returns:
        Execution results
    """
    agent = DeveloperAgent(
        model=model_name,
        session_id=session_id,
        user_id="developer_agent_user",
    )

    return agent.run(
        sprint_id=sprint_id,
        backlog_path=backlog_path,
        sprint_path=sprint_path,
        working_directory=working_directory,
        thread_id=thread_id,
        continue_on_error=continue_on_error,
    )
