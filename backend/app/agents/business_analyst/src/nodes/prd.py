import json
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import BAState
from ..schemas import (
    QuestionsOutput,
    PRDOutput,
    PRDUpdateOutput
)
from app.agents.core.prompt_utils import (
    load_prompts_yaml
)

# Load prompts from YAML (same pattern as Developer V2)
PROMPTS = load_prompts_yaml(Path(__file__).parent.parent / "prompts.yaml")

# Default values for BA agent persona
BA_DEFAULTS = {
    "name": "Business Analyst",
    "role": "Business Analyst / Requirements Specialist",
    "goal": "Phân tích requirements, tạo PRD và user stories",
    "description": "Chuyên gia phân tích yêu cầu phần mềm",
    "personality": "Thân thiện, kiên nhẫn, giỏi lắng nghe",
    "communication_style": "Đơn giản, dễ hiểu, tránh thuật ngữ kỹ thuật",
}
from app.core.db import engine

logger = logging.getLogger(__name__)

from .utils import  _invoke_structured, _cfg, _sys_prompt, _user_prompt, _save_interview_state_to_question, _default_llm

async def generate_prd(state: BAState, agent=None) -> dict:
    """Node: Generate PRD document.

    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    logger.info(f"[BA] Generating PRD...")

    system_prompt = _sys_prompt(agent, "generate_prd")
    user_prompt = _user_prompt(
        "generate_prd",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False)
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    # Build smart fallback from collected info (used when LLM fails)
    collected_info = state.get("collected_info", {})
    answers = collected_info.get("interview_answers", [])

    # Extract info from answers
    fallback_users = []
    fallback_features = []
    for ans in answers:
        cat = ans.get("category", "")
        answer_text = ans.get("answer", "")
        if cat == "target_users" and answer_text:
            fallback_users = [u.strip() for u in answer_text.split(",")]
        elif cat == "main_features" and answer_text:
            # Create basic features from answer
            for feat in answer_text.split(","):
                feat = feat.strip()
                if feat:
                    fallback_features.append({
                        "name": feat[:50],
                        "description": feat,
                        "priority": "medium",
                        "requirements": []
                    })

    fallback = {
        "project_name": state["user_message"][:50] if state.get("user_message") else "New Project",
        "version": "1.0",
        "overview": state.get("user_message", "")[:200],
        "objectives": ["Xây dựng sản phẩm theo yêu cầu của khách hàng"],
        "target_users": fallback_users[:5] if fallback_users else ["Người dùng chung"],
        "features": fallback_features[:7] if fallback_features else [{"name": "Core Feature", "description": "Main functionality", "priority": "high", "requirements": []}],
        "constraints": [],
        "success_metrics": [],
        "risks": [],
        "message": "⚠️ PRD được tạo từ thông tin cơ bản (LLM không phản hồi). Vui lòng kiểm tra và bổ sung thêm chi tiết."
    }

    result = await _invoke_structured(
        llm=_default_llm,
        schema=PRDOutput,
        messages=messages,
        config=_cfg(state, "generate_prd"),
        fallback_data=fallback
    )

    # Extract message and create PRD dict (message is separate from PRD content)
    message = result.pop("message", "")
    prd = result

    logger.info(f"[BA] PRD generated: {prd.get('project_name', 'Untitled')}")

    return {"prd_draft": prd, "prd_message": message}




async def update_prd(state: BAState, agent=None) -> dict:
    """Node: Update existing PRD.

    Uses structured output for reliable parsing (Developer V2 pattern).

    FLOW:
    1. Check if this is a NEW feature request → ask clarification if needed
    2. If refinement of existing feature → proceed with update
    """
    logger.info(f"[BA] Updating existing PRD...")

    existing_prd = state.get("existing_prd", {})
    existing_epics = state.get("epics", [])
    user_message = state.get("user_message", "")
    skip_clarity_check = state.get("skip_clarity_check", False)

    if not existing_prd:
        logger.warning("[BA] No existing PRD to update, creating new one")
        return await generate_prd(state, agent)

    # ====================================================================================
    # STEP 0: CLASSIFY CRUD OPERATION
    # ====================================================================================
    crud_operation, crud_confidence = _classify_crud_operation(user_message)
    logger.info(f"[BA] CRUD classification: {crud_operation} (confidence: {crud_confidence:.2f})")

    # ====================================================================================
    # STEP 1: CHECK CLARITY - Ask clarification ONLY for CREATE operations on NEW features
    # DELETE/UPDATE operations are always clear (user explicitly states what to modify/remove)
    # ====================================================================================
    should_skip_clarity = (
        skip_clarity_check or
        crud_operation == "DELETE" or
        crud_operation == "UPDATE"
    )

    if should_skip_clarity:
        if crud_operation == "DELETE":
            logger.info(f"[BA] Skipping clarity check (DELETE operation - always clear)")
        elif crud_operation == "UPDATE":
            logger.info(f"[BA] Skipping clarity check (UPDATE operation - always clear)")
        else:
            logger.info(f"[BA] Skipping clarity check (resuming from clarification)")
        is_clear = True
        missing_details = []
        related_feature = None
    else:
        # Only CREATE operations need clarity check
        logger.info(f"[BA] CREATE operation detected - checking if NEW feature or REFINEMENT of existing")
        is_clear, missing_details, related_feature = await _check_request_clarity(
            user_message, existing_epics, existing_prd, agent
        )

    if not is_clear and agent:
        # Request needs clarification - either NEW feature or EXISTING without specific change
        logger.info(f"[BA] Clarification needed (related_feature={related_feature}): {missing_details}")

        # Build context message
        if related_feature:
            # EXISTING feature → use simple open question (missing_details is list of strings)
            context_msg = f"Tính năng \"{related_feature}\" đã có trong hệ thống. Mình cần biết thêm chi tiết để cập nhật."
            batch_questions = [
                {
                    "question_text": detail,
                    "question_type": "open",
                    "options": None,
                    "allow_multiple": False,
                    "context": context_msg if i == 0 else None,
                }
                for i, detail in enumerate(missing_details)
            ]
        else:
            # NEW feature → generate multichoice questions specific to this feature
            logger.info(f"[BA] NEW feature detected, generating feature-specific multichoice questions...")
            context_msg = f"Để mình hiểu rõ hơn về \"{user_message}\", bạn cho mình biết thêm nhé!"

            # Generate multichoice questions using LLM (specific to the new feature, not general interview)
            try:
                system_prompt = _sys_prompt(agent, "generate_feature_questions")
                user_prompt = _user_prompt(
                    "generate_feature_questions",
                    user_message=user_message
                )

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]

                result = await _invoke_structured(
                    llm=_default_llm,
                    schema=QuestionsOutput,
                    messages=messages,
                    config=_cfg(state, "generate_feature_questions"),
                    fallback_data={"questions": []}
                )

                generated_questions = []
                for q in result.get("questions", []):
                    if hasattr(q, "model_dump"):
                        q_dict = q.model_dump()
                    elif isinstance(q, dict):
                        q_dict = q
                    else:
                        continue

                    # Ensure multichoice type
                    if q_dict.get("type") != "multichoice":
                        q_dict["type"] = "multichoice"
                    if not q_dict.get("options"):
                        q_dict["options"] = ["Có", "Không", "Khác (vui lòng mô tả)"]

                    generated_questions.append(q_dict)

                if generated_questions:
                    batch_questions = [
                        {
                            "question_text": q["text"],
                            "question_type": q.get("type", "multichoice"),
                            "options": q.get("options"),
                            "allow_multiple": q.get("allow_multiple", False),
                            "context": context_msg if i == 0 else None,
                        }
                        for i, q in enumerate(generated_questions)
                    ]
                else:
                    raise ValueError("No questions generated")

            except Exception as e:
                logger.warning(f"[BA] Failed to generate feature-specific questions: {e}, using fallback")
                # Fallback: use simple open questions
                batch_questions = [
                    {
                        "question_text": detail,
                        "question_type": "open",
                        "options": None,
                        "allow_multiple": False,
                        "context": context_msg if i == 0 else None,
                    }
                    for i, detail in enumerate(missing_details)
                ]

        logger.info(f"[BA] Sending {len(batch_questions)} clarification questions via question cards...")

        # Send questions using question cards (same as interview flow)
        question_ids = await agent.ask_multiple_clarification_questions(batch_questions)

        # Save interview state with original_intent so RESUME knows to continue prd_update
        with Session(engine) as session:
            interview_state = {
                "original_intent": "prd_update",  # IMPORTANT: Mark this as prd_update flow
                "user_message": user_message,
                "existing_prd": existing_prd,
                "epics": existing_epics,
                "questions": batch_questions,
                "question_ids": [str(qid) for qid in question_ids],
                "related_feature": related_feature,
            }
            _save_interview_state_to_question(session, question_ids[0], interview_state)
            logger.info(f"[BA] Saved prd_update state for RESUME flow")

        # Return early - STOP the flow (waiting for user answers via question cards)
        return {
            "needs_clarification": True,
            "waiting_for_answer": True,
            "question_ids": [str(qid) for qid in question_ids],
            "is_complete": True,  # Mark complete to stop flow
            "result": {
                "summary": f"Feature '{related_feature}' already exists - asked for specific changes" if related_feature else "New feature request - asked for clarification",
                "task_completed": False  # Don't release ownership - waiting for user
            }
        }

    # ====================================================================================
    # STEP 2: Proceed with PRD update (feature has specific change to make)
    # ====================================================================================

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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    result = await _invoke_structured(
        llm=_default_llm,
        schema=PRDUpdateOutput,
        messages=messages,
        config=_cfg(state, "update_prd"),
        fallback_data={
            "updated_prd": existing_prd,
            "change_summary": "Không thể cập nhật PRD",
            "message": ""
        }
    )

    logger.info(f"[BA] PRD updated: {result.get('change_summary', 'Changes applied')[:100]}")

    # Extract updated_prd (which is a PRDOutput object or dict)
    updated_prd = result.get("updated_prd", {})
    if hasattr(updated_prd, "model_dump"):
        updated_prd = updated_prd.model_dump()

    # Remove message from PRD dict if it exists (it's a separate field)
    if isinstance(updated_prd, dict):
        updated_prd.pop("message", None)

    return {
        "prd_draft": updated_prd,
        "change_summary": result.get("change_summary", ""),
        "prd_message": result.get("message", "")
    }




