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

# from templates.prompts.product_owner.vision 

from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

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

        checkpointer = MemorySaver()

        return graph_builder.compile(
            checkpointer=checkpointer
        )