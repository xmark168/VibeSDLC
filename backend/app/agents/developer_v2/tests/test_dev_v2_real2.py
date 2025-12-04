"""Test Developer V2 with 2 consecutive stories (real LangGraph execution).

Stories:
1. EPIC-001-US-001: Homepage with featured books (no dependencies)
2. EPIC-001-US-002: Search functionality (depends on US-001)

Usage:
    python backend/app/agents/developer_v2/tests/test_dev_v2_real2.py
    python backend/app/agents/developer_v2/tests/test_dev_v2_real2.py --story1
"""
import asyncio
import json
import logging
import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Add backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Boilerplate path
BOILERPLATE_PATH = backend_path / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"


def setup_workspace_from_boilerplate(temp_dir: str) -> str:
    """Copy boilerplate to temp directory for testing (legacy - uses temp dir).
    
    Args:
        temp_dir: Temporary directory path
        
    Returns:
        Workspace path
    """
    workspace_path = os.path.join(temp_dir, "workspace")
    
    if not BOILERPLATE_PATH.exists():
        raise FileNotFoundError(f"Boilerplate not found at {BOILERPLATE_PATH}")
    
    # Copy boilerplate (exclude .git, node_modules, .next)
    def ignore_patterns(directory, files):
        ignored = []
        for f in files:
            if f in ['.git', 'node_modules', '.next', '__pycache__', '.turbo']:
                ignored.append(f)
        return ignored
    
    shutil.copytree(
        BOILERPLATE_PATH,
        workspace_path,
        ignore=ignore_patterns
    )
    
    logger.info(f"[setup] Copied boilerplate to {workspace_path}")
    
    # Create .env file if not exists
    env_path = os.path.join(workspace_path, ".env")
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write("DATABASE_URL=postgresql://test:test@localhost:5432/test\n")
            f.write("NEXTAUTH_SECRET=test-secret\n")
            f.write("NEXTAUTH_URL=http://localhost:3000\n")
    
    return workspace_path


# Projects directory for persistent workspaces
PROJECTS_DIR = backend_path / "projects"


def setup_workspace_with_worktree(workspace_name: str = "ws_str2") -> tuple[str, str]:
    """Setup workspace in /backend/projects with git worktree.
    
    Flow:
    1. Copy boilerplate to /backend/projects/{workspace_name}_main
    2. Init git repo
    3. Create worktree at /backend/projects/{workspace_name}
    
    Args:
        workspace_name: Name for the worktree (default: ws_str2)
        
    Returns:
        Tuple of (worktree_path, main_workspace_path)
    """
    import subprocess
    
    if not BOILERPLATE_PATH.exists():
        raise FileNotFoundError(f"Boilerplate not found at {BOILERPLATE_PATH}")
    
    # Ensure projects directory exists
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    main_workspace = PROJECTS_DIR / f"{workspace_name}_main"
    worktree_path = PROJECTS_DIR / workspace_name
    branch_name = f"story_{workspace_name}"
    
    # Auto-cleanup existing directories if they exist (like run_dev_v2_real)
    if worktree_path.exists() or main_workspace.exists():
        print(f"[setup] Found existing workspace '{workspace_name}', removing...")
        
        if worktree_path.exists():
            # Try git worktree remove first
            try:
                subprocess.run(
                    ["git", "worktree", "remove", str(worktree_path), "--force"],
                    cwd=str(main_workspace) if main_workspace.exists() else str(PROJECTS_DIR),
                    capture_output=True,
                    timeout=30
                )
            except Exception:
                pass
            # Force remove directory
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
        
        if main_workspace.exists():
            shutil.rmtree(main_workspace, ignore_errors=True)
        
        print(f"[setup] Removed existing workspace '{workspace_name}'")
    
    # Copy boilerplate (exclude heavy dirs)
    def ignore_patterns(directory, files):
        ignored = []
        for f in files:
            if f in ['.git', 'node_modules', '.next', '__pycache__', '.turbo', 'bun.lock']:
                ignored.append(f)
        return ignored
    
    logger.info(f"[setup] Copying boilerplate to {main_workspace}")
    shutil.copytree(
        BOILERPLATE_PATH,
        main_workspace,
        ignore=ignore_patterns
    )
    
    # Create .env file
    env_path = main_workspace / ".env"
    with open(env_path, 'w') as f:
        f.write("DATABASE_URL=postgresql://test:test@localhost:5432/test\n")
        f.write("NEXTAUTH_SECRET=test-secret-key-for-testing\n")
        f.write("NEXTAUTH_URL=http://localhost:3000\n")
    
    # Init git repo
    logger.info(f"[setup] Initializing git repo in {main_workspace}")
    subprocess.run(["git", "init"], cwd=str(main_workspace), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(main_workspace), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit from boilerplate"],
        cwd=str(main_workspace),
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com"}
    )
    
    # Create branch and worktree
    logger.info(f"[setup] Creating worktree '{workspace_name}' with branch '{branch_name}'")
    
    # Create branch
    subprocess.run(
        ["git", "branch", branch_name],
        cwd=str(main_workspace),
        capture_output=True
    )
    
    # Create worktree
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=str(main_workspace),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"[setup] Failed to create worktree: {result.stderr}")
        raise RuntimeError(f"Failed to create worktree: {result.stderr}")
    
    logger.info(f"[setup] Worktree created at {worktree_path}")
    
    return str(worktree_path), str(main_workspace)


def cleanup_workspace(workspace_name: str = "ws_str2"):
    """Cleanup workspace and worktree after test."""
    import subprocess
    
    main_workspace = PROJECTS_DIR / f"{workspace_name}_main"
    worktree_path = PROJECTS_DIR / workspace_name
    
    # Remove worktree
    if main_workspace.exists():
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=str(main_workspace),
                capture_output=True,
                timeout=30
            )
        except Exception:
            pass
    
    # Remove directories
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
    if main_workspace.exists():
        shutil.rmtree(main_workspace, ignore_errors=True)
    
    logger.info(f"[cleanup] Removed workspace: {workspace_name}")

# Stories data
STORY_1 = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "story_title": "Homepage with featured books and categories",
    "story_description": """The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories. This story establishes the foundation for user engagement by presenting featured books, bestsellers, and category navigation that helps visitors understand what the store offers and guides them toward their interests.""",
    "story_requirements": [
        "Display hero section with 3-5 featured books rotating every 5 seconds",
        "Show 'Bestsellers' section with top 10 books based on sales data",
        "Display 'New Arrivals' section with latest 8 books added to catalog",
        "Present main book categories (Fiction, Non-Fiction, Children, Academic) with cover images",
        "Include promotional banner area for special offers or campaigns",
        "Show 'Recommended for You' section with 6 books",
        "All book cards display: cover image, title, author, price, and rating",
        "Implement lazy loading for images to optimize page load time under 2 seconds",
    ],
    "acceptance_criteria": [
        "Given I am a visitor on the homepage, When the page loads, Then I see hero section with featured books, bestsellers section, new arrivals section, and category navigation within 2 seconds",
        "Given I am viewing the homepage, When I see a book card, Then it displays cover image, title, author name, current price, and average rating (if available)",
        "Given I am on the homepage, When I click on a book card, Then I am navigated to that book's detail page",
        "Given I am on the homepage, When I click on a category tile, Then I am navigated to the category page showing all books in that category",
        "Given the homepage has loaded, When I wait 5 seconds, Then the hero section automatically transitions to the next featured book",
    ],
}

STORY_2 = {
    "story_id": "EPIC-001-US-002",
    "epic": "EPIC-001",
    "story_title": "Search books by title, author, or keyword",
    "story_description": """The search functionality enables visitors to actively find books rather than browsing through categories. This story implements a prominent search bar with autocomplete suggestions that helps users discover books efficiently, reducing the time from intent to finding desired books and improving overall user experience.""",
    "story_requirements": [
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
        "Given I search for a term with no matches, When the search completes, Then I see a 'No results found' message with suggestions to try different keywords",
        "Given I am viewing autocomplete suggestions, When I use arrow keys to navigate suggestions, Then the selected suggestion is highlighted and I can press Enter to select it",
    ],
}


def format_story_content(story: dict) -> str:
    """Format story dict to content string for processing."""
    return json.dumps({
        "story_id": story["story_id"],
        "title": story["story_title"],
        "content": f"""## {story['story_title']}

**ID:** {story['story_id']}
**Epic:** {story['epic']}

### Description
{story['story_description']}

### Requirements
{chr(10).join(f'- {r}' for r in story['story_requirements'])}

### Acceptance Criteria
{chr(10).join(f'- {ac}' for ac in story['acceptance_criteria'])}
""",
        "acceptance_criteria": story["acceptance_criteria"],
    })


def _setup_langfuse(story_id: str, story_title: str):
    """Setup Langfuse tracing for a story run."""
    try:
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler
        
        langfuse = get_client()
        langfuse_ctx = langfuse.start_as_current_observation(
            as_type="span",
            name=f"test_story_{story_id}"
        )
        langfuse_span = langfuse_ctx.__enter__()
        langfuse_span.update_trace(
            user_id="test-user",
            session_id="test-dev-v2-real2",
            input={"story_id": story_id, "title": story_title},
            tags=["developer_v2", "test"],
            metadata={"test_file": "test_dev_v2_real2.py"}
        )
        langfuse_handler = CallbackHandler()
        return langfuse_handler, langfuse_ctx, langfuse_span
    except Exception as e:
        logger.debug(f"Langfuse setup skipped: {e}")
        return None, None, None


def _close_langfuse(langfuse_ctx, langfuse_span, final_state: dict, error: Exception = None):
    """Close Langfuse span with output data."""
    if not langfuse_ctx or not langfuse_span:
        return
    try:
        if error:
            langfuse_ctx.__exit__(type(error), error, error.__traceback__)
        else:
            langfuse_span.update_trace(output={
                "action": final_state.get("action"),
                "task_type": final_state.get("task_type"),
                "total_steps": final_state.get("total_steps", 0),
                "files_modified": final_state.get("files_modified", []),
                "run_status": final_state.get("run_status"),
                "debug_count": final_state.get("debug_count", 0),
            })
            langfuse_ctx.__exit__(None, None, None)
        logger.info("[langfuse] Trace closed")
    except Exception as e:
        logger.debug(f"Langfuse close error: {e}")


async def run_story(graph, story: dict, workspace_path: str, story_num: int) -> dict:
    """Run a single story through the graph with Langfuse tracing."""
    logger.info(f"\n{'='*70}")
    logger.info(f"STORY {story_num}: {story['story_id']} - {story['story_title'][:50]}...")
    logger.info(f"{'='*70}")
    
    start_time = datetime.now()
    
    # Setup Langfuse tracing
    langfuse_handler, langfuse_ctx, langfuse_span = _setup_langfuse(
        story["story_id"], story["story_title"]
    )
    
    # Build initial state
    initial_state = {
        "story_id": story["story_id"],
        "epic": story["epic"],
        "story_title": story["story_title"],
        "story_description": story["story_description"],
        "story_requirements": story["story_requirements"],
        "acceptance_criteria": story["acceptance_criteria"],
        "project_id": "test-project",
        "task_id": story["story_id"],
        "user_id": "test-user",
        "langfuse_handler": langfuse_handler,
        
        # Workspace
        "workspace_path": workspace_path,
        "branch_name": f"story-{story['story_id'].lower()}",
        "main_workspace": workspace_path,
        "workspace_ready": True,
        "index_ready": False,
        "merged": False,
        
        # Workflow state
        "action": None,
        "task_type": None,
        "complexity": None,
        "analysis_result": None,
        "implementation_plan": [],
        "files_created": [],
        "files_modified": [],
        "affected_files": [],
        "current_step": 0,
        "total_steps": 0,
        "validation_result": None,
        "message": None,
        
        # Design
        "logic_analysis": [],
        "dependencies_content": {},
        
        # Run/test state
        "run_status": None,
        "run_result": None,
        "run_stdout": "",
        "run_stderr": "",
        "error_logs": "",
        
        # Debug state
        "debug_count": 0,
        "max_debug": 5,
        "debug_history": [],
        "error_analysis": None,
        
        # Review
        "review_result": None,
        "review_feedback": None,
        "review_count": 0,
        "total_lbtm_count": 0,
        
        # Summarize
        "is_pass": None,
        "summarize_count": 0,
        
        # Tech stack
        "tech_stack": "nextjs",
        "skill_registry": None,
        
        # Context
        "project_context": None,
        "agents_md": None,
        
        # Project config for run_code
        "project_config": {
               "tech_stack": {
                    "name": "nextjs-app",
                    "service": [
                        {
                            "name": "app",
                            "path": ".",
                            "runtime": "bun",
                            "framework": "nextjs",
                            "orm": "prisma",
                            "db_type": "postgresql",
                            "validation": "zod",
                            "auth": "next-auth",
                            "install_cmd": "bun install",
                            "test_cmd": "bun run test",
                            "run_cmd": "bun dev",
                            "build_cmd": "bun run build",
                            "lint_cmd": "bun run lint",
                            "lint_fix_cmd": "bunx eslint --fix . --ext .ts,.tsx,.js,.jsx",
                            "format_cmd": "bunx prettier --write .",
                            "needs_db": True,
                            "db_cmds": ["bunx prisma generate", "bunx prisma db push --accept-data-loss"],
                        }
                    ]
                }
        },
    }
    
    try:
        # Increase recursion limit for complex stories (steps * retries)
        config = {"recursion_limit": 100}
        final_state = await graph.ainvoke(initial_state, config=config)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Close Langfuse trace with success
        _close_langfuse(langfuse_ctx, langfuse_span, final_state)
        
        result = {
            "story_id": story["story_id"],
            "success": True,
            "elapsed_seconds": elapsed,
            "action": final_state.get("action"),
            "task_type": final_state.get("task_type"),
            "complexity": final_state.get("complexity"),
            "total_steps": final_state.get("total_steps", 0),
            "files_modified": final_state.get("files_modified", []),
            "files_created": final_state.get("files_created", []),
            "run_status": final_state.get("run_status"),
            "review_result": final_state.get("review_result"),
            "is_pass": final_state.get("is_pass"),
            "debug_count": final_state.get("debug_count", 0),
            "message": final_state.get("message", "")[:200],
            "error": final_state.get("error"),
        }
        
        logger.info(f"\n[RESULT] Story {story_num} completed in {elapsed:.1f}s")
        logger.info(f"  Action: {result['action']}")
        logger.info(f"  Steps: {result['total_steps']}")
        logger.info(f"  Files modified: {len(result['files_modified'])}")
        logger.info(f"  Run status: {result['run_status']}")
        logger.info(f"  Debug attempts: {result['debug_count']}")
        
        return result
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Close Langfuse trace with error
        _close_langfuse(langfuse_ctx, langfuse_span, {}, error=e)
        
        logger.error(f"[ERROR] Story {story_num} failed: {e}", exc_info=True)
        return {
            "story_id": story["story_id"],
            "success": False,
            "elapsed_seconds": elapsed,
            "error": str(e),
        }


async def test_two_stories_sequential():
    """Test running 2 stories sequentially."""
    print("\n" + "=" * 70)
    print("Developer V2 - Two Stories Sequential Test")
    print("=" * 70)
    
    # Import graph
    try:
        from app.agents.developer_v2.src.graph import DeveloperGraph
    except ImportError as e:
        print(f"[SKIP] Cannot import DeveloperGraph: {e}")
        print("Run this test from backend directory with proper environment")
        return None
    
    # Setup workspace from boilerplate
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            workspace_path = setup_workspace_from_boilerplate(temp_dir)
        except FileNotFoundError as e:
            print(f"[SKIP] {e}")
            return None
        
        print(f"\nWorkspace: {workspace_path}")
        
        # Initialize graph (without agent for standalone test)
        graph_engine = DeveloperGraph(agent=None)
        graph = graph_engine.graph
        
        results = []
        total_start = datetime.now()
        
        # Run Story 1
        result1 = await run_story(graph, STORY_1, workspace_path, 1)
        results.append(result1)
        
        # Run Story 2 (depends on Story 1)
        result2 = await run_story(graph, STORY_2, workspace_path, 2)
        results.append(result2)
        
        total_elapsed = (datetime.now() - total_start).total_seconds()
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        for r in results:
            status = "PASS" if r["success"] else "FAIL"
            print(f"\n[{status}] {r['story_id']}")
            print(f"  Time: {r['elapsed_seconds']:.1f}s")
            if r["success"]:
                print(f"  Steps: {r.get('total_steps', 0)}")
                print(f"  Files: {len(r.get('files_modified', []))}")
                print(f"  Run: {r.get('run_status', 'N/A')}")
            else:
                print(f"  Error: {r.get('error', 'Unknown')[:100]}")
        
        print(f"\nTotal time: {total_elapsed:.1f}s")
        print(f"Stories: {len([r for r in results if r['success']])}/{len(results)} passed")
        
        return results


async def test_story_1_only():
    """Test just Story 1 (Homepage) for quick validation."""
    print("\n" + "=" * 70)
    print("Developer V2 - Story 1 Only Test")
    print("=" * 70)
    
    try:
        from app.agents.developer_v2.src.graph import DeveloperGraph
    except ImportError as e:
        print(f"[SKIP] Cannot import: {e}")
        return None
    
    # Setup workspace from boilerplate
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            workspace_path = setup_workspace_from_boilerplate(temp_dir)
        except FileNotFoundError as e:
            print(f"[SKIP] {e}")
            return None
        
        print(f"Workspace: {workspace_path}")
        
        graph_engine = DeveloperGraph(agent=None)
        result = await run_story(graph_engine.graph, STORY_1, workspace_path, 1)
        
        print("\n" + "=" * 70)
        status = "PASS" if result["success"] else "FAIL"
        print(f"[{status}] {result['story_id']} - {result['elapsed_seconds']:.1f}s")
        print("=" * 70)
        
        return result


async def test_with_worktree(workspace_name: str = "ws_str2", cleanup: bool = False):
    """Test with persistent workspace using git worktree in /backend/projects.
    
    This creates:
    - /backend/projects/{workspace_name}_main  (main repo with boilerplate)
    - /backend/projects/{workspace_name}       (worktree for development)
    
    Args:
        workspace_name: Name for worktree directory (default: ws_str2)
        cleanup: Whether to cleanup after test (default: False - keep workspace)
    """
    print("\n" + "=" * 70)
    print(f"Developer V2 - Worktree Test ({workspace_name})")
    print("=" * 70)
    
    try:
        from app.agents.developer_v2.src.graph import DeveloperGraph
    except ImportError as e:
        print(f"[SKIP] Cannot import: {e}")
        return None
    
    try:
        # Setup workspace with worktree
        worktree_path, main_workspace = setup_workspace_with_worktree(workspace_name)
        print(f"\nMain workspace: {main_workspace}")
        print(f"Worktree: {worktree_path}")
        
        # Initialize graph
        graph_engine = DeveloperGraph(agent=None)
        graph = graph_engine.graph
        
        results = []
        total_start = datetime.now()
        
        # Run Story 1
        result1 = await run_story(graph, STORY_1, worktree_path, 1)
        results.append(result1)
        
        # Run Story 2
        result2 = await run_story(graph, STORY_2, worktree_path, 2)
        results.append(result2)
        
        total_elapsed = (datetime.now() - total_start).total_seconds()
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        for r in results:
            status = "PASS" if r["success"] else "FAIL"
            print(f"\n[{status}] {r['story_id']}")
            print(f"  Time: {r['elapsed_seconds']:.1f}s")
            if r["success"]:
                print(f"  Steps: {r.get('total_steps', 0)}")
                print(f"  Files: {len(r.get('files_modified', []))}")
                print(f"  Run: {r.get('run_status', 'N/A')}")
            else:
                print(f"  Error: {r.get('error', 'Unknown')[:100]}")
        
        print(f"\nTotal time: {total_elapsed:.1f}s")
        print(f"Stories: {len([r for r in results if r['success']])}/{len(results)} passed")
        print(f"\nWorkspace preserved at: {worktree_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        return None
        
    finally:
        if cleanup:
            cleanup_workspace(workspace_name)
            print(f"\n[cleanup] Workspace '{workspace_name}' removed")
        else:
            print(f"\n[info] Workspace preserved at: {PROJECTS_DIR / workspace_name}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Developer V2 with stories")
    parser.add_argument("--story1", action="store_true", help="Run only Story 1 (temp workspace)")
    parser.add_argument("--both", action="store_true", help="Run both stories in temp workspace (default)")
    parser.add_argument("--worktree", action="store_true", help="Run with persistent worktree in /backend/projects")
    parser.add_argument("--name", type=str, default="ws_str2", help="Worktree name (default: ws_str2)")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup workspace after test (default: keep)")
    args = parser.parse_args()
    
    if args.story1:
        result = asyncio.run(test_story_1_only())
    elif args.worktree:
        result = asyncio.run(test_with_worktree(
            workspace_name=args.name,
            cleanup=args.cleanup
        ))
    else:
        result = asyncio.run(test_two_stories_sequential())
    
    if result is None:
        sys.exit(2)  # Skip
    elif isinstance(result, list):
        success = all(r["success"] for r in result)
    else:
        success = result.get("success", False)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
