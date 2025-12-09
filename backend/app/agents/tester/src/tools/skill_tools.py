"""Skill Tools for Tester Agent - Activate testing skills dynamically.

Implements progressive disclosure:
- Level 1: Skill catalog in system prompt (name + description)
- Level 2: activate_skill() returns full SKILL.md content
- Level 3: read_skill_file() returns bundled files
"""
import logging
from typing import Optional

from langchain_core.tools import tool

from app.agents.tester.src.skills import SkillRegistry

logger = logging.getLogger(__name__)

# Global skill registry (set by set_skill_context)
_skill_registry: Optional[SkillRegistry] = None

# Cache activated skills (prevents duplicate activations)
_activated_skills_cache: dict[str, str] = {}


def set_skill_context(registry: SkillRegistry):
    """Set the skill registry for tools to use."""
    global _skill_registry
    _skill_registry = registry
    logger.debug(f"[skill_tools] Context set: {len(registry.skills)} skills")


def reset_skill_cache():
    """Reset skill activation cache. Call at start of each test generation."""
    global _activated_skills_cache
    _activated_skills_cache = {}


def get_skill_catalog() -> str:
    """Get skill catalog for prompt injection."""
    if not _skill_registry:
        return ""
    return _skill_registry.get_skill_catalog_for_prompt()


@tool
def activate_skill(skill_id: str) -> str:
    """Activate a testing skill to get specialized instructions.
    
    Call this to load detailed testing patterns and examples for a specific type of test.
    
    Available skills:
    - integration-test: Jest integration tests for API routes and database operations
    
    Args:
        skill_id: The skill to activate (e.g., "integration-test")
    
    Returns:
        Detailed testing instructions, patterns, and examples for the skill
    """
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    # Check cache
    if skill_id in _activated_skills_cache:
        logger.info(f"[skill_tools] Skill '{skill_id}' already activated (cached)")
        return _activated_skills_cache[skill_id]
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        available = ", ".join(_skill_registry.get_skill_ids())
        return f"Skill '{skill_id}' not found. Available skills: {available}"
    
    content = skill.load_content()
    if not content:
        return f"Skill '{skill_id}' has no content"
    
    logger.info(f"[skill_tools] Activated skill: {skill_id} ({len(content)} chars)")
    
    # Build result
    bundled_files = skill.list_bundled_files()
    result = f"""[SKILL ACTIVATED: {skill_id}]

{content}

---
Bundled reference files: {', '.join(bundled_files) or 'None'}
Use read_skill_file("{skill_id}", "filename.md") to read additional references."""
    
    # Cache
    _activated_skills_cache[skill_id] = result
    return result


@tool
def read_skill_file(skill_id: str, filename: str) -> str:
    """Read a reference file bundled with a skill.
    
    Use this to access additional examples, patterns, or documentation bundled with a skill.
    Only call after activate_skill() if you need more detailed information.
    
    Args:
        skill_id: The skill ID (e.g., "integration-test")
        filename: The file to read (e.g., "mock-patterns.md", "page-objects.md")
    
    Returns:
        Content of the reference file
    """
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        return f"Skill '{skill_id}' not found"
    
    # Try with and without references/ prefix
    content = skill.load_bundled_file(f"references/{filename}")
    if not content:
        content = skill.load_bundled_file(filename)
    
    if not content:
        available = skill.list_references()
        return f"File '{filename}' not found in skill '{skill_id}'. Available: {', '.join(available) or 'None'}"
    
    logger.info(f"[skill_tools] Read file: {skill_id}/{filename} ({len(content)} chars)")
    return content


@tool
def list_skill_files(skill_id: str) -> str:
    """List all reference files available in a skill.
    
    Args:
        skill_id: The skill ID
    
    Returns:
        List of available reference files
    """
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        return f"Skill '{skill_id}' not found"
    
    files = skill.list_bundled_files()
    if not files:
        return f"Skill '{skill_id}' has no additional reference files."
    
    return f"Reference files in skill '{skill_id}':\n" + "\n".join(f"- {f}" for f in files)


# Tool registry
SKILL_TOOLS = [
    activate_skill,
    read_skill_file,
    list_skill_files,
]


def get_skill_tools():
    """Get list of skill tools for agent."""
    return SKILL_TOOLS
