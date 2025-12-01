"""
Skill Registry - manages skills by tech stack.

Supports two formats:
1. SKILL.md (Anthropic Agent Skills pattern) - preferred
2. YAML files (legacy) - backward compatible
"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

from app.agents.developer_v2.src.skills.skill_loader import (
    Skill as MDSkill,
    discover_skills,
    load_skill,
    SkillMetadata,
)

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


@dataclass
class LegacySkill:
    """Legacy YAML-based skill definition (backward compatible)."""
    id: str
    name: str
    description: str
    triggers: List[str]
    role: str
    system_prompt: str
    user_prompt: str
    tech_stack: str
    
    def matches(self, file_path: str, description: str) -> int:
        """Return match score based on triggers."""
        combined = f"{file_path} {description}".lower()
        return sum(1 for t in self.triggers if t.lower() in combined)
    
    def to_prompt_section(self, include_content: bool = True) -> str:
        """Format skill for prompt injection."""
        if not include_content:
            return f"**{self.name}**: {self.description}"
        return f"""<skill name="{self.id}" description="{self.description}">
{self.system_prompt}
</skill>"""


Skill = Union[MDSkill, LegacySkill]


@dataclass
class SkillRegistry:
    """Registry of skills for a specific tech stack.
    
    Supports both SKILL.md (preferred) and YAML (legacy) formats.
    """
    tech_stack: str
    skills: Dict[str, Skill] = field(default_factory=dict)
    _metadata_cache: Dict[str, str] = field(default_factory=dict, repr=False)
    
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        """Load all skills for a tech stack.
        
        Priority: SKILL.md format > YAML format
        
        Args:
            tech_stack: Tech stack identifier (e.g., "nextjs", "django")
            
        Returns:
            SkillRegistry instance with loaded skills
        """
        registry = cls(tech_stack=tech_stack)
        stack_dir = SKILLS_DIR / tech_stack
        
        if not stack_dir.exists():
            logger.warning(f"[SkillRegistry] No skills directory found for '{tech_stack}'")
            return registry
        
        # Load SKILL.md format skills (preferred)
        md_skills = discover_skills(stack_dir)
        for skill_id, skill in md_skills.items():
            registry.skills[skill_id] = skill
            registry._metadata_cache[skill_id] = f"- **{skill.name}**: {skill.description}"
            logger.debug(f"[SkillRegistry] Loaded SKILL.md: {skill_id}")
        
        # Load legacy YAML skills (backward compatible)
        for file in stack_dir.glob("*.yaml"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                skill_id = f"{tech_stack}.{file.stem}"
                
                # Skip if already loaded from SKILL.md
                if skill_id in registry.skills:
                    logger.debug(f"[SkillRegistry] Skipping YAML {skill_id} (SKILL.md exists)")
                    continue
                
                skill = LegacySkill(
                    id=skill_id,
                    name=data.get('name', file.stem),
                    description=data.get('description', ''),
                    triggers=data.get('triggers', []),
                    role=data.get('role', 'Senior Developer'),
                    system_prompt=data.get('system_prompt', ''),
                    user_prompt=data.get('user_prompt', ''),
                    tech_stack=tech_stack,
                )
                registry.skills[skill_id] = skill
                registry._metadata_cache[skill_id] = f"- **{skill.name}**: {skill.description}"
                logger.debug(f"[SkillRegistry] Loaded YAML: {skill_id}")
                
            except Exception as e:
                logger.warning(f"[SkillRegistry] Failed to load {file}: {e}")
        
        # Also load general skills (available for all tech stacks)
        general_dir = SKILLS_DIR / "general"
        if general_dir.exists():
            general_skills = discover_skills(general_dir)
            for skill_id, skill in general_skills.items():
                if skill_id not in registry.skills:
                    registry.skills[skill_id] = skill
                    registry._metadata_cache[skill_id] = f"- **{skill.name}**: {skill.description}"
                    logger.debug(f"[SkillRegistry] Loaded general skill: {skill_id}")
        
        logger.info(f"[SkillRegistry] Loaded {len(registry.skills)} skills for '{tech_stack}'")
        return registry
    
    def get_skill_summaries(self) -> str:
        """Get Level 1 metadata summaries for all skills (for system prompt).
        
        This implements progressive disclosure - only load metadata at startup.
        """
        if not self._metadata_cache:
            return "No skills available."
        
        lines = [f"## Available Skills ({self.tech_stack})"]
        lines.extend(self._metadata_cache.values())
        return "\n".join(lines)
    
    def detect_skill(self, file_path: str, description: str) -> Optional[Skill]:
        """Detect best matching skill based on file path and description.
        
        Args:
            file_path: Path to the file being implemented
            description: Step description from the plan
            
        Returns:
            Best matching Skill or None
        """
        if not self.skills:
            return None
        
        best_skill = None
        best_score = 0
        combined = f"{file_path} {description}"
        
        for skill in self.skills.values():
            # Handle both MDSkill and LegacySkill
            if isinstance(skill, MDSkill):
                score = skill.metadata.matches(combined)
            else:
                score = skill.matches(file_path, description)
            
            if score > best_score:
                best_score = score
                best_skill = skill
        
        if best_skill:
            logger.info(f"[SkillRegistry] Detected skill '{best_skill.id}' (score: {best_score}) for {file_path}")
        
        return best_skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID.
        
        Args:
            skill_id: Full skill ID (e.g., "nextjs.frontend-component")
            
        Returns:
            Skill or None if not found
        """
        return self.skills.get(skill_id)
    
    def get_skill_list(self) -> str:
        """Get formatted list of available skills for prompt injection.
        
        Returns:
            Markdown-formatted string listing all skills
        """
        if not self.skills:
            return "No skills available."
        
        lines = [f"## Available Skills ({self.tech_stack})"]
        for skill in self.skills.values():
            triggers_str = ", ".join(skill.triggers[:5])
            if len(skill.triggers) > 5:
                triggers_str += "..."
            lines.append(f"- **{skill.id}**: {skill.description}")
            lines.append(f"  Triggers: `{triggers_str}`")
        return "\n".join(lines)
    
    def get_skill_ids(self) -> List[str]:
        """Get list of all skill IDs.
        
        Returns:
            List of skill IDs
        """
        return list(self.skills.keys())
    
    def get_skill_prompts(self, skill: Skill, context: Dict[str, str]) -> tuple:
        """Get formatted system and user prompts from skill.
        
        Args:
            skill: Skill instance (MDSkill or LegacySkill)
            context: Dict with keys like step_description, file_path, action, etc.
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        if isinstance(skill, MDSkill):
            # MDSkill: Load full content (Level 2)
            system = skill.load_content()
            user = ""  # MDSkill uses content directly, no separate user prompt
        else:
            # LegacySkill: Use system_prompt and user_prompt
            system = skill.system_prompt
            user = skill.user_prompt
            
            # Format user prompt with context
            for key, value in context.items():
                placeholder = "{" + key + "}"
                user = user.replace(placeholder, str(value) if value else "")
        
        return system, user
    
    def get_skill_content(self, skill: Skill) -> str:
        """Get skill content for prompt injection.
        
        Args:
            skill: Skill instance
            
        Returns:
            Formatted skill content for prompt
        """
        return skill.to_prompt_section(include_content=True)
