"""Test plan node with real LLM - HOMEPAGE_STORY.

Run: uv run python app/agents/developer_v2/tests/run_plan_real.py
"""
import asyncio
import json
import time
import shutil
import logging
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

Create the foundational homepage that serves as the entry point for all customers. This page must establish trust, showcase the bookstore's offerings, and provide clear navigation paths.""",
    "requirements": [
        "Display hero section with main value proposition and call-to-action button",
        "Show featured/bestselling textbooks section with book covers, titles, prices",
        "Include prominent search bar at the top of the page",
        "Display trust indicators: return policy, genuine books guarantee",
        "Show category navigation menu organized by grade levels",
    ],
    "acceptance_criteria": [
        "Given a user visits the homepage, When the page loads, Then they see the hero section, featured books, search bar",
        "Given a user views featured books, When they hover over a book, Then they see a visual indication",
    ]
}


async def main():
    from app.agents.developer_v2.src.nodes.plan import plan
    from app.agents.developer_v2.src.skills import SkillRegistry
    
    print("=" * 70)
    print("TEST: Plan Node with Real LLM - HOMEPAGE_STORY")
    print("=" * 70)
    
    # Create temp workspace by copying boilerplate
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "bookstore"
        
        # Copy boilerplate (exclude node_modules and .git for speed)
        print(f"Copying boilerplate from {BOILERPLATE_PATH}...")
        
        def ignore_patterns(dir, files):
            return [f for f in files if f in ['node_modules', '.git', '.next']]
        
        shutil.copytree(BOILERPLATE_PATH, workspace, ignore=ignore_patterns)
        print(f"Workspace created at {workspace}")
        
        # Prepare state
        req_text = "\n".join(f"- {r}" for r in HOMEPAGE_STORY["requirements"])
        ac_text = "\n".join(f"- {ac}" for ac in HOMEPAGE_STORY["acceptance_criteria"])
        
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
            "acceptance_criteria": HOMEPAGE_STORY["acceptance_criteria"],
            "files_modified": [],
        }
        
        print(f"\nWorkspace: {workspace}")
        print(f"Story: {HOMEPAGE_STORY['title']}")
        print(f"Requirements: {len(HOMEPAGE_STORY['requirements'])}")
        
        # Run plan
        print("\n" + "-" * 70)
        print("Running plan node...")
        print("-" * 70)
        
        start_time = time.time()
        result = await plan(state)
        elapsed = time.time() - start_time
        
        print(f"\nPlan completed in {elapsed:.1f}s")
        
        # Output results
        steps = result.get("implementation_plan", [])
        total_steps = result.get("total_steps", 0)
        can_parallel = result.get("can_parallel", False)
        parallel_layers = result.get("parallel_layers", {})
        
        print("\n" + "=" * 70)
        print(f"PLAN OUTPUT: {total_steps} steps")
        print("=" * 70)
        
        for step in steps:
            order = step.get("order", "?")
            file_path = step.get("file_path", "unknown")
            action = step.get("action", "?")
            task = step.get("task", step.get("description", ""))[:80]
            skills = step.get("skills", [])
            deps = step.get("dependencies", [])
            
            print(f"\n[{order}] {file_path}")
            print(f"    Action: {action}")
            print(f"    Task: {task}...")
            print(f"    Skills: {skills}")
            print(f"    Dependencies: {deps}")
        
        # Parallel analysis
        print("\n" + "=" * 70)
        print("PARALLEL ANALYSIS")
        print("=" * 70)
        print(f"Can use parallel: {can_parallel}")
        
        if parallel_layers:
            print("\nLayer distribution:")
            for layer_num in sorted(parallel_layers.keys()):
                files = parallel_layers[layer_num]
                mode = "PARALLEL" if len(files) > 1 else "SEQ"
                print(f"  Layer {layer_num}: {len(files)} files - {mode}")
                for f in files:
                    print(f"    - {f}")
        
        # Quality checks
        print("\n" + "=" * 70)
        print("QUALITY CHECKS")
        print("=" * 70)
        
        has_schema = any("schema" in s.get("file_path", "").lower() for s in steps)
        has_seed = any("seed" in s.get("file_path", "").lower() for s in steps)
        api_steps = [s for s in steps if "/api/" in s.get("file_path", "")]
        component_steps = [s for s in steps if "/components/" in s.get("file_path", "")]
        page_steps = [s for s in steps if "page.tsx" in s.get("file_path", "")]
        steps_with_deps = [s for s in steps if s.get("dependencies")]
        steps_with_skills = [s for s in steps if s.get("skills")]
        
        print(f"Has schema step: {has_schema}")
        print(f"Has seed step: {has_seed}")
        print(f"API routes: {len(api_steps)}")
        print(f"Components: {len(component_steps)}")
        print(f"Pages: {len(page_steps)}")
        print(f"Steps with dependencies: {len(steps_with_deps)}/{total_steps}")
        print(f"Steps with skills: {len(steps_with_skills)}/{total_steps}")
        
        # Message output
        print("\n" + "=" * 70)
        print("MESSAGE OUTPUT")
        print("=" * 70)
        print(result.get("message", "No message"))
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
