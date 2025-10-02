"""This file contains the LangGraph Agent/workflow and interactions with the LLM for gatherer agent."""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()



class GathererAgent:
    """Gatherer Agent for gathering product requirements."""

    MODEL = "gpt-4o"
    LLM_TEMPERATURE = 0.2

    def __init__(self):
        """Initialize the gatherer agent."""
        self.llm = ChatOpenAI(
            model=self.MODEL,
            temperature=self.LLM_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("OPENAI_BASE_URL"),
        )
        self.langfuse_handler = CallbackHandler()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph_builder = StateGraph(State)
        graph_builder.add_node("initialize", self._initialize)
        

        return graph_builder.compile()

    def _initialize(self, state: State) -> State:
        """Initialize the state."""
        return state

 