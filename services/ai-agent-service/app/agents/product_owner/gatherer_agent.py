"""This class contains the LangGraph Agent/workflow and interactions with the LLM for gatherer agent."""

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
    """State for the gatherer agent workflow."""

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
    """Gatherer Agent for gathering product brief that can help generate backlog in future."""

    MODEL = "gpt-4o"
    TEMPERATURE = 0.2

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Initialize the gatherer agent.

        Args:
            session_id: Optional session ID for tracking
            user_id: Optional user ID for tracking
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
        """Build the LangGraph workflow."""
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("initialize", self._initialize)
        graph_builder.add_node("collect_inputs", self.collect_inputs)
        graph_builder.add_node("evaluate", self.evaluate)
        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "collect_inputs")
        graph_builder.add_edge("initialize", END)
        graph_builder.add_edge("collect_inputs", "evaluate")
        return graph_builder.compile()

    def _initialize(self, state: State) -> State:
        """Initialize the state."""
        return state
    def collect_inputs(self, state: State) -> State:
        """Collect additional inputs from user to fill information gaps."""
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
        """Evaluate conversation completeness for brief generation using structured output."""
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
    def run(self, initial_context: str = "") -> dict[str, Any]:
        """Run the gatherer agent workflow.

        Args:
            initial_context: Initial context or requirements for the product brief

        Returns:
            dict: Final state containing the generated brief and evaluation metrics
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
