"""Business Analyst Agent - LangGraph-based Implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Set
from uuid import UUID
from sqlmodel import Session, select
from app.core.agent.base_agent import BaseAgent, TaskContext, TaskResult
from app.core.agent.project_context import ProjectContext
from app.core.agent.mixins import PausableAgentMixin
from app.models import Agent as AgentModel, Project, AgentQuestion, QuestionStatus, ArtifactType
from app.utils.project_files import ProjectFiles
from app.kafka.event_schemas import AgentTaskType
from app.core.db import engine
from app.services.artifact_service import ArtifactService
from app.agents.business_analyst.src import BusinessAnalystGraph
from app.agents.business_analyst.src.nodes import (
    process_answer, ask_one_question, 
    process_batch_answers,
    generate_prd, update_prd, extract_stories, save_artifacts,
    check_clarity, analyze_domain, ask_batch_questions,
    analyze_document_content, generate_document_feedback,
)

logger = logging.getLogger(__name__)


class TaskStoppedException(Exception):
    """Raised when task processing should stop (pause/cancel)."""
    def __init__(self, task_id: str, reason: str, message: str = ""):
        self.task_id = task_id
        self.reason = reason  # "pause" or "cancel"
        self.message = message or f"Task {task_id} stopped: {reason}"
        super().__init__(self.message)


class BusinessAnalyst(BaseAgent, PausableAgentMixin):
    """
    Business Analyst using LangGraph for workflow management.
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Business Analyst LangGraph")
        self.context = ProjectContext.get(self.project_id)
        self.project_files = None
        if self.project_id:
            with Session(engine) as session:
                project = session.exec(
                    select(Project).where(Project.id == self.project_id)
                ).first()
                
                if project and project.project_path:
                    self.project_files = ProjectFiles(Path(project.project_path))
                else:
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        # Pass self to graph for Langfuse callback access
        self.graph_engine = BusinessAnalystGraph(agent=self)
        
        # Initialize PausableAgentMixin (provides pause/resume/cancel functionality)
        self.init_pausable_mixin()
        
        logger.info(f"[{self.name}] LangGraph initialized successfully")
    
    # =========================================================================
    # PAUSE/RESUME/CANCEL METHODS (Dev V2 pattern)
    # =========================================================================
    
    def check_should_stop(self, task_id: str) -> None:
        """Check if task should stop. Raises TaskStoppedException if cancelled/paused."""
        signal = self.check_signal(task_id)
        if signal == "cancel":
            self._cancelled_tasks.add(task_id)
            raise TaskStoppedException(task_id, "cancel", "Cancel requested")
        elif signal == "pause":
            self._paused_tasks.add(task_id)
            raise TaskStoppedException(task_id, "pause", "Paused")
    
    def is_task_paused(self, task_id: str) -> bool:
        """Check if task is paused."""
        return task_id in self._paused_tasks
    
    def is_task_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        return task_id in self._cancelled_tasks
    
    async def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        self._paused_tasks.add(task_id)
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"[{self.name}] Paused task {task_id}")
            return True
        return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        self._cancelled_tasks.add(task_id)
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            await self._cleanup_task(task_id)
            logger.info(f"[{self.name}] Cancelled task {task_id}")
            return True
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """Check if task can be resumed from checkpoint."""
        try:
            # Check if we have a checkpoint for this task
            if self.graph_engine.checkpointer:
                config = {"configurable": {"thread_id": f"{self.agent_id}_{task_id}"}}
                checkpoint = await self.graph_engine.checkpointer.aget(config)
                if checkpoint:
                    self._paused_tasks.discard(task_id)
                    logger.info(f"[{self.name}] Task {task_id} can be resumed from checkpoint")
                    return True
            return False
        except Exception as e:
            logger.error(f"[{self.name}] Error checking resume for {task_id}: {e}")
            return False
    
    async def _cleanup_task(self, task_id: str):
        """Cleanup resources for a cancelled/finished task."""
        self._running_tasks.pop(task_id, None)
        self._cancelled_tasks.discard(task_id)
        self._paused_tasks.discard(task_id)
        self.clear_signal(task_id)
    
    def clear_task_cache(self, task_id: str) -> None:
        """Clear task from caches for restart."""
        self._cancelled_tasks.discard(task_id)
        self._paused_tasks.discard(task_id)
        self._running_tasks.pop(task_id, None)
        self.clear_signal(task_id)
    
    async def _run_graph_with_signal_check(self, initial_state: dict, config: dict, task_id: str) -> dict:
        """Run graph with signal checking between nodes."""
        final_state = None
        node_count = 0
        
        # Check signal before start
        signal = self.check_signal(task_id)
        if signal == "cancel":
            raise TaskStoppedException(task_id, "cancel", "Cancel before start")
        
        # Ensure graph is setup
        await self.graph_engine.setup()
        
        async for event in self.graph_engine.graph.astream(initial_state, config, stream_mode="values"):
            node_count += 1
            final_state = event
            
            # Check signal after each node
            signal = self.check_signal(task_id)
            if signal == "cancel":
                self._cancelled_tasks.add(task_id)
                raise TaskStoppedException(task_id, "cancel", "Cancel signal")
            elif signal == "pause":
                self._paused_tasks.add(task_id)
                raise TaskStoppedException(task_id, "pause", "Pause signal")
        
        logger.info(f"[{self.name}] Graph completed after {node_count} nodes")
        return final_state
    
    def _build_base_state(self, task: TaskContext) -> dict:
        """Build base state dict with common fields for all task types."""
        return {
            "project_id": str(self.project_id),
            "task_id": str(task.task_id),
            "user_id": str(task.user_id) if task.user_id else "",
            "project_path": str(self.project_files.project_path) if self.project_files else "",
        }

    def _load_existing_prd(self) -> dict | None:
        """Load existing PRD from Artifact table."""
        try:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.get_latest_version(
                    project_id=self.project_id,
                    artifact_type=ArtifactType.PRD
                )
                if artifact:
                    logger.info(f"[{self.name}] Loaded existing PRD: {artifact.title} (v{artifact.version})")
                    return artifact.content
                return None
        except Exception as e:
            logger.debug(f"[{self.name}] No existing PRD: {e}")
            return None
    
    def _load_existing_epics_and_stories(self) -> tuple[list, list, str]:
        """Load existing epics and stories from Artifact table (for approval flow).
        
        Returns:
            Tuple of (epics_list, stories_list, approval_message)
        """
        try:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.get_latest_version(
                    project_id=self.project_id,
                    artifact_type=ArtifactType.USER_STORIES
                )
                if artifact and artifact.content:
                    content = artifact.content
                    epics = content.get("epics", [])
                    stories = content.get("stories", [])
                    approval_message = content.get("approval_message", "")  # Load saved approval message
                    logger.info(f"[{self.name}] Loaded existing epics/stories from artifact {artifact.id}: {len(epics)} epics, {len(stories)} stories")
                    return epics, stories, approval_message
                else:
                    logger.info(f"[{self.name}] No USER_STORIES artifact found for project {self.project_id}")
                return [], [], ""
        except Exception as e:
            logger.warning(f"[{self.name}] Error loading epics/stories: {e}", exc_info=True)
            return [], [], ""

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph.
        
        Note: Langfuse tracing is automatically handled by BaseAgent.
        Token tracking is handled via callback in BaseAgent._process_task().
        """
        return await self._handle_task_internal(task)
    
    async def _handle_task_internal(self, task: TaskContext) -> TaskResult:
        """Internal task handling logic."""
        # Check if this is a resume task (user answered a question)
        is_resume = task.task_type == AgentTaskType.RESUME_WITH_ANSWER
        
        # For RESUME tasks, answer is in context, not content
        if is_resume:
            answer = task.context.get("answer", "") if task.context else ""
            logger.info(f"[{self.name}] Processing RESUME task with answer: {answer[:50] if answer else 'empty'}")
            return await self._handle_resume_task(task, answer)
        
        logger.info(f"[{self.name}] Processing task with LangGraph: {task.content[:50] if task.content else 'empty'}")
        
        try:
            # Check for UPDATE MODE first (feature is in context, not content)
            is_update_mode = task.context.get("is_update_mode", False) if task.context else False
            if is_update_mode:
                logger.info(f"[{self.name}] Detected UPDATE MODE from context")
                return await self._handle_update_mode(task)
            
            # Validate user message (only for non-resume, non-update tasks)
            if not task.content or not task.content.strip():
                logger.error(f"[{self.name}] Empty task content received")
                return TaskResult(
                    success=False,
                    output="",
                    error_message="Empty user message"
                )
            
            return await self._handle_new_task(task)
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )
    
    async def _handle_resume_task(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle resume task - user answered question(s).
        
        Supports both:
        - Batch mode: All answers at once (is_batch=True in context)
        - Sequential mode: One answer at a time (legacy)
        """
        # Check if this is batch mode
        is_batch = task.context.get("is_batch", False) if task.context else False
        batch_answers = task.context.get("batch_answers", []) if task.context else []
        
        if is_batch:
            logger.info(f"[{self.name}] Handling RESUME task (BATCH mode, {len(batch_answers)} answers)")
            return await self._handle_batch_resume(task, batch_answers)
        else:
            logger.info(f"[{self.name}] Handling RESUME task (sequential mode)")
            return await self._handle_sequential_resume(task, answer)
    
    async def _handle_batch_resume(self, task: TaskContext, batch_answers: list) -> TaskResult:
        """Handle batch mode resume - all answers at once.
        
        Supports different flows based on original_intent:
        - interview: Create new PRD (default)
        - prd_update: Update existing PRD
        - stories_update: Update existing stories
        """
        if not batch_answers:
            logger.error(f"[{self.name}] No batch answers in RESUME task")
            return TaskResult(
                success=False,
                output="",
                error_message="No answers received"
            )
        
        # Load interview state from database
        interview_state = await self._load_interview_state(task)
        
        if not interview_state:
            logger.warning(f"[{self.name}] No interview state found for batch, treating as new task")
            return await self._handle_new_task(task)
        
        # Check original_intent to determine which flow to continue
        original_intent = interview_state.get("original_intent", "interview")
        logger.info(f"[{self.name}] RESUME batch with original_intent: {original_intent}")
        
        # Route to appropriate handler based on original_intent
        if original_intent == "prd_update":
            return await self._handle_prd_update_resume(task, batch_answers, interview_state)
        elif original_intent == "stories_update":
            return await self._handle_stories_update_resume(task, batch_answers, interview_state)
        else:
            # Default: interview flow (create new PRD)
            return await self._handle_interview_resume(task, batch_answers, interview_state)
    
    async def _handle_interview_resume(self, task: TaskContext, batch_answers: list, interview_state: dict) -> TaskResult:
        """Handle interview flow resume - create new PRD."""
        # Load existing PRD from database
        existing_prd = self._load_existing_prd()
        
        # Build state with batch answers
        user_message = interview_state.get("user_message", "") or interview_state.get("original_request", "Tạo PRD dựa trên thông tin đã thu thập")
        
        state = {
            **self._build_base_state(task),
            "user_message": user_message,
            "collected_info": interview_state.get("collected_info", {}),
            "existing_prd": existing_prd,
            "intent": "interview",
            "questions": interview_state.get("questions", []),
            "batch_answers": batch_answers,
            "waiting_for_answer": False,
            "all_questions_answered": False,
            "research_loop_count": interview_state.get("research_loop_count", 0),
        }
        
        # Process all batch answers
        logger.info(f"[{self.name}] Processing {len(batch_answers)} batch answers for interview")
        state = {**state, **(await process_batch_answers(state, agent=self))}
        
        # Check clarity - do we have enough info or need more research?
        max_research_loops = 2
        research_loop_count = state.get("research_loop_count", 0)
        
        while research_loop_count < max_research_loops:
            clarity_result = check_clarity(state)
            is_clear = clarity_result.get("is_clear", False)
            missing_categories = clarity_result.get("missing_categories", [])
            
            if is_clear:
                logger.info(f"[{self.name}] Info is clear, generating PRD")
                break
            else:
                logger.info(f"[{self.name}] Missing categories: {missing_categories}, doing research (loop {research_loop_count + 1})")
                state["missing_categories"] = missing_categories
                
                # Do domain research and generate more questions
                state = {**state, **(await analyze_domain(state, agent=self))}
                research_loop_count = state.get("research_loop_count", research_loop_count + 1)
                
                # Check if we have new questions to ask
                new_questions = state.get("questions", [])
                if new_questions:
                    logger.info(f"[{self.name}] Research generated {len(new_questions)} more questions, asking user...")
                    state = {**state, **(await ask_batch_questions(state, agent=self))}
                    
                    # If waiting for answer, save state and return
                    if state.get("waiting_for_answer"):
                        logger.info(f"[{self.name}] Waiting for user to answer research questions")
                        return TaskResult(
                            success=True,
                            output="Research questions asked, waiting for answer",
                            structured_data={"waiting_for_answer": True, "research_loop": research_loop_count}
                        )
                else:
                    logger.info(f"[{self.name}] No new questions from research, proceeding to PRD")
                    break
        
        if research_loop_count >= max_research_loops:
            logger.info(f"[{self.name}] Max research loops ({max_research_loops}) reached, generating PRD anyway")
        
        # Generate PRD
        logger.info(f"[{self.name}] Generating PRD...")
        state = {**state, **(await generate_prd(state, agent=self))}
        
        # Save PRD and wait for user approval before extracting stories
        state = {**state, **(await save_artifacts(state, agent=self))}
        
        return TaskResult(
            success=True,
            output=str(state.get("result", {})),
            structured_data=state.get("result", {})
        )
    
    async def _handle_prd_update_resume(self, task: TaskContext, batch_answers: list, interview_state: dict) -> TaskResult:
        """Handle PRD update flow resume - update existing PRD with user's clarified requirements."""
        logger.info(f"[{self.name}] Resuming prd_update flow after clarification")
        
        # Build combined message from original request + answers
        original_message = interview_state.get("user_message", "")
        questions = interview_state.get("questions", [])
        
        # Combine answers into context
        clarification_context = []
        for i, ans in enumerate(batch_answers):
            q_text = questions[i].get("question_text", f"Câu hỏi {i+1}") if i < len(questions) else f"Câu hỏi {i+1}"
            a_text = ans.get("answer", "") or ", ".join(ans.get("selected_options", []))
            clarification_context.append(f"Q: {q_text}\nA: {a_text}")
        
        combined_message = f"{original_message}\n\nChi tiết bổ sung:\n" + "\n".join(clarification_context)
        
        # Build state and call update_prd
        state = {
            **self._build_base_state(task),
            "user_message": combined_message,
            "existing_prd": interview_state.get("existing_prd") or self._load_existing_prd(),
            "epics": interview_state.get("epics", []),
            "intent": "prd_update",
            "skip_clarity_check": True,  # IMPORTANT: Skip clarity check since we already got clarification
        }
        
        # Now call update_prd (skip clarity check because we have detailed answers)
        state = {**state, **(await update_prd(state, agent=self))}
        
        # Save artifacts
        state = {**state, **(await save_artifacts(state, agent=self))}
        
        return TaskResult(
            success=True,
            output=str(state.get("result", {})),
            structured_data=state.get("result", {})
        )
    
    async def _handle_stories_update_resume(self, task: TaskContext, batch_answers: list, interview_state: dict) -> TaskResult:
        """Handle stories update flow resume - update existing stories with user's clarified requirements."""
        logger.info(f"[{self.name}] Resuming stories_update flow after clarification")
        
        # Build combined message from original request + answers
        original_message = interview_state.get("user_message", "")
        questions = interview_state.get("questions", [])
        
        # Combine answers into context
        clarification_context = []
        for i, ans in enumerate(batch_answers):
            q_text = questions[i].get("question_text", f"Câu hỏi {i+1}") if i < len(questions) else f"Câu hỏi {i+1}"
            a_text = ans.get("answer", "") or ", ".join(ans.get("selected_options", []))
            clarification_context.append(f"Q: {q_text}\nA: {a_text}")
        
        combined_message = f"{original_message}\n\nChi tiết bổ sung:\n" + "\n".join(clarification_context)
        
        # Load epics from state or database
        epics = interview_state.get("epics", [])
        if not epics:
            epics, _, _ = self._load_existing_epics()
        
        # Build state and call update_stories
        state = {
            **self._build_base_state(task),
            "user_message": combined_message,
            "existing_prd": interview_state.get("existing_prd") or self._load_existing_prd(),
            "epics": epics,
            "intent": "stories_update",
            "skip_clarity_check": True,  # IMPORTANT: Skip clarity check since we already got clarification
        }
        
        # Now call update_stories (skip clarity check because we have detailed answers)
        from app.agents.business_analyst.src.nodes import update_stories
        state = {**state, **(await update_stories(state, agent=self))}
        
        # Save artifacts
        state = {**state, **(await save_artifacts(state, agent=self))}
        
        return TaskResult(
            success=True,
            output=str(state.get("result", {})),
            structured_data=state.get("result", {})
        )
    
    async def _handle_sequential_resume(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle sequential mode resume - one answer at a time (legacy)."""
        if not answer:
            logger.error(f"[{self.name}] Empty answer in RESUME task")
            return TaskResult(
                success=False,
                output="",
                error_message="Empty answer"
            )
        
        # Load interview state from database
        interview_state = await self._load_interview_state(task)
        
        if not interview_state:
            logger.warning(f"[{self.name}] No interview state found, treating as new task")
            return await self._handle_new_task(task)
        
        # Load existing PRD from database
        existing_prd = self._load_existing_prd()
        
        # Build state from saved interview state + user answer
        state = {
            **self._build_base_state(task),
            "user_message": answer,
            "collected_info": interview_state.get("collected_info", {}),
            "existing_prd": existing_prd,
            "intent": "interview",
            "questions": interview_state.get("questions", []),
            "current_question_index": interview_state.get("current_question_index", 0),
            "collected_answers": interview_state.get("collected_answers", []),
            "waiting_for_answer": False,
            "all_questions_answered": False,
        }
        
        # Process the answer
        logger.info(f"[{self.name}] Processing answer for question {state['current_question_index'] + 1}")
        state = {**state, **(await process_answer(state, agent=self))}
        
        # Check if more questions or generate PRD
        if state.get("all_questions_answered"):
            # Check clarity before generating PRD
            clarity_result = check_clarity(state)
            is_clear = clarity_result.get("is_clear", False)
            research_loop_count = state.get("research_loop_count", 0)
            
            if not is_clear and research_loop_count < 2:
                missing_categories = clarity_result.get("missing_categories", [])
                logger.info(f"[{self.name}] Missing categories: {missing_categories}, doing research")
                state["missing_categories"] = missing_categories
                state = {**state, **(await analyze_domain(state, agent=self))}
                
                new_questions = state.get("questions", [])
                if new_questions:
                    logger.info(f"[{self.name}] Research generated {len(new_questions)} more questions")
                    state = {**state, **(await ask_batch_questions(state, agent=self))}
                    if state.get("waiting_for_answer"):
                        return TaskResult(
                            success=True,
                            output="Research questions asked, waiting for answer",
                            structured_data={"waiting_for_answer": True}
                        )
            
            logger.info(f"[{self.name}] Generating PRD...")
            state = {**state, **(await generate_prd(state, agent=self))}
            
            # Save PRD and wait for user approval before extracting stories
            state = {**state, **(await save_artifacts(state, agent=self))}
            
            return TaskResult(
                success=True,
                output=str(state.get("result", {})),
                structured_data=state.get("result", {})
            )
        else:
            # Ask next question
            logger.info(f"[{self.name}] Asking next question {state['current_question_index'] + 1}")
            state = {**state, **(await ask_one_question(state, agent=self))}
            
            # Save state for next resume
            await self._save_interview_state(task, state)
            
            return TaskResult(
                success=True,
                output="Question asked, waiting for answer",
                structured_data={"waiting_for_answer": True}
            )
    
    async def _handle_new_task(self, task: TaskContext) -> TaskResult:
        """Handle new task - run full LangGraph."""
        logger.info(f"[{self.name}] Handling NEW task for project_id={self.project_id}, message: {task.content[:100] if task.content else 'empty'}")
        
        # Load shared context (cached, parallel loading) - same as Team Leader
        await self.context.ensure_loaded()
        
        # Note: UPDATE MODE is already checked in handle_task() before calling this method
        
        # Check for file attachments and combine with user message
        user_message = task.content
        # Note: use "or []" because attachments key may exist with None value
        attachments = (task.context.get("attachments") or []) if task.context else []
        pre_collected_info = {}  # Pre-populated from document analysis
        document_is_comprehensive = False
        document_type = ""  # "complete_requirements" | "partial_requirements" | "not_requirements"
        
        if attachments:
            logger.info(f"[{self.name}] Found {len(attachments)} attachment(s) in task")
            doc_texts = []
            all_extracted_text = ""
            
            for att in attachments:
                if att.get("type") == "document" and att.get("extracted_text"):
                    filename = att.get("filename", "document")
                    extracted = att.get("extracted_text", "")
                    doc_texts.append(f"[Tài liệu đính kèm: {filename}]\n{extracted}")
                    all_extracted_text += extracted + "\n\n"
                    logger.info(f"[{self.name}] Included document '{filename}' ({len(extracted)} chars)")
                    logger.info(f"[{self.name}] Document preview (first 300 chars): {extracted[:300]}")
            
            if doc_texts:
                # Combine user message with document content
                user_message = f"{task.content}\n\n---\n\n" + "\n\n---\n\n".join(doc_texts)
                logger.info(f"[{self.name}] Combined message length: {len(user_message)} chars")
                
                # Send acknowledgment message to user
                first_filename = attachments[0].get("filename", "document")
                await self.message_user(
                    "response",
                    f"📄 Đã nhận file '{first_filename}'. Đang phân tích nội dung tài liệu..."
                )
                
                # Show typing indicator while analyzing (response above clears it)
                await self.message_user("thinking", "Đang phân tích tài liệu...")
                
                # Always analyze document (regardless of length)
                doc_analysis = await analyze_document_content(all_extracted_text, agent=self)
                document_type = doc_analysis.get("document_type", "partial_requirements")
                pre_collected_info = doc_analysis.get("collected_info", {})
                document_is_comprehensive = doc_analysis.get("is_comprehensive", False)
                summary = doc_analysis.get("summary", "")
                extracted_items = doc_analysis.get("extracted_items", [])
                missing_info = doc_analysis.get("missing_info", [])
                detected_doc_kind = doc_analysis.get("detected_doc_kind", "")
                
                logger.info(
                    f"[{self.name}] Document analysis result: "
                    f"type={document_type}, "
                    f"comprehensive={document_is_comprehensive}, "
                    f"score={doc_analysis.get('completeness_score', 0):.0%}, "
                    f"collected_info={list(pre_collected_info.keys())}"
                )
                
                # Generate natural feedback message using LLM (with agent personality)
                feedback_msg = await generate_document_feedback(
                    document_type=document_type,
                    detected_doc_kind=detected_doc_kind,
                    summary=summary,
                    extracted_items=extracted_items,
                    missing_info=missing_info,
                    completeness_score=doc_analysis.get("completeness_score", 0),
                    agent=self
                )
                
                # Send feedback to user
                await self.message_user("response", feedback_msg)
                
                # Handle based on document type
                if document_type == "not_requirements":
                    # Return early - don't run interview, wait for user to clarify
                    doc_kind_text = detected_doc_kind if detected_doc_kind else "tài liệu chung"
                    logger.info(f"[{self.name}] Document is not_requirements, waiting for user clarification")
                    return TaskResult(
                        success=True,
                        output=f"Document analyzed as {doc_kind_text}, waiting for user clarification",
                        structured_data={"action": "waiting_clarification", "document_type": document_type}
                    )
                    
                elif document_type == "complete_requirements" and document_is_comprehensive:
                    # Show typing indicator while generating PRD
                    await self.message_user("thinking", "Đang tạo PRD...")
                    
                else:
                    # Show typing indicator while preparing questions
                    await self.message_user("thinking", "Đang chuẩn bị câu hỏi...")
        
        # Add user message to shared memory
        self.context.add_message("user", task.content)  # Save original message to memory
        
        # Load existing PRD from database
        existing_prd = self._load_existing_prd()
        
        # Load existing epics/stories from database (for approval flow)
        existing_epics, existing_stories, existing_approval_message = self._load_existing_epics_and_stories()
        logger.info(f"[{self.name}] Initial state: existing_epics={len(existing_epics)}, existing_stories={len(existing_stories)}")
        
        # Get conversation context - prefer from Team Leader delegation if available
        conversation_context = ""
        if task.context and task.context.get("conversation_history"):
            # Use conversation history passed from Team Leader (more complete context)
            conversation_context = task.context.get("conversation_history", "")
            logger.info(f"[{self.name}] Using conversation history from Team Leader ({len(conversation_context)} chars)")
        else:
            # Fallback to local memory
            conversation_context = self.context.format_memory()
            logger.info(f"[{self.name}] Using local conversation context ({len(conversation_context)} chars)")
        
        langfuse_ctx = None
        
        from app.core.config import settings
        if settings.LANGFUSE_ENABLED:
            try:
                from langfuse import get_client
                langfuse = get_client()
                langfuse_ctx = langfuse.start_as_current_observation(
                    as_type="span",
                    name="business_analyst_graph"
                )
                langfuse_span = langfuse_ctx.__enter__()
                langfuse_span.update_trace(
                    user_id=str(task.user_id) if task.user_id else None,
                    session_id=str(self.project_id),
                    input={"message": task.content[:200] if task.content else ""},
                    tags=["business_analyst", self.role_type],
                    metadata={"agent": self.name, "task_id": str(task.task_id)}
                )

            except Exception as e:
                logger.debug(f"[{self.name}] Langfuse setup: {e}")
        
        # Prepare initial state
        initial_state = {
            **self._build_base_state(task),
            "user_message": user_message,  # Use combined message with attachments
            "has_attachments": bool(attachments),  # Flag for document upload
            "document_type": document_type,  # For routing: partial_requirements -> interview
            "collected_info": pre_collected_info,  # Pre-populated from document analysis
            "existing_prd": existing_prd,
            "conversation_context": conversation_context,  # From Team Leader or local memory
            "intent": "",
            "reasoning": "",
            "questions": [],
            "current_question_index": 0,
            "collected_answers": [],
            "waiting_for_answer": False,
            "all_questions_answered": False,
            "prd_draft": None,
            "prd_final": None,
            "prd_saved": False,
            "change_summary": "",
            "epics": existing_epics,
            "stories": existing_stories,
            "stories_approval_message": existing_approval_message,  # Pre-load from artifact for approve flow
            "stories_saved": False,
            "analysis_text": "",
            "error": None,
            "retry_count": 0,
            "result": {},
            "is_complete": False,
            "langfuse_handler": langfuse_handler,
        }
        
        # Setup graph with checkpointer
        await self.graph_engine.setup()
        
        # Generate thread_id for checkpointing (enables pause/resume)
        task_id = str(task.task_id)
        thread_id = f"{self.agent_id}_{task_id}"
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [langfuse_handler] if langfuse_handler else []
        }
        
        # Track current task for cancel/pause
        current_task = asyncio.current_task()
        if current_task:
            self._running_tasks[task_id] = current_task
        
        # Clear any leftover signals
        self.clear_signal(task_id)
        
        try:
            logger.info(f"[{self.name}] Invoking LangGraph with signal checking...")
            final_state = await self._run_graph_with_signal_check(initial_state, config, task_id)
            
            # Remove from running tasks
            self._running_tasks.pop(task_id, None)
            
            # Close Langfuse span
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "intent": final_state.get("intent"),
                        "waiting_for_answer": final_state.get("waiting_for_answer"),
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            # If waiting for answer, save state for resume
            if final_state.get("waiting_for_answer"):
                await self._save_interview_state(task, final_state)
                return TaskResult(
                    success=True,
                    output="Question asked, waiting for answer",
                    structured_data={"waiting_for_answer": True}
                )
            
            # Extract result
            result_data = final_state.get("result", {})
            action = final_state.get("intent", "completed")
            
            logger.info(f"[{self.name}] Graph completed: action={action}")
            
            # Add response to shared memory (for conversation context)
            response_summary = result_data.get("summary", "") if isinstance(result_data, dict) else str(result_data)[:200]
            if response_summary:
                self.context.add_message("assistant", response_summary)
            
            # Check if we should create a conversation summary
            await self.context.maybe_summarize()
            
            return TaskResult(
                success=True,
                output=str(result_data),
                structured_data=result_data
            )
        
        except asyncio.CancelledError:
            # Task was cancelled (user clicked Cancel or Pause)
            logger.info(f"[{self.name}] Task {task_id} was cancelled/paused (CancelledError)")
            self._running_tasks.pop(task_id, None)
            
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message="Task was cancelled or paused"
            )
        
        except TaskStoppedException as e:
            # Task was stopped via signal
            logger.info(f"[{self.name}] Task {task_id} stopped: {e.message}")
            self._running_tasks.pop(task_id, None)
            self.consume_signal(task_id)
            
            # Notify user
            if e.reason == "pause":
                await self.message_user("response", "⏸️ Đã tạm dừng. Bạn có thể tiếp tục bất cứ lúc nào.")
            elif e.reason == "cancel":
                await self.message_user("response", "🛑 Đã hủy tác vụ.")
            
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message=f"Task {e.reason}ed"
            )
    
    async def _load_interview_state(self, task: TaskContext) -> dict | None:
        """Load interview state from database (via question context).
        
        Supports both:
        - Sequential mode: question_id in context
        - Batch mode: batch_answers with question_ids, or original_context with interview_state
        """
        try:
            question_id = None
            is_batch = task.context.get("is_batch", False) if task.context else False
            
            if task.context:
                logger.info(f"[{self.name}] Task context keys: {list(task.context.keys())}")
                
                # For batch mode, try to get interview_state from original_context first
                if is_batch:
                    original_context = task.context.get("original_context", {})
                    if original_context and original_context.get("interview_state"):
                        logger.info(f"[{self.name}] Found interview_state in original_context (batch mode)")
                        return original_context.get("interview_state")
                    
                    # Otherwise, try first question from batch_answers
                    batch_answers = task.context.get("batch_answers", [])
                    if batch_answers:
                        question_id = batch_answers[0].get("question_id")
                        logger.info(f"[{self.name}] Using first question from batch: {question_id}")
                else:
                    question_id = task.context.get("question_id")
                    logger.info(f"[{self.name}] question_id from context: {question_id}")
            else:
                logger.warning(f"[{self.name}] Task context is None or empty!")
            
            with Session(engine) as session:
                question = None
                
                if question_id:
                    # Direct lookup by question_id from RESUME task context
                    try:
                        question = session.get(AgentQuestion, UUID(question_id))
                        logger.info(f"[{self.name}] Loaded question from DB: {question.id if question else 'NOT FOUND'}")
                    except Exception as uuid_err:
                        logger.error(f"[{self.name}] Failed to parse question_id as UUID: {uuid_err}")
                else:
                    # Fallback: Find the most recently answered question for this project/agent
                    logger.info(f"[{self.name}] No question_id in context, using fallback query")
                    question = session.exec(
                        select(AgentQuestion)
                        .where(AgentQuestion.project_id == self.project_id)
                        .where(AgentQuestion.agent_id == self.agent_id)
                        .where(AgentQuestion.status == QuestionStatus.ANSWERED)
                        .order_by(AgentQuestion.answered_at.desc())
                    ).first()
                    if question:
                        logger.info(f"[{self.name}] Fallback found question: {question.id}")
                
                if question:
                    logger.info(f"[{self.name}] Question task_context: {question.task_context}")
                    if question.task_context:
                        task_context = question.task_context
                        interview_state = task_context.get("interview_state", {})
                        
                        if interview_state:
                            logger.info(f"[{self.name}] Found interview state from question {question.id}, "
                                       f"current_question_index={interview_state.get('current_question_index')}, "
                                       f"questions_count={len(interview_state.get('questions', []))}")
                            return interview_state
                        else:
                            logger.warning(f"[{self.name}] Question {question.id} has task_context but NO interview_state!")
                    else:
                        logger.warning(f"[{self.name}] Question {question.id} has NO task_context!")
                else:
                    logger.warning(f"[{self.name}] No question found in database")
                    
            return None
        except Exception as e:
            logger.error(f"[{self.name}] Failed to load interview state: {e}", exc_info=True)
            return None
    
    async def _save_interview_state(self, task: TaskContext, state: dict) -> None:
        """Save interview state for resume (stored in question's task_context)."""
        try:
            # State is already saved when question is created via ask_clarification_question
            # This method can be used for additional state persistence if needed
            logger.info(f"[{self.name}] Interview state saved (question index: {state.get('current_question_index', 0)})")
        except Exception as e:
            logger.error(f"[{self.name}] Failed to save interview state: {e}")
    
    async def _handle_update_mode(self, task: TaskContext) -> TaskResult:
        """Handle UPDATE MODE - add features to existing PRD.
        
        When user wants to add/update features:
        1. Load existing PRD
        2. Get feature description from context
        3. Generate updated PRD with new features
        4. Extract new stories for the feature
        """
        try:
            # Get feature info from context (set by Team Leader)
            ctx = task.context or {}
            feature_description = ctx.get("feature_to_add") or task.content or ""
            existing_title = ctx.get("existing_prd_title", "project hiện tại")
            
            logger.info(f"[{self.name}] UPDATE MODE: Adding feature to '{existing_title}': {feature_description[:100]}...")
            
            # Load existing PRD
            existing_prd = self._load_existing_prd()
            
            if not existing_prd:
                # No existing PRD - tell user to create one first
                logger.warning(f"[{self.name}] No existing PRD found for update")
                await self.message_user(
                    "response",
                    "Chưa có PRD nào để cập nhật. Bạn cần tạo PRD trước khi thêm feature mới nhé! 📝\n\nHãy mô tả dự án bạn muốn làm để mình tạo PRD."
                )
                return TaskResult(
                    success=True,
                    output="No PRD to update",
                    structured_data={"action": "need_create_prd_first"}
                )
            
            # Send acknowledgment
            await self.message_user(
                "response",
                f"📝 Đang cập nhật PRD \"{existing_title}\" với feature mới: {feature_description[:50]}..."
            )
            await self.message_user("thinking", "Đang cập nhật PRD...")
            
            # Load existing epics/stories
            existing_epics, existing_stories, existing_approval_message = self._load_existing_epics_and_stories()
            
            # Build state for update
            initial_state = {
                **self._build_base_state(task),
                "user_message": feature_description,  # The feature to add
                "collected_info": {},
                "existing_prd": existing_prd,
                "conversation_context": self.context.format_memory(),
                "intent": "prd_update",  # Special intent for update flow
                "questions": [],
                "current_question_index": 0,
                "collected_answers": [],
                "waiting_for_answer": False,
                "all_questions_answered": True,  # Skip interview
                "prd_draft": None,
                "prd_final": None,
                "prd_saved": False,
                "change_summary": "",
                "epics": existing_epics,
                "stories": existing_stories,
                "stories_approval_message": existing_approval_message,
                "stories_saved": False,
                "analysis_text": "",
                "error": None,
                "retry_count": 0,
                "result": {},
                "is_complete": False,
                "is_update_mode": True,  # Flag for update mode
                "feature_to_add": feature_description,
            }
            
            # Update existing PRD with new feature (use update_prd, not generate_prd)
            logger.info(f"[{self.name}] Updating PRD with new feature...")
            initial_state = {**initial_state, **(await update_prd(initial_state, agent=self))}
            
            # Extract new stories
            logger.info(f"[{self.name}] Extracting stories for new feature...")
            initial_state = {**initial_state, **(await extract_stories(initial_state, agent=self))}
            
            # Save artifacts
            initial_state = {**initial_state, **(await save_artifacts(initial_state, agent=self))}
            
            return TaskResult(
                success=True,
                output="PRD updated with new feature",
                structured_data=initial_state.get("result", {})
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error in UPDATE MODE: {e}", exc_info=True)
            await self.message_user(
                "response",
                "Có lỗi xảy ra khi cập nhật PRD. Vui lòng thử lại! 😅"
            )
            return TaskResult(
                success=False,
                output="",
                error_message=str(e)
            )
