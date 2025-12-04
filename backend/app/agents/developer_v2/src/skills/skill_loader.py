"""
Skill Loader - Load skills using Anthropic's Agent Skills pattern.

Skills use SKILL.md format with YAML frontmatter:
- name: skill identifier
- description: what the skill does and when to use it

Progressive disclosure:
1. Level 1: name + description (loaded at startup for catalog)
2. Level 2: Full SKILL.md body (loaded when skill is activated)
3. Level 3: Bundled files in references/, scripts/, assets/ (loaded as needed)
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


@dataclass
class SkillMetadata:
    """Level 1: Skill metadata from YAML frontmatter."""
    name: str
    description: str
    internal: bool = False  # If True, skill is hidden from catalog (used internally by nodes)
    
    def matches(self, context: str) -> int:
        """Return match score based on description keywords."""
        context_lower = context.lower()
        desc_lower = self.description.lower()
        # Simple keyword matching from description
        keywords = [w for w in desc_lower.split() if len(w) > 3]
        return sum(1 for kw in keywords if kw in context_lower)


@dataclass
class Skill:
    """Full skill definition with progressive disclosure."""
    id: str
    metadata: SkillMetadata
    skill_dir: Path
    
    _content: Optional[str] = field(default=None, repr=False)
    _bundled_files: Dict[str, str] = field(default_factory=dict, repr=False)
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def description(self) -> str:
        return self.metadata.description
    
    @property
    def internal(self) -> bool:
        return self.metadata.internal
    
    def load_content(self) -> str:
        """Level 2: Load full SKILL.md body (lazy loading)."""
        if self._content is not None:
            return self._content
        
        skill_file = self.skill_dir / "SKILL.md"
        if not skill_file.exists():
            return ""
        
        try:
            content = skill_file.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    self._content = parts[2].strip()
                else:
                    self._content = content
            else:
                self._content = content
            return self._content
        except Exception as e:
            logger.error(f"[Skill] Failed to load content for {self.id}: {e}")
            return ""
    
    def load_reference(self, filename: str) -> str:
        """Level 3: Load file from references/ directory."""
        return self.load_bundled_file(f"references/{filename}")
    
    def load_bundled_file(self, filepath: str) -> str:
        """Load any bundled file by path (e.g., 'references/forms.md')."""
        if filepath in self._bundled_files:
            return self._bundled_files[filepath]
        
        file_path = self.skill_dir / filepath
        if not file_path.exists():
            return ""
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self._bundled_files[filepath] = content
            return content
        except Exception as e:
            logger.error(f"[Skill] Failed to load {filepath}: {e}")
            return ""
    
    def list_references(self) -> List[str]:
        """List files in references/ directory."""
        refs_dir = self.skill_dir / "references"
        if not refs_dir.exists():
            return []
        return [f.name for f in refs_dir.iterdir() if f.is_file()]
    
    def list_scripts(self) -> List[str]:
        """List files in scripts/ directory."""
        scripts_dir = self.skill_dir / "scripts"
        if not scripts_dir.exists():
            return []
        return [f.name for f in scripts_dir.iterdir() if f.is_file()]
    
    def list_assets(self) -> List[str]:
        """List files in assets/ directory."""
        assets_dir = self.skill_dir / "assets"
        if not assets_dir.exists():
            return []
        return [f.name for f in assets_dir.iterdir() if f.is_file()]
    
    def list_bundled_files(self) -> List[str]:
        """List all bundled files (references + scripts + assets)."""
        files = []
        files.extend([f"references/{f}" for f in self.list_references()])
        files.extend([f"scripts/{f}" for f in self.list_scripts()])
        files.extend([f"assets/{f}" for f in self.list_assets()])
        return files
    
    def to_prompt_section(self, include_content: bool = True) -> str:
        """Format skill for prompt injection."""
        if not include_content:
            return f"**{self.name}**: {self.description}"
        
        content = self.load_content()
        refs = self.list_references()
        refs_note = f"\n\nAvailable references: {', '.join(refs)}" if refs else ""
        
        return f"""<skill name="{self.id}" description="{self.description}">
{content}{refs_note}
</skill>"""


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter or {}, body
    except yaml.YAMLError as e:
        logger.error(f"[SkillLoader] Invalid YAML frontmatter: {e}")
        return {}, content


def load_skill_metadata(skill_dir: Path) -> Optional[SkillMetadata]:
    """Load skill metadata from SKILL.md frontmatter (Level 1)."""
    skill_file = skill_dir / "SKILL.md"
    
    if not skill_file.exists():
        return None
    
    try:
        content = skill_file.read_text(encoding='utf-8')
        frontmatter, _ = parse_frontmatter(content)
        
        if not frontmatter.get('name'):
            logger.warning(f"[SkillLoader] Missing 'name' in {skill_file}")
            return None
        
        return SkillMetadata(
            name=frontmatter.get('name', skill_dir.name),
            description=frontmatter.get('description', ''),
            internal=frontmatter.get('internal', False),
        )
    except Exception as e:
        logger.error(f"[SkillLoader] Failed to load metadata from {skill_file}: {e}")
        return None


def load_skill(skill_dir: Path, tech_stack: str = "") -> Optional[Skill]:
    """Load a skill from directory."""
    metadata = load_skill_metadata(skill_dir)
    if not metadata:
        return None
    
    skill_id = f"{tech_stack}.{skill_dir.name}" if tech_stack else skill_dir.name
    
    return Skill(
        id=skill_id,
        metadata=metadata,
        skill_dir=skill_dir,
    )


def discover_skills(base_dir: Path) -> Dict[str, Skill]:
    """Discover all skills in a directory."""
    skills = {}
    
    if not base_dir.exists():
        return skills
    
    for item in base_dir.iterdir():
        if item.is_dir() and not item.name.startswith('__'):
            skill_file = item / "SKILL.md"
            
            if skill_file.exists():
                skill = load_skill(item, tech_stack=base_dir.name)
                if skill:
                    skills[skill.id] = skill
                    logger.debug(f"[SkillLoader] Discovered: {skill.id}")
            else:
                # Check subdirectories
                sub_skills = discover_skills(item)
                skills.update(sub_skills)
    
    return skills


def get_project_structure(tech_stack: str = "nextjs") -> str:
    """Load project-structure.md for a tech stack."""
    structure_file = SKILLS_DIR / tech_stack / "project-structure.md"
    
    if not structure_file.exists():
        return ""
    
    try:
        return structure_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"[SkillLoader] Failed to load project structure: {e}")
        return ""


def get_plan_prompts(tech_stack: str = "nextjs") -> dict:
    """Load plan_prompts.yaml for a tech stack.
    
    Returns:
        dict with 'system_prompt' and 'input_template' keys
    """
    prompts_file = SKILLS_DIR / tech_stack / "plan_prompts.yaml"
    
    if not prompts_file.exists():
        return {"system_prompt": "", "input_template": ""}
    
    try:
        import yaml
        content = prompts_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)
        return {
            "system_prompt": data.get("system_prompt", ""),
            "input_template": data.get("input_template", ""),
        }
    except Exception as e:
        logger.error(f"[SkillLoader] Failed to load plan prompts: {e}")
        return {"system_prompt": "", "input_template": ""}
