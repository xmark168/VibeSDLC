"""Prompt building and response parsing utilities for Business Analyst.

Uses shared prompt_utils from core for prompt building (same pattern as Team Leader).
"""

import json
import logging
import re
from pathlib import Path

from app.agents.core.prompt_utils import (
    load_prompts_yaml,
    get_task_prompts,
    build_system_prompt,
    build_user_prompt,
)

logger = logging.getLogger(__name__)

# Load prompts configuration
PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")

# Default values for BA agent (used when agent model doesn't have persona)
BA_DEFAULTS = {
    "name": "Business Analyst",
    "role": "Business Analyst / Requirements Specialist",
    "goal": "Phân tích requirements, tạo PRD và user stories",
    "description": "Chuyên gia phân tích yêu cầu phần mềm",
    "personality": "Thân thiện, kiên nhẫn, giỏi lắng nghe",
    "communication_style": "Đơn giản, dễ hiểu, tránh thuật ngữ kỹ thuật",
}


def _repair_json(json_str: str) -> str:
    """
    Attempt to repair common JSON syntax errors from LLM output.
    
    Common issues:
    - Trailing commas before ] or }
    - Missing commas between elements
    - Unescaped newlines in strings
    - Single quotes instead of double quotes
    """
    # Remove trailing commas before ] or }
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Fix missing commas between } and { or } and "
    json_str = re.sub(r'}\s*{', r'},{', json_str)
    json_str = re.sub(r'}\s*"', r'},"', json_str)
    
    # Fix missing commas between ] and { or ] and "
    json_str = re.sub(r']\s*{', r'],{', json_str)
    json_str = re.sub(r']\s*"', r'],"', json_str)
    
    # Fix missing commas between string values: "value" "key"
    json_str = re.sub(r'"\s+"', r'","', json_str)
    
    # Fix missing commas after true/false/null/numbers before "
    json_str = re.sub(r'(true|false|null|\d)\s+"', r'\1,"', json_str)
    
    return json_str


def parse_json_response(response: str) -> dict:
    """
    Parse JSON from LLM response with automatic repair for common errors.
    
    Handles cases where JSON is wrapped in markdown code blocks.
    
    Args:
        response: Raw LLM response string
    
    Returns:
        Parsed JSON as dict
    
    Raises:
        json.JSONDecodeError: If JSON parsing fails after repair attempts
    """
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response
    
    # First attempt: parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as first_error:
        logger.debug(f"[parse_json] First parse failed: {first_error}, attempting repair...")
    
    # Second attempt: repair and parse
    try:
        repaired = _repair_json(json_str)
        return json.loads(repaired)
    except json.JSONDecodeError as second_error:
        logger.warning(f"[parse_json] Repair failed: {second_error}")
        raise second_error


def parse_intent_response(response: str) -> dict:
    """
    Parse intent classification response.
    
    Args:
        response: LLM response string
    
    Returns:
        dict with 'intent' and 'reasoning' keys
    """
    try:
        result = parse_json_response(response)
        
        if "intent" in result:
            return {
                "intent": result["intent"],
                "reasoning": result.get("reasoning", "")
            }
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[parse_intent] Parse error: {e}")
    
    # Default to interview if parsing fails
    return {
        "intent": "interview",
        "reasoning": "Could not parse intent, defaulting to interview"
    }


def parse_questions_response(response: str) -> list[dict]:
    """
    Parse questions from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        List of question dicts with 'text', 'type', 'options', 'allow_multiple' keys
    """
    try:
        result = parse_json_response(response)
        questions_list = result.get("questions", [])
        
        parsed_questions = []
        for q in questions_list:
            if isinstance(q, str):
                # Old format: just string
                parsed_questions.append({
                    "text": q,
                    "type": "open",
                    "options": None,
                    "allow_multiple": False
                })
            elif isinstance(q, dict):
                # New format: dict with text, type, options
                parsed_questions.append({
                    "text": q.get("text", ""),
                    "type": q.get("type", "open"),
                    "options": q.get("options"),
                    "allow_multiple": q.get("allow_multiple", False)
                })
        
        return parsed_questions
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[parse_questions] Parse error: {e}")
        return []


def parse_prd_response(response: str) -> dict:
    """
    Parse PRD from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        PRD dict
    """
    try:
        return parse_json_response(response)
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_prd] Parse error: {e}")
        return {
            "project_name": "Generated PRD",
            "overview": "Error parsing PRD",
            "raw_content": response[:1000]
        }


def parse_prd_update_response(response: str) -> dict:
    """
    Parse PRD update response.
    
    Args:
        response: LLM response string
    
    Returns:
        dict with 'updated_prd' and 'change_summary' keys
    """
    try:
        result = parse_json_response(response)
        return {
            "updated_prd": result.get("updated_prd", {}),
            "change_summary": result.get("change_summary", "PRD updated")
        }
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_prd_update] Parse error: {e}")
        return {
            "updated_prd": None,
            "change_summary": f"Error parsing update: {str(e)}"
        }


def parse_document_analysis_response(response: str) -> dict:
    """
    Parse document analysis response.
    
    Args:
        response: LLM response string
    
    Returns:
        dict with 'document_type', 'collected_info', 'completeness_score', 
        'is_comprehensive', 'summary', 'extracted_items', 'missing_info'
    """
    try:
        result = parse_json_response(response)
        return {
            "document_type": result.get("document_type", "partial_requirements"),
            "detected_doc_kind": result.get("detected_doc_kind", ""),
            "collected_info": result.get("collected_info", {}),
            "completeness_score": float(result.get("completeness_score", 0.0)),
            "is_comprehensive": result.get("is_comprehensive", False),
            "summary": result.get("summary", ""),
            "extracted_items": result.get("extracted_items", []),
            "missing_info": result.get("missing_info", [])
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[parse_document_analysis] Parse error: {e}")
        return {
            "document_type": "partial_requirements",
            "detected_doc_kind": "",
            "collected_info": {},
            "completeness_score": 0.0,
            "is_comprehensive": False,
            "summary": "Không thể phân tích tài liệu",
            "extracted_items": [],
            "missing_info": ["target_users", "main_features", "business_model"]
        }


def parse_stories_response(response: str) -> dict:
    """
    Parse epics with user stories from LLM response.
    
    Args:
        response: LLM response string
    
    Returns:
        Dict with 'epics' list, each epic containing 'stories' list
    """
    try:
        result = parse_json_response(response)
        logger.info(f"[parse_stories] Parsed result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
        
        # New format: epics with stories
        if "epics" in result:
            epics = result.get("epics", [])
            logger.info(f"[parse_stories] Found {len(epics)} epics in response")
            return {"epics": epics}
        
        # Legacy format: flat stories list - convert to single epic
        if "stories" in result:
            stories = result.get("stories", [])
            logger.info(f"[parse_stories] Found {len(stories)} stories (legacy format)")
            return {
                "epics": [{
                    "id": "EPIC-001",
                    "title": "User Stories",
                    "description": "Auto-generated epic from legacy format",
                    "domain": "General",
                    "stories": stories,
                    "total_story_points": sum(
                        s.get("story_points", 0) for s in stories
                    )
                }]
            }
        
        logger.warning(f"[parse_stories] No 'epics' or 'stories' key found. Keys: {list(result.keys()) if isinstance(result, dict) else result}")
        return {"epics": []}
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_stories] Parse error: {e}")
        logger.warning(f"[parse_stories] Raw response: {response[:500]}")
        return {"epics": []}
