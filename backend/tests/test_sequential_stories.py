"""Test 3 sequential stories on same workspace - FULL FLOW (plan + implement + run_code)."""
import asyncio
import time
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.agents.developer_v2.src.nodes.plan import plan, FileRepository
from app.agents.developer_v2.src.nodes.implement import implement_parallel
from app.agents.developer_v2.src.nodes.run_code import run_code
from app.agents.developer_v2.src.nodes.parallel_utils import group_steps_by_layer

# 3 Sequential Stories
STORIES = [
    {
        "id": "EPIC-001-US-001",
        "title": "Homepage Featured Books",
        "description": "As a first-time visitor, I want to see featured books and categories on the homepage so that I can quickly discover interesting books without searching",
        "requirements": [
            "Display hero section with 3-5 featured books rotating every 5 seconds",
            "Show 'Bestsellers' section with top 10 books based on sales data",
            "Display 'New Arrivals' section with latest 8 books added to catalog",
            "Present main book categories (Fiction, Non-Fiction, Children, Academic, etc.) with representative cover images",
            "Include promotional banner area for special offers or campaigns",
            "Show 'Recommended for You' section with 6 books",
            "Ensure all book cards display: cover image, title, author, price, and rating",
            "Implement lazy loading for images to optimize page load time under 2 seconds",
        ],
        "acceptance_criteria": [
            "Given I am a visitor on the homepage, When the page loads, Then I see hero section with featured books, bestsellers section, new arrivals section, and category navigation within 2 seconds",
            "Given I am viewing the homepage, When I see a book card, Then it displays cover image, title, author name, current price, and average rating",
            "Given I am on the homepage, When I click on a book card, Then I am navigated to that book's detail page",
            "Given I am on the homepage, When I click on a category tile, Then I am navigated to the category page showing all books in that category",
        ],
    },
    {
        "id": "EPIC-001-US-002",
        "title": "Search with Autocomplete",
        "description": "As a visitor, I want to search for books by title, author, or keyword so that I can quickly find specific books I'm interested in",
        "requirements": [
            "Display search bar prominently in the header, visible on all pages",
            "Implement autocomplete that shows suggestions after user types 2+ characters",
            "Search across book titles, author names, and ISBN numbers",
            "Show up to 8 autocomplete suggestions with book cover thumbnail, title, and author",
            "Display 'No results found' message when search yields no matches",
            "Highlight matching text in autocomplete suggestions",
            "Return search results within 1 second for optimal user experience",
            "Preserve search query in the search bar after navigating to results page",
        ],
        "acceptance_criteria": [
            "Given I am on any page, When I type 2 or more characters in the search bar, Then I see up to 8 autocomplete suggestions within 1 second",
            "Given I see autocomplete suggestions, When I click on a suggestion, Then I am navigated to that book's detail page",
            "Given I have typed a search query, When I press Enter or click the search button, Then I am navigated to the search results page showing all matching books",
            "Given I search for a term with no matches, When the search completes, Then I see a 'No results found' message",
        ],
    },
    {
        "id": "EPIC-001-US-003",
        "title": "Filter and Sort Search Results",
        "description": "As a visitor, I want to filter and sort search results by category, price range, and author so that I can narrow down my options to find the most relevant books",
        "requirements": [
            "Display filter panel on the left side of search results page with collapsible sections",
            "Implement category filter with checkboxes for all available book categories",
            "Provide price range filter with min/max input fields and predefined ranges",
            "Include author filter with searchable dropdown showing authors from current results",
            "Add rating filter with star rating options (4+ stars, 3+ stars, etc.)",
            "Implement sort dropdown with options: Relevance, Price Low to High, Price High to Low, Newest First, Best Rated",
            "Show active filter count badge and 'Clear All Filters' button when filters are applied",
            "Update results dynamically within 1 second when filters or sort order changes",
        ],
        "acceptance_criteria": [
            "Given I am on the search results page, When I select one or more category filters, Then the results update to show only books in selected categories within 1 second",
            "Given I am viewing filtered results, When I enter a price range, Then the results show only books within that price range",
            "Given I have applied multiple filters, When I click 'Clear All Filters', Then all filters are removed",
            "Given I am on the search results page, When I change the sort order dropdown, Then the results reorder immediately",
        ],
    },
]


async def test_sequential():
    """Test 3 stories sequentially on same workspace - FULL FLOW."""
    from uuid import uuid4
    from app.agents.developer_v2.src.tools.workspace_manager import ProjectWorkspaceManager
    from app.agents.developer_v2.src.skills.registry import SkillRegistry
    import subprocess
    
    print("=" * 70)
    print("SEQUENTIAL STORIES TEST - FULL FLOW (Plan + Implement + Run)")
    print("=" * 70)
    
    # Create workspace once
    print("\n[1/4] Creating workspace...")
    project_id = uuid4()
    ws = ProjectWorkspaceManager(project_id)
    workspace_path = str(ws.get_main_workspace())
    print(f"Workspace: {workspace_path}")
    
    # Install dependencies once
    print("\n[2/4] Installing dependencies (pnpm install)...")
    subprocess.run("pnpm install", cwd=workspace_path, shell=True, capture_output=True)
    print("Done!")
    
    all_results = []
    total_files_created = 0
    
    for i, story in enumerate(STORIES, 1):
        print(f"\n{'='*70}")
        print(f"STORY {i}/3: {story['title']}")
        print(f"{'='*70}")
        
        story_start = time.time()
        
        # Check FileRepository state before planning
        repo = FileRepository(workspace_path)
        print(f"\n[FileRepository] Before plan:")
        print(f"  - Total files: {len(repo.file_tree)}")
        print(f"  - Components: {len(repo.components)}")
        print(f"  - API routes: {len(repo.api_routes)}")
        if repo.components:
            print(f"  - Component names: {list(repo.components.keys())}")
        
        # Build state with proper config
        state = {
            "workspace_path": workspace_path,
            "project_id": str(project_id),
            "story_id": story["id"],
            "story_title": story["title"],
            "story_description": story["description"],
            "story_requirements": story["requirements"],
            "acceptance_criteria": story["acceptance_criteria"],
            "tech_stack": "nextjs",
            "use_code_review": False,  # Skip review for speed
            "langfuse_trace_id": f"sequential-test-story-{i}",
            "project_config": {
                "tech_stack": {
                    "name": "nextjs",
                    "service": [
                        {
                            "name": "frontend",
                            "path": "",
                            "typecheck_cmd": "pnpm run typecheck",
                            "build_cmd": "pnpm run build",
                            "format_cmd": "pnpm exec prettier --write .",
                            "lint_fix_cmd": "pnpm run lint:fix",
                        }
                    ]
                }
            },
        }
        
        # === PHASE 1: PLAN ===
        print(f"\n[Phase 1] Planning...")
        plan_start = time.time()
        state = await plan(state)
        plan_time = time.time() - plan_start
        
        steps = state.get("implementation_plan", [])
        layers = state.get("parallel_layers", {})
        
        print(f"  - {len(steps)} steps in {plan_time:.1f}s")
        print(f"  - {len(layers)} parallel layers")
        
        # Print steps
        print("\n  Steps:")
        for step in steps:
            action = step.get('action', 'create')
            print(f"    {step['order']:2}. [{action}] {step['file_path']}")
        
        # === PHASE 2: IMPLEMENT ===
        print(f"\n[Phase 2] Implementing...")
        impl_start = time.time()
        
        # Load skill registry
        skill_registry = SkillRegistry.load("nextjs")
        state["skill_registry"] = skill_registry
        
        state = await implement_parallel(state)
        impl_time = time.time() - impl_start
        
        modified_files = state.get("files_modified", [])
        print(f"  - Modified {len(modified_files)} files in {impl_time:.1f}s")
        
        # === PHASE 3: RUN CODE (typecheck + build) ===
        print(f"\n[Phase 3] Running typecheck + build...")
        run_start = time.time()
        state = await run_code(state)
        run_time = time.time() - run_start
        
        run_result = state.get("run_result", {})
        status = run_result.get("status", "UNKNOWN")
        print(f"  - Status: {status} in {run_time:.1f}s")
        
        if status == "FAIL":
            error = run_result.get("error", "")[:500]
            print(f"  - Error: {error}")
        
        # Total time for this story
        story_time = time.time() - story_start
        
        # Analyze result
        result_info = {
            "story": story["title"],
            "steps": len(steps),
            "plan_time": plan_time,
            "impl_time": impl_time,
            "run_time": run_time,
            "total_time": story_time,
            "files_modified": len(modified_files),
            "status": status,
        }
        all_results.append(result_info)
        total_files_created += len(modified_files)
        
        # Check quality
        issues = []
        
        # 1. Schema should be modify for story 2, 3
        if i > 1:
            schema_steps = [s for s in steps if "schema.prisma" in s.get("file_path", "")]
            for s in schema_steps:
                if s.get("action") == "create":
                    issues.append("Schema should be 'modify' not 'create'")
        
        if issues:
            print(f"\n[Issues] {issues}")
        
        print(f"\n[Story {i}] Completed in {story_time:.1f}s - {status}")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    print("\n| Story | Steps | Plan | Impl | Run | Total | Status |")
    print("|-------|-------|------|------|-----|-------|--------|")
    for r in all_results:
        print(f"| {r['story'][:20]:20} | {r['steps']:5} | {r['plan_time']:4.1f}s | {r['impl_time']:4.1f}s | {r['run_time']:4.1f}s | {r['total_time']:5.1f}s | {r['status']:6} |")
    
    total_time = sum(r["total_time"] for r in all_results)
    total_steps = sum(r["steps"] for r in all_results)
    pass_count = sum(1 for r in all_results if r["status"] == "PASS")
    
    print(f"\nTotal: {total_steps} steps, {total_time:.1f}s, {total_files_created} files, {pass_count}/3 PASS")
    
    # Check final workspace state
    final_repo = FileRepository(workspace_path)
    print(f"\n[Final Workspace]")
    print(f"  - Total files: {len(final_repo.file_tree)}")
    print(f"  - Components: {len(final_repo.components)}")
    print(f"  - API routes: {len(final_repo.api_routes)}")
    
    if final_repo.components:
        print(f"\n  Components ({len(final_repo.components)}):")
        for name in sorted(final_repo.components.keys()):
            print(f"    - {name}")
    
    if final_repo.api_routes:
        print(f"\n  API routes ({len(final_repo.api_routes)}):")
        for route in sorted(final_repo.api_routes):
            print(f"    - {route}")
    
    return all_results


if __name__ == "__main__":
    asyncio.run(test_sequential())
