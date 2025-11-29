"""Shared Project Context Cache."""

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
KANBAN_CACHE_TTL = 30


class ProjectContext:
    """Singleton per project_id - shared memory + preferences + Kanban cache."""
    
    _instances: Dict[UUID, "ProjectContext"] = {}
    
    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self.memory: List[dict] = []
        self.preferences: dict = {}
        self._loaded = False
        self._lock = asyncio.Lock()
        self._max_memory = 20
        
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
        try:
            from sqlmodel import Session, select
            from app.core.db import engine
            from app.models import Message, AuthorType, MessageVisibility
            
            with Session(engine) as session:
                messages = session.exec(
                    select(Message)
                    .where(Message.project_id == self.project_id)
                    .where(Message.visibility == MessageVisibility.USER_MESSAGE)
                    .order_by(Message.created_at.desc())
                    .limit(self._max_memory)
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
        self.memory.append({"role": role, "content": content[:500]})
        if len(self.memory) > self._max_memory:
            self.memory = self.memory[-self._max_memory:]
    
    def update_preference(self, key: str, value):
        self.preferences[key] = value
    
    def invalidate(self):
        self._loaded = False
    
    def invalidate_kanban(self):
        """Force refresh Kanban cache on next access."""
        self._kanban_loaded_at = 0
    
    def get_kanban_context(self) -> tuple[dict, dict, dict]:
        """Get cached Kanban context, refresh if TTL expired.
        
        Returns:
            (board_state, flow_metrics, wip_available)
        """
        now = time.time()
        if now - self._kanban_loaded_at > KANBAN_CACHE_TTL:
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
                self._kanban_flow_metrics = kanban_service.get_project_flow_metrics(self.project_id)
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
        if not self.memory:
            return ""
        msgs = self.memory[:-1] if exclude_last else self.memory
        return "\n".join(f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in msgs)
    
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
