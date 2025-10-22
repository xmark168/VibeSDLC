#!/usr/bin/env python3
"""
Test script to verify full-file regeneration approach.
"""

import sys
import os

# Test the new prompt template
def test_prompt_template():
    """Test that the new prompt template is correctly formatted"""
    print("=" * 60)
    print("Testing Full-File Regeneration Prompt Template")
    print("=" * 60)
    
    sys.path.append('ai-agent-service/app/agents/developer/implementor/utils')
    
    try:
        from prompts import BACKEND_FILE_MODIFICATION_PROMPT
        
        print("\n✅ Successfully imported BACKEND_FILE_MODIFICATION_PROMPT")
        print(f"📏 Prompt length: {len(BACKEND_FILE_MODIFICATION_PROMPT)} chars")
        
        # Check for key phrases that indicate full-file regeneration
        key_phrases = [
            "FULL FILE REGENERATION",
            "PRESERVE ALL EXISTING CODE",
            "Return the ENTIRE file",
            "COMPLETE file content",
            "DO NOT use the OLD_CODE/NEW_CODE format",
        ]
        
        found_phrases = []
        missing_phrases = []
        
        for phrase in key_phrases:
            if phrase in BACKEND_FILE_MODIFICATION_PROMPT:
                found_phrases.append(phrase)
            else:
                missing_phrases.append(phrase)
        
        print(f"\n✅ Found {len(found_phrases)}/{len(key_phrases)} key phrases:")
        for phrase in found_phrases:
            print(f"   ✓ {phrase}")
        
        if missing_phrases:
            print(f"\n⚠️ Missing {len(missing_phrases)} key phrases:")
            for phrase in missing_phrases:
                print(f"   ✗ {phrase}")
        
        # Check that OLD_CODE/NEW_CODE instructions are removed
        old_approach_phrases = [
            "MODIFICATION #1:",
            "Each modification must use the EXACT format",
        ]
        
        old_found = []
        for phrase in old_approach_phrases:
            if phrase in BACKEND_FILE_MODIFICATION_PROMPT:
                old_found.append(phrase)
        
        if old_found:
            print(f"\n⚠️ Warning: Found {len(old_found)} old approach phrases (should be removed):")
            for phrase in old_found:
                print(f"   ! {phrase}")
        else:
            print(f"\n✅ Old approach phrases successfully removed")
        
        # Print a sample of the prompt
        print(f"\n📄 Prompt preview (first 500 chars):")
        print("-" * 60)
        print(BACKEND_FILE_MODIFICATION_PROMPT[:500])
        print("-" * 60)
        
        return len(missing_phrases) == 0 and len(old_found) == 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generate_code_logic():
    """Test that generate_code.py uses the new approach"""
    print("\n" + "=" * 60)
    print("Testing Generate Code Logic")
    print("=" * 60)
    
    try:
        # Read the generate_code.py file
        file_path = "ai-agent-service/app/agents/developer/implementor/nodes/generate_code.py"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n✅ Read {file_path}")
        print(f"📏 File length: {len(content)} chars")
        
        # Check for new approach markers
        new_approach_markers = [
            "NEW APPROACH: Full-file regeneration",
            "full-file regeneration approach",
            "_clean_llm_response",
        ]
        
        found_markers = []
        for marker in new_approach_markers:
            if marker in content:
                found_markers.append(marker)
        
        print(f"\n✅ Found {len(found_markers)}/{len(new_approach_markers)} new approach markers:")
        for marker in found_markers:
            print(f"   ✓ {marker}")
        
        # Check that old approach is removed/commented
        old_approach_markers = [
            "MODIFICATION #",
            "structured_modifications",
            "_validate_old_code_size",
        ]
        
        old_found = []
        for marker in old_approach_markers:
            if marker in content:
                # Count occurrences
                count = content.count(marker)
                old_found.append((marker, count))
        
        if old_found:
            print(f"\n⚠️ Found old approach markers (may be in comments/debug):")
            for marker, count in old_found:
                print(f"   ! {marker}: {count} occurrences")
        
        return len(found_markers) >= 2
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_implement_files_logic():
    """Test that implement_files.py uses the new approach"""
    print("\n" + "=" * 60)
    print("Testing Implement Files Logic")
    print("=" * 60)
    
    try:
        # Read the implement_files.py file
        file_path = "ai-agent-service/app/agents/developer/implementor/nodes/implement_files.py"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n✅ Read {file_path}")
        print(f"📏 File length: {len(content)} chars")
        
        # Check for new approach markers
        new_approach_markers = [
            "NEW APPROACH: Always use full-file regeneration",
            "Writing complete file",
        ]
        
        found_markers = []
        for marker in new_approach_markers:
            if marker in content:
                found_markers.append(marker)
        
        print(f"\n✅ Found {len(found_markers)}/{len(new_approach_markers)} new approach markers:")
        for marker in found_markers:
            print(f"   ✓ {marker}")
        
        # Check that incremental modification logic is removed/bypassed
        old_logic_markers = [
            "_apply_structured_modifications",
            "_apply_incremental_change",
        ]
        
        old_found = []
        for marker in old_logic_markers:
            if marker in content:
                count = content.count(marker)
                old_found.append((marker, count))
        
        if old_found:
            print(f"\n⚠️ Found old logic markers (should be removed/unused):")
            for marker, count in old_found:
                print(f"   ! {marker}: {count} occurrences")
        
        return len(found_markers) >= 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Full-File Regeneration Implementation")
    print("=" * 70)
    
    test1 = test_prompt_template()
    test2 = test_generate_code_logic()
    test3 = test_implement_files_logic()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Prompt Template: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Generate Code Logic: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Implement Files Logic: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    all_pass = test1 and test2 and test3
    
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - Full-file regeneration approach is ready!")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
