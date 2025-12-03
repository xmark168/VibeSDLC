"""Universal JSON extraction utilities for Developer V2."""

import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def extract_json_universal(response_text: str, debug_info: str = "unknown") -> Dict[str, Any]:
    """
    Universal JSON extractor supporting multiple model response formats.
    
    Parsing strategies in order of priority:
    1. <result>...</result> tags (most reliable)
    2. Markdown code blocks (```json...``` or ```...```)
    3. Raw JSON objects in text ({...})
    4. Fallback regex patterns
    
    Args:
        response_text: The raw response text from any LLM model
        debug_info: Context info for logging (e.g., "plan_node")
    
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        ValueError: If no valid JSON found after all strategies
    """
    if not response_text or not isinstance(response_text, str):
        raise ValueError(f"[{debug_info}] Invalid response_text: {type(response_text)}")
    
    original_text = response_text
    response_text = response_text.strip()
    
    # Strategy 1: <result>...</result> tags (highest priority)
    json_obj = _extract_from_result_tags(response_text, debug_info)
    if json_obj is not None:
        return json_obj
    
    # Strategy 2: Markdown code blocks
    json_obj = _extract_from_code_blocks(response_text, debug_info)
    if json_obj is not None:
        return json_obj
    
    # Strategy 3: Raw JSON objects
    json_obj = _extract_raw_json(response_text, debug_info)
    if json_obj is not None:
        return json_obj
    
    # Strategy 4: Fallback patterns
    json_obj = _extract_fallback_patterns(response_text, debug_info)
    if json_obj is not None:
        return json_obj
    
    # All strategies failed
    logger.error(f"[{debug_info}] JSON extraction failed. Response preview: {original_text[:500]}")
    raise ValueError(
        f"[{debug_info}] Unable to extract JSON from response. "
        f"Expected formats: <result>{{...}}</result>, ```json{{...}}```, or raw JSON. "
        f"Response preview: {original_text[:200]}..."
    )


def _extract_from_result_tags(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from <result>...</result> tags."""
    try:
        pattern = r'<result>\s*(.*?)\s*</result>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            json_content = match.group(1).strip()
            # Remove any nested code blocks within result tags
            json_content = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', json_content, flags=re.DOTALL)
            parsed = json.loads(json_content)
            logger.info(f"[{debug_info}] JSON extracted from <result> tags")
            return parsed
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug(f"[{debug_info}] Failed to parse <result> tags: {e}")
    return None


def _extract_from_code_blocks(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from markdown code blocks."""
    try:
        # Try ```json first, then ``` without language specifier
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_content = match.group(1).strip()
                parsed = json.loads(json_content)
                logger.info(f"[{debug_info}] JSON extracted from code block")
                return parsed
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug(f"[{debug_info}] Failed to parse code blocks: {e}")
    return None


def _extract_raw_json(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    """Extract raw JSON objects from text."""
    try:
        # Find JSON objects starting with { and ending with }
        # Support nested objects and arrays
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        
        # Try parsing each potential JSON object
        for match in matches:
            try:
                # Clean up the match
                json_content = match.strip()
                # Try to parse - if successful, return
                parsed = json.loads(json_content)
                # Validate it's actually a meaningful object (not just {})
                if parsed and isinstance(parsed, dict) and len(parsed) > 0:
                    logger.info(f"[{debug_info}] JSON extracted as raw object")
                    return parsed
            except json.JSONDecodeError:
                continue
                
        # Try more aggressive pattern for complex nested JSON
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
                    # Found complete JSON object
                    json_content = text[start_idx:i+1]
                    try:
                        parsed = json.loads(json_content)
                        if parsed and isinstance(parsed, dict) and len(parsed) > 0:
                            logger.info(f"[{debug_info}] JSON extracted with brace counting")
                            return parsed
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
                    
    except Exception as e:
        logger.debug(f"[{debug_info}] Failed to parse raw JSON: {e}")
    return None


def _extract_fallback_patterns(text: str, debug_info: str) -> Optional[Dict[str, Any]]:
    """Fallback extraction using various regex patterns."""
    try:
        # Pattern for typical JSON responses with some surrounding text
        fallback_patterns = [
            r'(?:JSON|json|Result|result):\s*(\{.*?\})',
            r'(?:Response|response):\s*(\{.*?\})',
            r'(\{[^{}]*"[^"]*":[^{}]*\})',  # Simple key-value pairs
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    parsed = json.loads(match.strip())
                    if parsed and isinstance(parsed, dict) and len(parsed) > 0:
                        logger.info(f"[{debug_info}] JSON extracted with fallback pattern")
                        return parsed
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logger.debug(f"[{debug_info}] Failed fallback extraction: {e}")
    return None


# Backwards compatibility function name
def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Legacy function name for backwards compatibility."""
    return extract_json_universal(text, "legacy_call")
