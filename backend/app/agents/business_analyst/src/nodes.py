"""LangGraph Node Functions for Business Analyst"""

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .state import BAState
from .prompts import (
    build_system_prompt,
    build_user_prompt,
    parse_intent_response,
    parse_questions_response,
    parse_prd_response,
    parse_prd_update_response,
    parse_stories_response,
)

logger = logging.getLogger(__name__)


def _get_llm_with_callback(agent, trace_name: str, tags: list = None, metadata: dict = None):
    """Create LLM instance with Langfuse callback from agent."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    callbacks = []
    if agent:
        callback = agent.get_langfuse_callback(
            trace_name=trace_name,
            tags=tags or ["ba"],
            metadata=metadata or {}
        )
        if callback:
            callbacks.append(callback)
    
    return llm, callbacks


def _get_agent_info(agent):
    """Get agent personality info."""
    if agent:
        return {
            "name": agent.name,
            "traits": agent.agent_model.personality_traits or [],
            "style": agent.agent_model.communication_style or "professional and clear"
        }
    return {
        "name": "Business Analyst",
        "traits": [],
        "style": "professional and clear"
    }


async def analyze_intent(state: BAState, agent=None) -> dict:
    """Node: Analyze user intent and classify task.
    
    Uses BaseAgent's get_langfuse_callback() for LLM tracing.
    """
    logger.info(f"[BA] Analyzing intent: {state['user_message'][:80]}...")
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_analyze_intent",
        tags=["ba", "intent"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="analyze_intent"
    )
    
    user_prompt = build_user_prompt(
        task_name="analyze_intent",
        user_message=state["user_message"],
        has_prd="Yes" if state.get("existing_prd") else "No",
        has_info="Yes" if state.get("collected_info") else "No"
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
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
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_interview",
        tags=["ba", "interview"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="interview_requirements"
    )
    
    user_prompt = build_user_prompt(
        task_name="interview_requirements",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False),
        has_prd="Yes" if state.get("existing_prd") else "No"
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
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
            question=f"**Câu hỏi {current_index + 1}/{len(questions)}:**\n\n{question_text}",
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
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_generate_prd",
        tags=["ba", "prd", "generate"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="generate_prd"
    )
    
    user_prompt = build_user_prompt(
        task_name="generate_prd",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False)
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
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
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_update_prd",
        tags=["ba", "prd", "update"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="update_prd"
    )
    
    user_prompt = build_user_prompt(
        task_name="update_prd",
        existing_prd=json.dumps(existing_prd, ensure_ascii=False, indent=2),
        user_message=state["user_message"]
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
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
    """Node: Extract user stories from PRD."""
    logger.info(f"[BA] Extracting user stories...")
    
    prd = state.get("prd_draft") or state.get("existing_prd", {})
    
    if not prd:
        logger.error("[BA] No PRD available to extract stories from")
        return {
            "stories": [],
            "error": "No PRD available. Please create a PRD first."
        }
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_extract_stories",
        tags=["ba", "stories"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="extract_stories"
    )
    
    user_prompt = build_user_prompt(
        task_name="extract_stories",
        prd=json.dumps(prd, ensure_ascii=False, indent=2)
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
        )
        
        stories = parse_stories_response(response.content)
        logger.info(f"[BA] Extracted {len(stories)} user stories")
        
        return {"stories": stories}
        
    except Exception as e:
        logger.error(f"[BA] Failed to extract stories: {e}")
        return {
            "stories": [],
            "error": f"Failed to extract stories: {str(e)}"
        }


async def analyze_domain(state: BAState, agent=None) -> dict:
    """Node: Perform domain analysis."""
    logger.info(f"[BA] Analyzing domain...")
    
    agent_info = _get_agent_info(agent)
    llm, callbacks = _get_llm_with_callback(
        agent,
        trace_name="ba_domain_analysis",
        tags=["ba", "domain"],
        metadata={
            "project_id": state.get("project_id"),
            "task_id": state.get("task_id"),
        }
    )
    
    system_prompt = build_system_prompt(
        agent_name=agent_info["name"],
        personality_traits=agent_info["traits"],
        communication_style=agent_info["style"],
        task_name="domain_analysis"
    )
    
    user_prompt = build_user_prompt(
        task_name="domain_analysis",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False)
    )
    
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
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
    """Node: Save PRD/stories to file system and create artifacts."""
    logger.info(f"[BA] Saving artifacts...")
    
    result = {
        "action_taken": state.get("intent", "unknown"),
        "summary": "",
        "next_steps": []
    }
    
    project_files = agent.project_files if agent else None
    
    # Save PRD if exists
    if state.get("prd_draft") and project_files:
        try:
            prd_data = state["prd_draft"]
            await project_files.save_prd(prd_data)
            result["prd_saved"] = True
            
            project_name = prd_data.get("project_name", "Project")
            result["summary"] = f"PRD '{project_name}' saved successfully"
            result["next_steps"].extend([
                "Review PRD document",
                "Extract user stories if needed",
                "Share with stakeholders"
            ])
            
            # Send success message to user
            if agent:
                await agent.message_user(
                    event_type="response",
                    content=f"✅ **PRD Created Successfully**\n\n**Project:** {project_name}\n\n**Next steps:**\n" +
                            "\n".join(f"- {step}" for step in result["next_steps"]),
                    details={"prd": prd_data}
                )
            
            logger.info(f"[BA] PRD saved: {project_name}")
            
        except Exception as e:
            logger.error(f"[BA] Failed to save PRD: {e}", exc_info=True)
            result["error"] = f"Failed to save PRD: {str(e)}"
    
    # Save stories if exist
    if state.get("stories") and project_files:
        try:
            stories_data = state["stories"]
            await project_files.save_user_stories(stories_data)
            result["stories_saved"] = True
            
            stories_count = len(stories_data)
            result["summary"] = f"Extracted {stories_count} user stories"
            result["next_steps"].extend([
                "Review and prioritize stories",
                "Add stories to backlog",
                "Estimate effort for each story"
            ])
            
            # Send success message to user
            if agent:
                await agent.message_user(
                    event_type="response",
                    content=f"✅ **User Stories Extracted** ({stories_count} stories)\n\n**Next steps:**\n" +
                            "\n".join(f"- {step}" for step in result["next_steps"]),
                    details={"stories": stories_data}
                )
            
            logger.info(f"[BA] Saved {stories_count} user stories")
            
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
                content=f"📊 **Domain Analysis Complete**\n\n{state['analysis_text'][:2000]}",
                details={"analysis": state["analysis_text"]}
            )
    
    # PRD update
    if state.get("change_summary"):
        result["change_summary"] = state["change_summary"]
        
        if agent:
            await agent.message_user(
                event_type="response",
                content=f"✅ **PRD Updated**\n\n{state['change_summary']}",
                details={"prd": state.get("prd_draft")}
            )
    
    logger.info(f"[BA] Artifacts saved: {result['summary']}")
    
    return {
        "result": result,
        "is_complete": True
    }
