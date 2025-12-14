"""Skill Registry - manages skills by tech stack."""
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from app.core.skills.skill_loader import Skill, discover_skills

logger = logging.getLogger(__name__)
SKILLS_DIR = Path(__file__).parent


@dataclass
class SkillRegistry:
    """Registry of skills by tech stack."""
    tech_stack: str
    skills: Dict[str, Skill] = field(default_factory=dict)
    
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        registry = cls(tech_stack=tech_stack)
        stack_dir = SKILLS_DIR / tech_stack
        if stack_dir.exists():
            registry.skills.update(discover_skills(stack_dir))
        
        general_dir = SKILLS_DIR / "general"
        if general_dir.exists():
            for skill_id, skill in discover_skills(general_dir).items():
                if skill_id not in registry.skills:
                    registry.skills[skill_id] = skill
        
        logger.info(f"[SkillRegistry] Loaded {len(registry.skills)} skills for '{tech_stack}'")
        return registry
    
    def get_skill_catalog_for_prompt(self) -> str:
        if not self.skills:
            return ""
        lines = ["## Available Skills", "", "Call `activate_skill(skill_id)` to load instructions.", ""]
        for skill_id, skill in self.skills.items():
            lines.append(f"- **{skill_id.split('.')[-1]}**: {skill.description}")
        return "\n".join(lines)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        if skill_id in self.skills:
            return self.skills[skill_id]
        full_id = f"{self.tech_stack}.{skill_id}"
        if full_id in self.skills:
            return self.skills[full_id]
        for sid, skill in self.skills.items():
            if sid.endswith(f".{skill_id}"):
                return skill
        return None
    
    def get_skill_ids(self) -> List[str]:
        return list(self.skills.keys())
    
    def get_skill_content(self, skill: Skill) -> str:
        return skill.to_prompt_section(include_content=True)
