import json
import os
import re
import uuid
from typing import Any, Literal, Optional
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.templates.prompts.product_owner.backlog import (
    GENERATE_PROMPT,
    EVALUATE_PROMPT,
    REFINE_PROMPT,
)

from langgraph.checkpoint.memory import MemorySaver


load_dotenv()

# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class BacklogItem(BaseModel):
    """Model cho một backlog item.

    Hierarchy theo Jira:
    - Epic (parent_id=null): Container cho các stories
    - User Story (parent_id=EPIC-xxx): Standard work item, con của Epic
    - Task (parent_id=EPIC-xxx): Standard work item, con của Epic, cùng cấp với User Story
    - Sub-task (parent_id=US-xxx hoặc TASK-xxx): Con của User Story hoặc Task
    """

    id: str = Field(description="ID: EPIC-001, US-001, TASK-001, SUB-001")
    type: Literal["Epic", "User Story", "Task", "Sub-task"] = Field(
        description="Loại item"
    )
    parent_id: Optional[str] = Field(default=None, description="ID của parent item")
    title: str = Field(description="Tiêu đề item")
    description: str = Field(default="", description="Mô tả chi tiết")
    rank: Optional[int] = Field(
        default=None, description="Thứ tự ưu tiên, Priority Agent sẽ fill"
    )
    status: Literal["Backlog", "Ready", "In Progress", "Done"] = Field(
        default="Backlog"
    )
    story_point: Optional[int] = Field(default=None, description="CHỈ cho User Story")
    estimate_value: Optional[float] = Field(
        default=None, description="CHỈ cho Task và Sub-task"
    )
    acceptance_criteria: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    task_type: Optional[str] = Field(
        default=None, description="CHỈ cho Task và Sub-task: Development/Testing/etc"
    )
    business_value: Optional[str] = Field(
        default=None, description="Cho Epic và User Story, null cho Task và Sub-task"
    )


class GenerateOutput(BaseModel):
    """Structured output từ generate node."""

    metadata: dict = Field(description="Metadata: product_name")
    items: list[BacklogItem] = Field(description="Danh sách backlog items")


class BacklogState(BaseModel):
    """State cho Backlog Agent workflow."""

    # Input
    product_vision: dict = Field(default_factory=dict)

    # Generate outputs
    backlog_items: list[dict] = Field(default_factory=list)

    # Evaluate outputs
    invest_issues: list[dict] = Field(default_factory=list)
    gherkin_issues: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    readiness_score: float = 0.0
    can_proceed: bool = False

    # Loop control
    max_loops: int = 2
    current_loop: int = 0

    # Preview & user approval
    user_approval: Optional[str] = Field(
        default=None, description="'approve' hoặc 'edit'"
    )
    user_feedback: Optional[str] = Field(
        default=None, description="Lý do/yêu cầu chỉnh sửa từ user"
    )

    # Final output
    product_backlog: dict = Field(default_factory=dict)
    status: str = "initial"


# ============================================================================
# Backlog Agent Class
# ============================================================================


class BacklogAgent:
    """Backlog Agent - Tạo Product Backlog từ Product Vision (fully automated)."""

    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        websocket_broadcast_fn=None,
        project_id: str | None = None,
        response_manager=None,
        event_loop=None
    ):
        """Khởi tạo backlog agent.

        Args:
            session_id: Session ID tùy chọn
            user_id: User ID tùy chọn
            websocket_broadcast_fn: Async function to broadcast WebSocket messages (optional)
            project_id: Project ID for WebSocket broadcasting (optional)
            response_manager: ResponseManager for human-in-the-loop via WebSocket (optional)
            event_loop: Event loop for async operations (required for WebSocket mode)
        """
        self.session_id = session_id
        self.user_id = user_id

        # WebSocket dependencies (optional)
        self.websocket_broadcast_fn = websocket_broadcast_fn
        self.project_id = project_id
        self.response_manager = response_manager
        self.event_loop = event_loop
        self.use_websocket = (
            websocket_broadcast_fn is not None
            and project_id is not None
            and response_manager is not None
        )

        # Initialize Langfuse callback handler (without session_id/user_id in constructor)
        # Session/user metadata will be passed via config metadata during invoke/stream
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

        # Always use async version for preview (like gatherer agent)
        graph_builder.add_node("preview", self.preview_async)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "generate")
        graph_builder.add_edge("generate", "evaluate")
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        graph_builder.add_edge(
            "refine", "evaluate"
        )  # Loop back to evaluate (not generate)
        graph_builder.add_edge("finalize", "preview")  # finalize → preview
        graph_builder.add_conditional_edges(
            "preview", self.preview_branch
        )  # preview → approve/edit

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Node: Initialize
    # ========================================================================

    def initialize(self, state: BacklogState) -> BacklogState:
        """Initialize - Validate và load Product Vision vào working memory.

        Chỉ làm:
        - Validate product_vision có tồn tại
        - Set max_loops
        - Set status = ready
        """
        print("\n" + "=" * 80)
        print("🚀 INITIALIZE - LOAD CONTEXT")
        print("=" * 80)

        # Validate product_vision structure
        if not state.product_vision or len(state.product_vision) == 0:
            print("⚠️  Chưa có product_vision, không thể tạo backlog")
            state.status = "error"
            return state

        product_name = state.product_vision.get("product_name", "N/A")
        print(f"✓ Đã load product_vision: {product_name}")

        # Set max_loops (increased to 2 to allow more refine iterations)
        state.max_loops = 2
        state.current_loop = 0

        # Set ready status
        state.status = "ready"

        print(f"✓ Max loops: {state.max_loops}")
        print("✅ Ready to generate backlog")
        print("=" * 80 + "\n")

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
        print("\n" + "=" * 80)
        print("✨ GENERATE - TẠO PRODUCT BACKLOG ITEMS")
        print("=" * 80)

        # Prepare prompt với vision
        vision_text = json.dumps(state.product_vision, ensure_ascii=False, indent=2)

        prompt = GENERATE_PROMPT.format(vision=vision_text)

        try:
            # Use JSON mode (compatible với API)
            llm = self._llm("gpt-4.1", 0.2)

            print("\n🤖 Calling LLM to generate backlog items...")
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Debug: Print response info
            print(f"📄 Response length: {len(response_text)} chars")

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove any trailing commas before closing braces/brackets (common LLM error)
            response_text = re.sub(r",(\s*[}\]])", r"\1", response_text)

            # Remove // comments (JSON doesn't support comments)
            response_text = re.sub(r"//.*?$", "", response_text, flags=re.MULTILINE)

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
                lines = response_text.split("\n")
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                for i in range(start, end):
                    marker = ">>> " if i == e.lineno - 1 else "    "
                    print(f"{marker}Line {i+1}: {lines[i]}")
                raise

            generate_result = GenerateOutput(**result_dict)

            # Count by type
            epics = [i for i in generate_result.items if i.type == "Epic"]
            stories = [i for i in generate_result.items if i.type == "User Story"]
            tasks = [i for i in generate_result.items if i.type == "Task"]
            subtasks = [i for i in generate_result.items if i.type == "Sub-task"]

            # Calculate totals
            total_items = len(generate_result.items)
            total_story_points = sum(
                item.story_point or 0 for item in generate_result.items
            )
            total_estimate_hours = sum(
                item.estimate_value or 0 for item in generate_result.items
            )

            # Update metadata with calculated values
            generate_result.metadata.update(
                {
                    "version": "v1.0",
                    "total_items": total_items,
                    "total_epics": len(epics),
                    "total_user_stories": len(stories),
                    "total_tasks": len(tasks),
                    "total_subtasks": len(subtasks),
                    "total_story_points": total_story_points,
                    "total_estimate_hours": total_estimate_hours,
                }
            )

            # Update state
            state.backlog_items = [item.model_dump() for item in generate_result.items]

            # Store complete backlog with metadata in product_backlog
            state.product_backlog = {
                "metadata": generate_result.metadata,
                "items": state.backlog_items,
            }

            # Print summary
            print(f"\n✓ Generate completed")
            print(f"   Total Items: {total_items}")

            print(f"\n📊 Backlog Breakdown:")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")
            print(f"   - Sub-tasks: {len(subtasks)}")
            print(f"   - Total Story Points: {total_story_points}")
            print(f"   - Total Estimate Hours: {total_estimate_hours}")

            # Show sample items
            print(f"\n📝 Sample Items:")
            for item_type in ["Epic", "User Story", "Task", "Sub-task"]:
                sample = next(
                    (i for i in generate_result.items if i.type == item_type), None
                )
                if sample:
                    print(f"\n   [{item_type}] {sample.id}: {sample.title[:60]}...")
                    if sample.parent_id:
                        print(f"      Parent: {sample.parent_id}")
                    if sample.acceptance_criteria:
                        print(f"      AC: {len(sample.acceptance_criteria)} criteria")

            print("\n" + "=" * 80 + "\n")

            # Print structured output (first 3 items only for brevity)
            print("\n📊 Structured Output từ generate (sample 3 items):")
            sample_output = {
                "metadata": generate_result.metadata,
                "items": [item.model_dump() for item in generate_result.items[:3]],
            }
            print(json.dumps(sample_output, ensure_ascii=False, indent=2))
            print(f"... và {len(generate_result.items) - 3} items khác\n")

            state.status = "generated"

        except Exception as e:
            print(f"❌ Lỗi khi generate backlog: {e}")
            import traceback

            traceback.print_exc()
            state.status = "error_generating"

        print("=" * 80 + "\n")
        return state

    # ========================================================================
    # Node: Evaluate (to be implemented)
    # ========================================================================

    def evaluate(self, state: BacklogState) -> BacklogState:
        """Evaluate backlog quality.

        Theo sơ đồ:
        - Kiểm INVEST cho User Stories → needs_split / not_testable
        - Kiểm Gherkin cho Acceptance Criteria → weak_ac / missing_cases
        - Score readiness(backlog) → điểm & đánh giá thiếu sót (KHÔNG đánh giá/so sánh thứ tự)
        """
        print("\n" + "=" * 80)
        print("🔍 EVALUATE - ĐÁNH GIÁ CHẤT LƯỢNG BACKLOG")
        print("=" * 80)

        if not state.backlog_items:
            print("⚠️  Không có backlog items để đánh giá")
            state.can_proceed = False
            state.status = "error_no_items"
            return state

        print(f"✓ Evaluating {len(state.backlog_items)} backlog items...")

        # Prepare backlog for prompt
        backlog_text = json.dumps(state.product_backlog, ensure_ascii=False, indent=2)

        prompt = EVALUATE_PROMPT.format(backlog=backlog_text)

        try:
            llm = self._llm("gpt-4.1", 0.3)

            # Add JSON instruction
            json_prompt = (
                prompt
                + "\n\nIMPORTANT: Return ONLY valid JSON with the exact fields specified above. No markdown, no explanations."
            )

            print("\n🤖 Calling LLM to evaluate backlog...")
            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove comments
            response_text = re.sub(r"//.*?$", "", response_text, flags=re.MULTILINE)

            # Parse JSON
            result_dict = json.loads(response_text)

            # Update state with evaluation results
            state.readiness_score = result_dict.get("readiness_score", 0.0)
            state.invest_issues = result_dict.get("invest_issues", [])
            state.gherkin_issues = result_dict.get("gherkin_issues", [])
            state.recommendations = result_dict.get("recommendations", [])
            state.can_proceed = result_dict.get("can_proceed", False)

            # Print evaluation summary
            print(f"\n✓ Evaluate completed")
            print(f"   Readiness Score: {state.readiness_score:.2f}")
            print(f"   Can Proceed: {state.can_proceed}")

            if state.invest_issues:
                print(f"\n⚠️  INVEST Issues ({len(state.invest_issues)}):")
                for i, issue in enumerate(state.invest_issues[:5], 1):
                    print(
                        f"   {i}. [{issue.get('item_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}..."
                    )
                if len(state.invest_issues) > 5:
                    print(f"   ... và {len(state.invest_issues) - 5} issues khác")

            if state.gherkin_issues:
                print(f"\n⚠️  Gherkin Issues ({len(state.gherkin_issues)}):")
                for i, issue in enumerate(state.gherkin_issues[:5], 1):
                    print(
                        f"   {i}. [{issue.get('item_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}..."
                    )
                if len(state.gherkin_issues) > 5:
                    print(f"   ... và {len(state.gherkin_issues) - 5} issues khác")

            if state.recommendations:
                print(f"\n💡 Recommendations ({len(state.recommendations)}):")
                for i, rec in enumerate(state.recommendations[:3], 1):
                    print(f"   {i}. {rec}")
                if len(state.recommendations) > 3:
                    print(
                        f"   ... và {len(state.recommendations) - 3} recommendations khác"
                    )

            print("\n" + "=" * 80 + "\n")

            # Print structured output
            print("\n📊 Structured Output từ evaluate:")
            eval_output = {
                "readiness_score": state.readiness_score,
                "can_proceed": state.can_proceed,
                "invest_issues_count": len(state.invest_issues),
                "gherkin_issues_count": len(state.gherkin_issues),
                "recommendations_count": len(state.recommendations),
            }
            print(json.dumps(eval_output, ensure_ascii=False, indent=2))
            print()

            # Update status
            if state.can_proceed:
                state.status = "evaluated_pass"
                print("✅ Backlog đạt yêu cầu, ready để finalize")
            else:
                state.status = "evaluated_needs_refine"
                print("⚠️  Backlog cần refine thêm")

        except Exception as e:
            print(f"❌ Lỗi khi evaluate backlog: {e}")
            import traceback

            traceback.print_exc()
            state.can_proceed = False
            state.status = "error_evaluating"

        print("=" * 80 + "\n")
        return state

    # ========================================================================
    # Node: Refine (to be implemented)
    # ========================================================================

    def refine(self, state: BacklogState) -> BacklogState:
        """Refine backlog based on evaluation.

        Theo sơ đồ:
        - Sửa thiếu sót: chia nhỏ mục lớn, bổ sung/sửa AC (GWT)
        - Điền đủ WSJF inputs/ ước lượng/phụ thuộc
        - Loại bỏ mục lệch Product Goal
        - loops++
        """
        print("\n" + "=" * 80)
        print("🔧 REFINE - CẢI THIỆN BACKLOG")
        print("=" * 80)

        # Increment loop counter
        state.current_loop += 1
        print(f"✓ Loop: {state.current_loop}/{state.max_loops}")

        if not state.backlog_items:
            print("⚠️  Không có backlog items để refine")
            state.status = "error_no_items"
            return state

        print(f"✓ Refining {len(state.backlog_items)} backlog items...")

        # Check if this is user-requested refine (from preview)
        if state.user_feedback:
            print(f"\n👤 User Feedback: {state.user_feedback}")
            print(f"✓ Refining based on user feedback...")
        else:
            print(
                f"✓ Issues to fix: {len(state.invest_issues)} INVEST + {len(state.gherkin_issues)} Gherkin"
            )

        # Prepare data for prompt
        backlog_text = json.dumps(state.product_backlog, ensure_ascii=False, indent=2)
        issues_text = json.dumps(
            {
                "invest_issues": state.invest_issues,
                "gherkin_issues": state.gherkin_issues,
            },
            ensure_ascii=False,
            indent=2,
        )
        recommendations_text = "\n".join([f"- {rec}" for rec in state.recommendations])

        # Build prompt - include user_feedback if available
        if state.user_feedback:
            # User-driven refine: prioritize user feedback
            prompt = REFINE_PROMPT.format(
                backlog=backlog_text,
                issues=issues_text,
                recommendations=recommendations_text,
            )
            # Append user feedback as highest priority
            prompt += f"\n\n🚨 CRITICAL USER FEEDBACK (HIGHEST PRIORITY):\n{state.user_feedback}\n\nIMPORTANT: Address the user feedback above FIRST, then fix other issues if time permits."
        else:
            # Auto refine: use standard prompt
            prompt = REFINE_PROMPT.format(
                backlog=backlog_text,
                issues=issues_text,
                recommendations=recommendations_text,
            )

        try:
            llm = self._llm("gpt-4.1", 0.3)

            # Add JSON instruction
            json_prompt = (
                prompt
                + "\n\nIMPORTANT: Return ONLY valid JSON with the same format as input backlog (metadata + items). No markdown, no explanations."
            )

            print("\n🤖 Calling LLM to refine backlog...")
            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove trailing commas and comments
            response_text = re.sub(r",(\s*[}\]])", r"\1", response_text)
            response_text = re.sub(r"//.*?$", "", response_text, flags=re.MULTILINE)

            # Parse JSON
            result_dict = json.loads(response_text)

            # Validate structure
            if "items" not in result_dict:
                raise ValueError("Refined backlog missing 'items' field")

            # Parse items with Pydantic validation
            refined_items = [BacklogItem(**item) for item in result_dict["items"]]

            # Count by type
            epics = [i for i in refined_items if i.type == "Epic"]
            stories = [i for i in refined_items if i.type == "User Story"]
            tasks = [i for i in refined_items if i.type == "Task"]
            subtasks = [i for i in refined_items if i.type == "Sub-task"]

            # Recalculate metadata
            total_items = len(refined_items)
            total_story_points = sum(item.story_point or 0 for item in refined_items)
            total_estimate_hours = sum(
                item.estimate_value or 0 for item in refined_items
            )

            refined_metadata = result_dict.get("metadata", {})
            refined_metadata.update(
                {
                    "version": "v1.0",
                    "total_items": total_items,
                    "total_epics": len(epics),
                    "total_user_stories": len(stories),
                    "total_tasks": len(tasks),
                    "total_subtasks": len(subtasks),
                    "total_story_points": total_story_points,
                    "total_estimate_hours": total_estimate_hours,
                }
            )

            # Store old counts for comparison
            old_issues_count = len(state.invest_issues) + len(state.gherkin_issues)

            # Update state with refined backlog
            state.backlog_items = [item.model_dump() for item in refined_items]
            state.product_backlog = {
                "metadata": refined_metadata,
                "items": state.backlog_items,
            }

            # Clear old evaluation results (they will be recalculated in next evaluate)
            # This prevents LLM from being confused by old issues
            state.invest_issues = []
            state.gherkin_issues = []
            state.recommendations = []
            state.readiness_score = 0.0
            state.can_proceed = False

            # Print summary
            print(f"\n✓ Refine completed")
            print(
                f"   Total Items: {total_items} (before: {len(result_dict.get('items', []))})"
            )

            print(f"\n📊 Refined Backlog Breakdown:")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")
            print(f"   - Sub-tasks: {len(subtasks)}")
            print(f"   - Total Story Points: {total_story_points}")
            print(f"   - Total Estimate Hours: {total_estimate_hours}")

            # Show changes summary
            print(f"\n🔄 Changes Applied:")
            if state.user_feedback:
                print(f"   - Addressed user feedback")
            if old_issues_count > 0:
                print(
                    f"   - Attempted to fix {old_issues_count} issues from previous evaluation"
                )
            print(f"   - Cleared old evaluation state (will re-evaluate)")

            # Clear user_feedback after applying
            if state.user_feedback:
                print(f"\n✓ User feedback đã được xử lý, clearing feedback...")
                state.user_feedback = None

            print("\n" + "=" * 80 + "\n")

            # Print structured output (first 3 items only)
            print("\n📊 Refined Backlog (sample 3 items):")
            sample_output = {
                "metadata": refined_metadata,
                "items": [item.model_dump() for item in refined_items[:3]],
            }
            print(json.dumps(sample_output, ensure_ascii=False, indent=2))
            print(f"... và {len(refined_items) - 3} items khác\n")

            state.status = "refined"
            print(
                f"✅ Backlog đã được refined, loop {state.current_loop}/{state.max_loops}"
            )

        except Exception as e:
            print(f"❌ Lỗi khi refine backlog: {e}")
            import traceback

            traceback.print_exc()
            state.status = "error_refining"

        print("=" * 80 + "\n")
        return state

    # ========================================================================
    # Node: Finalize (to be implemented)
    # ========================================================================

    def finalize(self, state: BacklogState) -> BacklogState:
        """Finalize backlog."""
        print("\n" + "="*80)
        print("✅ FINALIZE - HOÀN THIỆN PRODUCT BACKLOG")
        print("=" * 80)

        if not state.backlog_items:
            print("⚠️  Không có backlog items để finalize")
            state.status = "error_no_items"
            return state

        print(f"✓ Finalizing {len(state.backlog_items)} backlog items...")

        try:
            final_items = [BacklogItem(**item) for item in state.backlog_items]

            # Calculate metadata (simple math, no LLM needed)
            epics = [i for i in final_items if i.type == "Epic"]
            stories = [i for i in final_items if i.type == "User Story"]
            tasks = [i for i in final_items if i.type == "Task"]
            subtasks = [i for i in final_items if i.type == "Sub-task"]

            total_items = len(final_items)
            total_story_points = sum(item.story_point or 0 for item in final_items)
            total_estimate_hours = sum(item.estimate_value or 0 for item in final_items)

            # Get existing metadata and update
            final_metadata = state.product_backlog.get("metadata", {}).copy()
            final_metadata.update({
                "version": "v1.0",
                "total_items": total_items,
                "total_epics": len(epics),
                "total_user_stories": len(stories),
                "total_tasks": len(tasks),
                "total_subtasks": len(subtasks),
                "total_story_points": total_story_points,
                "total_estimate_hours": total_estimate_hours,
                "export_status": "success"
            })

            # Update state (no LLM processing needed)
            state.product_backlog = {
                "metadata": final_metadata,
                "items": state.backlog_items,
            }

            # Print final summary
            print(f"\n✓ Finalize completed")
            print(f"\n📊 Final Product Backlog:")
            print(f"   Product: {final_metadata.get('product_name', 'N/A')}")
            print(f"   Version: {final_metadata.get('version', 'N/A')}")
            print(f"   Total Items: {total_items}")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")
            print(f"   - Sub-tasks: {len(subtasks)}")
            print(f"   Total Story Points: {total_story_points}")
            print(f"   Total Estimate Hours: {total_estimate_hours}")

            # Validation summary
            print(f"\n🔍 Validation Summary:")
            items_with_ac = sum(1 for item in final_items if item.acceptance_criteria)
            items_with_deps = sum(1 for item in final_items if item.dependencies)
            stories_with_points = sum(
                1
                for item in final_items
                if item.type == "User Story" and item.story_point
            )
            subtasks_with_estimate = sum(
                1
                for item in final_items
                if item.type == "Sub-task" and item.estimate_value
            )

            print(f"   - Items with Acceptance Criteria: {items_with_ac}/{total_items}")
            print(f"   - Items with Dependencies: {items_with_deps}/{total_items}")
            print(
                f"   - User Stories with Story Point: {stories_with_points}/{len(stories)}"
            )
            print(
                f"   - Sub-tasks with Estimate Value: {subtasks_with_estimate}/{len(subtasks) if subtasks else 0}"
            )

            print(
                f"\n📤 Export Status: {final_metadata.get('export_status', 'unknown')}"
            )
            print(f"   → Ready for handoff to Priority Agent")

            print("\n" + "=" * 80 + "\n")

            # Print metadata
            print("\n📊 Final Metadata:")
            print(json.dumps(final_metadata, ensure_ascii=False, indent=2))
            print()

            # Reset loop counter for potential preview → edit flow
            print(
                f"✓ Resetting loop counter (current: {state.current_loop}) để chuẩn bị cho preview..."
            )
            state.current_loop = 0

            state.status = "completed"
            print(f"✅ Product Backlog đã hoàn thiện!")

        except Exception as e:
            print(f"❌ Lỗi khi finalize backlog: {e}")
            import traceback

            traceback.print_exc()
            state.status = "error_finalizing"
            # Still set export_status to failed in metadata
            if state.product_backlog.get("metadata"):
                state.product_backlog["metadata"]["export_status"] = "failed"

        print("=" * 80 + "\n")
        return state

    # ========================================================================
    # Node: Preview
    # ========================================================================

    async def preview_async(self, state: BacklogState) -> BacklogState:
        """Async version of preview - works for both WebSocket and terminal modes."""
        print("\n[preview_async] ===== ENTERED =====", flush=True)
        print(f"[preview_async] use_websocket: {self.use_websocket}", flush=True)

        if not self.use_websocket:
            # Terminal mode - run sync version in executor
            print(f"[preview_async] Routing to terminal mode (via executor)", flush=True)
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.preview, state)

        # WebSocket mode
        print(f"[preview_async] WebSocket mode, queuing preview...", flush=True)

        # Generate unique preview ID
        preview_id = str(uuid.uuid4())

        # Queue preview message for broadcast
        preview_message = {
            "type": "agent_preview",
            "preview_id": preview_id,
            "agent": "Backlog Agent",
            "preview_type": "product_backlog",
            "title": "📋 PREVIEW - Product Backlog",
            "backlog": state.product_backlog,
            "options": ["approve", "edit"],
            "prompt": "Bạn muốn phê duyệt backlog này không?"
        }

        await self.response_manager.queue_broadcast(preview_message, self.project_id)
        print(f"[preview_async] ✓ Preview queued!", flush=True)

        # Wait for user choice
        print(f"[preview_async] Waiting for user choice...", flush=True)
        user_response = await self.response_manager.await_response(
            self.project_id,
            preview_id,
            timeout=600.0
        )

        if user_response is None:
            print(f"[preview_async] ⏰ Timeout, defaulting to 'approve'", flush=True)
            state.user_approval = "approve"
            state.user_feedback = None
            return state

        # Parse user response
        if isinstance(user_response, dict):
            choice = user_response.get("choice", "approve")
            edit_changes = user_response.get("edit_changes", "")
        else:
            choice = str(user_response).strip().lower()
            edit_changes = ""

        print(f"[preview_async] User choice: {choice}", flush=True)

        state.user_approval = choice

        if choice == "edit" and edit_changes:
            state.user_feedback = edit_changes
            print(f"[preview_async] Edit changes: {edit_changes[:100]}...", flush=True)
        else:
            state.user_feedback = None

        return state

    def preview(self, state: BacklogState) -> BacklogState:
        """Preview - Hiển thị bản nháp handoff để người dùng chọn: Approve / Edit.

        Theo sơ đồ:
        - Hiển thị bản nháp backlog (unordered)
        - Người dùng chọn: Approve / Edit
        - Nếu Approve → END
        - Nếu Edit → refine
        """
        print("\n" + "=" * 80)
        print("👀 PREVIEW - BẢN NHÁP HANDOFF")
        print("=" * 80)

        if not state.backlog_items:
            print("⚠️  Không có backlog items để preview")
            state.status = "error_no_items"
            state.user_approval = "edit"  # Force edit nếu không có items
            return state

        print(f"✓ Previewing {len(state.backlog_items)} backlog items...")
        print(f"\n📊 Product Backlog Summary:")

        metadata = state.product_backlog.get("metadata", {})
        print(f"   Product: {metadata.get('product_name', 'N/A')}")
        print(f"   Total Items: {metadata.get('total_items', 0)}")
        print(f"   - Epics: {metadata.get('total_epics', 0)}")
        print(f"   - User Stories: {metadata.get('total_user_stories', 0)}")
        print(f"   - Tasks: {metadata.get('total_tasks', 0)}")
        print(f"   - Sub-tasks: {metadata.get('total_subtasks', 0)}")
        print(f"   Total Story Points: {metadata.get('total_story_points', 0)}")
        print(f"   Total Estimate Hours: {metadata.get('total_estimate_hours', 0)}")

        # Show sample items by type
        print(f"\n📝 Sample Items:")
        for item_type in ["Epic", "User Story", "Task", "Sub-task"]:
            items_of_type = [
                item for item in state.backlog_items if item.get("type") == item_type
            ]
            if items_of_type:
                sample = items_of_type[0]
                print(
                    f"\n   [{item_type}] {sample.get('id')}: {sample.get('title', '')[:60]}..."
                )
                print(f"      Rank: {sample.get('rank', 'Not Set')}")
                if sample.get("parent_id"):
                    print(f"      Parent: {sample.get('parent_id')}")
                if sample.get("acceptance_criteria"):
                    print(
                        f"      AC: {len(sample.get('acceptance_criteria', []))} criteria"
                    )
                if item_type == "User Story" and sample.get("story_point"):
                    print(f"      Story Point: {sample.get('story_point')}")
                if item_type == "Sub-task" and sample.get("estimate_value"):
                    print(f"      Estimate Value: {sample.get('estimate_value')} hours")

        print("\n" + "=" * 80)
        print("\n🔔 HUMAN INPUT REQUIRED:")
        print("   Backlog đã sẵn sàng để handoff đến Priority Agent.")
        print("   Bạn có muốn:")
        print("   - 'approve': Chấp nhận và kết thúc")
        print("   - 'edit': Yêu cầu chỉnh sửa (quay lại refine)")
        print()

        # For automated testing, default to 'approve'
        # In production, this should wait for user input via API/UI
        user_input = input("   Your choice (approve/edit): ").strip().lower()

        if user_input == "approve":
            state.user_approval = "approve"
            state.user_feedback = None  # Clear any previous feedback
            state.status = "approved"
            print("\n✅ User approved! Backlog sẽ được handoff.")
        elif user_input == "edit":
            state.user_approval = "edit"
            state.status = "needs_edit"
            print("\n🔧 User requested edit.")

            # Ask for feedback/reason
            print("\n📝 Vui lòng nhập lý do/yêu cầu chỉnh sửa:")
            print(
                "   (Ví dụ: 'Thêm user story cho tính năng thanh toán', 'Chia nhỏ Epic-001', 'Bổ sung AC cho US-003')"
            )
            print()
            feedback = input("   Feedback: ").strip()

            if feedback:
                state.user_feedback = feedback
                print(f"\n✓ Đã ghi nhận feedback: {feedback[:100]}...")
            else:
                print("\n⚠️  Không có feedback, sẽ yêu cầu refine tổng quát")
                state.user_feedback = (
                    "Cải thiện chất lượng backlog dựa trên các recommendations hiện có."
                )

            print("\n🔧 Returning to refine...")
        else:
            # Default to approve if invalid input
            print(f"\n⚠️  Invalid input '{user_input}', defaulting to 'approve'")
            state.user_approval = "approve"
            state.user_feedback = None
            state.status = "approved"

        print("=" * 80 + "\n")
        return state

    # ========================================================================
    # Conditional Branch
    # ========================================================================

    def evaluate_branch(self, state: BacklogState) -> str:
        """Branch sau evaluate node.

        Logic (theo diagram):
        - score < 0.8 AND loops < max_loops → refine
        - score ≥ 0.8 OR loops ≥ max_loops → finalize
        """
        print(f"\n🔀 Evaluate Branch Decision:")
        print(f"   Readiness Score: {state.readiness_score:.2f}")
        print(f"   Current Loop: {state.current_loop}")
        print(f"   Max Loops: {state.max_loops}")

        if state.readiness_score < 0.8 and state.current_loop < state.max_loops:
            print(f"   → Decision: REFINE (score < 0.8 and loops < max)")
            return "refine"
        else:
            reason = (
                "score ≥ 0.8" if state.readiness_score >= 0.8 else "reached max_loops"
            )
            print(f"   → Decision: FINALIZE ({reason})")
            return "finalize"

    def preview_branch(self, state: BacklogState) -> str:
        """Branch sau preview node.

        Logic (theo diagram):
        - user_approval == 'approve' → END
        - user_approval == 'edit' → refine
        """
        print(f"\n🔀 Preview Branch Decision:")
        print(f"   User Approval: {state.user_approval}")

        if state.user_approval == "approve":
            print(f"   → Decision: END (user approved)")
            return END
        else:
            print(f"   → Decision: REFINE (user requested edit)")
            return "refine"

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
        print(f"\n[BacklogAgent.run] Called!", flush=True)
        print(f"[BacklogAgent.run] use_websocket: {self.use_websocket}", flush=True)

        # For WebSocket mode, run async version in dedicated WebSocket helper loop
        if self.use_websocket:
            print(f"[BacklogAgent.run] WebSocket mode - using WebSocket helper loop", flush=True)

            # Import websocket helper
            from app.core.websocket_helper import websocket_helper

            # Run async version in dedicated WebSocket loop
            print(f"[BacklogAgent.run] Scheduling in WebSocket helper loop...", flush=True)
            result = websocket_helper.run_coroutine(
                self.run_async(product_vision, thread_id),
                timeout=1200  # 20 minutes (increased for large backlogs with refine cycles)
            )
            print(f"[BacklogAgent.run] Execution completed!", flush=True)
            return result

        # Terminal mode: sync execution
        print(f"[BacklogAgent.run] Terminal mode - sync execution", flush=True)

        if thread_id is None:
            thread_id = self.session_id or "default_backlog_thread"

        initial_state = BacklogState(product_vision=product_vision)

        # Build metadata for Langfuse tracing with session_id and user_id
        metadata = {}
        if self.session_id:
            metadata["langfuse_session_id"] = self.session_id
        if self.user_id:
            metadata["langfuse_user_id"] = self.user_id
        # Add tags
        metadata["langfuse_tags"] = ["backlog_agent"]

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "metadata": metadata,  # Pass session_id/user_id via metadata
            "recursion_limit": 50,
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output

        # Return final state (last node output)
        return final_state or {}

    async def run_async(self, product_vision: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Async version for WebSocket mode.

        Args:
            product_vision: Product Vision từ Vision Agent
            thread_id: Thread ID cho checkpointer

        Returns:
            dict: Final state với product_backlog
        """
        print(f"\n[BacklogAgent.run_async] ENTERED", flush=True)

        if thread_id is None:
            thread_id = self.session_id or "default_backlog_thread"

        initial_state = BacklogState(product_vision=product_vision)

        # Build metadata for Langfuse tracing
        metadata = {}
        if self.session_id:
            metadata["langfuse_session_id"] = self.session_id
        if self.user_id:
            metadata["langfuse_user_id"] = self.user_id
        metadata["langfuse_tags"] = ["backlog_agent"]

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "metadata": metadata,
            "recursion_limit": 50,
        }

        print(f"[BacklogAgent.run_async] Starting astream...", flush=True)

        final_state = None
        async for output in self.graph.astream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output
            print(f"[BacklogAgent.run_async] Got output from node", flush=True)

        print(f"[BacklogAgent.run_async] COMPLETED", flush=True)
        return final_state or {}
