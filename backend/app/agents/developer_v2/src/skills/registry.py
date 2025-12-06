"""Skill Registry - manages skills by tech stack (Anthropic Agent Skills pattern).

This module provides the SkillRegistry class that organizes and provides
access to skills for a specific technology stack (e.g., Next.js, Python).
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from app.agents.developer_v2.src.skills.skill_loader import (
    Skill,
    discover_skills,
)

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


@dataclass
class SkillRegistry:
    """Registry of skills by tech stack. Loads from skills/{tech_stack}/ + general/."""
    tech_stack: str
    skills: Dict[str, Skill] = field(default_factory=dict)
    
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        """Load all skills for a tech stack."""
        registry = cls(tech_stack=tech_stack)
        stack_dir = SKILLS_DIR / tech_stack
        
        if stack_dir.exists():
            skills = discover_skills(stack_dir)
            registry.skills.update(skills)
        
        # Load general skills (available for all tech stacks)
        general_dir = SKILLS_DIR / "general"
        if general_dir.exists():
            general_skills = discover_skills(general_dir)
            for skill_id, skill in general_skills.items():
                if skill_id not in registry.skills:
                    registry.skills[skill_id] = skill
        
        logger.info(f"[SkillRegistry] Loaded {len(registry.skills)} skills for '{tech_stack}'")
        return registry
    
    def get_skill_catalog_for_prompt(self) -> str:
        """Get skill catalog for system prompt (Level 1 - metadata only).
        
        Claude uses this to know what skills exist and when to activate them.
        """
        if not self.skills:
            return ""
        
        lines = ["## Available Skills", ""]
        lines.append("Call `activate_skill(skill_id)` to load instructions.")
        lines.append("")
        for skill_id, skill in self.skills.items():
            short_id = skill_id.split(".")[-1]
            lines.append(f"- **{short_id}**: {skill.description}")
        return "\n".join(lines)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        # Exact match
        if skill_id in self.skills:
            return self.skills[skill_id]
        
        # With tech_stack prefix
        full_id = f"{self.tech_stack}.{skill_id}"
        if full_id in self.skills:
            return self.skills[full_id]
        
        # Partial match
        for sid, skill in self.skills.items():
            if sid.endswith(f".{skill_id}"):
                return skill
        
        return None
    
    def get_skill_ids(self) -> List[str]:
        """Get list of all skill IDs."""
        return list(self.skills.keys())
    
    def get_skill_content(self, skill: Skill) -> str:
        """Get skill content for injection (Level 2)."""
        return skill.to_prompt_section(include_content=True)
