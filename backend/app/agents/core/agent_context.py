"""Agent Context Protocol and Implementation.

This module provides a clean interface for tools to interact with agents,
decoupling tools from the agent pool manager implementation.

Architecture:
- AgentContext: Protocol defining operations available to tools
- AgentToolContext: Concrete implementation backed by BaseAgent
"""

from typing import Protocol, Optional, List, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class AgentContext(Protocol):
    """Protocol for agent operations available to tools.
    
    This protocol defines the interface that tools can use to interact with
    agents without needing to know about pool managers or agent internals.
    
    Benefits:
    - Loose coupling: Tools don't depend on agent implementation
    - Testability: Easy to mock in tests
    - Flexibility: Can be implemented by different agent types
    - Future-proof: Supports migration to distributed architecture
    """
    
    async def send_message(
        self, 
        event_type: str, 
        content: str, 
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[UUID]:
        """Send message/event to user.
        
        Args:
            event_type: Type of event (response, thinking, progress, etc.)
            content: Message content (human-readable text)
            details: Additional structured data
            **kwargs: Extra metadata
            
        Returns:
            Message ID if saved, None otherwise
        """
        ...
    
    async def ask_question(
        self,
        question: str,
        question_type: str = "open",
        options: Optional[List[str]] = None,
        allow_multiple: bool = False
    ) -> UUID:
        """Ask user a clarification question.
        
        Args:
            question: Question text to ask user
            question_type: Type of question (open, multichoice, multiselect, yesno)
            options: List of options for multichoice/multiselect
            allow_multiple: Allow multiple selections (for multiselect)
            
        Returns:
            Question ID (UUID)
        """
        ...
    
    async def create_artifact(
        self,
        artifact_type: str,
        title: str,
        content: dict,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> UUID:
        """Create and persist an artifact.
        
        Args:
            artifact_type: Type of artifact (prd, architecture, code, etc.)
            title: Human-readable title
            content: Structured content dict
            description: Optional description
            tags: Optional tags for categorization
            
        Returns:
            Artifact ID (UUID)
        """
        ...


class AgentToolContext:
    """Concrete implementation of AgentContext backed by BaseAgent.
    
    This class wraps a BaseAgent instance and provides the AgentContext
    interface for tools to use.
    
    Example:
        >>> agent = BusinessAnalyst(...)
        >>> context = AgentToolContext(agent)
        >>> question_id = await context.ask_question("What is the feature name?")
    """
    
    def __init__(self, agent):
        """Initialize tool context.
        
        Args:
            agent: BaseAgent instance to wrap
        """
        self._agent = agent
        logger.debug(f"Created AgentToolContext for agent {agent.name}")
    
    async def send_message(
        self, 
        event_type: str, 
        content: str, 
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[UUID]:
        """Send message via agent's message_user method."""
        return await self._agent.message_user(
            event_type=event_type,
            content=content,
            details=details,
            **kwargs
        )
    
    async def ask_question(
        self,
        question: str,
        question_type: str = "open",
        options: Optional[List[str]] = None,
        allow_multiple: bool = False
    ) -> UUID:
        """Ask question via agent's message_user method."""
        return await self._agent.message_user(
            event_type="question",
            content=question,
            question_config={
                "question_type": question_type,
                "options": options,
                "allow_multiple": allow_multiple
            }
        )
    
    async def create_artifact(
        self,
        artifact_type: str,
        title: str,
        content: dict,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> UUID:
        """Create artifact via agent's message_user method."""
        return await self._agent.message_user(
            event_type="artifact",
            content=f"Created {artifact_type}: {title}",
            artifact_config={
                "artifact_type": artifact_type,
                "title": title,
                "content": content,
                "description": description,
                "tags": tags or [],
                "save_to_file": True
            }
        )
    
    @property
    def agent_id(self) -> UUID:
        """Get agent ID."""
        return self._agent.agent_id
    
    @property
    def agent_name(self) -> str:
        """Get agent name."""
        return self._agent.name
    
    @property
    def project_id(self) -> UUID:
        """Get project ID."""
        return self._agent.project_id
