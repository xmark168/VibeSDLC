import json
from typing import TypedDict, Literal, List
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, START, END

import os
from langfuse.langchain import CallbackHandler
load_dotenv()
llm = ChatOpenAI(model="gpt-4o", temperature=0)

langfuse_handler = CallbackHandler()
class EvaluateOutput(BaseModel):
    gaps: List[str] = Field(description="List of information gaps")
    score: float = Field(description="Score from 0 to 1")
    status: str = Field(description="Status, e.g., incomplete, done")
    confidence: float = Field(description="Confidence from 0 to 1")
class State(TypedDict):
    messages: List[BaseMessage]
    iteration_count: int
    max_iterations: int
    retry_count: int
    gaps: List[str]
    score: float
    status: str
    confidence: float
    brief: str
    incomplete_flag: bool
    questions: str
    user_choice: Literal["approve", "edit", "regenerate", ""]
    edit_changes: str


def initialize(state: State) -> State:
    state["messages"] = []
    state["iteration_count"] = 0
    state["max_iterations"] = 5
    state["retry_count"] = 0
    state["gaps"] = []
    state["score"] = 0.0
    state["status"] = "initial"
    state["confidence"] = 0.0
    state["brief"] = ""
    state["incomplete_flag"] = False
    state["questions"] = ""
    state["user_choice"] = ""
    state["edit_changes"] = ""
    # Load context if needed (assuming empty for now)
    return state

graph_builder = StateGraph(State)
graph_builder.add_node("initialize", initialize)

graph_builder.add_edge(START, "initialize")



graph = graph_builder.compile()
initial_input = {"messages": [HumanMessage(content="Start generating a brief about AI agents.")]}

for output in graph.stream(initial_input, config={"callbacks": [langfuse_handler]}):
    # The graph will pause at user interaction nodes for input
    pass