"""Product Owner Agent - Deep Agent orchestrator cho workflow PO.

Architecture:
- Deep Agent pattern (deepagents library) với advanced features
- Planning tool: LLM tạo plan trước khi execute
- Virtual file system: Lưu trữ intermediate outputs
- Sub agents với context quarantine
- PO Agent tự reasoning và quyết định gọi tool nào tiếp theo
- Sub agents (Gatherer, Vision, Backlog, Priority) được wrap thành tools
- Human-in-the-loop: Built-in support với tool_configs
"""

import json
import os
from typing import Any, Annotated

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from app.agents.product_owner.gatherer_agent import GathererAgent
from app.agents.product_owner.vision_agent import VisionAgent
from app.agents.product_owner.backlog_agent import BacklogAgent
from app.agents.product_owner.priority_agent import PriorityAgent

# Import prompts for PO Agent
from app.templates.prompts.product_owner.po_agent import SYSTEM_PROMPT

load_dotenv()


class POAgent:
    """Product Owner Agent - Orchestrator sử dụng Deep Agent pattern (deepagents library).

    Workflow:
    1. Thu thập thông tin sản phẩm (GathererAgent tool)
    2. Tạo Product Vision (VisionAgent tool)
    3. Tạo Product Backlog (BacklogAgent tool)
    4. Tạo Sprint Plan (PriorityAgent tool)

    Features (từ deepagents library):
    - Planning Tool: LLM tạo plan trước khi thực thi workflow
    - Virtual File System: Lưu intermediate outputs
    - Sub-agents với context quarantine
    - Built-in human-in-the-loop support
    - LLM tự reasoning và quyết định workflow
    - Tools trả về full data (cho frontend), terminal show summary (Langfuse)
    - State persistence với checkpointer
    """

    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        websocket_broadcast_fn=None,
        project_id: str | None = None,
        response_manager=None,
        event_loop=None
    ):
        """Khởi tạo PO Agent.

        Args:
            session_id: Session ID cho tracking
            user_id: User ID cho tracking
            websocket_broadcast_fn: Async function to broadcast WebSocket messages (optional)
            project_id: Project ID for WebSocket broadcasting (optional)
            response_manager: ResponseManager for human-in-the-loop via WebSocket (optional)
            event_loop: Event loop for async operations (optional)
        """
        self.session_id = session_id or "default_po_session"
        self.user_id = user_id

        # WebSocket dependencies (optional)
        self.websocket_broadcast_fn = websocket_broadcast_fn
        self.project_id = project_id
        self.response_manager = response_manager
        self.event_loop = event_loop

        # Storage for tool results (to extract after streaming)
        self._sprint_plan_result = None

        # Initialize Langfuse callback handler (with batch size limit)
        # Note: session_id and user_id are NOT passed to constructor
        # They should be added via metadata in config when invoking
        # Set flush_at to smaller value to avoid 413 errors with large traces
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,  # Flush every 5 events instead of default (15)
                flush_interval=1.0,  # Flush every 1 second
            )
        except Exception:
            # Fallback if flush_at not supported in this version
            self.langfuse_handler = CallbackHandler()

        # Note: Sub agents are NOT initialized here
        # They will be created on-demand in each tool call with separate Langfuse handlers
        # This ensures each tool call gets its own tracing

        # Build tools
        self.tools = self._build_tools()

        # Create Deep Agent (from deepagents library)
        self.agent = self._build_agent()

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

    def _build_tools(self) -> list:
        """Build tools từ sub agents.

        NOTE: Tools được định nghĩa như nested functions để access self.
        """

        @tool
        def gather_product_info(
            user_input: str,
        ) -> Annotated[dict, "Product Brief với full data"]:
            """Thu thập thông tin sản phẩm từ user, tạo Product Brief.

            Tool này sẽ tương tác với user qua terminal để:
            - Đánh giá độ đầy đủ thông tin
            - Hỏi thêm câu hỏi nếu thiếu thông tin
            - Tạo Product Brief hoàn chỉnh
            - Preview và yêu cầu user approve/edit

            Args:
                user_input: Thông tin ban đầu từ user về sản phẩm (mô tả ý tưởng)

            Returns:
                dict: Product Brief với các trường:
                    - product_name: Tên sản phẩm
                    - description: Mô tả chi tiết
                    - target_audience: Danh sách đối tượng mục tiêu
                    - key_features: Danh sách tính năng chính
                    - benefits: Danh sách lợi ích
                    - competitors: Danh sách đối thủ
                    - completeness_note: Ghi chú về độ hoàn thiện

            Notes:
                - Tool này có human-in-the-loop (preview/approve ở GathererAgent)
                - Trả về full data cho frontend
                - Terminal output được track qua Langfuse
            """
            print("\n" + "=" * 80)
            print("🔧 PO AGENT - Calling Tool: gather_product_info")
            print("=" * 80)
            print(f"📥 Input: {user_input[:100]}...")

            try:
                # Create separate session_id for this tool call to create a new trace
                tool_session_id = f"{self.session_id}_gatherer_tool"

                # Get event loop from self
                event_loop = getattr(self, 'event_loop', None)
                print(f"[Tool Call] event_loop: {event_loop}", flush=True)
                print(f"[Tool Call] websocket_broadcast_fn: {getattr(self, 'websocket_broadcast_fn', None) is not None}", flush=True)
                print(f"[Tool Call] project_id: {getattr(self, 'project_id', None)}", flush=True)
                print(f"[Tool Call] response_manager: {getattr(self, 'response_manager', None) is not None}", flush=True)

                # Create a new GathererAgent instance with separate session_id
                # Pass WebSocket dependencies if available
                gatherer_agent = GathererAgent(
                    session_id=tool_session_id,
                    user_id=self.user_id,
                    websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
                    project_id=getattr(self, 'project_id', None),
                    response_manager=getattr(self, 'response_manager', None),
                    event_loop=event_loop  # Use stored event loop
                )

                print(f"[Tool Call] GathererAgent created, about to call run()...", flush=True)

                # Call GathererAgent - it will create its own trace via its handler
                result = gatherer_agent.run(
                    initial_context=user_input, thread_id=f"{tool_session_id}_thread"
                )

                print(f"[Tool Call] GathererAgent.run() returned!", flush=True)

                # Extract brief from final state
                # Result structure: {node_name: state_data}
                brief = None
                for node_name, state_data in result.items():
                    if isinstance(state_data, dict):
                        brief = state_data.get("brief")
                        if brief:
                            break

                if not brief:
                    raise ValueError("GathererAgent did not return a brief")

                print(f"\n✅ Tool completed - Product Brief created")
                print(f"   Product: {brief.get('product_name', 'N/A')}")
                print(f"   Features: {len(brief.get('key_features', []))}")
                print("=" * 80 + "\n")

                return brief

            except Exception as e:
                print(f"\n❌ Tool error: {e}")
                print("=" * 80 + "\n")
                raise

        @tool
        def create_vision(
            product_brief: dict,
        ) -> Annotated[dict, "Product Vision với PRD full data"]:
            """Tạo Product Vision và PRD từ Product Brief.

            Tool này sẽ:
            - Tạo Vision Statement (solution-free)
            - Định nghĩa Experience Principles
            - Phân tích Problem & Audience Segments
            - Tạo Functional Requirements với acceptance criteria
            - Tạo Non-Functional Requirements (Performance, Security, UX)
            - Preview và yêu cầu user approve/edit

            Args:
                product_brief: Product Brief từ gather_product_info tool

            Returns:
                dict: Product Vision với các trường:
                    - product_name: Tên sản phẩm
                    - vision_statement_final: Vision statement cuối cùng
                    - experience_principles: Nguyên tắc trải nghiệm
                    - problem_summary: Tóm tắt vấn đề
                    - audience_segments: Phân tích đối tượng mục tiêu
                    - scope_capabilities: Khả năng cốt lõi
                    - scope_non_goals: Những gì không làm
                    - functional_requirements: Tính năng cụ thể với AC
                    - performance_requirements: Yêu cầu hiệu năng
                    - security_requirements: Yêu cầu bảo mật
                    - ux_requirements: Yêu cầu UX
                    - dependencies: Phụ thuộc
                    - risks: Rủi ro
                    - assumptions: Giả định

            Notes:
                - Tool này có human-in-the-loop (preview/approve ở VisionAgent)
                - Trả về full data cho frontend
            """
            print("\n" + "=" * 80)
            print("🔧 PO AGENT - Calling Tool: create_vision")
            print("=" * 80)
            print(f"📥 Input Product Brief: {product_brief.get('product_name', 'N/A')}")

            try:
                # Create separate session_id for this tool call to create a new trace
                tool_session_id = f"{self.session_id}_vision_tool"

                # Get WebSocket dependencies (same as GathererAgent)
                event_loop = getattr(self, 'event_loop', None)
                print(f"[Vision Tool Call] event_loop: {event_loop}", flush=True)
                print(f"[Vision Tool Call] websocket_broadcast_fn: {getattr(self, 'websocket_broadcast_fn', None) is not None}", flush=True)
                print(f"[Vision Tool Call] project_id: {getattr(self, 'project_id', None)}", flush=True)
                print(f"[Vision Tool Call] response_manager: {getattr(self, 'response_manager', None) is not None}", flush=True)

                # Create a new VisionAgent instance with separate session_id
                # Pass WebSocket dependencies if available (like GathererAgent)
                vision_agent = VisionAgent(
                    session_id=tool_session_id,
                    user_id=self.user_id,
                    websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
                    project_id=getattr(self, 'project_id', None),
                    response_manager=getattr(self, 'response_manager', None),
                    event_loop=event_loop  # Use stored event loop
                )

                print(f"[Vision Tool Call] VisionAgent created with WebSocket support", flush=True)

                # Call VisionAgent - it will auto-detect WebSocket mode and use websocket_helper
                result = vision_agent.run(
                    product_brief=product_brief, thread_id=f"{tool_session_id}_thread"
                )

                # Extract vision from final state
                vision = None
                for node_name, state_data in result.items():
                    if isinstance(state_data, dict):
                        vision = state_data.get("product_vision")
                        if vision:
                            break

                if not vision:
                    raise ValueError("VisionAgent did not return a vision")

                print(f"\n✅ Tool completed - Product Vision created")
                print(f"   Product: {vision.get('product_name', 'N/A')}")
                print(
                    f"   Vision: {vision.get('vision_statement_final', 'N/A')[:80]}..."
                )
                print(
                    f"   Functional Reqs: {len(vision.get('functional_requirements', []))}"
                )
                print("=" * 80 + "\n")

                return vision

            except Exception as e:
                print(f"\n❌ Tool error: {e}")
                print("=" * 80 + "\n")
                raise

        @tool
        def create_backlog(
            product_vision: dict,
        ) -> Annotated[dict, "Product Backlog với full data"]:
            """Tạo Product Backlog từ Product Vision.

            Tool này sẽ:
            - Tạo Epics, User Stories, Tasks, Sub-tasks
            - Viết User Stories theo INVEST
            - Thêm Acceptance Criteria dạng Gherkin (Given-When-Then)
            - Ước lượng story points và effort
            - Xác định dependencies
            - Đánh giá và refine nếu cần
            - Preview và yêu cầu user approve/edit

            Args:
                product_vision: Product Vision từ create_vision tool

            Returns:
                dict: Product Backlog với cấu trúc:
                    - metadata: Thông tin meta (product_name, version, totals, etc.)
                    - items: Danh sách backlog items:
                        * id: EPIC-001, US-001, TASK-001, SUB-001
                        * type: Epic / User Story / Task / Sub-task
                        * parent_id: ID của parent item
                        * title: Tiêu đề
                        * description: Mô tả chi tiết
                        * acceptance_criteria: Tiêu chí chấp nhận
                        * story_point: Story point (cho User Story)
                        * estimate_value: Giờ ước lượng (cho Task/Sub-task)
                        * dependencies: Dependencies
                        * labels: Labels

            Notes:
                - Tool này có human-in-the-loop (preview/approve ở BacklogAgent)
                - Trả về full data với metadata và items
            """
            print("\n" + "=" * 80)
            print("🔧 PO AGENT - Calling Tool: create_backlog")
            print("=" * 80)
            print(
                f"📥 Input Product Vision: {product_vision.get('product_name', 'N/A')}"
            )

            try:
                # Create separate session_id for this tool call to create a new trace
                tool_session_id = f"{self.session_id}_backlog_tool"

                # Get WebSocket dependencies (same as VisionAgent)
                event_loop = getattr(self, 'event_loop', None)
                print(f"[Backlog Tool Call] event_loop: {event_loop}", flush=True)
                print(f"[Backlog Tool Call] websocket_broadcast_fn: {getattr(self, 'websocket_broadcast_fn', None) is not None}", flush=True)
                print(f"[Backlog Tool Call] project_id: {getattr(self, 'project_id', None)}", flush=True)
                print(f"[Backlog Tool Call] response_manager: {getattr(self, 'response_manager', None) is not None}", flush=True)

                # Create a new BacklogAgent instance with separate session_id
                # Pass WebSocket dependencies if available (like VisionAgent)
                backlog_agent = BacklogAgent(
                    session_id=tool_session_id,
                    user_id=self.user_id,
                    websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
                    project_id=getattr(self, 'project_id', None),
                    response_manager=getattr(self, 'response_manager', None),
                    event_loop=event_loop  # Use stored event loop
                )

                print(f"[Backlog Tool Call] BacklogAgent created with WebSocket support", flush=True)

                # Call BacklogAgent - it will auto-detect WebSocket mode and use websocket_helper
                result = backlog_agent.run(
                    product_vision=product_vision, thread_id=f"{tool_session_id}_thread"
                )

                # Extract backlog from final state
                backlog = None
                for node_name, state_data in result.items():
                    if isinstance(state_data, dict):
                        backlog = state_data.get("product_backlog")
                        if backlog:
                            break

                if not backlog:
                    raise ValueError("BacklogAgent did not return a backlog")

                metadata = backlog.get("metadata", {})
                print(f"\n✅ Tool completed - Product Backlog created")
                print(f"   Product: {metadata.get('product_name', 'N/A')}")
                print(f"   Total Items: {metadata.get('total_items', 0)}")
                print(f"   Epics: {metadata.get('total_epics', 0)}")
                print(f"   User Stories: {metadata.get('total_user_stories', 0)}")
                print(f"   Tasks: {metadata.get('total_tasks', 0)}")
                print("=" * 80 + "\n")

                return backlog

            except Exception as e:
                print(f"\n❌ Tool error: {e}")
                print("=" * 80 + "\n")
                raise

        @tool
        def create_sprint_plan(
            product_backlog: dict,
        ) -> Annotated[dict, "Sprint Plan với full data"]:
            """Tạo Sprint Plan từ Product Backlog.

            Tool này sẽ:
            - Tính WSJF (Weighted Shortest Job First) cho prioritization
            - Rank items theo WSJF score
            - Pack items vào sprints với capacity planning
            - Xử lý dependencies giữa items
            - Đánh giá và refine sprint plan
            - Preview và yêu cầu user approve/edit/reprioritize

            Args:
                product_backlog: Product Backlog từ create_backlog tool

            Returns:
                dict: Sprint Plan với cấu trúc:
                    - metadata: Thông tin meta (product_name, sprint config, totals, etc.)
                    - prioritized_backlog: Backlog items đã được rank theo WSJF
                    - wsjf_calculations: Chi tiết WSJF calculations cho từng item
                    - sprints: Danh sách sprints:
                        * sprint_id: sprint-1, sprint-2, ...
                        * sprint_number: Số thứ tự
                        * sprint_goal: Mục tiêu sprint
                        * start_date, end_date: Ngày bắt đầu/kết thúc
                        * velocity_plan: Story points planned
                        * assigned_items: IDs của items được assign
                        * status: Planned / Active / Completed
                    - unassigned_items: Items chưa được assign (nếu có)

            Notes:
                - Tool này có human-in-the-loop (preview/approve ở PriorityAgent)
                - Trả về full data với metadata, prioritized backlog, và sprints
            """
            print("\n" + "=" * 80)
            print("🔧 PO AGENT - Calling Tool: create_sprint_plan")
            print("=" * 80)

            metadata = product_backlog.get("metadata", {})
            print(f"📥 Input Product Backlog: {metadata.get('product_name', 'N/A')}")
            print(f"   Total Items: {metadata.get('total_items', 0)}")

            try:
                # Create separate session_id for this tool call to create a new trace
                tool_session_id = f"{self.session_id}_priority_tool"

                # Get WebSocket dependencies (same as VisionAgent)
                event_loop = getattr(self, 'event_loop', None)
                print(f"[Priority Tool Call] event_loop: {event_loop}", flush=True)
                print(f"[Priority Tool Call] websocket_broadcast_fn: {getattr(self, 'websocket_broadcast_fn', None) is not None}", flush=True)
                print(f"[Priority Tool Call] project_id: {getattr(self, 'project_id', None)}", flush=True)
                print(f"[Priority Tool Call] response_manager: {getattr(self, 'response_manager', None) is not None}", flush=True)

                # Create a new PriorityAgent instance with separate session_id
                # Pass WebSocket dependencies if available (like VisionAgent)
                priority_agent = PriorityAgent(
                    session_id=tool_session_id,
                    user_id=self.user_id,
                    websocket_broadcast_fn=getattr(self, 'websocket_broadcast_fn', None),
                    project_id=getattr(self, 'project_id', None),
                    response_manager=getattr(self, 'response_manager', None),
                    event_loop=event_loop  # Use stored event loop
                )

                print(f"[Priority Tool Call] PriorityAgent created with WebSocket support", flush=True)

                # Call PriorityAgent - it will auto-detect WebSocket mode and use websocket_helper
                sprint_plan = priority_agent.run(
                    product_backlog=product_backlog,
                    thread_id=f"{tool_session_id}_thread",
                )

                if not sprint_plan:
                    raise ValueError("PriorityAgent did not return a sprint plan")

                sp_metadata = sprint_plan.get("metadata", {})
                print(f"\n✅ Tool completed - Sprint Plan created")
                print(f"   Product: {sp_metadata.get('product_name', 'N/A')}")
                print(f"   Total Sprints: {sp_metadata.get('total_sprints', 0)}")
                print(
                    f"   Total Items Assigned: {sp_metadata.get('total_items_assigned', 0)}"
                )
                print(
                    f"   Total Story Points: {sp_metadata.get('total_story_points', 0)}"
                )
                print("=" * 80 + "\n")

                # Save sprint_plan to PO Agent instance for later extraction
                self._sprint_plan_result = sprint_plan
                print(f"[Priority Tool] Saved sprint_plan to PO Agent instance")

                return sprint_plan

            except Exception as e:
                print(f"\n❌ Tool error: {e}")
                print("=" * 80 + "\n")
                raise

        return [
            gather_product_info,
            create_vision,
            create_backlog,
            create_sprint_plan,
        ]

    def _build_agent(self):
        """Build Deep Agent với tools và system instructions."""
        return create_deep_agent(
            tools=self.tools,
            model=self._llm("gpt-4o", 0.2),
            # model=self._llm("claude-sonnet-4-5", 0.2),
            system_prompt=SYSTEM_PROMPT,
        )

    def _is_product_idea_intent(self, text: str) -> bool:
        """Detect if user intends to describe a product idea.

        Returns True if user is describing a product idea (not just greeting).
        This triggers Gatherer Agent to collect requirements.
        """
        t = (text or "").lower().strip()

        # Greeting keywords that should NOT trigger product gathering
        greeting_keywords = {
            "bắt đầu", "bat dau", "start", "hi", "hello",
            "chào", "chao", "xin chào", "xin chao"
        }

        # If it's just a greeting, return False
        if t in greeting_keywords:
            return False

        # Product idea keywords that should trigger Gatherer Agent
        product_keywords = [
            "tao", "tạo",  # create
            "xay dung", "xây dựng",  # build
            "lam", "làm",  # make
            "phat trien", "phát triển",  # develop
            "app", "ung dung", "ứng dụng",  # application
            "website", "trang web", "web",  # website
            "san pham", "sản phẩm",  # product
            "dich vu", "dịch vụ",  # service
            "he thong", "hệ thống",  # system
            "platform", "nen tang",  # platform
            "tool", "cong cu",  # tool
            "phan mem", "phần mềm",  # software
        ]

        # If text contains any product-related keyword, it's likely a product idea
        return any(k in t for k in product_keywords)

    async def _trigger_scrum_master_orchestrator(
        self,
        sprint_plan: dict,
        backlog_items: list[dict],
        websocket_broadcast_fn,
        project_id: str
    ) -> None:
        """Trigger Scrum Master Orchestrator sau khi PO Agent hoàn thành.

        Args:
            sprint_plan: Sprint plan từ Priority Agent
            backlog_items: Backlog items từ Priority Agent
            websocket_broadcast_fn: Function để broadcast qua WebSocket
            project_id: Project ID
        """
        try:
            from app.agents.scrum_master.orchestrator import ScrumMasterOrchestrator

            # Create orchestrator
            orchestrator = ScrumMasterOrchestrator(
                project_id=project_id,
                user_id=self.user_id or "unknown",
                session_id=self.session_id,
                websocket_broadcast_fn=websocket_broadcast_fn
            )

            # Process PO output
            result = await orchestrator.process_po_output(
                sprint_plan=sprint_plan,
                backlog_items=backlog_items
            )

            print(f"[PO Agent] Scrum Master Orchestrator completed: {result.get('total_sprints', 0)} sprints, {result.get('total_items', 0)} items")

        except Exception as e:
            print(f"[PO Agent] Error triggering Scrum Master Orchestrator: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - PO Agent should still complete successfully

    def _needs_kickoff_only(self, user_input: str) -> bool:
        """Return True if we should only greet and ask for more info (no tools)."""
        text = (user_input or "").strip().lower()
        # Only block on explicit greeting keywords, not on length
        # This allows short but meaningful inputs like "Tạo website" to trigger full workflow
        if text in {"bắt đầu", "bat dau", "start", "hi", "hello", "chào", "chao", "xin chào", "xin chao"}:
            return True
        # Removed: length check that was blocking short but valid inputs
        # Old logic: return len(text) < 20
        return False

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
        # Store dependencies for tool access
        self.websocket_broadcast_fn = websocket_broadcast_fn
        self.project_id = project_id
        self.response_manager = response_manager

        # Store event loop for tools that need async operations
        import asyncio
        try:
            # Try to get the currently running loop (preferred)
            self.event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback to get_event_loop (might return None or a new loop)
            self.event_loop = asyncio.get_event_loop()

        if thread_id is None:
            thread_id = self.session_id

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50,
        }

        try:
            # Reset sprint_plan result from previous runs
            self._sprint_plan_result = None

            final_result = None
            step_count = 0

            # Check if user is describing a product idea (not just greeting)
            # If so, let Deep Agent handle the full workflow (Gatherer -> Vision -> Backlog -> Priority)
            # Don't bypass it by calling Gatherer directly
            if not self._is_product_idea_intent(user_input):
                # Not a product idea, check if it's just a greeting
                if self._needs_kickoff_only(user_input):
                    greeting = (
                        "Chào bạn! Tôi là Product Owner Agent (PO Agent). "
                        "Tôi có thể giúp lập kế hoạch và tạo Sprint Plan từ ý tưởng sản phẩm. "
                        "Quy trình: Gatherer -> Vision -> Backlog -> Priority. "
                        "Vui lòng mô tả ý tưởng để bắt đầu."
                    )
                    return {"messages": [{"type": "assistant", "content": greeting}]}

            # Full execution path - product idea detected, run Deep Agent workflow
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "started",
                "agent": "PO Agent",
                "message": "🚀 PO Agent bắt đầu xử lý..."
            }, project_id)

            final_result = {}

            async for chunk in self.agent.astream(
                {"messages": [("user", user_input)]},
                config=config,
                stream_mode="updates"
            ):
                step_count += 1

                # Stream each chunk to WebSocket
                if isinstance(chunk, dict):
                    for node_name, node_data in chunk.items():
                        # Save latest node_data as final_result
                        if isinstance(node_data, dict):
                            final_result = node_data

                        # Broadcast node execution
                        await websocket_broadcast_fn({
                            "type": "agent_step",
                            "step": "executing",
                            "node": node_name,
                            "step_number": step_count
                        }, project_id)

                        if isinstance(node_data, dict):
                            messages = node_data.get("messages", [])
                            if messages:
                                last_msg = messages[-1] if isinstance(messages, list) else messages

                                # Check for tool calls
                                if hasattr(last_msg, "tool_calls"):
                                    tool_calls = last_msg.tool_calls
                                    if tool_calls:
                                        for tc in tool_calls:
                                            tool_name = tc.get('name', 'unknown')
                                            # Map tool names to friendly names
                                            agent_names = {
                                                "gatherer_agent_tool": "Gatherer Agent - Thu thập thông tin",
                                                "vision_agent_tool": "Vision Agent - Tạo tài liệu tầm nhìn",
                                                "backlog_agent_tool": "Backlog Agent - Tạo Product Backlog",
                                                "priority_agent_tool": "Priority Agent - Ưu tiên & tạo Sprint Plan"
                                            }
                                            friendly_name = agent_names.get(tool_name, tool_name)

                                            await websocket_broadcast_fn({
                                                "type": "tool_call",
                                                "tool": tool_name,
                                                "display_name": friendly_name
                                            }, project_id)
                                    else:
                                        # AI response without tool calls
                                        if hasattr(last_msg, "content"):
                                            content = last_msg.content
                                            if content and len(content.strip()) > 0:
                                                await websocket_broadcast_fn({
                                                    "type": "agent_thinking",
                                                    "content": content
                                                }, project_id)
                                elif hasattr(last_msg, "content"):
                                    content = last_msg.content
                                    if content and len(content.strip()) > 0:
                                        await websocket_broadcast_fn({
                                            "type": "agent_thinking",
                                            "content": content
                                        }, project_id)

            print("\n[PO Agent] Stream completed, extracting sprint_plan from messages...")
            print(f"   final_result type: {type(final_result)}")
            print(f"   final_result keys: {list(final_result.keys()) if isinstance(final_result, dict) else 'N/A'}")

            # Send completion
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "completed",
                "agent": "PO Agent",
                "message": f"✅ Hoàn thành! Đã thực hiện {step_count} bước."
            }, project_id)

            # Extract sprint plan from tool result saved in instance
            sprint_plan_data = None
            backlog_items = []

            print("\n[PO Agent] Extracting sprint plan from tool result...")

            # Check if Priority Agent tool was called and saved result
            if self._sprint_plan_result:
                sprint_plan_data = self._sprint_plan_result
                print(f"   ✅ Found sprint_plan from Priority Agent tool")
                print(f"   sprint_plan_data type: {type(sprint_plan_data)}")

                if sprint_plan_data and isinstance(sprint_plan_data, dict):
                    backlog_items = sprint_plan_data.get("prioritized_backlog", [])
                    print(f"   backlog_items count: {len(backlog_items)}")
                    print(f"   sprints count: {len(sprint_plan_data.get('sprints', []))}")
            else:
                print(f"   ⚠️ sprint_plan_data not found - Priority Agent tool may not have been called")

            # Trigger Scrum Master Orchestrator if we have sprint plan
            if sprint_plan_data and backlog_items:
                print("\n[PO Agent] ✅ Triggering Scrum Master Orchestrator...")
                print(f"   Sprint Plan: {len(sprint_plan_data.get('sprints', []))} sprints")
                print(f"   Backlog Items: {len(backlog_items)} items")

                await self._trigger_scrum_master_orchestrator(
                    sprint_plan=sprint_plan_data,
                    backlog_items=backlog_items,
                    websocket_broadcast_fn=websocket_broadcast_fn,
                    project_id=project_id
                )
            else:
                print("\n[PO Agent] ⚠️ NOT triggering Scrum Master - missing data:")
                print(f"   sprint_plan_data: {sprint_plan_data is not None}")
                print(f"   backlog_items: {len(backlog_items) if backlog_items else 0}")

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
        """Run PO Agent workflow.

        Args:
            user_input: Ý tưởng sản phẩm hoặc yêu cầu từ user
            thread_id: Thread ID cho checkpointer (để resume)

        Returns:
            dict: Final state với messages và outputs
        """
        # Check if WebSocket mode is enabled
        if self.websocket_broadcast_fn and self.project_id and self.response_manager:
            print(f"[POAgent.run] WebSocket mode detected - using websocket_helper", flush=True)

            # Import websocket helper
            from app.core.websocket_helper import websocket_helper

            # Run async version in dedicated WebSocket loop
            print(f"[POAgent.run] Scheduling in WebSocket helper loop...", flush=True)
            result = websocket_helper.run_coroutine(
                self.run_with_streaming(
                    user_input=user_input,
                    websocket_broadcast_fn=self.websocket_broadcast_fn,
                    project_id=self.project_id,
                    response_manager=self.response_manager,
                    thread_id=thread_id
                ),
                timeout=660  # 11 minutes
            )
            print(f"[POAgent.run] Execution completed!", flush=True)
            return result

        # Terminal mode: sync execution
        print(f"[POAgent.run] Terminal mode - sync execution", flush=True)

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
            # Stream agent execution để xem từng bước
            print("📡 Streaming agent execution...\n")

            final_result = None
            step_count = 0

            # Check if user is describing a product idea (not just greeting)
            # If so, let Deep Agent handle the full workflow (Gatherer -> Vision -> Backlog -> Priority)
            # Don't bypass it by calling Gatherer directly
            if not self._is_product_idea_intent(user_input):
                # Not a product idea, check if it's just a greeting
                if self._needs_kickoff_only(user_input):
                    greeting = (
                        "Chào bạn! Tôi là Product Owner Agent (PO Agent). "
                        "Tôi có thể giúp lập kế hoạch và tạo Sprint Plan từ ý tưởng sản phẩm. "
                        "Quy trình: Gatherer -> Vision -> Backlog -> Priority. "
                        "Vui lòng mô tả ý tưởng để bắt đầu."
                    )
                    return {"messages": [{"type": "assistant", "content": greeting}]}

            # Product idea detected, run Deep Agent workflow
            for chunk in self.agent.stream(
                {"messages": [("user", user_input)]},
                config=config,
                stream_mode="updates",
            ):
                step_count += 1
                print(f"\n{'='*80}")
                print(f"📍 STEP {step_count}")
                print(f"{'='*80}")

                # Log chunk structure
                if isinstance(chunk, dict):
                    for node_name, node_data in chunk.items():
                        print(f"🔹 Node: {node_name}")

                        if isinstance(node_data, dict):
                            # Check for messages
                            messages = node_data.get("messages", [])
                            if messages:
                                last_msg = (
                                    messages[-1]
                                    if isinstance(messages, list)
                                    else messages
                                )
                                print(f"   Type: {type(last_msg).__name__}")

                                # Check if AI message with tool calls
                                if hasattr(last_msg, "tool_calls"):
                                    tool_calls = last_msg.tool_calls
                                    if tool_calls:
                                        print(f"   🔧 Tool Calls: {len(tool_calls)}")
                                        for tc in tool_calls:
                                            print(
                                                f"      - {tc.get('name', 'unknown')}"
                                            )
                                    else:
                                        print(f"   💬 AI Response (no tool calls)")
                                        if hasattr(last_msg, "content"):
                                            content = last_msg.content
                                            print(f"      Content: {content[:150]}...")
                                elif hasattr(last_msg, "content"):
                                    content = last_msg.content
                                    print(f"   📝 Content: {content[:150]}...")

                        final_result = node_data

                print(f"{'='*80}\n")

            print("\n" + "=" * 80)
            print("✅ PO AGENT COMPLETED")
            print("=" * 80)
            print(f"📊 Total Steps: {step_count}")
            if final_result and isinstance(final_result, dict):
                messages = final_result.get("messages", [])
                print(f"💬 Total Messages: {len(messages)}")
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
