"""Business Analyst Agent - LangGraph-based Implementation."""

import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.models import Agent as AgentModel, Project, AgentQuestion, QuestionStatus, ArtifactType
from app.utils.project_files import ProjectFiles
from app.kafka.event_schemas import AgentTaskType
from app.core.db import engine
from app.services.artifact_service import ArtifactService
from app.agents.business_analyst.src import BusinessAnalystGraph
from app.agents.business_analyst.src.nodes import (
    process_answer, ask_one_question, 
    process_batch_answers,
    generate_prd, extract_stories, save_artifacts,
    check_clarity, analyze_domain, ask_batch_questions,
    analyze_document_content,
)

logger = logging.getLogger(__name__)


class BusinessAnalyst(BaseAgent):
    """Business Analyst using LangGraph for workflow management.
    
    Langfuse tracing is handled by BaseAgent.get_langfuse_callback().
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Business Analyst LangGraph")
        
        # Shared project context (memory + preferences) - same as Team Leader
        self.context = ProjectContext.get(self.project_id)
        
        # Initialize project files
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
        
        logger.info(f"[{self.name}] LangGraph initialized successfully")
    
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
    
    def _load_existing_epics_and_stories(self) -> tuple[list, list]:
        """Load existing epics and stories from Artifact table (for approval flow).
        
        Returns:
            Tuple of (epics_list, stories_list)
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
                    logger.info(f"[{self.name}] Loaded existing epics/stories from artifact {artifact.id}: {len(epics)} epics, {len(stories)} stories")
                    return epics, stories
                else:
                    logger.info(f"[{self.name}] No USER_STORIES artifact found for project {self.project_id}")
                return [], []
        except Exception as e:
            logger.warning(f"[{self.name}] Error loading epics/stories: {e}", exc_info=True)
            return [], []

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph.
        
        Note: Langfuse tracing is automatically handled by BaseAgent.
        """
        # Check if this is a resume task (user answered a question)
        is_resume = task.task_type == AgentTaskType.RESUME_WITH_ANSWER
        
        # For RESUME tasks, answer is in context, not content
        if is_resume:
            answer = task.context.get("answer", "") if task.context else ""
            logger.info(f"[{self.name}] Processing RESUME task with answer: {answer[:50] if answer else 'empty'}")
            return await self._handle_resume_task(task, answer)
        
        logger.info(f"[{self.name}] Processing task with LangGraph: {task.content[:50] if task.content else 'empty'}")
        
        try:
            # Validate user message (only for non-resume tasks)
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
        """Handle batch mode resume - all answers at once."""
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
        logger.info(f"[{self.name}] Processing {len(batch_answers)} batch answers")
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
        
        # Check for file attachments and combine with user message
        user_message = task.content
        attachments = task.context.get("attachments", []) if task.context else []
        pre_collected_info = {}  # Pre-populated from document analysis
        document_is_comprehensive = False
        
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
            
            if doc_texts:
                # Combine user message with document content
                user_message = f"{task.content}\n\n---\n\n" + "\n\n---\n\n".join(doc_texts)
                logger.info(f"[{self.name}] Combined message length: {len(user_message)} chars")
                
                # Send acknowledgment message to user
                first_filename = attachments[0].get("filename", "document")
                await self.message_user(
                    "response",
                    f"📄 Đã nhận file **{first_filename}**. Đang phân tích nội dung tài liệu..."
                )
                
                # Analyze document to extract requirements info
                if len(all_extracted_text) > 500:  # Only analyze if document has substantial content
                    doc_analysis = await analyze_document_content(all_extracted_text, agent=self)
                    pre_collected_info = doc_analysis.get("collected_info", {})
                    document_is_comprehensive = doc_analysis.get("is_comprehensive", False)
                    
                    logger.info(
                        f"[{self.name}] Document analysis result: "
                        f"comprehensive={document_is_comprehensive}, "
                        f"score={doc_analysis.get('completeness_score', 0):.0%}, "
                        f"collected_info={list(pre_collected_info.keys())}"
                    )
                    
                    # Notify user about analysis result
                    if document_is_comprehensive:
                        await self.message_user(
                            "response",
                            f"✅ Tài liệu đầy đủ thông tin! Mình sẽ tạo PRD trực tiếp từ nội dung này."
                        )
                    else:
                        missing = doc_analysis.get("missing_info", [])
                        if missing:
                            await self.message_user(
                                "response",
                                f"📝 Đã trích xuất một số thông tin từ tài liệu. Mình cần hỏi thêm vài câu để làm rõ."
                            )
        
        # Add user message to shared memory
        self.context.add_message("user", task.content)  # Save original message to memory
        
        # Load existing PRD from database
        existing_prd = self._load_existing_prd()
        
        # Load existing epics/stories from database (for approval flow)
        existing_epics, existing_stories = self._load_existing_epics_and_stories()
        logger.info(f"[{self.name}] Initial state: existing_epics={len(existing_epics)}, existing_stories={len(existing_stories)}")
        
        # Setup Langfuse tracing (1 trace for entire graph - same as Team Leader)
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        try:
            langfuse = get_client()
            # Create parent span for entire graph execution
            langfuse_ctx = langfuse.start_as_current_observation(
                as_type="span",
                name="business_analyst_graph"
            )
            # Enter context and get span object
            langfuse_span = langfuse_ctx.__enter__()
            # Update trace with metadata
            langfuse_span.update_trace(
                user_id=str(task.user_id) if task.user_id else None,
                session_id=str(self.project_id),
                input={"message": task.content[:200] if task.content else ""},
                tags=["business_analyst", self.role_type],
                metadata={"agent": self.name, "task_id": str(task.task_id)}
            )
            # Handler inherits trace context automatically
            langfuse_handler = CallbackHandler()
        except Exception as e:
            logger.debug(f"[{self.name}] Langfuse setup: {e}")
        
        # Prepare initial state
        initial_state = {
            **self._build_base_state(task),
            "user_message": user_message,  # Use combined message with attachments
            "has_attachments": bool(attachments),  # Flag for document upload
            "collected_info": pre_collected_info,  # Pre-populated from document analysis
            "existing_prd": existing_prd,
            "conversation_context": self.context.format_memory(),
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
            "stories_saved": False,
            "analysis_text": "",
            "error": None,
            "retry_count": 0,
            "result": {},
            "is_complete": False,
            "langfuse_handler": langfuse_handler,
        }
        
        logger.info(f"[{self.name}] Invoking LangGraph...")
        final_state = await self.graph_engine.execute(initial_state)
        
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
