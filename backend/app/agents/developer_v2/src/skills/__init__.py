"""Skills package for developer_v2.

Skills are specialized prompt packages organized by tech stack.
Each skill defines role, system_prompt, and user_prompt for specific task types.

Usage:
    from app.agents.developer_v2.src.skills import SkillRegistry, Skill
    
    # Load skills for a tech stack
    registry = SkillRegistry.load("nextjs")
    
    # Get available skills
    skills_list = registry.get_skill_list()
    
    # Detect skill for a file
    skill = registry.detect_skill("src/components/Button.tsx", "Create button component")
    
    # Get skill by ID
    skill = registry.get_skill("nextjs.frontend-component")
"""

from app.agents.developer_v2.src.skills.registry import Skill, SkillRegistry

__all__ = ["Skill", "SkillRegistry"]
