"""LangGraph Node Functions for Business Analyst

Uses shared prompt_utils from core (same pattern as Team Leader).
"""

import json
import logging
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, func, select
from sqlalchemy.orm.attributes import flag_modified

from .state import BAState
from .prompts import (
    PROMPTS,
    BA_DEFAULTS,
    parse_intent_response,
    parse_questions_response,
    parse_prd_response,
    parse_prd_update_response,
    parse_stories_response,
)
from app.agents.core.prompt_utils import (
    build_system_prompt as _build_system_prompt,
    build_user_prompt as _build_user_prompt,
)
from app.core.db import engine
from app.models import AgentQuestion, Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService

logger = logging.getLogger(__name__)

# LLM instances (shared, like Team Leader)
# Using same model naming as team_leader (claude-haiku/sonnet without prefix)
_fast_llm = ChatOpenAI(model="gpt-4.1", temperature=0.1, timeout=30)
_default_llm = ChatOpenAI(model="gpt-4.1", temperature=0.7, timeout=90)
_story_llm = ChatOpenAI(model="gpt-4.1", temperature=0.7, timeout=180)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback from state (same pattern as Team Leader)."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _sys_prompt(agent, task: str) -> str:
    """Build system prompt with agent personality (same pattern as Team Leader)."""
    return _build_system_prompt(PROMPTS, task, agent, BA_DEFAULTS)


def _user_prompt(task: str, **kwargs) -> str:
    """Build user prompt for LLM."""
    # Extract user_message from kwargs if present, otherwise use empty string
    user_message = kwargs.pop("user_message", "")
    return _build_user_prompt(PROMPTS, task, user_message, **kwargs)


async def analyze_intent(state: BAState, agent=None) -> dict:
    """Node: Analyze user intent and classify task."""
    logger.info(f"[BA] Analyzing intent: {state['user_message'][:80]}...")
    
    system_prompt = _sys_prompt(agent, "analyze_intent")
    user_prompt = _user_prompt(
        "analyze_intent",
        user_message=state["user_message"],
        has_prd="Yes" if state.get("existing_prd") else "No",
        has_info="Yes" if state.get("collected_info") else "No"
    )
    
    try:
        response = await _fast_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "analyze_intent")
        )
        
        result = parse_intent_response(response.content)
        logger.info(f"[BA] Intent classified: {result['intent']}")
        
        return result
        
    except Exception as e:
        logger.warning(f"[BA] Could not parse intent: {e}")
        return {
            "intent": "interview",
            "reasoning": f"Error parsing intent: {str(e)}"
        }


async def interview_requirements(state: BAState, agent=None) -> dict:
    """Node: Generate clarification questions."""
    logger.info(f"[BA] Generating interview questions...")
    
    system_prompt = _sys_prompt(agent, "interview_requirements")
    user_prompt = _user_prompt(
        "interview_requirements",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False),
        has_prd="Yes" if state.get("existing_prd") else "No"
    )
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "interview_requirements")
        )
        
        questions = parse_questions_response(response.content)
        logger.info(f"[BA] Generated {len(questions)} questions")
        
        return {"questions": questions}
        
    except Exception as e:
        logger.error(f"[BA] Failed to generate questions: {e}")
        return {"questions": [], "error": f"Failed to generate questions: {str(e)}"}


async def ask_one_question(state: BAState, agent=None) -> dict:
    """Node: Send ONE question to user (sequential mode).
    
    This node sends the current question (at current_question_index) and waits.
    When user answers, the task will be resumed and this node checks if more questions.
    """
    logger.info(f"[BA] Asking one question (sequential mode)...")
    
    questions = state.get("questions", [])
    current_index = state.get("current_question_index", 0)
    
    if not questions:
        logger.warning("[BA] No questions to send")
        return {
            "waiting_for_answer": False,
            "all_questions_answered": True
        }
    
    if current_index >= len(questions):
        logger.info("[BA] All questions have been asked")
        return {
            "waiting_for_answer": False,
            "all_questions_answered": True
        }
    
    if not agent:
        logger.error("[BA] No agent available to send question")
        return {"error": "No agent available"}
    
    try:
        # Get current question
        current_question = questions[current_index]
        question_text = current_question["text"]
        question_type = current_question.get("type", "open")
        options = current_question.get("options")
        
        logger.info(f"[BA] Sending question {current_index + 1}/{len(questions)}: {question_text[:50]}...")
        
        # Send single question using ask_clarification_question
        question_id = await agent.ask_clarification_question(
            question=f"Câu hỏi {current_index + 1}/{len(questions)}:\n{question_text}",
            question_type=question_type,
            options=options,
            allow_multiple=current_question.get("allow_multiple", False)
        )
        
        # Save interview state to question's task_context for resume
        with Session(engine) as session:
            question = session.get(AgentQuestion, question_id)
            if question:
                # Update task_context with interview state
                # IMPORTANT: Create new dict to ensure SQLAlchemy detects the change
                existing_context = question.task_context or {}
                new_task_context = {
                    **existing_context,
                    "interview_state": {
                        "questions": questions,
                        "current_question_index": current_index,
                        "collected_answers": state.get("collected_answers", []),
                        "collected_info": state.get("collected_info", {}),
                        "user_message": state.get("user_message", ""),  # Save original request for PRD generation
                    }
                }
                question.task_context = new_task_context
                # Explicitly mark the JSON field as modified so SQLAlchemy persists it
                flag_modified(question, "task_context")
                session.add(question)
                session.commit()
                
                # Verify the save was successful by re-reading from DB
                session.refresh(question)
                saved_state = question.task_context.get("interview_state") if question.task_context else None
                if saved_state:
                    logger.info(f"[BA] Verified interview state saved to question {question_id} "
                               f"(current_index={saved_state.get('current_question_index')}, "
                               f"questions_count={len(saved_state.get('questions', []))})")
                else:
                    logger.error(f"[BA] Interview state NOT saved to question {question_id}! task_context={question.task_context}")
            else:
                logger.error(f"[BA] Failed to find question {question_id} in database to save interview state!")
        
        logger.info(f"[BA] Question {current_index + 1} sent, waiting for answer...")
        
        return {
            "waiting_for_answer": True,
            "all_questions_answered": False,
            "current_question_id": str(question_id)
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to send question: {e}", exc_info=True)
        return {
            "waiting_for_answer": False,
            "error": f"Failed to send question: {str(e)}"
        }


async def ask_batch_questions(state: BAState, agent=None) -> dict:
    """Node: Send ALL questions to user at once (batch mode).
    
    This node sends all questions in a single batch.
    User answers all questions, then submits all at once.
    """
    logger.info(f"[BA] Asking all questions at once (batch mode)...")
    
    questions = state.get("questions", [])
    
    if not questions:
        logger.warning("[BA] No questions to send")
        return {
            "waiting_for_answer": False,
            "all_questions_answered": True
        }
    
    if not agent:
        logger.error("[BA] No agent available to send questions")
        return {"error": "No agent available"}
    
    try:
        # Format questions for batch API
        batch_questions = [
            {
                "question_text": q["text"],
                "question_type": q.get("type", "open"),
                "options": q.get("options"),
                "allow_multiple": q.get("allow_multiple", False),
                "context": q.get("context"),
            }
            for q in questions
        ]
        
        logger.info(f"[BA] Sending {len(batch_questions)} questions in batch...")
        
        # Send all questions at once
        question_ids = await agent.ask_multiple_clarification_questions(batch_questions)
        
        # Save interview state to the FIRST question's task_context for resume
        batch_id = None
        with Session(engine) as session:
            first_question = session.get(AgentQuestion, question_ids[0])
            if first_question and first_question.task_context:
                batch_id = first_question.task_context.get("batch_id")
                
                # Update task_context with interview state
                existing_context = first_question.task_context or {}
                new_task_context = {
                    **existing_context,
                    "interview_state": {
                        "questions": questions,
                        "question_ids": [str(qid) for qid in question_ids],
                        "collected_info": state.get("collected_info", {}),
                        "user_message": state.get("user_message", ""),  # Save original request for PRD generation
                    }
                }
                first_question.task_context = new_task_context
                flag_modified(first_question, "task_context")
                session.add(first_question)
                session.commit()
                
                logger.info(f"[BA] Saved interview state to batch (batch_id={batch_id}, questions={len(questions)})")
        
        logger.info(f"[BA] All {len(questions)} questions sent in batch, waiting for answers...")
        
        return {
            "waiting_for_answer": True,
            "all_questions_answered": False,
            "batch_id": batch_id,
            "question_ids": [str(qid) for qid in question_ids]
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to send batch questions: {e}", exc_info=True)
        return {
            "waiting_for_answer": False,
            "error": f"Failed to send questions: {str(e)}"
        }


async def process_batch_answers(state: BAState, agent=None) -> dict:
    """Node: Process ALL user answers from batch mode.
    
    This node is called when user answers all questions at once (via RESUME task with is_batch=True).
    """
    logger.info(f"[BA] Processing batch answers...")
    
    questions = state.get("questions", [])
    batch_answers = state.get("batch_answers", [])
    
    if not batch_answers:
        logger.warning("[BA] No batch answers received")
        return {
            "error": "No answers received",
            "all_questions_answered": False
        }
    
    # Build collected_answers from batch_answers
    collected_answers = []
    for ans in batch_answers:
        # Find matching question by index or question_id
        q_idx = ans.get("question_index", len(collected_answers))
        if q_idx < len(questions):
            answer_text = ans.get("answer", "")
            selected_options = ans.get("selected_options", [])
            
            # If multichoice, join selected options
            if selected_options:
                answer_text = ", ".join(selected_options)
            
            collected_answers.append({
                "question_index": q_idx,
                "question_text": questions[q_idx]["text"],
                "answer": answer_text,
                "selected_options": selected_options
            })
    
    logger.info(f"[BA] Processed {len(collected_answers)} answers from batch")
    
    # Build collected_info - ACCUMULATE answers from previous rounds
    collected_info = state.get("collected_info", {})
    existing_answers = collected_info.get("interview_answers", [])
    all_answers = existing_answers + collected_answers
    collected_info["interview_answers"] = all_answers
    collected_info["interview_completed"] = True
    
    logger.info(f"[BA] Total accumulated answers: {len(all_answers)} (new: {len(collected_answers)}, previous: {len(existing_answers)})")
    
    return {
        "collected_answers": all_answers,  # Return ALL answers, not just new ones
        "collected_info": collected_info,
        "waiting_for_answer": False,
        "all_questions_answered": True
    }


async def process_answer(state: BAState, agent=None) -> dict:
    """Node: Process user's answer and prepare for next question or continue.
    
    This node is called when user answers a question (via RESUME task).
    It records the answer and increments the question index.
    """
    logger.info(f"[BA] Processing user answer...")
    
    questions = state.get("questions", [])
    current_index = state.get("current_question_index", 0)
    collected_answers = state.get("collected_answers", [])
    user_message = state.get("user_message", "")
    
    # Record the answer
    if current_index < len(questions):
        answer_record = {
            "question_index": current_index,
            "question_text": questions[current_index]["text"],
            "answer": user_message
        }
        collected_answers = collected_answers + [answer_record]
        logger.info(f"[BA] Recorded answer for question {current_index + 1}: {user_message[:50]}...")
    
    # Move to next question
    next_index = current_index + 1
    all_answered = next_index >= len(questions)
    
    if all_answered:
        logger.info(f"[BA] All {len(questions)} questions answered!")
        # Build collected_info from answers
        collected_info = state.get("collected_info", {})
        collected_info["interview_answers"] = collected_answers
        collected_info["interview_completed"] = True
        
        return {
            "current_question_index": next_index,
            "collected_answers": collected_answers,
            "collected_info": collected_info,
            "waiting_for_answer": False,
            "all_questions_answered": True
        }
    else:
        logger.info(f"[BA] Moving to question {next_index + 1}/{len(questions)}")
        return {
            "current_question_index": next_index,
            "collected_answers": collected_answers,
            "waiting_for_answer": False,
            "all_questions_answered": False
        }


async def generate_prd(state: BAState, agent=None) -> dict:
    """Node: Generate PRD document."""
    logger.info(f"[BA] Generating PRD...")
    
    system_prompt = _sys_prompt(agent, "generate_prd")
    user_prompt = _user_prompt(
        "generate_prd",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False)
    )
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "generate_prd")
        )
        
        prd = parse_prd_response(response.content)
        logger.info(f"[BA] PRD generated: {prd.get('project_name', 'Untitled')}")
        
        return {"prd_draft": prd}
        
    except Exception as e:
        logger.error(f"[BA] Failed to generate PRD: {e}")
        return {
            "prd_draft": {
                "project_name": "Generated PRD",
                "overview": state["user_message"][:200],
                "error": str(e)
            },
            "error": f"Could not generate PRD: {str(e)}"
        }


async def update_prd(state: BAState, agent=None) -> dict:
    """Node: Update existing PRD."""
    logger.info(f"[BA] Updating existing PRD...")
    
    existing_prd = state.get("existing_prd", {})
    
    if not existing_prd:
        logger.warning("[BA] No existing PRD to update, creating new one")
        return await generate_prd(state, agent)
    
    system_prompt = _sys_prompt(agent, "update_prd")
    user_prompt = _user_prompt(
        "update_prd",
        existing_prd=json.dumps(existing_prd, ensure_ascii=False, indent=2),
        user_message=state["user_message"]
    )
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "update_prd")
        )
        
        result = parse_prd_update_response(response.content)
        logger.info(f"[BA] PRD updated: {result.get('change_summary', 'Changes applied')[:100]}")
        
        if result["updated_prd"]:
            return {
                "prd_draft": result["updated_prd"],
                "change_summary": result["change_summary"]
            }
        else:
            return {
                "error": "Failed to parse updated PRD",
                "prd_draft": existing_prd
            }
        
    except Exception as e:
        logger.error(f"[BA] Failed to update PRD: {e}")
        return {
            "error": f"Failed to update PRD: {str(e)}",
            "prd_draft": existing_prd
        }


async def extract_stories(state: BAState, agent=None) -> dict:
    """Node: Extract epics with INVEST-compliant user stories from PRD."""
    logger.info(f"[BA] Extracting epics and user stories...")
    
    prd = state.get("prd_draft") or state.get("existing_prd", {})
    
    if not prd:
        logger.error("[BA] No PRD available to extract stories from")
        return {
            "epics": [],
            "stories": [],
            "error": "No PRD available. Please create a PRD first."
        }
    
    system_prompt = _sys_prompt(agent, "extract_stories")
    user_prompt = _user_prompt(
        "extract_stories",
        prd=json.dumps(prd, ensure_ascii=False, indent=2)
    )
    
    try:
        # Use _story_llm with longer timeout for complex story extraction
        response = await _story_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "extract_stories")
        )
        
        # Debug: log raw response length
        logger.info(f"[BA] LLM response length: {len(response.content)} chars")
        logger.debug(f"[BA] LLM response preview: {response.content[:500]}...")
        
        result = parse_stories_response(response.content)
        epics = result.get("epics", [])
        
        # Debug: log parsed result
        logger.info(f"[BA] Parsed epics count: {len(epics)}")
        if not epics:
            logger.warning(f"[BA] No epics parsed! Response preview: {response.content[:1000]}")
        
        # Flatten stories for backward compatibility
        all_stories = []
        for epic in epics:
            stories_in_epic = epic.get("stories", [])
            epic_title = epic.get("title", epic.get("name", "Unknown"))
            logger.info(f"[BA] Epic '{epic_title}' has {len(stories_in_epic)} stories")
            for story in stories_in_epic:
                story["epic_id"] = epic.get("id")
                story["epic_title"] = epic_title
                # Log story details including priority and story_point
                logger.info(f"[BA] Extracted story: '{story.get('title', '')[:50]}' - priority={story.get('priority')}, story_point={story.get('story_point')}")
                logger.info(f"[BA] Story keys from LLM: {list(story.keys())}")
                all_stories.append(story)
        
        total_epics = len(epics)
        total_stories = len(all_stories)
        logger.info(f"[BA] Extracted {total_epics} epics with {total_stories} user stories")
        
        return {
            "epics": epics,
            "stories": all_stories
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to extract stories: {e}")
        return {
            "epics": [],
            "stories": [],
            "error": f"Failed to extract stories: {str(e)}"
        }


async def update_stories(state: BAState, agent=None) -> dict:
    """Node: Update existing Epics and Stories based on user feedback."""
    logger.info(f"[BA] Updating stories based on user feedback...")
    
    epics = state.get("epics", [])
    if not epics:
        return {"error": "No existing stories to update"}
    
    # Get conversation context for memory
    conversation_context = state.get("conversation_context", "")
    if conversation_context:
        logger.info(f"[BA] Using conversation context: {len(conversation_context)} chars")
    
    system_prompt = _sys_prompt(agent, "update_stories")
    user_prompt = _user_prompt(
        "update_stories",
        epics=json.dumps(epics, ensure_ascii=False, indent=2),
        user_message=state["user_message"],
        conversation_context=conversation_context
    )
    
    try:
        response = await _story_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "update_stories")
        )
        
        result = parse_stories_response(response.content)
        updated_epics = result.get("epics", [])
        change_summary = result.get("change_summary", "Đã cập nhật stories")
        
        # Flatten stories for backward compatibility (use get, NOT pop - to keep stories in epics)
        all_stories = []
        for epic in updated_epics:
            stories_in_epic = epic.get("stories", [])  # IMPORTANT: use get() not pop() to keep stories in epic
            epic_title = epic.get("title", epic.get("name", "Unknown"))
            for story in stories_in_epic:
                story["epic_id"] = epic.get("id")
                story["epic_title"] = epic_title
                all_stories.append(story)
        
        logger.info(f"[BA] Updated {len(updated_epics)} epics with {len(all_stories)} stories")
        
        return {
            "epics": updated_epics,
            "stories": all_stories,
            "change_summary": change_summary
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to update stories: {e}")
        return {"error": f"Failed to update stories: {str(e)}"}


async def approve_stories(state: BAState, agent=None) -> dict:
    """Node: Approve stories and save them to database."""
    logger.info(f"[BA] Approving stories and saving to database...")
    
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    if not epics_data and not stories_data:
        return {"error": "No stories to approve"}
    
    if not agent:
        return {"error": "No agent context for saving to database"}
    
    try:
        created_epics = []
        created_stories = []
        epic_id_map = {}  # Map string ID (EPIC-001) to UUID
        
        with Session(engine) as session:
            # 1. Create Epics first
            for epic_data in epics_data:
                epic = Epic(
                    title=epic_data.get("title", epic_data.get("name", "Unknown Epic")),
                    description=epic_data.get("description"),
                    domain=epic_data.get("domain"),
                    project_id=agent.project_id,
                    epic_status=EpicStatus.PLANNED
                )
                session.add(epic)
                session.flush()  # Get the UUID
                
                # Map string ID to UUID
                string_id = epic_data.get("id", "")
                epic_id_map[string_id] = epic.id
                created_epics.append({
                    "id": str(epic.id),
                    "title": epic.title,
                    "domain": epic.domain
                })
                logger.info(f"[BA] Created Epic: {epic.title} (id={epic.id})")
            
            # 2. Create Stories linked to their Epics
            # Get current max rank for TODO stories
            max_rank_result = session.exec(
                select(func.max(Story.rank)).where(
                    Story.project_id == agent.project_id,
                    Story.status == StoryStatus.TODO
                )
            ).one()
            current_rank = (max_rank_result or 0)
            
            for story_data in stories_data:
                # Get the epic UUID from the string ID
                epic_string_id = story_data.get("epic_id", "")
                epic_uuid = epic_id_map.get(epic_string_id)
                
                # Parse acceptance criteria
                acceptance_criteria = story_data.get("acceptance_criteria", [])
                if isinstance(acceptance_criteria, list):
                    acceptance_criteria = "\n".join(f"- {ac}" for ac in acceptance_criteria)
                
                # Get requirements list (keep as list for JSON storage)
                requirements = story_data.get("requirements", [])
                
                # Auto-increment rank for ordering
                current_rank += 1
                
                # Get priority and story_point from LLM
                priority = story_data.get("priority")
                story_point = story_data.get("story_point")
                logger.info(f"[BA] Creating story: '{story_data.get('title', '')[:50]}' - priority={priority}, story_point={story_point}, epic_id={epic_string_id}")
                logger.info(f"[BA] Story data keys: {list(story_data.keys())}")
                
                story = Story(
                    title=story_data.get("title", "Unknown Story"),
                    description=story_data.get("description"),
                    acceptance_criteria=acceptance_criteria,
                    requirements=requirements,
                    project_id=agent.project_id,
                    epic_id=epic_uuid,
                    status=StoryStatus.TODO,
                    type=StoryType.USER_STORY,
                    priority=priority,
                    story_point=story_point,
                    rank=current_rank,
                )
                session.add(story)
                session.flush()
                
                created_stories.append({
                    "id": str(story.id),
                    "title": story.title,
                    "epic_id": str(epic_uuid) if epic_uuid else None
                })
                logger.info(f"[BA] Created Story: {story.title} (id={story.id})")
            
            session.commit()
        
        logger.info(f"[BA] Saved {len(created_epics)} epics and {len(created_stories)} stories to database")
        
        return {
            "stories_approved": True,
            "created_epics": created_epics,
            "created_stories": created_stories,
            "approval_message": f"Đã phê duyệt và thêm {len(created_epics)} Epics, {len(created_stories)} Stories vào backlog."
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to save stories to database: {e}", exc_info=True)
        return {"error": f"Failed to save stories: {str(e)}"}


# Categories for clarity check
REQUIRED_CATEGORIES = {
    "target_users": ["khách hàng", "người dùng", "đối tượng", "ai sẽ dùng", "ai dùng"],
    "main_features": ["tính năng", "chức năng", "website cần có", "cần có gì"],
    "risks": ["lo ngại", "thách thức", "rủi ro", "khó khăn", "lo lắng"],
}

OPTIONAL_CATEGORIES = {
    "business_model": ["kiếm tiền", "thu nhập", "doanh thu", "mô hình"],
    "priorities": ["ưu tiên", "quan trọng nhất", "quan trọng"],
    "details": ["thanh toán", "giao hàng", "chi tiết"],
}


def check_clarity(state: BAState) -> dict:
    """Check if collected info covers required categories.
    
    Returns:
        dict with is_clear, covered_categories, missing_categories
    """
    answers = state.get("collected_info", {}).get("interview_answers", [])
    
    covered = {cat: False for cat in REQUIRED_CATEGORIES}
    
    for answer in answers:
        question_text = answer.get("question_text", "").lower()
        answer_text = answer.get("answer", "")
        
        # Skip empty answers
        if not answer_text or len(answer_text.strip()) < 5:
            continue
        
        for category, keywords in REQUIRED_CATEGORIES.items():
            if any(kw in question_text for kw in keywords):
                covered[category] = True
    
    missing = [cat for cat, is_covered in covered.items() if not is_covered]
    is_clear = len(missing) == 0
    
    logger.info(f"[BA] Clarity check: covered={[c for c, v in covered.items() if v]}, missing={missing}")
    
    return {
        "is_clear": is_clear,
        "covered_categories": [c for c, v in covered.items() if v],
        "missing_categories": missing
    }


async def analyze_domain(state: BAState, agent=None) -> dict:
    """Node: Web search + generate questions about missing categories.
    
    This node:
    1. Does web search based on user's project to gather domain insights
    2. Generates additional questions about missing categories
    3. Returns questions to loop back to ask_batch_questions
    """
    logger.info(f"[BA] Domain analysis with web search...")
    
    loop_count = state.get("research_loop_count", 0)
    missing_categories = state.get("missing_categories", [])
    collected_info = state.get("collected_info", {})
    user_message = state.get("user_message", "")
    
    # Increment loop count
    new_loop_count = loop_count + 1
    logger.info(f"[BA] Research loop {new_loop_count}/2, missing: {missing_categories}")
    
    # 1. Web search for domain insights
    domain_research = {}
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        
        # Build search query from user message and collected info
        search_query = f"{user_message} website features best practices 2024"
        
        tavily = TavilySearchResults(max_results=3)
        search_results = await tavily.ainvoke({"query": search_query})
        
        if search_results:
            domain_research = {
                "query": search_query,
                "results": search_results[:3] if isinstance(search_results, list) else search_results,
            }
            logger.info(f"[BA] Web search completed: {len(search_results)} results")
    except ImportError:
        logger.warning("[BA] Tavily not installed, skipping web search")
    except Exception as e:
        logger.warning(f"[BA] Web search failed: {e}")
    
    # 2. Generate additional questions about missing categories
    category_prompts = {
        "target_users": "người dùng mục tiêu, đối tượng khách hàng",
        "main_features": "tính năng chính cần có",
        "risks": "rủi ro, thách thức, lo ngại khi xây dựng",
    }
    
    missing_info = ", ".join([category_prompts.get(cat, cat) for cat in missing_categories])
    
    system_prompt = _sys_prompt(agent, "interview_requirements")
    user_prompt = f"""Dựa trên cuộc trò chuyện trước, user muốn: "{user_message}"

Thông tin đã thu thập: {json.dumps(collected_info, ensure_ascii=False)}

Kết quả tìm hiểu thêm từ web: {json.dumps(domain_research, ensure_ascii=False)[:1500]}

THIẾU THÔNG TIN VỀ: {missing_info}

Hãy tạo 2-3 câu hỏi BỔ SUNG để làm rõ những thông tin còn thiếu.
Dựa vào kết quả research, đề xuất các options phù hợp với xu hướng hiện tại.

Ví dụ: Nếu research thấy nhiều website bán sách có ebook/audiobook, 
hãy hỏi: "Ngoài sách giấy, bạn có muốn bán thêm?" với options ["Ebook", "Audiobook", "Cả hai", "Không cần"]

Return JSON format:
```json
{{
  "questions": [
    {{
      "text": "Câu hỏi tiếng Việt?",
      "type": "multichoice",
      "options": ["Option 1", "Option 2", "Khác"],
      "allow_multiple": true
    }}
  ]
}}
```"""
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "domain_research")
        )
        
        questions = parse_questions_response(response.content)
        logger.info(f"[BA] Generated {len(questions)} additional questions from research")
        
        return {
            "questions": questions,
            "research_loop_count": new_loop_count,
            "research_done": True,
            "domain_research": domain_research,
            "analysis_text": f"Researched: {missing_info}",
        }
        
    except Exception as e:
        logger.error(f"[BA] Domain analysis failed: {e}")
        return {
            "research_loop_count": new_loop_count,
            "research_done": True,
            "error": str(e)
        }


async def save_artifacts(state: BAState, agent=None) -> dict:
    """Node: Save PRD/stories to database and file system."""
    logger.info(f"[BA] Saving artifacts...")
    
    result = {
        "action_taken": state.get("intent", "unknown"),
        "summary": "",
        "next_steps": [],
        "prd_artifact_id": None
    }
    
    project_files = agent.project_files if agent else None
    
    # Save PRD if exists
    if state.get("prd_draft") and agent:
        try:
            prd_data = state["prd_draft"]
            project_name = prd_data.get("project_name", "Project")
            
            # Save to Artifact table
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.create_artifact(
                    project_id=agent.project_id,
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    artifact_type=ArtifactType.PRD,
                    title=project_name,
                    content=prd_data,
                    description=f"PRD for {project_name}",
                    save_to_file=False  # We save our own markdown
                )
                result["prd_artifact_id"] = str(artifact.id)
            
            # Also save markdown for human reading
            if project_files:
                await project_files.save_prd(prd_data)
            
            result["prd_saved"] = True
            result["summary"] = f"PRD '{project_name}' saved successfully"
            result["next_steps"].extend([
                "Review PRD document",
                "Approve to create user stories",
                "Or request edits"
            ])
            
            # Send message with View button (different text for create vs update)
            is_update = bool(state.get("change_summary"))
            if is_update:
                message_content = f"Mình đã cập nhật PRD theo yêu cầu của bạn rồi nhé! 📝 Bạn xem lại và cho mình biết còn gì cần chỉnh sửa không"
            else:
                message_content = f"Tuyệt vời! 🎉 Mình đã hoàn thành PRD cho dự án **{project_name}** rồi! Bạn xem qua và phê duyệt để mình tạo user stories nhé~"
            
            if agent:
                await agent.message_user(
                    event_type="response",
                    content=message_content,
                    details={
                        "message_type": "prd_created",
                        "file_path": "docs/prd.md",
                        "title": project_name,
                        "artifact_id": result["prd_artifact_id"]
                    }
                )
            
            logger.info(f"[BA] PRD saved: {project_name} (artifact_id={result['prd_artifact_id']}")
            
        except Exception as e:
            logger.error(f"[BA] Failed to save PRD: {e}", exc_info=True)
            result["error"] = f"Failed to save PRD: {str(e)}"
    
    # Save epics and stories if exist (only for extract_stories/update_stories, not approve or prd_update)
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    # Check if stories were approved (either by stories_approved flag or by presence of created_epics)
    is_stories_approved = state.get("stories_approved", False) or bool(state.get("created_epics"))
    # Only process stories for story-related intents (not prd_create, prd_update, etc.)
    intent = state.get("intent", "")
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories"]
    
    logger.info(f"[BA] save_artifacts: epics_count={len(epics_data)}, stories_count={len(stories_data)}, is_approved={is_stories_approved}, intent={intent}")
    
    # Only save markdown and send stories_created message for extract_stories/update_stories (not approve or prd_update)
    if (epics_data or stories_data) and project_files and not is_stories_approved and is_story_intent:
        try:
            # Save with epic structure to markdown
            await project_files.save_user_stories(epics_data, stories_data)
            result["stories_saved"] = True
            
            epics_count = len(epics_data)
            stories_count = len(stories_data)
            
            # Also save to Artifact table for later retrieval (for approval flow)
            if agent:
                try:
                    logger.info(f"[BA] Saving stories artifact for project_id={agent.project_id}")
                    with Session(engine) as session:
                        service = ArtifactService(session)
                        # Store epics with their stories inside
                        artifact_content = {
                            "epics": epics_data,
                            "stories": stories_data,
                            "epics_count": epics_count,
                            "stories_count": stories_count
                        }
                        # Log first story to verify priority/story_point
                        if stories_data:
                            first_story = stories_data[0]
                            logger.info(f"[BA] Saving artifact - first story keys: {list(first_story.keys())}")
                            logger.info(f"[BA] Saving artifact - first story priority={first_story.get('priority')}, story_point={first_story.get('story_point')}")
                        artifact = service.create_artifact(
                            project_id=agent.project_id,
                            agent_id=agent.agent_id,
                            agent_name=agent.name,
                            artifact_type=ArtifactType.USER_STORIES,
                            title="User Stories",
                            content=artifact_content,
                            description=f"{epics_count} epics with {stories_count} stories",
                            save_to_file=False
                        )
                        result["stories_artifact_id"] = str(artifact.id)
                        logger.info(f"[BA] Saved stories artifact: {artifact.id} for project {agent.project_id}")
                except Exception as artifact_err:
                    logger.error(f"[BA] Failed to save stories artifact: {artifact_err}", exc_info=True)
            
            result["summary"] = f"Extracted {epics_count} epics with {stories_count} INVEST-compliant stories"
            result["next_steps"].extend([
                "Review epics and prioritize stories",
                "Approve to add to backlog"
            ])
            
            # Send success message with View button (pending approval)
            if agent:
                await agent.message_user(
                    event_type="response",
                    content=f"Xong rồi! 🚀 Mình đã tạo **{stories_count} User Stories** từ PRD. Bạn review và phê duyệt để đưa vào backlog nhé~",
                    details={
                        "message_type": "stories_created",
                        "file_path": "docs/user-stories.md",
                        "epics_count": epics_count,
                        "stories_count": stories_count,
                        "status": "pending"  # Important: pending status
                    }
                )
            
            logger.info(f"[BA] Saved {epics_count} epics with {stories_count} user stories (pending approval)")
            
        except Exception as e:
            logger.error(f"[BA] Failed to save stories: {e}", exc_info=True)
            result["error"] = f"Failed to save stories: {str(e)}"
    
    # Handle case where story extraction failed (no stories returned)
    elif is_story_intent and not epics_data and not stories_data and agent:
        error_msg = state.get("error", "Không thể tạo stories từ PRD.")
        logger.warning(f"[BA] Story extraction failed: {error_msg}")
        result["error"] = error_msg
        await agent.message_user(
            event_type="response",
            content=f"Hmm, mình gặp chút vấn đề khi tạo stories nè 😅 Bạn thử kiểm tra lại PRD hoặc nhờ mình thử lại nhé!",
            details={
                "message_type": "error",
                "error": error_msg
            }
        )
    
    # Interview questions sent
    if state.get("questions_sent"):
        questions_count = len(state.get("questions", []))
        result["summary"] = f"Sent {questions_count} clarification questions to user"
        result["next_steps"].append("Wait for user answers to continue")
    
    # Domain analysis
    if state.get("analysis_text") and not state.get("error"):
        result["summary"] = "Domain analysis completed"
        result["analysis"] = state["analysis_text"]
        result["next_steps"].append("Review analysis insights")
        
        # Send analysis to user
        if agent:
            await agent.message_user(
                event_type="response",
                content=f"Mình đã phân tích xong domain rồi! 📊\n\n{state['analysis_text'][:2000]}",
                details={"analysis": state["analysis_text"]}
            )
    
    # PRD update - show updated PRD card (same as create, no extra text message)
    if state.get("change_summary"):
        result["change_summary"] = state["change_summary"]
        # Card is already shown in the PRD save section above
    
    # Stories approved - only save to DB, notify Kanban to refresh (no card)
    stories_approved_flag = state.get("stories_approved", False)
    created_epics_list = state.get("created_epics", [])
    logger.info(f"[BA] Checking stories_approved: flag={stories_approved_flag}, created_epics={len(created_epics_list)}")
    
    if stories_approved_flag or created_epics_list:
        approval_message = state.get("approval_message", "Epics & Stories đã được phê duyệt")
        
        result["summary"] = approval_message
        result["stories_approved"] = True
        result["created_epics"] = created_epics_list
        result["created_stories"] = state.get("created_stories", [])
        
        # Send simple notification to trigger Kanban refresh (no card displayed)
        if agent:
            logger.info(f"[BA] Sending stories_approved message to frontend")
            stories_approved = len(state.get("created_stories", []))
            await agent.message_user(
                event_type="response",
                content=f"Tuyệt vời! 🎊 Đã thêm **{stories_approved} User Stories** vào backlog rồi! Bạn có thể xem trên Kanban board và bắt đầu implement được luôn nha~",
                details={
                    "message_type": "stories_approved"  # Frontend will refresh Kanban, no card
                }
            )
    
    logger.info(f"[BA] Artifacts saved: {result['summary']}")
    
    return {
        "result": result,
        "is_complete": True
    }
