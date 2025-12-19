"""LangGraph Workflow for Business Analyst"""

import logging
from functools import partial
from typing import Literal, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .state import BAState
from .nodes import (
    analyze_intent,
    respond_conversational,
    interview_requirements,
    ask_one_question,
    ask_batch_questions,
    process_answer,
    process_batch_answers,
    generate_prd,
    update_prd,
    extract_stories,
    update_stories,
    edit_single_story,
    approve_stories,
    analyze_domain,
    save_artifacts,
    check_clarity,
)
from app.core.config import settings
import psycopg_pool
import asyncio

logger = logging.getLogger(__name__)

# Global PostgresSaver instance (shared across all BA agents)
_postgres_checkpointer: Optional[AsyncPostgresSaver] = None
_connection_pool = None


async def get_postgres_checkpointer() -> AsyncPostgresSaver:
    """Get or create a PostgresSaver checkpointer for persistent state."""
    global _postgres_checkpointer, _connection_pool
    
    # Health check: Reset if pool is closed/stale
    if _connection_pool is not None:
        try:
            if _connection_pool.closed:
                logger.warning("[BA Graph] Connection pool is closed, reinitializing...")
                _postgres_checkpointer = None
                _connection_pool = None
        except Exception:
            pass
    
    if _postgres_checkpointer is None:
       
        
        # Build connection string from settings
        db_url = str(settings.DATABASE_URL)
        if db_url.startswith("postgresql+psycopg"):
            db_url = db_url.replace("postgresql+psycopg", "postgresql")
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"[BA Graph] Creating connection pool (attempt {attempt + 1}/{max_retries})...")
                
                # Create connection pool with larger size and timeout
                _connection_pool = psycopg_pool.AsyncConnectionPool(
                    conninfo=db_url,
                    max_size=10,  # Increased from 5
                    min_size=2,   # Increased from 1
                    open=False,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                    },
                )
                
                # Open with timeout to prevent indefinite hang
                await asyncio.wait_for(
                    _connection_pool.open(),
                    timeout=10.0
                )
                logger.info("[BA Graph] Connection pool opened successfully")
                
                # Create checkpointer
                _postgres_checkpointer = AsyncPostgresSaver(_connection_pool)
                
                # Setup tables if needed
                await _postgres_checkpointer.setup()
                logger.info("[BA Graph] PostgresSaver initialized successfully")
                break
                
            except asyncio.TimeoutError:
                logger.warning(f"[BA Graph] Connection pool open timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"[BA Graph] Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    logger.error("[BA Graph] Failed to connect after 3 retries, falling back to None")
                    return None
                    
            except Exception as e:
                logger.error(f"[BA Graph] PostgresSaver setup failed: {e}")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"[BA Graph] Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"[BA Graph] Failed to create PostgresSaver after retries, falling back to None")
                    return None
    
    return _postgres_checkpointer


def route_by_intent(state: BAState) -> Literal["conversational", "interview", "prd_create", "prd_update", "extract_stories", "stories_update", "story_edit_single", "stories_approve"]:
    """Router: Direct flow based on classified intent."""
    intent = state.get("intent", "interview")
    reasoning = state.get("reasoning", "")
    collected_info = state.get("collected_info", {})
    existing_prd = state.get("existing_prd")
    epics = state.get("epics", [])
    document_type = state.get("document_type", "")
    
    # Conversational messages go directly to respond node
    if intent == "conversational":
        logger.info("[BA Graph] Routing to 'conversational' (casual chat)")
        return "conversational"
    
    # domain_analysis is now integrated into interview flow
    # Redirect to interview which will do research automatically
    if intent == "domain_analysis":
        logger.info("[BA Graph] Redirecting 'domain_analysis' -> 'interview' (research integrated)")
        return "interview"
    
    # FORCE INTERVIEW for partial_requirements documents
    # Even if we have some collected_info, we need to ask about missing parts
    if document_type == "partial_requirements":
        logger.info(
            f"[BA Graph] Overriding '{intent}' -> 'interview': "
            f"Document is partial_requirements, need to ask about missing info"
        )
        return "interview"
    
    # FORCE INTERVIEW only for prd_create without collected info
    # prd_update can proceed if we have existing PRD (user wants to edit it)
    if intent == "prd_create" and not collected_info:
        logger.warning(
            f"[BA Graph] Overriding 'prd_create' -> 'interview': "
            f"No collected info yet, need to gather requirements first"
        )
        return "interview"
    
    # For prd_update, we need existing PRD
    if intent == "prd_update" and not existing_prd:
        logger.warning(
            f"[BA Graph] Overriding 'prd_update' -> 'interview': "
            f"No existing PRD found, need to create PRD first"
        )
        return "interview"
    
    # For stories_update and story_edit_single, we need existing epics
    # For stories_approve, let the node handle loading from artifact
    if intent in ("stories_update", "story_edit_single") and not epics:
        logger.warning(
            f"[BA Graph] Overriding '{intent}' -> 'extract_stories': "
            f"No existing stories found, need to create stories first"
        )
        return "extract_stories"
    
    # story_edit_single: route to dedicated fast edit node
    if intent == "story_edit_single":
        logger.info("[BA Graph] Routing to 'story_edit_single' (targeted single story edit)")
        return "story_edit_single"
    
    # stories_approve: always route to approve_stories, it will load from artifact if needed
    if intent == "stories_approve":
        logger.info("[BA Graph] Routing to 'stories_approve' (will load from artifact if needed)")
        return "stories_approve"
    
    logger.info(f"[BA Graph] Routing to '{intent}': {reasoning[:80] if reasoning else 'no reason'}")
    return intent


def should_ask_questions(state: BAState) -> Literal["ask", "save"]:
    """Router: Decide whether to ask questions or skip to save."""
    has_questions = bool(state.get("questions"))
    
    if has_questions:
        logger.info(f"[BA Graph] {len(state.get('questions', []))} questions to ask")
        return "ask"
    else:
        logger.info("[BA Graph] No questions, skipping to save")
        return "save"


def should_continue_or_wait(state: BAState) -> Literal["wait", "next_question", "generate_prd"]:
    """Router: After asking/processing, decide next step.
    
    - wait: Question sent, waiting for user answer (END this run)
    - next_question: More questions to ask
    - generate_prd: All questions answered, generate PRD
    """
    waiting = state.get("waiting_for_answer", False)
    all_answered = state.get("all_questions_answered", False)
    
    if waiting:
        logger.info("[BA Graph] Waiting for user answer, pausing execution")
        return "wait"
    elif all_answered:
        logger.info("[BA Graph] All questions answered, proceeding to PRD generation")
        return "generate_prd"
    else:
        logger.info("[BA Graph] More questions to ask")
        return "next_question"


def batch_after_ask(state: BAState) -> Literal["wait", "generate_prd"]:
    """Router: After asking batch questions, wait or generate PRD."""
    waiting = state.get("waiting_for_answer", False)
    all_answered = state.get("all_questions_answered", False)
    
    if waiting:
        logger.info("[BA Graph] Batch questions sent, waiting for all answers")
        return "wait"
    elif all_answered:
        logger.info("[BA Graph] All batch answers received, generating PRD")
        return "generate_prd"
    else:
        # If no questions, go to PRD
        return "generate_prd"


def should_save_or_end(state: BAState) -> Literal["save", "end"]:
    """Router: After update_stories, check if we should save or end.
    
    Logic:
    - If found_existing_story=True → end (waiting for user decision)
    - If needs_clarification=True → end (waiting for user clarification)
    - Otherwise → save artifacts
    """
    found_existing = state.get("found_existing_story", False)
    needs_clarification = state.get("needs_clarification", False)
    awaiting_user = state.get("awaiting_user_decision", False)
    
    if found_existing or awaiting_user:
        logger.info("[BA Graph] Found existing story - ending flow (waiting for user)")
        return "end"
    elif needs_clarification:
        logger.info("[BA Graph] Needs clarification - ending flow (waiting for user)")
        return "end"
    else:
        logger.info("[BA Graph] Proceeding to save artifacts")
        return "save"


def should_research_or_generate(state: BAState) -> Literal["research", "generate"]:
    """Router: After processing answers, decide if we need more research or can generate PRD.
    
    Logic:
    1. Check if we've reached max loops (2) → generate PRD
    2. Check clarity (required categories covered?) → if clear, generate PRD
    3. Otherwise → do domain research to get more info
    """
    loop_count = state.get("research_loop_count", 0)
    max_loops = 2
    
    # Max loops reached → generate PRD anyway
    if loop_count >= max_loops:
        logger.info(f"[BA Graph] Max research loops ({max_loops}) reached, generating PRD")
        return "generate"
    
    # Check clarity using categories
    clarity_result = check_clarity(state)
    is_clear = clarity_result.get("is_clear", False)
    missing = clarity_result.get("missing_categories", [])
    
    if is_clear:
        logger.info(f"[BA Graph] Info is clear, generating PRD")
        return "generate"
    else:
        logger.info(f"[BA Graph] Missing categories: {missing}, doing research (loop {loop_count + 1})")
        # Store missing categories in state for domain_analysis to use
        state["missing_categories"] = missing
        return "research"


class BusinessAnalystGraph:
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: BusinessAnalyst agent instance (for Langfuse callback access)
        """
        self.agent = agent
        self.checkpointer = None  # Will be set by setup()
        self._setup_complete = False
        
        graph = StateGraph(BAState)
        
        # Add nodes with agent reference using partial
        graph.add_node("analyze_intent", partial(analyze_intent, agent=agent))
        graph.add_node("respond_conversational", partial(respond_conversational, agent=agent))
        graph.add_node("interview_requirements", partial(interview_requirements, agent=agent))
        # Sequential mode nodes (deprecated but kept for compatibility)
        graph.add_node("ask_one_question", partial(ask_one_question, agent=agent))
        graph.add_node("process_answer", partial(process_answer, agent=agent))
        # Batch mode nodes (preferred)
        graph.add_node("ask_batch_questions", partial(ask_batch_questions, agent=agent))
        graph.add_node("process_batch_answers", partial(process_batch_answers, agent=agent))
        # PRD and other nodes
        graph.add_node("generate_prd", partial(generate_prd, agent=agent))
        graph.add_node("update_prd", partial(update_prd, agent=agent))
        graph.add_node("extract_stories", partial(extract_stories, agent=agent))
        graph.add_node("update_stories", partial(update_stories, agent=agent))
        graph.add_node("edit_single_story", partial(edit_single_story, agent=agent))
        graph.add_node("approve_stories", partial(approve_stories, agent=agent))
        graph.add_node("analyze_domain", partial(analyze_domain, agent=agent))
        graph.add_node("save_artifacts", partial(save_artifacts, agent=agent))
        
        # Set entry point
        graph.set_entry_point("analyze_intent")
        
        # Add conditional routing after intent analysis
        # Note: domain_analysis intent is redirected to interview in route_by_intent()
        graph.add_conditional_edges(
            "analyze_intent",
            route_by_intent,
            {
                "conversational": "respond_conversational",
                "interview": "interview_requirements",
                "prd_create": "generate_prd",
                "prd_update": "update_prd",
                "extract_stories": "extract_stories",
                "stories_update": "update_stories",
                "story_edit_single": "edit_single_story",
                "stories_approve": "approve_stories",
            }
        )
        
        # Interview flow: generate questions -> ask ALL at once (batch mode)
        graph.add_conditional_edges(
            "interview_requirements",
            should_ask_questions,
            {
                "ask": "ask_batch_questions",  # Use batch mode
                "save": "save_artifacts"
            }
        )
        
        # After asking batch questions: wait for all answers
        graph.add_conditional_edges(
            "ask_batch_questions",
            batch_after_ask,
            {
                "wait": END,  # Pause, wait for user answers (RESUME will call process_batch_answers)
                "generate_prd": "generate_prd"  # All answered, generate PRD
            }
        )
        
        # After processing batch answers: check clarity → research or generate PRD
        graph.add_conditional_edges(
            "process_batch_answers",
            should_research_or_generate,
            {
                "research": "analyze_domain",  # Need more info → web search + more questions
                "generate": "generate_prd"     # Info is clear → generate PRD
            }
        )
        
        # After domain analysis (research): loop back to ask more questions
        graph.add_edge("analyze_domain", "ask_batch_questions")
        
        # Keep sequential mode edges for backward compatibility (not used in main flow)
        graph.add_conditional_edges(
            "ask_one_question",
            should_continue_or_wait,
            {
                "wait": END,
                "next_question": "ask_one_question",
                "generate_prd": "generate_prd"
            }
        )
        
        graph.add_conditional_edges(
            "process_answer",
            should_continue_or_wait,
            {
                "wait": END,
                "next_question": "ask_one_question",
                "generate_prd": "generate_prd"
            }
        )
        
        # Conversational -> END (no artifacts to save)
        graph.add_edge("respond_conversational", END)
        
        # PRD creation -> save (wait for user approval before extracting stories)
        graph.add_edge("generate_prd", "save_artifacts")
        
        # Story extraction -> save (called when user approves PRD)
        graph.add_edge("extract_stories", "save_artifacts")
        
        # Story update -> conditional: check if we should save or end early
        graph.add_conditional_edges(
            "update_stories",
            should_save_or_end,
            {
                "save": "save_artifacts",
                "end": END  # End early if found duplicate or needs clarification
            }
        )
        
        # Single story edit -> save (fast targeted edit)
        graph.add_edge("edit_single_story", "save_artifacts")
        
        # Story approve -> save
        graph.add_edge("approve_stories", "save_artifacts")
        
        # PRD update -> conditional: check if we should save or end early (for clarification)
        graph.add_conditional_edges(
            "update_prd",
            should_save_or_end,
            {
                "save": "save_artifacts",
                "end": END  # End early if needs clarification for new feature
            }
        )
        
        # Note: analyze_domain now loops back to ask_batch_questions (defined above)
        # Removed: graph.add_edge("analyze_domain", "save_artifacts")
        
        # Save -> END
        graph.add_edge("save_artifacts", END)
        
        # Store uncompiled graph - will compile with checkpointer in setup()
        self._graph_builder = graph
        self.graph = None
        
        logger.info("[BA Graph] Graph builder ready, call setup() before execute()")
    
    async def setup(self):
        """Setup graph with PostgresSaver checkpointer for persistent state."""
        if self._setup_complete:
            return
        
        try:
            # Try to get PostgresSaver
            self.checkpointer = await get_postgres_checkpointer()
            
            if self.checkpointer:
                # Compile with PostgresSaver for persistent checkpoints
                self.graph = self._graph_builder.compile(checkpointer=self.checkpointer)
                logger.info("[BA Graph] Compiled with PostgresSaver checkpointer")
            else:
                # Fallback to MemorySaver
                self.checkpointer = MemorySaver()
                self.graph = self._graph_builder.compile(checkpointer=self.checkpointer)
                logger.warning("[BA Graph] Compiled with MemorySaver (no persistence)")
            
            self._setup_complete = True
            
        except Exception as e:
            logger.error(f"[BA Graph] Setup failed: {e}, using MemorySaver")
            self.checkpointer = MemorySaver()
            self.graph = self._graph_builder.compile(checkpointer=self.checkpointer)
            self._setup_complete = True
    
    async def execute(self, initial_state: dict, config: dict = None) -> dict:
        """Execute graph with initial state.
        
        Args:
            initial_state: Initial state dict
            config: Optional config with thread_id for checkpointing
        """
        # Ensure setup is complete
        if not self._setup_complete:
            await self.setup()
        
        logger.info(f"[BA Graph] Starting execution...")
        
        try:
            if config:
                result = await self.graph.ainvoke(initial_state, config)
            else:
                result = await self.graph.ainvoke(initial_state)
            
            logger.info(
                f"[BA Graph] Execution complete: "
                f"intent={result.get('intent')}, "
                f"complete={result.get('is_complete', False)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[BA Graph] Execution failed: {e}", exc_info=True)
            raise
    
    async def resume(self, config: dict) -> dict:
        """Resume graph from checkpoint using Command(resume=True).
        """
        if not self._setup_complete:
            await self.setup()
        
        from langgraph.types import Command
        
        logger.info(f"[BA Graph] Resuming from checkpoint...")
        
        try:
            result = await self.graph.ainvoke(Command(resume=True), config)
            
            logger.info(
                f"[BA Graph] Resume complete: "
                f"intent={result.get('intent')}, "
                f"complete={result.get('is_complete', False)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[BA Graph] Resume failed: {e}", exc_info=True)
            raise
