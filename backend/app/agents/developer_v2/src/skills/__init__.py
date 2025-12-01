"""Skills package for developer_v2.

Skills are specialized prompt packages organized by tech stack.
Supports two formats:
1. SKILL.md (Anthropic Agent Skills pattern) - preferred
2. YAML files (legacy) - backward compatible

Progressive Disclosure:
- Level 1: name + description (loaded at startup)
- Level 2: Full SKILL.md content (loaded when activated)
- Level 3+: Bundled files (loaded as needed)

Usage:
    from app.agents.developer_v2.src.skills import SkillRegistry, Skill
    
    # Load skills for a tech stack
    registry = SkillRegistry.load("nextjs")
    
    # Get skill summaries for system prompt (Level 1)
    summaries = registry.get_skill_summaries()
    
    # Get available skills list
    skills_list = registry.get_skill_list()
    
    # Detect skill for a file
    skill = registry.detect_skill("src/components/Button.tsx", "Create button component")
    
    # Get skill by ID
    skill = registry.get_skill("nextjs.frontend-component")
    
    # Get skill content for prompt injection (Level 2)
    content = registry.get_skill_content(skill)
"""

from app.agents.developer_v2.src.skills.registry import Skill, SkillRegistry, LegacySkill
from app.agents.developer_v2.src.skills.skill_loader import (
    Skill as MDSkill,
    SkillMetadata,
    load_skill,
    discover_skills,
    get_project_structure,
)

__all__ = [
    "Skill",
    "SkillRegistry",
    "LegacySkill",
    "MDSkill",
    "SkillMetadata",
    "load_skill",
    "discover_skills",
    "get_project_structure",
]
