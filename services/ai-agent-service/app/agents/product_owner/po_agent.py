"""Product Owner Agent - LangGraph orchestrator cho workflow PO.

Architecture:
- LangGraph pattern với state management
- LLM-driven routing: LLM quyết định sub-agent nào cần gọi tiếp theo
- Sub agents (Gatherer, Vision, Backlog, Priority) được gọi như nodes
- Human-in-the-loop: Built-in support trong sub-agents
- State persistence với checkpointer
"""

import json
import os
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.product_owner.gatherer_agent import GathererAgent
from app.agents.product_owner.vision_agent import VisionAgent
from app.agents.product_owner.backlog_agent import BacklogAgent
from app.agents.product_owner.priority_agent import PriorityAgent

# Import prompts for PO Agent
from app.templates.prompts.product_owner.po_agent import SYSTEM_PROMPT, ROUTER_PROMPT

load_dotenv()


class RouterDecision(BaseModel):
    """Decision from router node."""
    next_agent: Literal["gatherer", "vision", "backlog", "priority", "finalize"] = Field(
        description="Next agent to call"
    )
    reasoning: str = Field(description="Why this agent should be called next")


class POAgentState(BaseModel):
    """State for PO Agent workflow."""

    # Messages and input
    messages: list[BaseMessage] = Field(default_factory=list)
    user_input: str = ""

    # Outputs from sub-agents
    product_brief: dict = Field(default_factory=dict)
    product_vision: dict = Field(default_factory=dict)
    product_backlog: dict = Field(default_factory=dict)
    sprint_plan: dict = Field(default_factory=dict)

    # Control flow
    current_step: str = "initial"
    status: str = "pending"

    # Kickoff logic
    is_website_intent: bool = False
    needs_kickoff_only: bool = False


class POAgent:
    """Product Owner Agent - Orchestrator sử dụng LangGraph pattern.

    Workflow:
    1. Thu thập thông tin sản phẩm (GathererAgent node)
    2. Tạo Product Vision (VisionAgent node)
    3. Tạo Product Backlog (BacklogAgent node)
    4. Tạo Sprint Plan (PriorityAgent node)

    Features:
    - LangGraph state management
    - LLM-driven routing: LLM quyết định sub-agent nào cần gọi tiếp theo
    - Sub-agents được gọi như nodes
    - Human-in-the-loop support trong sub-agents
    - State persistence với checkpointer
    """

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo PO Agent.

        Args:
            session_id: Session ID cho tracking
            user_id: User ID cho tracking
        """
        self.session_id = session_id or "default_po_session"
        self.user_id = user_id

        # Initialize Langfuse callback handler (with batch size limit)
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,
                flush_interval=1.0,
            )
        except Exception:
            self.langfuse_handler = CallbackHandler()

        # Build LangGraph
        self.graph = self._build_graph()

    def _llm(self, model: str, temperature: float) -> ChatOpenAI:
        """Initialize LLM instance."""
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
            return llm
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {e}")

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph_builder = StateGraph(POAgentState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("router", self.router)
        graph_builder.add_node("run_gatherer", self.run_gatherer)
        graph_builder.add_node("run_vision", self.run_vision)
        graph_builder.add_node("run_backlog", self.run_backlog)
        graph_builder.add_node("run_priority", self.run_priority)
        graph_builder.add_node("finalize", self.finalize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_conditional_edges("initialize", self.initialize_branch)
        graph_builder.add_conditional_edges("router", self.router_branch)
        graph_builder.add_edge("run_gatherer", "router")
        graph_builder.add_edge("run_vision", "router")
        graph_builder.add_edge("run_backlog", "router")
        graph_builder.add_edge("run_priority", "router")
        graph_builder.add_edge("finalize", END)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Nodes
    # ========================================================================

    def initialize(self, state: POAgentState) -> POAgentState:
        """Initialize - Xử lý kickoff logic và chuẩn bị state."""
        print("\n" + "=" * 80)
        print("🚀 INITIALIZE - PO AGENT")
        print("=" * 80)
        print(f"📝 User Input: {state.user_input[:200]}...")
        print("=" * 80 + "\n")

        # Check kickoff logic
        state.needs_kickoff_only = self._needs_kickoff_only(state.user_input)
        state.is_website_intent = self._is_website_intent(state.user_input)

        # Add user input to messages
        if state.user_input:
            state.messages.append(HumanMessage(content=state.user_input))

        state.status = "initialized"
        return state

    def router(self, state: POAgentState) -> POAgentState:
        """Router - LLM quyết định sub-agent nào cần gọi tiếp theo."""
        print("\n" + "=" * 80)
        print("🔀 ROUTER - DECIDING NEXT AGENT")
        print("=" * 80)

        # Prepare context for LLM
        context = {
            "current_step": state.current_step,
            "has_product_brief": bool(state.product_brief),
            "has_product_vision": bool(state.product_vision),
            "has_product_backlog": bool(state.product_backlog),
            "has_sprint_plan": bool(state.sprint_plan),
        }

        context_text = json.dumps(context, ensure_ascii=False, indent=2)
        prompt = ROUTER_PROMPT.format(context=context_text)

        try:
            structured_llm = self._llm("gpt-4o", 0.2).with_structured_output(RouterDecision)
            decision = structured_llm.invoke([HumanMessage(content=prompt)])

            state.current_step = decision.next_agent

            print(f"✓ Decision: {decision.next_agent}")
            print(f"  Reasoning: {decision.reasoning}")
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ Router error: {e}")
            # Fallback logic
            if not state.product_brief:
                state.current_step = "gatherer"
            elif not state.product_vision:
                state.current_step = "vision"
            elif not state.product_backlog:
                state.current_step = "backlog"
            elif not state.sprint_plan:
                state.current_step = "priority"
            else:
                state.current_step = "finalize"

        return state

    async def run_gatherer(self, state: POAgentState) -> POAgentState:
        """Run Gatherer Agent."""
        print("\n" + "=" * 80)
        print("🔧 RUNNING GATHERER AGENT")
        print("=" * 80)

        tool_session_id = f"{self.session_id}_gatherer"

        gatherer_agent = GathererAgent(
            session_id=tool_session_id,
            user_id=self.user_id,
            websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
            project_id=getattr(self, 'project_id', None),
            response_manager=getattr(self, 'response_manager', None),
            event_loop=getattr(self, 'event_loop', None)
        )

        result = await gatherer_agent.run_async(
            initial_context=state.user_input,
            thread_id=f"{tool_session_id}_thread"
        )

        # Extract brief from result
        brief = None
        for node_name, state_data in result.items():
            if isinstance(state_data, dict):
                brief = state_data.get("brief")
                if brief:
                    break

        if brief:
            state.product_brief = brief
            print(f"✅ Gatherer completed - Product Brief created")
        else:
            print(f"⚠️ Gatherer completed but no brief returned")

        print("=" * 80 + "\n")
        return state

    async def run_vision(self, state: POAgentState) -> POAgentState:
        """Run Vision Agent."""
        print("\n" + "=" * 80)
        print("🔧 RUNNING VISION AGENT")
        print("=" * 80)

        tool_session_id = f"{self.session_id}_vision"

        vision_agent = VisionAgent(
            session_id=tool_session_id,
            user_id=self.user_id,
            websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
            project_id=getattr(self, 'project_id', None),
            response_manager=getattr(self, 'response_manager', None),
            event_loop=getattr(self, 'event_loop', None)
        )

        result = await vision_agent.run_async(
            product_brief=state.product_brief,
            thread_id=f"{tool_session_id}_thread"
        )

        # Extract vision from result
        vision = None
        for node_name, state_data in result.items():
            if isinstance(state_data, dict):
                vision = state_data.get("product_vision")
                if vision:
                    break

        if vision:
            state.product_vision = vision
            print(f"✅ Vision completed - Product Vision created")
        else:
            print(f"⚠️ Vision completed but no vision returned")

        print("=" * 80 + "\n")
        return state

    async def run_backlog(self, state: POAgentState) -> POAgentState:
        """Run Backlog Agent."""
        print("\n" + "=" * 80)
        print("🔧 RUNNING BACKLOG AGENT")
        print("=" * 80)

        tool_session_id = f"{self.session_id}_backlog"

        backlog_agent = BacklogAgent(
            session_id=tool_session_id,
            user_id=self.user_id,
            websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
            project_id=getattr(self, 'project_id', None),
            response_manager=getattr(self, 'response_manager', None),
            event_loop=getattr(self, 'event_loop', None)
        )

        result = await backlog_agent.run_async(
            product_vision=state.product_vision,
            thread_id=f"{tool_session_id}_thread"
        )

        # Extract backlog from result
        backlog = None
        for node_name, state_data in result.items():
            if isinstance(state_data, dict):
                backlog = state_data.get("product_backlog")
                if backlog:
                    break

        if backlog:
            state.product_backlog = backlog
            print(f"✅ Backlog completed - Product Backlog created")
        else:
            print(f"⚠️ Backlog completed but no backlog returned")

        print("=" * 80 + "\n")
        return state

    async def run_priority(self, state: POAgentState) -> POAgentState:
        """Run Priority Agent."""
        print("\n" + "=" * 80)
        print("🔧 RUNNING PRIORITY AGENT")
        print("=" * 80)

        tool_session_id = f"{self.session_id}_priority"

        priority_agent = PriorityAgent(
            session_id=tool_session_id,
            user_id=self.user_id,
            websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
            project_id=getattr(self, 'project_id', None),
            response_manager=getattr(self, 'response_manager', None),
            event_loop=getattr(self, 'event_loop', None)
        )

        result = await priority_agent.run_async(
            product_backlog=state.product_backlog,
            thread_id=f"{tool_session_id}_thread"
        )

        # Extract sprint_plan from result
        sprint_plan = result if isinstance(result, dict) and "metadata" in result else None

        if sprint_plan:
            state.sprint_plan = sprint_plan
            print(f"✅ Priority completed - Sprint Plan created")
        else:
            print(f"⚠️ Priority completed but no sprint plan returned")

        print("=" * 80 + "\n")
        return state

    def finalize(self, state: POAgentState) -> POAgentState:
        """Finalize - Hoàn tất workflow."""
        print("\n" + "=" * 80)
        print("✅ FINALIZE - WORKFLOW COMPLETED")
        print("=" * 80)
        print(f"✓ Product Brief: {'✅' if state.product_brief else '❌'}")
        print(f"✓ Product Vision: {'✅' if state.product_vision else '❌'}")
        print(f"✓ Product Backlog: {'✅' if state.product_backlog else '❌'}")
        print(f"✓ Sprint Plan: {'✅' if state.sprint_plan else '❌'}")
        print("=" * 80 + "\n")

        state.status = "completed"
        return state

    # ========================================================================
    # Conditional Branches
    # ========================================================================

    def initialize_branch(self, state: POAgentState) -> str:
        """Branch after initialize."""
        if state.needs_kickoff_only and not state.is_website_intent:
            # Just greeting, return finalize to end
            return "finalize"
        else:
            # Start workflow with router
            return "router"

    def router_branch(self, state: POAgentState) -> str:
        """Branch after router."""
        return f"run_{state.current_step}" if state.current_step != "finalize" else "finalize"

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _is_website_intent(self, text: str) -> bool:
        """Detect if user intends to create a website/web app."""
        t = (text or "").lower()
        keywords = [
            "tao trang web", "tạo trang web", "trang web", "website", "web app",
            "xay dung website", "xây dựng website", "lam website", "làm website",
            "xay dung trang web", "xây dựng trang web", "phat trien website",
            "phát triển website",
        ]
        return any(k in t for k in keywords)

    def _needs_kickoff_only(self, user_input: str) -> bool:
        """Return True if we should only greet and ask for more info (no tools)."""
        text = (user_input or "").strip().lower()
        if text in {"bắt đầu", "bat dau", "start", "hi", "hello", "chào", "chao", "xin chào", "xin chao"}:
            return True
        return False

    # ========================================================================
    # Run Methods
    # ========================================================================

    async def run_with_streaming(
        self,
        user_input: str,
        websocket_broadcast_fn,
        project_id: str,
        response_manager,
        thread_id: str | None = None
    ) -> dict[str, Any]:
        """Run PO Agent workflow with WebSocket streaming.

        Args:
            user_input: Ý tưởng sản phẩm hoặc yêu cầu từ user
            websocket_broadcast_fn: Async function to broadcast messages
            project_id: Project ID for broadcasting
            response_manager: ResponseManager instance for human-in-the-loop
            thread_id: Thread ID cho checkpointer (để resume)

        Returns:
            dict: Final state với messages và outputs
        """
        # Store dependencies for node access
        self.websocket_broadcast_fn = websocket_broadcast_fn
        self.project_id = project_id
        self.response_manager = response_manager

        # Store event loop for nodes that need async operations
        import asyncio
        try:
            self.event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self.event_loop = asyncio.get_event_loop()

        if thread_id is None:
            thread_id = self.session_id

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50,
        }

        try:
            # Send start indicator
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "started",
                "agent": "PO Agent",
                "message": "🚀 PO Agent bắt đầu xử lý..."
            }, project_id)

            # Create initial state
            initial_state = POAgentState(user_input=user_input)

            final_result = None
            step_count = 0

            # Stream graph execution
            async for chunk in self.graph.astream(
                initial_state.model_dump(),
                config=config,
                stream_mode="updates"
            ):
                step_count += 1

                # Stream each chunk to WebSocket
                if isinstance(chunk, dict):
                    for node_name, node_data in chunk.items():
                        # Broadcast node execution
                        await websocket_broadcast_fn({
                            "type": "agent_step",
                            "step": "executing",
                            "node": node_name,
                            "step_number": step_count
                        }, project_id)

                        final_result = node_data

            # Send completion
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "completed",
                "agent": "PO Agent",
                "message": f"✅ Hoàn thành! Đã thực hiện {step_count} bước."
            }, project_id)

            return final_result or {}

        except Exception as e:
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "error",
                "agent": "PO Agent",
                "message": f"❌ Lỗi: {str(e)}"
            }, project_id)
            raise

    def run(self, user_input: str, thread_id: str | None = None) -> dict[str, Any]:
        """Run PO Agent workflow (sync version for terminal).

        Args:
            user_input: Ý tưởng sản phẩm hoặc yêu cầu từ user
            thread_id: Thread ID cho checkpointer (để resume)

        Returns:
            dict: Final state với messages và outputs
        """
        if thread_id is None:
            thread_id = self.session_id

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50,
        }

        print("\n" + "=" * 80)
        print("🚀 PO AGENT STARTED")
        print("=" * 80)
        print(f"📝 User Input: {user_input[:200]}...")
        print(f"🔗 Thread ID: {thread_id}")
        print("=" * 80 + "\n")

        try:
            # Create initial state
            initial_state = POAgentState(user_input=user_input)

            final_result = None
            step_count = 0

            # Stream graph execution
            for chunk in self.graph.stream(
                initial_state.model_dump(),
                config=config,
                stream_mode="updates",
            ):
                step_count += 1
                print(f"\n{'='*80}")
                print(f"📍 STEP {step_count}")
                print(f"{'='*80}")

                if isinstance(chunk, dict):
                    for node_name, node_data in chunk.items():
                        print(f"🔹 Node: {node_name}")
                        final_result = node_data

                print(f"{'='*80}\n")

            print("\n" + "=" * 80)
            print("✅ PO AGENT COMPLETED")
            print("=" * 80)
            print(f"📊 Total Steps: {step_count}")
            print("=" * 80 + "\n")

            return final_result or {}

        except Exception as e:
            print("\n" + "=" * 80)
            print("❌ PO AGENT ERROR")
            print("=" * 80)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("=" * 80 + "\n")
            raise


# Example usage (for testing)
if __name__ == "__main__":
    # Test PO Agent
    po_agent = POAgent(session_id="test_session", user_id="test_user")

    user_input = """
    Tôi muốn tạo một ứng dụng quản lý công việc cá nhân (Todo App).
    Ứng dụng này giúp người dùng:
    - Tạo và quản lý tasks
    - Sắp xếp tasks theo priority
    - Set reminders cho tasks
    - Track progress

    Target audience: Professionals và students muốn quản lý công việc hiệu quả.
    """

    result = po_agent.run(user_input)

    print("\n📊 FINAL RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
