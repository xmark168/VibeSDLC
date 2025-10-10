import json
import os
import re
from typing import Any, Literal, Optional
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from templates.prompts.product_owner.backlog import (
    INITIALIZE_PROMPT,
    GENERATE_PROMPT,
    EVALUATE_PROMPT,
    REFINE_PROMPT,
    FINALIZE_PROMPT,
)

from langgraph.checkpoint.memory import MemorySaver


load_dotenv()

# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class InitializeOutput(BaseModel):
    """Structured output từ initialize node."""
    validation_status: Literal["complete", "incomplete", "missing_critical"] = Field(
        description="Trạng thái validation của Product Vision"
    )
    readiness_score: float = Field(
        description="Điểm readiness từ 0.0-1.0",
        ge=0.0,
        le=1.0
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="Danh sách thông tin còn thiếu"
    )
    key_capabilities: list[str] = Field(
        default_factory=list,
        description="Khả năng cốt lõi trích xuất từ vision"
    )
    dependency_map: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping dependencies giữa requirements"
    )
    estimated_items: dict[str, int] = Field(
        default_factory=dict,
        description="Ước lượng số items: {epics, user_stories, tasks}"
    )


class BacklogItem(BaseModel):
    """Model cho một backlog item."""
    id: str = Field(description="ID: EPIC-001, US-001, TASK-001")
    type: Literal["Epic", "User Story", "Task"] = Field(description="Loại item")
    parent_id: Optional[str] = Field(default=None, description="ID của parent item")
    title: str = Field(description="Tiêu đề item")
    description: str = Field(description="Mô tả chi tiết")
    priority: Literal["High", "Medium", "Low", "Not Set"] = Field(default="Not Set")
    status: Literal["Backlog", "Ready", "In Progress", "Done"] = Field(default="Backlog")
    story_points: Optional[int] = Field(default=None, description="CHỈ cho User Story")
    estimated_hours: Optional[float] = Field(default=None, description="CHỈ cho Task")
    acceptance_criteria: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    task_type: Optional[str] = Field(default=None, description="CHỈ cho Task")
    business_value: Optional[str] = Field(default=None, description="Cho Epic và User Story, null cho Task")
    wsjf_inputs: dict = Field(default_factory=dict, description="Empty dict, Priority Agent sẽ fill")


class GenerateOutput(BaseModel):
    """Structured output từ generate node."""
    metadata: dict = Field(description="Metadata: product_name, version, total_items, total_story_points")
    items: list[BacklogItem] = Field(description="Danh sách backlog items")


class BacklogState(BaseModel):
    """State cho Backlog Agent workflow."""
    # Input
    messages: list[BaseMessage] = Field(default_factory=list)
    product_vision: dict = Field(default_factory=dict)

    # Initialize outputs
    validation_status: str = "pending"
    readiness_score: float = 0.0
    missing_info: list[str] = Field(default_factory=list)
    key_capabilities: list[str] = Field(default_factory=list)
    dependency_map: dict = Field(default_factory=dict)
    estimated_items: dict = Field(default_factory=dict)

    # Generate outputs
    backlog_items: list[dict] = Field(default_factory=list)

    # Evaluate outputs
    invest_issues: list[dict] = Field(default_factory=list)
    gherkin_issues: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    can_proceed: bool = False

    # Loop control
    max_loops: int = 2
    current_loop: int = 0

    # Final output
    product_backlog: dict = Field(default_factory=dict)
    summary_markdown: str = ""
    status: str = "initial"


# ============================================================================
# Backlog Agent Class
# ============================================================================

class BacklogAgent:
    """Backlog Agent - Tạo Product Backlog từ Product Vision (fully automated)."""

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo backlog agent.

        Args:
            session_id: Session ID tùy chọn
            user_id: User ID tùy chọn
        """
        self.session_id = session_id
        self.user_id = user_id

        # Initialize Langfuse callback handler
        self.langfuse_handler = CallbackHandler()

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
        except Exception:
            return None

    def _build_graph(self) -> StateGraph:
        """Xây dựng LangGraph workflow."""
        graph_builder = StateGraph(BacklogState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("generate", self.generate)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("refine", self.refine)
        graph_builder.add_node("finalize", self.finalize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "generate")
        # graph_builder.add_edge("generate", "evaluate")
        # graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        # graph_builder.add_edge("refine", "generate")  # Loop back
        # graph_builder.add_edge("finalize", END)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Node: Initialize
    # ========================================================================

    def initialize(self, state: BacklogState) -> BacklogState:
        """Initialize - Load Product Vision và chuẩn bị working state.

        Theo sơ đồ:
        - Load product_vision
        - Set max_loops = 2
        - Init dependency map
        """
        print("\n" + "="*80)
        print("🚀 INITIALIZE - KHỞI TẠO BACKLOG AGENT")
        print("="*80)

        # Validate product_vision structure
        if not state.product_vision or len(state.product_vision) == 0:
            print("⚠ Chưa có product_vision, không thể tạo backlog")
            state.validation_status = "missing_critical"
            state.status = "error"
            return state

        print(f"✓ Đã load product_vision từ state")
        product_name = state.product_vision.get("product_name", "N/A")
        print(f"  - Product Name: {product_name}")

        # Set max_loops
        state.max_loops = 2
        state.current_loop = 0
        print(f"  - Max Loops: {state.max_loops}")

        # Prepare vision for prompt
        vision_text = json.dumps(state.product_vision, ensure_ascii=False, indent=2)

        prompt = INITIALIZE_PROMPT.format(vision=vision_text)

        try:
            # Use JSON mode (more compatible than structured output)
            llm = self._llm("gpt-4.1", 0.3)

            # Add JSON instruction to prompt
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON with the exact fields specified above. No markdown, no explanations."

            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up response (remove markdown if present)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse and validate with Pydantic
            result_dict = json.loads(response_text)
            initialize_result = InitializeOutput(**result_dict)

            # Update state with initialization results
            state.validation_status = initialize_result.validation_status
            state.readiness_score = initialize_result.readiness_score
            state.missing_info = initialize_result.missing_info
            state.key_capabilities = initialize_result.key_capabilities
            state.dependency_map = initialize_result.dependency_map
            state.estimated_items = initialize_result.estimated_items

            # Print initialization summary
            print(f"\n✓ Initialize completed")
            print(f"   Validation Status: {initialize_result.validation_status}")
            print(f"   Readiness Score: {initialize_result.readiness_score:.2f}")

            if initialize_result.missing_info:
                print(f"\n⚠️  Missing Info ({len(initialize_result.missing_info)}):")
                for i, info in enumerate(initialize_result.missing_info, 1):
                    print(f"   {i}. {info}")

            print(f"\n🎯 Key Capabilities ({len(initialize_result.key_capabilities)}):")
            for i, cap in enumerate(initialize_result.key_capabilities[:3], 1):
                print(f"   {i}. {cap}")
            if len(initialize_result.key_capabilities) > 3:
                print(f"   ... và {len(initialize_result.key_capabilities) - 3} capabilities khác")

            print(f"\n🔗 Dependency Map:")
            if initialize_result.dependency_map:
                for key, deps in list(initialize_result.dependency_map.items())[:3]:
                    print(f"   {key} → {deps}")
                if len(initialize_result.dependency_map) > 3:
                    print(f"   ... và {len(initialize_result.dependency_map) - 3} dependencies khác")
            else:
                print("   (No dependencies mapped)")

            print(f"\n📊 Estimated Items:")
            if initialize_result.estimated_items:
                print(f"   Epics: {initialize_result.estimated_items.get('epics', 0)}")
                print(f"   User Stories: {initialize_result.estimated_items.get('user_stories', 0)}")
                print(f"   Tasks: {initialize_result.estimated_items.get('tasks', 0)}")

            print("\n" + "="*80 + "\n")

            # Print structured output JSON
            print("\n📊 Structured Output từ initialize:")
            print(json.dumps(initialize_result.model_dump(), ensure_ascii=False, indent=2))
            print()

            # Update status
            if initialize_result.readiness_score >= 0.8:
                state.status = "ready"
                print("✅ Vision đủ sẵn sàng để tạo backlog")
            elif initialize_result.readiness_score >= 0.5:
                state.status = "partial_ready"
                print("⚠️  Vision thiếu một số thông tin nhưng vẫn có thể tạo backlog")
            else:
                state.status = "not_ready"
                print("❌ Vision thiếu quá nhiều thông tin, cần bổ sung trước khi tạo backlog")

        except Exception as e:
            print(f"❌ Lỗi khi initialize: {e}")
            import traceback
            traceback.print_exc()
            state.validation_status = "error"
            state.status = "error"
            state.readiness_score = 0.0

        print("="*80 + "\n")
        return state

    # ========================================================================
    # Node: Generate (to be implemented)
    # ========================================================================

    def generate(self, state: BacklogState) -> BacklogState:
        """Generate backlog items từ Product Vision.

        Theo sơ đồ:
        - Tạo Epic → các Product Backlog Item (PBI)
        - Với mỗi PBI: viết user story theo INVEST
        - Thêm acceptance criteria dạng Gherkin (Given-When-Then)
        - THU THẬP WSJF inputs: business/user value, time criticality, risk reduction/opportunity, job size
        - Ước lượng kích cỡ & ghi phụ thuộc & ghi chú
        """
        print("\n" + "="*80)
        print("✨ GENERATE - TẠO PRODUCT BACKLOG ITEMS")
        print("="*80)

        # Check readiness from initialize
        if state.readiness_score < 0.5:
            print(f"⚠️  Readiness score quá thấp ({state.readiness_score:.2f}), không thể tạo backlog")
            state.status = "not_ready"
            return state

        print(f"✓ Readiness Score: {state.readiness_score:.2f}")
        print(f"✓ Key Capabilities: {len(state.key_capabilities)} capabilities")
        print(f"✓ Dependency Map: {len(state.dependency_map)} dependencies")

        # Prepare prompt với vision và dependency_map
        vision_text = json.dumps(state.product_vision, ensure_ascii=False, indent=2)
        dependency_map_text = json.dumps(state.dependency_map, ensure_ascii=False, indent=2)

        prompt = GENERATE_PROMPT.format(
            vision=vision_text,
            dependency_map=dependency_map_text
        )

        try:
            # Use JSON mode (compatible với API)
            llm = self._llm("gpt-4.1", 0.3)

            # Simplified prompt với dependency mapping
            dependency_map_text = json.dumps(state.dependency_map, ensure_ascii=False, indent=2)

            simplified_prompt = f"""Dựa trên Product Vision, tạo Product Backlog với:
- 3-5 Epics
- 2-3 User Stories cho mỗi Epic
- 1-2 Tasks cho mỗi User Story

**Product Vision:**
{json.dumps(state.product_vision, ensure_ascii=False, indent=2)}

**Dependency Map (từ Initialize):**
{dependency_map_text}

Dùng dependency map này để set dependencies cho items. Ví dụ:
- Nếu map có "User Profile" → ["Authentication"], thì EPIC về User Profile phải có dependencies = [ID của Epic Authentication]

**Output JSON format:**
{{
  "metadata": {{
    "product_name": "...",
    "version": "v1.0",
    "total_items": 0,
    "total_story_points": 0
  }},
  "items": [
    {{
      "id": "EPIC-001",
      "type": "Epic",
      "parent_id": null,
      "title": "Authentication System",
      "description": "...",
      "priority": "Not Set",
      "status": "Backlog",
      "story_points": null,
      "estimated_hours": null,
      "acceptance_criteria": [],
      "dependencies": [],
      "labels": ["core"],
      "task_type": null,
      "business_value": "...",
      "wsjf_inputs": {{}}
    }},
    {{
      "id": "EPIC-002",
      "type": "Epic",
      "parent_id": null,
      "title": "User Profile Management",
      "dependencies": ["EPIC-001"],  ← Phụ thuộc vào Authentication
      ...
    }},
    {{
      "id": "US-001",
      "type": "User Story",
      "parent_id": "EPIC-001",
      "title": "As a user, I want to login...",
      "dependencies": [],  ← User Story đầu tiên không dependencies
      ...
    }},
    {{
      "id": "US-002",
      "type": "User Story",
      "parent_id": "EPIC-002",
      "dependencies": ["US-001"],  ← Phụ thuộc vào Login story
      ...
    }}
  ]
}}

**Quy tắc QUAN TRỌNG:**
1. ID: EPIC-001, US-001, TASK-001 (CHỮ HOA)
2. User Story title: "As a [user], I want to [action] so that [benefit]"
3. User Story: story_points = 1,2,3,5,8,13,21
4. Task: estimated_hours = 0.5-200, task_type = "Feature Development"/"Bug Fix"/etc
5. Epic/Task: story_points = null
6. Epic/US: estimated_hours = null
7. **Dependencies**: Dựa vào dependency_map để set đúng. Epic/US/Task phụ thuộc kỹ thuật phải khai báo dependencies = [list of IDs]

Return ONLY valid JSON, no markdown, no explanations."""

            print("\n🤖 Calling LLM to generate backlog items...")
            response = llm.invoke([HumanMessage(content=simplified_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Debug: Print response info
            print(f"📄 Response length: {len(response_text)} chars")

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove any trailing commas before closing braces/brackets (common LLM error)
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)

            # Debug: Print cleaned response samples
            print(f"📄 First 300 chars:\n{response_text[:300]}")
            print(f"📄 Last 300 chars:\n{response_text[-300:]}")

            # Parse và validate
            try:
                result_dict = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON Parse Error at line {e.lineno}, column {e.colno}")
                print(f"   Error: {e.msg}")
                print(f"\n📄 Problematic area (around error):")
                lines = response_text.split('\n')
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                for i in range(start, end):
                    marker = ">>> " if i == e.lineno - 1 else "    "
                    print(f"{marker}Line {i+1}: {lines[i]}")
                raise

            generate_result = GenerateOutput(**result_dict)

            # Update state
            state.backlog_items = [item.model_dump() for item in generate_result.items]

            # Print summary
            print(f"\n✓ Generate completed")
            print(f"   Total Items: {len(generate_result.items)}")

            # Count by type
            epics = [i for i in generate_result.items if i.type == "Epic"]
            stories = [i for i in generate_result.items if i.type == "User Story"]
            tasks = [i for i in generate_result.items if i.type == "Task"]

            print(f"\n📊 Backlog Breakdown:")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")

            # Calculate total story points
            total_sp = sum(item.story_points or 0 for item in generate_result.items)
            print(f"   - Total Story Points: {total_sp}")

            # Show sample items
            print(f"\n📝 Sample Items:")
            for item_type in ["Epic", "User Story", "Task"]:
                sample = next((i for i in generate_result.items if i.type == item_type), None)
                if sample:
                    print(f"\n   [{item_type}] {sample.id}: {sample.title[:60]}...")
                    if sample.acceptance_criteria:
                        print(f"      AC: {len(sample.acceptance_criteria)} criteria")

            print("\n" + "="*80 + "\n")

            # Print structured output (first 3 items only for brevity)
            print("\n📊 Structured Output từ generate (sample 3 items):")
            sample_output = {
                "metadata": generate_result.metadata,
                "items": [item.model_dump() for item in generate_result.items[:3]]
            }
            print(json.dumps(sample_output, ensure_ascii=False, indent=2))
            print(f"... và {len(generate_result.items) - 3} items khác\n")

            state.status = "generated"

        except Exception as e:
            print(f"❌ Lỗi khi generate backlog: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_generating"

        print("="*80 + "\n")
        return state

    # ========================================================================
    # Node: Evaluate (to be implemented)
    # ========================================================================

    def evaluate(self, state: BacklogState) -> BacklogState:
        """Evaluate backlog quality."""
        # TODO: Implement
        pass

    # ========================================================================
    # Node: Refine (to be implemented)
    # ========================================================================

    def refine(self, state: BacklogState) -> BacklogState:
        """Refine backlog based on evaluation."""
        # TODO: Implement
        pass

    # ========================================================================
    # Node: Finalize (to be implemented)
    # ========================================================================

    def finalize(self, state: BacklogState) -> BacklogState:
        """Finalize backlog."""
        # TODO: Implement
        pass

    # ========================================================================
    # Conditional Branch
    # ========================================================================

    def evaluate_branch(self, state: BacklogState) -> str:
        """Branch sau evaluate node.

        Logic:
        - score < 0.8 AND loops < max_loops → refine
        - score ≥ 0.8 OR loops ≥ max_loops → finalize
        """
        if state.readiness_score < 0.8 and state.current_loop < state.max_loops:
            return "refine"
        else:
            return "finalize"

    # ========================================================================
    # Run Method
    # ========================================================================

    def run(self, product_vision: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Chạy Backlog Agent workflow.

        Args:
            product_vision: Product Vision từ Vision Agent
            thread_id: Thread ID cho checkpointer

        Returns:
            dict: Final state với product_backlog
        """
        if thread_id is None:
            thread_id = self.session_id or "default_backlog_thread"

        initial_state = BacklogState(product_vision=product_vision)

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output

        return final_state or {}

    