"""Message routing system - routes events to appropriate agents."""

from app.agents.routers.base import BaseEventRouter
from app.agents.routers.message_router import MessageRouter
from app.agents.routers.user_message_router import UserMessageRouter
from app.agents.routers.agent_message_router import AgentMessageRouter
from app.agents.routers.task_completion_router import TaskCompletionRouter
from app.agents.routers.agent_response_router import AgentResponseRouter
from app.agents.routers.story_event_router import StoryEventRouter
from app.agents.routers.agent_status_router import AgentStatusRouter
from app.agents.routers.question_answer_router import QuestionAnswerRouter
from app.agents.routers.batch_answers_router import BatchAnswersRouter
from app.agents.routers.delegation_router import DelegationRouter


__all__ = [
    # Base
    "BaseEventRouter",
    # Main Router
    "MessageRouter",
    # Individual Routers
    "UserMessageRouter",
    "AgentMessageRouter",
    "TaskCompletionRouter",
    "AgentResponseRouter",
    "StoryEventRouter",
    "AgentStatusRouter",
    "QuestionAnswerRouter",
    "BatchAnswersRouter",
    "DelegationRouter",
]
