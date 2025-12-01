"""Skill Registry - manages skills by tech stack (SKILL.md format only)."""
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
    """Registry of skills for a specific tech stack."""
    tech_stack: str
    skills: Dict[str, Skill] = field(default_factory=dict)
    _metadata_cache: Dict[str, str] = field(default_factory=dict, repr=False)
    
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        """Load all skills for a tech stack."""
        registry = cls(tech_stack=tech_stack)
        stack_dir = SKILLS_DIR / tech_stack
        
        if not stack_dir.exists():
            logger.warning(f"[SkillRegistry] No skills directory for '{tech_stack}'")
            return registry
        
        # Load SKILL.md format skills
        md_skills = discover_skills(stack_dir)
        for skill_id, skill in md_skills.items():
            registry.skills[skill_id] = skill
            registry._metadata_cache[skill_id] = f"- **{skill.name}**: {skill.description}"
        
        # Load general skills (available for all tech stacks)
        general_dir = SKILLS_DIR / "general"
        if general_dir.exists():
            general_skills = discover_skills(general_dir)
            for skill_id, skill in general_skills.items():
                if skill_id not in registry.skills:
                    registry.skills[skill_id] = skill
                    registry._metadata_cache[skill_id] = f"- **{skill.name}**: {skill.description}"
        
        logger.info(f"[SkillRegistry] Loaded {len(registry.skills)} skills for '{tech_stack}'")
        return registry
    
    def get_skill_catalog(self) -> str:
        """Get skill catalog for LLM to choose from (Level 1 metadata)."""
        if not self.skills:
            return "No skills available."
        
        lines = [f"## Available Skills ({self.tech_stack})", ""]
        for skill_id, skill in self.skills.items():
            lines.append(f"- **{skill_id}**: {skill.description}")
        lines.append("")
        lines.append("Use `required_skill` field in each step to specify which skill to use.")
        return "\n".join(lines)
    
    def detect_skill(self, file_path: str, description: str) -> Optional[Skill]:
        """Detect best matching skill based on triggers (fallback if LLM didn't specify)."""
        if not self.skills:
            return None
        
        best_skill = None
        best_score = 0
        combined = f"{file_path} {description}"
        
        for skill in self.skills.values():
            score = skill.metadata.matches(combined)
            if score > best_score:
                best_score = score
                best_skill = skill
        
        if best_skill:
            logger.info(f"[SkillRegistry] Auto-detected skill '{best_skill.id}' (score: {best_score})")
        
        return best_skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        # Try exact match first
        if skill_id in self.skills:
            return self.skills[skill_id]
        
        # Try with tech_stack prefix
        full_id = f"{self.tech_stack}.{skill_id}"
        if full_id in self.skills:
            return self.skills[full_id]
        
        # Try partial match (e.g., "frontend-component" -> "nextjs.frontend-component")
        for sid, skill in self.skills.items():
            if sid.endswith(f".{skill_id}") or sid == skill_id:
                return skill
        
        return None
    
    def get_skill_ids(self) -> List[str]:
        """Get list of all skill IDs."""
        return list(self.skills.keys())
    
    def get_skill_content(self, skill: Skill) -> str:
        """Get skill content for injection (Level 2)."""
        return skill.to_prompt_section(include_content=True)
