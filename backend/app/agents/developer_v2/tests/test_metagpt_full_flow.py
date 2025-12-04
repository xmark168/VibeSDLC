"""
MetaGPT-Style Full Flow Simulation

Tests:
- Implement: Single LLM call, no tools
- Review: LGTM/LBTM check
- Full flow: Plan → Implement → Review

Run:
    python backend/app/agents/developer_v2/tests/test_metagpt_full_flow.py
"""
import os
import sys
import re
import tempfile
from pathlib import Path

# Add paths
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))


# =============================================================================
# SKILLS (Pre-loaded patterns)
# =============================================================================

SKILL_API_ROUTE = """
## API Route Skill
- Collection routes: `app/api/users/route.ts` - GET (list), POST (create)
- Resource routes: `app/api/users/[id]/route.ts` - GET (one), PUT, DELETE
- CRITICAL: In Next.js 16, await params before using
- Use Zod for validation
- Use try/catch with handleError

```typescript
// Pattern: Collection Route
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';

const createSchema = z.object({
  name: z.string().min(2),
});

export async function GET(request: NextRequest) {
  try {
    const items = await prisma.model.findMany();
    return Response.json(items);
  } catch (error) {
    return Response.json({ error: 'Failed' }, { status: 500 });
  }
}
```
"""

SKILL_FRONTEND_COMPONENT = """
## Frontend Component Skill
- Server Components (default): Fetch data, async/await
- Client Components ('use client'): Hooks, events, browser APIs
- Add 'use client' when using: useState, useEffect, onClick, onChange
- CRITICAL: Array props always default to []
- CRITICAL: Check props before accessing

```typescript
// Pattern: Client Component with form
'use client'
import { useState, useCallback } from 'react'

interface Props {
  onSubmit: (data: string) => void
  items?: string[]  // Optional with default
}

export function MyComponent({ onSubmit, items = [] }: Props) {
  const [value, setValue] = useState('')
  
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(value.trim())
  }, [value, onSubmit])
  
  return (
    <form onSubmit={handleSubmit}>
      <input value={value} onChange={e => setValue(e.target.value)} />
      <button type="submit">Submit</button>
    </form>
  )
}
```
"""

def get_skill_for_file(file_path: str) -> str:
    """Auto-detect skill based on file path."""
    if "/api/" in file_path:
        return SKILL_API_ROUTE
    elif "/components/" in file_path or file_path.endswith(".tsx"):
        return SKILL_FRONTEND_COMPONENT
    return ""


# =============================================================================
# PROMPTS (MetaGPT-style with Skills)
# =============================================================================

IMPLEMENT_PROMPT = """
## Task
[{action}] {file_path}
{description}

## Skill Pattern (MUST FOLLOW)
{skill}

## Related Code
{dependencies}

## Output
Write COMPLETE code for `{file_path}`.
No TODOs, no placeholders, no "...".
FOLLOW the skill pattern exactly.

```typescript
// {file_path}
... your complete code ...
```
"""

REVIEW_PROMPT = """
## Code to Review: {filename}
```
{code}
```

## Checklist
1. Logic correct? Any bugs?
2. Types correct? No 'any'?
3. Edge cases handled? (null, empty)
4. Imports present?
5. Follows conventions?

## Output Format
If code is good:
LGTM

If code has issues:
LBTM
Issues:
- issue 1
- issue 2

Fixed code:
```typescript
... fixed code ...
```
"""

# =============================================================================
# SUMMARIZE + IS_PASS (MetaGPT SummarizeCode style)
# =============================================================================

SUMMARIZE_PROMPT = """
## Files Modified
{files_list}

## Code Contents
{code_contents}

## Review All Code
Check for:
- Unimplemented functions (TODOs, placeholders)
- Missing imports
- Type errors
- Edge cases not handled
- Inconsistencies between files

## Summary
Brief description of what each file does

## TODOs
List any remaining issues as JSON:
{{"file_path": "issue description"}}
"""

IS_PASS_PROMPT = """
{summary}
---
Does the above summary indicate the implementation is COMPLETE?

Rules:
- If TODOs is empty or {{}} -> YES
- If any unimplemented functions -> NO
- If missing critical imports -> NO
- If all files look complete -> YES

Answer: YES or NO

If NO, provide the todo list:
{{"file": "what needs to be done"}}
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_code_block(text: str) -> str:
    """Extract code from markdown code block."""
    # Try ```typescript or ```tsx
    match = re.search(r'```(?:typescript|tsx|javascript|js)?\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def build_dependencies_text(dependencies_content: dict, step_deps: list) -> str:
    """Build dependencies context string."""
    parts = []
    
    # Step-specific deps first
    for dep in step_deps:
        if dep in dependencies_content:
            parts.append(f"### {dep}\n```\n{dependencies_content[dep]}\n```")
    
    # Common files
    for path, content in dependencies_content.items():
        if path not in step_deps:
            parts.append(f"### {path}\n```\n{content}\n```")
    
    return "\n\n".join(parts) if parts else "(no dependencies)"


# =============================================================================
# MOCK LLM RESPONSES
# =============================================================================

MOCK_IMPLEMENT_RESPONSES = {
    "src/app/api/search/route.ts": '''```typescript
// src/app/api/search/route.ts
import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const q = searchParams.get('q') || ''
  
  const results = await prisma.textbook.findMany({
    where: { 
      title: { contains: q, mode: 'insensitive' } 
    },
    take: 20
  })
  
  return NextResponse.json(results)
}
```''',

    "src/components/SearchBar.tsx": '''```typescript
// src/components/SearchBar.tsx
'use client'
import { useState, useCallback } from 'react'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
}

export function SearchBar({ onSearch, placeholder = "Search..." }: SearchBarProps) {
  const [query, setQuery] = useState('')
  
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    onSearch(query.trim())
  }, [query, onSearch])
  
  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input 
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="border rounded px-3 py-2 flex-1"
      />
      <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded">
        Search
      </button>
    </form>
  )
}
```''',
}

MOCK_REVIEW_RESPONSES = {
    "src/app/api/search/route.ts": "LGTM",
    "src/components/SearchBar.tsx": "LGTM",
}


# =============================================================================
# SIMULATE FUNCTIONS
# =============================================================================

def simulate_implement(step: dict, dependencies_content: dict) -> tuple:
    """Simulate MetaGPT WriteCode - single LLM call with skill."""
    file_path = step['file_path']
    
    # Auto-detect skill based on file path
    skill = get_skill_for_file(file_path)
    
    # Build prompt (for logging)
    deps_text = build_dependencies_text(
        dependencies_content, 
        step.get('dependencies', [])
    )
    
    prompt = IMPLEMENT_PROMPT.format(
        action=step['action'],
        file_path=file_path,
        description=step['description'],
        skill=skill or "(no specific skill)",
        dependencies=deps_text
    )
    
    # Get mock response
    response = MOCK_IMPLEMENT_RESPONSES.get(file_path, "// No mock for this file")
    code = extract_code_block(response)
    
    # Return code and detected skill name
    skill_name = "api-route" if "/api/" in file_path else "frontend-component" if skill else None
    return code, skill_name


def simulate_review(file_path: str, code: str) -> dict:
    """Simulate MetaGPT WriteCodeReview - LGTM/LBTM."""
    
    # Build prompt (for logging)
    prompt = REVIEW_PROMPT.format(filename=file_path, code=code)
    
    # Get mock response
    response = MOCK_REVIEW_RESPONSES.get(file_path, "LGTM")
    
    if "LGTM" in response:
        return {"result": "LGTM", "code": code, "issues": []}
    else:
        # Parse LBTM response
        fixed_code = extract_code_block(response)
        return {"result": "LBTM", "code": fixed_code, "issues": ["mock issue"]}


def simulate_summarize(files_modified: dict) -> str:
    """Simulate MetaGPT SummarizeCode - review all files."""
    
    files_list = "\n".join(f"- {f}" for f in files_modified.keys())
    code_contents = "\n\n".join(
        f"### {path}\n```\n{code[:500]}\n```"
        for path, code in files_modified.items()
    )
    
    # Build summary
    summary_parts = ["## Summary"]
    for path, code in files_modified.items():
        if "/api/" in path:
            summary_parts.append(f"- {path}: API endpoint with request handlers")
        elif "/components/" in path:
            summary_parts.append(f"- {path}: React component with props interface")
        else:
            summary_parts.append(f"- {path}: Code file")
    
    # Check for issues
    todos = {}
    for path, code in files_modified.items():
        if "TODO" in code or "..." in code or "// implement" in code.lower():
            todos[path] = "Contains unimplemented code"
        if "any" in code and ".tsx" in path:
            todos[path] = "Uses 'any' type - should use explicit types"
    
    summary_parts.append("\n## TODOs")
    if todos:
        summary_parts.append(str(todos))
    else:
        summary_parts.append("{}")
    
    return "\n".join(summary_parts)


def simulate_is_pass(summary: str) -> dict:
    """Simulate MetaGPT IS_PASS check - YES/NO completion gate."""
    
    # Check if TODOs section has issues
    if "TODOs" in summary:
        todos_section = summary.split("TODOs")[-1]
        if "{}" in todos_section or "None" in todos_section:
            return {"result": "YES", "todos": {}}
        else:
            # Extract todos (mock)
            return {"result": "NO", "todos": {"some_file": "needs work"}}
    
    return {"result": "YES", "todos": {}}


def simulate_full_flow_with_validation(steps: list, dependencies_content: dict, max_review: int = 2) -> dict:
    """Full MetaGPT flow: Implement -> Review -> Summarize -> IS_PASS."""
    
    # Step 1: Implement all steps with review
    files_modified = {}
    results = []
    
    for step in steps:
        file_path = step['file_path']
        
        # IMPLEMENT
        code, skill_name = simulate_implement(step, dependencies_content)
        
        # REVIEW loop
        for i in range(max_review):
            review = simulate_review(file_path, code)
            if review['result'] == "LGTM":
                break
            code = review['code']
        
        files_modified[file_path] = code
        results.append({
            'file_path': file_path,
            'skill': skill_name,
            'review': review['result']
        })
    
    # Step 2: Summarize all code
    summary = simulate_summarize(files_modified)
    
    # Step 3: IS_PASS check
    is_pass = simulate_is_pass(summary)
    
    return {
        'steps': results,
        'files_modified': files_modified,
        'summary': summary,
        'is_pass': is_pass['result'],
        'todos': is_pass['todos']
    }


def simulate_full_flow(steps: list, dependencies_content: dict, max_review: int = 2) -> list:
    """Simulate full MetaGPT flow: Implement (with skill) -> Review loop."""
    results = []
    
    for step in steps:
        file_path = step['file_path']
        
        # IMPLEMENT (single call with auto-detected skill)
        code, skill_name = simulate_implement(step, dependencies_content)
        
        # REVIEW loop
        final_review = None
        for i in range(max_review):
            review = simulate_review(file_path, code)
            final_review = review
            
            if review['result'] == "LGTM":
                break
            else:
                # Use fixed code for next iteration
                code = review['code']
        
        results.append({
            'step': step['order'],
            'file_path': file_path,
            'action': step['action'],
            'skill': skill_name,
            'code_length': len(code),
            'review_result': final_review['result'],
        })
    
    return results


# =============================================================================
# TESTS
# =============================================================================

def test_implement_single_call():
    """Test implement produces complete code with skill."""
    print("\n[TEST] test_implement_single_call")
    
    step = {
        "order": 1,
        "file_path": "src/app/api/search/route.ts",
        "action": "create",
        "description": "Search API endpoint with prisma query",
        "dependencies": ["prisma/schema.prisma"]
    }
    
    deps = {
        "prisma/schema.prisma": "model Textbook { id Int @id; title String }",
        "src/lib/prisma.ts": "export const prisma = new PrismaClient()"
    }
    
    code, skill_name = simulate_implement(step, deps)
    
    # Assertions
    assert len(code) > 100, "Code too short"
    assert "prisma" in code.lower(), "Should use prisma"
    assert "GET" in code or "get" in code.lower(), "Should have GET handler"
    assert skill_name == "api-route", f"Should detect api-route skill, got {skill_name}"
    
    print(f"   Code length: {len(code)} chars")
    print(f"   Skill detected: {skill_name}")
    print(f"   Has prisma: True")
    print(f"   Has GET handler: True")
    print("[PASS] test_implement_single_call")


def test_review_lgtm():
    """Test review returns LGTM for good code."""
    print("\n[TEST] test_review_lgtm")
    
    code = '''
import { prisma } from '@/lib/prisma'
export async function GET() {
  return Response.json(await prisma.textbook.findMany())
}
'''
    
    review = simulate_review("src/app/api/search/route.ts", code)
    
    assert review['result'] == "LGTM", f"Expected LGTM, got {review['result']}"
    assert review['code'] == code, "Code should be unchanged for LGTM"
    
    print(f"   Result: {review['result']}")
    print("[PASS] test_review_lgtm")


def test_full_flow_simulation():
    """Test full flow: plan → implement → review."""
    print("\n[TEST] test_full_flow_simulation")
    
    # Mock plan
    steps = [
        {
            "order": 1,
            "file_path": "src/app/api/search/route.ts",
            "action": "create",
            "description": "Search API endpoint",
            "dependencies": ["prisma/schema.prisma", "src/lib/prisma.ts"]
        },
        {
            "order": 2,
            "file_path": "src/components/SearchBar.tsx",
            "action": "create",
            "description": "Search input component",
            "dependencies": []
        }
    ]
    
    # Mock dependencies
    deps = {
        "prisma/schema.prisma": "model Textbook { id Int @id; title String; author String }",
        "src/lib/prisma.ts": "import { PrismaClient } from '@prisma/client'\nexport const prisma = new PrismaClient()"
    }
    
    # Run flow
    results = simulate_full_flow(steps, deps)
    
    # Assertions
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    
    for r in results:
        assert r['review_result'] == "LGTM", f"Step {r['step']} not LGTM"
        assert r['code_length'] > 100, f"Step {r['step']} code too short"
    
    print(f"   Steps completed: {len(results)}")
    print(f"   All LGTM: True")
    
    for r in results:
        print(f"   Step {r['step']}: [{r['action']}] {r['file_path']}")
        print(f"           Skill: {r['skill']}, Code: {r['code_length']} chars, Review: {r['review_result']}")
    
    print("[PASS] test_full_flow_simulation")


def test_flow_with_workspace():
    """Test flow writes files to workspace."""
    print("\n[TEST] test_flow_with_workspace")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create workspace structure
        os.makedirs(os.path.join(tmpdir, "src", "app", "api", "search"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "components"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "prisma"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "lib"), exist_ok=True)
        
        # Create dependency files
        with open(os.path.join(tmpdir, "prisma", "schema.prisma"), 'w') as f:
            f.write("model Textbook { id Int @id; title String }")
        
        with open(os.path.join(tmpdir, "src", "lib", "prisma.ts"), 'w') as f:
            f.write("export const prisma = new PrismaClient()")
        
        # Steps
        steps = [
            {
                "order": 1,
                "file_path": "src/app/api/search/route.ts",
                "action": "create",
                "description": "Search API",
                "dependencies": ["prisma/schema.prisma"]
            }
        ]
        
        deps = {
            "prisma/schema.prisma": "model Textbook { id Int @id; title String }",
        }
        
        # Implement (with skill auto-detection)
        code, skill_name = simulate_implement(steps[0], deps)
        
        # Write to workspace
        file_path = os.path.join(tmpdir, steps[0]['file_path'])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(code)
        
        # Verify file exists
        assert os.path.exists(file_path), "File not created"
        
        with open(file_path, 'r') as f:
            written_code = f.read()
        
        assert len(written_code) > 100, "Written code too short"
        assert "prisma" in written_code.lower(), "Code should use prisma"
        assert skill_name == "api-route", f"Should use api-route skill, got {skill_name}"
        
        print(f"   File created: {steps[0]['file_path']}")
        print(f"   Skill used: {skill_name}")
        print(f"   Code size: {len(written_code)} chars")
        print("[PASS] test_flow_with_workspace")


def test_summarize_code():
    """Test SummarizeCode produces summary and detects issues."""
    print("\n[TEST] test_summarize_code")
    
    # Good code - no TODOs
    files_good = {
        "src/app/api/search/route.ts": """
import { prisma } from '@/lib/prisma'
export async function GET() {
  return Response.json(await prisma.textbook.findMany())
}
""",
        "src/components/SearchBar.tsx": """
'use client'
import { useState } from 'react'
export function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [query, setQuery] = useState('')
  return <input value={query} onChange={e => setQuery(e.target.value)} />
}
"""
    }
    
    summary = simulate_summarize(files_good)
    
    assert "## Summary" in summary, "Missing summary section"
    assert "## TODOs" in summary, "Missing TODOs section"
    assert "{}" in summary, "Good code should have empty TODOs"
    
    print(f"   Summary length: {len(summary)} chars")
    print(f"   Has empty TODOs: True")
    print("[PASS] test_summarize_code")


def test_summarize_detects_issues():
    """Test SummarizeCode detects TODOs and issues."""
    print("\n[TEST] test_summarize_detects_issues")
    
    # Bad code - has TODOs
    files_bad = {
        "src/app/api/search/route.ts": """
export async function GET() {
  // TODO: implement search
  return Response.json([])
}
"""
    }
    
    summary = simulate_summarize(files_bad)
    
    assert "## TODOs" in summary, "Missing TODOs section"
    assert "{}" not in summary or "unimplemented" in summary.lower(), "Should detect TODO"
    
    print(f"   Detected issues in code with TODO")
    print("[PASS] test_summarize_detects_issues")


def test_is_pass_yes():
    """Test IS_PASS returns YES for complete code."""
    print("\n[TEST] test_is_pass_yes")
    
    summary_complete = """
## Summary
- api/route.ts: Complete API endpoint
- components/SearchBar.tsx: Complete component

## TODOs
{}
"""
    
    result = simulate_is_pass(summary_complete)
    
    assert result['result'] == "YES", f"Expected YES, got {result['result']}"
    assert result['todos'] == {}, "Should have no todos"
    
    print(f"   Result: {result['result']}")
    print("[PASS] test_is_pass_yes")


def test_is_pass_no():
    """Test IS_PASS returns NO for incomplete code."""
    print("\n[TEST] test_is_pass_no")
    
    summary_incomplete = """
## Summary
- api/route.ts: Has issues

## TODOs
{'api/route.ts': 'implement search logic'}
"""
    
    result = simulate_is_pass(summary_incomplete)
    
    assert result['result'] == "NO", f"Expected NO, got {result['result']}"
    assert len(result['todos']) > 0, "Should have todos"
    
    print(f"   Result: {result['result']}")
    print(f"   TODOs: {result['todos']}")
    print("[PASS] test_is_pass_no")


def test_full_flow_with_validation():
    """Test complete flow: Implement -> Review -> Summarize -> IS_PASS."""
    print("\n[TEST] test_full_flow_with_validation")
    
    steps = [
        {
            "order": 1,
            "file_path": "src/app/api/search/route.ts",
            "action": "create",
            "description": "Search API",
            "dependencies": ["prisma/schema.prisma"]
        },
        {
            "order": 2,
            "file_path": "src/components/SearchBar.tsx",
            "action": "create",
            "description": "Search component",
            "dependencies": []
        }
    ]
    
    deps = {
        "prisma/schema.prisma": "model Textbook { id Int; title String }",
    }
    
    result = simulate_full_flow_with_validation(steps, deps)
    
    assert len(result['steps']) == 2, "Should have 2 steps"
    assert len(result['files_modified']) == 2, "Should have 2 files"
    assert "## Summary" in result['summary'], "Should have summary"
    assert result['is_pass'] in ["YES", "NO"], "Should have IS_PASS result"
    
    print(f"   Steps completed: {len(result['steps'])}")
    print(f"   Files modified: {list(result['files_modified'].keys())}")
    print(f"   IS_PASS: {result['is_pass']}")
    if result['todos']:
        print(f"   TODOs: {result['todos']}")
    print("[PASS] test_full_flow_with_validation")


def test_comparison_tool_calls():
    """Compare tool calls: current vs MetaGPT style."""
    print("\n[TEST] test_comparison_tool_calls")
    
    # Current dev_v2 approach (estimated)
    current_calls_per_step = {
        "read_file": 3,
        "grep_files": 2,
        "glob": 1,
        "write_file": 1,
        "edit_file": 1,
        "list_directory": 2,
    }
    current_total = sum(current_calls_per_step.values())
    
    # MetaGPT approach
    metagpt_calls_per_step = {
        "implement_llm_call": 1,
        "review_llm_call": 1,
        "write_file": 1,  # Direct write, no tool
    }
    metagpt_total = 2  # Just LLM calls, write is direct
    
    print(f"   Current dev_v2 per step: ~{current_total} tool calls")
    print(f"   MetaGPT style per step: {metagpt_total} LLM calls")
    print(f"   Reduction: {current_total - metagpt_total} fewer calls ({(1 - metagpt_total/current_total)*100:.0f}%)")
    
    # For 2 steps
    print(f"\n   For 2 steps:")
    print(f"   Current: ~{current_total * 2} tool calls")
    print(f"   MetaGPT: {metagpt_total * 2} LLM calls")
    
    assert metagpt_total < current_total, "MetaGPT should have fewer calls"
    
    print("[PASS] test_comparison_tool_calls")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MetaGPT-Style Full Flow Simulation Tests")
    print("=" * 60)
    
    tests = [
        # Basic tests
        test_implement_single_call,
        test_review_lgtm,
        test_full_flow_simulation,
        test_flow_with_workspace,
        # SummarizeCode + IS_PASS tests
        test_summarize_code,
        test_summarize_detects_issues,
        test_is_pass_yes,
        test_is_pass_no,
        test_full_flow_with_validation,
        # Comparison
        test_comparison_tool_calls,
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
    
    if failed > 0:
        sys.exit(1)
