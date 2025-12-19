import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage


from app.core.agent.llm_factory import get_llm, create_llm, MODELS

from ..state import BAState
from ..schemas import (
    IntentOutput,
    DocumentAnalysisOutput,
    DocumentFeedbackOutput
)
from app.core.agent.prompt_utils import (
    load_prompts_yaml
)

# Load prompts from YAML 
PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")

logger = logging.getLogger(__name__)

from .utils import _invoke_structured, _cfg, _sys_prompt, _user_prompt, _fast_llm, _default_llm


def _build_context_summary(features: list, epics: list) -> tuple[str, str]:
    """Build context summary for intent analysis. """
    # Features context
    features_context = ""
    if features:
        feature_names = [f"  - {f.get('name', 'Unknown')}" for f in features[:10]]
        features_context = f"Existing PRD features ({len(features)} total):\n{chr(10).join(feature_names)}"
    else:
        features_context = "Existing PRD features: None (no PRD yet)"
    
    # Epics context
    epics_context = ""
    if epics:
        epic_items = [
            f"  - {e.get('domain', 'General')}: {e.get('title', 'Unknown')} ({len(e.get('stories', []))} stories)"
            for e in epics[:8]
        ]
        epics_context = f"Existing Epics/Stories ({len(epics)} epics total):\n{chr(10).join(epic_items)}"
    else:
        epics_context = "Existing Epics/Stories: None (no stories created yet)"
    
    return features_context, epics_context


def _clean_collected_info(info: dict) -> dict:
    """Remove None, 'null', and empty values from collected_info."""
    if hasattr(info, "model_dump"):
        info = info.model_dump()
    return {
        k: v for k, v in info.items() 
        if v is not None and v != "null" and v != ""
    }


async def analyze_intent(state: BAState, agent=None) -> dict:
    """Analyze user intent and classify task.
    
    Uses LLM with structured output for reliable intent classification.
    Context-aware: considers existing PRD features and epics.
    """
    logger.info("[BA] Analyzing intent: %s...", state["user_message"][:80])
    
    # Build dynamic context - extract only what's needed
    existing_prd = state.get("existing_prd") or {}
    prd_features = existing_prd.get("features", [])
    existing_epics = state.get("epics", [])
    
    features_ctx, epics_ctx = _build_context_summary(prd_features, existing_epics)
    
    # Build prompts
    system_prompt = _sys_prompt(agent, "analyze_intent")
    user_prompt = _user_prompt(
        "analyze_intent",
        user_message=state["user_message"],
        has_prd="Yes" if existing_prd else "No",
        has_info="Yes" if state.get("collected_info") else "No",
        existing_features_context=features_ctx,
        existing_epics_context=epics_ctx,
    )
    
    # Call LLM for intent classification
    result = await _invoke_structured(
        llm=_fast_llm,
        schema=IntentOutput,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        config=_cfg(state, "analyze_intent"),
        fallback_data=None  # No fallback - expose failures for debugging
    )
    
    logger.info("[BA] Intent: %s (reason: %s)", 
                result['intent'], 
                result.get('reasoning', '')[:100])
    return result




async def analyze_document_content(document_text: str, agent=None) -> dict:
    """Analyze uploaded document to extract requirements information. """
    # Truncate if too long
    MAX_CHARS = 15000
    if len(document_text) > MAX_CHARS:
        document_text = document_text[:MAX_CHARS] + "\n\n[... truncated ...]"
        logger.debug("[BA] Document truncated to %d chars", MAX_CHARS)
    
    # Build prompts
    system_prompt = _sys_prompt(agent, "analyze_document")
    user_prompt = _user_prompt("analyze_document", document_text=document_text)
    
    # Define fallback structure
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
    
    # Call LLM
    result = await _invoke_structured(
        llm=_default_llm,
        schema=DocumentAnalysisOutput,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        config={"run_name": "analyze_document"},
        fallback_data=fallback
    )
    
    # Clean collected_info - remove None/empty values
    collected_info = _clean_collected_info(result.get("collected_info", {}))
    
    logger.info(
        "[BA] Document: type=%s, score=%.0f%%, comprehensive=%s",
        result['document_type'],
        result['completeness_score'] * 100,
        result['is_comprehensive']
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
    "complete_requirements": "Tài liệu đầy đủ thông tin! Mình sẽ tạo PRD trực tiếp từ nội dung này.",
    "partial_requirements": "Đã trích xuất một số thông tin từ tài liệu. Mình cần hỏi thêm vài câu để làm rõ.",
    "not_requirements": "Đây không phải tài liệu yêu cầu dự án. Bạn muốn mình làm gì với nội dung này?",
}




async def generate_document_feedback(
    document_type: str,
    detected_doc_kind: str = "",
    summary: str = "",
    extracted_items: list = None,
    missing_info: list = None,
    completeness_score: float = 0.0,
    agent=None
) -> str:
    """Generate natural feedback message about document analysis.
    
    Falls back to predefined messages if LLM fails.
    """
    extracted_items = extracted_items or []
    missing_info = missing_info or []
    
    try:
        system_prompt = _sys_prompt(agent, "document_analysis_feedback")
        user_prompt = _user_prompt(
            "document_analysis_feedback",
            document_type=document_type,
            detected_doc_kind=detected_doc_kind or "không xác định",
            summary=summary or "Không có tóm tắt",
            extracted_items=", ".join(extracted_items) or "Không có",
            missing_info=", ".join(missing_info) or "Không có",
            completeness_score=f"{completeness_score * 100:.0f}"
        )
        
        result = await _invoke_structured(
            llm=_default_llm,
            schema=DocumentFeedbackOutput,
            messages=[
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            fallback_data={
                "message": _DOC_FALLBACK_MESSAGES.get(
                    document_type, 
                    _DOC_FALLBACK_MESSAGES["partial_requirements"]
                )
            }
        )
        
        message = result.get("message", "")
        logger.debug("[BA] Generated feedback: %s...", message[:100])
        return message
        
    except Exception as e:
        logger.warning("[BA] Feedback generation failed: %s, using fallback", e)
        return _DOC_FALLBACK_MESSAGES.get(
            document_type, 
            _DOC_FALLBACK_MESSAGES["partial_requirements"]
        )




