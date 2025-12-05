#!/usr/bin/env python
"""Standalone test runner for Developer V2 Skills.

Run: uv run python app/agents/developer_v2/tests/run_tests.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Import skills module (no heavy dependencies)
from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills.skill_loader import Skill, discover_skills


def test_skill_registry():
    """Test SkillRegistry loading."""
    print("\n=== TestSkillRegistry ===")
    
    # Test load
    registry = SkillRegistry.load("nextjs")
    assert len(registry.skills) > 0, "Should load skills"
    assert registry.tech_stack == "nextjs"
    print(f"[PASS] Loaded {len(registry.skills)} skills for nextjs")
    print(f"       Skills: {list(registry.skills.keys())}")
    
    # Test get skill
    skill = registry.get_skill("frontend-component")
    assert skill is not None, "Should find frontend-component skill"
    print(f"[PASS] Found skill: {skill.id}")
    
    # Test skill content (Level 2)
    content = skill.load_content()
    assert content and len(content) > 100, "Should have content"
    print(f"[PASS] Skill content loaded: {len(content)} chars")
    
    # Test catalog for prompt
    catalog = registry.get_skill_catalog_for_prompt()
    assert "Available Skills" in catalog
    print(f"[PASS] Catalog generated: {len(catalog)} chars")


def test_bundled_files():
    """Test bundled files loading (Level 3)."""
    print("\n=== TestBundledFiles ===")
    
    registry = SkillRegistry.load("nextjs")
    skill = registry.get_skill("frontend-component")
    
    # Test list bundled files
    files = skill.list_bundled_files()
    assert isinstance(files, list)
    print(f"[PASS] list_bundled_files(): {files}")
    
    # Test read bundled file if exists
    if files:
        content = skill.load_bundled_file(files[0])
        assert content and len(content) > 0
        print(f"[PASS] load_bundled_file('{files[0]}'): {len(content)} chars")
    else:
        print("[SKIP] No bundled files to test")
    
    # Test nonexistent file returns empty
    content = skill.load_bundled_file("nonexistent.md")
    assert content == ""
    print("[PASS] Nonexistent file returns empty string")


def test_skill_discovery():
    """Test skill discovery from directory."""
    print("\n=== TestSkillDiscovery ===")
    
    skills_dir = Path(__file__).parent.parent / "src" / "skills" / "nextjs"
    if skills_dir.exists():
        skills = discover_skills(skills_dir)
        assert len(skills) > 0, "Should discover skills"
        print(f"[PASS] Discovered {len(skills)} skills from {skills_dir.name}/")
        for sid, skill in skills.items():
            print(f"       - {sid}: {skill.description[:50]}...")
    else:
        print(f"[SKIP] Skills dir not found: {skills_dir}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Developer V2 Skills Tests")
    print("=" * 60)
    
    try:
        test_skill_registry()
        test_bundled_files()
        test_skill_discovery()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
