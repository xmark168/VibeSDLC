"""Shared Project Context Cache."""

import asyncio
import logging
from typing import Dict, List
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


class ProjectContext:
    """Singleton per project_id - shared memory + preferences cache."""
    
    _instances: Dict[UUID, "ProjectContext"] = {}
    
    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self.memory: List[dict] = []
        self.preferences: dict = {}
        self._loaded = False
        self._lock = asyncio.Lock()
        self._max_memory = 20
    
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
