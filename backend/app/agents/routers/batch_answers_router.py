
"""Router for BatchAnswers Router."""

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

class BatchAnswersRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_batch_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        batch_id = event_dict.get("batch_id")
        answers = event_dict.get("answers", [])
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        
        if not batch_id or not answers:
            self.logger.error("Batch answer event missing batch_id or answers")
            return
        
        try:
            if isinstance(agent_id_raw, str):
                agent_id = UUID(agent_id_raw)
            else:
                agent_id = agent_id_raw
            
            if isinstance(task_id, str):
                task_id = UUID(task_id)
        except Exception as e:
            self.logger.error(f"Invalid UUID in batch answer event: {e}")
            return
        
        project_id = event_dict.get("project_id")
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        
        from app.models import AgentQuestion, Message, QuestionStatus, Agent
        
        with Session(engine) as session:
            first_question = None
            
            for ans_data in answers:
                question_id = UUID(ans_data["question_id"])
                
                question = session.get(AgentQuestion, question_id)
                if question:
                    if not first_question:
                        first_question = question
                    
                    question.status = QuestionStatus.ANSWERED
                    question.answer = ans_data.get("answer", "")
                    question.selected_options = ans_data.get("selected_options")
                    question.answered_at = datetime.now(timezone.utc)
                    session.add(question)
                
                message = session.get(Message, question_id)
                if message:
                    message.structured_data = {
                        **(message.structured_data or {}),
                        "answered": True,
                        "answered_at": datetime.now(timezone.utc).isoformat(),
                        "user_answer": ans_data.get("answer", ""),
                        "user_selected_options": ans_data.get("selected_options", []),
                        "status": "answered"
                    }
                    session.add(message)
            
            session.commit()
            original_task_context = first_question.task_context if first_question else {}
        
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"batch_answers:{batch_id}",
            priority="high",
            additional_context={
                "batch_id": batch_id,
                "batch_answers": answers,
                "answer_count": len(answers),
                "original_context": original_task_context,
                "is_batch": True,
            }
        )
        
        self.logger.info(f"Published RESUME_WITH_ANSWER task to agent {agent_id} with {len(answers)} batch answers")
        
        from app.websocket.connection_manager import connection_manager
        
        agent_name = "Agent"
        with Session(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent_name = agent.human_name or agent.name or "Agent"
        
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed_batch",
                "batch_id": batch_id,
                "agent_id": str(agent_id),
                "agent_name": agent_name,
                "answer_count": len(answers),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
        
        await connection_manager.broadcast_to_project(
            {
                "type": "messages_updated",
                "reason": "batch_questions_answered",
                "batch_id": batch_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
