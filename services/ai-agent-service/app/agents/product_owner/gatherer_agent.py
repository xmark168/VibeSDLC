"""Lớp này chứa LangGraph Agent/workflow và các tương tác với LLM cho gatherer agent."""

import json
import os
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from templates.prompts.product_owner.gatherer import EVALUATE_PROMPT

load_dotenv()


class EvaluateOutput(BaseModel):
    gaps: list[str] = Field(description="Danh sách các thông tin còn thiếu")
    score: float = Field(description="Điểm đánh giá độ đầy đủ", ge=0.0, le=1.0)
    status: str = Field(description="Trạng thái: incomplete hoặc done")
    confidence: float = Field(description="Độ tin cậy đánh giá", ge=0.0, le=1.0)


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
    brief: str = ""
    incomplete_flag: bool = False
    questions: str = ""
    user_choice: Literal["approve", "edit", "regenerate", ""] = ""
    edit_changes: str = ""


class GathererAgent:
    """Gatherer Agent để thu thập thông tin sản phẩm giúp tạo backlog trong tương lai."""

    MODEL = "gpt-4o"
    TEMPERATURE = 0.2

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo gatherer agent.

        Args:
            session_id: Session ID tùy chọn để theo dõi
            user_id: User ID tùy chọn để theo dõi
        """
        self.session_id = session_id
        self.user_id = user_id

        self.llm = ChatOpenAI(
            model=self.MODEL,
            temperature=self.TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
        # Initialize Langfuse callback handler
        self.langfuse_handler = CallbackHandler()

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Xây dựng quy trình làm việc LangGraph."""
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("initialize", self._initialize)
        graph_builder.add_node("collect_inputs", self.collect_inputs)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("force_generate", self.force_generate)
        graph_builder.add_node("validate", self.validate)    
        graph_builder.add_node("retry_decision", self.retry_decision)
        graph_builder.add_node("clarify", self.clarify)
        graph_builder.add_node("suggest", self.suggest)
        graph_builder.add_node("ask_user", self.ask_user)
        graph_builder.add_node("increment_iteration", self.increment_iteration)
        graph_builder.add_node("preview", self.preview)
        graph_builder.add_node("edit_mode", self.edit_mode)
        graph_builder.add_node("finalize", self.finalize)
        graph_builder.add_node("generate", self.generate)
        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "collect_inputs")
        graph_builder.add_edge("initialize", END)
        graph_builder.add_edge("collect_inputs", "evaluate")
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        return graph_builder.compile()

    def _initialize(self, state: State) -> State:
        """Khởi tạo trạng thái."""
        return state
    def collect_inputs(self, state: State) -> State:
        """Thu thập thông tin bổ sung từ người dùng để điền vào các khoảng trống thông tin."""
        if not state.gaps:
            return state

        print("\n" + "=" * 80)
        print("CẦN THU THẬP THÊM THÔNG TIN")
        print("=" * 80)
        print(f"\nĐộ đầy đủ hiện tại: {state.score:.0%}")
        print(f"\nCác thông tin còn thiếu ({len(state.gaps)}):")
        for i, gap in enumerate(state.gaps, 1):
            print(f"  {i}. {gap}")

        print("\n" + "-" * 80)
        print("Vui lòng cung cấp thông tin bổ sung (nhập 'skip' để bỏ qua):")
        print("-" * 80)

        try:
            user_input = input("\n> ").strip()

            if user_input and user_input.lower() != "skip":
                # Add user message to conversation
                state.messages.append(HumanMessage(content=user_input))
                print(f"\n✓ Đã thêm thông tin vào cuộc hội thoại")
            else:
                print("\n⊘ Bỏ qua thu thập thêm thông tin")

        except (EOFError, KeyboardInterrupt):
            print("\n⊘ Bỏ qua thu thập thêm thông tin")

        return state
    
    def evaluate(self, state: State) -> State:
        """Đánh giá độ đầy đủ của cuộc hội thoại để tạo bản tóm tắt sử dụng structured output."""
        # Format messages
        formatted_messages = "\n".join([
            f"{i}. [{'User' if isinstance(msg, HumanMessage) else 'Assistant'}]: "
            f"{msg.content if hasattr(msg, 'content') else str(msg)}"
            for i, msg in enumerate(state.messages, 1)
        ]) if state.messages else "Chưa có thông tin nào được thu thập."

        prompt = EVALUATE_PROMPT.format(messages=formatted_messages)

        # Use structured output with Pydantic model
        structured_llm = self.llm.with_structured_output(EvaluateOutput)
        evaluation = structured_llm.invoke([HumanMessage(content=prompt)])

        # Update state
        state.gaps = evaluation.gaps
        state.score = evaluation.score
        state.status = evaluation.status
        state.confidence = evaluation.confidence
        return state
    def force_generate(self,state: State) -> State:
        prompt = f"Tạo một brief sử dụng thông tin có sẵn từ cuộc trò chuyện, ngay cả khi chưa hoàn chỉnh:\n{state['messages']}"
        response = self.llm.invoke(prompt)
        state["brief"] = response.content
        state["incomplete_flag"] = True
        return state

    def validate(self,state: State) -> State:
        prompt = f"""Xác thực brief đã tạo về tính hoàn chỉnh và chính xác so với cuộc trò chuyện:
        Brief: {state['brief']}
        Cuộc trò chuyện: {state['messages']}
        Output dưới dạng JSON với valid (bool), confidence, score."""
        response = self.llm.invoke(prompt)
        try:
            parsed = json.loads(response.content)
            state["valid"] = parsed.get("valid", False)
            state["confidence"] = parsed.get("confidence", 0.0)
            state["score"] = parsed.get("score", 0.0)
        except:
            state["valid"] = False
        return state

    def retry_decision(self,state: State) -> State:
        state["retry_count"] += 1
        return state
    def clarify(self,state: State) -> State:
        prompt = f"Diễn đạt lại bất kỳ câu hỏi nào chưa rõ ràng hoặc đơn giản hóa đầu vào từ cuộc trò chuyện để cải thiện sự hiểu biết:\n{state['messages']}"
        response = self.llm.invoke(prompt)
        state["messages"].append(AIMessage(content=response.content))
        return state
    def suggest(self,state: State) -> State:
        prompt = f"Ưu tiên các khoảng trống quan trọng từ: {state['gaps']}\nOutput dưới dạng JSON với prioritized_gaps."
        response = self.llm.invoke(prompt)
        try:
            parsed = json.loads(response.content)
            state["gaps"] = parsed.get("prioritized_gaps", state["gaps"])
        except:
            pass
        return state
    def ask_user(self,state: State) -> State:
        prompt = f"Tạo tối đa 3 câu hỏi để lấp đầy các khoảng trống {state['gaps']} dựa trên cuộc trò chuyện {state['messages']}. Cung cấp ví dụ nếu hữu ích.\nOutput dưới dạng JSON với questions."
        response = self.llm.invoke(prompt)
        try:
            parsed = json.loads(response.content)
            state["questions"] = '\n'.join(parsed.get("questions", []))
        except:
            state["questions"] = ""
        print(f"Câu hỏi để làm rõ:\n{state['questions']}")
        user_response = input("Câu trả lời của bạn (hoặc gõ 'skip' để tiếp tục mà không cần): ")
        if user_response.lower() == 'skip':
            state["status"] = "skipped"
        else:
            state["messages"].append(HumanMessage(content=user_response))
            state["status"] = "clarified"
        return state

    def increment_iteration(state: State) -> State:
        state["iteration_count"] += 1
        # Could save checkpoint here if using a checkpointer
        return state
    def preview(self,state: State) -> State:
        print(f"Brief Đã Tạo (Cờ chưa hoàn chỉnh: {state['incomplete_flag']}):\n{state['brief']}")
        user_choice = input("Phê duyệt/Chỉnh sửa/Tạo lại? ").lower()
        state["user_choice"] = user_choice
        if user_choice == "edit":
            edit_changes = input("Nhập chỉnh sửa của bạn: ")
            state["edit_changes"] = edit_changes
        return state
    def edit_mode(self,state: State) -> State:
        prompt = f"Áp dụng các thay đổi sau vào brief:\nThay đổi: {state['edit_changes']}\nBrief Gốc: {state['brief']}"
        response = self.llm.invoke(prompt)
        state["brief"] = response.content
        state["edit_changes"] = ""
        return state
    def finalize(self,state: State) -> State:
        prompt = f"Tạo tóm tắt cuối cùng từ brief đã phê duyệt:\n{state['brief']}"
        response = self.llm.invoke(prompt)
        state["status"] = "completed"
        print(f"Tóm Tắt Cuối Cùng:\n{response.content}")
        return state

    def generate(self,state: State) -> State:
        prompt = f"Tạo bản nháp brief từ cuộc trò chuyện dù có bỏ qua:\n{state['messages']}"
        response = self.llm.invoke(prompt)
        state["brief"] = response.content
        return state

    # Conditional branches
    def evaluate_branch(state: State) -> str:
        if len(state["gaps"]) > 0 and state["confidence"] > 0.6:
            return "clarify"
        elif state["iteration_count"] < state["max_iterations"]:
            return "force_generate"
        else:
            return END
    def run(self, initial_context: str = "") -> dict[str, Any]:
        """Chạy quy trình làm việc của gatherer agent.

        Args:
            initial_context: Ngữ cảnh ban đầu hoặc yêu cầu cho bản tóm tắt sản phẩm

        Returns:
            dict: Trạng thái cuối cùng chứa bản tóm tắt đã tạo và các chỉ số đánh giá
        """
        initial_state = State(
            messages=[HumanMessage(content=initial_context)] if initial_context else []
        )

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config={"callbacks": [self.langfuse_handler]},
        ):
            final_state = output

        return final_state
