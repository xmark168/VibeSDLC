"""Integration test for MetaGPT-style planning flow.

Tests:
1. analyze_and_plan produces logic_analysis + dependencies_content
2. implement uses pre-loaded context correctly
3. End-to-end flow validation

Run directly:
    python backend/app/agents/developer_v2/tests/test_metagpt_flow.py
"""
import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add paths for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))


# =============================================================================
# Mock LLM Response
# =============================================================================

MOCK_PLAN_RESPONSE = """
I'll analyze the codebase and create a plan.

After exploring the project structure, here's my implementation plan:

<result>
{
  "story_summary": "Search functionality for textbooks",
  "logic_analysis": [
    ["src/app/api/search/route.ts", "GET handler with query param, prisma.textbook.findMany"],
    ["src/components/SearchBar.tsx", "SearchBar component with useState, debounced input"],
    ["src/app/search/page.tsx", "Search page rendering SearchBar and results"]
  ],
  "steps": [
    {
      "order": 1,
      "description": "Create search API endpoint",
      "file_path": "src/app/api/search/route.ts",
      "action": "create",
      "dependencies": ["prisma/schema.prisma", "src/lib/prisma.ts"]
    },
    {
      "order": 2,
      "description": "Create SearchBar component",
      "file_path": "src/components/SearchBar.tsx",
      "action": "create",
      "dependencies": []
    }
  ]
}
</result>
"""

MOCK_IMPLEMENT_RESPONSE = """
I'll create the search API endpoint.

Using write_file_safe to create src/app/api/search/route.ts with the search handler.
"""


# =============================================================================
# Helper Functions (copied from analyze_and_plan.py for isolated testing)
# =============================================================================

def _preload_dependencies(workspace_path: str, steps: list) -> dict:
    """Pre-load dependency file contents (MetaGPT-style)."""
    dependencies_content = {}
    
    if not workspace_path or not os.path.exists(workspace_path):
        return dependencies_content
    
    all_deps = set()
    for step in steps:
        deps = step.get("dependencies", [])
        if isinstance(deps, list):
            all_deps.update(deps)
    
    common_files = [
        "prisma/schema.prisma",
        "src/lib/prisma.ts",
        "src/types/index.ts",
    ]
    all_deps.update(common_files)
    
    for dep_path in all_deps:
        full_path = os.path.join(workspace_path, dep_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if len(content) > 3000:
                    content = content[:3000] + "\n... (truncated)"
                dependencies_content[dep_path] = content
            except Exception:
                pass
    
    return dependencies_content


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list) -> str:
    """Build pre-loaded dependencies context for the current step."""
    if not dependencies_content:
        return ""
    
    parts = []
    
    if step_dependencies:
        for dep_path in step_dependencies:
            if dep_path in dependencies_content:
                content = dependencies_content[dep_path]
                parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    common_files = ["prisma/schema.prisma", "src/lib/prisma.ts"]
    for dep_path in common_files:
        if dep_path in dependencies_content and dep_path not in (step_dependencies or []):
            content = dependencies_content[dep_path]
            parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    if not parts:
        return ""
    
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


def extract_json_universal(text: str, context: str = "") -> dict:
    """Extract JSON from text with multiple format support."""
    import re
    
    # Try <result> tags first
    result_match = re.search(r'<result>\s*(.*?)\s*</result>', text, re.DOTALL)
    if result_match:
        try:
            return json.loads(result_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try ```json blocks
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try raw JSON
    json_pattern = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_pattern:
        try:
            return json.loads(json_pattern.group(0))
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract JSON from {context}")


# =============================================================================
# Workspace Setup
# =============================================================================

def create_test_workspace(tmpdir: str) -> str:
    """Create minimal Next.js workspace for testing."""
    
    # prisma/schema.prisma
    prisma_dir = os.path.join(tmpdir, "prisma")
    os.makedirs(prisma_dir, exist_ok=True)
    with open(os.path.join(prisma_dir, "schema.prisma"), 'w') as f:
        f.write("""datasource db {
  provider = "postgresql"
}

model Textbook {
  id        Int      @id @default(autoincrement())
  title     String
  author    String
  isbn      String   @unique
  createdAt DateTime @default(now())
}

model User {
  id    Int    @id @default(autoincrement())
  email String @unique
  name  String?
}
""")
    
    # src/lib/prisma.ts
    lib_dir = os.path.join(tmpdir, "src", "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(lib_dir, "prisma.ts"), 'w') as f:
        f.write("""import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const prisma = globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
""")
    
    # src/app/layout.tsx
    app_dir = os.path.join(tmpdir, "src", "app")
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(app_dir, "layout.tsx"), 'w') as f:
        f.write("""export default function RootLayout({ children }) {
  return <html><body>{children}</body></html>
}
""")
    
    # src/components (empty dir)
    components_dir = os.path.join(tmpdir, "src", "components")
    os.makedirs(components_dir, exist_ok=True)
    
    # package.json
    with open(os.path.join(tmpdir, "package.json"), 'w') as f:
        f.write('{"name": "test-project", "dependencies": {"next": "14.0.0"}}')
    
    # tsconfig.json
    with open(os.path.join(tmpdir, "tsconfig.json"), 'w') as f:
        f.write('{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}')
    
    return tmpdir


# =============================================================================
# Test 1: Plan Output Validation
# =============================================================================

def test_plan_produces_logic_analysis():
    """Verify plan response produces MetaGPT-style fields."""
    print("\n[TEST] test_plan_produces_logic_analysis")
    
    # Parse mock response
    data = extract_json_universal(MOCK_PLAN_RESPONSE, "plan")
    
    # Check story_summary
    assert "story_summary" in data, "Missing story_summary"
    assert len(data["story_summary"]) > 0, "Empty story_summary"
    
    # Check logic_analysis (MetaGPT-style)
    assert "logic_analysis" in data, "Missing logic_analysis"
    assert isinstance(data["logic_analysis"], list), "logic_analysis should be list"
    assert len(data["logic_analysis"]) >= 2, f"Expected 2+ logic entries, got {len(data['logic_analysis'])}"
    
    # Each entry should be [file_path, description]
    for entry in data["logic_analysis"]:
        assert isinstance(entry, list), f"Logic entry should be list: {entry}"
        assert len(entry) == 2, f"Logic entry should have 2 elements: {entry}"
        assert isinstance(entry[0], str), "File path should be string"
        assert isinstance(entry[1], str), "Description should be string"
    
    # Check steps with new format
    assert "steps" in data, "Missing steps"
    for step in data["steps"]:
        assert "order" in step, "Step missing order"
        assert "description" in step, "Step missing description"
        assert "file_path" in step, "Step missing file_path (MetaGPT-style)"
        assert "action" in step, "Step missing action"
        assert "dependencies" in step, "Step missing dependencies"
    
    print(f"   logic_analysis entries: {len(data['logic_analysis'])}")
    print(f"   steps: {len(data['steps'])}")
    print(f"   Step 1 file_path: {data['steps'][0]['file_path']}")
    print(f"   Step 1 dependencies: {data['steps'][0]['dependencies']}")
    print("[PASS] test_plan_produces_logic_analysis")


# =============================================================================
# Test 2: Pre-load Dependencies Validation
# =============================================================================

def test_preload_reads_correct_files():
    """Verify dependencies are pre-loaded from steps."""
    print("\n[TEST] test_preload_reads_correct_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = create_test_workspace(tmpdir)
        
        steps = [
            {
                "order": 1,
                "description": "Create search API",
                "file_path": "src/app/api/search/route.ts",
                "action": "create",
                "dependencies": ["prisma/schema.prisma", "src/lib/prisma.ts"]
            },
            {
                "order": 2,
                "description": "Create SearchBar",
                "file_path": "src/components/SearchBar.tsx",
                "action": "create",
                "dependencies": []
            }
        ]
        
        # Pre-load dependencies
        deps_content = _preload_dependencies(workspace, steps)
        
        # Check step-specific dependencies
        assert "prisma/schema.prisma" in deps_content, "Missing schema.prisma"
        assert "src/lib/prisma.ts" in deps_content, "Missing prisma.ts"
        
        # Check content is loaded correctly
        assert "model Textbook" in deps_content["prisma/schema.prisma"], "Schema content not loaded"
        assert "PrismaClient" in deps_content["src/lib/prisma.ts"], "Prisma.ts content not loaded"
        
        print(f"   Pre-loaded files: {list(deps_content.keys())}")
        print(f"   schema.prisma size: {len(deps_content['prisma/schema.prisma'])} chars")
        print("[PASS] test_preload_reads_correct_files")


# =============================================================================
# Test 3: Implement Uses Pre-loaded Context
# =============================================================================

def test_implement_builds_preloaded_context():
    """Verify implement builds correct pre-loaded context."""
    print("\n[TEST] test_implement_builds_preloaded_context")
    
    # Simulate dependencies_content from analyze_and_plan
    dependencies_content = {
        "prisma/schema.prisma": "model Textbook { id Int @id }",
        "src/lib/prisma.ts": "export const prisma = new PrismaClient()",
    }
    
    # Step with dependencies
    step_dependencies = ["prisma/schema.prisma", "src/lib/prisma.ts"]
    
    # Build context
    context = _build_dependencies_context(dependencies_content, step_dependencies)
    
    # Assertions
    assert "<pre_loaded_context>" in context, "Missing pre_loaded_context tag"
    assert "prisma/schema.prisma" in context, "Missing schema.prisma in context"
    assert "model Textbook" in context, "Schema content not in context"
    assert "PrismaClient" in context, "Prisma.ts content not in context"
    
    print(f"   Context length: {len(context)} chars")
    print(f"   Contains schema: {'prisma/schema.prisma' in context}")
    print(f"   Contains prisma.ts: {'src/lib/prisma.ts' in context}")
    print("[PASS] test_implement_builds_preloaded_context")


# =============================================================================
# Test 4: E2E Flow Simulation
# =============================================================================

def test_e2e_plan_to_implement_flow():
    """End-to-end test: plan → pre-load → implement context."""
    print("\n[TEST] test_e2e_plan_to_implement_flow")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = create_test_workspace(tmpdir)
        
        # Step 1: Parse plan response
        print("   Step 1: Parsing plan response...")
        plan_data = extract_json_universal(MOCK_PLAN_RESPONSE, "plan")
        
        story_summary = plan_data["story_summary"]
        logic_analysis = plan_data["logic_analysis"]
        steps = plan_data["steps"]
        
        assert len(logic_analysis) == 3, f"Expected 3 logic entries, got {len(logic_analysis)}"
        assert len(steps) == 2, f"Expected 2 steps, got {len(steps)}"
        
        # Step 2: Pre-load dependencies
        print("   Step 2: Pre-loading dependencies...")
        dependencies_content = _preload_dependencies(workspace, steps)
        
        assert len(dependencies_content) >= 2, f"Expected 2+ deps, got {len(dependencies_content)}"
        
        # Step 3: Simulate implement for step 1
        print("   Step 3: Building implement context for step 1...")
        step1 = steps[0]
        step1_deps = step1.get("dependencies", [])
        
        context = _build_dependencies_context(dependencies_content, step1_deps)
        
        # Verify context contains what implement needs
        assert "<pre_loaded_context>" in context, "No pre_loaded_context for implement"
        assert "model Textbook" in context, "Step 1 missing Textbook model"
        
        # Step 4: Simulate implement for step 2
        print("   Step 4: Building implement context for step 2...")
        step2 = steps[1]
        step2_deps = step2.get("dependencies", [])
        
        context2 = _build_dependencies_context(dependencies_content, step2_deps)
        
        # Step 2 has no explicit dependencies, but common files should be included
        if context2:
            assert "prisma/schema.prisma" in context2 or "src/lib/prisma.ts" in context2, \
                "Common files should be in context even without explicit deps"
        
        # Summary
        print(f"\n   === E2E Flow Summary ===")
        print(f"   Story: {story_summary}")
        print(f"   Logic Analysis: {len(logic_analysis)} entries")
        print(f"   Steps: {len(steps)}")
        print(f"   Pre-loaded deps: {len(dependencies_content)} files")
        print(f"   Step 1 context: {len(context)} chars")
        print(f"   Step 2 context: {len(context2)} chars")
        
        print("[PASS] test_e2e_plan_to_implement_flow")


# =============================================================================
# Test 5: Validate Plan Format Matches Prompt Template
# =============================================================================

def test_plan_format_matches_template():
    """Verify plan output matches expected format from plan_prompts.yaml."""
    print("\n[TEST] test_plan_format_matches_template")
    
    data = extract_json_universal(MOCK_PLAN_RESPONSE, "plan")
    
    # Required fields from new template
    required_fields = ["story_summary", "logic_analysis", "steps"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Step format validation
    step_required = ["order", "description", "file_path", "action", "dependencies"]
    for i, step in enumerate(data["steps"]):
        for field in step_required:
            assert field in step, f"Step {i+1} missing field: {field}"
        
        # Action should be create/modify/delete
        assert step["action"] in ["create", "modify", "delete"], \
            f"Invalid action: {step['action']}"
        
        # Dependencies should be list
        assert isinstance(step["dependencies"], list), \
            f"Dependencies should be list: {step['dependencies']}"
    
    print(f"   All {len(required_fields)} required fields present")
    print(f"   All {len(data['steps'])} steps have correct format")
    print("[PASS] test_plan_format_matches_template")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MetaGPT-Style Planning Flow Tests")
    print("=" * 60)
    
    tests = [
        test_plan_produces_logic_analysis,
        test_preload_reads_correct_files,
        test_implement_builds_preloaded_context,
        test_e2e_plan_to_implement_flow,
        test_plan_format_matches_template,
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
