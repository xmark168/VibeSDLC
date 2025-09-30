"""Task management AI agent using LangGraph."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.core.config import settings
from app.core.langfuse_config import langfuse_manager

logger = logging.getLogger(__name__)


class TaskState(BaseModel):
    """State for task management agent."""
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    task_description: Optional[str] = None
    priority: str = "medium"
    suggestions: List[str] = []
    analysis: Optional[str] = None
    next_action: Optional[str] = None


class TaskAgent:
    """AI Agent for intelligent task management."""

    def __init__(self):
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()

    def _initialize_llm(self):
        """Initialize the language model."""
        callbacks = []
        if langfuse_manager.initialize():
            callback_handler = langfuse_manager.get_callback_handler()
            if callback_handler:
                callbacks.append(callback_handler)

        # Use Anthropic Claude as primary, OpenAI as fallback
        if settings.ANTHROPIC_API_KEY:
            return ChatAnthropic(
                model=settings.ANTHROPIC_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                callbacks=callbacks,
            )
        elif settings.OPENAI_API_KEY:
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                callbacks=callbacks,
            )
        else:
            logger.warning("No LLM API key provided. Agent functionality limited.")
            return None

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(TaskState)

        # Add nodes
        workflow.add_node("analyze_task", self.analyze_task)
        workflow.add_node("generate_suggestions", self.generate_suggestions)
        workflow.add_node("prioritize_task", self.prioritize_task)

        # Add edges
        workflow.set_entry_point("analyze_task")
        workflow.add_edge("analyze_task", "generate_suggestions")
        workflow.add_edge("generate_suggestions", "prioritize_task")
        workflow.add_edge("prioritize_task", END)

        return workflow.compile()

    async def analyze_task(self, state: TaskState) -> TaskState:
        """Analyze the task using LLM."""
        if not self.llm or not state.task_description:
            return state

        try:
            trace = langfuse_manager.create_trace(
                name="task_analysis",
                user_id=state.user_id,
                metadata={"task": state.task_description}
            )

            messages = [
                SystemMessage(content="""You are an intelligent task management assistant.
                Analyze the given task and provide insights about its complexity, estimated time,
                required skills, and potential challenges."""),
                HumanMessage(content=f"Analyze this task: {state.task_description}")
            ]

            response = await self.llm.ainvoke(messages)
            state.analysis = response.content

            if trace:
                trace.update(output={"analysis": state.analysis})

        except Exception as e:
            logger.error(f"Error analyzing task: {e}")
            state.analysis = "Unable to analyze task due to technical issues."

        return state

    async def generate_suggestions(self, state: TaskState) -> TaskState:
        """Generate task suggestions and recommendations."""
        if not self.llm or not state.task_description:
            return state

        try:
            messages = [
                SystemMessage(content="""You are a productivity expert. Based on the task
                analysis, provide 3-5 actionable suggestions to help the user complete
                the task more efficiently. Format as a bullet list."""),
                HumanMessage(content=f"""Task: {state.task_description}
                Analysis: {state.analysis or 'No analysis available'}

                Provide practical suggestions:""")
            ]

            response = await self.llm.ainvoke(messages)
            suggestions_text = response.content

            # Parse suggestions (simple split by bullet points or newlines)
            state.suggestions = [
                s.strip() for s in suggestions_text.split('\n')
                if s.strip() and (s.strip().startswith('-') or s.strip().startswith('•'))
            ]

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            state.suggestions = ["Review task requirements", "Break into smaller steps"]

        return state

    async def prioritize_task(self, state: TaskState) -> TaskState:
        """Determine task priority and next actions."""
        if not self.llm:
            return state

        try:
            messages = [
                SystemMessage(content="""Determine the priority level (high, medium, low)
                for this task and suggest the immediate next action."""),
                HumanMessage(content=f"""Task: {state.task_description}
                Analysis: {state.analysis or 'No analysis'}

                Determine priority and next action:""")
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content.lower()

            # Extract priority
            if "high" in content:
                state.priority = "high"
            elif "low" in content:
                state.priority = "low"
            else:
                state.priority = "medium"

            state.next_action = response.content

        except Exception as e:
            logger.error(f"Error prioritizing task: {e}")
            state.priority = "medium"
            state.next_action = "Review task and start planning"

        return state

    async def process_task(self, user_id: str, task_description: str) -> Dict[str, Any]:
        """Process a task through the agent workflow."""
        try:
            # Create initial state
            initial_state = TaskState(
                user_id=user_id,
                task_description=task_description
            )

            # Run the workflow
            result = await self.graph.ainvoke(initial_state)

            # Flush LangFuse traces
            langfuse_manager.flush()

            return {
                "analysis": result.analysis,
                "suggestions": result.suggestions,
                "priority": result.priority,
                "next_action": result.next_action,
                "processed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {
                "error": "Failed to process task",
                "processed_at": datetime.utcnow().isoformat()
            }

    # Event handlers for Kafka events
    async def on_user_created(self, data: Dict[str, Any]):
        """Handle user creation event."""
        logger.info(f"New user created: {data.get('email')}")
        # Could send welcome message or create onboarding tasks

    async def on_user_updated(self, data: Dict[str, Any]):
        """Handle user update event."""
        logger.info(f"User updated: {data.get('email')}")

    async def on_user_deleted(self, data: Dict[str, Any]):
        """Handle user deletion event."""
        logger.info(f"User deleted: {data.get('email')}")

    async def on_item_created(self, data: Dict[str, Any]):
        """Handle item/task creation event."""
        logger.info(f"New item created: {data.get('title')}")

        # Automatically process the new task
        if data.get('title') and data.get('owner_id'):
            result = await self.process_task(
                user_id=str(data['owner_id']),
                task_description=data['title']
            )
            logger.info(f"Task processed: {result}")

    async def on_item_updated(self, data: Dict[str, Any]):
        """Handle item/task update event."""
        logger.info(f"Item updated: {data.get('title')}")

    async def on_item_deleted(self, data: Dict[str, Any]):
        """Handle item/task deletion event."""
        logger.info(f"Item deleted: {data.get('title')}")