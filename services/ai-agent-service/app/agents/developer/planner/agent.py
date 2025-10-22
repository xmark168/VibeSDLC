"""
Planner Agent

Main PlannerAgent class với LangGraph workflow cho 4-phase planning process.
"""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import (
    finalize,
    generate_plan,
    initialize,
    initialize_sandbox,
    map_dependencies,
    parse_task,
    validate_plan,
)
from .state import PlannerState

# Load environment variables
load_dotenv()


class PlannerAgent:
    """
    Planner Agent - Phân tích task requirements và tạo detailed implementation plan.

    Workflow:
    START → initialize → initialize_sandbox → parse_task → websearch → analyze_codebase →
    map_dependencies → generate_plan → validate_plan → finalize → END

    Với validation loop: validate_plan có thể loop back đến analyze_codebase
    """

    def __init__(
        self,
        model: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ):
        """
        Initialize PlannerAgent.

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
        """Build LangGraph workflow cho planner."""
        graph_builder = StateGraph(PlannerState)

        # Add nodes
        graph_builder.add_node("initialize", initialize)
        graph_builder.add_node("initialize_sandbox", initialize_sandbox)
        graph_builder.add_node("parse_task", parse_task)
        from .nodes.analyze_codebase import analyze_codebase
        from .nodes.websearch import websearch

        graph_builder.add_node("websearch", websearch)
        graph_builder.add_node("analyze_codebase", analyze_codebase)
        graph_builder.add_node("map_dependencies", map_dependencies)
        graph_builder.add_node("generate_plan", generate_plan)
        graph_builder.add_node("validate_plan", validate_plan)
        graph_builder.add_node("finalize", finalize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "initialize_sandbox")
        graph_builder.add_edge("initialize_sandbox", "parse_task")

        # Conditional edge từ parse_task
        graph_builder.add_conditional_edges("parse_task", self.websearch_branch)

        # Include analyze_codebase in workflow
        graph_builder.add_edge("websearch", "analyze_codebase")
        graph_builder.add_edge("analyze_codebase", "map_dependencies")
        graph_builder.add_edge("map_dependencies", "generate_plan")
        graph_builder.add_edge("generate_plan", "validate_plan")

        # Conditional edges for validation loop
        graph_builder.add_conditional_edges("validate_plan", self.validate_branch)
        graph_builder.add_edge("finalize", END)

        # Setup checkpointer
        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    def websearch_branch(self, state: PlannerState) -> str:
        """
        Conditional branch sau parse_task node.

        Logic:
        - Đánh giá xem có cần web search hay không
        - Nếu cần → websearch
        - Nếu không cần → analyze_codebase
        """
        from .tools.tavily_search import should_perform_websearch

        task_description = state.task_description
        task_requirements = state.task_requirements.model_dump()
        codebase_context = state.codebase_context

        should_search, reason = should_perform_websearch(
            task_description=task_description,
            task_requirements=task_requirements,
            codebase_context=codebase_context,
        )

        print("\n🔀 WebSearch Branch Decision:")
        print(f"   Should Search: {should_search}")
        print(f"   Reason: {reason}")

        if should_search:
            print("   → Decision: WEBSEARCH")
            return "websearch"
        else:
            print("   → Decision: ANALYZE_CODEBASE (skip websearch)")
            return "analyze_codebase"

    def validate_branch(self, state: PlannerState) -> str:
        """
        Conditional branch sau validate_plan node.

        Logic:
        - Nếu can_proceed = True → finalize
        - Nếu can_proceed = False và current_iteration < max_iterations → analyze_codebase (retry)
        - Nếu can_proceed = False và current_iteration >= max_iterations → finalize (force)

        Args:
            state: PlannerState với validation results

        Returns:
            Next node name
        """
        print("\n🔀 Validation Branch Decision:")
        print(f"   Can Proceed: {state.can_proceed}")
        print(f"   Validation Score: {state.validation_score:.2f}")
        print(f"   Current Iteration: {state.current_iteration}")
        print(f"   Max Iterations: {state.max_iterations}")
        print(f"   Issues: {len(state.validation_issues)}")
        print(f"   Status: {state.status}")

        # Check for error states that should go directly to finalize
        error_states = [
            "error_plan_generation",
            "error_empty_plan_validation",
            "error_empty_implementation_plan",
        ]

        if state.status in error_states:
            print(f"   → Decision: FINALIZE (error state: {state.status})")
            return "finalize"
        elif state.can_proceed:
            print("   → Decision: FINALIZE (validation passed)")
            return "finalize"
        elif state.current_iteration < state.max_iterations:
            print(
                f"   → Decision: RETRY (iteration {state.current_iteration}/{state.max_iterations})"
            )
            return "analyze_codebase"  # Loop back to analysis
        else:
            print("   → Decision: FORCE FINALIZE (max iterations reached)")
            return "finalize"

    def run(
        self,
        task_description: str,
        codebase_context: str = "",
        codebase_path: str = "",
        github_repo_url: str = "",
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run planner workflow.

        Args:
            task_description: Task description từ product backlog
            codebase_context: Additional codebase context
            codebase_path: Path to codebase for analysis (empty = use default)
            github_repo_url: GitHub repository URL to clone into Daytona sandbox (empty = use local path)
            thread_id: Thread ID cho checkpointer (để resume)

        Returns:
            Dict với final_plan và metadata
        """
        if thread_id is None:
            thread_id = self.session_id or "default"

        # Create initial state
        initial_state = PlannerState(
            task_description=task_description,
            codebase_context=codebase_context,
            codebase_path=codebase_path,
            github_repo_url=github_repo_url,
        )

        # Build metadata for Langfuse tracing
        metadata = {}
        if self.session_id:
            metadata["langfuse_session_id"] = self.session_id
        if self.user_id:
            metadata["langfuse_user_id"] = self.user_id
        metadata["langfuse_tags"] = ["planner_agent"]

        # Setup config with optional Langfuse callback
        callbacks = []
        if self.langfuse_handler:
            callbacks.append(self.langfuse_handler)

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": callbacks,
            "metadata": metadata,
            "recursion_limit": 50,
        }

        print("\n" + "=" * 80)
        print("🚀 PLANNER AGENT STARTED")
        print("=" * 80)
        print(f"📝 Task: {task_description[:100]}...")
        print(f"🔗 Thread ID: {thread_id}")
        print("=" * 80 + "\n")

        try:
            # Stream agent execution
            final_state = None
            step_count = 0

            for output in self.graph.stream(
                initial_state.model_dump(),
                config=config,
            ):
                step_count += 1
                final_state = output

                # Log progress
                if isinstance(output, dict):
                    for node_name, node_output in output.items():
                        if isinstance(node_output, dict) and "status" in node_output:
                            print(
                                f"📍 Step {step_count}: {node_name} - {node_output['status']}"
                            )

            # Extract final result
            if final_state and isinstance(final_state, dict):
                # Get the last node's output
                last_node_output = list(final_state.values())[-1]

                # Get implementation plan object
                implementation_plan = last_node_output.get("implementation_plan")

                result = {
                    "success": True,
                    "final_plan": last_node_output.get("final_plan", {}),
                    "ready_for_implementation": last_node_output.get(
                        "ready_for_implementation", False
                    ),
                    "task_id": (
                        implementation_plan.task_id if implementation_plan else ""
                    ),
                    "complexity_score": (
                        implementation_plan.complexity_score
                        if implementation_plan
                        else 0
                    ),
                    "estimated_hours": (
                        implementation_plan.total_estimated_hours
                        if implementation_plan
                        else 0
                    ),
                    "story_points": (
                        implementation_plan.story_points if implementation_plan else 0
                    ),
                    "validation_score": last_node_output.get("validation_score", 0.0),
                    "status": last_node_output.get("status", "unknown"),
                    "iterations": last_node_output.get("current_iteration", 0),
                    "metadata": {
                        "planner_version": "1.0",
                        "total_steps": step_count,
                        "thread_id": thread_id,
                    },
                }

                print("\n" + "=" * 80)
                print("✅ PLANNER AGENT COMPLETED")
                print("=" * 80)
                print(f"📋 Task ID: {result['task_id']}")
                print(f"📊 Complexity: {result['complexity_score']}/10")
                print(
                    f"⏱️  Estimated: {result['estimated_hours']} hours ({result['story_points']} SP)"
                )
                print(
                    f"✅ Ready for Implementation: {result['ready_for_implementation']}"
                )
                print(f"📈 Validation Score: {result['validation_score']:.1%}")
                print(f"🔄 Iterations: {result['iterations']}")
                print("=" * 80 + "\n")

                return result
            else:
                raise Exception("No final state received from workflow")

        except Exception as e:
            print(f"\n❌ PLANNER AGENT ERROR: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_plan": {},
                "ready_for_implementation": False,
                "metadata": {
                    "planner_version": "1.0",
                    "thread_id": thread_id,
                    "error_occurred": True,
                },
            }
