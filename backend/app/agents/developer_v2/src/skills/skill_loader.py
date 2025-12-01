"""
Skill Loader - Load skills using Anthropic's Agent Skills pattern.

Skills use SKILL.md format with YAML frontmatter for metadata,
following progressive disclosure:
1. Level 1: name + description (loaded at startup)
2. Level 2: Full SKILL.md content (loaded when skill is activated)
3. Level 3+: Bundled files referenced in SKILL.md (loaded as needed)
"""
import logging
import re
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
    triggers: List[str] = field(default_factory=list)
    version: str = "1.0"
    author: str = ""
    
    def matches(self, context: str) -> int:
        """Return match score based on triggers."""
        context_lower = context.lower()
        score = 0
        for trigger in self.triggers:
            if trigger.lower() in context_lower:
                score += 1
        return score


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
    def triggers(self) -> List[str]:
        return self.metadata.triggers
    
    def load_content(self) -> str:
        """Level 2: Load full SKILL.md content (lazy loading)."""
        if self._content is not None:
            return self._content
        
        skill_file = self.skill_dir / "SKILL.md"
        if not skill_file.exists():
            logger.warning(f"[Skill] SKILL.md not found: {skill_file}")
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
            
            logger.debug(f"[Skill] Loaded content for {self.id}: {len(self._content)} chars")
            return self._content
        except Exception as e:
            logger.error(f"[Skill] Failed to load content for {self.id}: {e}")
            return ""
    
    def load_bundled_file(self, filename: str) -> str:
        """Level 3+: Load additional bundled file."""
        if filename in self._bundled_files:
            return self._bundled_files[filename]
        
        file_path = self.skill_dir / filename
        if not file_path.exists():
            logger.warning(f"[Skill] Bundled file not found: {file_path}")
            return ""
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self._bundled_files[filename] = content
            logger.debug(f"[Skill] Loaded bundled file {filename}: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"[Skill] Failed to load {filename}: {e}")
            return ""
    
    def get_referenced_files(self) -> List[str]:
        """Extract referenced files from SKILL.md content."""
        content = self.load_content()
        pattern = r'`([a-zA-Z0-9_\-]+\.(?:md|py|ts|js|yaml|json))`'
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    def list_bundled_files(self) -> List[str]:
        """List all files in skill directory (excluding SKILL.md)."""
        files = []
        for f in self.skill_dir.iterdir():
            if f.is_file() and f.name != "SKILL.md" and not f.name.startswith("__"):
                files.append(f.name)
        return files
    
    def get_scripts(self) -> List[Path]:
        """Get executable scripts bundled with skill."""
        scripts = []
        for f in self.skill_dir.iterdir():
            if f.suffix in ['.py', '.sh', '.js', '.ts']:
                scripts.append(f)
        return scripts
    
    def to_prompt_section(self, include_content: bool = True) -> str:
        """Format skill for prompt injection."""
        if not include_content:
            return f"**{self.name}**: {self.description}"
        
        content = self.load_content()
        return f"""<skill name="{self.id}" description="{self.description}">
{content}
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
            triggers=frontmatter.get('triggers', []),
            version=frontmatter.get('version', '1.0'),
            author=frontmatter.get('author', ''),
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
    """Discover all skills in a directory (recursively)."""
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
                    logger.debug(f"[SkillLoader] Discovered skill: {skill.id}")
            else:
                sub_skills = discover_skills(item)
                skills.update(sub_skills)
    
    return skills


def get_project_structure(tech_stack: str = "nextjs") -> str:
    """Load project-structure.md for a tech stack.
    
    Args:
        tech_stack: Tech stack identifier (e.g., "nextjs")
        
    Returns:
        Content of project-structure.md or empty string if not found
    """
    structure_file = SKILLS_DIR / tech_stack / "project-structure.md"
    
    if not structure_file.exists():
        logger.debug(f"[SkillLoader] No project-structure.md for {tech_stack}")
        return ""
    
    try:
        content = structure_file.read_text(encoding='utf-8')
        logger.debug(f"[SkillLoader] Loaded project structure: {len(content)} chars")
        return content
    except Exception as e:
        logger.error(f"[SkillLoader] Failed to load project structure: {e}")
        return ""
