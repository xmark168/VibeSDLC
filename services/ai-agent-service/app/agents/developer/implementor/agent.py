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
    copy_boilerplate,
    create_pr,
    finalize,
    implement_files,
    initialize,
    run_and_verify,
    run_tests,
    setup_branch,
)
from .state import ImplementorState

# Load environment variables
load_dotenv()


class ImplementorAgent:
    """
    Implementor Agent - Thực hiện implementation plan từ Planner Agent.

    Workflow:
    START → initialize → setup_branch → [copy_boilerplate] → implement_files →
    run_tests → commit_changes → create_pr → finalize → END

    Với conditional branch: copy_boilerplate chỉ chạy cho new projects
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
        self.session_id = session_id
        self.user_id = user_id

        # Setup Langfuse tracing (optional)
        try:
            if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
                self.langfuse_handler = CallbackHandler(
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                    session_id=session_id,
                    user_id=user_id,
                )
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
        """Build LangGraph workflow cho implementor."""
        graph_builder = StateGraph(ImplementorState)

        # Add nodes
        graph_builder.add_node("initialize", initialize)
        graph_builder.add_node("setup_branch", setup_branch)
        graph_builder.add_node("copy_boilerplate", copy_boilerplate)
        graph_builder.add_node("implement_files", implement_files)
        graph_builder.add_node("run_tests", run_tests)
        graph_builder.add_node("run_and_verify", run_and_verify)
        graph_builder.add_node("commit_changes", commit_changes)
        graph_builder.add_node("create_pr", create_pr)
        graph_builder.add_node("finalize", finalize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "setup_branch")

        # Conditional edge after setup_branch
        graph_builder.add_conditional_edges("setup_branch", self.after_setup_branch)

        # Continue workflow
        graph_builder.add_edge("copy_boilerplate", "implement_files")
        graph_builder.add_edge("implement_files", "run_tests")
        graph_builder.add_edge("run_tests", "run_and_verify")
        graph_builder.add_edge("run_and_verify", "commit_changes")
        graph_builder.add_edge("commit_changes", "create_pr")
        graph_builder.add_edge("create_pr", "finalize")
        graph_builder.add_edge("finalize", END)

        # Setup checkpointer
        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    def after_setup_branch(self, state: ImplementorState) -> str:
        """
        Conditional branch sau setup_branch node.

        Logic:
        - Nếu is_new_project = True và có boilerplate_template → copy_boilerplate
        - Ngược lại → implement_files

        Args:
            state: ImplementorState với project type info

        Returns:
            Next node name
        """
        print("\n🔀 Branch Decision after setup_branch:")
        print(f"   Is New Project: {state.is_new_project}")
        print(f"   Boilerplate Template: {state.boilerplate_template}")

        if state.is_new_project and state.boilerplate_template:
            print("   → Decision: COPY_BOILERPLATE (new project with template)")
            return "copy_boilerplate"
        else:
            print("   → Decision: IMPLEMENT_FILES (existing project or no template)")
            return "implement_files"

    def run(
        self,
        implementation_plan: dict[str, Any],
        task_description: str = "",
        sandbox_id: str = "",
        codebase_path: str = "",
        github_repo_url: str = "",
        thread_id: str | None = None,
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

            # Setup thread config
            thread_config = {"configurable": {"thread_id": thread_id or "default"}}

            # Run workflow
            print("📊 Executing implementation workflow...")
            final_state = None

            for step in self.graph.stream(initial_state, config=thread_config):
                node_name = list(step.keys())[0]
                node_state = step[node_name]

                print(f"  ✓ Completed: {node_name}")

                # Check for errors
                if node_state.status == "error":
                    print(f"  ❌ Error in {node_name}: {node_state.error_message}")
                    break

                final_state = node_state

            if final_state is None:
                raise Exception("Workflow failed to complete")

            # Prepare results
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

            print(f"🎉 Implementor completed: {final_state.status}")
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
