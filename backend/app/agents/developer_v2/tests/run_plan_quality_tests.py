#!/usr/bin/env python
"""Standalone test runner for Plan Node Quality.

Run: uv run app/agents/developer_v2/tests/run_plan_quality_tests.py
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

import os
if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
    print("[SKIP] No API key found (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
    sys.exit(0)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_layer_priority(file_path: str) -> int:
    """Get layer priority for a file path. Lower = should come first."""
    path = file_path.replace("\\", "/").lower()
    
    if "prisma" in path and "schema" in path:
        return 1
    if "prisma/seed" in path:
        return 1
    if "/types/" in path or path.endswith(".d.ts"):
        return 2
    if "/lib/" in path or "/utils/" in path or "/hooks/" in path:
        return 3
    if "/api/" in path and "route.ts" in path:
        return 4
    if "/actions/" in path:
        return 5
    if "page.tsx" in path or "page.ts" in path:
        return 7
    if "/components/" in path:
        return 6
    return 6


def check_ordering_violations(plan: List[Dict]) -> List[Tuple[int, int, str]]:
    """Check for layer ordering violations."""
    violations = []
    for i, step in enumerate(plan):
        file_path = step.get("file_path", "")
        current_layer = get_layer_priority(file_path)
        for j in range(i + 1, len(plan)):
            later_file = plan[j].get("file_path", "")
            later_layer = get_layer_priority(later_file)
            if later_layer < current_layer:
                violations.append((i + 1, j + 1,
                    f"Step {i+1} ({file_path}, L{current_layer}) before Step {j+1} ({later_file}, L{later_layer})"))
    return violations


def check_dependency_violations(plan: List[Dict]) -> List[Tuple[int, str]]:
    """Check for dependency violations."""
    violations = []
    for i, step in enumerate(plan):
        deps = step.get("dependencies", [])
        for dep in deps:
            if not isinstance(dep, str):
                violations.append((i + 1, f"Invalid dep type: {type(dep).__name__} ({dep})"))
            elif dep and "/" not in dep and "." not in dep:
                violations.append((i + 1, f"Suspicious dep: {dep}"))
    return violations


def calculate_ordering_score(plan: List[Dict]) -> float:
    """Calculate ordering quality score (0-100)."""
    if not plan:
        return 100.0
    violations = check_ordering_violations(plan)
    max_violations = len(plan) * (len(plan) - 1) / 2
    if max_violations == 0:
        return 100.0
    return max(0, 100 * (1 - len(violations) / max_violations))


def calculate_dependency_score(plan: List[Dict]) -> float:
    """Calculate dependency quality score (0-100)."""
    if not plan:
        return 100.0
    violations = check_dependency_violations(plan)
    return max(0, 100 * (1 - len(violations) / len(plan)))


# =============================================================================
# TEST STORIES
# =============================================================================

STORY_HOMEPAGE = {
    "story_id": "TEST-001",
    "story_title": "Homepage with Featured Books",
    "story_description": "Create homepage with hero section, featured books grid, and category navigation.",
    "story_requirements": [
        "Display hero section with featured books carousel",
        "Show bestsellers section with top 8 books",
        "Display book cards with cover, title, author, price",
    ],
    "acceptance_criteria": [
        "Given I visit homepage, When page loads, Then I see hero and book sections",
    ],
}

STORY_CRUD = {
    "story_id": "TEST-002",
    "story_title": "Book Management CRUD",
    "story_description": "Full CRUD for books with database model, API, and admin UI.",
    "story_requirements": [
        "Create Book model in Prisma with title, author, price",
        "Create API routes for GET, POST, PUT, DELETE",
        "Create admin page to list and manage books",
    ],
    "acceptance_criteria": [
        "Given I am admin, When I create a book, Then it appears in the list",
    ],
}


# =============================================================================
# TESTS
# =============================================================================

async def test_plan_quality(story: Dict, workspace_path: str):
    """Test plan quality for a story."""
    from app.agents.developer_v2.src.nodes.plan import plan
    from app.agents.developer_v2.src.tools import set_tool_context
    
    state = {
        "workspace_path": workspace_path,
        "project_id": "test-project",
        "task_id": story["story_id"],
        "tech_stack": "nextjs",
        "story_id": story["story_id"],
        "story_title": story["story_title"],
        "story_description": story["story_description"],
        "story_requirements": story["story_requirements"],
        "acceptance_criteria": story["acceptance_criteria"],
        "files_modified": [],
    }
    
    set_tool_context(workspace_path, state["project_id"], state["task_id"])
    
    print(f"\n{'='*60}")
    print(f"STORY: {story['story_title']}")
    print(f"{'='*60}")
    
    start = datetime.now()
    result = await plan(state)
    elapsed = (datetime.now() - start).total_seconds()
    
    steps = result.get("implementation_plan", [])
    print(f"\nGenerated {len(steps)} steps in {elapsed:.1f}s:\n")
    
    for i, step in enumerate(steps):
        fp = step.get("file_path", "")
        layer = get_layer_priority(fp)
        deps = step.get("dependencies", [])
        print(f"  {i+1}. [L{layer}] {fp}")
        if deps:
            print(f"       deps: {deps[:2]}{'...' if len(deps) > 2 else ''}")
    
    # Check violations
    ordering_violations = check_ordering_violations(steps)
    dep_violations = check_dependency_violations(steps)
    
    ordering_score = calculate_ordering_score(steps)
    dep_score = calculate_dependency_score(steps)
    overall = (ordering_score + dep_score) / 2
    
    print(f"\n--- QUALITY METRICS ---")
    print(f"Ordering violations: {len(ordering_violations)}")
    if ordering_violations:
        for v in ordering_violations[:3]:
            print(f"  - {v[2]}")
    print(f"Dependency violations: {len(dep_violations)}")
    print(f"Ordering Score: {ordering_score:.0f}/100")
    print(f"Dependency Score: {dep_score:.0f}/100")
    print(f"Overall Score: {overall:.0f}/100")
    
    return {
        "story": story["story_title"][:30],
        "steps": len(steps),
        "ordering": ordering_score,
        "deps": dep_score,
        "overall": overall,
        "time": elapsed,
    }


async def main():
    """Run all tests."""
    import tempfile
    import os
    
    print("=" * 60)
    print("Plan Node Quality Tests")
    print("=" * 60)
    
    # Create temp workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create basic structure
        (workspace / "src" / "app" / "api").mkdir(parents=True)
        (workspace / "src" / "components").mkdir(parents=True)
        (workspace / "src" / "lib").mkdir(parents=True)
        (workspace / "src" / "types").mkdir(parents=True)
        (workspace / "prisma").mkdir()
        
        # Create minimal files
        (workspace / "prisma" / "schema.prisma").write_text("""
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
generator client {
  provider = "prisma-client-js"
}
model Book {
  id    String @id @default(uuid())
  title String
}
""")
        (workspace / "src" / "lib" / "prisma.ts").write_text("export const prisma = {};\n")
        (workspace / "src" / "types" / "index.ts").write_text("export interface Book { id: string; title: string; }\n")
        
        results = []
        
        for story in [STORY_HOMEPAGE, STORY_CRUD]:
            try:
                result = await test_plan_quality(story, str(workspace))
                results.append(result)
            except Exception as e:
                print(f"\n[ERROR] {story['story_title']}: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        if results:
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            
            avg_ordering = sum(r["ordering"] for r in results) / len(results)
            avg_deps = sum(r["deps"] for r in results) / len(results)
            avg_overall = sum(r["overall"] for r in results) / len(results)
            
            for r in results:
                print(f"{r['story']}: {r['steps']} steps, {r['time']:.1f}s, score={r['overall']:.0f}")
            
            print(f"\nAVERAGE SCORES:")
            print(f"  Ordering: {avg_ordering:.0f}/100")
            print(f"  Dependencies: {avg_deps:.0f}/100")
            print(f"  Overall: {avg_overall:.0f}/100")
            
            if avg_overall >= 60:
                print("\n[PASS] Quality threshold met!")
                return 0
            else:
                print(f"\n[FAIL] Quality score {avg_overall:.0f} < 60")
                return 1
        
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
