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
    acceptance_criteria: list[str] = Field(description="Tiêu chí chấp nhận - điều kiện cụ thể để tính năng được coi là hoàn thành đúng yêu cầu nghiệp vụ")


class FinalizeOutput(BaseModel):
    product_name: str = Field(description="Tên sản phẩm")
    vision_statement: str = Field(description="Vision statement cuối cùng")
    summary_markdown: str = Field(description="Tóm tắt đầy đủ dạng markdown")


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
        graph_builder.add_node("preview", self.preview)
        graph_builder.add_node("reason", self.reason)
        graph_builder.add_node("finalize", self.finalize)

        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "generate")
        graph_builder.add_edge("generate", "validate")
        graph_builder.add_edge("validate", "preview")
        graph_builder.add_conditional_edges("preview", self.preview_branch)
        graph_builder.add_edge("reason", "generate")  # Loop back to generate
        graph_builder.add_edge("finalize", END)

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

        # Check if there's edit feedback
        if state.edit_reason:
            prompt = GENERATE_PROMPT.format(brief=brief_text) + f"\n\n**EDIT FEEDBACK từ user:**\n{state.edit_reason}\n\nHãy tạo lại Product Vision với những điều chỉnh theo feedback trên."
        else:
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

        # Consolidate to product_vision dict for easy access
        state.product_vision = {
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

        # Update product_vision with validation info
        if state.product_vision:
            state.product_vision["quality_score"] = state.quality_score
            state.product_vision["validation_result"] = state.validation_result

        return state

    def preview(self, state: VisionState) -> VisionState:
        """Preview - Hiển thị product vision cho user và hỏi: Approve / Edit.

        Theo sơ đồ:
        - Show đầy đủ vision cho user
        - Hỏi user lựa chọn: Approve hoặc Edit
        - Cập nhật user_choice vào state
        """
        print("\n" + "="*80)
        print("📋 PREVIEW - XEM TRƯỚC PRODUCT VISION & PRD")
        print("="*80)
        print(f"🎯 Quality Score: {state.quality_score:.2f}")
        print(f"📝 Validation: {state.validation_result}")
        print("="*80)

        # Display Vision
        print("\n🌟 VISION STATEMENT:")
        print(f"   {state.draft_vision_statement}")

        print("\n💡 EXPERIENCE PRINCIPLES:")
        for i, principle in enumerate(state.experience_principles, 1):
            print(f"   {i}. {principle}")

        print(f"\n🎯 PROBLEM SUMMARY:")
        print(f"   {state.problem_summary}")

        print(f"\n👥 AUDIENCE SEGMENTS ({len(state.audience_segments)}):")
        for i, seg in enumerate(state.audience_segments, 1):
            print(f"   {i}. {seg.get('name', 'N/A')}: {seg.get('description', 'N/A')[:80]}...")

        print(f"\n⚙️  SCOPE - CAPABILITIES ({len(state.scope_capabilities)}):")
        for i, cap in enumerate(state.scope_capabilities[:3], 1):  # Show first 3
            print(f"   {i}. {cap[:80]}...")
        if len(state.scope_capabilities) > 3:
            print(f"   ... và {len(state.scope_capabilities) - 3} khả năng khác")

        print(f"\n🚫 SCOPE - NON-GOALS ({len(state.scope_non_goals)}):")
        for i, ng in enumerate(state.scope_non_goals[:3], 1):
            print(f"   {i}. {ng[:80]}...")
        if len(state.scope_non_goals) > 3:
            print(f"   ... và {len(state.scope_non_goals) - 3} non-goals khác")

        print(f"\n📋 FUNCTIONAL REQUIREMENTS ({len(state.functional_requirements)}):")
        for i, req in enumerate(state.functional_requirements[:3], 1):
            print(f"   {i}. {req.get('name', 'N/A')} ({req.get('priority', 'N/A')})")
        if len(state.functional_requirements) > 3:
            print(f"   ... và {len(state.functional_requirements) - 3} requirements khác")

        print(f"\n⚡ PERFORMANCE REQUIREMENTS: {len(state.performance_requirements)}")
        print(f"🔒 SECURITY REQUIREMENTS: {len(state.security_requirements)}")
        print(f"🎨 UX REQUIREMENTS: {len(state.ux_requirements)}")

        print(f"\n🔗 DEPENDENCIES: {len(state.dependencies)}")
        print(f"⚠️  RISKS: {len(state.risks)}")
        print(f"💭 ASSUMPTIONS: {len(state.assumptions)}")

        print("\n" + "="*80)
        print("💡 Bạn có thể:")
        print("  1. Gõ 'approve' để phê duyệt vision")
        print("  2. Gõ 'edit' để chỉnh sửa vision")
        print("="*80 + "\n")

        try:
            user_choice = input("👤 Lựa chọn của bạn (approve/edit): ").strip().lower()

            if user_choice not in ["approve", "edit"]:
                print(f"⚠️  Lựa chọn không hợp lệ: '{user_choice}'. Mặc định chọn 'approve'.")
                user_choice = "approve"

            state.user_choice = user_choice

            if user_choice == "approve":
                print("✅ Bạn đã phê duyệt vision.")
            elif user_choice == "edit":
                print("📝 Chuyển sang chế độ chỉnh sửa...")

        except Exception as e:
            print(f"❌ Lỗi khi nhận input: {e}. Mặc định chọn 'approve'.")
            state.user_choice = "approve"

        return state

    def reason(self, state: VisionState) -> VisionState:
        """Reason - Thu thập lý do chỉnh sửa từ user.

        Theo sơ đồ:
        - User nhập lý do chỉnh sửa
        - Lưu edit_reason vào state
        - Sau đó quay lại generate để tạo lại với feedback
        """
        print("\n" + "="*80)
        print("📝 REASON - THU THẬP LÝ DO CHỈNH SỬA")
        print("="*80)
        print("💡 Hãy mô tả những điểm bạn muốn chỉnh sửa trong Product Vision.")
        print("   Ví dụ:")
        print("   - Vision statement chưa đủ inspiring")
        print("   - Thiếu functional requirement về authentication")
        print("   - Performance requirement cần cụ thể hơn")
        print("="*80 + "\n")

        try:
            edit_reason = input("👤 Lý do chỉnh sửa của bạn: ").strip()

            if not edit_reason:
                print("⚠️  Không nhận được lý do chỉnh sửa. Sử dụng lý do mặc định.")
                edit_reason = "User requested edits without specific reason"

            state.edit_reason = edit_reason
            print(f"\n✓ Đã ghi nhận: {edit_reason}")

            # Add to messages for context
            state.messages.append(HumanMessage(content=f"Edit request: {edit_reason}"))

            # Create structured output for logging
            reason_output = {
                "edit_reason": edit_reason,
                "timestamp": "current",
                "will_regenerate": True
            }

            print("\n📊 Structured Output từ reason:")
            print(json.dumps(reason_output, ensure_ascii=False, indent=2))
            print()

            print("🔄 Sẽ tạo lại Product Vision với feedback của bạn...")

        except Exception as e:
            print(f"❌ Lỗi khi thu thập lý do: {e}")
            state.edit_reason = "Error collecting edit reason"

        return state

    def preview_branch(self, state: VisionState) -> str:
        """Quyết định luồng sau preview node.

        Theo sơ đồ:
        - Nếu user chọn "approve" → finalize
        - Nếu user chọn "edit" → reason
        """
        if state.user_choice == "approve":
            return "finalize"
        elif state.user_choice == "edit":
            return "reason"
        else:
            # Default: finalize
            return "finalize"

    def finalize(self, state: VisionState) -> VisionState:
        """Finalize - Lưu product_vision.json và generate summary.md với structured output.

        Theo sơ đồ:
        - Lưu product_vision.json
        - Generate summary.md (markdown format)
        - Update status = "completed"
        """
        print("\n" + "="*80)
        print("✅ FINALIZE - HOÀN TẤT PRODUCT VISION & PRD")
        print("="*80)

        # Prepare vision for finalization
        vision_text = json.dumps(state.product_vision, ensure_ascii=False, indent=2)
        prompt = FINALIZE_PROMPT.format(vision=vision_text)

        try:
            # Use structured output with Pydantic model
            structured_llm = self._llm("gpt-4o", 0.3).with_structured_output(FinalizeOutput)
            finalize_result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Update state
            state.summary_markdown = finalize_result.summary_markdown
            state.status = "completed"

            # Update product_vision with final summary
            state.product_vision["product_name"] = finalize_result.product_name
            state.product_vision["vision_statement_final"] = finalize_result.vision_statement
            state.product_vision["summary_markdown"] = finalize_result.summary_markdown

            # Print final output
            print(f"\n✓ Finalize completed")
            print(f"   Product Name: {finalize_result.product_name}")
            print(f"   Status: {state.status}")
            print(f"\n📄 SUMMARY MARKDOWN:")
            print("="*80)
            print(finalize_result.summary_markdown)
            print("="*80)

            print("\n📊 Structured Output từ finalize:")
            print(json.dumps(finalize_result.model_dump(), ensure_ascii=False, indent=2))
            print()

            # Print final product_vision JSON
            print("\n💾 FINAL PRODUCT VISION JSON:")
            print(json.dumps(state.product_vision, ensure_ascii=False, indent=2))
            print()

        except Exception as e:
            print(f"❌ Lỗi khi finalize vision: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_finalizing"
            state.summary_markdown = "Error during finalization"

        print("\n" + "="*80)
        print(f"✅ HOÀN TẤT - Status: {state.status}")
        print("="*80 + "\n")

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

        # Convert messages to serializable format before returning
        if final_state:
            # Extract the actual state from the output (it's wrapped in a node key)
            for node_name, state_data in final_state.items():
                if isinstance(state_data, dict) and "messages" in state_data:
                    # Convert BaseMessage objects to dicts
                    serializable_messages = []
                    for msg in state_data.get("messages", []):
                        if hasattr(msg, "dict"):  # Pydantic v1
                            serializable_messages.append(msg.dict())
                        elif hasattr(msg, "model_dump"):  # Pydantic v2
                            serializable_messages.append(msg.model_dump())
                        else:
                            # Fallback for plain objects
                            serializable_messages.append({
                                "type": msg.__class__.__name__,
                                "content": str(msg.content) if hasattr(msg, "content") else str(msg)
                            })
                    state_data["messages"] = serializable_messages

        return final_state or {}