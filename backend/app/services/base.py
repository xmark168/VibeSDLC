"""Base service classes for sync and async operations."""

from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, Session

ModelType = TypeVar("ModelType")


class AsyncBaseService(Generic[ModelType]):
    """Base async service with common CRUD operations.
    
    Provides standard database operations using async/await pattern.
    All operations are non-blocking and use async database session.
    
    Example:
        ```python
        class UserService(AsyncBaseService[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)
                
            async def get_by_email(self, email: str) -> Optional[User]:
                result = await self.session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalar_one_or_none()
        ```
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """Initialize async service.
        
        Args:
            session: Async database session
            model: SQLModel model class
        """
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get entity by ID.
        
        Args:
            id: Entity UUID
            
        Returns:
            Entity instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all entities with pagination.
        
        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            
        Returns:
            List of entities
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def create(self, obj: ModelType) -> ModelType:
        """Create new entity.
        
        Args:
            obj: Entity instance to create
            
        Returns:
            Created entity with ID populated
        """
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def update(self, obj: ModelType) -> ModelType:
        """Update existing entity.
        
        Args:
            obj: Entity instance to update
            
        Returns:
            Updated entity
        """
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def delete(self, obj: ModelType) -> None:
        """Delete entity.
        
        Args:
            obj: Entity instance to delete
        """
        await self.session.delete(obj)
        await self.session.flush()
    
    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()


class SyncBaseService(Generic[ModelType]):
    """Base sync service with common CRUD operations (legacy).
    
    Use AsyncBaseService for new code.
    This class exists for backward compatibility during migration.
    """
    
    def __init__(self, session: Session, model: Type[ModelType]):
        """Initialize sync service.
        
        Args:
            session: Sync database session
            model: SQLModel model class
        """
        self.session = session
        self.model = model
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get entity by ID (sync)."""
        return self.session.get(self.model, id)
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all entities (sync)."""
        result = self.session.exec(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.all())
    
    def create(self, obj: ModelType) -> ModelType:
        """Create new entity (sync)."""
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj
    
    def update(self, obj: ModelType) -> ModelType:
        """Update entity (sync)."""
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj
    
    def delete(self, obj: ModelType) -> None:
        """Delete entity (sync)."""
        self.session.delete(obj)
        self.session.flush()
    
    def commit(self) -> None:
        """Commit transaction (sync)."""
        self.session.commit()
    
    def rollback(self) -> None:
        """Rollback transaction (sync)."""
        self.session.rollback()
