"""Test skill loading - verify reference files work.

Run directly:
    python backend/app/agents/developer_v2/tests/test_skill_tools.py
    
This test directly uses skill_loader to avoid import issues.
"""
from pathlib import Path

# Skills directory
SKILLS_DIR = Path(__file__).parent.parent / "src" / "skills"


def test_skill_has_references():
    """frontend-component skill should have reference files."""
    skill_dir = SKILLS_DIR / "nextjs" / "frontend-component"
    refs_dir = skill_dir / "references"
    
    assert skill_dir.exists(), f"Skill dir not found: {skill_dir}"
    assert refs_dir.exists(), f"References dir not found: {refs_dir}"
    
    ref_files = list(refs_dir.glob("*.md"))
    assert len(ref_files) >= 1, f"No reference files found in {refs_dir}"
    
    print("[PASS] test_skill_has_references")
    print(f"   Found {len(ref_files)} reference files:")
    for f in ref_files:
        print(f"   - {f.name}")


def test_reference_content_readable():
    """Reference files should be readable and have content."""
    forms_path = SKILLS_DIR / "nextjs" / "frontend-component" / "references" / "forms.md"
    
    assert forms_path.exists(), f"forms.md not found at {forms_path}"
    
    content = forms_path.read_text(encoding='utf-8')
    assert len(content) > 100, f"forms.md too short: {len(content)} chars"
    
    print("[PASS] test_reference_content_readable")
    print(f"   forms.md has {len(content)} chars")


def test_debugging_has_references():
    """debugging skill should have error-handling reference."""
    refs_dir = SKILLS_DIR / "general" / "debugging" / "references"
    
    assert refs_dir.exists(), f"References dir not found: {refs_dir}"
    
    error_patterns = refs_dir / "error-handling-patterns.md"
    assert error_patterns.exists(), f"error-handling-patterns.md not found"
    
    content = error_patterns.read_text(encoding='utf-8')
    assert len(content) > 100, f"Content too short: {len(content)} chars"
    
    print("[PASS] test_debugging_has_references")
    print(f"   error-handling-patterns.md has {len(content)} chars")


def test_skill_follows_format():
    """SKILL.md should follow the standard format with opening prose."""
    skill_md = SKILLS_DIR / "nextjs" / "frontend-component" / "SKILL.md"
    
    content = skill_md.read_text(encoding='utf-8')
    
    # Check for opening prose paragraph (not jumping straight to ## headers)
    lines = content.split('\n')
    found_prose = False
    for line in lines:
        if line.startswith('---'):
            continue
        if line.startswith('#') and not line.startswith('##'):
            continue
        if line.strip() and not line.startswith('##') and not line.startswith('name:') and not line.startswith('description:'):
            found_prose = True
            break
    
    assert found_prose, "SKILL.md should have opening prose paragraph"
    assert "CRITICAL" in content or "IMPORTANT" in content, "SKILL.md should have CRITICAL/IMPORTANT callout"
    assert "NEVER" in content, "SKILL.md should have NEVER section"
    
    print("[PASS] test_skill_follows_format")
    print("   SKILL.md follows standard format with prose and callouts")


if __name__ == "__main__":
    print("\n=== Running Skill Reference Tests ===\n")
    
    tests = [
        test_skill_has_references,
        test_reference_content_readable,
        test_debugging_has_references,
        test_skill_follows_format,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
        print()
    
    print(f"\n=== Results: {passed} passed, {failed} failed ===")
