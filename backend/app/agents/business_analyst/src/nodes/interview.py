import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import BAState
from ..schemas import (
    QuestionsOutput
)
from app.agents.core.prompt_utils import (
    load_prompts_yaml,
    extract_agent_personality,
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
from app.core.config import settings
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

from .utils import _invoke_structured, _cfg, _sys_prompt, _user_prompt, _save_interview_state_to_question, _default_llm, REQUIRED_CATEGORIES

async def interview_requirements(state: BAState, agent=None) -> dict:
    """Uses structured output for reliable parsing"""
    conversation_context = state.get("conversation_context", "")
    if conversation_context:
        logger.info(f"[BA] Using conversation context ({len(conversation_context)} chars) for question generation")

    system_prompt = _sys_prompt(agent, "interview_requirements")
    user_prompt = _user_prompt(
        "interview_requirements",
        user_message=state["user_message"],
        collected_info=json.dumps(state.get("collected_info", {}), ensure_ascii=False),
        has_prd="Yes" if state.get("existing_prd") else "No",
        conversation_context=conversation_context
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    result = await _invoke_structured(
        llm=_default_llm,
        schema=QuestionsOutput,
        messages=messages,
        config=_cfg(state, "interview_requirements"),
        fallback_data={"questions": []}
    )

    # Convert Pydantic Question objects to dicts and enforce multichoice type
    questions = []
    for q in result.get("questions", []):
        if hasattr(q, "model_dump"):
            q_dict = q.model_dump()
        elif isinstance(q, dict):
            q_dict = q
        else:
            continue

        # FORCE multichoice type (LLM sometimes returns "open" despite schema default)
        if q_dict.get("type") != "multichoice":
            q_dict["type"] = "multichoice"
            # If no options, add default ones
            if not q_dict.get("options"):
                q_dict["options"] = ["Có", "Không", "Khác (vui lòng mô tả)"]

        questions.append(q_dict)

    logger.info(f"[BA] Generated {len(questions)} questions (all forced to multichoice)")

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

    # Build category info for prompt
    categories_to_ask = []
    for cat in missing_categories:
        cat_name = category_prompts.get(cat, cat)
        categories_to_ask.append(f'- category: "{cat}", về: {cat_name}')
    categories_str = "\n".join(categories_to_ask)

    # Use prompts from YAML (no hardcoded prompts)
    system_prompt = _sys_prompt(agent, "domain_research")
    user_prompt = _user_prompt(
        "domain_research",
        user_message=user_message,
        collected_info=json.dumps(collected_info, ensure_ascii=False),
        domain_research=json.dumps(domain_research, ensure_ascii=False)[:1500],
        categories_str=categories_str
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    result = await _invoke_structured(
        llm=_default_llm,
        schema=QuestionsOutput,
        messages=messages,
        config=_cfg(state, "domain_research"),
        fallback_data={"questions": []}
    )

    # Convert Pydantic Question objects to dicts
    questions = []
    for q in result.get("questions", []):
        if hasattr(q, "model_dump"):
            questions.append(q.model_dump())
        elif isinstance(q, dict):
            questions.append(q)

    logger.info(f"[BA] Generated {len(questions)} additional questions from research")

    return {
        "questions": questions,
        "research_loop_count": new_loop_count,
        "research_done": True,
        "domain_research": domain_research,
        "analysis_text": f"Researched: {missing_categories}",
    }




