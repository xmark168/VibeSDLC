"""This file contains the LangGraph Agent/workflow and interactions with the LLM for gatherer agent."""

import os
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()


# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


class EvaluateOutput(BaseModel):
    """Output model for brief evaluation."""

    gaps: list[str] = Field(description="List of information gaps")
    score: float = Field(description="Score from 0 to 1")
    status: str = Field(description="Status, e.g., incomplete, done")
    confidence: float = Field(description="Confidence from 0 to 1")


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
    """Gatherer Agent for gathering product requirements."""

    MODEL = "gpt-4"
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

        # Initialize Langfuse callback handler with metadata
        self.langfuse_handler = CallbackHandler(
            session_id=session_id,
            user_id=user_id,
            tags=["gatherer-agent", "product-owner"],
        )

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("initialize", self._initialize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", END)

        return graph_builder.compile()

    def _initialize(self, state: State) -> State:
        """Initialize the state."""
        # Log initialization event to Langfuse
        langfuse.create_event(
            name="gatherer_agent_initialized",
            session_id=self.session_id,
            user_id=self.user_id,
            metadata={
                "max_iterations": state.max_iterations,
                "model": self.MODEL,
                "temperature": self.TEMPERATURE,
            },
        )
        return state

    def run(self, initial_context: str = "", trace_name: str = "gatherer_agent_run") -> dict[str, Any]:
        """Run the gatherer agent workflow.

        Args:
            initial_context: Initial context or requirements for the product brief
            trace_name: Name for the Langfuse trace

        Returns:
            dict: Final state containing the generated brief and evaluation metrics
        """
        # Start a span for the entire workflow
        span = langfuse.start_span(
            name=trace_name,
            input={"initial_context": initial_context},
            metadata={
                "agent_type": "gatherer",
                "model": self.MODEL,
                "temperature": self.TEMPERATURE,
                "session_id": self.session_id,
                "user_id": self.user_id,
            },
        )

        initial_state = State(
            messages=[HumanMessage(content=initial_context)] if initial_context else []
        )

        final_state = None
        try:
            for output in self.graph.stream(
                initial_state.model_dump(),
                config={"callbacks": [self.langfuse_handler]},
            ):
                final_state = output

            # End span with output
            span.end(
                output=final_state,
                metadata={
                    "agent_type": "gatherer",
                    "model": self.MODEL,
                    "temperature": self.TEMPERATURE,
                    "final_status": final_state.get("status") if final_state else "unknown",
                },
            )

            # Log completion event
            langfuse.create_event(
                name="gatherer_agent_completed",
                metadata={
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "iterations": final_state.get("iteration_count") if final_state else 0,
                    "status": final_state.get("status") if final_state else "unknown",
                },
            )

        except Exception as e:
            # End span with error
            span.end(
                level="ERROR",
                status_message=str(e),
            )

            # Log error event
            langfuse.create_event(
                name="gatherer_agent_error",
                level="ERROR",
                metadata={
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "error": str(e),
                },
            )
            raise

        finally:
            # Flush events to Langfuse
            langfuse.flush()

        return final_state
