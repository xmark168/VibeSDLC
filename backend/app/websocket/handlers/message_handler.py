"""
Message Handler

Handles agent response and routing events
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session

from app.models import Message as MessageModel, AuthorType
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class MessageHandler(BaseEventHandler):
    """Handles message-related WebSocket events"""

    async def handle_agent_response(self, event):
        """Handle agent response events and forward to WebSocket clients"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Agent response event missing project_id")
                return

            content = event_data.get("content", "")
            structured_data = event_data.get("structured_data")
            agent_name = event_data.get("agent_name", "")
            task_id = event_data.get("task_id")
            execution_id = event_data.get("execution_id")

            # Build metadata
            metadata = {"agent_name": agent_name} if agent_name else {}
            if task_id:
                metadata["task_id"] = str(task_id)
            if execution_id:
                metadata["execution_id"] = str(execution_id)
            if structured_data:
                metadata.update(structured_data)

            # Save to database
            with Session(self.engine) as db_session:
                db_message = MessageModel(
                    project_id=project_id,
                    user_id=None,
                    agent_id=None,
                    content=content,
                    author_type=AuthorType.AGENT,
                    message_type=structured_data.get("message_type", "text") if structured_data else "text",
                    structured_data=structured_data.get("data") if structured_data and "data" in structured_data else None,
                    message_metadata=metadata if metadata else None,
                )
                db_session.add(db_message)
                db_session.commit()
                db_session.refresh(db_message)
                message_id = db_message.id

            logger.info(
                f"Saved agent response: {message_id}, "
                f"task_id={task_id}, execution_id={execution_id}"
            )

            # Format WebSocket message
            ws_message = {
                "type": "agent_message",
                "agent_name": agent_name,
                "agent_type": event_data.get("agent_type", ""),
                "content": content,
                "message_id": str(message_id),
                "project_id": str(project_id),
                "timestamp": self._get_timestamp(event_data),
                "requires_approval": event_data.get("requires_approval", False),
            }

            if task_id:
                ws_message["task_id"] = str(task_id)
            if execution_id:
                ws_message["execution_id"] = str(execution_id)
            if structured_data and structured_data.get("message_type"):
                ws_message["structured_data"] = structured_data
            if event_data.get("approval_request_id"):
                ws_message["approval_request_id"] = str(event_data["approval_request_id"])

            # Broadcast
            await self._broadcast(project_id, ws_message)

            # Broadcast task completion if execution_id present
            if execution_id:
                task_complete_msg = {
                    "type": "task_completed",
                    "task_id": str(task_id) if task_id else None,
                    "execution_id": str(execution_id),
                    "agent_name": agent_name,
                    "message_id": str(message_id),
                    "timestamp": self._get_timestamp(event_data),
                }
                await self._broadcast(project_id, task_complete_msg)

        except Exception as e:
            logger.error(f"Error handling agent response: {e}", exc_info=True)

    async def handle_agent_routing(self, event):
        """Handle agent routing events (delegation)"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Agent routing event missing project_id")
                return

            # Skip if no active connections
            if not self._has_active_connections(project_id):
                return

            ws_message = {
                "type": "routing",
                "from_agent": event_data.get("from_agent", ""),
                "to_agent": event_data.get("to_agent", ""),
                "reason": event_data.get("delegation_reason", ""),
                "context": event_data.get("context", {}),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling routing event: {e}", exc_info=True)
