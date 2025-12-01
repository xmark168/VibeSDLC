"""Skill Tools - Claude-driven skill activation (Anthropic Agent Skills pattern).

Tools for Claude to discover and activate skills dynamically.
Implements progressive disclosure:
- Level 1: Skill catalog in system prompt (name + description)
- Level 2: activate_skill() returns full SKILL.md content
- Level 3: read_skill_file() returns bundled files
"""
import logging
from typing import Optional
from langchain_core.tools import tool

from app.agents.developer_v2.src.skills import SkillRegistry

logger = logging.getLogger(__name__)

# Global skill registry (set by set_skill_context)
_skill_registry: Optional[SkillRegistry] = None

# Cache activated skills per step (prevents duplicate activations)
_activated_skills_cache: dict[str, str] = {}


def set_skill_context(registry: SkillRegistry):
    """Set the skill registry for tools to use."""
    global _skill_registry
    _skill_registry = registry
    logger.debug(f"[skill_tools] Context set: {len(registry.skills)} skills")


def reset_skill_cache():
    """Reset skill activation cache. Call at start of each implement step."""
    global _activated_skills_cache
    _activated_skills_cache = {}


@tool
def activate_skill(skill_id: str) -> str:
    """Activate a skill to get specialized coding instructions and patterns.
    
    Call this BEFORE writing code when you need domain-specific guidance.
    Skills provide conventions, best practices, and examples.
    
    Args:
        skill_id: Skill ID from the catalog (e.g., "frontend-component", "api-route")
    
    Returns:
        Full skill instructions with patterns and examples
    """
    # Check cache first (prevents duplicate activations in same step)
    if skill_id in _activated_skills_cache:
        logger.info(f"[skill_tools] Skill '{skill_id}' already activated (cached)")
        return _activated_skills_cache[skill_id]
    
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        available = ", ".join(_skill_registry.get_skill_ids())
        return f"Error: Skill '{skill_id}' not found. Available: {available}"
    
    content = skill.load_content()
    if not content:
        return f"Error: Skill '{skill_id}' has no content"
    
    logger.info(f"[skill_tools] Activated skill: {skill_id} ({len(content)} chars)")
    
    # Build result
    result = f"""[SKILL ACTIVATED: {skill_id}]

{content}

---
Bundled files available: {', '.join(skill.list_bundled_files()) or 'None'}
Use read_skill_file("{skill_id}", "filename") to read additional files."""
    
    # Cache for this step
    _activated_skills_cache[skill_id] = result
    return result


@tool
def read_skill_file(skill_id: str, filename: str) -> str:
    """Read additional file bundled with a skill.
    
    Use this to access examples, references, or scripts bundled with a skill.
    Only call after activate_skill() if you need more context.
    
    Args:
        skill_id: Skill ID (e.g., "frontend-component")
        filename: File to read (e.g., "examples.md", "patterns.md")
    
    Returns:
        File content
    """
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        return f"Error: Skill '{skill_id}' not found"
    
    content = skill.load_bundled_file(filename)
    if not content:
        available = skill.list_bundled_files()
        return f"Error: File '{filename}' not found in skill '{skill_id}'. Available: {', '.join(available) or 'None'}"
    
    logger.info(f"[skill_tools] Read bundled file: {skill_id}/{filename} ({len(content)} chars)")
    return content


@tool
def list_skill_files(skill_id: str) -> str:
    """List all files bundled with a skill.
    
    Args:
        skill_id: Skill ID
    
    Returns:
        List of available files
    """
    if not _skill_registry:
        return "Error: Skill registry not initialized"
    
    skill = _skill_registry.get_skill(skill_id)
    if not skill:
        return f"Error: Skill '{skill_id}' not found"
    
    files = skill.list_bundled_files()
    if not files:
        return f"Skill '{skill_id}' has no additional bundled files."
    
    return f"Files in skill '{skill_id}':\n" + "\n".join(f"- {f}" for f in files)
