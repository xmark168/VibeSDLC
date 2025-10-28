"""
Implementor Agent

Main ImplementorAgent class với LangGraph workflow cho implementation process.
"""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import (
    commit_changes,
    create_pr,
    finalize,
    initialize,
    run_and_verify,
    run_tests,
    setup_branch,
)
from .state import ImplementorState

# Load environment variables
load_dotenv()

# Import install_dependencies separately

# Import generate_code separately to avoid auto-formatter issues


class ImplementorAgent:
    """
    Implementor Agent - Thực hiện implementation plan từ Planner Agent.

    Workflow:
    START → initialize → setup_branch → install_dependencies →
    generate_code → execute_step → implement_files → run_tests → commit_changes → create_pr → finalize → END

    install_dependencies luôn chạy để cài đặt external dependencies từ plan
    generate_code luôn chạy để tạo actual code content
    execute_step executes steps và sub_steps sequentially từ simplified plan
    Repository creation từ template được xử lý bởi GitHub Template Repository API
    """

    def __init__(
        self,
        model: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ):
        """
        Initialize ImplementorAgent.

        Args:
            model: Model name (default: gpt-4o)
            session_id: Session ID cho Langfuse tracing
            user_id: User ID cho Langfuse tracing
        """
        self.model_name = model or "gpt-4o"
        self.session_id = session_id or "default_implementor_session"
        self.user_id = user_id

        # Setup Langfuse tracing (optional)
        try:
            if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
                self.langfuse_handler = CallbackHandler()
            else:
                self.langfuse_handler = None
        except Exception as e:
            print(f"⚠️  Langfuse not configured: {e}")
            self.langfuse_handler = None

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _llm(self, model: str = "gpt-4o", temperature: float = 0.3) -> ChatOpenAI:
        """Create LLM instance."""
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow cho implementor (Option 1 Flow)."""
        graph_builder = StateGraph(ImplementorState)

        # Add nodes
        graph_builder.add_node("initialize", initialize)
        graph_builder.add_node("setup_branch", setup_branch)

        # Import nodes here to avoid auto-formatter issues
        from .nodes.execute_step import execute_step
        from .nodes.install_dependencies import install_dependencies

        graph_builder.add_node("install_dependencies", install_dependencies)
        graph_builder.add_node(
            "execute_step", execute_step
        )  # Now includes generation + implementation

        # Legacy nodes (not used in Option 1 main flow)
        # from .nodes.generate_code import generate_code
        # graph_builder.add_node("generate_code", generate_code)
        # graph_builder.add_node("implement_files", implement_files)

        graph_builder.add_node("run_tests", run_tests)
        graph_builder.add_node("run_and_verify", run_and_verify)
        graph_builder.add_node("commit_changes", commit_changes)
        graph_builder.add_node("create_pr", create_pr)
        graph_builder.add_node("finalize", finalize)

        # Add edges - Option 1 Flow
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "setup_branch")
        graph_builder.add_edge("setup_branch", "install_dependencies")

        # Option 1: Direct flow to execute_step (skips generate_code and implement_files)
        graph_builder.add_edge("install_dependencies", "execute_step")

        # Conditional edge: execute_step loops back if more sub-steps, or proceeds to run_tests
        graph_builder.add_conditional_edges(
            "execute_step",
            self._should_continue_execution,
            {
                "continue": "execute_step",  # Loop back for next sub-step
                "done": "run_tests",  # All sub-steps completed
            },
        )

        # Rest of the workflow remains the same
        graph_builder.add_edge("run_tests", "run_and_verify")
        graph_builder.add_edge("run_and_verify", "commit_changes")
        graph_builder.add_edge("commit_changes", "create_pr")
        graph_builder.add_edge("create_pr", "finalize")
        graph_builder.add_edge("finalize", END)

        # Setup checkpointer
        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    def _should_continue_execution(self, state: ImplementorState) -> str:
        """
        Determine if execute_step should continue or proceed to next phase.

        NOTE: This function should NOT mutate state. All state mutations
        happen in execute_step node to ensure they are properly persisted.

        Returns:
            "continue" if there are more sub-steps to execute
            "done" if all steps completed or error occurred
        """
        # ✅ CHECK ERROR STATUS FIRST (prevent infinite loop on failures)
        if state.status == "step_execution_failed":
            print("❌ Stopping execution due to sub-step failure")
            print(f"   Error: {state.error_message}")
            return "done"  # Exit loop to prevent infinite retry

        # Check if execution is complete
        if state.status == "execution_complete":
            print("✅ Execution complete, proceeding to tests")
            return "done"

        # Check if we have steps to execute
        if not state.plan_steps:
            print("⚠️ No plan steps found")
            return "done"

        # Check if all steps completed
        if state.current_step_index >= len(state.plan_steps):
            print("✅ All steps completed (by index check)")
            return "done"

        # More work to do
        print(
            f"🔄 Continuing execution: Step {state.current_step_index + 1}, Sub-step {state.current_sub_step_index + 1}"
        )
        return "continue"

    def run(
        self,
        implementation_plan: dict[str, Any],
        task_description: str = "",
        sandbox_id: str = "",
        codebase_path: str = "",
        github_repo_url: str = "",
        thread_id: str | None = None,
        test_mode: bool = False,
        source_branch: str = None,  # New parameter for sequential branching
    ) -> dict[str, Any]:
        """
        Run implementor workflow.

        Args:
            implementation_plan: Implementation plan từ Planner Agent
            task_description: Task description
            sandbox_id: Daytona sandbox ID
            codebase_path: Path to codebase
            github_repo_url: GitHub repository URL
            thread_id: Thread ID cho conversation tracking
            test_mode: If True, skip branch creation for testing
            source_branch: Source branch for sequential branching (optional)

        Returns:
            Implementation results
        """
        try:
            print("🚀 Starting Implementor Agent...")

            # Create initial state
            initial_state = ImplementorState(
                implementation_plan=implementation_plan,
                task_description=task_description,
                sandbox_id=sandbox_id,
                codebase_path=codebase_path,
                github_repo_url=github_repo_url,
            )

            # Add test mode if specified
            if test_mode:
                initial_state.test_mode = test_mode

            # Add source branch for sequential branching
            if source_branch:
                initial_state.source_branch = source_branch

            # Build metadata for Langfuse tracing
            metadata = {}
            if self.session_id:
                metadata["langfuse_session_id"] = self.session_id
            if self.user_id:
                metadata["langfuse_user_id"] = self.user_id
            metadata["langfuse_tags"] = ["implementor_agent"]

            # Setup config with optional Langfuse callback
            callbacks = []
            if self.langfuse_handler:
                callbacks.append(self.langfuse_handler)

            config = {
                "configurable": {"thread_id": thread_id or "default"},
                "callbacks": callbacks,
                "metadata": metadata,
                "recursion_limit": 50,
            }

            # Run workflow
            print("📊 Executing implementation workflow...")
            final_state = None

            for step in self.graph.stream(initial_state.model_dump(), config=config):
                node_name = list(step.keys())[0]
                node_state = step[node_name]

                print(f"  ✓ Completed: {node_name}")

                # Check for errors - node_state is dict, not object
                if isinstance(node_state, dict):
                    status = node_state.get("status", "")
                    if status == "error":
                        error_msg = node_state.get("error_message", "Unknown error")
                        print(f"  ❌ Error in {node_name}: {error_msg}")
                        break
                else:
                    # If it's an object, access attributes directly
                    if hasattr(node_state, "status") and node_state.status == "error":
                        print(f"  ❌ Error in {node_name}: {node_state.error_message}")
                        break

                final_state = node_state

            if final_state is None:
                raise Exception("Workflow failed to complete")

            # Prepare results - handle both dict and object final_state
            if isinstance(final_state, dict):
                results = {
                    "status": final_state.get("status", "unknown"),
                    "implementation_complete": final_state.get(
                        "implementation_complete", False
                    ),
                    "task_id": final_state.get("task_id", ""),
                    "task_description": final_state.get("task_description", ""),
                    "feature_branch": final_state.get("feature_branch", ""),
                    "final_commit_hash": final_state.get("final_commit_hash", ""),
                    "files_created": final_state.get("files_created", []),
                    "files_modified": final_state.get("files_modified", []),
                    "tests_passed": final_state.get("tests_passed", False),
                    "summary": final_state.get("summary", {}),
                    "error_message": final_state.get("error_message", ""),
                    "messages": [
                        msg.get("content", "") if isinstance(msg, dict) else msg.content
                        for msg in final_state.get("messages", [])
                    ],
                }
                status = final_state.get("status", "unknown")
            else:
                results = {
                    "status": final_state.status,
                    "implementation_complete": final_state.implementation_complete,
                    "task_id": final_state.task_id,
                    "task_description": final_state.task_description,
                    "feature_branch": final_state.feature_branch,
                    "final_commit_hash": final_state.final_commit_hash,
                    "files_created": final_state.files_created,
                    "files_modified": final_state.files_modified,
                    "tests_passed": final_state.tests_passed,
                    "summary": final_state.summary,
                    "error_message": final_state.error_message,
                    "messages": [msg.content for msg in final_state.messages],
                }
                status = final_state.status

            print(f"🎉 Implementor completed: {status}")
            return results

        except Exception as e:
            error_msg = f"Implementor workflow failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "implementation_complete": False,
                "error_message": error_msg,
                "summary": {},
            }
