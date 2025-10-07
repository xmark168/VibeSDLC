"""Lớp này chứa LangGraph Agent/workflow và các tương tác với LLM cho gatherer agent."""

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

from templates.prompts.product_owner.gatherer import EVALUATE_PROMPT, CLARIFY_PROMPT, SUGGEST_PROMPT, ASK_USER_PROMPT
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


class EvaluateOutput(BaseModel):
    gaps: list[str] = Field(description="Danh sách các thông tin còn thiếu")
    score: float = Field(description="Điểm đánh giá độ đầy đủ", ge=0.0, le=1.0)
    status: str = Field(description="Trạng thái: incomplete hoặc done")
    confidence: float = Field(description="Độ tin cậy đánh giá", ge=0.0, le=1.0)
    message: str = Field(description="Lý do")


class EvaluateMessageOutput(BaseModel):
    is_unclear: bool = Field(description="True nếu message mơ hồ/không rõ ràng, False nếu rõ ràng")
    reason: str = Field(description="Lý do đánh giá message là unclear hoặc clear")


class ClarifyOutput(BaseModel):
    summary: str = Field(description="Tóm tắt những gì đã hiểu từ cuộc hội thoại")
    unclear_points: list[str] = Field(description="Danh sách các điểm còn mơ hồ hoặc cần làm rõ")
    clarified_gaps: list[str] = Field(description="Danh sách gaps đã được làm rõ và cần ưu tiên thu thập")
    message_to_user: str = Field(description="Thông điệp gửi đến user để xác nhận hiểu biết và yêu cầu làm rõ")


class FilledGap(BaseModel):
    gap_name: str = Field(description="Tên của gap")
    suggested_value: str = Field(description="Giá trị gợi ý để fill gap")
    reason: str = Field(description="Lý do ngắn gọn tại sao gợi ý giá trị này")


class SuggestOutput(BaseModel):
    prioritized_gaps: list[str] = Field(description="Danh sách gaps còn lại chưa fill được, sắp xếp theo độ ưu tiên")
    filled_gaps: list[FilledGap] = Field(description="Danh sách các gaps đã gợi ý fill với giá trị và lý do")


class AskUserOutput(BaseModel):
    questions: list[str] = Field(description="Danh sách tối đa 3 câu hỏi để thu thập thông tin cho các gaps")


class State(BaseModel):
    """Trạng thái cho quy trình làm việc của gatherer agent."""

    messages: list[BaseMessage] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 5
    retry_count: int = 0
    gaps: list[str] = Field(default_factory=list)
    score: float = 0.0
    status: str = "initial"
    confidence: float = 0.0
    message: str = ""
    brief: dict =  Field(default_factory=dict)
    incomplete_flag: bool = False
    questions: list[str] = Field(default_factory=list)
    unclear_input: list[str] = Field(default_factory=list)
    user_choice: Literal["approve", "edit", "regenerate", ""] = ""
    edit_changes: str = ""


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

        # Initialize Langfuse callback handler
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
            # Avoid noisy context warnings when no active span
            return ""

    def _build_graph(self) -> StateGraph:
        """Xây dựng quy trình làm việc LangGraph."""
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("initialize", self._initialize)
        graph_builder.add_node("collect_inputs", self.collect_inputs)
        graph_builder.add_node("evaluate", self.evaluate)
        # graph_builder.add_node("force_generate", self.force_generate)
        # graph_builder.add_node("validate", self.validate)    
        # graph_builder.add_node("retry_decision", self.retry_decision)
        graph_builder.add_node("clarify", self.clarify)
        graph_builder.add_node("suggest", self.suggest)
        graph_builder.add_node("ask_user", self.ask_user)
        graph_builder.add_node("increment_iteration", self.increment_iteration)
        # graph_builder.add_node("preview", self.preview)
        # graph_builder.add_node("edit_mode", self.edit_mode)
        # graph_builder.add_node("finalize", self.finalize)
        # graph_builder.add_node("generate", self.generate)
        # # Add edges
        graph_builder.add_edge(START, "initialize")
        # graph_builder.add_edge("initialize", "collect_inputs")
        # graph_builder.add_edge("initialize", END)
        graph_builder.add_edge("collect_inputs", "evaluate")
        graph_builder.add_conditional_edges("initialize", self.initialize_branch)
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        graph_builder.add_edge("clarify", "suggest")
        graph_builder.add_edge("suggest", "ask_user")
        graph_builder.add_edge("ask_user", "increment_iteration")
        checkpointer = MemorySaver()  # Khởi tạo MemorySaver
        return graph_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["collect_inputs"]  # Pause trước node collect_inputs
        )

    def _initialize(self, state: State) -> State:
        print(state)
        """Khởi tạo trạng thái."""
        return state
    def collect_inputs(self, state: State) -> State:
        """Thu thập thông tin bổ sung từ người dùng để điền vào các khoảng trống thông tin."""
        

        return state
    
    def evaluate_message(self, message: str) -> bool:
        """Đánh giá xem message cuối cùng của người dùng có unclear hay không bằng regex patterns."""
        message_lower = message.lower().strip()

        # Patterns cho unclear messages (Vietnamese best practices)
        unclear_patterns = [
            # Đại từ mơ hồ
            r'\b(nó|cái đó|cái này|thứ đó|thứ này|chỗ đó|chỗ này|cái kia|thằng đó)\b',
            # Tham chiếu mơ hồ
            r'\b(như trên|như vậy|như thế|y như|y chang|tương tự|giống vậy|như kia)\b',
            # Thiếu thông tin cụ thể (câu quá ngắn < 10 ký tự)
            r'^.{1,10}$',
            # Câu hỏi mơ hồ không có ngữ cảnh
            r'^\s*(sao|thế nào|như nào|ra sao|gì|à|hả|ừ|uh|uhm)\s*\??\s*$',
            # Chỉ có yes/no không có ngữ cảnh
            r'^\s*(có|không|ok|được|rồi|ừ|uh|yes|no|yeah|nope)\s*$',
        ]

        # Check nếu match bất kỳ pattern nào
        for pattern in unclear_patterns:
            if re.search(pattern, message_lower):
                return True 

        # Clear nếu không match pattern nào
        return False

    def evaluate(self, state: State) -> State:
        """Đánh giá độ đầy đủ của cuộc hội thoại để tạo bản tóm tắt sử dụng structured output."""
        # Evaluate last message if it exists and is from user
        if state.messages:
            last_message = state.messages[-1]
            if last_message.type == "human":
                is_unclear = self.evaluate_message(last_message.content)
                if is_unclear:
                    # Add unclear message to unclear_input list
                    state.unclear_input.append(last_message.content)

        # Format messages
        formatted_messages = "\n".join([
            f"{i}. [{'User' if msg.type=='human' else 'Assistant'}]: "
            f"{msg.content if hasattr(msg, 'content') else str(msg)}"
            for i, msg in enumerate(state.messages, 1)
        ]) if state.messages else "Chưa có thông tin nào được thu thập."

        prompt = EVALUATE_PROMPT.format(messages=formatted_messages)

        # Use structured output with Pydantic model
        structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(EvaluateOutput)
        evaluation = structured_llm.invoke([HumanMessage(content=prompt)])

        # Update state
        state.gaps = evaluation.gaps
        state.score = evaluation.score
        state.status = evaluation.status
        state.confidence = evaluation.confidence
        state.message = evaluation.message
        return state

    
    # def force_generate(self, state: State) -> State:
    #     prompt = f"Tạo một brief sử dụng thông tin có sẵn từ cuộc trò chuyện, ngay cả khi chưa hoàn chỉnh:\n{state.messages}"
    #     response = self.llm.invoke(prompt)
    #     state.brief = response.content
    #     state.incomplete_flag = True
    #     return state

    # def validate(self, state: State) -> State:
    #     prompt = f"""Xác thực brief đã tạo về tính hoàn chỉnh và chính xác so với cuộc trò chuyện:
    #     Brief: {state.brief}
    #     Cuộc trò chuyện: {state.messages}
    #     Output dưới dạng JSON với valid (bool), confidence, score."""
    #     response = self.llm.invoke(prompt)
    #     try:
    #         parsed = json.loads(response.content)
    #         state.confidence = parsed.get("confidence", 0.0)
    #         state.score = parsed.get("score", 0.0)
    #     except:
    #         pass
    #     return state

    # def retry_decision(self, state: State) -> State:
    #     state.retry_count += 1
    #     return state

    def clarify(self, state: State) -> State:
        """Làm rõ các thông tin mơ hồ hoặc không rõ ràng trong cuộc hội thoại."""
        # Format messages
        formatted_messages = "\n".join([
            f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content}"
            for msg in state.messages
        ])

        # Format unclear inputs
        unclear_inputs = "\n".join([f"- {unclear}" for unclear in state.unclear_input]) if state.unclear_input else "Không có"

        # Format gaps
        formatted_gaps = "\n".join([f"- {gap}" for gap in state.gaps]) if state.gaps else "Không có"

        prompt = CLARIFY_PROMPT.format(
            messages=formatted_messages,
            unclear_inputs=unclear_inputs,
            gaps=formatted_gaps
        )

        # Use structured output with Pydantic model
        structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(ClarifyOutput)
        clarify_result = structured_llm.invoke([HumanMessage(content=prompt)])

        # Update state with clarified gaps for suggest node
        state.gaps = clarify_result.clarified_gaps

        # Append message to user
        state.messages.append(AIMessage(content=clarify_result.message_to_user))

        return state

    def suggest(self, state: State) -> State:
        """Gợi ý nội dung để tự động fill các gaps quan trọng, giúp thu thập thông tin nhanh hơn mà không bắt user nghĩ tất cả."""
        # Format gaps
        formatted_gaps = "\n".join([f"- {gap}" for gap in state.gaps]) if state.gaps else "Không có gaps"

        # Format messages - limit length to avoid overload
        formatted_messages = "\n".join([
            f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content[:500]}"  # Limit each message to 500 chars
            for msg in state.messages[-10:]  # Only take last 10 messages
        ])

        prompt = SUGGEST_PROMPT.format(
            gaps=formatted_gaps,
            messages=formatted_messages
        )

        try:
            # Use structured output with Pydantic model
            structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(SuggestOutput)
            suggest_result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Update state with prioritized gaps
            state.gaps = suggest_result.prioritized_gaps

            # Store filled gaps if any
            if suggest_result.filled_gaps:
                filled_msg = "Các thông tin được gợi ý tự động fill dựa trên ngữ cảnh:\n\n" + "\n\n".join(
                    [f"**{fg.gap_name}**\n• Giá trị: {fg.suggested_value}\n• Lý do: {fg.reason}"
                     for fg in suggest_result.filled_gaps]
                ) + "\n\nNếu không chính xác, vui lòng chỉnh sửa."
                state.messages.append(AIMessage(content=filled_msg))
        except Exception as e:
            print(f"Error in suggest: {e}")
            # Fallback: keep gaps as is if error occurs
            pass

        return state
    
    def ask_user(self, state: State) -> State:
        """Tạo câu hỏi để thu thập thông tin cho các gaps còn thiếu."""
        # Format gaps
        formatted_gaps = "\n".join([f"- {gap}" for gap in state.gaps]) if state.gaps else "Không có gaps"

        # Format messages - limit to last 10 messages
        formatted_messages = "\n".join([
            f"[{'User' if msg.type=='human' else 'Assistant'}]: {msg.content[:500]}"
            for msg in state.messages[-10:]
        ])

        prompt = ASK_USER_PROMPT.format(
            gaps=formatted_gaps,
            messages=formatted_messages
        )

        try:
            # Use structured output with Pydantic model
            structured_llm = self._llm("gpt-4.1", 0.1).with_structured_output(AskUserOutput)
            ask_result = structured_llm.invoke([HumanMessage(content=prompt)])
            state.questions = ask_result.questions
        except Exception as e:
            print(f"Error in ask_user: {e}")
            state.questions = []

        has_responses = False
        for question in state.questions:
            # Append the question as an AIMessage to maintain conversation flow
            state.messages.append(AIMessage(content=question))
            print(f"Câu hỏi để làm rõ: {question}")
            user_response = input("Câu trả lời của bạn (hoặc gõ 'skip' để bỏ qua câu này): ").strip()
            if user_response.lower() == 'skip':
                continue
            state.messages.append(HumanMessage(content=user_response))
            has_responses = True

        if has_responses:
            state.status = "clarified"
        else:
            state.status = "skipped"

        print(f"Full: {state.messages}")

        return state

    def increment_iteration(self, state: State) -> State:
        """Tăng iteration count và checkpoint state để có thể resume sau này."""
        state.iteration_count += 1
        print(f"\n=== Iteration {state.iteration_count}/{state.max_iterations} completed ===")
        print(f"Current gaps: {len(state.gaps)}")
        print(f"Score: {state.score}, Confidence: {state.confidence}, Status: {state.status}")

        # Checkpoint is automatically saved by LangGraph MemorySaver after each node execution
        return state

    # def preview(self, state: State) -> State:
    #     print(f"Brief Đã Tạo (Cờ chưa hoàn chỉnh: {state.incomplete_flag}):\n{state.brief}")
    #     user_choice = input("Phê duyệt/Chỉnh sửa/Tạo lại? ").lower()
    #     state.user_choice = user_choice
    #     if user_choice == "edit":
    #         edit_changes = input("Nhập chỉnh sửa của bạn: ")
    #         state.edit_changes = edit_changes
    #     return state

    # def edit_mode(self, state: State) -> State:
    #     prompt = f"Áp dụng các thay đổi sau vào brief:\nThay đổi: {state.edit_changes}\nBrief Gốc: {state.brief}"
    #     response = self.llm.invoke(prompt)
    #     state.brief = response.content
    #     state.edit_changes = ""
    #     return state

    # def finalize(self, state: State) -> State:
    #     prompt = f"Tạo tóm tắt cuối cùng từ brief đã phê duyệt:\n{state.brief}"
    #     response = self.llm.invoke(prompt)
    #     state.status = "completed"
    #     print(f"Tóm Tắt Cuối Cùng:\n{response.content}")
    #     return state

    # def generate(self, state: State) -> State:
    #     prompt = f"Tạo bản nháp brief từ cuộc trò chuyện dù có bỏ qua:\n{state.messages}"
    #     response = self.llm.invoke(prompt)
    #     state.brief = response.content
    #     return state

    # # Conditional branches
    # def evaluate_branch(self, state: State) -> str:
    #     if len(state.gaps) > 0 and state.confidence > 0.6:
    #         return "clarify"
    #     elif state.iteration_count < state.max_iterations:
    #         return "force_generate"
    #     else:
    #         return END
        
    def initialize_branch(self, state: State) -> str:
        if len(state.gaps) == 0 and len(state.messages) == 1:
            return "evaluate"
        else:
            return "collect_inputs"

    def evaluate_branch(self, state: State) -> str:
        if state.confidence <= 0.6:
            return "clarify"
        elif len(state.gaps) > 0 and state.confidence > 0.6 and state.confidence < 0.8:
            return "force_generate"
        else:
            return END

    def run(self, initial_context: str = "", thread_id: str | None = None) -> dict[str, Any]:
        """Chạy quy trình làm việc của gatherer agent.

        Args:
            initial_context: Ngữ cảnh ban đầu hoặc yêu cầu cho bản tóm tắt sản phẩm
            thread_id: ID để resume state (nếu None, dùng session_id hoặc default)

        Returns:
            dict: Trạng thái cuối cùng chứa bản tóm tắt đã tạo và các chỉ số đánh giá
        """
        if thread_id is None:
            thread_id = self.session_id or "default_thread"  # Default nếu không có

        initial_state = State(
            messages=[HumanMessage(content=initial_context)] if initial_context else []
        )

        config = {
            "configurable": {"thread_id": thread_id},  # Để checkpointer lưu theo thread
            "callbacks": [self.langfuse_handler]
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump() if initial_state else None,  # Nếu resume, pass None để load từ checkpointer
            config=config,
        ):
            final_state = output

        # Sau interrupt, bạn có thể check state và resume
        current_state = self.graph.get_state(config)
        if current_state.next:  # Nếu bị interrupt (paused)
            print("Graph paused at:", current_state.next)
            # Lấy input từ người dùng
            user_input = input("Nhập input của bạn (hoặc 'skip' để bỏ qua): ").strip()

            if user_input.lower() != 'skip':
                # Append input vào state.messages
                updated_messages = current_state.values["messages"] + [HumanMessage(content=user_input)]
                updates = {"messages": updated_messages}
                # Update state (as_node=None để resume chạy node tiếp theo)
                self.graph.update_state(config, updates, as_node=None)
            else:
                print("\n⊘ Bỏ qua append input")

            # Resume stream từ state đã update
            for output in self.graph.stream(None, config):
                final_state = output

        return final_state or {}  # Return final_state hoặc empty nếu không có