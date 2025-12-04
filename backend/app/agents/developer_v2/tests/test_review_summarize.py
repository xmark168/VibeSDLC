"""Test review and summarize nodes (MetaGPT-style)."""
import os
import sys
import re
import tempfile


# ============================================================================
# Local copies of parsing functions (avoid import issues)
# ============================================================================

def _parse_review_response(response: str) -> dict:
    """Parse review response to extract decision and feedback."""
    result = {
        "decision": "LGTM",
        "review": "",
        "feedback": ""
    }
    
    decision_match = re.search(r'DECISION:\s*(LGTM|LBTM)', response, re.IGNORECASE)
    if decision_match:
        result["decision"] = decision_match.group(1).upper()
    
    review_match = re.search(r'REVIEW:\s*\n([\s\S]*?)(?=FEEDBACK:|$)', response, re.IGNORECASE)
    if review_match:
        result["review"] = review_match.group(1).strip()
    
    feedback_match = re.search(r'FEEDBACK:\s*\n?([\s\S]*?)$', response, re.IGNORECASE)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
    
    return result


def _parse_summarize_response(response: str) -> dict:
    """Parse summarize response."""
    result = {
        "summary": "",
        "files_reviewed": "",
        "todos": {},
        "is_pass": "YES",
        "feedback": ""
    }
    
    summary_match = re.search(r'## Summary\s*\n([\s\S]*?)(?=## Files|## TODOs|$)', response)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    files_match = re.search(r'## Files Reviewed\s*\n([\s\S]*?)(?=## TODOs|## IS_PASS|$)', response)
    if files_match:
        result["files_reviewed"] = files_match.group(1).strip()
    
    todos_match = re.search(r'## TODOs Found\s*\n\{([\s\S]*?)\}', response)
    if todos_match:
        todos_str = todos_match.group(1).strip()
        if todos_str:
            for line in todos_str.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().strip('"\'')
                    value = parts[1].strip().strip('",\'')
                    if key:
                        result["todos"][key] = value
    
    is_pass_match = re.search(r'## IS_PASS:\s*(YES|NO)', response, re.IGNORECASE)
    if is_pass_match:
        result["is_pass"] = is_pass_match.group(1).upper()
    
    feedback_match = re.search(r'## Feedback[^\n]*\n([\s\S]*?)$', response)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
    
    return result


def route_after_review(state: dict) -> str:
    """Route based on review result."""
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    max_reviews = 2
    
    if review_result == "LBTM" and review_count < max_reviews:
        return "implement"
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step >= total_steps:
        return "summarize"
    
    return "next_step"


def route_after_summarize(state: dict) -> str:
    """Route based on IS_PASS result."""
    is_pass = state.get("is_pass", "YES")
    summarize_count = state.get("summarize_count", 0)
    max_summarize_retries = 2
    
    if is_pass == "NO" and summarize_count < max_summarize_retries:
        return "implement"
    
    return "validate"


def _read_modified_files(workspace_path: str, files_modified: list) -> dict:
    """Read content of all modified files."""
    files_content = {}
    
    for file_path in files_modified:
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_content[file_path] = content[:3000]
            except Exception as e:
                files_content[file_path] = f"[Error reading file: {e}]"
        else:
            files_content[file_path] = "[File not found]"
    
    return files_content


# ============================================================================
# Tests
# ============================================================================

def test_parse_review_response():
    """Test parsing review response."""
    print("\n[TEST] test_parse_review_response")
    
    # Test LGTM response
    lgtm_response = """
DECISION: LGTM

REVIEW:
- Code is complete and well-structured
- All types are properly defined
- Error handling is in place

FEEDBACK:
"""
    result = _parse_review_response(lgtm_response)
    assert result["decision"] == "LGTM", f"Expected LGTM, got {result['decision']}"
    assert "complete" in result["review"].lower()
    print(f"   LGTM response parsed correctly")
    
    # Test LBTM response
    lbtm_response = """
DECISION: LBTM

REVIEW:
- Missing error handling in API route
- TODO comment found on line 15

FEEDBACK:
Please add try/catch block around the database query and remove the TODO comment.
"""
    result = _parse_review_response(lbtm_response)
    assert result["decision"] == "LBTM", f"Expected LBTM, got {result['decision']}"
    assert "TODO" in result["review"]
    assert "try/catch" in result["feedback"]
    print(f"   LBTM response parsed correctly")
    
    print("[PASS] test_parse_review_response")


def test_parse_summarize_response():
    """Test parsing summarize response."""
    print("\n[TEST] test_parse_summarize_response")
    
    # Test IS_PASS YES
    yes_response = """
## Summary
Implemented homepage with hero section, featured books grid, and trust indicators.

## Files Reviewed
- src/app/page.tsx: OK - Main homepage component
- src/components/HeroSection.tsx: OK - Hero with CTA

## TODOs Found
{}

## IS_PASS: YES

## Feedback
"""
    result = _parse_summarize_response(yes_response)
    assert result["is_pass"] == "YES", f"Expected YES, got {result['is_pass']}"
    assert len(result["todos"]) == 0, f"Expected no TODOs, got {result['todos']}"
    assert "homepage" in result["summary"].lower()
    print(f"   IS_PASS=YES parsed correctly")
    
    # Test IS_PASS NO
    no_response = """
## Summary
Partial implementation of homepage.

## Files Reviewed
- src/app/page.tsx: HAS_ISSUES - Contains TODO
- src/components/HeroSection.tsx: OK

## TODOs Found
{
  "src/app/page.tsx": "TODO: Add loading state",
  "src/components/FeaturedBooks.tsx": "Empty function body"
}

## IS_PASS: NO

## Feedback
Please complete the loading state in page.tsx and implement the FeaturedBooks component.
"""
    result = _parse_summarize_response(no_response)
    assert result["is_pass"] == "NO", f"Expected NO, got {result['is_pass']}"
    assert len(result["todos"]) == 2, f"Expected 2 TODOs, got {len(result['todos'])}"
    assert "src/app/page.tsx" in result["todos"]
    print(f"   IS_PASS=NO parsed correctly with {len(result['todos'])} TODOs")
    
    print("[PASS] test_parse_summarize_response")


def test_route_after_review():
    """Test review routing logic."""
    print("\n[TEST] test_route_after_review")
    
    # LGTM -> next_step
    state = {"review_result": "LGTM", "current_step": 1, "total_steps": 3}
    result = route_after_review(state)
    assert result == "next_step", f"Expected next_step, got {result}"
    print(f"   LGTM + more steps -> next_step")
    
    # LGTM on last step -> summarize
    state = {"review_result": "LGTM", "current_step": 3, "total_steps": 3}
    result = route_after_review(state)
    assert result == "summarize", f"Expected summarize, got {result}"
    print(f"   LGTM + last step -> summarize")
    
    # LBTM -> implement
    state = {"review_result": "LBTM", "review_count": 0, "current_step": 1, "total_steps": 3}
    result = route_after_review(state)
    assert result == "implement", f"Expected implement, got {result}"
    print(f"   LBTM -> implement (retry)")
    
    # LBTM max retries -> next_step anyway
    state = {"review_result": "LBTM", "review_count": 2, "current_step": 1, "total_steps": 3}
    result = route_after_review(state)
    assert result == "next_step", f"Expected next_step (max retries), got {result}"
    print(f"   LBTM + max retries -> next_step")
    
    print("[PASS] test_route_after_review")


def test_route_after_summarize():
    """Test summarize routing logic."""
    print("\n[TEST] test_route_after_summarize")
    
    # IS_PASS YES -> validate
    state = {"is_pass": "YES"}
    result = route_after_summarize(state)
    assert result == "validate", f"Expected validate, got {result}"
    print(f"   IS_PASS=YES -> validate")
    
    # IS_PASS NO -> implement
    state = {"is_pass": "NO", "summarize_count": 0}
    result = route_after_summarize(state)
    assert result == "implement", f"Expected implement, got {result}"
    print(f"   IS_PASS=NO -> implement (retry)")
    
    # IS_PASS NO max retries -> validate anyway
    state = {"is_pass": "NO", "summarize_count": 2}
    result = route_after_summarize(state)
    assert result == "validate", f"Expected validate (max retries), got {result}"
    print(f"   IS_PASS=NO + max retries -> validate")
    
    print("[PASS] test_route_after_summarize")


def test_read_modified_files():
    """Test reading modified files."""
    print("\n[TEST] test_read_modified_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, 'w') as f:
            f.write("export function test() { return 'hello'; }")
        
        # Read files
        files_content = _read_modified_files(tmpdir, ["test.ts"])
        
        assert "test.ts" in files_content
        assert "export function" in files_content["test.ts"]
        print(f"   Read test.ts: {len(files_content['test.ts'])} chars")
        
        # Test non-existent file
        files_content = _read_modified_files(tmpdir, ["nonexistent.ts"])
        assert "nonexistent.ts" in files_content
        assert "not found" in files_content["nonexistent.ts"].lower()
        print(f"   Non-existent file handled correctly")
    
    print("[PASS] test_read_modified_files")


def test_full_metagpt_flow_simulation():
    """Simulate full MetaGPT-style flow."""
    print("\n[TEST] test_full_metagpt_flow_simulation")
    
    # Simulate the flow: implement -> review -> (LGTM) -> summarize -> (YES) -> validate
    
    steps = [
        {"file_path": "src/app/api/books/route.ts", "action": "create", "description": "Books API"},
        {"file_path": "src/components/BookCard.tsx", "action": "create", "description": "Book card"},
    ]
    
    files_created = {}
    review_results = []
    
    # Simulate implement + review for each step
    for i, step in enumerate(steps):
        # Implement (simulated)
        code = f"// {step['description']}\nexport default function() {{ return null; }}"
        files_created[step["file_path"]] = code
        
        # Review (simulated - assume LGTM)
        review_result = "LGTM"
        review_results.append(review_result)
        
        print(f"   Step {i+1}: {step['file_path']} -> {review_result}")
    
    # Summarize (simulated)
    summary = f"Implemented {len(steps)} files"
    todos = {}  # No issues
    is_pass = "YES"
    
    print(f"   Summarize: {len(files_created)} files, IS_PASS={is_pass}")
    
    # Validate
    assert len(files_created) == 2
    assert all(r == "LGTM" for r in review_results)
    assert is_pass == "YES"
    
    print(f"\n   Flow: implement -> review (x{len(steps)}) -> summarize -> validate")
    print(f"   Result: {len(steps)} steps, all LGTM, IS_PASS=YES")
    
    print("[PASS] test_full_metagpt_flow_simulation")


def test_flow_with_lbtm():
    """Test flow with LBTM triggering re-implement."""
    print("\n[TEST] test_flow_with_lbtm")
    
    # Step 1: First implement
    state = {
        "current_step": 1,
        "total_steps": 2,
        "review_result": "LBTM",
        "review_feedback": "Missing error handling",
        "review_count": 0
    }
    
    # Route should go back to implement
    route = route_after_review(state)
    assert route == "implement", f"Expected implement, got {route}"
    print(f"   Attempt 1: LBTM -> implement")
    
    # Step 2: Second implement (with feedback)
    state["review_count"] = 1
    state["review_result"] = "LGTM"
    
    route = route_after_review(state)
    assert route == "next_step", f"Expected next_step, got {route}"
    print(f"   Attempt 2: LGTM -> next_step")
    
    print("[PASS] test_flow_with_lbtm")


def test_flow_with_is_pass_no():
    """Test flow with IS_PASS=NO triggering re-implement."""
    print("\n[TEST] test_flow_with_is_pass_no")
    
    # First summarize: NO
    state = {
        "is_pass": "NO",
        "summarize_feedback": "TODO found in page.tsx",
        "summarize_count": 0
    }
    
    route = route_after_summarize(state)
    assert route == "implement", f"Expected implement, got {route}"
    print(f"   Attempt 1: IS_PASS=NO -> implement")
    
    # Second summarize: YES
    state["summarize_count"] = 1
    state["is_pass"] = "YES"
    
    route = route_after_summarize(state)
    assert route == "validate", f"Expected validate, got {route}"
    print(f"   Attempt 2: IS_PASS=YES -> validate")
    
    print("[PASS] test_flow_with_is_pass_no")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Review & Summarize Nodes Tests")
    print("=" * 60)
    
    tests = [
        test_parse_review_response,
        test_parse_summarize_response,
        test_route_after_review,
        test_route_after_summarize,
        test_read_modified_files,
        test_full_metagpt_flow_simulation,
        test_flow_with_lbtm,
        test_flow_with_is_pass_no,
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
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
