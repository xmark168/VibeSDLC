import json
import logging
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from sqlmodel import Session, func, select
from sqlalchemy.orm.attributes import flag_modified

from .state import BAState
from .schemas import (
    IntentOutput,
    QuestionsOutput,
    PRDOutput,
    PRDUpdateOutput,
    DocumentAnalysisOutput,
    EpicsOnlyOutput,
    StoriesForEpicOutput,
    FullStoriesOutput,
    VerifyStoryOutput,
    DocumentFeedbackOutput,
    SingleStoryEditOutput,
    FeatureClarityOutput,
)
from app.agents.core.prompt_utils import (
    load_prompts_yaml,
    extract_agent_personality,
)

# Load prompts from YAML (same pattern as Developer V2)
PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")

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
from app.models import AgentQuestion, Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

# =============================================================================
# LLM CONFIGURATION (Following Developer V2 pattern)
# =============================================================================

# API configuration
ANTHROPIC_API_BASE = os.getenv("ANTHROPIC_API_BASE", "https://ai.megallm.io")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

# Model tiers (like Dev V2)
MODELS = {
    "fast": "claude-sonnet-4-5-20250929",      # Intent, simple tasks
    "default": "claude-sonnet-4-5-20250929",   # PRD, questions
    "complex": "claude-sonnet-4-5-20250929",   # Stories (can upgrade to opus if needed)
}


def _get_llm(tier: str = "default", temperature: float = 0.2, timeout: int = 60) -> BaseChatModel:
    """Get LLM instance by tier. Uses ChatAnthropic for Claude models."""
    model = MODELS.get(tier, MODELS["default"])
    
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": 16384,
        "timeout": timeout,
        "max_retries": 3,
    }
    if ANTHROPIC_API_BASE:
        kwargs["base_url"] = ANTHROPIC_API_BASE
    if ANTHROPIC_API_KEY:
        kwargs["api_key"] = ANTHROPIC_API_KEY
    
    return ChatAnthropic(**kwargs)


# Pre-configured LLM instances
_fast_llm = _get_llm("fast", temperature=0.1, timeout=30)
_default_llm = _get_llm("default", temperature=0.2, timeout=90)
_story_llm = _get_llm("complex", temperature=0.2, timeout=180)


async def _invoke_structured(
    llm: BaseChatModel,
    schema,
    messages: list,
    config: dict = None,
    fallback_data: dict = None
) -> dict:
    """Invoke LLM with structured output, with fallback chain.
    
    Pattern from Developer V2:
    1. PRIMARY: with_structured_output() - 99% reliable
    2. FALLBACK: Return fallback_data if provided
    
    Args:
        llm: LLM instance
        schema: Pydantic schema class
        messages: List of messages
        config: Optional config dict for Langfuse
        fallback_data: Data to return if structured output fails
    
    Returns:
        Parsed dict from schema
    """
    try:
        structured_llm = llm.with_structured_output(schema)
        if config:
            result = await structured_llm.ainvoke(messages, config=config)
        else:
            result = await structured_llm.ainvoke(messages)
        return result.model_dump()
    except Exception as e:
        logger.warning(f"[BA] Structured output failed: {e}")
        if fallback_data:
            logger.info("[BA] Using fallback data")
            return fallback_data
        raise

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
        
        # CASE 3: Existing feature WITHOUT specific change → notify and ask what to change
        if not is_new and not has_specific_change:
            existing_feature_questions = [
                f"Tính năng '{related}' đã có trong hệ thống rồi. Bạn muốn bổ sung/thay đổi gì cụ thể?",
                "Ví dụ: thêm section mới, thay đổi layout, bổ sung thông tin gì?"
            ]
            return False, questions if questions else existing_feature_questions, related
        
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


async def analyze_intent(state: BAState, agent=None) -> dict:
    """Node: Analyze user intent and classify task.
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    Enhanced with dynamic context about existing PRD features and epics.
    """
    logger.info(f"[BA] Analyzing intent: {state['user_message'][:80]}...")
    
    # BUILD DYNAMIC CONTEXT about existing PRD features and epics
    existing_prd = state.get("existing_prd") or {}  # Handle None case
    existing_epics = state.get("epics", [])
    
    # Format PRD features outline (show what topics are already covered)
    existing_features_context = ""
    if existing_prd and existing_prd.get("features"):
        features_list = []
        for feat in existing_prd.get("features", [])[:10]:  # Show max 10 features
            feat_name = feat.get("name", "Unknown")
            features_list.append(f"  - {feat_name}")
        
        existing_features_context = f"""Existing PRD features ({len(existing_prd.get('features', []))} total):
{chr(10).join(features_list)}"""
    else:
        existing_features_context = "Existing PRD features: None (no PRD yet)"
    
    # Format Epics/Stories outline (show what implementation already exists)
    existing_epics_context = ""
    if existing_epics:
        epics_list = []
        for epic in existing_epics[:8]:  # Show max 8 epics
            epic_title = epic.get("title", "Unknown")
            epic_domain = epic.get("domain", "General")
            story_count = len(epic.get("stories", []))
            epics_list.append(f"  - {epic_domain}: {epic_title} ({story_count} stories)")
        
        existing_epics_context = f"""Existing Epics/Stories ({len(existing_epics)} epics total):
{chr(10).join(epics_list)}"""
    else:
        existing_epics_context = "Existing Epics/Stories: None (no stories created yet)"
    
    # Safe logging with None check
    prd_features_count = len(existing_prd.get('features', [])) if existing_prd else 0
    logger.info(f"[BA] Context for intent analysis: {prd_features_count} PRD features, {len(existing_epics)} epics")
    
    system_prompt = _sys_prompt(agent, "analyze_intent")
    user_prompt = _user_prompt(
        "analyze_intent",
        user_message=state["user_message"],
        has_prd="Yes" if existing_prd else "No",
        has_info="Yes" if state.get("collected_info") else "No",
        existing_features_context=existing_features_context,
        existing_epics_context=existing_epics_context,
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Smart fallback based on keywords in user message
    user_msg_lower = state["user_message"].lower()
    if any(kw in user_msg_lower for kw in ["phê duyệt story", "phê duyệt stories", "approve story", "approve stories", "duyệt story"]):
        fallback_intent = "stories_approve"
        fallback_reason = "Keyword-based: approve stories"
    elif any(kw in user_msg_lower for kw in ["phê duyệt prd", "prd ok", "tạo story", "tạo stories", "extract story"]):
        fallback_intent = "extract_stories"
        fallback_reason = "Keyword-based: extract stories from PRD"
    # Detect SINGLE story edit: mentions specific story + specific field change
    elif _is_single_story_edit(user_msg_lower):
        fallback_intent = "story_edit_single"
        fallback_reason = "Keyword-based: single story edit (specific story + specific change)"
    elif any(kw in user_msg_lower for kw in ["sửa story", "update story", "chỉnh story", "thay đổi story"]):
        fallback_intent = "stories_update"
        fallback_reason = "Keyword-based: update stories"
    elif any(kw in user_msg_lower for kw in ["sửa prd", "update prd", "chỉnh prd", "thêm feature mới", "feature mới"]):
        fallback_intent = "prd_update"
        fallback_reason = "Keyword-based: update PRD"
    # NEW: Detect refinement keywords (thêm menu, thêm button, thêm filter, etc.) → stories_update
    elif any(kw in user_msg_lower for kw in ["thêm", "bổ sung", "add", "thay đổi", "sửa", "chỉnh"]) and existing_epics:
        # User wants to refine existing features (has epics) → stories_update
        fallback_intent = "stories_update"
        fallback_reason = "Keyword-based: refine existing feature (has epics)"
    elif state.get("existing_prd") and not existing_epics:
        # Has PRD but NO epics yet → extract stories
        fallback_intent = "extract_stories"
        fallback_reason = "Has PRD, no epics - extract stories first"
    elif state.get("existing_prd") and not state.get("collected_info"):
        # Has PRD + epics but user message vague → default to stories_update (safer than extract_stories)
        fallback_intent = "stories_update"
        fallback_reason = "Has PRD+epics, vague request - default to stories_update"
    else:
        fallback_intent = "interview"
        fallback_reason = "Default fallback to interview"
    
    result = await _invoke_structured(
        llm=_fast_llm,
        schema=IntentOutput,
        messages=messages,
        config=_cfg(state, "analyze_intent"),
        fallback_data={"intent": fallback_intent, "reasoning": fallback_reason}
    )
    
    logger.info(f"[BA] Intent classified: {result['intent']} (reasoning: {result.get('reasoning', '')[:100]})")
    return result


async def analyze_document_content(document_text: str, agent=None) -> dict:
    """Analyze uploaded document to extract requirements information.
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    
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
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    fallback = {
        "document_type": "partial_requirements",
        "detected_doc_kind": "",
        "collected_info": {},
        "is_comprehensive": False,
        "completeness_score": 0.0,
        "summary": "",
        "extracted_items": [],
        "missing_info": []
    }
    
    result = await _invoke_structured(
        llm=_default_llm,
        schema=DocumentAnalysisOutput,
        messages=messages,
        config={"run_name": "analyze_document"},
        fallback_data=fallback
    )
    
    # Convert collected_info from Pydantic model to dict, filter None values
    collected_info_raw = result.get("collected_info", {})
    if hasattr(collected_info_raw, "model_dump"):
        collected_info_raw = collected_info_raw.model_dump()
    collected_info = {
        k: v for k, v in collected_info_raw.items() 
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
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        result = await _invoke_structured(
            llm=_default_llm,
            schema=DocumentFeedbackOutput,
            messages=messages,
            fallback_data={"message": _DOC_FALLBACK_MESSAGES.get(document_type, _DOC_FALLBACK_MESSAGES["partial_requirements"])}
        )
        
        message = result.get("message", "")
        logger.info(f"[BA] Generated document feedback: {message[:100]}...")
        return message
        
    except Exception as e:
        logger.warning(f"[BA] generate_document_feedback failed: {e}, using fallback")
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
    """Node: Generate clarification questions.
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    logger.info(f"[BA] Generating interview questions...")
    
    # Get conversation context from Team Leader delegation
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
    
    # Convert Pydantic Question objects to dicts
    questions = []
    for q in result.get("questions", []):
        if hasattr(q, "model_dump"):
            questions.append(q.model_dump())
        elif isinstance(q, dict):
            questions.append(q)
    
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
    # STEP 1: CHECK CLARITY - Ask clarification if this is a NEW feature or existing without specific change
    # Skip if we're resuming from a previous clarification (skip_clarity_check=True)
    # ====================================================================================
    if skip_clarity_check:
        logger.info(f"[BA] Skipping clarity check (resuming from clarification)")
        is_clear = True
        missing_details = []
        related_feature = None
    else:
        is_clear, missing_details, related_feature = await _check_request_clarity(
            user_message, existing_epics, existing_prd, agent
        )
    
    if not is_clear and agent:
        # Request needs clarification - either NEW feature or EXISTING without specific change
        logger.info(f"[BA] Clarification needed (related_feature={related_feature}): {missing_details}")
        
        # Build context message
        if related_feature:
            context_msg = f"Tính năng \"{related_feature}\" đã có trong hệ thống. Mình cần biết thêm chi tiết để cập nhật."
        else:
            context_msg = f"Để mình hiểu rõ hơn về \"{user_message}\", bạn cho mình biết thêm nhé!"
        
        # Format questions for batch API (use question cards like interview flow)
        batch_questions = [
            {
                "question_text": detail,
                "question_type": "open",
                "options": None,
                "allow_multiple": False,
                "context": context_msg if i == 0 else None,  # Only add context to first question
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


async def _generate_stories_for_epic(
    epic: dict, 
    prd: dict, 
    all_epic_ids: list, 
    state: BAState, 
    agent=None
) -> dict:
    """Generate stories for a single Epic (used in parallel batch processing).
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    epic_id = epic.get("id", "EPIC-???")
    epic_title = epic.get("title", "Unknown")
    
    logger.info(f"[BA] Generating stories for Epic: {epic_title}")
    
    # Find related features from PRD
    feature_refs = epic.get("feature_refs", [])
    prd_features = []
    for feature in prd.get("features", []):
        feature_name = feature.get("name") if isinstance(feature, dict) else str(feature)
        if feature_name in feature_refs:
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
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    logger.info(f"[BA] Calling LLM for Epic '{epic_title}' with {len(prd_features)} features")
    
    result = await _invoke_structured(
        llm=_story_llm,
        schema=StoriesForEpicOutput,
        messages=messages,
        config=_cfg(state, f"generate_stories_{epic_id}"),
        fallback_data={"stories": []}
    )
    
    # Convert Pydantic UserStory objects to dicts
    stories = []
    for s in result.get("stories", []):
        if hasattr(s, "model_dump"):
            story_dict = s.model_dump()
        elif isinstance(s, dict):
            story_dict = s
        else:
            continue
        # Add epic info to each story
        story_dict["epic_id"] = epic_id
        story_dict["epic_title"] = epic_title
        stories.append(story_dict)
    
    logger.info(f"[BA] Generated {len(stories)} stories for Epic '{epic_title}'")
    return {"epic_id": epic_id, "stories": stories}


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
        # Uses structured output for reliable parsing
        # =============================================
        logger.info("[BA] Phase 1: Extracting Epics structure...")
        
        system_prompt = _sys_prompt(agent, "extract_epics_only")
        user_prompt = _user_prompt(
            "extract_epics_only",
            prd=json.dumps(prd, ensure_ascii=False, indent=2)
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        epics_result = await _invoke_structured(
            llm=_fast_llm,
            schema=EpicsOnlyOutput,
            messages=messages,
            config=_cfg(state, "extract_epics_only"),
            fallback_data={"epics": [], "message_template": "", "approval_template": ""}
        )
        
        # Convert Pydantic Epic objects to dicts
        epics = []
        for e in epics_result.get("epics", []):
            if hasattr(e, "model_dump"):
                epics.append(e.model_dump())
            elif isinstance(e, dict):
                epics.append(e)
        
        message_template = epics_result.get("message_template", "")
        approval_template = epics_result.get("approval_template", "")
        
        if not epics:
            logger.warning("[BA] No epics extracted, falling back to single call")
            return await _extract_stories_single_call(state, agent, prd)
        
        logger.info(f"[BA] Phase 1 complete: {len(epics)} Epics extracted, message_template: {message_template[:50] if message_template else 'none'}...")
        
        # =============================================
        # PHASE 2: Generate stories for each Epic IN PARALLEL
        # =============================================
        logger.info(f"[BA] Phase 2: Generating stories for {len(epics)} Epics in parallel...")
        
        all_epic_ids = [epic.get("id", "") for epic in epics]
        
        # Use semaphore to limit concurrent LLM calls (avoid rate limiting)
        # Increased from 5 to 7 to process all epics in one batch
        MAX_CONCURRENT_LLM_CALLS = 7
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
        
        async def _generate_with_semaphore(epic):
            async with semaphore:
                return await _generate_stories_for_epic(epic, prd, all_epic_ids, state, agent)
        
        # Create tasks with rate limiting
        tasks = [_generate_with_semaphore(epic) for epic in epics]
        
        # Run all epics in parallel (limited by semaphore)
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
        
        # Use hardcoded messages (LLM-generated templates were unreliable - often mentioned "Phase 2" incorrectly)
        message = f"🎉 Đã tạo xong {total_stories} User Stories từ {total_epics} Epics! Bạn xem qua và bấm 'Phê duyệt Stories' để thêm vào backlog nhé! 📋"
        approval_message = f"✅ Đã phê duyệt và thêm {total_epics} Epics, {total_stories} Stories vào backlog! 🎊"
        
        logger.info(f"[BA] Stories message: {message[:50]}...")
        
        return {
            "epics": epics,
            "stories": all_stories,
            "stories_message": message,
            "stories_approval_message": approval_message
        }
        
    except Exception as e:
        logger.error(f"[BA] Batch extraction failed: {e}, falling back to single call")
        return await _extract_stories_single_call(state, agent, prd)


async def _extract_stories_single_call(state: BAState, agent, prd: dict) -> dict:
    """Original single-call story extraction (fallback for simple PRDs).
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    system_prompt = _sys_prompt(agent, "extract_stories")
    user_prompt = _user_prompt(
        "extract_stories",
        prd=json.dumps(prd, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_story_llm,
        schema=FullStoriesOutput,
        messages=messages,
        config=_cfg(state, "extract_stories"),
        fallback_data={"epics": [], "message_template": "", "approval_template": "", "change_summary": ""}
    )
    
    # Convert Pydantic Epic objects to dicts
    epics = []
    for e in result.get("epics", []):
        if hasattr(e, "model_dump"):
            epics.append(e.model_dump())
        elif isinstance(e, dict):
            epics.append(e)
    
    message_template = result.get("message_template", "")
    approval_template = result.get("approval_template", "")
    
    # Flatten stories for backward compatibility
    all_stories = []
    for epic in epics:
        stories_in_epic = epic.get("stories", [])
        epic_title = epic.get("title", epic.get("name", "Unknown"))
        for story in stories_in_epic:
            if hasattr(story, "model_dump"):
                story = story.model_dump()
            story["epic_id"] = epic.get("id")
            story["epic_title"] = epic_title
            all_stories.append(story)
    
    total_epics = len(epics)
    total_stories = len(all_stories)
    logger.info(f"[BA] Single-call extraction: {total_epics} epics, {total_stories} stories")
    
    # Use hardcoded messages (LLM templates unreliable)
    message = f"🎉 Đã tạo xong {total_stories} User Stories từ {total_epics} Epics! Bạn xem qua và bấm 'Phê duyệt Stories' để thêm vào backlog nhé! 📋"
    approval_message = f"✅ Đã phê duyệt và thêm {total_epics} Epics, {total_stories} Stories vào backlog! 🎊"
    
    return {
        "epics": epics,
        "stories": all_stories,
        "stories_message": message,
        "stories_approval_message": approval_message
    }


async def update_stories(state: BAState, agent=None) -> dict:
    """Node: Update existing Epics and Stories based on user feedback.
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    
    FLOW:
    1. Check request clarity → ask clarification if vague
    2. Send to LLM for update
    3. Validate no duplicates created
    
    OPTIMIZATION: If user mentions specific page/domain (e.g., "thêm menu ở homepage"),
    only send RELEVANT epics to LLM instead of all epics (avoids timeout on large projects).
    """
    logger.info(f"[BA] Updating stories based on user feedback...")
    
    all_epics = state.get("epics", [])
    if not all_epics:
        return {"error": "No existing stories to update"}
    
    user_message = state.get("user_message", "")
    existing_prd = state.get("existing_prd")
    skip_clarity_check = state.get("skip_clarity_check", False)
    
    # ====================================================================================
    # STEP 1: CHECK FOR EXISTING STORIES FIRST - Before asking clarification
    # This prevents asking clarification for features that already exist in stories
    # ====================================================================================
    if not skip_clarity_check:  # Only check if not resuming from clarification
        user_keywords = _extract_intent_keywords(user_message)
        
        # Search for existing stories that might already cover this functionality
        matching_stories = []
        for epic in all_epics:
            for story in epic.get("stories", []):
                story_text = (
                    f"{story.get('title', '')} {story.get('description', '')} "
                    f"{' '.join(story.get('requirements', []))}"
                ).lower()
                
                # Check if user keywords appear in story
                matches = sum(1 for kw in user_keywords if kw in story_text)
                if matches >= 2:  # At least 2 keywords match
                    matching_stories.append({
                        "story": story,
                        "epic_domain": epic.get("domain"),
                        "match_score": matches / len(user_keywords) if user_keywords else 0
                    })
        
        if matching_stories and agent:
            # Found existing stories that might cover this functionality
            matching_stories.sort(key=lambda x: x["match_score"], reverse=True)
            best_match = matching_stories[0]
            story = best_match["story"]
            
            logger.info(f"[BA] Found existing story that might cover this: {story.get('id')} - {story.get('title')}")
            
            # Ask user if they want to update existing story or create new one
            existing_story_msg = (
                f"🔍 Mình tìm thấy story \"{story.get('title', '')}\" (ID: {story.get('id')}) "
                f"trong domain {best_match['epic_domain']} có vẻ đã cover chức năng này rồi.\n\n"
                f"Bạn muốn bổ sung gì vào story này không?"
            )
            
            await agent.message_user("response", existing_story_msg)
            
            # Return early - STOP the flow (waiting for user decision)
            return {
                "found_existing_story": True,
                "existing_story_id": story.get("id"),
                "existing_story_title": story.get("title"),
                "awaiting_user_decision": True,
                "is_complete": True,
                "result": {
                    "summary": "Found existing story - awaiting user decision",
                    "task_completed": False
                }
            }
    
    # ====================================================================================
    # STEP 2: CHECK CLARITY - Ask clarification if this is a NEW feature
    # Only runs if no existing stories found AND not resuming from clarification
    # ====================================================================================
    if skip_clarity_check:
        logger.info(f"[BA] Skipping clarity check (resuming from clarification)")
        is_clear = True
        missing_details = []
        related_feature = None
    else:
        is_clear, missing_details, related_feature = await _check_request_clarity(
            user_message, all_epics, existing_prd, agent
        )
    
    if not is_clear and agent:
        # Request needs clarification - either NEW feature or EXISTING without specific change
        logger.info(f"[BA] Clarification needed (related_feature={related_feature}): {missing_details}")
        
        # Build context message
        if related_feature:
            context_msg = f"Tính năng \"{related_feature}\" đã có trong hệ thống. Mình cần biết thêm chi tiết để cập nhật."
        else:
            context_msg = f"Để mình hiểu rõ hơn về \"{user_message}\", bạn cho mình biết thêm nhé!"
        
        # Format questions for batch API (use question cards like interview flow)
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
        
        # Send questions using question cards
        question_ids = await agent.ask_multiple_clarification_questions(batch_questions)
        
        # Save interview state with original_intent so RESUME knows to continue stories_update
        with Session(engine) as session:
            interview_state = {
                "original_intent": "stories_update",
                "user_message": user_message,
                "existing_prd": existing_prd,
                "epics": all_epics,
                "questions": batch_questions,
                "question_ids": [str(qid) for qid in question_ids],
                "related_feature": related_feature,
            }
            _save_interview_state_to_question(session, question_ids[0], interview_state)
            logger.info(f"[BA] Saved stories_update state for RESUME flow")
        
        # Return early - STOP the flow (waiting for user answers)
        return {
            "needs_clarification": True,
            "waiting_for_answer": True,
            "question_ids": [str(qid) for qid in question_ids],
            "is_complete": True,
            "result": {
                "summary": f"Feature '{related_feature}' already exists - asked for specific changes" if related_feature else "New feature request - asked for clarification",
                "task_completed": False
            }
        }
    
    # ====================================================================================
    # STEP 3: PROCEED WITH UPDATE - Either resuming from clarification or request is clear
    # ====================================================================================
    user_message_lower = state["user_message"].lower()
    
    # SMART FILTERING: Detect if user mentions specific domain/page
    # If yes, only update that epic (much faster, avoids timeout)
    relevant_epics = []
    mentioned_domains = []
    
    for epic in all_epics:
        epic_domain = (epic.get("domain") or "").lower()
        epic_title = (epic.get("title") or "").lower()
        
        # Check if user message mentions this epic's domain or title
        if epic_domain and epic_domain in user_message_lower:
            relevant_epics.append(epic)
            mentioned_domains.append(epic_domain)
        elif any(keyword in epic_title for keyword in user_message_lower.split() if len(keyword) > 3):
            # Match significant words (>3 chars) from user message to epic title
            relevant_epics.append(epic)
            mentioned_domains.append(epic_domain or "unknown")
    
    # If no specific domain mentioned, or too many epics (>5), use ALL epics (general update)
    # But warn about performance
    if not relevant_epics or len(relevant_epics) > 5:
        logger.info(f"[BA] No specific domain detected or too many matches, using ALL {len(all_epics)} epics (may be slow)")
        epics_to_update = all_epics
    else:
        logger.info(f"[BA] Detected specific domains: {mentioned_domains}. Updating only {len(relevant_epics)} relevant epics (optimization)")
        epics_to_update = relevant_epics
    
    # Get conversation context for memory
    conversation_context = state.get("conversation_context", "")
    if conversation_context:
        logger.info(f"[BA] Using conversation context: {len(conversation_context)} chars")
    
    system_prompt = _sys_prompt(agent, "update_stories")
    user_prompt = _user_prompt(
        "update_stories",
        epics=json.dumps(epics_to_update, ensure_ascii=False, indent=2),
        user_message=state["user_message"],
        conversation_context=conversation_context
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_story_llm,
        schema=FullStoriesOutput,
        messages=messages,
        config=_cfg(state, "update_stories"),
        fallback_data={"epics": epics_to_update, "message_template": "", "approval_template": "", "change_summary": "Không thể cập nhật"}
    )
    
    # Convert Pydantic Epic objects to dicts
    updated_epics_from_llm = []
    for e in result.get("epics", []):
        if hasattr(e, "model_dump"):
            updated_epics_from_llm.append(e.model_dump())
        elif isinstance(e, dict):
            updated_epics_from_llm.append(e)
    
    # MERGE: If we only updated SOME epics (optimization), merge them back into all_epics
    # Otherwise, use the updated epics directly
    if len(epics_to_update) < len(all_epics):
        logger.info(f"[BA] Merging {len(updated_epics_from_llm)} updated epics back into {len(all_epics)} total epics")
        
        # Build map of updated epics by ID
        updated_map = {epic.get("id"): epic for epic in updated_epics_from_llm}
        
        # Merge: replace updated epics, keep others unchanged
        final_epics = []
        for epic in all_epics:
            epic_id = epic.get("id")
            if epic_id in updated_map:
                final_epics.append(updated_map[epic_id])  # Use updated version
            else:
                final_epics.append(epic)  # Keep original
    else:
        # All epics were updated, use result directly
        final_epics = updated_epics_from_llm
    
    change_summary = result.get("change_summary", "Đã cập nhật stories")
    message_template = result.get("message_template", "")
    approval_template = result.get("approval_template", "")
    
    # Flatten stories for backward compatibility (use get, NOT pop - to keep stories in epics)
    all_stories = []
    for epic in final_epics:
        stories_in_epic = epic.get("stories", [])
        epic_title = epic.get("title", epic.get("name", "Unknown"))
        for story in stories_in_epic:
            if hasattr(story, "model_dump"):
                story = story.model_dump()
            story["epic_id"] = epic.get("id")
            story["epic_title"] = epic_title
            all_stories.append(story)
    
    total_epics = len(final_epics)
    total_stories = len(all_stories)
    logger.info(f"[BA] Updated {len(updated_epics_from_llm)} epics, final result: {total_epics} epics with {total_stories} stories")
    
    # No more validation needed here - STEP 2 already checked for existing functionality
    # If we reach here, user has confirmed they want to proceed
    # Use hardcoded messages (LLM templates unreliable)
    message = f"✏️ Đã cập nhật xong! Hiện có {total_stories} Stories trong {total_epics} Epics. Bạn xem qua và bấm 'Phê duyệt Stories' nhé! 📋"
    approval_message = f"✅ Đã cập nhật và lưu {total_epics} Epics, {total_stories} Stories vào backlog! 🎊"
    
    return {
        "epics": final_epics,
        "stories": all_stories,
        "change_summary": change_summary,
        "stories_message": message,
        "stories_approval_message": approval_message
    }


async def edit_single_story(state: BAState, agent=None) -> dict:
    """Node: Edit a SINGLE specific story based on user request.
    
    This is a FAST targeted update - finds the story by title/ID and applies only the requested change.
    Much faster than update_stories which regenerates everything.
    """
    logger.info(f"[BA] Editing single story (targeted mode)...")
    
    epics = state.get("epics", [])
    stories = state.get("stories", [])
    user_message = state.get("user_message", "")
    
    if not epics and not stories:
        logger.warning("[BA] No existing stories to edit")
        return {"error": "No existing stories to edit"}
    
    # Step 1: Find the target story from user message
    # Search by title match or ID match
    target_story = None
    target_epic_idx = None
    target_story_idx = None
    user_msg_lower = user_message.lower()
    
    # Flatten stories if not already
    if not stories:
        stories = []
        for epic in epics:
            for story in epic.get("stories", []):
                story["epic_id"] = epic.get("id")
                story["epic_title"] = epic.get("title")
                stories.append(story)
    
    # Search for story by title or ID - use BEST MATCH strategy
    best_match_story = None
    best_match_idx = None
    best_match_score = 0
    
    for i, story in enumerate(stories):
        story_title = story.get("title", "").lower()
        story_id = story.get("id", "").lower()
        
        # Check if story ID is mentioned in user message (exact match)
        if story_id and story_id in user_msg_lower:
            target_story = story
            target_story_idx = i
            logger.info(f"[BA] Found story by ID: {story_id}")
            break
        
        # Calculate match score based on KEY WORDS in story title
        # Focus on unique/distinctive words, not common ones like "want", "administrator"
        common_words = {"as", "a", "an", "i", "want", "to", "so", "that", "can", "the", "for", "and", "or", "in", "on", "is", "be", "user", "administrator", "customer"}
        title_words = [w for w in story_title.split() if len(w) > 2 and w not in common_words]
        
        # Count how many KEY words from title appear in user message
        match_count = sum(1 for w in title_words if w in user_msg_lower)
        
        # Calculate score as percentage of key words matched
        if title_words:
            score = match_count / len(title_words)
            logger.debug(f"[BA] Story '{story_title[:40]}...' score: {score:.2f} ({match_count}/{len(title_words)} key words)")
            
            # Keep track of best match
            if score > best_match_score:
                best_match_score = score
                best_match_story = story
                best_match_idx = i
    
    # Use best match if score is good enough (at least 40% key words match)
    if not target_story and best_match_story and best_match_score >= 0.4:
        target_story = best_match_story
        target_story_idx = best_match_idx
        logger.info(f"[BA] Found story by best title match (score={best_match_score:.2f}): {target_story.get('title')[:50]}...")
    
    if not target_story:
        logger.warning(f"[BA] Could not find target story in message: {user_message[:100]}...")
        # Fallback: Let LLM try to find it
        return await _edit_story_with_llm_search(state, agent, epics, stories)
    
    # Step 2: Use LLM to apply the specific change
    logger.info(f"[BA] Applying changes to story: {target_story.get('id')} - {target_story.get('title')[:50]}...")
    
    system_prompt = _sys_prompt(agent, "edit_single_story")
    user_prompt = _user_prompt(
        "edit_single_story",
        user_message=user_message,
        target_story=json.dumps(target_story, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_fast_llm,  # Use fast LLM since it's a simple edit
        schema=SingleStoryEditOutput,
        messages=messages,
        config=_cfg(state, "edit_single_story"),
        fallback_data={
            "story_id": target_story.get("id", ""),
            "found": True,
            "updated_story": target_story,
            "change_summary": "Không thể áp dụng thay đổi",
            "message": "⚠️ Không thể xử lý yêu cầu. Bạn thử lại nhé!"
        }
    )
    
    # Check if edit was successful
    updated_story = result.get("updated_story")
    if not updated_story:
        logger.warning("[BA] LLM could not process the edit - no updated_story returned")
        error_message = result.get("message", "⚠️ Không thể áp dụng thay đổi. Bạn thử lại nhé!")
        # Send error message to user directly
        if agent:
            await agent.message_user("response", error_message)
        return {
            "error": error_message,
            "is_complete": True  # Mark complete so graph ends
        }
    
    # Step 3: Check if user wants to DELETE the story
    # Story is considered "deleted" if:
    # - User explicitly says "xóa", "delete", "remove"
    # - LLM returns empty requirements AND empty acceptance_criteria
    if hasattr(updated_story, "model_dump"):
        updated_story = updated_story.model_dump()
    
    user_wants_delete = any(kw in user_msg_lower for kw in ["xóa", "delete", "remove", "loại bỏ", "bỏ story"])
    story_is_empty = (
        not updated_story.get("requirements") and 
        not updated_story.get("acceptance_criteria")
    )
    
    should_delete_story = user_wants_delete or story_is_empty
    
    if should_delete_story:
        # DELETE story completely from epics and stories
        story_id = target_story.get("id")
        logger.info(f"[BA] DELETING story {story_id} (user requested or story is empty)")
        
        # Remove from flat stories list
        stories = [s for s in stories if s.get("id") != story_id]
        
        # Remove from epics structure
        for epic in epics:
            epic_stories = epic.get("stories", [])
            epic["stories"] = [s for s in epic_stories if s.get("id") != story_id]
        
        change_summary = f"Đã xóa story {story_id}"
        message = result.get("message", f"🗑️ Đã xóa thành công story \"{target_story.get('title', '')[:50]}...\"")
        
        logger.info(f"[BA] Story deleted: {story_id}")
        
        return {
            "epics": epics,
            "stories": stories,
            "change_summary": change_summary,
            "stories_message": message,
            "stories_approval_message": f"✅ Đã xóa story khỏi backlog!"
        }
    else:
        # UPDATE story (keep it, just modify)
        # Update in stories list
        stories[target_story_idx] = updated_story
        
        # Update in epics structure
        for epic in epics:
            epic_stories = epic.get("stories", [])
            for j, s in enumerate(epic_stories):
                if s.get("id") == updated_story.get("id"):
                    epic_stories[j] = updated_story
                    break
        
        change_summary = result.get("change_summary", "Đã cập nhật story")
        message = result.get("message", f"✅ Đã cập nhật story '{updated_story.get('title', '')[:50]}...'")
        
        logger.info(f"[BA] Single story edit complete: {change_summary}")
        
        return {
            "epics": epics,
            "stories": stories,
            "change_summary": change_summary,
            "stories_message": message,
            "stories_approval_message": f"✅ Đã lưu thay đổi cho story!"
        }


async def _edit_story_with_llm_search(state: BAState, agent, epics: list, stories: list) -> dict:
    """Fallback: Let LLM search for the story when we can't find it by keyword matching."""
    logger.info("[BA] Using LLM to search for target story...")
    
    # Create a summary of all stories for LLM to search
    stories_summary = []
    for story in stories:
        stories_summary.append({
            "id": story.get("id"),
            "title": story.get("title"),
            "epic_id": story.get("epic_id")
        })
    
    # Ask LLM to identify which story and what change
    system_prompt = """You identify which story the user wants to edit.
Return JSON: {"story_id": "EPIC-XXX-US-XXX", "found": true/false}
If you can't identify, set found=false."""
    
    user_prompt = f"""User request: "{state.get('user_message', '')}"

Available stories:
{json.dumps(stories_summary, ensure_ascii=False, indent=2)}

Which story does the user want to edit?"""
    
    try:
        response = await _fast_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Parse response
        import re
        match = re.search(r'"story_id"\s*:\s*"([^"]+)"', response.content)
        if match:
            story_id = match.group(1)
            # Find the story
            for i, story in enumerate(stories):
                if story.get("id") == story_id:
                    # Now edit this story
                    state_copy = dict(state)
                    state_copy["target_story_idx"] = i
                    # Recursively call with found story
                    return await _apply_edit_to_story(state_copy, agent, epics, stories, i)
    except Exception as e:
        logger.warning(f"[BA] LLM search failed: {e}")
    
    # Could not find - fall back to full update
    logger.warning("[BA] Could not find specific story, falling back to full update_stories")
    return await update_stories(state, agent)


async def _apply_edit_to_story(state: BAState, agent, epics: list, stories: list, story_idx: int) -> dict:
    """Apply edit to a specific story after it's been found."""
    target_story = stories[story_idx]
    user_message = state.get("user_message", "")
    
    system_prompt = _sys_prompt(agent, "edit_single_story")
    user_prompt = _user_prompt(
        "edit_single_story",
        user_message=user_message,
        target_story=json.dumps(target_story, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_fast_llm,
        schema=SingleStoryEditOutput,
        messages=messages,
        config=_cfg(state, "edit_single_story"),
        fallback_data={
            "story_id": target_story.get("id", ""),
            "found": True,
            "updated_story": target_story,
            "change_summary": "Không thể áp dụng thay đổi",
            "message": "⚠️ Không thể xử lý yêu cầu."
        }
    )
    
    updated_story = result.get("updated_story")
    if not updated_story:
        logger.warning("[BA] _apply_edit_to_story: LLM could not process the edit")
        error_message = result.get("message", "⚠️ Không thể áp dụng thay đổi. Bạn thử lại nhé!")
        if agent:
            await agent.message_user("response", error_message)
        return {"error": error_message, "is_complete": True}
    if hasattr(updated_story, "model_dump"):
        updated_story = updated_story.model_dump()
    
    stories[story_idx] = updated_story
    
    for epic in epics:
        epic_stories = epic.get("stories", [])
        for j, s in enumerate(epic_stories):
            if s.get("id") == updated_story.get("id"):
                epic_stories[j] = updated_story
                break
    
    return {
        "epics": epics,
        "stories": stories,
        "change_summary": result.get("change_summary", "Đã cập nhật"),
        "stories_message": result.get("message", "✅ Đã cập nhật story!"),
        "stories_approval_message": "✅ Đã lưu thay đổi!"
    }


async def approve_stories(state: BAState, agent=None) -> dict:
    """Node: Approve stories and save them to database using UPSERT logic.
    
    UPSERT Strategy (preserves existing stories):
    - Epics/Stories with matching code: UPDATE (preserve status, progress)
    - New Epics/Stories: INSERT
    - Epics/Stories not in new data: KEEP (don't delete - user may have other epics)
    
    This allows incremental updates when user adds/modifies features without
    losing existing stories that are in progress.
    """
    logger.info(f"[BA] Approving stories with UPSERT logic...")
    
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    # If no epics in state, try to load from artifact (fix for approval flow)
    if not epics_data and agent:
        logger.info("[BA] No epics in state, trying to load from artifact...")
        try:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.get_latest_version(
                    project_id=agent.project_id,
                    artifact_type=ArtifactType.USER_STORIES
                )
                if artifact and artifact.content:
                    epics_data = artifact.content.get("epics", [])
                    stories_data = artifact.content.get("stories", [])
                    logger.info(f"[BA] Loaded from artifact: {len(epics_data)} epics, {len(stories_data)} stories")
        except Exception as e:
            logger.warning(f"[BA] Failed to load from artifact: {e}")
    
    if not epics_data and not stories_data:
        return {"error": "No stories to approve"}
    
    if not agent:
        return {"error": "No agent context for saving to database"}
    
    try:
        created_epics = []
        updated_epics = []
        created_stories = []
        updated_stories = []
        epic_id_map = {}  # Map string ID (EPIC-001) to UUID
        story_id_map = {}  # Map string ID (EPIC-001-US-001) to actual UUID
        
        with Session(engine) as session:
            # 0. Load existing epics and stories (for UPSERT comparison)
            existing_epics_db = session.exec(
                select(Epic).where(Epic.project_id == agent.project_id)
            ).all()
            existing_stories_db = session.exec(
                select(Story).where(Story.project_id == agent.project_id)
            ).all()
            
            # Build lookup maps by epic_code and story_code
            existing_epics_map = {e.epic_code: e for e in existing_epics_db if e.epic_code}
            existing_stories_map = {s.story_code: s for s in existing_stories_db if s.story_code}
            
            logger.info(
                f"[BA] UPSERT: Found {len(existing_epics_map)} existing epics, "
                f"{len(existing_stories_map)} existing stories in DB"
            )
            
            # 1. UPSERT Epics
            for epic_data in epics_data:
                epic_string_id = epic_data.get("id", "")  # e.g., "EPIC-001"
                existing_epic = existing_epics_map.get(epic_string_id)
                
                if existing_epic:
                    # UPDATE existing epic (preserve UUID, update content)
                    existing_epic.title = epic_data.get("title", epic_data.get("name", existing_epic.title))
                    existing_epic.description = epic_data.get("description", existing_epic.description)
                    existing_epic.domain = epic_data.get("domain", existing_epic.domain)
                    # Note: preserve epic_status - don't reset to PLANNED
                    
                    epic_id_map[epic_string_id] = existing_epic.id
                    updated_epics.append({
                        "id": str(existing_epic.id),
                        "title": existing_epic.title,
                        "domain": existing_epic.domain,
                        "action": "updated"
                    })
                    logger.debug(f"[BA] Updated epic: {epic_string_id} -> {existing_epic.id}")
                else:
                    # INSERT new epic
                    new_epic = Epic(
                        epic_code=epic_string_id if epic_string_id else None,
                        title=epic_data.get("title", epic_data.get("name", "Unknown Epic")),
                        description=epic_data.get("description"),
                        domain=epic_data.get("domain"),
                        project_id=agent.project_id,
                        epic_status=EpicStatus.PLANNED
                    )
                    session.add(new_epic)
                    session.flush()  # Get UUID immediately
                    
                    epic_id_map[epic_string_id] = new_epic.id
                    created_epics.append({
                        "id": str(new_epic.id),
                        "title": new_epic.title,
                        "domain": new_epic.domain,
                        "action": "created"
                    })
                    logger.debug(f"[BA] Created epic: {epic_string_id} -> {new_epic.id}")
            
            logger.info(f"[BA] Epics: {len(created_epics)} created, {len(updated_epics)} updated")
            
            # 2. UPSERT Stories
            # Get max rank for new stories
            max_rank_result = session.exec(
                select(func.max(Story.rank)).where(
                    Story.project_id == agent.project_id,
                    Story.status == StoryStatus.TODO
                )
            ).one()
            current_rank = (max_rank_result or 0)
            
            story_objects_for_deps = []  # (story, string_id, original_deps) for dependency resolution
            
            for story_data in stories_data:
                story_string_id = story_data.get("id", "")  # e.g., "EPIC-001-US-001"
                epic_string_id = story_data.get("epic_id", "")
                epic_uuid = epic_id_map.get(epic_string_id)
                original_dependencies = story_data.get("dependencies", [])
                
                existing_story = existing_stories_map.get(story_string_id)
                
                if existing_story:
                    # UPDATE existing story (preserve status, UUID, rank)
                    existing_story.title = story_data.get("title", existing_story.title)
                    existing_story.description = story_data.get("description", existing_story.description)
                    existing_story.acceptance_criteria = story_data.get("acceptance_criteria", existing_story.acceptance_criteria)
                    existing_story.requirements = story_data.get("requirements", existing_story.requirements)
                    existing_story.priority = story_data.get("priority", existing_story.priority)
                    existing_story.story_point = story_data.get("story_point", existing_story.story_point)
                    # Update epic_id in case story moved to different epic
                    if epic_uuid:
                        existing_story.epic_id = epic_uuid
                    # Note: preserve status, rank - don't reset to TODO
                    
                    story_id_map[story_string_id] = str(existing_story.id)
                    story_objects_for_deps.append((existing_story, story_string_id, original_dependencies))
                    updated_stories.append({
                        "id": str(existing_story.id),
                        "string_id": story_string_id,
                        "title": existing_story.title,
                        "epic_id": str(existing_story.epic_id) if existing_story.epic_id else None,
                        "status": existing_story.status.value if existing_story.status else "TODO",
                        "action": "updated"
                    })
                    logger.debug(f"[BA] Updated story: {story_string_id} (status preserved: {existing_story.status})")
                else:
                    # INSERT new story
                    current_rank += 1
                    new_story = Story(
                        story_code=story_string_id if story_string_id else None,
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
                    session.add(new_story)
                    session.flush()  # Get UUID immediately
                    
                    story_id_map[story_string_id] = str(new_story.id)
                    story_objects_for_deps.append((new_story, story_string_id, original_dependencies))
                    created_stories.append({
                        "id": str(new_story.id),
                        "string_id": story_string_id,
                        "title": new_story.title,
                        "epic_id": str(new_story.epic_id) if new_story.epic_id else None,
                        "action": "created"
                    })
                    logger.debug(f"[BA] Created story: {story_string_id} -> {new_story.id}")
            
            logger.info(f"[BA] Stories: {len(created_stories)} created, {len(updated_stories)} updated")
            
            # 3. DELETE stories that are NOT in the new artifact (user deleted them)
            # This handles the case where user says "xóa story X"
            deleted_stories = []
            stories_in_artifact = {s.get("id") for s in stories_data if s.get("id")}
            
            for existing_story in existing_stories_db:
                story_code = existing_story.story_code
                if story_code and story_code not in stories_in_artifact:
                    # Story was in DB but NOT in artifact → User deleted it
                    logger.info(f"[BA] DELETING story from DB: {story_code} (not in artifact)")
                    session.delete(existing_story)
                    deleted_stories.append({
                        "id": str(existing_story.id),
                        "string_id": story_code,
                        "title": existing_story.title,
                        "action": "deleted"
                    })
            
            if deleted_stories:
                logger.info(f"[BA] Deleted {len(deleted_stories)} stories from DB")
            
            # 4. Resolve dependencies for all stories (both new and updated)
            deps_resolved = 0
            for story, string_id, original_deps in story_objects_for_deps:
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
            
            # Commit all changes (including deletions)
            session.commit()
        
        total_epics = len(created_epics) + len(updated_epics)
        total_stories = len(created_stories) + len(updated_stories)
        
        logger.info(
            f"[BA] UPSERT complete: {total_epics} epics ({len(created_epics)} new, {len(updated_epics)} updated), "
            f"{total_stories} stories ({len(created_stories)} new, {len(updated_stories)} updated, {len(deleted_stories)} deleted)"
        )
        
        # Build approval message - ONLY show actions that actually happened
        actions = []
        
        # Only mention what actually changed
        if len(created_stories) > 0:
            actions.append(f"{len(created_stories)} story thêm mới")
        if len(updated_stories) > 0:
            actions.append(f"{len(updated_stories)} story cập nhật")
        if len(deleted_stories) > 0:
            actions.append(f"{len(deleted_stories)} story xóa")
        
        if actions:
            # Show only what changed
            approval_msg = f"✅ Đã cập nhật backlog! {', '.join(actions)}. 🎉"
        else:
            # Nothing changed
            approval_msg = "✅ Backlog đã được đồng bộ! 🎉"
        
        return {
            "stories_approved": True,
            "created_epics": created_epics,
            "updated_epics": updated_epics,
            "created_stories": created_stories,
            "updated_stories": updated_stories,
            "approval_message": approval_msg,
            "stories_approval_message": approval_msg
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
        
        # Send message to user - use message from LLM response instead of separate call
        is_update = bool(state.get("change_summary"))
        prd_message = state.get("prd_message", "")
        
        # Fallback message if LLM didn't generate one
        if not prd_message:
            prd_message = f"Mình đã cập nhật PRD theo yêu cầu của bạn rồi nhé! 📝" if is_update else f"Tuyệt vời! 🎉 Mình đã hoàn thành PRD cho dự án '{project_name}' rồi!"
        
        await agent.message_user(
            event_type="response",
            content=prd_message,
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
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories", "story_edit_single"]
    
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
                # Include approval_message so it can be loaded when user approves later
                approval_message = state.get("stories_approval_message", "")
                artifact_content = {
                    "epics": epics_data, 
                    "stories": stories_data, 
                    "epics_count": epics_count, 
                    "stories_count": stories_count,
                    "approval_message": approval_message  # Save for later use in approve_stories
                }
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
        
        # Send message to user - use message from state (already filled from LLM template)
        if agent:
            stories_message = state.get("stories_message", "")
            logger.info(f"[BA] _save_stories_artifact: stories_message from state = '{stories_message[:50] if stories_message else 'EMPTY'}...'")
            
            # Fallback only if state somehow doesn't have message (shouldn't happen normally)
            if not stories_message:
                stories_message = f"Xong rồi! 🚀 Mình đã tạo {stories_count} User Stories từ {epics_count} Epics. Bạn xem qua và phê duyệt nhé!"
                logger.warning(f"[BA] _save_stories_artifact: stories_message was empty, using fallback")
            
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
    
    # Domain analysis - internal process, don't send message to user
    # The analysis helps generate better PRD/stories, but users don't need to see it
    if state.get("analysis_text") and not state.get("error"):
        result["summary"] = "Domain analysis completed"
        result["analysis"] = state["analysis_text"]
        # Don't send "Mình đã phân tích xong domain" message - it's confusing for users
    
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
        # Use approval_message from LLM response (generated during story extraction/update)
        if agent:
            logger.info(f"[BA] Sending stories_approved message to frontend")
            stories_count = len(state.get("created_stories", []))
            epics_count = len(created_epics_list)
            
            # Get approval message from state (already filled from LLM template)
            approved_message = state.get("stories_approval_message", "")
            logger.info(f"[BA] save_artifacts: stories_approval_message from state = '{approved_message[:50] if approved_message else 'EMPTY'}...'")
            
            # Fallback only if state somehow doesn't have message (shouldn't happen normally)
            if not approved_message:
                approved_message = f"Tuyệt vời! 🎊 Đã thêm {epics_count} Epics và {stories_count} Stories vào backlog rồi!"
                logger.warning(f"[BA] save_artifacts: stories_approval_message was empty, using fallback")
            
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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_default_llm,
        schema=VerifyStoryOutput,
        messages=messages,
        config=_cfg(state, "verify_story_simple"),
        fallback_data={
            "is_duplicate": False,
            "invest_score": 4,
            "invest_issues": [],
            "summary": "Không thể xác minh story"
        }
    )
    
    logger.info(f"[BA] Story verification complete: invest_score={result.get('invest_score')}, "
                f"is_duplicate={result.get('is_duplicate')}")
    
    # Send suggestions to user (always send, even without agent)
    await _send_verify_message(agent, new_story, result, project_id=project_id)
    
    return {
        "verification_result": result,
        "is_complete": True
    }


async def _send_verify_message(agent, story, result: dict, project_id=None) -> None:
    """Send verification result message to user via Kafka."""
    from uuid import uuid4
    from app.kafka import get_kafka_producer, KafkaTopics
    from app.kafka.event_schemas import AgentEvent
    from app.models import Message, AuthorType
    
    # Extract all fields from result
    is_duplicate = result.get("is_duplicate", False)
    duplicate_of = result.get("duplicate_of")
    duplicate_reason = result.get("duplicate_reason")
    invest_score = result.get("invest_score", 6)
    invest_issues = result.get("invest_issues", [])
    
    # Story content suggestions (all in English)
    suggested_title = result.get("suggested_title")
    suggested_description = result.get("suggested_description")
    suggested_requirements = result.get("suggested_requirements")
    suggested_ac = result.get("suggested_acceptance_criteria")
    
    # Additional suggestions
    suggested_story_point = result.get("suggested_story_point")
    suggested_priority = result.get("suggested_priority")
    should_split = result.get("should_split", False)
    split_suggestions = result.get("split_suggestions")
    
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
    
    # Check if we have any suggestions
    has_suggestions = bool(
        suggested_title or suggested_description or 
        suggested_requirements or suggested_ac or
        suggested_story_point or suggested_priority or
        should_split
    )
    
    details = {
        "message_type": "story_review",
        "story_id": str(story.id),
        "story_title": story.title,
        # Duplicate info
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "duplicate_reason": duplicate_reason,
        # INVEST evaluation
        "invest_score": invest_score,
        "invest_issues": invest_issues,
        # Story content suggestions (English)
        "suggested_title": suggested_title,
        "suggested_description": suggested_description,
        "suggested_requirements": suggested_requirements,
        "suggested_acceptance_criteria": suggested_ac,
        # Additional suggestions
        "suggested_story_point": suggested_story_point,
        "suggested_priority": suggested_priority,
        "should_split": should_split,
        "split_suggestions": split_suggestions,
        # Meta
        "has_suggestions": has_suggestions,
        "summary": summary,
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
