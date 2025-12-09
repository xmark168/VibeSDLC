"""Test plan + implement with real LLM - HOMEPAGE_STORY.

Run: uv run python app/agents/developer_v2/tests/run_plan_implement_real.py
"""
import asyncio
import time
import shutil
import logging
import os
from pathlib import Path

# Load env
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

# Boilerplate path
BOILERPLATE_PATH = backend_dir / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

HOMEPAGE_STORY = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "title": "Homepage with Featured Books",
    "description": """As a first-time visitor, I want to see a clear homepage layout with featured books so that I can quickly understand what the bookstore offers and start browsing.

Create the foundational homepage that serves as the entry point for all customers.""",
    "requirements": [
        "Display hero section with main value proposition and call-to-action button",
        "Show featured/bestselling textbooks section with book covers, titles, prices",
        "Include prominent search bar at the top of the page",
        "Display trust indicators: return policy, genuine books guarantee",
        "Show category navigation menu organized by grade levels",
    ],
}

# Limit steps to test (to save time/cost)
MAX_IMPLEMENT_STEPS = 5


async def main():
    from app.agents.developer_v2.src.nodes.plan import plan
    from app.agents.developer_v2.src.nodes.implement import implement
    from app.agents.developer_v2.src.skills import SkillRegistry
    
    print("=" * 70)
    print("TEST: Plan + Implement with Real LLM")
    print("=" * 70)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "bookstore"
        
        # Copy boilerplate
        print(f"Copying boilerplate...")
        def ignore_patterns(dir, files):
            return [f for f in files if f in ['node_modules', '.git', '.next']]
        shutil.copytree(BOILERPLATE_PATH, workspace, ignore=ignore_patterns)
        print(f"Workspace: {workspace}")
        
        # =====================================================================
        # PHASE 1: PLAN
        # =====================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: PLAN")
        print("=" * 70)
        
        state = {
            "workspace_path": str(workspace),
            "project_id": "test-bookstore",
            "task_id": HOMEPAGE_STORY["story_id"],
            "story_id": HOMEPAGE_STORY["story_id"],
            "epic": HOMEPAGE_STORY["epic"],
            "tech_stack": "nextjs",
            "story_title": HOMEPAGE_STORY["title"],
            "story_description": HOMEPAGE_STORY["description"],
            "story_requirements": HOMEPAGE_STORY["requirements"],
            "files_modified": [],
        }
        
        plan_start = time.time()
        state = await plan(state)
        plan_time = time.time() - plan_start
        
        steps = state.get("implementation_plan", [])
        print(f"\nPlan completed: {len(steps)} steps in {plan_time:.1f}s")
        
        for step in steps[:MAX_IMPLEMENT_STEPS + 2]:
            print(f"  [{step.get('order')}] {step.get('file_path')} - {step.get('action')}")
        if len(steps) > MAX_IMPLEMENT_STEPS + 2:
            print(f"  ... and {len(steps) - MAX_IMPLEMENT_STEPS - 2} more steps")
        
        # =====================================================================
        # PHASE 2: IMPLEMENT (first N steps)
        # =====================================================================
        print("\n" + "=" * 70)
        print(f"PHASE 2: IMPLEMENT (first {MAX_IMPLEMENT_STEPS} steps)")
        print("=" * 70)
        
        implement_times = []
        generated_files = {}
        
        for i in range(min(MAX_IMPLEMENT_STEPS, len(steps))):
            step = steps[i]
            file_path = step.get("file_path", "unknown")
            
            print(f"\n--- Step {i+1}/{MAX_IMPLEMENT_STEPS}: {file_path} ---")
            
            # Set current step
            state["current_step"] = i
            state["total_steps"] = len(steps)
            state["review_count"] = 0
            state["complexity"] = "low"  # Skip review for speed
            
            step_start = time.time()
            state = await implement(state)
            step_time = time.time() - step_start
            implement_times.append(step_time)
            
            print(f"  Completed in {step_time:.1f}s")
            
            # Read generated file
            full_path = workspace / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                generated_files[file_path] = content
                lines = len(content.split('\n'))
                print(f"  Generated: {lines} lines, {len(content)} chars")
            else:
                print(f"  WARNING: File not created!")
        
        total_implement_time = sum(implement_times)
        avg_implement_time = total_implement_time / len(implement_times) if implement_times else 0
        
        # =====================================================================
        # RESULTS SUMMARY
        # =====================================================================
        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        
        print(f"\nTiming:")
        print(f"  Plan: {plan_time:.1f}s")
        print(f"  Implement ({len(implement_times)} steps): {total_implement_time:.1f}s")
        print(f"  Average per step: {avg_implement_time:.1f}s")
        print(f"  Total: {plan_time + total_implement_time:.1f}s")
        
        print(f"\nFiles generated: {len(generated_files)}")
        for fp, content in generated_files.items():
            lines = len(content.split('\n'))
            print(f"  - {fp}: {lines} lines")
        
        # =====================================================================
        # GENERATED CODE
        # =====================================================================
        print("\n" + "=" * 70)
        print("GENERATED CODE")
        print("=" * 70)
        
        for file_path, content in generated_files.items():
            print(f"\n### {file_path}")
            print("-" * 50)
            # Truncate long files
            if len(content) > 3000:
                print(content[:1500])
                print(f"\n... [{len(content) - 3000} chars truncated] ...\n")
                print(content[-1500:])
            else:
                print(content)
            print("-" * 50)
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
