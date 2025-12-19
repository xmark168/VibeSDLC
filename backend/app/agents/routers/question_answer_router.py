
"""Router for QuestionAnswer Router."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session

from app.kafka.event_schemas import AgentTaskType, BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class QuestionAnswerRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        question_id = event_dict.get("question_id")
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        answer = event_dict.get("answer")
        selected_options = event_dict.get("selected_options")
        
        if not question_id or not agent_id_raw:
            self.logger.error(f"Missing required fields: question_id={question_id}, agent_id={agent_id_raw}")
            return
        
        agent_id = UUID(agent_id_raw) if isinstance(agent_id_raw, str) else agent_id_raw
        
        self.logger.info(
            f"[QUESTION_ANSWER_ROUTER] Routing answer for question {question_id} "
            f"back to agent {agent_id}"
        )
        
        from app.models import AgentQuestion, QuestionStatus, QuestionType
        
        with Session(engine) as session:
            question = session.get(AgentQuestion, question_id)
            
            if not question:
                self.logger.error(f"Question {question_id} not found!")
                return
            
            if question.status != QuestionStatus.WAITING_ANSWER:
                self.logger.warning(
                    f"Question {question_id} already answered/expired, ignoring"
                )
                return
            
            question.status = QuestionStatus.ANSWERED
            question.answer = answer
            question.selected_options = selected_options
            
            if question.question_type == QuestionType.APPROVAL:
                question.approved = event_dict.get("approved")
                question.modified_data = event_dict.get("modified_data")
            
            question.answered_at = datetime.now(timezone.utc)
            session.add(question)
            
            from app.models import Message
            message = session.get(Message, question_id)
            if message:
                message.structured_data = {
                    **(message.structured_data or {}),
                    "answered": True,
                    "answered_at": datetime.now(timezone.utc).isoformat(),
                    "user_answer": answer or "",
                    "user_selected_options": selected_options or [],
                    "status": "answered"
                }
                session.add(message)
            
            session.commit()
            original_task_context = question.task_context
            project_id = question.project_id  # Get project_id from question
        
        context_data = {
            "question_id": str(question_id),
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "answer": answer,
            "selected_options": selected_options,
            "original_context": original_task_context,
        }
        
        if question.question_type == QuestionType.APPROVAL:
            context_data.update({
                "approved": question.approved,
                "modified_data": question.modified_data,
                "proposed_data": question.proposed_data,
                "final_data": question.modified_data if question.modified_data else question.proposed_data,
            })
        
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"question_answer:{question_id}",
            priority="high",
            additional_context=context_data
        )
        
        self.logger.info(
            f"Published RESUME_WITH_ANSWER task to agent {agent_id}"
        )
        
        from app.websocket.connection_manager import connection_manager
        
        agent_name = "Agent"
        with Session(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent_name = agent.human_name or agent.name or "Agent"
        
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed",
                "question_id": str(question_id),
                "agent_id": str(agent_id),
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
        
        await connection_manager.broadcast_to_project(
            {
                "type": "messages_updated",
                "reason": "question_answered",
                "message_id": str(question_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
