"""Team Leader Agent - LangGraph-based Routing."""

import logging
from typing import List
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel
from app.agents.team_leader.src import TeamLeaderGraph

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader using LangGraph for intelligent routing.
    
    Langfuse tracing is handled by BaseAgent._process_task().
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Agent")
        
        # Memory: conversation history cache (restored from DB on first task)
        self._memory: List[dict] = []
        self._memory_max_size = 20
        self._memory_restored = False
        
        # User preferences cache (loaded from DB on first task)
        self._preferences: dict = {}
        self._preferences_loaded = False
        
        # Pass self to graph for delegation and Langfuse callback access
        self.graph_engine = TeamLeaderGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized successfully")
    
    def _trim_memory(self) -> None:
        """Keep only recent messages."""
        if len(self._memory) > self._memory_max_size:
            self._memory = self._memory[-self._memory_max_size:]
    
    def _format_memory(self) -> str:
        """Format memory for LLM prompt."""
        if not self._memory:
            return ""
        lines = []
        for msg in self._memory[:-1]:  # Exclude current message (already in prompt)
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    async def _restore_memory_from_db(self) -> None:
        """Restore memory from recent messages in DB (called once on first task)."""
        if self._memory_restored:
            return
        
        self._memory_restored = True
        
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
                    .limit(self._memory_max_size)
                ).all()
            
            # Reverse to chronological order
            self._memory = [
                {"role": "user" if m.author_type == AuthorType.USER else "assistant",
                 "content": m.content[:500]}
                for m in reversed(messages)
            ]
            
            logger.info(f"[{self.name}] Restored {len(self._memory)} messages from DB")
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to restore memory from DB: {e}")

    async def _load_preferences_from_db(self) -> None:
        """Load project preferences from DB (called once on first task)."""
        if self._preferences_loaded:
            return
        
        self._preferences_loaded = True
        
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import ProjectPreference
            
            with Session(engine) as session:
                pref = session.query(ProjectPreference).filter(
                    ProjectPreference.project_id == self.project_id
                ).first()
                
                if pref and pref.preferences:
                    self._preferences = pref.preferences
                    logger.info(f"[{self.name}] Loaded preferences: {list(self._preferences.keys())}")
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to load preferences: {e}")
    
    def _format_preferences(self) -> str:
        """Format preferences for LLM prompt.
        
        Handles flexible JSONB preferences with smart formatting.
        """
        if not self._preferences:
            return ""
        
        lines = []
        
        # Known preference keys with custom formatting
        key_labels = {
            "preferred_language": "Preferred language",
            "communication_style": "Communication style",
            "response_length": "Response length",
            "expertise_level": "User expertise level",
            "timezone": "Timezone",
            "domain_context": "Domain/Project context",
            "tech_stack": "Tech stack",
            "custom_instructions": "Special instructions",
        }
        
        for key, value in self._preferences.items():
            if value is None or value == "" or value == "auto":
                continue
            
            # Handle boolean emoji_usage specially
            if key == "emoji_usage" and value is False:
                lines.append("- Do not use emojis")
                continue
            elif key == "emoji_usage":
                continue  # Skip if True (default behavior)
            
            # Handle lists (e.g., tech_stack)
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            
            label = key_labels.get(key, key.replace("_", " ").title())
            lines.append(f"- {label}: {value}")
        
        return "\n".join(lines) if lines else ""

    async def update_preference(self, key: str, value) -> bool:
        """Update a single preference in DB and local cache.
        
        Args:
            key: Preference key (e.g., 'preferred_language', 'emoji_usage')
            value: Preference value (can be str, bool, list, dict, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import ProjectPreference
            
            with Session(engine) as session:
                pref = session.query(ProjectPreference).filter(
                    ProjectPreference.project_id == self.project_id
                ).first()
                
                if not pref:
                    # Create new preference record
                    pref = ProjectPreference(
                        project_id=self.project_id,
                        preferences={key: value}
                    )
                    session.add(pref)
                else:
                    # Update existing preferences (merge)
                    current = pref.preferences or {}
                    current[key] = value
                    pref.preferences = current
                
                session.commit()
                
                # Update local cache
                self._preferences[key] = value
                
                logger.info(f"[{self.name}] Updated preference: {key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"[{self.name}] Failed to update preference: {e}")
            return False

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph with conversation memory.
        
        Note: Langfuse tracing is automatically handled by BaseAgent.
        """
        logger.info(f"[{self.name}] Processing task with LangGraph: {task.content[:50]}")
        
        # Restore memory and preferences from DB on first task
        await self._restore_memory_from_db()
        await self._load_preferences_from_db()
        
        try:
            # 1. Add user message to memory
            self._memory.append({
                "role": "user",
                "content": task.content[:500]
            })
            self._trim_memory()
            
            # 2. Build state with conversation history and preferences
            initial_state = {
                "messages": [],
                "user_message": task.content,
                "user_id": str(task.user_id) if task.user_id else "",
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "conversation_history": self._format_memory(),
                "user_preferences": self._format_preferences(),
                "action": None,
                "target_role": None,
                "message": None,
                "reason": None,
                "confidence": None,
            }
            
            logger.info(f"[{self.name}] Invoking LangGraph with {len(self._memory)} messages in memory...")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            action = final_state.get("action")
            confidence = final_state.get("confidence")
            target_role = final_state.get("target_role")
            response_msg = final_state.get("message", "")
            
            # 3. Add response to memory
            if response_msg:
                self._memory.append({
                    "role": "assistant",
                    "content": response_msg[:500]
                })
                self._trim_memory()
            
            logger.info(
                f"[{self.name}] Graph completed: action={action}, "
                f"confidence={confidence}"
            )
            
            return TaskResult(
                success=True,
                output=response_msg,
                structured_data={
                    "action": action,
                    "target_role": target_role,
                    "reason": final_state.get("reason"),
                    "confidence": confidence,
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )

