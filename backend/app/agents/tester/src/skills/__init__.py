"""Skills package for Tester Agent - SKILL.md format (Anthropic Agent Skills pattern).

Progressive Disclosure:
- Level 1: name + description (loaded at startup)
- Level 2: Full SKILL.md content (loaded when activated)
- Level 3+: Bundled files (loaded as needed)

Usage:
    from app.agents.tester.src.skills import SkillRegistry
    
    registry = SkillRegistry.load("nextjs")
    catalog = registry.get_skill_catalog_for_prompt()
    skill = registry.get_skill("integration-test")
    content = skill.load_content()  # Level 2
"""

from app.agents.tester.src.skills.skill_loader import (
    Skill,
    SkillMetadata,
    load_skill,
    discover_skills,
)
from app.agents.tester.src.skills.registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillRegistry",
    "load_skill",
    "discover_skills",
]
