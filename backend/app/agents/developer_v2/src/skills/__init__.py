"""Skills package - SKILL.md format only (Claude Agent Skills pattern).

Progressive Disclosure:
- Level 1: name + description (loaded at startup)
- Level 2: Full SKILL.md content (loaded when activated)
- Level 3+: Bundled files (loaded as needed)

Usage:
    from app.agents.developer_v2.src.skills import SkillRegistry
    
    registry = SkillRegistry.load("nextjs")
    catalog = registry.get_skill_catalog_for_prompt()
    skill = registry.get_skill("frontend-component")
    content = skill.load_content()  # Level 2
"""

from app.agents.developer_v2.src.skills.skill_loader import (
    Skill,
    SkillMetadata,
    load_skill,
    discover_skills,
    get_project_structure,
)
from app.agents.developer_v2.src.skills.registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillRegistry",
    "load_skill",
    "discover_skills",
    "get_project_structure",
]
