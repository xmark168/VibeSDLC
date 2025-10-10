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


class BacklogItem(BaseModel):
    """Model cho một backlog item."""
    id: str = Field(description="ID: EPIC-001, US-001, TASK-001")
    type: Literal["Epic", "User Story", "Task"] = Field(description="Loại item")
    parent_id: Optional[str] = Field(default=None, description="ID của parent item")
    title: str = Field(description="Tiêu đề item")
    description: str = Field(default="", description="Mô tả chi tiết")
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
    metadata: dict = Field(description="Metadata: product_name")
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
        graph_builder.add_edge("generate", "evaluate")
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        graph_builder.add_edge("refine", "evaluate")  # Loop back to evaluate (not generate)
        graph_builder.add_edge("finalize", END)

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
        state.max_loops = 1
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

            print("\n🤖 Calling LLM to generate backlog items...")
            response = llm.invoke([HumanMessage(content=prompt)])

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
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)

            # Remove // comments (JSON doesn't support comments)
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

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

            # Count by type
            epics = [i for i in generate_result.items if i.type == "Epic"]
            stories = [i for i in generate_result.items if i.type == "User Story"]
            tasks = [i for i in generate_result.items if i.type == "Task"]

            # Calculate totals
            total_items = len(generate_result.items)
            total_story_points = sum(item.story_points or 0 for item in generate_result.items)

            # Update metadata with calculated values
            generate_result.metadata.update({
                "version": "v1.0",
                "total_items": total_items,
                "total_epics": len(epics),
                "total_user_stories": len(stories),
                "total_tasks": len(tasks),
                "total_story_points": total_story_points
            })

            # Update state
            state.backlog_items = [item.model_dump() for item in generate_result.items]

            # Store complete backlog with metadata in product_backlog
            state.product_backlog = {
                "metadata": generate_result.metadata,
                "items": state.backlog_items
            }

            # Print summary
            print(f"\n✓ Generate completed")
            print(f"   Total Items: {total_items}")

            print(f"\n📊 Backlog Breakdown:")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")
            print(f"   - Total Story Points: {total_story_points}")

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
        """Evaluate backlog quality.

        Theo sơ đồ:
        - Kiểm INVEST cho User Stories → needs_split / not_testable
        - Kiểm Gherkin cho Acceptance Criteria → weak_ac / missing_cases
        - Score readiness(backlog) → điểm & đánh giá thiếu sót (KHÔNG đánh giá/so sánh thứ tự)
        """
        print("\n" + "="*80)
        print("🔍 EVALUATE - ĐÁNH GIÁ CHẤT LƯỢNG BACKLOG")
        print("="*80)

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
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON with the exact fields specified above. No markdown, no explanations."

            print("\n🤖 Calling LLM to evaluate backlog...")
            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove comments
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

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
                    print(f"   {i}. [{issue.get('item_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}...")
                if len(state.invest_issues) > 5:
                    print(f"   ... và {len(state.invest_issues) - 5} issues khác")

            if state.gherkin_issues:
                print(f"\n⚠️  Gherkin Issues ({len(state.gherkin_issues)}):")
                for i, issue in enumerate(state.gherkin_issues[:5], 1):
                    print(f"   {i}. [{issue.get('item_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}...")
                if len(state.gherkin_issues) > 5:
                    print(f"   ... và {len(state.gherkin_issues) - 5} issues khác")

            if state.recommendations:
                print(f"\n💡 Recommendations ({len(state.recommendations)}):")
                for i, rec in enumerate(state.recommendations[:3], 1):
                    print(f"   {i}. {rec}")
                if len(state.recommendations) > 3:
                    print(f"   ... và {len(state.recommendations) - 3} recommendations khác")

            print("\n" + "="*80 + "\n")

            # Print structured output
            print("\n📊 Structured Output từ evaluate:")
            eval_output = {
                "readiness_score": state.readiness_score,
                "can_proceed": state.can_proceed,
                "invest_issues_count": len(state.invest_issues),
                "gherkin_issues_count": len(state.gherkin_issues),
                "recommendations_count": len(state.recommendations)
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

        print("="*80 + "\n")
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
        print("\n" + "="*80)
        print("🔧 REFINE - CẢI THIỆN BACKLOG")
        print("="*80)

        # Increment loop counter
        state.current_loop += 1
        print(f"✓ Loop: {state.current_loop}/{state.max_loops}")

        if not state.backlog_items:
            print("⚠️  Không có backlog items để refine")
            state.status = "error_no_items"
            return state

        print(f"✓ Refining {len(state.backlog_items)} backlog items...")
        print(f"✓ Issues to fix: {len(state.invest_issues)} INVEST + {len(state.gherkin_issues)} Gherkin")

        # Prepare data for prompt
        backlog_text = json.dumps(state.product_backlog, ensure_ascii=False, indent=2)
        issues_text = json.dumps({
            "invest_issues": state.invest_issues,
            "gherkin_issues": state.gherkin_issues
        }, ensure_ascii=False, indent=2)
        recommendations_text = "\n".join([f"- {rec}" for rec in state.recommendations])

        prompt = REFINE_PROMPT.format(
            backlog=backlog_text,
            issues=issues_text,
            recommendations=recommendations_text
        )

        try:
            llm = self._llm("gpt-4.1", 0.3)

            # Add JSON instruction
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON with the same format as input backlog (metadata + items). No markdown, no explanations."

            print("\n🤖 Calling LLM to refine backlog...")
            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove trailing commas and comments
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

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

            # Recalculate metadata
            total_items = len(refined_items)
            total_story_points = sum(item.story_points or 0 for item in refined_items)

            refined_metadata = result_dict.get("metadata", {})
            refined_metadata.update({
                "version": "v1.0",
                "total_items": total_items,
                "total_epics": len(epics),
                "total_user_stories": len(stories),
                "total_tasks": len(tasks),
                "total_story_points": total_story_points
            })

            # Update state with refined backlog
            state.backlog_items = [item.model_dump() for item in refined_items]
            state.product_backlog = {
                "metadata": refined_metadata,
                "items": state.backlog_items
            }

            # Print summary
            print(f"\n✓ Refine completed")
            print(f"   Total Items: {total_items} (before: {len(result_dict.get('items', []))})")

            print(f"\n📊 Refined Backlog Breakdown:")
            print(f"   - Epics: {len(epics)}")
            print(f"   - User Stories: {len(stories)}")
            print(f"   - Tasks: {len(tasks)}")
            print(f"   - Total Story Points: {total_story_points}")

            # Show changes summary
            print(f"\n🔄 Changes Applied:")
            if state.invest_issues:
                print(f"   - Fixed {len(state.invest_issues)} INVEST issues")
            if state.gherkin_issues:
                print(f"   - Fixed {len(state.gherkin_issues)} Gherkin issues")
            if state.recommendations:
                print(f"   - Applied {len(state.recommendations)} recommendations")

            print("\n" + "="*80 + "\n")

            # Print structured output (first 3 items only)
            print("\n📊 Refined Backlog (sample 3 items):")
            sample_output = {
                "metadata": refined_metadata,
                "items": [item.model_dump() for item in refined_items[:3]]
            }
            print(json.dumps(sample_output, ensure_ascii=False, indent=2))
            print(f"... và {len(refined_items) - 3} items khác\n")

            state.status = "refined"
            print(f"✅ Backlog đã được refined, loop {state.current_loop}/{state.max_loops}")

        except Exception as e:
            print(f"❌ Lỗi khi refine backlog: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_refining"

        print("="*80 + "\n")
        return state

    # ========================================================================
    # Node: Finalize (to be implemented)
    # ========================================================================

    def finalize(self, state: BacklogState) -> BacklogState:
        """Finalize backlog.

        Theo sơ đồ:
        - Định dạng OUTPUT: danh sách PBI CHƯA SẮP XẾP (unordered)
        - Kiểm tra nhất quán: liên kết goal, có AC, ước lượng, phụ thuộc
        - Export: JSON/Sheet/Jira (handoff → Priority agent để sắp xếp)
        """
        print("\n" + "="*80)
        print("✅ FINALIZE - HOÀN THIỆN PRODUCT BACKLOG")
        print("="*80)

        if not state.backlog_items:
            print("⚠️  Không có backlog items để finalize")
            state.status = "error_no_items"
            return state

        print(f"✓ Finalizing {len(state.backlog_items)} backlog items...")

        # Prepare backlog for prompt
        backlog_text = json.dumps(state.product_backlog, ensure_ascii=False, indent=2)

        prompt = FINALIZE_PROMPT.format(backlog=backlog_text)

        try:
            llm = self._llm("gpt-4.1", 0.3)

            # Add JSON instruction
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON with metadata and items. No markdown, no explanations."

            print("\n🤖 Calling LLM to finalize backlog...")
            response = llm.invoke([HumanMessage(content=json_prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Clean up markdown if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Remove trailing commas and comments
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

            # Parse JSON
            result_dict = json.loads(response_text)

            # Validate structure
            if "items" not in result_dict:
                raise ValueError("Finalized backlog missing 'items' field")
            if "metadata" not in result_dict:
                raise ValueError("Finalized backlog missing 'metadata' field")

            # Parse items with Pydantic validation
            final_items = [BacklogItem(**item) for item in result_dict["items"]]

            # Recalculate metadata to ensure accuracy
            epics = [i for i in final_items if i.type == "Epic"]
            stories = [i for i in final_items if i.type == "User Story"]
            tasks = [i for i in final_items if i.type == "Task"]

            total_items = len(final_items)
            total_story_points = sum(item.story_points or 0 for item in final_items)

            final_metadata = result_dict["metadata"]
            final_metadata.update({
                "version": "v1.0",
                "total_items": total_items,
                "total_epics": len(epics),
                "total_user_stories": len(stories),
                "total_tasks": len(tasks),
                "total_story_points": total_story_points,
                "export_status": "success"
            })

            # Update state with finalized backlog
            state.backlog_items = [item.model_dump() for item in final_items]
            state.product_backlog = {
                "metadata": final_metadata,
                "items": state.backlog_items
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
            print(f"   Total Story Points: {total_story_points}")

            # Validation summary
            print(f"\n🔍 Validation Summary:")
            items_with_ac = sum(1 for item in final_items if item.acceptance_criteria)
            items_with_deps = sum(1 for item in final_items if item.dependencies)
            stories_with_points = sum(1 for item in final_items if item.type == "User Story" and item.story_points)
            tasks_with_hours = sum(1 for item in final_items if item.type == "Task" and item.estimated_hours)

            print(f"   - Items with Acceptance Criteria: {items_with_ac}/{total_items}")
            print(f"   - Items with Dependencies: {items_with_deps}/{total_items}")
            print(f"   - User Stories with Story Points: {stories_with_points}/{len(stories)}")
            print(f"   - Tasks with Estimated Hours: {tasks_with_hours}/{len(tasks)}")

            print(f"\n📤 Export Status: {final_metadata.get('export_status', 'unknown')}")
            print(f"   → Ready for handoff to Priority Agent")

            print("\n" + "="*80 + "\n")

            # Print metadata
            print("\n📊 Final Metadata:")
            print(json.dumps(final_metadata, ensure_ascii=False, indent=2))
            print()

            state.status = "completed"
            print(f"✅ Product Backlog đã hoàn thiện! Tổng {state.current_loop} loops.")

        except Exception as e:
            print(f"❌ Lỗi khi finalize backlog: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_finalizing"
            # Still set export_status to failed in metadata
            if state.product_backlog.get("metadata"):
                state.product_backlog["metadata"]["export_status"] = "failed"

        print("="*80 + "\n")
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
            reason = "score ≥ 0.8" if state.readiness_score >= 0.8 else "reached max_loops"
            print(f"   → Decision: FINALIZE ({reason})")
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

        # return final_state or {}
        return None

    