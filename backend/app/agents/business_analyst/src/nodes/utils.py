import json
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from sqlmodel import Session, func, select
from sqlalchemy.orm.attributes import flag_modified

from app.agents.core.llm_factory import create_fast_llm, create_medium_llm, create_complex_llm

from ..state import BAState
from ..schemas import (

    FeatureClarityOutput,
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
from app.models import AgentQuestion, Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

# Retry configuration
MAX_LLM_RETRIES = 2  # Total 3 attempts (initial + 2 retries)
RETRY_BACKOFF_BASE = 1.0  # Linear backoff: 1s, 2s

# Step mappings for BA agent
# Pre-configured LLM instances (direct from factory)
_fast_llm = create_fast_llm()      # For intent analysis, simple tasks
_default_llm = create_medium_llm()  # For PRD, questions
_story_llm = create_complex_llm()   # For story creation




async def _invoke_structured(
    llm: BaseChatModel,
    schema,
    messages: list,
    config: dict = None,
    fallback_data: dict = None,
    max_retries: int = None
) -> dict:
    """Invoke LLM with structured output, with retry and fallback chain.
    
    Strategy:
    1. PRIMARY: with_structured_output() with retry on validation errors
    2. FALLBACK: Return fallback_data if all retries fail
    
    Args:
        llm: LLM instance
        schema: Pydantic schema class
        messages: List of messages
        config: Optional config dict for Langfuse
        fallback_data: Data to return if all retries fail
        max_retries: Maximum retry attempts (default: MAX_LLM_RETRIES from config)
    
    Returns:
        Parsed dict from schema
    """
    import asyncio
    from pydantic import ValidationError
    
    # Use global config if not specified
    if max_retries is None:
        max_retries = MAX_LLM_RETRIES
    
    last_error = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            structured_llm = llm.with_structured_output(schema)
            if config:
                result = await structured_llm.ainvoke(messages, config=config)
            else:
                result = await structured_llm.ainvoke(messages)
            
            # Check if result is None (LLM failed to return structured output)
            if result is None:
                logger.warning(f"[BA] LLM returned None (attempt {attempt + 1}/{max_retries + 1})")
                last_error = ValueError("LLM returned None")
                if attempt < max_retries:
                    wait_time = RETRY_BACKOFF_BASE * (attempt + 1)
                    logger.info(f"[BA] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                # Last attempt failed
                if fallback_data:
                    logger.info("[BA] All retries exhausted, using fallback data")
                    return fallback_data
                raise last_error
            
            # Success - return result
            return result.model_dump()
            
        except ValidationError as e:
            # Pydantic validation error - LLM returned wrong structure
            last_error = e
            logger.warning(f"[BA] Structured output validation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                wait_time = RETRY_BACKOFF_BASE * (attempt + 1)
                logger.info(f"[BA] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            # Last attempt failed
            if fallback_data:
                logger.info("[BA] All retries exhausted, using fallback data")
                return fallback_data
            raise
            
        except Exception as e:
            # Other errors (network, API, etc.) - let LangChain's auto-retry handle it
            # Only catch and retry if it's a known retryable error
            error_str = str(e).lower()
            is_retryable = any(keyword in error_str for keyword in [
                "timeout", "connection", "rate limit", "429", "500", "503", "504"
            ])
            
            last_error = e
            if is_retryable and attempt < max_retries:
                wait_time = RETRY_BACKOFF_BASE * (attempt + 1)
                logger.warning(f"[BA] Retryable error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                logger.info(f"[BA] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            
            # Non-retryable error or last attempt
            logger.warning(f"[BA] LLM call failed: {e}")
            if fallback_data:
                logger.info("[BA] Using fallback data")
                return fallback_data
            raise
    
    # Should never reach here, but just in case
    if fallback_data:
        logger.info("[BA] Fallback after all retries")
        return fallback_data
    raise last_error or Exception("Unknown error in _invoke_structured")



def _classify_crud_operation(user_message: str) -> tuple:
    """Classify user message into CRUD operation and confidence.
    
    Returns (operation, confidence) where:
    - operation: "CREATE" | "READ" | "UPDATE" | "DELETE" | "UNKNOWN"
    - confidence: 0.0-1.0 (how confident we are)
    
    Examples:
    - "xóa epic Notifications" → ("DELETE", 1.0)
    - "sửa story EPIC-001-US-003" → ("UPDATE", 1.0)
    - "thêm menu ở homepage" → ("CREATE", 0.9)
    - "trang about" → ("UNKNOWN", 0.0)
    """
    user_msg_lower = user_message.lower()
    
    # DELETE - highest priority (most explicit)
    delete_keywords = ["xóa", "delete", "remove", "bỏ", "loại bỏ", "gỡ bỏ"]
    if any(kw in user_msg_lower for kw in delete_keywords):
        return ("DELETE", 1.0)
    
    # UPDATE - second priority
    update_keywords = ["sửa", "edit", "update", "chỉnh", "thay đổi", "modify", "đổi"]
    if any(kw in user_msg_lower for kw in update_keywords):
        return ("UPDATE", 1.0)
    
    # CREATE - third priority (can be ambiguous with refinement)
    create_keywords = ["thêm", "add", "tạo", "create", "thêm mới", "bổ sung"]
    if any(kw in user_msg_lower for kw in create_keywords):
        # Lower confidence because "thêm" can mean refine existing OR create new
        return ("CREATE", 0.8)
    
    # READ - rarely used in BA context
    read_keywords = ["xem", "hiển thị", "show", "view", "list"]
    if any(kw in user_msg_lower for kw in read_keywords):
        return ("READ", 0.6)
    
    return ("UNKNOWN", 0.0)




def _extract_intent_keywords(user_message: str) -> list:
    """Extract key intent keywords from user message for matching.
    
    Returns list of meaningful keywords (nouns, verbs) excluding common words.
    
    Examples:
    - "thêm menu cho homepage" → ["menu", "homepage"]
    - "thêm filter giá sản phẩm" → ["filter", "giá", "sản phẩm"]
    """
    import re
    
    # Remove Vietnamese diacritics for better matching (optional, keep original for now)
    user_msg_lower = user_message.lower()
    
    # Remove common action words (they don't help matching)
    stop_words = {
        "thêm", "add", "tạo", "create", "sửa", "edit", "update", "xóa", "delete", "remove",
        "cho", "for", "vào", "into", "to", "the", "a", "an", "của", "in", "on", "at",
        "là", "is", "are", "và", "and", "or", "với", "with"
    }
    
    # Extract words (alphanumeric + Vietnamese)
    words = re.findall(r'[\w]+', user_msg_lower, re.UNICODE)
    
    # Filter: remove stop words, keep words with length >= 3
    keywords = [w for w in words if w not in stop_words and len(w) >= 3]
    
    return keywords




async def _check_request_clarity(
    user_message: str, 
    existing_epics: list, 
    existing_prd: dict = None,
    agent=None
) -> tuple:
    """Check if user request relates to existing features or is completely new.
    
    Uses LLM to intelligently analyze the request against existing features.
    
    Returns (is_clear, missing_details) where:
    - is_clear: True if this is a refinement of existing feature (can proceed)
    - missing_details: List of clarification questions if this is a NEW feature
    
    Logic:
    - REFINEMENT of existing feature → proceed with update (is_clear=True)
    - NEW feature not covered by existing PRD/epics → ask clarification (is_clear=False)
    """
    # Build context about existing features
    existing_features = []
    if existing_prd and existing_prd.get("features"):
        existing_features = [f.get("name", "") for f in existing_prd.get("features", []) if f.get("name")]
    
    existing_epic_info = []
    for epic in existing_epics:
        epic_title = epic.get("title", "")
        epic_domain = epic.get("domain", "")
        stories = epic.get("stories", [])
        story_titles = [s.get("title", "")[:50] for s in stories[:5]]  # First 5 stories
        existing_epic_info.append({
            "title": epic_title,
            "domain": epic_domain,
            "sample_stories": story_titles
        })
    
    # Build prompts from YAML
    system_prompt = _sys_prompt(agent, "check_feature_clarity")
    user_prompt = _user_prompt(
        "check_feature_clarity",
        user_message=user_message,
        existing_features=json.dumps(existing_features, ensure_ascii=False) if existing_features else "Chưa có PRD",
        existing_epics=json.dumps(existing_epic_info, ensure_ascii=False, indent=2) if existing_epic_info else "Chưa có Epics"
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Default fallback - if no existing features, assume new feature
    default_questions = [
        "Tính năng này dành cho ai sử dụng? (visitor, customer, admin, ...)",
        "Bạn có thể mô tả chi tiết hơn về tính năng này không?",
        "Tính năng này cần những chức năng gì cụ thể?"
    ]
    
    fallback_data = {
        "is_new_feature": not existing_features and not existing_epics,  # New if no existing context
        "related_existing_feature": None,
        "has_specific_change": False,
        "clarification_questions": default_questions if (not existing_features and not existing_epics) else [],
        "reasoning": "Fallback: Không có context về features đã có" if (not existing_features and not existing_epics) else "Fallback: Có features đã có, giả định là refinement"
    }
    
    try:
        # Get langfuse callback safely (requires trace_name parameter)
        langfuse_handler = None
        if agent and hasattr(agent, 'get_langfuse_callback'):
            try:
                langfuse_handler = agent.get_langfuse_callback("check_feature_clarity")
            except Exception:
                pass  # Ignore langfuse errors
        
        config = _cfg({"langfuse_handler": langfuse_handler}, "check_feature_clarity") if langfuse_handler else {}
        
        result = await _invoke_structured(
            llm=_fast_llm,
            schema=FeatureClarityOutput,
            messages=messages,
            config=config,
            fallback_data=fallback_data
        )
        
        is_new = result.get("is_new_feature", False)
        has_specific_change = result.get("has_specific_change", False)
        questions = result.get("clarification_questions", [])
        reasoning = result.get("reasoning", "")
        related = result.get("related_existing_feature")
        
        logger.info(f"[BA] Feature clarity check: is_new={is_new}, has_specific_change={has_specific_change}, related={related}, reasoning={reasoning[:100]}")
        
        # CASE 1: New feature → need clarification
        if is_new:
            return False, questions if questions else default_questions, None
        
        # CASE 2: Existing feature WITH specific change → can proceed
        if not is_new and has_specific_change:
            return True, [], related
        
        # CASE 3: Existing feature WITHOUT specific change → notify clearly and ask what to do
        if not is_new and not has_specific_change:
            # Use LLM-generated questions if available (should include clear notification)
            if questions:
                return False, questions, related
            
            # Fallback: Clear notification about duplicate feature with ONE simple question
            existing_feature_questions = [
                f"Tính năng '{related}' đã có trong hệ thống rồi. Bạn muốn thay đổi/chỉnh sửa phần nào của tính năng hiện tại?"
            ]
            return False, existing_feature_questions, related
        
        return True, [], related
            
    except Exception as e:
        logger.warning(f"[BA] Feature clarity check failed: {e}, using simple fallback")
        # Simple fallback: SHORT message (< 5 words) = always ask clarification
        # Examples: "thêm trang about" (3 words), "thêm menu" (2 words)
        word_count = len(user_message.split())
        if word_count < 5:
            # Message too short/vague → always ask clarification
            vague_questions = [
                "Bạn muốn trang/tính năng này có những nội dung gì?",
                "Tính năng này dành cho ai sử dụng? (khách hàng, admin, ...)",
                "Có chức năng cụ thể nào bạn muốn thêm không?"
            ]
            return False, vague_questions, None
        return True, [], None  # Longer message = assume clear enough


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




def _is_single_story_edit(user_msg_lower: str) -> bool:
    """Detect if user wants to edit a SINGLE specific story.
    
    Returns True if message contains:
    1. Story edit keywords (sửa story, edit story, etc.)
    2. Specific story identifier (quoted title OR story ID pattern)
    3. Specific field change (requirements, acceptance criteria, etc.)
    """
    # Must have edit keyword
    edit_keywords = ["sửa story", "edit story", "chỉnh story", "update story", "thay đổi story"]
    has_edit = any(kw in user_msg_lower for kw in edit_keywords)
    if not has_edit:
        return False
    
    # Must have specific story identifier
    # Check for quoted story title (e.g., 'sửa story "As an administrator..."')
    import re
    has_quoted_title = bool(re.search(r'["\']as\s+a[n]?\s+', user_msg_lower))
    has_story_id = bool(re.search(r'epic-\d+-us-\d+', user_msg_lower))
    has_specific_story = has_quoted_title or has_story_id
    
    if not has_specific_story:
        return False
    
    # Must have specific field change
    field_keywords = [
        "requirement", "acceptance", "criteria", "bỏ", "xóa", "thêm", "add", "remove",
        "delete", "loại bỏ", "thay đổi", "change", "sửa đổi"
    ]
    has_field_change = any(kw in user_msg_lower for kw in field_keywords)
    
    return has_field_change




def _sys_prompt(agent, task: str) -> str:
    """Build system prompt with agent personality.
    
    Uses .replace() instead of .format() to avoid issues with JSON examples in prompts.
    Pattern from Developer V2.
    """
    task_config = PROMPTS.get("tasks", {}).get(task, {})
    template = task_config.get("system_prompt", "")
    
    # Replace shared context
    shared = PROMPTS.get("shared_context", {})
    for key, value in shared.items():
        template = template.replace(f"{{shared_context.{key}}}", str(value))
    
    # Get agent personality or defaults
    personality = extract_agent_personality(agent) if agent else {}
    for key, value in BA_DEFAULTS.items():
        if key not in personality or not personality.get(key):
            personality[key] = value
    
    # Replace personality placeholders
    for key, value in personality.items():
        template = template.replace("{" + key + "}", str(value) if value else "")
    
    return template




def _user_prompt(task: str, **kwargs) -> str:
    """Build user prompt for LLM.
    
    Uses .replace() instead of .format() to avoid issues with JSON examples in prompts.
    Pattern from Developer V2.
    """
    task_config = PROMPTS.get("tasks", {}).get(task, {})
    template = task_config.get("user_prompt", "")
    
    # Replace all kwargs
    for key, value in kwargs.items():
        template = template.replace("{" + key + "}", str(value) if value else "")
    
    return template




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




