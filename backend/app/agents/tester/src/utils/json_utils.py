"""JSON parsing utilities for Tester Agent."""

import json
import logging
import re
from typing import Any, Union

logger = logging.getLogger(__name__)


def parse_json_safe(content: str) -> Union[dict, list, None]:
    """Parse JSON from LLM response with fallback extraction.
    
    Args:
        content: Raw LLM response
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    if not content:
        return None
        
    # Try direct parse first
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    # Extract from markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[parse_json_safe] Failed: {content[:300]}...")
        return None


def extract_json_universal(text: str, context: str = "") -> dict:
    """Extract JSON from LLM response using multiple strategies.
    
    Strategies:
    1. Direct JSON parse
    2. Extract from <result> tags
    3. Extract from markdown code blocks
    4. Regex extraction for JSON objects
    
    Args:
        text: Raw LLM response
        context: Context name for logging
        
    Returns:
        Parsed JSON dict (empty dict if all strategies fail)
    """
    if not text:
        return {}
    
    # Strategy 1: Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from <result> tags
    result_match = re.search(r'<result>\s*(.*?)\s*</result>', text, re.DOTALL)
    if result_match:
        try:
            return json.loads(result_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Extract from markdown code blocks
    code_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]
    for pattern in code_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue
    
    # Strategy 4: Find JSON object with regex
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"[extract_json_universal] [{context}] All strategies failed: {text[:200]}...")
    return {}
