"""Tests for Developer V2 Skills System.

Run with: uv run pytest app/agents/developer_v2/tests/test_skills.py -v
"""
import pytest
from pathlib import Path

from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills.skill_loader import Skill, discover_skills


class TestSkillRegistry:
    """Test SkillRegistry loading."""
    
    def test_load_nextjs_skills(self):
        """Should load skills for nextjs tech stack."""
        registry = SkillRegistry.load("nextjs")
        assert len(registry.skills) > 0
        assert registry.tech_stack == "nextjs"
    
    def test_get_skill_by_id(self):
        """Should get skill by ID."""
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("frontend-component")
        assert skill is not None
        assert "frontend" in skill.id.lower()
    
    def test_skill_has_content(self):
        """Should load skill content (SKILL.md)."""
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("frontend-component")
        content = skill.load_content()
        assert content is not None
        assert len(content) > 100
    
    def test_skill_catalog_for_prompt(self):
        """Should generate skill catalog for LLM prompt."""
        registry = SkillRegistry.load("nextjs")
        catalog = registry.get_skill_catalog_for_prompt()
        assert "Available Skills" in catalog
        assert "activate_skill" in catalog


class TestBundledFiles:
    """Test bundled files loading (Level 3)."""
    
    def test_list_bundled_files(self):
        """Should list bundled files for a skill."""
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("frontend-component")
        files = skill.list_bundled_files()
        assert isinstance(files, list)
        assert len(files) > 0  # frontend-component has bundled files
    
    def test_read_bundled_file(self):
        """Should read bundled file."""
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("frontend-component")
        files = skill.list_bundled_files()
        
        content = skill.load_bundled_file(files[0])
        assert content is not None
        assert len(content) > 0
    
    def test_read_nonexistent_file(self):
        """Should return empty string for nonexistent file."""
        registry = SkillRegistry.load("nextjs")
        skill = registry.get_skill("frontend-component")
        content = skill.load_bundled_file("nonexistent.md")
        assert content == ""


class TestSkillDiscovery:
    """Test skill discovery."""
    
    def test_discover_skills_from_directory(self):
        """Should discover skills from nextjs directory."""
        skills_dir = Path(__file__).parent.parent / "src" / "skills" / "nextjs"
        skills = discover_skills(skills_dir)
        assert len(skills) > 0
        assert any("frontend-component" in sid for sid in skills.keys())
    
    def test_skill_has_metadata(self):
        """Each skill should have name and description."""
        registry = SkillRegistry.load("nextjs")
        for skill_id, skill in registry.skills.items():
            assert skill.name, f"Skill {skill_id} missing name"
            assert skill.description, f"Skill {skill_id} missing description"
