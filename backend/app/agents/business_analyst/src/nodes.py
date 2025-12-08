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
    parse_document_analysis_response,
)
from app.agents.core.prompt_utils import (
    build_system_prompt as _build_system_prompt,
    build_user_prompt as _build_user_prompt,
)
from app.core.db import engine
from app.models import AgentQuestion, Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

# LLM instances (shared, like Team Leader)
# Using same model naming as team_leader (claude-haiku/sonnet without prefix)
_fast_llm = ChatOpenAI(model="claude-sonnet-4-5-20250929", temperature=0.1, timeout=30)
_default_llm = ChatOpenAI(model="claude-sonnet-4-5-20250929", temperature=0.3, timeout=90)
_story_llm = ChatOpenAI(model="claude-sonnet-4-5-20250929", temperature=0.3, timeout=180)

# Categories for clarity check (used in check_clarity and analyze_domain)
REQUIRED_CATEGORIES = {
    "target_users": [
        "khách hàng", "người dùng", "đối tượng", "ai sẽ dùng", "ai dùng",
        "cá nhân", "mình tôi", "chỉ mình", "một mình", "cho ai", "dùng cho",
        "sử dụng cho", "ai sử dụng", "người sử dụng", "dùng cho ai",
        "chia sẻ", "đồng nghiệp", "gia đình", "bạn bè", "nhóm", "team"
    ],
    "main_features": ["tính năng", "chức năng", "website cần có", "cần có gì"],
    "risks": ["lo ngại", "thách thức", "rủi ro", "khó khăn", "lo lắng", "bảo mật"],
}

OPTIONAL_CATEGORIES = {
    "business_model": ["kiếm tiền", "thu nhập", "doanh thu", "mô hình"],
    "priorities": ["ưu tiên", "quan trọng nhất", "quan trọng"],
    "details": ["thanh toán", "giao hàng", "chi tiết"],
}


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


def _save_interview_state_to_question(
    session: Session,
    question_id,
    interview_state: dict,
    verify: bool = False
) -> bool:
    """Save interview state to question's task_context for resume.
    
    Args:
        session: SQLModel session
        question_id: UUID of the question to update
        interview_state: Interview state dict to save
        verify: If True, refresh and verify the save
        
    Returns:
        True if saved successfully
    """
    question = session.get(AgentQuestion, question_id)
    if not question:
        logger.error(f"[BA] Question {question_id} not found in database")
        return False
    
    existing_context = question.task_context or {}
    question.task_context = {
        **existing_context,
        "interview_state": interview_state
    }
    flag_modified(question, "task_context")
    session.add(question)
    session.commit()
    
    if verify:
        session.refresh(question)
        saved_state = question.task_context.get("interview_state") if question.task_context else None
        if saved_state:
            logger.info(f"[BA] Verified interview state saved to question {question_id}")
            return True
        else:
            logger.error(f"[BA] Interview state NOT saved to question {question_id}!")
            return False
    
    return True


async def _generate_completion_message(
    state: BAState, 
    agent, 
    task_type: str, 
    context: str, 
    next_step: str,
    fallback: str
) -> str:
    """Generate a natural completion message using LLM with agent personality.
    
    Args:
        state: Current BA state
        agent: Agent instance for personality
        task_type: Type of completed task (prd_created, prd_updated, stories_created, stories_approved)
        context: Context info (project name, count, etc.)
        next_step: Hint for what user should do next
        fallback: Fallback message if LLM fails
    
    Returns:
        Natural completion message
    """
    try:
        system_prompt = _sys_prompt(agent, "completion_message")
        user_prompt = _user_prompt(
            "completion_message",
            task_type=task_type,
            context=context,
            next_step=next_step
        )
        
        response = await _fast_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, f"completion_{task_type}")
        )
        
        message = response.content.strip()
        # Remove any quotes if LLM wrapped the response
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        
        logger.info(f"[BA] Generated completion message: {message[:80]}...")
        return message
        
    except Exception as e:
        logger.warning(f"[BA] Failed to generate completion message: {e}, using fallback")
        return fallback


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


async def analyze_document_content(document_text: str, agent=None) -> dict:
    """Analyze uploaded document to extract requirements information.
    
    This function is called BEFORE the graph runs to pre-populate collected_info
    if the document contains comprehensive requirements.
    
    Args:
        document_text: Extracted text from uploaded document
        agent: Agent instance for LLM config
        
    Returns:
        dict with 'collected_info', 'is_comprehensive', 'summary'
    """
    logger.info(f"[BA] Analyzing uploaded document ({len(document_text)} chars)...")
    
    # Truncate very long documents to avoid token limits
    max_chars = 15000
    if len(document_text) > max_chars:
        document_text = document_text[:max_chars] + "\n\n[... document truncated ...]"
        logger.info(f"[BA] Document truncated to {max_chars} chars for analysis")
    
    system_prompt = _sys_prompt(agent, "analyze_document")
    user_prompt = _user_prompt(
        "analyze_document",
        document_text=document_text
    )
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"run_name": "analyze_document"}
        )
        
        result = parse_document_analysis_response(response.content)
        
        # Filter out None values from collected_info
        collected_info = {
            k: v for k, v in result.get("collected_info", {}).items() 
            if v is not None and v != "null" and v != ""
        }
        
        logger.info(
            f"[BA] Document analysis: type={result['document_type']}, "
            f"score={result['completeness_score']:.0%}, "
            f"comprehensive={result['is_comprehensive']}, "
            f"collected_categories={list(collected_info.keys())}"
        )
        
        return {
            "document_type": result["document_type"],
            "detected_doc_kind": result.get("detected_doc_kind", ""),
            "collected_info": collected_info,
            "is_comprehensive": result["is_comprehensive"],
            "completeness_score": result["completeness_score"],
            "summary": result["summary"],
            "extracted_items": result.get("extracted_items", []),
            "missing_info": result["missing_info"]
        }
        
    except Exception as e:
        logger.warning(f"[BA] Document analysis failed: {e}")
        return {
            "document_type": "partial_requirements",
            "detected_doc_kind": "",
            "collected_info": {},
            "is_comprehensive": False,
            "completeness_score": 0.0,
            "summary": "",
            "extracted_items": [],
            "missing_info": []
        }


# Fallback messages for document analysis feedback
_DOC_FALLBACK_MESSAGES = {
    "complete_requirements": "✅ Tài liệu đầy đủ thông tin! Mình sẽ tạo PRD trực tiếp từ nội dung này.",
    "partial_requirements": "📝 Đã trích xuất một số thông tin từ tài liệu. Mình cần hỏi thêm vài câu để làm rõ.",
    "not_requirements": "📄 Đây không phải tài liệu yêu cầu dự án. Bạn muốn mình làm gì với nội dung này?",
}


async def generate_document_feedback(
    document_type: str,
    detected_doc_kind: str,
    summary: str,
    extracted_items: list,
    missing_info: list,
    completeness_score: float,
    agent=None
) -> str:
    """Generate natural feedback message about document analysis using LLM.
    
    Args:
        document_type: "complete_requirements" | "partial_requirements" | "not_requirements"
        detected_doc_kind: Brief description if not_requirements (e.g., "biên bản họp")
        summary: Summary of document content
        extracted_items: List of successfully extracted items
        missing_info: List of missing categories
        completeness_score: 0.0-1.0 score
        agent: Agent instance for LLM config
        
    Returns:
        Generated feedback message string
    """
    try:
        system_prompt = _sys_prompt(agent, "document_analysis_feedback")
        user_prompt = _user_prompt(
            "document_analysis_feedback",
            document_type=document_type,
            detected_doc_kind=detected_doc_kind or "không xác định",
            summary=summary or "Không có tóm tắt",
            extracted_items=", ".join(extracted_items) if extracted_items else "Không có",
            missing_info=", ".join(missing_info) if missing_info else "Không có",
            completeness_score=f"{completeness_score * 100:.0f}"
        )
        
        response = await _default_llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        
        message = response.content.strip()
        logger.info(f"[BA] Generated document feedback: {message[:100]}...")
        return message
        
    except Exception as e:
        logger.warning(f"[BA] generate_document_feedback LLM failed: {e}, using fallback")
        return _DOC_FALLBACK_MESSAGES.get(document_type, _DOC_FALLBACK_MESSAGES["partial_requirements"])


async def respond_conversational(state: BAState, agent=None) -> dict:
    """Node: Respond to casual conversation (greetings, thanks, etc.)."""
    logger.info(f"[BA] Handling conversational message: {state['user_message'][:50]}...")
    
    try:
        system_prompt = _sys_prompt(agent, "respond_conversational")
        user_prompt = _user_prompt(
            "respond_conversational",
            user_message=state["user_message"]
        )
        
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "respond_conversational")
        )
        
        message = response.content.strip()
        
        # Send response to user
        if agent:
            await agent.message_user("response", message)
            # Note: Removed redundant warning about attachments - the main response should address document context
        
        logger.info(f"[BA] Conversational response sent: {message[:50]}...")
        
        return {"is_complete": True}
        
    except Exception as e:
        logger.error(f"[BA] Conversational response failed: {e}")
        fallback = "Chào bạn! Mình là BA, sẵn sàng hỗ trợ. Bạn cần gì nhé? 😊"
        if agent:
            await agent.message_user("response", fallback)
        return {"is_complete": True}


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
        
        # If no questions generated, send fallback message to user
        if not questions and agent:
            logger.warning("[BA] No questions generated, sending fallback message")
            await agent.message_user(
                "response",
                "Để mình giúp bạn tạo PRD, bạn có thể cho mình biết thêm:\n"
                "- Sản phẩm/dự án bạn muốn làm là gì?\n"
                "- Đối tượng người dùng là ai?\n"
                "- Những tính năng chính cần có?"
            )
        
        return {"questions": questions}
        
    except Exception as e:
        logger.error(f"[BA] Failed to generate questions: {e}")
        # Send fallback message on error
        if agent:
            await agent.message_user(
                "response",
                "Mình cần thêm thông tin để hỗ trợ bạn. Bạn có thể mô tả sản phẩm/dự án cần làm không?"
            )
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
            interview_state = {
                "questions": questions,
                "current_question_index": current_index,
                "collected_answers": state.get("collected_answers", []),
                "collected_info": state.get("collected_info", {}),
                "user_message": state.get("user_message", ""),
            }
            _save_interview_state_to_question(session, question_id, interview_state, verify=True)
        
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
            
            interview_state = {
                "questions": questions,
                "question_ids": [str(qid) for qid in question_ids],
                "collected_info": state.get("collected_info", {}),
                "user_message": state.get("user_message", ""),
                "research_loop_count": state.get("research_loop_count", 0),
            }
            _save_interview_state_to_question(session, question_ids[0], interview_state)
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
            question = questions[q_idx]
            answer_text = ans.get("answer", "")
            selected_options = ans.get("selected_options", [])
            
            # If multichoice, join selected options
            if selected_options:
                answer_text = ", ".join(selected_options)
            
            collected_answers.append({
                "question_index": q_idx,
                "question_text": question.get("text", ""),
                "answer": answer_text,
                "selected_options": selected_options,
                "category": question.get("category", "")  # Preserve category for clarity check
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
    
    # Get conversation context for memory
    conversation_context = state.get("conversation_context", "")
    if conversation_context:
        logger.info(f"[BA] Using conversation context for PRD update: {len(conversation_context)} chars")
    
    system_prompt = _sys_prompt(agent, "update_prd")
    user_prompt = _user_prompt(
        "update_prd",
        existing_prd=json.dumps(existing_prd, ensure_ascii=False, indent=2),
        user_message=state["user_message"],
        conversation_context=conversation_context
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


async def _generate_stories_for_epic(
    epic: dict, 
    prd: dict, 
    all_epic_ids: list, 
    state: BAState, 
    agent=None
) -> dict:
    """Generate stories for a single Epic (used in parallel batch processing)."""
    epic_id = epic.get("id", "EPIC-???")
    epic_title = epic.get("title", "Unknown")
    
    logger.info(f"[BA] Generating stories for Epic: {epic_title}")
    
    # Find related features from PRD
    feature_refs = epic.get("feature_refs", [])
    prd_features = []
    for feature in prd.get("features", []):
        if feature.get("name") in feature_refs:
            prd_features.append(feature)
    
    # If no feature_refs matched, include all features for this epic
    if not prd_features:
        prd_features = prd.get("features", [])
    
    system_prompt = _sys_prompt(agent, "generate_stories_for_epic")
    user_prompt = _user_prompt(
        "generate_stories_for_epic",
        epic_id=epic_id,
        epic_title=epic_title,
        epic_domain=epic.get("domain", "General"),
        epic_description=epic.get("description", ""),
        prd_features=json.dumps(prd_features, ensure_ascii=False, indent=2),
        all_epic_ids=", ".join(all_epic_ids)
    )
    
    try:
        logger.info(f"[BA] Calling LLM for Epic '{epic_title}' with {len(prd_features)} features")
        
        response = await _story_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, f"generate_stories_{epic_id}")
        )
        
        logger.info(f"[BA] LLM response for Epic '{epic_title}': {len(response.content)} chars")
        logger.debug(f"[BA] Response preview: {response.content[:500]}...")
        
        result = parse_stories_response(response.content)
        logger.info(f"[BA] Parsed result keys for Epic '{epic_title}': {list(result.keys())}")
        
        # parse_stories_response returns {"epics": [...]} format
        # For single epic generation, stories are inside the first epic
        stories = []
        if "epics" in result and result["epics"]:
            # Get stories from the first (and only) epic in the response
            first_epic = result["epics"][0]
            stories = first_epic.get("stories", [])
            logger.info(f"[BA] Found {len(stories)} stories in epics[0] for Epic '{epic_title}'")
        elif "stories" in result:
            # Direct stories format (fallback)
            stories = result.get("stories", [])
            logger.info(f"[BA] Found {len(stories)} stories directly for Epic '{epic_title}'")
        else:
            logger.warning(f"[BA] No stories found in result for Epic '{epic_title}': {result}")
        
        # Add epic info to each story
        for story in stories:
            story["epic_id"] = epic_id
            story["epic_title"] = epic_title
        
        logger.info(f"[BA] Generated {len(stories)} stories for Epic '{epic_title}'")
        return {"epic_id": epic_id, "stories": stories}
        
    except Exception as e:
        logger.error(f"[BA] Failed to generate stories for Epic '{epic_title}': {e}")
        return {"epic_id": epic_id, "stories": [], "error": str(e)}


async def extract_stories(state: BAState, agent=None) -> dict:
    """Node: Extract epics with INVEST-compliant user stories from PRD.
    
    Uses BATCH PROCESSING for better performance:
    - Phase 1: Extract Epics only (fast, ~5s)
    - Phase 2: Generate stories for each Epic in PARALLEL (~15s total instead of ~60s)
    """
    import asyncio
    
    logger.info(f"[BA] Extracting epics and user stories (batch mode)...")
    
    prd = state.get("prd_draft") or state.get("existing_prd", {})
    
    if not prd:
        logger.error("[BA] No PRD available to extract stories from")
        return {
            "epics": [],
            "stories": [],
            "error": "No PRD available. Please create a PRD first."
        }
    
    # Check if PRD is simple (few features) - use single call instead of batch
    features_count = len(prd.get("features", []))
    use_batch = features_count >= 3  # Use batch for 3+ features
    
    if not use_batch:
        # Simple PRD - use single call (original method)
        logger.info(f"[BA] Using single-call mode for simple PRD ({features_count} features)")
        return await _extract_stories_single_call(state, agent, prd)
    
    logger.info(f"[BA] Using batch mode for complex PRD ({features_count} features)")
    
    try:
        # =============================================
        # PHASE 1: Extract Epics only (fast call ~5s)
        # =============================================
        logger.info("[BA] Phase 1: Extracting Epics structure...")
        
        system_prompt = _sys_prompt(agent, "extract_epics_only")
        user_prompt = _user_prompt(
            "extract_epics_only",
            prd=json.dumps(prd, ensure_ascii=False, indent=2)
        )
        
        response = await _fast_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "extract_epics_only")
        )
        
        epics_result = parse_stories_response(response.content)
        epics = epics_result.get("epics", [])
        
        if not epics:
            logger.warning("[BA] No epics extracted, falling back to single call")
            return await _extract_stories_single_call(state, agent, prd)
        
        logger.info(f"[BA] Phase 1 complete: {len(epics)} Epics extracted")
        
        # =============================================
        # PHASE 2: Generate stories for each Epic IN PARALLEL
        # =============================================
        logger.info(f"[BA] Phase 2: Generating stories for {len(epics)} Epics in parallel...")
        
        all_epic_ids = [epic.get("id", "") for epic in epics]
        
        # Use semaphore to limit concurrent LLM calls (avoid rate limiting)
        MAX_CONCURRENT_LLM_CALLS = 5
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
        
        async def _generate_with_semaphore(epic):
            async with semaphore:
                return await _generate_stories_for_epic(epic, prd, all_epic_ids, state, agent)
        
        # Create tasks with rate limiting
        tasks = [_generate_with_semaphore(epic) for epic in epics]
        
        # Run tasks (max 2 concurrent at a time)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all stories and update epics
        all_stories = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[BA] Error generating stories for Epic {i}: {result}")
                continue
            
            epic_id = result.get("epic_id")
            stories = result.get("stories", [])
            
            # Find and update the epic with its stories
            for epic in epics:
                if epic.get("id") == epic_id:
                    epic["stories"] = stories
                    break
            
            # Add to flat list
            all_stories.extend(stories)
        
        total_epics = len(epics)
        total_stories = len(all_stories)
        logger.info(f"[BA] Batch extraction complete: {total_epics} epics with {total_stories} stories")
        
        # If batch mode generated no stories, fall back to single call
        if total_stories == 0 and total_epics > 0:
            logger.warning(f"[BA] Batch mode generated 0 stories for {total_epics} epics, falling back to single call")
            return await _extract_stories_single_call(state, agent, prd)
        
        return {
            "epics": epics,
            "stories": all_stories
        }
        
    except Exception as e:
        logger.error(f"[BA] Batch extraction failed: {e}, falling back to single call")
        return await _extract_stories_single_call(state, agent, prd)


async def _extract_stories_single_call(state: BAState, agent, prd: dict) -> dict:
    """Original single-call story extraction (fallback for simple PRDs)."""
    system_prompt = _sys_prompt(agent, "extract_stories")
    user_prompt = _user_prompt(
        "extract_stories",
        prd=json.dumps(prd, ensure_ascii=False, indent=2)
    )
    
    try:
        response = await _story_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "extract_stories")
        )
        
        result = parse_stories_response(response.content)
        epics = result.get("epics", [])
        
        # Flatten stories for backward compatibility
        all_stories = []
        for epic in epics:
            stories_in_epic = epic.get("stories", [])
            epic_title = epic.get("title", epic.get("name", "Unknown"))
            for story in stories_in_epic:
                story["epic_id"] = epic.get("id")
                story["epic_title"] = epic_title
                all_stories.append(story)
        
        logger.info(f"[BA] Single-call extraction: {len(epics)} epics, {len(all_stories)} stories")
        
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
    """Node: Approve stories and save them to database (batch operation)."""
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
        story_id_map = {}  # Map string ID (EPIC-001-US-001) to actual UUID
        
        with Session(engine) as session:
            # 1. Create all Epics at once
            epic_objects = []
            for epic_data in epics_data:
                epic_string_id = epic_data.get("id", "")  # e.g., "EPIC-001"
                epic = Epic(
                    epic_code=epic_string_id if epic_string_id else None,  # Save epic code
                    title=epic_data.get("title", epic_data.get("name", "Unknown Epic")),
                    description=epic_data.get("description"),
                    domain=epic_data.get("domain"),
                    project_id=agent.project_id,
                    epic_status=EpicStatus.PLANNED
                )
                epic_objects.append((epic, epic_string_id))
                session.add(epic)
            
            # Single flush for all epics
            session.flush()
            
            # Build epic ID map after flush
            for epic, string_id in epic_objects:
                epic_id_map[string_id] = epic.id
                created_epics.append({
                    "id": str(epic.id),
                    "title": epic.title,
                    "domain": epic.domain
                })
            
            logger.info(f"[BA] Created {len(created_epics)} epics in batch")
            
            # 2. Create all Stories at once
            max_rank_result = session.exec(
                select(func.max(Story.rank)).where(
                    Story.project_id == agent.project_id,
                    Story.status == StoryStatus.TODO
                )
            ).one()
            current_rank = (max_rank_result or 0)
            
            story_objects = []  # (story, string_id, original_deps)
            for story_data in stories_data:
                epic_string_id = story_data.get("epic_id", "")
                epic_uuid = epic_id_map.get(epic_string_id)
                current_rank += 1
                story_string_id = story_data.get("id", "")  # e.g., "EPIC-001-US-001"
                original_dependencies = story_data.get("dependencies", [])
                
                story = Story(
                    story_code=story_string_id if story_string_id else None,  # Save story code
                    title=story_data.get("title", "Unknown Story"),
                    description=story_data.get("description"),
                    acceptance_criteria=story_data.get("acceptance_criteria", []),
                    requirements=story_data.get("requirements", []),
                    project_id=agent.project_id,
                    epic_id=epic_uuid,
                    status=StoryStatus.TODO,
                    type=StoryType.USER_STORY,
                    priority=story_data.get("priority"),
                    story_point=story_data.get("story_point"),
                    rank=current_rank,
                    dependencies=[],
                )
                story_objects.append((story, story_string_id, original_dependencies))
                session.add(story)
            
            # Single flush for all stories
            session.flush()
            
            # Build story ID map and created_stories list after flush
            for story, string_id, _ in story_objects:
                story_id_map[string_id] = str(story.id)
                created_stories.append({
                    "id": str(story.id),
                    "string_id": string_id,
                    "title": story.title,
                    "epic_id": str(story.epic_id) if story.epic_id else None
                })
            
            logger.info(f"[BA] Created {len(created_stories)} stories in batch")
            
            # 3. Resolve dependencies (no additional flush needed, just update objects)
            deps_resolved = 0
            for story, _, original_deps in story_objects:
                if original_deps:
                    resolved_deps = [
                        story_id_map[dep_id] 
                        for dep_id in original_deps 
                        if dep_id in story_id_map
                    ]
                    if resolved_deps:
                        story.dependencies = resolved_deps
                        deps_resolved += 1
            
            if deps_resolved:
                logger.info(f"[BA] Resolved dependencies for {deps_resolved} stories")
            
            # Single commit for everything
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


def check_clarity(state: BAState) -> dict:
    """Check if collected info covers required categories.
    
    Returns:
        dict with is_clear, covered_categories, missing_categories
    """
    answers = state.get("collected_info", {}).get("interview_answers", [])
    
    covered = {cat: False for cat in REQUIRED_CATEGORIES}
    
    for answer in answers:
        question_text = answer.get("question_text", "").lower()
        answer_text = str(answer.get("answer", "")).lower()
        category = answer.get("category", "")  # Check explicit category first
        
        # Skip empty answers
        if not answer_text or len(answer_text.strip()) < 3:
            continue
        
        # Method 1: Check explicit category field (preferred)
        if category and category in covered:
            covered[category] = True
            logger.debug(f"[BA] Category '{category}' covered by explicit field")
            continue
        
        # Method 2: Fallback to keyword matching in question + answer
        combined_text = f"{question_text} {answer_text}"
        for cat, keywords in REQUIRED_CATEGORIES.items():
            if not covered[cat]:  # Only check if not already covered
                if any(kw in combined_text for kw in keywords):
                    covered[cat] = True
                    logger.debug(f"[BA] Category '{cat}' covered by keyword match in: {combined_text[:100]}")
    
    missing = [cat for cat, is_covered in covered.items() if not is_covered]
    is_clear = len(missing) == 0
    
    logger.info(f"[BA] Clarity check: covered={[c for c, v in covered.items() if v]}, missing={missing}, total_answers={len(answers)}")
    
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
    
    # Build category info for prompt
    categories_to_ask = []
    for cat in missing_categories:
        cat_name = category_prompts.get(cat, cat)
        categories_to_ask.append(f'- category: "{cat}", về: {cat_name}')
    categories_str = "\n".join(categories_to_ask)
    
    user_prompt = f"""Dựa trên cuộc trò chuyện trước, user muốn: "{user_message}"

Thông tin đã thu thập: {json.dumps(collected_info, ensure_ascii=False)}

Kết quả tìm hiểu thêm từ web: {json.dumps(domain_research, ensure_ascii=False)[:1500]}

**QUAN TRỌNG - KIỂM TRA KỸ TRƯỚC KHI HỎI:**
Xem kỹ "Thông tin đã thu thập" ở trên. NẾU user đã trả lời về:
- Đối tượng sử dụng (ví dụ: "cá nhân", "chỉ mình tôi", "cho bản thân") → KHÔNG hỏi lại về target_users
- Tính năng (ví dụ: đã liệt kê các features) → KHÔNG hỏi lại về main_features  
- Rủi ro/lo ngại (ví dụ: "bảo mật", "an toàn") → KHÔNG hỏi lại về risks

CẦN HỎI THÊM VỀ CÁC CATEGORY SAU (NẾU CHƯA CÓ trong collected_info):
{categories_str}

Hãy tạo 1-2 câu hỏi CHO MỖI CATEGORY thực sự còn thiếu.
QUAN TRỌNG: 
- Mỗi question PHẢI có field "category" để tracking
- KHÔNG hỏi lại những gì user đã trả lời
- Nếu tất cả categories đã có thông tin, trả về questions: []

**LUÔN DÙNG MULTICHOICE** để user dễ trả lời nhanh:
- Tất cả câu hỏi PHẢI là "type": "multichoice" với options
- Luôn thêm option cuối: "Khác (vui lòng mô tả)"

Return JSON format:
```json
{{
  "questions": [
    {{
      "text": "Câu hỏi về rủi ro/lo ngại?",
      "type": "multichoice",
      "options": ["Lo ngại 1", "Lo ngại 2", "Khác (vui lòng mô tả)"],
      "allow_multiple": true,
      "category": "risks"
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


async def _save_prd_artifact(state: BAState, agent, project_files) -> dict:
    """Save PRD to database and file system.
    
    Returns:
        dict with prd_artifact_id, prd_saved, summary, next_steps, error
    """
    result = {"prd_artifact_id": None, "prd_saved": False, "summary": "", "next_steps": [], "error": None}
    prd_data = state.get("prd_draft")
    
    if not prd_data or not agent:
        return result
    
    try:
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
                save_to_file=False
            )
            result["prd_artifact_id"] = str(artifact.id)
        
        # Save markdown for human reading
        if project_files:
            await project_files.save_prd(prd_data)
        
        result["prd_saved"] = True
        result["summary"] = f"PRD '{project_name}' saved successfully"
        result["next_steps"] = ["Review PRD document", "Approve to create user stories", "Or request edits"]
        
        # Send message to user
        is_update = bool(state.get("change_summary"))
        task_type = "prd_updated" if is_update else "prd_created"
        context = f"Đã cập nhật PRD cho dự án '{project_name}'" if is_update else f"Đã tạo xong PRD cho dự án '{project_name}'"
        next_step = "User cần review lại và cho biết còn gì cần chỉnh không" if is_update else "User cần xem qua và phê duyệt để tạo user stories"
        fallback = f"Mình đã cập nhật PRD theo yêu cầu của bạn rồi nhé! 📝" if is_update else f"Tuyệt vời! 🎉 Mình đã hoàn thành PRD cho dự án '{project_name}' rồi!"
        
        message_content = await _generate_completion_message(state, agent, task_type, context, next_step, fallback)
        await agent.message_user(
            event_type="response",
            content=message_content,
            details={"message_type": "prd_created", "file_path": "docs/prd.md", "title": project_name, "artifact_id": result["prd_artifact_id"]}
        )
        
        logger.info(f"[BA] PRD saved: {project_name} (artifact_id={result['prd_artifact_id']})")
        
    except Exception as e:
        logger.error(f"[BA] Failed to save PRD: {e}", exc_info=True)
        result["error"] = f"Failed to save PRD: {str(e)}"
    
    return result


async def _save_stories_artifact(state: BAState, agent, project_files) -> dict:
    """Save stories to database and file system.
    
    Returns:
        dict with stories_artifact_id, stories_saved, summary, next_steps, error
    """
    result = {"stories_artifact_id": None, "stories_saved": False, "summary": "", "next_steps": [], "error": None}
    
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    is_stories_approved = state.get("stories_approved", False) or bool(state.get("created_epics"))
    intent = state.get("intent", "")
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories"]
    
    if not (epics_data or stories_data) or not project_files or is_stories_approved or not is_story_intent:
        return result
    
    try:
        await project_files.save_user_stories(epics_data, stories_data)
        result["stories_saved"] = True
        
        epics_count = len(epics_data)
        stories_count = len(stories_data)
        
        # Save to Artifact table
        if agent:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact_content = {"epics": epics_data, "stories": stories_data, "epics_count": epics_count, "stories_count": stories_count}
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
        
        result["summary"] = f"Extracted {epics_count} epics with {stories_count} INVEST-compliant stories"
        result["next_steps"] = ["Review epics and prioritize stories", "Approve to add to backlog"]
        
        # Send message to user
        if agent:
            stories_message = await _generate_completion_message(
                state, agent, "stories_created",
                f"Đã tạo {stories_count} User Stories từ {epics_count} Epics",
                "User cần review và phê duyệt để đưa vào backlog",
                f"Xong rồi! 🚀 Mình đã tạo '{stories_count} User Stories' từ PRD."
            )
            await agent.message_user(
                event_type="response",
                content=stories_message,
                details={"message_type": "stories_created", "file_path": "docs/user-stories.md", "epics_count": epics_count, "stories_count": stories_count, "status": "pending"}
            )
        
        logger.info(f"[BA] Saved {epics_count} epics with {stories_count} user stories (pending approval)")
        
    except Exception as e:
        logger.error(f"[BA] Failed to save stories: {e}", exc_info=True)
        result["error"] = f"Failed to save stories: {str(e)}"
    
    return result


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
    
    # Save PRD using helper
    prd_result = await _save_prd_artifact(state, agent, project_files)
    if prd_result.get("prd_saved"):
        result.update({
            "prd_artifact_id": prd_result["prd_artifact_id"],
            "prd_saved": True,
            "summary": prd_result["summary"],
        })
        result["next_steps"].extend(prd_result["next_steps"])
    if prd_result.get("error"):
        result["error"] = prd_result["error"]
    
    # Save stories using helper
    stories_result = await _save_stories_artifact(state, agent, project_files)
    if stories_result.get("stories_saved"):
        result.update({
            "stories_artifact_id": stories_result["stories_artifact_id"],
            "stories_saved": True,
            "summary": stories_result["summary"],
        })
        result["next_steps"].extend(stories_result["next_steps"])
    if stories_result.get("error"):
        result["error"] = stories_result["error"]
    
    # Handle case where story extraction failed (no stories returned)
    intent = state.get("intent", "")
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories"]
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    if is_story_intent and not epics_data and not stories_data and agent and not stories_result.get("stories_saved"):
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
            stories_count = len(state.get("created_stories", []))
            approved_message = await _generate_completion_message(
                state, agent,
                task_type="stories_approved",
                context=f"Đã thêm {stories_count} User Stories vào backlog thành công",
                next_step="User có thể xem trên Kanban board và bắt đầu implement",
                fallback=f"Tuyệt vời! 🎊 Đã thêm Stories vào backlog rồi! Bạn có thể xem trên Kanban board và bắt đầu implement được luôn nha~"
            )
            await agent.message_user(
                event_type="response",
                content=approved_message,
                details={
                    "message_type": "stories_approved",  # Frontend will refresh Kanban, no card
                    "task_completed": True  # Signal to release ownership
                }
            )
    
    logger.info(f"[BA] Artifacts saved: {result['summary']}")
    
    # Determine if task is truly complete (should release ownership)
    # ONLY release ownership when stories are APPROVED (final step in BA workflow)
    # Keep ownership for: PRD create/update, stories pending approval, waiting for answer
    is_stories_approved = result.get("stories_approved", False)
    
    if is_stories_approved:
        result["task_completed"] = True
        logger.info(f"[BA] Stories approved - task completed, will release ownership")
    else:
        logger.info(f"[BA] Task not complete yet, keeping ownership (stories_approved={is_stories_approved})")
    
    return {
        "result": result,
        "is_complete": True
    }


# =============================================================================
# STORY VERIFY NODE - Simple 1-Phase LLM
# =============================================================================

async def verify_story_simple(state: dict, agent=None) -> dict:
    """Verify a newly created story with single LLM call.
    
    Loads PRD + existing stories, then asks LLM to:
    1. Check for duplicates
    2. Evaluate INVEST compliance
    3. Suggest improvements
    
    Args:
        state: Must contain:
            - new_story: Story object to verify
            - project_id: UUID of the project
            - full_prd: PRD dict (optional)
            - existing_stories: List of existing stories (optional)
        agent: BA agent instance for messaging
    
    Returns:
        dict with verification results
    """
    logger.info("[BA] Starting simple story verification...")
    
    new_story = state.get("new_story")
    project_id = state.get("project_id")
    full_prd = state.get("full_prd")
    existing_stories = state.get("existing_stories", [])
    
    if not new_story:
        logger.error("[BA] No new_story in state")
        return {"error": "No story provided", "is_complete": True}
    
    # Build story info
    story_info = {
        "title": new_story.title,
        "description": new_story.description or "(empty)",
        "acceptance_criteria": new_story.acceptance_criteria or "(empty)",
        "type": new_story.type.value if new_story.type else "UserStory"
    }
    
    # Build PRD context
    prd_context = "No PRD available for this project."
    if full_prd:
        prd_context = f"""PROJECT PRD:
- Project Name: {full_prd.get('project_name', 'Unknown')}
- Overview: {full_prd.get('overview', 'N/A')[:500]}
- Target Users: {json.dumps(full_prd.get('target_users', []), ensure_ascii=False)}
- Core Features: {json.dumps(full_prd.get('features', [])[:5], ensure_ascii=False)}
"""
    
    # Build existing stories context
    stories_context = "No existing stories in this project."
    if existing_stories:
        stories_list = []
        for s in existing_stories[:20]:  # Limit to 20 stories
            title = s.title if hasattr(s, 'title') else s.get('title', 'Unknown')
            desc = s.description if hasattr(s, 'description') else s.get('description', '')
            desc_preview = (desc or "")[:100]
            stories_list.append(f"- {title}: {desc_preview}")
        stories_context = f"EXISTING STORIES ({len(existing_stories)} total):\n" + "\n".join(stories_list)
    
    # Build prompts from YAML
    system_prompt = _sys_prompt(agent, "verify_story")
    user_prompt = _user_prompt(
        "verify_story",
        prd_context=prd_context,
        stories_context=stories_context,
        story_title=story_info['title'],
        story_description=story_info['description'],
        story_acceptance_criteria=story_info['acceptance_criteria'],
        story_type=story_info['type']
    )

    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "verify_story_simple")
        )
        
        # Parse JSON response
        content = response.content.strip()
        
        # Extract JSON from markdown code block if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        logger.info(f"[BA] Story verification complete: invest_score={result.get('invest_score')}, "
                    f"is_duplicate={result.get('is_duplicate')}")
        
        # Send suggestions to user (always send, even without agent)
        await _send_verify_message(agent, new_story, result, project_id=project_id)
        
        return {
            "verification_result": result,
            "is_complete": True
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[BA] Failed to parse LLM response: {e}")
        return {"error": str(e), "is_complete": True}
        
    except Exception as e:
        logger.error(f"[BA] Story verification failed: {e}", exc_info=True)
        return {"error": str(e), "is_complete": True}


async def _send_verify_message(agent, story, result: dict, project_id=None) -> None:
    """Send verification result message to user via Kafka."""
    from uuid import uuid4
    from app.kafka import get_kafka_producer, KafkaTopics
    from app.kafka.event_schemas import AgentEvent
    from app.models import Message, AuthorType
    
    is_duplicate = result.get("is_duplicate", False)
    duplicate_of = result.get("duplicate_of")
    invest_score = result.get("invest_score", 6)
    invest_issues = result.get("invest_issues", [])
    suggested_title = result.get("suggested_title")
    suggested_requirements = result.get("suggested_requirements")
    suggested_ac = result.get("suggested_acceptance_criteria")
    summary = result.get("summary", "")
    
    # Build natural message based on result
    if is_duplicate:
        content = f"Mình vừa kiểm tra story \"{story.title}\" và thấy có vẻ trùng với story đã có. Bạn xem chi tiết bên dưới nhé!"
    elif invest_score >= 5:
        content = f"Story \"{story.title}\" của bạn đã đạt chuẩn INVEST rồi đó! 👍"
    elif invest_score >= 3:
        content = f"Mình đã review story \"{story.title}\". Có một vài điểm cần cải thiện, bạn xem gợi ý bên dưới nhé!"
    else:
        content = f"Story \"{story.title}\" cần được cải thiện khá nhiều. Mình có một số gợi ý cho bạn!"
    
    details = {
        "message_type": "story_review",
        "story_id": str(story.id),
        "story_title": story.title,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "invest_score": invest_score,
        "invest_issues": invest_issues,
        "suggested_title": suggested_title,
        "suggested_requirements": suggested_requirements,
        "suggested_acceptance_criteria": suggested_ac,
        "has_suggestions": bool(suggested_title or suggested_requirements or suggested_ac)
    }
    
    # Get agent info (agent.name is already human_name from base_agent)
    agent_name = agent.name if agent else "Business Analyst"
    agent_id = str(agent.agent_id) if agent else None
    proj_id = str(project_id) if project_id else (str(agent.project_id) if agent else None)
    
    # Save to DB
    message_id = None
    try:
        with Session(engine) as session:
            db_message = Message(
                project_id=project_id or (agent.project_id if agent else None),
                content=content,
                author_type=AuthorType.AGENT,
                agent_id=agent.agent_id if agent else None,
                message_type="story_review",
                structured_data=details,
                message_metadata={"agent_name": agent_name}  # Fallback for agent_name
            )
            session.add(db_message)
            session.commit()
            session.refresh(db_message)
            message_id = db_message.id
            logger.info(f"[BA] Saved story review message to DB: {message_id}")
    except Exception as e:
        logger.error(f"[BA] Failed to save message to DB: {e}")
    
    # Publish to Kafka
    try:
        producer = await get_kafka_producer()
        event = AgentEvent(
            event_type="agent.response",
            agent_name=agent_name,
            agent_id=agent_id or "ba-auto-verify",
            project_id=proj_id,
            content=content,
            details={
                **details,
                "message_id": str(message_id) if message_id else None,
            },
            execution_context={
                "mode": "background",
                "task_type": "story_verify",
                "display_mode": "chat",
            }
        )
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        logger.info(f"[BA] Published story review to Kafka for story {story.id}")
    except Exception as e:
        logger.error(f"[BA] Failed to publish to Kafka: {e}")


async def send_review_action_response(
    story_id: str,
    story_title: str,
    action: str,
    project_id,
    agent = None
) -> None:
    """
    Send natural response message when user takes action on story review.
    Uses LLM to generate personality-driven message.
    """
    from app.models import Message, AuthorType
    from sqlmodel import Session
    from app.core.db import engine
    
    logger.info(f"[BA] Generating review action response for story {story_id}, action: {action}")
    
    # Get agent info
    agent_name = agent.name if agent else "Business Analyst"
    agent_id = str(agent.agent_id) if agent else None
    proj_id = str(project_id) if project_id else (str(agent.project_id) if agent else None)
    
    # Simple confirmation messages (no LLM needed)
    confirmation_messages = {
        "apply": f"Áp dụng gợi ý cho story \"{story_title}\".",
        "keep": f"Giữ nguyên story \"{story_title}\".",
        "remove": f"Loại bỏ story \"{story_title}\"."
    }
    content = confirmation_messages.get(action, f"Đã xử lý story \"{story_title}\".")
    
    # Save to DB
    message_id = None
    try:
        with Session(engine) as session:
            db_message = Message(
                project_id=project_id,
                content=content,
                author_type=AuthorType.AGENT,
                agent_id=agent.agent_id if agent else None,
                message_type="text",
                message_metadata={"agent_name": agent_name}
            )
            session.add(db_message)
            session.commit()
            session.refresh(db_message)
            message_id = db_message.id
            logger.info(f"[BA] Saved review action response to DB: {message_id}")
    except Exception as e:
        logger.error(f"[BA] Failed to save message to DB: {e}")
    
    # Publish to Kafka
    try:
        producer = await get_kafka_producer()
        event = AgentEvent(
            event_type="agent.response",
            agent_name=agent_name,
            agent_id=agent_id or "ba-auto-verify",
            project_id=proj_id,
            content=content,
            details={
                "message_id": str(message_id) if message_id else None,
                "action": action,
                "story_id": story_id,
            },
            execution_context={
                "mode": "background",
                "task_type": "review_action_response",
                "display_mode": "chat",
            }
        )
        await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
        logger.info(f"[BA] Published review action response to Kafka")
    except Exception as e:
        logger.error(f"[BA] Failed to publish to Kafka: {e}")
