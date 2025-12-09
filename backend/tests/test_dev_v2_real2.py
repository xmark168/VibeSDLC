"""Test Developer V2 with 2 consecutive stories (real LangGraph execution).

Uses SimpleDeveloperRunner pattern from run_dev_v2_real.py to let graph
handle workspace setup via setup_workspace node.

Usage:
    python backend/app/agents/developer_v2/tests/test_dev_v2_real2.py
    python backend/app/agents/developer_v2/tests/test_dev_v2_real2.py --story1
"""
import asyncio
import logging
import os
import stat
import sys
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add backend path for imports
backend_path = Path(__file__).parent.parent  # tests -> backend
sys.path.insert(0, str(backend_path))

# Load .env
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3", "git"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Boilerplate and projects paths
BOILERPLATE_PATH = backend_path / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"
PROJECTS_DIR = backend_path / "projects"

# Directories to ignore when copying boilerplate
IGNORE_DIRS = {'node_modules', '.next', '.swc', '__pycache__', '.turbo', 'tsconfig.tsbuildinfo'}


def copy_boilerplate(template_name: str, target_path: Path) -> bool:
    """Copy boilerplate template to target workspace."""
    if not BOILERPLATE_PATH.exists():
        logger.warning(f"Boilerplate not found: {BOILERPLATE_PATH}")
        target_path.mkdir(parents=True, exist_ok=True)
        return False
    
    def ignore_patterns(directory, files):
        return [f for f in files if f in IGNORE_DIRS]
    
    try:
        if target_path.exists():
            def onerror(func, path, exc_info):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            shutil.rmtree(target_path, onerror=onerror)
        
        shutil.copytree(BOILERPLATE_PATH, target_path, ignore=ignore_patterns)
        logger.info(f"[setup] Copied boilerplate to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy boilerplate: {e}")
        target_path.mkdir(parents=True, exist_ok=True)
        return False


class SimpleDeveloperRunner:
    """Runner for DeveloperV2 - mirrors run_dev_v2_real.py pattern."""
    
    def __init__(self, workspace_path: str, template: str = "nextjs"):
        self.name = "DeveloperV2"
        self.role_type = "developer"
        self.project_id = str(uuid4())
        self.template = template
        self.workspace_path = Path(workspace_path)
        self.active_workspace = None  # Track workspace from first story for reuse
        
        # Apply boilerplate
        self.template_applied = copy_boilerplate(template, self.workspace_path)
        
        # Import and init graph with parallel execution
        from app.agents.developer_v2.src.graph import DeveloperGraph
        self.graph = DeveloperGraph(agent=self, parallel=True)
        
        logger.info(f"[{self.name}] Workspace: {self.workspace_path} (parallel=True)")
    
    def _setup_workspace(self, story_id: str) -> dict:
        """Setup git workspace and branch - called by graph's setup_workspace node."""
        from app.agents.developer_v2.src.tools import set_tool_context
        from app.agents.developer_v2.src.tools.git_tools import git_create_branch, _git_commit
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        workspace_ready = False
        
        try:
            from git import Repo
            
            set_tool_context(root_dir=str(self.workspace_path))
            
            # Init git if needed
            git_dir = self.workspace_path / ".git"
            if not git_dir.exists():
                repo = Repo.init(str(self.workspace_path))
                logger.info(f"[{self.name}] Git init: {self.workspace_path}")
            else:
                repo = Repo(str(self.workspace_path))
            
            # Initial commit if needed
            if repo.untracked_files or repo.is_dirty():
                result = _git_commit("Initial boilerplate", ".")
                logger.info(f"[{self.name}] Initial commit: {result}")
            
            # Create and checkout branch
            result = git_create_branch.invoke({"branch_name": branch_name})
            logger.info(f"[{self.name}] Branch '{branch_name}': {result}")
            
            workspace_ready = True
            
        except ImportError:
            logger.warning(f"[{self.name}] GitPython not installed")
        except Exception as e:
            logger.warning(f"[{self.name}] Git setup failed: {e}")
        
        return {
            "workspace_path": str(self.workspace_path),
            "branch_name": branch_name,
            "main_workspace": str(self.workspace_path),
            "workspace_ready": workspace_ready,
        }
    
    async def message_user(self, msg_type: str, message: str):
        """No-op for local runner."""
        pass
    
    def _get_project_config(self) -> dict:
        """Get project config for run_code node."""
        return { "tech_stack": {
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
                            "install_cmd": "pnpm install --ignore-scripts ",
                            "test_cmd": "pnpm run test",
                            "run_cmd": "pnpm dev",
                            "build_cmd": "pnpm run build",
                            "lint_cmd": "pnpm run lint",
                            "lint_fix_cmd": "pnpm eslint --fix . --ext .ts,.tsx,.js,.jsx",
                            "format_cmd": "pnpm prettier --write .",
                            "needs_db": True,
                            "db_cmds": ["pnpm prisma generate", "pnpm prisma db push --accept-data-loss"],
                        }
                    ]
                }
        
        }
        
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        langfuse_handler = None
        langfuse_client = None
        
        if os.getenv("ENABLE_LANGFUSE", "false").lower() == "true":
            try:
                from langfuse import Langfuse
                from langfuse.langchain import CallbackHandler
                
                # Simple setup - no context manager (doesn't propagate to async tasks)
                langfuse_client = Langfuse()
                langfuse_handler = CallbackHandler()
                
                logger.info(f"[{self.name}] Langfuse tracing enabled")
            except Exception as e:
                logger.warning(f"[{self.name}] Langfuse setup failed: {e}")
        
        # Reuse workspace from previous story if available
        workspace_to_use = self.active_workspace or str(self.workspace_path)
        is_reusing = bool(self.active_workspace)
        
        if is_reusing:
            logger.info(f"[{self.name}] Reusing workspace: {workspace_to_use}")
        
        initial_state = {
            "story_id": story.get("story_id", str(uuid4())),
            "epic": story.get("epic", ""),
            "story_title": story.get("title", story.get("story_title", "Untitled")),
            "story_description": story.get("description", story.get("story_description", "")),
            "story_requirements": story.get("requirements", story.get("story_requirements", [])),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": self.project_id,
            "task_id": str(uuid4()),
            "user_id": str(uuid4()),
            "langfuse_handler": langfuse_handler,
            "langfuse_client": langfuse_client,  # Pass client for flushing
            
            # Workspace - reuse if available, else let graph setup
            "workspace_path": workspace_to_use,
            "branch_name": "",
            "main_workspace": str(self.workspace_path),
            "workspace_ready": is_reusing,  # Skip setup if reusing
            "index_ready": False,
            "merged": False,
            
            # Workflow state
            "action": None,
            "task_type": None,
            "complexity": None,
            "analysis_result": None,
            "implementation_plan": [],
            "current_step": 0,
            "total_steps": 0,
            "files_created": [],
            "files_modified": [],
            "affected_files": [],
            "message": None,
            "error": None,
            
            # Design
            "logic_analysis": [],
            "dependencies_content": {},
            
            # Run/test state
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "run_status": None,
            
            # Debug state
            "debug_count": 0,
            "max_debug": 5,
            "debug_history": [],
            "error_analysis": None,
            
            # React mode
            "react_mode": True,
            "react_loop_count": 0,
            "max_react_loop": 40,
            
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
            "project_config": self._get_project_config(),
        }
        
        logger.info(f"[{self.name}] Starting story: {story.get('story_title', story.get('title', 'Untitled'))}")
        
        try:
            # Build config with callbacks for Langfuse
            invoke_config = {"recursion_limit": 100}
            if langfuse_handler:
                invoke_config["callbacks"] = [langfuse_handler]
            
            result = await self.graph.graph.ainvoke(
                initial_state,
                config=invoke_config
            )
            
            # Save workspace for reuse in subsequent stories
            if result.get("workspace_path"):
                self.active_workspace = result["workspace_path"]
                logger.info(f"[{self.name}] Saved workspace for reuse: {self.active_workspace}")
            
            # Flush Langfuse on success
            if langfuse_client:
                try:
                    langfuse_client.flush()
                    logger.info(f"[{self.name}] Langfuse flushed")
                except Exception as e:
                    logger.error(f"Langfuse flush error: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph error: {e}", exc_info=True)
            if langfuse_client:
                try:
                    langfuse_client.flush()
                    logger.info(f"[{self.name}] Langfuse flushed (on error)")
                except Exception as cleanup_err:
                    logger.error(f"Langfuse cleanup error: {cleanup_err}")
            raise


# Story definitions
STORY_1 = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "story_title": "As a first-time visitor, I want to see featured books and categories on the homepage so that I can quickly discover interesting books without searching",
    "story_description": """The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories.""",
    "story_requirements": [
        "Display hero section with 3-5 featured books rotating every 5 seconds",
        "Show 'Bestsellers' section with top 10 books based on sales data",
        "Display 'New Arrivals' section with latest 8 books added to catalog",
        "Present main book categories (Fiction, Non-Fiction, Children, Academic, etc.) with representative cover images",
        "Include promotional banner area for special offers or campaigns",
        "Ensure all book cards display: cover image, title, author, price, and rating",
        "Implement lazy loading for images to optimize page load time under 2 seconds"
    ],
    "acceptance_criteria": [
        "Given I am a visitor on the homepage, When the page loads, Then I see hero section with featured books, bestsellers section, new arrivals section, and category navigation within 2 seconds",
        "Given I am viewing the homepage, When I see a book card, Then it displays cover image, title, author name, current price, and average rating (if available)",
        "Given I am on the homepage, When I click on a book card, Then I am navigated to that book's detail page",
        "Given I am on the homepage, When I click on a category tile, Then I am navigated to the category page showing all books in that category",
        "Given the homepage has loaded, When I wait 5 seconds, Then the hero section automatically transitions to the next featured book",
        "Given I am a non-logged user, When I view 'Recommended for You' section, Then I see 6 randomly selected popular books from various categories"
    ],
}

STORY_2 = {
    "story_id": "EPIC-001-US-002",
    "epic": "EPIC-001",
    "story_title": "As a visitor, I want to search for books by title, author, or keyword so that I can quickly find specific books I'm interested in",
    "story_description": """The search functionality enables visitors to find books by title, author, or keyword with autocomplete suggestions.""",
    "story_requirements": [
        "Display search bar prominently in the header, visible on all pages",
        "Implement autocomplete that shows suggestions after user types 2+ characters",
        "Search across book titles, author names, and ISBN numbers",
        "Show up to 8 autocomplete suggestions with book cover thumbnail, title, and author",
        "Display 'No results found' message when search yields no matches",
        "Highlight matching text in autocomplete suggestions",
        "Return search results within 1 second for optimal user experience",
        "Preserve search query in the search bar after navigating to results page"
    ],
    "acceptance_criteria": [
        "Given I am on any page, When I type 2 or more characters in the search bar, Then I see up to 8 autocomplete suggestions within 1 second",
        "Given I see autocomplete suggestions, When I click on a suggestion, Then I am navigated to that book's detail page",
        "Given I have typed a search query, When I press Enter or click the search button, Then I am navigated to the search results page showing all matching books",
        "Given I search for a term with no matches, When the search completes, Then I see a 'No results found' message with suggestions to try different keywords",
        "Given I am viewing autocomplete suggestions, When I use arrow keys to navigate suggestions, Then the selected suggestion is highlighted and I can press Enter to select it",
        "Given I have performed a search, When I view the results page, Then my search query remains visible in the search bar for easy modification"
    ],
}


def print_result(result: dict, workspace_path: Path):
    """Print story execution result."""
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Action: {result.get('action')}")
    print(f"Task Type: {result.get('task_type')}")
    print(f"Steps: {result.get('total_steps', 0)}")
    print(f"Files Modified: {len(result.get('files_modified', []))}")
    print(f"Run Status: {result.get('run_status', 'N/A')}")
    print(f"Debug Count: {result.get('debug_count', 0)}")
    print(f"Workspace: {workspace_path}")


async def test_story(story: dict, workspace_name: str = None) -> dict:
    """Run a single story test."""
    if workspace_name is None:
        workspace_name = f"test_{story['story_id'].lower().replace('-', '_')}"
    
    workspace_path = PROJECTS_DIR / workspace_name
    
    # Cleanup if exists
    if workspace_path.exists():
        shutil.rmtree(workspace_path, ignore_errors=True)
    
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'=' * 60}")
    print(f"Testing: {story['story_title']}")
    print(f"Workspace: {workspace_path}")
    print(f"{'=' * 60}\n")
    
    runner = SimpleDeveloperRunner(str(workspace_path), template="nextjs")
    
    start_time = datetime.now()
    
    try:
        result = await runner.run_story(story)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print_result(result, workspace_path)
        print(f"Time: {elapsed:.1f}s")
        
        return {
            "story_id": story["story_id"],
            "success": result.get("error") is None,
            "elapsed": elapsed,
            "result": result,
        }
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "story_id": story["story_id"],
            "success": False,
            "elapsed": elapsed,
            "error": str(e),
        }


async def test_two_stories_sequential():
    """Test running 2 stories sequentially in same workspace."""
    print("\n" + "=" * 70)
    print("Developer V2 - Two Stories Sequential Test (Zero-Shot + Parallel)")
    print("=" * 70)
    
    workspace_name = _timestamp_workspace("two_stories")
    workspace_path = PROJECTS_DIR / workspace_name
    
    # Cleanup if exists
    if workspace_path.exists():
        shutil.rmtree(workspace_path, ignore_errors=True)
    
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    runner = SimpleDeveloperRunner(str(workspace_path), template="nextjs")
    
    results = []
    total_start = datetime.now()
    
    # ========== STORY 1 ==========
    print(f"\n{'=' * 70}")
    print(f"STORY 1: {STORY_1['story_title'][:60]}...")
    print(f"{'=' * 70}")
    
    s1_start = datetime.now()
    try:
        result1 = await runner.run_story(STORY_1)
        s1_elapsed = (datetime.now() - s1_start).total_seconds()
        
        # Detailed timing from result
        s1_steps = result1.get('total_steps', 0)
        s1_files = len(result1.get('files_modified', []))
        s1_status = result1.get('run_status', 'N/A')
        s1_debug = result1.get('debug_count', 0)
        
        print(f"\n[STORY 1 RESULT]")
        print(f"  Time: {s1_elapsed:.1f}s")
        print(f"  Steps: {s1_steps}")
        print(f"  Files: {s1_files}")
        print(f"  Status: {s1_status}")
        print(f"  Debug: {s1_debug}")
        
        results.append({
            "story_id": STORY_1["story_id"],
            "success": s1_status == "PASS",
            "elapsed": s1_elapsed,
            "steps": s1_steps,
            "files": s1_files,
            "status": s1_status,
            "debug": s1_debug,
        })
    except Exception as e:
        s1_elapsed = (datetime.now() - s1_start).total_seconds()
        print(f"\n[STORY 1 FAILED] {e}")
        results.append({"story_id": STORY_1["story_id"], "success": False, "elapsed": s1_elapsed, "error": str(e)})
    
    # ========== STORY 2 ==========
    print(f"\n{'=' * 70}")
    print(f"STORY 2: {STORY_2['story_title'][:60]}...")
    print(f"{'=' * 70}")
    
    s2_start = datetime.now()
    try:
        result2 = await runner.run_story(STORY_2)
        s2_elapsed = (datetime.now() - s2_start).total_seconds()
        
        s2_steps = result2.get('total_steps', 0)
        s2_files = len(result2.get('files_modified', []))
        s2_status = result2.get('run_status', 'N/A')
        s2_debug = result2.get('debug_count', 0)
        
        print(f"\n[STORY 2 RESULT]")
        print(f"  Time: {s2_elapsed:.1f}s")
        print(f"  Steps: {s2_steps}")
        print(f"  Files: {s2_files}")
        print(f"  Status: {s2_status}")
        print(f"  Debug: {s2_debug}")
        
        results.append({
            "story_id": STORY_2["story_id"],
            "success": s2_status == "PASS",
            "elapsed": s2_elapsed,
            "steps": s2_steps,
            "files": s2_files,
            "status": s2_status,
            "debug": s2_debug,
        })
    except Exception as e:
        s2_elapsed = (datetime.now() - s2_start).total_seconds()
        print(f"\n[STORY 2 FAILED] {e}")
        results.append({"story_id": STORY_2["story_id"], "success": False, "elapsed": s2_elapsed, "error": str(e)})
    
    total_elapsed = (datetime.now() - total_start).total_seconds()
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"{'Story':<20} {'Time':>8} {'Steps':>6} {'Files':>6} {'Status':>8} {'Debug':>6}")
    print("-" * 70)
    for r in results:
        sid = r['story_id'].split('-')[-1] if '-' in r.get('story_id', '') else r.get('story_id', '')
        status = r.get('status', 'FAIL' if not r['success'] else 'N/A')
        print(f"{sid:<20} {r.get('elapsed', 0):>7.1f}s {r.get('steps', 0):>6} {r.get('files', 0):>6} {status:>8} {r.get('debug', 0):>6}")
    print("-" * 70)
    print(f"{'TOTAL':<20} {total_elapsed:>7.1f}s")
    print(f"\nWorkspace: {workspace_path}")
    print(f"All Pass: {all(r['success'] for r in results)}")
    
    return results


def _timestamp_workspace(prefix: str = "test") -> str:
    """Generate timestamp-based workspace name."""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


async def test_story_1_only():
    """Quick test with Story 1 only."""
    return await test_story(STORY_1, workspace_name=_timestamp_workspace("story1"))


async def test_story_on_existing(story: dict, existing_workspace: str) -> dict:
    """Run story on an existing workspace (for sequential story testing)."""
    workspace_path = PROJECTS_DIR / existing_workspace
    
    if not workspace_path.exists():
        print(f"ERROR: Workspace not found: {workspace_path}")
        return {"story_id": story["story_id"], "success": False, "error": "Workspace not found"}
    
    print(f"\n{'=' * 60}")
    print(f"Testing: {story['story_title']}")
    print(f"Workspace (existing): {workspace_path}")
    print(f"{'=' * 60}\n")
    
    runner = SimpleDeveloperRunner(str(workspace_path), template="nextjs")
    
    start_time = datetime.now()
    
    try:
        result = await runner.run_story(story)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print_result(result, workspace_path)
        print(f"Time: {elapsed:.1f}s")
        
        return {
            "story_id": story["story_id"],
            "success": result.get("error") is None,
            "elapsed": elapsed,
            "result": result,
        }
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "story_id": story["story_id"],
            "success": False,
            "elapsed": elapsed,
            "error": str(e),
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Developer V2")
    parser.add_argument("--story1", action="store_true", help="Run only Story 1")
    parser.add_argument("--story2", action="store_true", help="Run only Story 2 (new workspace)")
    parser.add_argument("--story2-on", type=str, metavar="WORKSPACE", help="Run Story 2 on existing workspace (e.g. story1_20251208_232145)")
    parser.add_argument("--both", action="store_true", help="Run both stories (default)")
    args = parser.parse_args()
    
    if args.story1:
        result = asyncio.run(test_story_1_only())
        success = result.get("success", False)
    elif args.story2:
        result = asyncio.run(test_story(STORY_2, workspace_name=_timestamp_workspace("story2")))
        success = result.get("success", False)
    elif args.story2_on:
        result = asyncio.run(test_story_on_existing(STORY_2, args.story2_on))
        success = result.get("success", False)
    else:
        results = asyncio.run(test_two_stories_sequential())
        success = all(r["success"] for r in results) if results else False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
