"""Team Leader Agent - Router với natural language support.

Team Leader Agent điều phối routing giữa PO, Scrum Master, Developer, và Tester agents.
Designed cho người dùng phổ thông sử dụng ngôn ngữ tự nhiên.

Features:
- Intent-based classification (không cần keywords)
- Conversation history tracking
- Natural language support (Vietnamese + English)
- LangChain integration
- Pydantic structured output
- Langfuse observability
"""

import json
import os
from typing import Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langfuse.langchain import CallbackHandler

from app.templates.prompts.team_leader.tl_prompt import SYSTEM_PROMPT

load_dotenv()


class RoutingDecision(BaseModel):
    """Structured routing decision output."""

    agent: Literal["po", "scrum_master", "developer", "tester"] = Field(
        description="Agent to route to"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score 0-1"
    )
    reasoning: str = Field(
        description="Why this agent was selected"
    )
    user_intent: str = Field(
        description="User's intent in Vietnamese"
    )


class TeamLeaderAgent:
    """Team Leader Agent - Intent-based router với natural language.

    Phân loại user intent và route đến agent phù hợp:
    - po: Product planning, new features, backlog
    - scrum_master: Sprint progress, velocity, timeline
    - developer: Technical questions, how it works
    - tester: Bug reports, quality checks

    Features:
    - Natural language understanding (no keywords needed)
    - Conversation history tracking
    - High accuracy with non-technical users
    - Fast classification (300-500ms)
    """

    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        model: str = "gpt-4o-mini"
    ):
        """Initialize Team Leader Agent.

        Args:
            session_id: Session ID for conversation tracking
            user_id: User ID for observability
            model: LLM model to use (default: gpt-4o-mini for speed/cost)
        """
        self.session_id = session_id or "default_tl_session"
        self.user_id = user_id
        self.model = model

        # LLM - fast and cheap model for classification
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0,  # Deterministic
            max_retries=3,
            request_timeout=30,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        # Langfuse callback for observability
        try:
            self.langfuse_handler = CallbackHandler(
                session_id=self.session_id,
                user_id=self.user_id,
                flush_at=5,
                flush_interval=1.0
            )
        except Exception:
            self.langfuse_handler = None

        # JSON output parser
        self.parser = JsonOutputParser(pydantic_object=RoutingDecision)

        # Build classification chain
        self.chain = self._build_chain()

        # Conversation history storage (in-memory)
        # In production, này nên được lưu vào database hoặc Redis
        self.conversations = {}  # session_id -> list of messages

    def _build_chain(self):
        """Build LangChain classification chain."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", """**Conversation History:**
{history}

**Current Message:**
"{message}"

**Task:** Phân tích intent và trả về routing decision JSON.

{format_instructions}
""")
        ])

        # Chain composition: prompt → llm → parser
        return prompt | self.llm | self.parser

    def classify(
        self,
        user_message: str,
        project_context: dict | None = None
    ) -> RoutingDecision:
        """Classify user intent and return routing decision.

        Args:
            user_message: User's message in natural language
            project_context: Optional context (project_phase, etc.)

        Returns:
            RoutingDecision with agent, confidence, reasoning
        """
        # Get conversation history
        history = self.conversations.get(self.session_id, [])
        history_str = self._format_history(history)

        # Add context if provided
        if project_context:
            phase = project_context.get("project_phase")
            if phase:
                history_str += f"\n\n**Project Phase:** {phase}"

        # Prepare callbacks
        callbacks = []
        if self.langfuse_handler:
            callbacks.append(self.langfuse_handler)

        # Invoke chain
        try:
            result_dict = self.chain.invoke(
                {
                    "message": user_message,
                    "history": history_str if history_str else "No previous messages",
                    "format_instructions": self.parser.get_format_instructions()
                },
                config={"callbacks": callbacks}
            )

            # Convert dict to Pydantic model
            result = RoutingDecision(**result_dict)

        except Exception as e:
            # Fallback on error
            print(f"[TL Agent] Classification error: {e}")
            result = self._fallback_classification(user_message)

        # Save to conversation history
        self._save_to_history(user_message, result.agent)

        return result

    def _fallback_classification(self, message: str) -> RoutingDecision:
        """Fallback classification dựa trên simple rules."""
        message_lower = message.lower()

        # Simple keyword matching as fallback
        if any(kw in message_lower for kw in [
            "tạo", "làm", "muốn", "app", "website", "trang web", "sản phẩm", "feature", "tính năng"
        ]):
            return RoutingDecision(
                agent="po",
                confidence=0.6,
                reasoning="Fallback: Detected project creation intent",
                user_intent="Có thể muốn tạo dự án mới"
            )
        elif any(kw in message_lower for kw in [
            "tiến độ", "bao giờ", "xong", "chậm", "nhanh", "velocity", "progress"
        ]):
            return RoutingDecision(
                agent="scrum_master",
                confidence=0.6,
                reasoning="Fallback: Detected timeline/progress intent",
                user_intent="Hỏi về tiến độ"
            )
        elif any(kw in message_lower for kw in [
            "lỗi", "bug", "không hoạt động", "không chạy", "bị", "error"
        ]):
            return RoutingDecision(
                agent="tester",
                confidence=0.6,
                reasoning="Fallback: Detected bug report",
                user_intent="Báo lỗi"
            )
        else:
            # Default to PO for ambiguous cases
            return RoutingDecision(
                agent="po",
                confidence=0.5,
                reasoning="Fallback: Default to PO for unclear intent",
                user_intent="Intent không rõ ràng"
            )

    def _format_history(self, history: list) -> str:
        """Format conversation history for prompt."""
        if not history:
            return ""

        formatted = []
        for msg in history[-5:]:  # Last 5 messages only
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"- {role}: {content}")

        return "\n".join(formatted)

    def _save_to_history(self, user_message: str, routed_agent: str):
        """Save message and routing to conversation history."""
        if self.session_id not in self.conversations:
            self.conversations[self.session_id] = []

        history = self.conversations[self.session_id]

        # Add user message
        history.append({
            "role": "user",
            "content": user_message
        })

        # Add routing decision
        history.append({
            "role": "system",
            "content": f"Routed to {routed_agent}"
        })

        # Keep only last 20 messages (10 turns)
        if len(history) > 20:
            self.conversations[self.session_id] = history[-20:]

    def run(self, user_message: str, context: dict | None = None) -> dict:
        """Main entry point compatible with other agents.

        Args:
            user_message: User's message
            context: Optional context dict

        Returns:
            dict with routing decision
        """
        result = self.classify(user_message, context)

        return {
            "agent_name": result.agent,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "user_intent": result.user_intent,
            "user_message": user_message
        }

    def get_conversation_history(self, session_id: str | None = None) -> list:
        """Get conversation history for a session.

        Args:
            session_id: Session ID (uses self.session_id if not provided)

        Returns:
            List of messages in conversation
        """
        sid = session_id or self.session_id
        return self.conversations.get(sid, [])

    def clear_history(self, session_id: str | None = None):
        """Clear conversation history for a session.

        Args:
            session_id: Session ID (uses self.session_id if not provided)
        """
        sid = session_id or self.session_id
        if sid in self.conversations:
            del self.conversations[sid]


# Quick test
if __name__ == "__main__":
    # Test với natural language
    tl_agent = TeamLeaderAgent(
        session_id="test_session",
        user_id="test_user"
    )

    test_messages = [
        "Tôi muốn làm một trang web bán quần áo online",
        "Bao giờ xong dự án?",
        "Website có thể handle 1000 users không?",
        "Trang đăng nhập bị lỗi"
    ]

    print("=" * 80)
    print("Team Leader Agent - Natural Language Classification Test")
    print("=" * 80)

    for msg in test_messages:
        print(f"\nUser: {msg}")
        result = tl_agent.classify(msg)
        print(f"→ Agent: {result.agent}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Intent: {result.user_intent}")
        print(f"  Reasoning: {result.reasoning}")
