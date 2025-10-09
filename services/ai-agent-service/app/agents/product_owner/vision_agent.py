import json
import os
import re
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage,AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from templates.prompts.product_owner.vision import (
    GENERATE_PROMPT,
    VALIDATE_PROMPT,
    REASON_PROMPT,
    FINALIZE_PROMPT,
) 

from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


class AudienceSegment(BaseModel):
    name: str = Field(description="Tên nhóm đối tượng")
    description: str = Field(description="Mô tả nhóm đối tượng")
    needs: list[str] = Field(description="Nhu cầu của nhóm")
    pain_points: list[str] = Field(description="Điểm đau của nhóm")


class FeatureRequirement(BaseModel):
    name: str = Field(description="Tên tính năng")
    description: str = Field(description="Mô tả chi tiết tính năng")
    priority: str = Field(description="Độ ưu tiên: Must-have, Should-have, Nice-to-have")
    user_stories: list[str] = Field(description="Danh sách user stories cho tính năng này")


class ValidateOutput(BaseModel):
    is_valid: bool = Field(description="True nếu vision hợp lệ")
    quality_score: float = Field(description="Điểm chất lượng 0.0-1.0", ge=0.0, le=1.0)
    issues: list[str] = Field(description="Danh sách vấn đề cần sửa")
    validation_message: str = Field(description="Thông điệp tóm tắt kết quả validation")


class GenerateOutput(BaseModel):
    draft_vision_statement: str = Field(description="Tuyên bố tầm nhìn (solution-free)")
    experience_principles: list[str] = Field(description="3-5 nguyên tắc trải nghiệm")
    problem_summary: str = Field(description="Tóm tắt vấn đề cần giải quyết")
    audience_segments: list[AudienceSegment] = Field(description="Phân tích các nhóm đối tượng")
    scope_capabilities: list[str] = Field(description="Khả năng cốt lõi (không phải tính năng)")
    scope_non_goals: list[str] = Field(description="Những gì KHÔNG làm trong phiên bản này")

    # PRD: Functional Requirements
    functional_requirements: list[FeatureRequirement] = Field(description="Các tính năng cụ thể cần implement")

    # PRD: Non-Functional Requirements
    performance_requirements: list[str] = Field(description="Yêu cầu về hiệu năng")
    security_requirements: list[str] = Field(description="Yêu cầu về bảo mật")
    ux_requirements: list[str] = Field(description="Yêu cầu về trải nghiệm người dùng")

    dependencies: list[str] = Field(description="Các phụ thuộc kỹ thuật")
    risks: list[str] = Field(description="Các rủi ro tiềm ẩn")
    assumptions: list[str] = Field(description="Các giả định quan trọng")


class VisionState(BaseModel): 
    # Input & Messages
    messages: list[BaseMessage] = Field(default_factory=list)
    product_brief: dict = Field(default_factory=dict)

    # Draft components from generate node
    draft_vision_statement: str = ""
    experience_principles: list[str] = Field(default_factory=list)
    problem_summary: str = ""
    audience_segments: list[dict] = Field(default_factory=list)
    scope_capabilities: list[str] = Field(default_factory=list)
    scope_non_goals: list[str] = Field(default_factory=list)

    # PRD components
    functional_requirements: list[dict] = Field(default_factory=list)
    performance_requirements: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)
    ux_requirements: list[str] = Field(default_factory=list)

    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    # Validation
    quality_score: float = 0.0
    validation_result: str = ""

    # User interaction
    user_choice: Literal["approve", "edit", ""] = ""
    edit_reason: str = ""

    # Final output
    product_vision: dict = Field(default_factory=dict)
    summary_markdown: str = ""
    status: str = "initial"

class VisionAgent:

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        self.session_id = session_id
        self.user_id = user_id

        self.langfuse_handler = CallbackHandler()

        self.graph = self._build_graph()

    def _llm(self, model: str, temperature: str) -> ChatOpenAI:
        try:
            llm = ChatOpenAI(
                model= model,
                temperature= temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
            return llm
        except Exception:
            return ""

    def _build_graph(self) -> StateGraph:
        graph_builder = StateGraph(VisionState)

        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("generate", self.generate)
        graph_builder.add_node("validate", self.validate)
        # graph_builder.add_node("preview", self.preview)
        # graph_builder.add_node("reason", self.reason)
        # graph_builder.add_node("finalize", self.finalize)

        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "generate")
        graph_builder.add_edge("generate", "validate")
        # graph_builder.add_edge("validate", "preview")
        # graph_builder.add_conditional_edges("preview", self.preview_branch)

        checkpointer = MemorySaver()

        return graph_builder.compile(
            checkpointer=checkpointer
        )

    def initialize(self, state: VisionState) -> VisionState:
        """Initialize - Load schema (ProductVision) và load product_brief (chuẩn bị dữ liệu).

        Theo sơ đồ:
        - Load schema ProductVision để validate structure
        - Load product_brief từ state (đã có sẵn)
        - Chuẩn bị dữ liệu cho các node tiếp theo
        """
        print("\n" + "="*80)
        print("🚀 INITIALIZE - KHỞI TẠO VISION AGENT")
        print("="*80)

        # Validate product_brief structure (đã có trong state.product_brief)
        if not state.product_brief or len(state.product_brief) == 0:
            print("⚠ Chưa có product_brief, sẽ cần thông tin bổ sung")
            state.status = "missing_brief"
        else:
            print(f"✓ Đã load product_brief từ state")
            print(f"  - Product Name: {state.product_brief.get('product_name', 'N/A')}")
            print(f"  - Description: {state.product_brief.get('description', 'N/A')[:100]}...")

            required_fields = ["product_name", "description", "target_audience", "key_features"]
            missing_fields = [field for field in required_fields if field not in state.product_brief]

            if missing_fields:
                print(f"⚠ Product brief thiếu các trường: {', '.join(missing_fields)}")
                state.status = "incomplete_brief"
            else:
                print("✓ Product brief đầy đủ các trường bắt buộc")
                state.status = "ready"

        print("="*80 + "\n")

        return state

    def generate(self, state: VisionState) -> VisionState:
        """Generate - Tạo draft vision statement, experience principles và điền các thông tin.

        Theo sơ đồ:
        - Draft vision statement (solution-free)
        - 3-5 experience principles
        - Điền: problem / audience / scope / deps / uncertainties (risks/assumptions)
        """
        print("\n" + "="*80)
        print("✨ GENERATE - TẠO PRODUCT VISION")
        print("="*80)

        # Format product brief
        brief_text = json.dumps(state.product_brief, ensure_ascii=False, indent=2)

        prompt = GENERATE_PROMPT.format(brief=brief_text)

        try:
            # Use structured output with Pydantic model
            structured_llm = self._llm("gpt-4o", 0.3).with_structured_output(GenerateOutput)
            generate_result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Update state with generated components
            state.draft_vision_statement = generate_result.draft_vision_statement
            state.experience_principles = generate_result.experience_principles
            state.problem_summary = generate_result.problem_summary
            state.audience_segments = [seg.model_dump() for seg in generate_result.audience_segments]
            state.scope_capabilities = generate_result.scope_capabilities
            state.scope_non_goals = generate_result.scope_non_goals

            # PRD components
            state.functional_requirements = [req.model_dump() for req in generate_result.functional_requirements]
            state.performance_requirements = generate_result.performance_requirements
            state.security_requirements = generate_result.security_requirements
            state.ux_requirements = generate_result.ux_requirements

            state.dependencies = generate_result.dependencies
            state.risks = generate_result.risks
            state.assumptions = generate_result.assumptions

            # Print summary
            print(f"\n✓ Đã tạo Product Vision draft")
            print(f"\n📝 Vision Statement:")
            print(f"   {state.draft_vision_statement}")
            print(f"\n💡 Experience Principles ({len(state.experience_principles)}):")
            for i, principle in enumerate(state.experience_principles, 1):
                print(f"   {i}. {principle}")
            print(f"\n🎯 Problem: {state.problem_summary[:100]}...")
            print(f"👥 Audience Segments: {len(state.audience_segments)}")
            print(f"⚙️  Capabilities: {len(state.scope_capabilities)}")
            print(f"🚫 Non-Goals: {len(state.scope_non_goals)}")
            print(f"\n📋 PRD - Functional Requirements: {len(state.functional_requirements)}")
            print(f"⚡ Performance Requirements: {len(state.performance_requirements)}")
            print(f"🔒 Security Requirements: {len(state.security_requirements)}")
            print(f"🎨 UX Requirements: {len(state.ux_requirements)}")
            print(f"\n🔗 Dependencies: {len(state.dependencies)}")
            print(f"⚠️  Risks: {len(state.risks)}")
            print(f"💭 Assumptions: {len(state.assumptions)}")

            print("\n" + "="*80 + "\n")

            # Print structured output
            print("\n📊 Structured Output từ generate:")
            print(json.dumps(generate_result.model_dump(), ensure_ascii=False, indent=2))
            print()

        except Exception as e:
            print(f"❌ Lỗi khi generate vision: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_generating"

        return state

    def validate(self, state: VisionState) -> VisionState:
        """Validate - Kiểm tra clarity, inspiration, solution-free, schema & completeness.

        Theo sơ đồ:
        - Kiểm tra vision statement: clarity & inspiration
        - Kiểm tra solution-free (không nói về công nghệ cụ thể)
        - Kiểm tra schema & completeness
        - Tính quality_score
        """
        print("\n" + "="*80)
        print("✅ VALIDATE - KIỂM TRA PRODUCT VISION")
        print("="*80)

        # Prepare vision draft for validation
        vision_draft = {
            "draft_vision_statement": state.draft_vision_statement,
            "experience_principles": state.experience_principles,
            "problem_summary": state.problem_summary,
            "audience_segments": state.audience_segments,
            "scope_capabilities": state.scope_capabilities,
            "scope_non_goals": state.scope_non_goals,
            "functional_requirements": state.functional_requirements,
            "performance_requirements": state.performance_requirements,
            "security_requirements": state.security_requirements,
            "ux_requirements": state.ux_requirements,
            "dependencies": state.dependencies,
            "risks": state.risks,
            "assumptions": state.assumptions,
        }

        vision_text = json.dumps(vision_draft, ensure_ascii=False, indent=2)
        prompt = VALIDATE_PROMPT.format(vision_draft=vision_text)

        try:
            # Use structured output with Pydantic model
            structured_llm = self._llm("gpt-4o", 0.1).with_structured_output(ValidateOutput)
            validate_result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Update state
            state.quality_score = validate_result.quality_score
            state.validation_result = validate_result.validation_message

            # Print validation result
            print(f"\n✓ Validation completed")
            print(f"   Valid: {'✅ Yes' if validate_result.is_valid else '❌ No'}")
            print(f"   Quality Score: {validate_result.quality_score:.2f}")
            print(f"   Message: {validate_result.validation_message}")

            if validate_result.issues:
                print(f"\n⚠️  Issues found ({len(validate_result.issues)}):")
                for i, issue in enumerate(validate_result.issues, 1):
                    print(f"   {i}. {issue}")

            print("\n" + "="*80 + "\n")

            # Print structured output
            print("\n📊 Structured Output từ validate:")
            print(json.dumps(validate_result.model_dump(), ensure_ascii=False, indent=2))
            print()

        except Exception as e:
            print(f"❌ Lỗi khi validate vision: {e}")
            import traceback
            traceback.print_exc()
            # Set low quality score on error
            state.quality_score = 0.5
            state.validation_result = f"Error during validation: {str(e)}"

        return state

    def run(self, product_brief: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Chạy quy trình làm việc của vision agent.

        Args:
            product_brief: Product brief từ gatherer_agent (dict chứa product info)
            thread_id: ID để resume state (nếu None, dùng session_id hoặc default)

        Returns:
            dict: Trạng thái cuối cùng chứa product_vision và summary
        """
        if thread_id is None:
            thread_id = self.session_id or "default_vision_thread"

        initial_state = VisionState(
            product_brief=product_brief
        )

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