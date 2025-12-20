from app.core.config import project_context_settings
"""Shared Project Context Cache with Rolling Summarization."""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

PREF_LABELS = {
    "preferred_language": "Preferred language",
    "communication_style": "Communication style",
    "response_length": "Response length",
    "expertise_level": "User expertise level",
    "timezone": "Timezone",
    "domain_context": "Domain/Project context",
    "tech_stack": "Tech stack",
    "custom_instructions": "Special instructions",
}

# Kanban cache TTL (seconds) - shorter than preferences since board changes more often
# Moved to project_context_settings

# Summarization settings
# Moved to project_context_settings  # Summarize when memory has N messages, then clear them


class ProjectContext:
    """Singleton per project_id - shared memory + preferences + Kanban cache + rolling summary.
    
    Summarization flow:
    1. Messages accumulate in self.memory
    2. When len(memory) >= project_context_settings.SUMMARY_THRESHOLD, summarize and CLEAR those messages
    3. format_memory() returns: summary + remaining messages
    """
    
    _instances: Dict[UUID, "ProjectContext"] = {}
    
    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self.memory: List[dict] = []  # Only unsummarized messages
        self.preferences: dict = {}
        self._loaded = False
        self._lock = asyncio.Lock()
        
        # Rolling summarization - summary of older messages (cleared from memory)
        self._summary: str = ""
        self._summary_lock = asyncio.Lock()
        
        # Kanban context cache (lazy loaded, with TTL)
        self._kanban_board_state: Optional[dict] = None
        self._kanban_flow_metrics: Optional[dict] = None
        self._kanban_wip_available: Optional[dict] = None
        self._kanban_loaded_at: float = 0
    
    @classmethod
    def get(cls, project_id: UUID) -> "ProjectContext":
        if project_id not in cls._instances:
            cls._instances[project_id] = cls(project_id)
        return cls._instances[project_id]
    
    @classmethod
    def clear(cls, project_id: UUID = None):
        if project_id:
            cls._instances.pop(project_id, None)
        else:
            cls._instances.clear()
    
    async def ensure_loaded(self):
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            await asyncio.gather(self._load_memory(), self._load_preferences(), return_exceptions=True)
            self._loaded = True
    
    async def _load_memory(self):
        """Load recent messages from DB (only used for initial context)."""
        try:
            from sqlmodel import Session, select
            from app.core.db import engine
            from app.models import Message, AuthorType, MessageVisibility
            
            # Load last 10 messages for initial context (will be summarized if needed)
            with Session(engine) as session:
                messages = session.exec(
                    select(Message)
                    .where(Message.project_id == self.project_id)
                    .where(Message.visibility == MessageVisibility.USER_MESSAGE)
                    .order_by(Message.created_at.desc())
                    .limit(10)
                ).all()
            
            self.memory = [
                {"role": "user" if m.author_type == AuthorType.USER else "assistant",
                 "content": (m.content or "")[:500]}
                for m in reversed(messages)
            ]
        except Exception as e:
            logger.warning(f"[ProjectContext] Load memory failed: {e}")
    
    async def _load_preferences(self):
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import ProjectPreference
            
            with Session(engine) as session:
                pref = session.query(ProjectPreference).filter(
                    ProjectPreference.project_id == self.project_id
                ).first()
                if pref and pref.preferences:
                    self.preferences = pref.preferences
        except Exception as e:
            logger.warning(f"[ProjectContext] Load preferences failed: {e}")
    
    def add_message(self, role: str, content: str):
        """Add message to memory (unsummarized messages only)."""
        self.memory.append({"role": role, "content": content[:500]})
    
    async def maybe_summarize(self):
        """Check and create summary if enough messages, then clear them."""
        if len(self.memory) >= project_context_settings.SUMMARY_THRESHOLD:
            async with self._summary_lock:
                # Double-check after acquiring lock
                if len(self.memory) >= project_context_settings.SUMMARY_THRESHOLD:
                    await self._create_summary()
    
    async def _create_summary(self):
        """Summarize messages and CLEAR them from memory."""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            
            # Take first project_context_settings.SUMMARY_THRESHOLD messages to summarize
            messages_to_summarize = self.memory[:project_context_settings.SUMMARY_THRESHOLD]
            
            if not messages_to_summarize:
                return
            
            # Format messages for summarization
            messages_text = "\n".join(
                f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                for m in messages_to_summarize
            )
            
            system_prompt = """You are a conversation summarizer. Create a concise summary that captures:
1. Key user requests and decisions made
2. Important items created/modified/deleted (preserve IDs like US-017, EPIC-001)
3. Current project state and context

Keep the summary to 2-4 sentences. Focus on information an AI agent would need to understand future requests.
Write in the same language as the conversation (Vietnamese if the conversation is in Vietnamese)."""

            prompt = f"""Previous context summary:
{self._summary or "None"}

New conversation to incorporate:
{messages_text}

Create an updated summary that merges the previous context with the new conversation.
Keep IDs (like US-017, EPIC-001) and important decisions.
Write 2-4 sentences maximum."""

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, timeout=30)
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ])
            
            self._summary = response.content.strip()
            
            # CLEAR summarized messages from memory
            self.memory = self.memory[project_context_settings.SUMMARY_THRESHOLD:]
            
            logger.info(f"[ProjectContext] Created summary, cleared {project_context_settings.SUMMARY_THRESHOLD} messages. Summary: {self._summary[:100]}...")
            
        except Exception as e:
            logger.warning(f"[ProjectContext] Summarization failed: {e}")
    
    def update_preference(self, key: str, value):
        self.preferences[key] = value
    
    def invalidate(self):
        """Reset context - used when project changes significantly."""
        self._loaded = False
        self._summary = ""
        self.memory = []
    
    def invalidate_kanban(self):
        """Force refresh Kanban cache on next access."""
        self._kanban_loaded_at = 0
    
    def get_kanban_context(self) -> tuple[dict, dict, dict]:
        """Get cached Kanban context, refresh if TTL expired.
        
        Returns:
            (board_state, flow_metrics, wip_available)
        """
        now = time.time()
        if now - self._kanban_loaded_at > project_context_settings.KANBAN_CACHE_TTL:
            self._load_kanban_context()
        
        return (
            self._kanban_board_state or {},
            self._kanban_flow_metrics or {},
            self._kanban_wip_available or {},
        )
    
    def _load_kanban_context(self):
        """Load Kanban context from DB."""
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.services import KanbanService
            
            with Session(engine) as session:
                kanban_service = KanbanService(session)
                self._kanban_board_state = kanban_service.get_dynamic_wip_with_usage(self.project_id)
                # TODO: Re-implement get_project_flow_metrics
                self._kanban_flow_metrics = {}  # kanban_service.get_project_flow_metrics(self.project_id)
                self._kanban_wip_available = {
                    col: data.get("available", 0) 
                    for col, data in self._kanban_board_state.items()
                }
                self._kanban_loaded_at = time.time()
                
                logger.debug(f"[ProjectContext] Kanban loaded: WIP={self._kanban_wip_available}")
        except Exception as e:
            logger.warning(f"[ProjectContext] Load Kanban failed: {e}")
            self._kanban_board_state = {}
            self._kanban_flow_metrics = {}
            self._kanban_wip_available = {}
    
    def format_memory(self, exclude_last: bool = True) -> str:
        """Format memory: summary + all remaining messages.
        
        Returns:
            Formatted string with:
            - Summary of older messages (if available)
            - All unsummarized messages in memory
        """
        msgs = self.memory[:-1] if (exclude_last and self.memory) else self.memory
        
        parts = []
        
        # Add summary if available
        if self._summary:
            parts.append(f"## Tóm tắt:\n{self._summary}")
        
        # Add remaining messages
        if msgs:
            recent_text = "\n".join(
                f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                for m in msgs
            )
            parts.append(f"## Gần đây:\n{recent_text}")
        
        return "\n\n".join(parts) if parts else ""
    
    def format_preferences(self) -> str:
        if not self.preferences:
            return ""
        lines = []
        for k, v in self.preferences.items():
            if v is None or v == "" or v == "auto":
                continue
            if k == "emoji_usage":
                if v is False:
                    lines.append("- Do not use emojis")
                continue
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            lines.append(f"- {PREF_LABELS.get(k, k.replace('_', ' ').title())}: {v}")
        return "\n".join(lines)
