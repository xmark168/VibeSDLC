"""Universal JSON extraction utilities."""

import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def extract_json_universal(response_text: str, debug_info: str = "unknown") -> Dict[str, Any]:
    """Universal JSON extractor supporting multiple formats."""
    if not response_text or not isinstance(response_text, str):
        raise ValueError(f"[{debug_info}] Invalid response_text")
    
    text = response_text.strip()
    
    # Strategy 1: <result>...</result> tags
    json_obj = _extract_from_result_tags(text, debug_info)
    if json_obj:
        return json_obj
    
    # Strategy 2: Markdown code blocks
    json_obj = _extract_from_code_blocks(text, debug_info)
    if json_obj:
        return json_obj
    
    # Strategy 3: Raw JSON objects
    json_obj = _extract_raw_json(text, debug_info)
    if json_obj:
        return json_obj
    
    raise ValueError(f"[{debug_info}] Unable to extract JSON. Preview: {text[:200]}...")


def _extract_from_result_tags(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    try:
        match = re.search(r'<result>\s*(.*?)\s*</result>', text, re.DOTALL | re.IGNORECASE)
        if match:
            content = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', match.group(1).strip(), flags=re.DOTALL)
            return json.loads(content)
    except:
        pass
    return None


def _extract_from_code_blocks(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    try:
        for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
    except:
        pass
    return None


def _extract_raw_json(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    try:
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    parsed = json.loads(text[start_idx:i+1])
                    if parsed and len(parsed) > 0:
                        return parsed
                    start_idx = -1
    except:
        pass
    return None
