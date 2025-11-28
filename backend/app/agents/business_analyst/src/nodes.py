"""LangGraph Node Functions for Business Analyst

Uses shared prompt_utils from core (same pattern as Team Leader).
"""

import json
import logging
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

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

logger = logging.getLogger(__name__)

# LLM instances (shared, like Team Leader)
_fast_llm = ChatOpenAI(model="gpt-4.1", temperature=0.1, timeout=30)
_default_llm = ChatOpenAI(model="gpt-4.1", temperature=0.7, timeout=90)  # 90s for complex prompts
_story_llm = ChatOpenAI(model="gpt-4.1", temperature=0.7, timeout=180)  # 180s for story extraction


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
        from sqlmodel import Session
        from sqlalchemy.orm.attributes import flag_modified
        from app.core.db import engine
        from app.models import AgentQuestion
        
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
        from sqlmodel import Session
        from sqlalchemy.orm.attributes import flag_modified
        from app.core.db import engine
        from app.models import AgentQuestion
        
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
    
    # Build collected_info
    collected_info = state.get("collected_info", {})
    collected_info["interview_answers"] = collected_answers
    collected_info["interview_completed"] = True
    
    return {
        "collected_answers": collected_answers,
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
        
        result = parse_stories_response(response.content)
        epics = result.get("epics", [])
        
        # Flatten stories for backward compatibility
        all_stories = []
        for epic in epics:
            for story in epic.get("stories", []):
                story["epic_id"] = epic.get("id")
                story["epic_title"] = epic.get("title")
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


async def analyze_domain(state: BAState, agent=None) -> dict:
    """Node: Perform domain analysis."""
    logger.info(f"[BA] Analyzing domain...")
    
    system_prompt = _sys_prompt(agent, "domain_analysis")
    user_prompt = _user_prompt(
        "domain_analysis",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False)
    )
    
    try:
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "analyze_domain")
        )
        
        logger.info(f"[BA] Domain analysis completed ({len(response.content)} chars)")
        return {"analysis_text": response.content}
        
    except Exception as e:
        logger.error(f"[BA] Domain analysis failed: {e}")
        return {
            "analysis_text": f"Domain analysis failed: {str(e)}",
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
            from sqlmodel import Session
            from app.core.db import engine
            from app.services.artifact_service import ArtifactService
            from app.models import ArtifactType
            
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
            message_content = "PRD đã được cập nhật" if is_update else "PRD được tạo thành công"
            
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
    
    # Save epics and stories if exist
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    if (epics_data or stories_data) and project_files:
        try:
            # Save with epic structure
            await project_files.save_user_stories(epics_data, stories_data)
            result["stories_saved"] = True
            
            epics_count = len(epics_data)
            stories_count = len(stories_data)
            total_points = sum(epic.get("total_story_points", 0) for epic in epics_data)
            
            result["summary"] = f"Extracted {epics_count} epics with {stories_count} INVEST-compliant stories"
            result["next_steps"].extend([
                "Review epics and prioritize stories",
                "Add stories to backlog",
                "Estimate effort for each story"
            ])
            
            # Send success message with View button
            if agent:
                await agent.message_user(
                    event_type="response",
                    content=f"Epics & User Stories đã được tạo",
                    details={
                        "message_type": "stories_created",
                        "file_path": "docs/user-stories.md",
                        "epics_count": epics_count,
                        "stories_count": stories_count,
                        "total_story_points": total_points
                    }
                )
            
            logger.info(f"[BA] Saved {epics_count} epics with {stories_count} user stories")
            
        except Exception as e:
            logger.error(f"[BA] Failed to save stories: {e}", exc_info=True)
            result["error"] = f"Failed to save stories: {str(e)}"
    
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
                content=f"📊 Domain Analysis Complete\n\n{state['analysis_text'][:2000]}",
                details={"analysis": state["analysis_text"]}
            )
    
    # PRD update - show updated PRD card (same as create, no extra text message)
    if state.get("change_summary"):
        result["change_summary"] = state["change_summary"]
        # Card is already shown in the PRD save section above
    
    logger.info(f"[BA] Artifacts saved: {result['summary']}")
    
    return {
        "result": result,
        "is_complete": True
    }
