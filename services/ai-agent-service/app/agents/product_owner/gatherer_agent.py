"""Lớp này chứa LangGraph Agent/workflow và các tương tác với LLM cho gatherer agent."""

import json
import os
import re
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from templates.prompts.product_owner.gatherer import (
    EVALUATE_PROMPT,
    CLARIFY_PROMPT,
    SUGGEST_PROMPT,
    ASK_USER_PROMPT,
    GENERATE_PROMPT,
    VALIDATE_PROMPT,
    FINALIZE_PROMPT,
    EDIT_MODE_PROMPT,
    FORCE_GENERATE_PROMPT,
)
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


class EvaluateOutput(BaseModel):
    gaps: list[str] = Field(description="Danh sách các thông tin còn thiếu")
    score: float = Field(description="Điểm đánh giá độ đầy đủ", ge=0.0, le=1.0)
    status: Literal["incomplete", "done"] = Field(
        description="Trạng thái: 'incomplete' nếu score < 0.8, 'done' nếu score >= 0.8"
    )
    confidence: float = Field(description="Độ tin cậy đánh giá", ge=0.0, le=1.0)
    message: str = Field(description="Lý do")


class EvaluateMessageOutput(BaseModel):
    is_unclear: bool = Field(
        description="True nếu message mơ hồ/không rõ ràng, False nếu rõ ràng"
    )
    reason: str = Field(description="Lý do đánh giá message là unclear hoặc clear")


class ClarifyOutput(BaseModel):
    summary: str = Field(description="Tóm tắt những gì đã hiểu từ cuộc hội thoại")
    unclear_points: list[str] = Field(
        description="Danh sách các điểm còn mơ hồ hoặc cần làm rõ"
    )
    clarified_gaps: list[str] = Field(
        description="Danh sách gaps đã được làm rõ và cần ưu tiên thu thập"
    )
    message_to_user: str = Field(
        description="Thông điệp gửi đến user để xác nhận hiểu biết và yêu cầu làm rõ"
    )


class FilledGap(BaseModel):
    gap_name: str = Field(description="Tên của gap")
    suggested_value: str = Field(description="Giá trị gợi ý để fill gap")
    reason: str = Field(description="Lý do ngắn gọn tại sao gợi ý giá trị này")


class SuggestOutput(BaseModel):
    prioritized_gaps: list[str] = Field(
        description="Danh sách gaps còn lại chưa fill được, sắp xếp theo độ ưu tiên"
    )
    filled_gaps: list[FilledGap] = Field(
        description="Danh sách các gaps đã gợi ý fill với giá trị và lý do"
    )


class CollectInputsOutput(BaseModel):
    total_messages: int = Field(description="Tổng số messages trong context")
    new_input_received: bool = Field(description="True nếu có input mới từ user")
    last_message_type: str = Field(description="Loại message cuối: human hoặc ai")
    last_message_preview: str = Field(
        description="Preview 200 ký tự đầu của message cuối"
    )
    context_summary: str = Field(description="Tóm tắt ngắn gọn context hiện tại")


class AskUserOutput(BaseModel):
    questions: list[str] = Field(
        description="Danh sách tối đa 3 câu hỏi để thu thập thông tin cho các gaps"
    )


class WaitForUserOutput(BaseModel):
    has_responses: bool = Field(
        description="True nếu user đã trả lời ít nhất 1 câu hỏi"
    )
    answered_count: int = Field(description="Số câu hỏi đã được trả lời")
    skipped_count: int = Field(description="Số câu hỏi bị bỏ qua")
    skip_all: bool = Field(description="True nếu user chọn skip_all")
    user_responses: list[dict[str, str]] = Field(
        description="Danh sách {question, answer} của các câu đã trả lời"
    )
    status: str = Field(
        description="Trạng thái: user_responded, skipped_all, no_responses, hoặc error"
    )
    message: str = Field(description="Thông điệp tóm tắt kết quả thu thập")


class GenerateOutput(BaseModel):
    product_name: str = Field(description="Tên sản phẩm")
    description: str = Field(description="Mô tả chi tiết sản phẩm")
    target_audience: list[str] = Field(description="Danh sách đối tượng mục tiêu")
    key_features: list[str] = Field(description="Danh sách tính năng chính")
    benefits: list[str] = Field(description="Danh sách lợi ích")
    competitors: list[str] = Field(
        default_factory=list, description="Danh sách đối thủ cạnh tranh"
    )
    completeness_note: str = Field(description="Ghi chú về mức độ hoàn thiện")


class EditModeOutput(BaseModel):
    product_name: str = Field(description="Tên sản phẩm")
    description: str = Field(description="Mô tả chi tiết sản phẩm")
    target_audience: list[str] = Field(description="Danh sách đối tượng mục tiêu")
    key_features: list[str] = Field(description="Danh sách tính năng chính")
    benefits: list[str] = Field(description="Danh sách lợi ích")
    competitors: list[str] = Field(
        default_factory=list, description="Danh sách đối thủ cạnh tranh"
    )
    completeness_note: str = Field(description="Ghi chú về thay đổi đã áp dụng")


class ForceGenerateOutput(BaseModel):
    product_name: str = Field(description="Tên sản phẩm")
    description: str = Field(description="Mô tả chi tiết sản phẩm")
    target_audience: list[str] = Field(description="Danh sách đối tượng mục tiêu")
    key_features: list[str] = Field(description="Danh sách tính năng chính")
    benefits: list[str] = Field(description="Danh sách lợi ích")
    competitors: list[str] = Field(
        default_factory=list, description="Danh sách đối thủ cạnh tranh"
    )
    completeness_note: str = Field(
        description="Ghi chú về mức độ hoàn thiện và các phần suy luận"
    )
    incomplete_flag: bool = Field(
        description="Flag đánh dấu brief chưa hoàn chỉnh", default=True
    )


class ValidateOutput(BaseModel):
    is_valid: bool = Field(description="True nếu brief đạt yêu cầu tối thiểu")
    confidence_score: float = Field(description="Độ tin cậy của brief", ge=0.0, le=1.0)
    completeness_score: float = Field(
        description="Điểm đánh giá độ đầy đủ", ge=0.0, le=1.0
    )
    missing_fields: list[str] = Field(
        description="Danh sách fields còn thiếu hoặc chưa đầy đủ"
    )
    validation_message: str = Field(
        description="Giải thích ngắn gọn kết quả validation"
    )


class FinalizeOutput(BaseModel):
    product_name: str = Field(description="Tên sản phẩm")
    executive_summary: str = Field(description="Tóm tắt điều hành 2-3 câu")
    target_users: str = Field(description="Đối tượng mục tiêu chính (1 câu ngắn)")
    top_features: list[str] = Field(description="Danh sách 3-5 tính năng nổi bật")
    core_value: str = Field(description="Giá trị cốt lõi mang lại (1-2 câu)")
    summary_markdown: str = Field(description="Tóm tắt đầy đủ theo format markdown")


class State(BaseModel):
    """Trạng thái cho quy trình làm việc của gatherer agent."""

    messages: list[BaseMessage] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    retry_count: int = 0
    gaps: list[str] = Field(default_factory=list)
    score: float = 0.0
    status: str = "initial"
    confidence: float = 0.0
    message: str = ""
    brief: dict = Field(default_factory=dict)
    incomplete_flag: bool = False
    questions: list[str] = Field(default_factory=list)
    unclear_input: list[str] = Field(default_factory=list)
    user_choice: Literal["approve", "edit", "regenerate", "skip", ""] = ""
    edit_changes: str = ""
    user_skipped: bool = False


class GathererAgent:
    """Gatherer Agent để thu thập thông tin sản phẩm giúp tạo backlog trong tương lai."""

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo gatherer agent.

        Args:
            session_id: Session ID tùy chọn để theo dõi
            user_id: User ID tùy chọn để theo dõi
        """
        self.session_id = session_id
        self.user_id = user_id

        self.langfuse_handler = CallbackHandler()

        self.graph = self._build_graph()

    def _llm(self, model: str, temperature: str) -> ChatOpenAI:
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
            return llm
        except Exception:
            return ""

    def _build_graph(self) -> StateGraph:
        """Xây dựng quy trình làm việc LangGraph."""
        graph_builder = StateGraph(State)

        graph_builder.add_node("initialize", self._initialize)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("clarify", self.clarify)
        graph_builder.add_node("suggest", self.suggest)
        graph_builder.add_node("ask_user", self.ask_user)
        graph_builder.add_node("increment_iteration", self.increment_iteration)
        graph_builder.add_node("wait_for_user", self.wait_for_user)
        graph_builder.add_node("generate", self.generate)
        graph_builder.add_node("force_generate", self.force_generate)
        graph_builder.add_node("validate", self.validate)
        graph_builder.add_node("retry_decision", self.retry_decision)
        graph_builder.add_node("preview", self.preview)
        graph_builder.add_node("edit_mode", self.edit_mode)
        graph_builder.add_node("finalize", self.finalize)

        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "evaluate")
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        graph_builder.add_edge("clarify", "suggest")
        graph_builder.add_edge("suggest", "ask_user")
        graph_builder.add_edge("ask_user", "increment_iteration")
        graph_builder.add_edge("increment_iteration", "wait_for_user")
        graph_builder.add_conditional_edges("wait_for_user", self.wait_for_user_branch)
        graph_builder.add_edge("generate", "validate")
        graph_builder.add_edge("force_generate", "validate")
        graph_builder.add_conditional_edges("validate", self.validate_branch)
        graph_builder.add_conditional_edges("preview", self.preview_branch)
        graph_builder.add_conditional_edges(
            "retry_decision", self.retry_decision_branch
        )
        graph_builder.add_edge("edit_mode", "validate")
        graph_builder.add_edge("finalize", END)
        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    def _initialize(self, state: State) -> State:
        print(state)
        """Khởi tạo trạng thái."""
        return state

    def evaluate_message(self, message: str) -> bool:
        """Đánh giá xem message cuối cùng của người dùng có unclear hay không bằng regex patterns."""
        message_lower = message.lower().strip()

        unclear_patterns = [
            r"\b(nó|cái đó|cái này|thứ đó|thứ này|chỗ đó|chỗ này|cái kia|thằng đó)\b",
            r"\b(như trên|như vậy|như thế|y như|y chang|tương tự|giống vậy|như kia)\b",
            r"^.{1,10}$",
            r"^\s*(sao|thế nào|như nào|ra sao|gì|à|hả|ừ|uh|uhm)\s*\??\s*$",
            r"^\s*(có|không|ok|được|rồi|ừ|uh|yes|no|yeah|nope)\s*$",
        ]

        for pattern in unclear_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def evaluate(self, state: State) -> State:
        """Đánh giá độ đầy đủ của cuộc hội thoại để tạo bản tóm tắt sử dụng structured output."""
        if state.messages:
            last_message = state.messages[-1]
            if last_message.type == "human":
                is_unclear = self.evaluate_message(last_message.content)
                if is_unclear:
                    state.unclear_input.append(last_message.content)

        formatted_messages = (
            "\n".join(
                [
                    f"{i}. [{'User' if msg.type=='human' else 'Assistant'}]: "
                    f"{msg.content if hasattr(msg, 'content') else str(msg)}"
                    for i, msg in enumerate(state.messages, 1)
                ]
            )
            if state.messages
            else "Chưa có thông tin nào được thu thập."
        )

        prompt = EVALUATE_PROMPT.format(messages=formatted_messages)

        structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(
            EvaluateOutput
        )
        evaluation = structured_llm.invoke([HumanMessage(content=prompt)])

        state.gaps = evaluation.gaps
        state.score = evaluation.score
        state.confidence = evaluation.confidence
        state.message = evaluation.message

        state.status = "done" if evaluation.score >= 0.8 else "incomplete"

        return state

    def force_generate(self, state: State) -> State:
        """Tạo brief với thông tin hiện có dù chưa đầy đủ khi đạt max_iterations.

        Theo sơ đồ:
        - Input: cuộc hội thoại khi iteration_count >= max_iterations
        - Generate brief với available info, flag: incomplete
        - Output: ForceGenerateOutput structured JSON
        """
        state.user_choice = ""

        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content}"
                for msg in state.messages
            ]
        )

        prompt = FORCE_GENERATE_PROMPT.format(messages=formatted_messages)

        try:
            structured_llm = self._llm("gpt-4.1", 0.3).with_structured_output(
                ForceGenerateOutput
            )
            brief_output = structured_llm.invoke([HumanMessage(content=prompt)])

            state.brief = brief_output.model_dump()
            state.incomplete_flag = brief_output.incomplete_flag

            print("\n" + "=" * 80)
            print("⚠️  FORCE GENERATE - TẠO BRIEF VỚI THÔNG TIN CHƯA ĐẦY ĐỦ")
            print("=" * 80)
            print(f"⚠️  Đã đạt số lần lặp tối đa ({state.max_iterations})")
            print(
                f"⚠️  Brief được tạo với thông tin hiện có, một số phần có thể được suy luận"
            )
            print("-" * 80)
            print(json.dumps(state.brief, ensure_ascii=False, indent=2))
            print("=" * 80 + "\n")

            print("\n📊 Structured Output từ force_generate:")
            print(json.dumps(brief_output.model_dump(), ensure_ascii=False, indent=2))
            print()

        except Exception as e:
            print(f"❌ Lỗi khi force generate brief: {e}")
            state.brief = {
                "product_name": "Chưa xác định",
                "description": f"Brief được tạo từ {len(state.messages)} messages với thông tin chưa đầy đủ",
                "target_audience": ["Chưa xác định"],
                "key_features": ["Chưa có thông tin đầy đủ"],
                "benefits": ["Chưa có thông tin đầy đủ"],
                "competitors": [],
                "completeness_note": f"Lỗi khi force generate: {str(e)}",
                "incomplete_flag": True,
            }
            state.incomplete_flag = True

        return state

    def clarify(self, state: State) -> State:
        """Làm rõ các thông tin mơ hồ hoặc không rõ ràng trong cuộc hội thoại."""
        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content}"
                for msg in state.messages
            ]
        )

        unclear_inputs = (
            "\n".join([f"- {unclear}" for unclear in state.unclear_input])
            if state.unclear_input
            else "Không có"
        )

        formatted_gaps = (
            "\n".join([f"- {gap}" for gap in state.gaps]) if state.gaps else "Không có"
        )

        prompt = CLARIFY_PROMPT.format(
            messages=formatted_messages,
            unclear_inputs=unclear_inputs,
            gaps=formatted_gaps,
        )

        structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(ClarifyOutput)
        clarify_result = structured_llm.invoke([HumanMessage(content=prompt)])

        state.gaps = clarify_result.clarified_gaps

        state.messages.append(AIMessage(content=clarify_result.message_to_user))

        return state

    def suggest(self, state: State) -> State:
        """Gợi ý nội dung để tự động fill các gaps quan trọng, giúp thu thập thông tin nhanh hơn mà không bắt user nghĩ tất cả."""
        formatted_gaps = (
            "\n".join([f"- {gap}" for gap in state.gaps])
            if state.gaps
            else "Không có gaps"
        )

        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content[:500]}"
                for msg in state.messages[-10:]
            ]
        )

        prompt = SUGGEST_PROMPT.format(gaps=formatted_gaps, messages=formatted_messages)

        try:
            structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(
                SuggestOutput
            )
            suggest_result = structured_llm.invoke([HumanMessage(content=prompt)])

            state.gaps = suggest_result.prioritized_gaps

            if suggest_result.filled_gaps:
                filled_msg = (
                    "Các thông tin được gợi ý tự động fill dựa trên ngữ cảnh:\n\n"
                    + "\n\n".join(
                        [
                            f"**{fg.gap_name}**\n• Giá trị: {fg.suggested_value}\n• Lý do: {fg.reason}"
                            for fg in suggest_result.filled_gaps
                        ]
                    )
                    + "\n\nNếu không chính xác, vui lòng chỉnh sửa."
                )
                state.messages.append(AIMessage(content=filled_msg))
        except Exception as e:
            print(f"Error in suggest: {e}")
            pass

        return state

    def ask_user(self, state: State) -> State:
        """Tạo câu hỏi để thu thập thông tin cho các gaps còn thiếu."""
        formatted_gaps = (
            "\n".join([f"- {gap}" for gap in state.gaps])
            if state.gaps
            else "Không có gaps"
        )

        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content[:500]}"
                for msg in state.messages[-10:]
            ]
        )

        prompt = ASK_USER_PROMPT.format(
            gaps=formatted_gaps, messages=formatted_messages
        )

        try:
            structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(
                AskUserOutput
            )
            ask_result = structured_llm.invoke([HumanMessage(content=prompt)])
            state.questions = ask_result.questions
            state.status = "awaiting_user"
        except Exception as e:
            print(f"Error in ask_user: {e}")
            state.questions = []
            state.status = "error_generating_questions"

        print(f"\n📝 Đã tạo {len(state.questions)} câu hỏi để thu thập thông tin.")

        return state

    def increment_iteration(self, state: State) -> State:
        """Tăng iteration count và checkpoint state để có thể resume sau này."""
        state.iteration_count += 1
        print(
            f"\n=== Iteration {state.iteration_count}/{state.max_iterations} completed ==="
        )
        print(f"Current gaps: {len(state.gaps)}")
        print(
            f"Score: {state.score}, Confidence: {state.confidence}, Status: {state.status}"
        )

        return state

    def wait_for_user(self, state: State) -> State:
        """Hỏi user từng câu một và đợi response với timeout 10 phút cho mỗi câu. Trả về structured output."""
        import signal

        print("\n" + "=" * 60)
        print("💬 PHẦN HỎI ĐÁP - Thu thập thông tin")
        print("=" * 60)
        print("💡 Bạn có thể:")
        print("  - Trả lời từng câu hỏi")
        print("  - Gõ 'skip' để bỏ qua câu hiện tại")
        print("  - Gõ 'skip_all' để bỏ qua tất cả và tạo brief với thông tin hiện có")
        print("  - Timeout: 10 phút cho mỗi câu hỏi")
        print("=" * 60 + "\n")

        def timeout_handler(signum, frame):
            raise TimeoutError("Timeout")

        has_responses = False
        skip_all = False
        answered_count = 0
        skipped_count = 0
        user_responses = []

        for idx, question in enumerate(state.questions, 1):
            if skip_all:
                break

            state.messages.append(AIMessage(content=question))

            print(f"\n[Câu hỏi {idx}/{len(state.questions)}]")
            print(f"❓ {question}\n")

            try:
                if hasattr(signal, "SIGALRM"):
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(600)

                user_input = input("👤 Câu trả lời của bạn: ").strip()

                if hasattr(signal, "SIGALRM"):
                    signal.alarm(0)

                if user_input.lower() == "skip_all":
                    skip_all = True
                    print("\n⊘ Bạn đã chọn bỏ qua tất cả câu hỏi còn lại.")
                    break
                elif user_input.lower() == "skip":
                    print("⊘ Bỏ qua câu này.\n")
                    skipped_count += 1
                    continue
                elif user_input:
                    state.messages.append(HumanMessage(content=user_input))
                    user_responses.append({"question": question, "answer": user_input})
                    has_responses = True
                    answered_count += 1
                    print("✓ Đã ghi nhận câu trả lời.\n")
                else:
                    print("⚠ Câu trả lời trống, bỏ qua.\n")
                    skipped_count += 1

            except TimeoutError:
                print(f"\n⏰ Timeout cho câu hỏi {idx}. Bỏ qua câu này.")
                skipped_count += 1
                continue
            except Exception as e:
                print(f"\n❌ Lỗi: {e}. Bỏ qua câu này.")
                skipped_count += 1
                continue

        if skip_all:
            output = WaitForUserOutput(
                has_responses=has_responses,
                answered_count=answered_count,
                skipped_count=skipped_count,
                skip_all=True,
                user_responses=user_responses,
                status="skipped_all",
                message=f"Đã bỏ qua tất cả câu hỏi. Trả lời: {answered_count}, Bỏ qua: {skipped_count}",
            )
            state.user_skipped = True
            state.status = "skipped_all"
            print("\n" + "=" * 60)
            print("⊘ Đã bỏ qua tất cả câu hỏi. Sẽ tạo brief với thông tin hiện có.")
            print("=" * 60 + "\n")
        elif has_responses:
            output = WaitForUserOutput(
                has_responses=True,
                answered_count=answered_count,
                skipped_count=skipped_count,
                skip_all=False,
                user_responses=user_responses,
                status="user_responded",
                message=f"Thu thập thành công {answered_count} câu trả lời, bỏ qua {skipped_count} câu",
            )
            state.user_skipped = False
            state.status = "user_responded"
            print("\n" + "=" * 60)
            print("✓ Đã hoàn thành phần hỏi đáp. Tiếp tục thu thập thông tin...")
            print("=" * 60 + "\n")
        else:
            output = WaitForUserOutput(
                has_responses=False,
                answered_count=0,
                skipped_count=skipped_count,
                skip_all=False,
                user_responses=[],
                status="no_responses",
                message=f"Không có câu trả lời nào. Bỏ qua: {skipped_count} câu",
            )
            state.user_skipped = True
            state.status = "no_responses"
            print("\n" + "=" * 60)
            print("⚠ Không có câu trả lời nào. Sẽ tạo brief với thông tin hiện có.")
            print("=" * 60 + "\n")

        print("\n📊 Structured Output:")
        print(json.dumps(output.model_dump(), ensure_ascii=False, indent=2))
        print()

        return state

    def generate(self, state: State) -> State:
        """Tạo Product Brief hoàn chỉnh từ thông tin đã thu thập, output structured JSON."""
        state.user_choice = ""

        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content}"
                for msg in state.messages
            ]
        )

        prompt = GENERATE_PROMPT.format(messages=formatted_messages)

        try:
            structured_llm = self._llm("gpt-4.1", 0.3).with_structured_output(
                GenerateOutput
            )
            brief_output = structured_llm.invoke([HumanMessage(content=prompt)])

            state.brief = brief_output.model_dump()

            print("\n" + "=" * 80)
            print("📄 PRODUCT BRIEF ĐÃ TẠO")
            print("=" * 80)
            print(json.dumps(state.brief, ensure_ascii=False, indent=2))
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ Lỗi khi tạo brief: {e}")
            state.brief = {
                "product_name": "Chưa xác định",
                "description": f"Brief được tạo từ {len(state.messages)} messages",
                "target_audience": [],
                "key_features": [],
                "benefits": [],
                "competitors": [],
                "completeness_note": f"Lỗi khi generate: {str(e)}",
            }

        return state

    def validate(self, state: State) -> State:
        """Validate brief đã tạo bằng llm_reflect - kiểm tra completeness và calculate confidence_score.

        Theo sơ đồ:
        - Input: brief từ force_generate
        - Sử dụng llm_reflect để phân tích brief
        - Output: ValidateOutput structured JSON
        - Branch logic sẽ được xử lý ở validate_branch
        """
        brief_text = (
            json.dumps(state.brief, ensure_ascii=False, indent=2)
            if state.brief
            else "Chưa có brief"
        )

        formatted_messages = "\n".join(
            [
                f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content[:300]}"
                for msg in state.messages[-10:]
            ]
        )

        prompt = VALIDATE_PROMPT.format(brief=brief_text, messages=formatted_messages)

        try:
            structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(
                ValidateOutput
            )
            validation_result = structured_llm.invoke([HumanMessage(content=prompt)])

            state.confidence = validation_result.confidence_score
            state.score = validation_result.completeness_score

            print("\n" + "=" * 60)
            print("✓ Validation Result:")
            print(f"  - Valid: {validation_result.is_valid}")
            print(f"  - Confidence: {state.confidence:.2f}")
            print(f"  - Completeness: {state.score:.2f}")
            print(f"  - Message: {validation_result.validation_message}")

            if validation_result.missing_fields:
                print(f"  - Missing: {', '.join(validation_result.missing_fields)}")

            print("=" * 60 + "\n")

            print("\n📊 Structured Output từ validate:")
            print(
                json.dumps(validation_result.model_dump(), ensure_ascii=False, indent=2)
            )
            print()

        except Exception as e:
            print(f"❌ Error in validate: {e}")
            state.confidence = 0.3
            state.score = 0.3

        return state

    def retry_decision(self, state: State) -> State:
        """Tăng retry_count để theo dõi số lần retry validate.

        Theo sơ đồ:
        - Input: brief không hợp lệ hoặc confidence ≤ 0.7
        - Tăng retry_count
        - Branch logic sẽ được xử lý ở retry_decision_branch
        """
        state.retry_count += 1

        print("\n" + "=" * 60)
        print(f"🔄 RETRY DECISION - Lần thử {state.retry_count}")
        print(f"  - Confidence: {state.confidence:.2f}")
        print(f"  - Completeness: {state.score:.2f}")
        print("=" * 60 + "\n")

        return state

    def preview(self, state: State) -> State:
        """Hiển thị brief cho user và hỏi: Approve/Edit/Regenerate.

        Theo sơ đồ:
        - Format brief và show to user
        - Hỏi user lựa chọn: Approve/Edit/Regenerate (với timeout option)
        - Cập nhật user_choice vào state
        - Nếu chọn Edit, thu thập edit_changes
        """
        print("\n" + "=" * 80)
        print("📋 PREVIEW - XEM TRƯỚC PRODUCT BRIEF")
        print("=" * 80)
        print(f"🚩 Cờ chưa hoàn chỉnh: {state.incomplete_flag}")
        print("\nNội dung Brief:")
        print("-" * 80)
        print(json.dumps(state.brief, ensure_ascii=False, indent=2))
        print("=" * 80 + "\n")

        print("💡 Bạn có thể:")
        print("  1. Gõ 'approve' để phê duyệt brief")
        print("  2. Gõ 'edit' để chỉnh sửa brief")
        print("  3. Gõ 'regenerate' để tạo lại brief")
        print()

        try:
            user_choice = (
                input("👤 Lựa chọn của bạn (approve/edit/regenerate): ").strip().lower()
            )

            if user_choice not in ["approve", "edit", "regenerate"]:
                print(
                    f"⚠ Lựa chọn không hợp lệ: '{user_choice}'. Mặc định chọn 'approve'."
                )
                user_choice = "approve"

            state.user_choice = user_choice

            if user_choice == "edit":
                print("\n📝 Nhập các thay đổi bạn muốn áp dụng vào brief:")
                edit_changes = input("👤 Thay đổi: ").strip()
                state.edit_changes = edit_changes
                print(f"✓ Đã ghi nhận thay đổi: {edit_changes[:100]}...")
            elif user_choice == "approve":
                print("✓ Bạn đã phê duyệt brief.")
            elif user_choice == "regenerate":
                print("🔄 Sẽ tạo lại brief.")
                state.retry_count = 0

        except Exception as e:
            print(f"❌ Lỗi khi nhận input: {e}. Mặc định chọn 'approve'.")
            state.user_choice = "approve"

        return state

    def edit_mode(self, state: State) -> State:
        """Áp dụng các thay đổi từ user vào brief và re-validate.

        Theo sơ đồ:
        - Input: edit_changes từ preview node
        - Apply user changes vào brief
        - Re-validate để đảm bảo brief vẫn hợp lệ
        """
        state.user_choice = ""

        brief_text = json.dumps(state.brief, ensure_ascii=False, indent=2)

        prompt = EDIT_MODE_PROMPT.format(
            brief=brief_text, edit_changes=state.edit_changes
        )

        try:
            structured_llm = self._llm("gpt-4.1", 0.3).with_structured_output(
                EditModeOutput
            )
            edited_brief = structured_llm.invoke([HumanMessage(content=prompt)])

            state.brief = edited_brief.model_dump()

            state.edit_changes = ""

            print("\n" + "=" * 60)
            print("✏️ ĐÃ ÁP DỤNG THAY ĐỔI VÀO BRIEF")
            print("=" * 60)
            print(json.dumps(state.brief, ensure_ascii=False, indent=2))
            print("=" * 60 + "\n")

            print("\n📊 Structured Output từ edit_mode:")
            print(json.dumps(edited_brief.model_dump(), ensure_ascii=False, indent=2))
            print()

        except Exception as e:
            print(f"❌ Lỗi khi áp dụng thay đổi: {e}")
            state.edit_changes = ""

        return state

    def finalize(self, state: State) -> State:
        """Lưu brief và tạo summary cuối cùng với structured output.

        Theo sơ đồ:
        - Input: brief đã được approve
        - Generate summary từ brief với structured JSON output
        - Cập nhật status = "completed"
        - Output: FinalizeOutput structured JSON
        """
        brief_text = json.dumps(state.brief, ensure_ascii=False, indent=2)

        prompt = FINALIZE_PROMPT.format(brief=brief_text)

        try:
            structured_llm = self._llm("gpt-4.1", 0.3).with_structured_output(
                FinalizeOutput
            )
            finalize_result = structured_llm.invoke([HumanMessage(content=prompt)])

            state.status = "completed"

            print("\n" + "=" * 80)
            print("✅ HOÀN TẤT - PRODUCT BRIEF ĐÃ ĐƯỢC PHÊ DUYỆT")
            print("=" * 80)
            print("\n📊 TÓM TẮT CUỐI CÙNG:\n")
            print(finalize_result.summary_markdown)
            print("\n" + "=" * 80)
            print(f"📈 Thống kê:")
            print(f"  - Số lần lặp: {state.iteration_count}/{state.max_iterations}")
            print(f"  - Số lần retry: {state.retry_count}")
            print(f"  - Confidence score: {state.confidence:.2f}")
            print(f"  - Completeness score: {state.score:.2f}")
            print(f"  - Tổng số messages: {len(state.messages)}")
            print("=" * 80 + "\n")

            print("\n📄 Structured Output từ finalize:")
            print(
                json.dumps(finalize_result.model_dump(), ensure_ascii=False, indent=2)
            )
            print()

        except Exception as e:
            print(f"❌ Lỗi khi tạo tóm tắt: {e}")
            state.status = "completed_with_errors"
            print("\n" + "=" * 80)
            print("⚠ HOÀN TẤT VỚI LỖI")
            print("=" * 80)
            print(f"Brief đã được lưu nhưng không thể tạo tóm tắt: {str(e)}")
            print("=" * 80 + "\n")

        return state

    # Conditional branches
    def evaluate_branch(self, state: State) -> str:
        """Quyết định luồng sau evaluate node theo sơ đồ.

        Theo sơ đồ:
        - Nếu iteration_count >= max_iterations → force_generate
        - Nếu status == done OR score >= 0.8 → generate
        - Nếu confidence <= 0.6 → clarify (low confidence)
        - Nếu có gaps AND confidence > 0.6 → suggest
        """
        if state.iteration_count >= state.max_iterations:
            return "force_generate"
        elif state.status == "done" or state.score >= 0.8:
            return "generate"
        elif state.confidence <= 0.6:
            return "clarify"
        elif len(state.gaps) > 0 and state.confidence > 0.6:
            return "suggest"
        else:
            return "generate"

    def wait_for_user_branch(self, state: State) -> str:
        """Quyết định next node sau wait_for_user."""
        if state.user_skipped or state.status in [
            "skipped_all",
            "no_responses",
            "error_generating_questions",
        ]:
            return "generate"
        elif state.status == "user_responded":
            return "evaluate"
        else:
            return "generate"

    def validate_branch(self, state: State) -> str:
        """Quyết định luồng sau validate node theo sơ đồ.

        Theo sơ đồ:
        - Nếu valid AND confidence > 0.7 → preview
        - Nếu invalid OR confidence ≤ 0.7 → retry_decision
        """
        if state.confidence > 0.7:
            return "preview"
        else:
            return "retry_decision"

    def retry_decision_branch(self, state: State) -> str:
        """Quyết định luồng sau retry_decision node theo sơ đồ.

        Theo sơ đồ:
        - Nếu retry_count >= 2 → preview (dù confidence thấp, vẫn cho user xem)
        - Nếu retry_count < 2 → generate (regenerate lại)
        """
        if state.retry_count >= 2:
            print(
                f"\n⚠️  Đã retry {state.retry_count} lần, chuyển sang preview để user quyết định.\n"
            )
            return "preview"
        else:
            print(f"\n🔄 Retry lần {state.retry_count + 1}, regenerate brief...\n")
            return "suggest"

    def preview_branch(self, state: State) -> str:
        """Quyết định luồng sau preview node theo sơ đồ.

        Theo sơ đồ:
        - Nếu user chọn "approve" → finalize
        - Nếu user chọn "edit" → edit_mode
        - Nếu user chọn "regenerate" → generate
        """
        if state.user_choice == "approve":
            return "finalize"
        elif state.user_choice == "edit":
            return "edit_mode"
        elif state.user_choice == "regenerate":
            return "generate"
        else:
            return "finalize"

    def run(
        self, initial_context: str = "", thread_id: str | None = None
    ) -> dict[str, Any]:
        """Chạy quy trình làm việc của gatherer agent.

        Args:
            initial_context: Ngữ cảnh ban đầu hoặc yêu cầu cho bản tóm tắt sản phẩm
            thread_id: ID để resume state (nếu None, dùng session_id hoặc default)

        Returns:
            dict: Trạng thái cuối cùng chứa bản tóm tắt đã tạo và các chỉ số đánh giá
        """
        if thread_id is None:
            thread_id = self.session_id or "default_thread"

        initial_state = State(
            messages=[HumanMessage(content=initial_context)] if initial_context else []
        )

        metadata = {}
        if self.session_id:
            metadata["langfuse_session_id"] = self.session_id
        if self.user_id:
            metadata["langfuse_user_id"] = self.user_id
        metadata["langfuse_tags"] = ["gatherer_agent"]

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "metadata": metadata,
            "recursion_limit": 50,
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump() if initial_state else None,
            config=config,
        ):
            final_state = output

        return final_state or {}
