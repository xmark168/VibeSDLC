"""Skill Registry - manages skills by tech stack."""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


@dataclass
class Skill:
    """Skill definition."""
    id: str                    # e.g., "nextjs.frontend-component"
    name: str                  # e.g., "Frontend Component"
    description: str
    triggers: List[str]
    role: str
    system_prompt: str
    user_prompt: str
    tech_stack: str            # e.g., "nextjs"
    
    def matches(self, file_path: str, description: str) -> int:
        """Return match score based on triggers."""
        combined = f"{file_path} {description}".lower()
        return sum(1 for t in self.triggers if t.lower() in combined)


@dataclass
class SkillRegistry:
    """Registry of skills for a specific tech stack."""
    tech_stack: str
    skills: Dict[str, Skill] = field(default_factory=dict)
    
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        """Load all skills for a tech stack.
        
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
        
        for file in stack_dir.glob("*.yaml"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                skill_id = f"{tech_stack}.{file.stem}"
                skill = Skill(
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
                logger.debug(f"[SkillRegistry] Loaded skill: {skill_id}")
                
            except Exception as e:
                logger.warning(f"[SkillRegistry] Failed to load {file}: {e}")
        
        logger.info(f"[SkillRegistry] Loaded {len(registry.skills)} skills for '{tech_stack}'")
        return registry
    
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
        
        for skill in self.skills.values():
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
            skill: Skill instance
            context: Dict with keys like step_description, file_path, action, etc.
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = skill.system_prompt
        user = skill.user_prompt
        
        # Format user prompt with context
        for key, value in context.items():
            placeholder = "{" + key + "}"
            user = user.replace(placeholder, str(value) if value else "")
        
        return system, user
