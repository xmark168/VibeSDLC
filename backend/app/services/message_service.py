"""Message Service - Encapsulates message database operations."""

from uuid import UUID
from typing import List, Optional

from sqlmodel import Session, select

from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Message as MessageModel, Message, AuthorType, MessageVisibility


class MessageService:
    """Service for message database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        project_id: UUID,
        content: str,
        author_type: AuthorType,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        message_type: str = "text",
        structured_data: Optional[dict] = None,
        visibility: MessageVisibility = MessageVisibility.USER_MESSAGE,
        message_metadata: Optional[dict] = None,
        **kwargs
    ) -> MessageModel:
        """Create a new message."""
        message = MessageModel(
            project_id=project_id,
            user_id=user_id,
            agent_id=agent_id,
            content=content,
            author_type=author_type,
            visibility=visibility,
            message_type=message_type,
            structured_data=structured_data,
            message_metadata=message_metadata,
            **kwargs
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def create_user_message(
        self,
        project_id: UUID,
        user_id: UUID,
        content: str,
        agent_id: Optional[UUID] = None,
        **kwargs
    ) -> MessageModel:
        """Shortcut for creating user messages.
        
        Args:
            project_id: Project UUID
            user_id: User ID
            content: Message content
            agent_id: Optional agent ID for @mention routing
            **kwargs: Additional fields
            
        Returns:
            Created message
        """
        return self.create(
            project_id=project_id,
            user_id=user_id,
            content=content,
            author_type=AuthorType.USER,
            agent_id=agent_id,
            visibility=MessageVisibility.USER_MESSAGE,
            **kwargs
        )

    def create_agent_message(
        self,
        project_id: UUID,
        agent_name: str,
        content: str,
        execution_id: Optional[UUID] = None,
        message_type: str = "text",
        structured_data: Optional[dict] = None,
        **kwargs
    ) -> MessageModel:
        """Shortcut for creating agent messages.
        
        Args:
            project_id: Project UUID
            agent_name: Agent name
            content: Message content
            execution_id: Optional execution ID
            message_type: Message type
            structured_data: Optional structured data
            **kwargs: Additional fields
            
        Returns:
            Created message
        """
        # Build metadata
        metadata = {"agent_name": agent_name}
        if execution_id:
            metadata["execution_id"] = str(execution_id)
        
        return self.create(
            project_id=project_id,
            content=content,
            author_type=AuthorType.AGENT,
            message_type=message_type,
            structured_data=structured_data,
            message_metadata=metadata,
            visibility=MessageVisibility.USER_MESSAGE,
            **kwargs
        )

    def create_activity_message(
        self,
        project_id: UUID,
        agent_name: str,
        content: str,
        execution_id: UUID,
        structured_data: Optional[dict] = None,
        **kwargs
    ) -> MessageModel:
        """Shortcut for creating activity messages.
        
        Args:
            project_id: Project UUID
            agent_name: Agent name
            content: Activity description
            execution_id: Execution ID
            structured_data: Optional structured data
            **kwargs: Additional fields
            
        Returns:
            Created message
        """
        metadata = {
            "agent_name": agent_name,
            "execution_id": str(execution_id)
        }
        
        return self.create(
            project_id=project_id,
            content=content,
            author_type=AuthorType.AGENT,
            message_type="activity",
            structured_data=structured_data,
            message_metadata=metadata,
            visibility=MessageVisibility.INTERNAL,
            **kwargs
        )

    def get_by_id(self, message_id: UUID) -> Optional[MessageModel]:
        """Get message by ID.
        
        Args:
            message_id: Message UUID
            
        Returns:
            Message or None if not found
        """
        return self.session.get(MessageModel, message_id)

    def update(
        self,
        message_id: UUID,
        **fields
    ) -> Optional[MessageModel]:
        """Update message fields.
        
        Args:
            message_id: Message UUID
            **fields: Fields to update
            
        Returns:
            Updated message or None if not found
        """
        message = self.session.get(MessageModel, message_id)
        if message:
            for key, value in fields.items():
                if hasattr(message, key):
                    setattr(message, key, value)
            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)
        return message

    def update_structured_data(
        self,
        message_id: UUID,
        structured_data: dict
    ) -> Optional[MessageModel]:
        """Update structured data of a message.
        
        Args:
            message_id: Message UUID
            structured_data: New structured data
            
        Returns:
            Updated message or None if not found
        """
        return self.update(message_id, structured_data=structured_data)

    def get_by_project(
        self,
        project_id: UUID,
        limit: int = 100,
        offset: int = 0,
        visibility: Optional[MessageVisibility] = None
    ) -> list[MessageModel]:
        """Get messages for a project.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of messages
            offset: Number of messages to skip
            visibility: Optional visibility filter
            
        Returns:
            List of messages
        """
        statement = (
            select(MessageModel)
            .where(MessageModel.project_id == project_id)
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if visibility:
            statement = statement.where(MessageModel.visibility == visibility)
        return self.session.exec(statement).all()

    def get_user_facing_messages(
        self,
        project_id: UUID,
        limit: int = 100
    ) -> list[MessageModel]:
        """Get user-facing messages for a project.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of messages
            
        Returns:
            List of user-facing messages
        """
        return self.get_by_project(
            project_id=project_id,
            limit=limit,
            visibility=MessageVisibility.USER_MESSAGE
        )

    def delete(self, message_id: UUID) -> bool:
        """Delete a message.
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        message = self.session.get(MessageModel, message_id)
        if message:
            self.session.delete(message)
            self.session.commit()
            return True
        return False


# ============================================================================
# ASYNC MESSAGE SERVICE - New async implementation
# ============================================================================

class AsyncMessageService:
    """Async message service for high-performance operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """Get message by ID (async)."""
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def create_message(self, message_data: dict) -> Message:
        """Create new message (async)."""
        message = Message(**message_data)
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message
    
    async def get_by_project(
        self,
        project_id: UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a project (async)."""
        result = await self.session.execute(
            select(Message)
            .where(Message.project_id == project_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message (async)."""
        message = await self.get_by_id(message_id)
        if not message:
            return False
        
        await self.session.delete(message)
        await self.session.commit()
        return True
