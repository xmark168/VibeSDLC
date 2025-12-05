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
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

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
        
        # Import and init graph
        from app.agents.developer_v2.src.graph import DeveloperGraph
        self.graph = DeveloperGraph(agent=self)
        
        logger.info(f"[{self.name}] Workspace: {self.workspace_path}")
    
    def _setup_workspace(self, story_id: str) -> dict:
        """Setup git workspace and branch - called by graph's setup_workspace node."""
        from app.agents.developer_v2.src.tools.git_tools import set_git_context, git_create_branch, _git_commit
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        workspace_ready = False
        
        try:
            from git import Repo
            
            set_git_context(str(self.workspace_path))
            
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
        return {
            "tech_stack": {
                "name": "nextjs-app",
                "service": [{
                    "name": "app",
                    "path": ".",
                    "runtime": "bun",
                    "framework": "nextjs",
                    "orm": "prisma",
                    "install_cmd": "bun install",
                    "build_cmd": "bun run build",
                    "typecheck_cmd": "bun run typecheck",
                    "test_cmd": "bun run test",
                    "lint_cmd": "bun run lint",
                    "lint_fix_cmd": "bunx eslint --fix . --ext .ts,.tsx,.js,.jsx",
                    "format_cmd": "bunx prettier --write .",
                    "needs_db": True,
                    "db_cmds": ["bunx prisma generate", "bunx prisma db push --accept-data-loss"],
                }]
            }
        }
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        # Setup Langfuse if enabled
        langfuse_handler = None
        if os.getenv("ENABLE_LANGFUSE", "false").lower() == "true":
            try:
                from langfuse.langchain import CallbackHandler
                langfuse_handler = CallbackHandler()
            except Exception:
                pass
        
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
        
        result = await self.graph.graph.ainvoke(
            initial_state,
            config={"recursion_limit": 100}
        )
        
        # Save workspace for reuse in subsequent stories
        if result.get("workspace_path"):
            self.active_workspace = result["workspace_path"]
            logger.info(f"[{self.name}] Saved workspace for reuse: {self.active_workspace}")
        
        return result


# Story definitions
STORY_1 = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "story_title": "Homepage with featured books and categories",
    "story_description": """The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories.""",
    "story_requirements": [
        "Display hero section with featured books carousel",
        "Show 'Bestsellers' section with top books",
        "Display 'New Arrivals' section with latest books",
        "Present main book categories with cover images",
        "All book cards display: cover image, title, author, price",
        "Implement lazy loading for images",
    ],
    "acceptance_criteria": [
        "Given I am on the homepage, When the page loads, Then I see hero section, bestsellers, new arrivals within 2 seconds",
        "Given I see a book card, Then it displays cover image, title, author name, price",
        "Given I click on a book card, Then I am navigated to that book's detail page",
    ],
}

STORY_2 = {
    "story_id": "EPIC-001-US-002",
    "epic": "EPIC-001",
    "story_title": "Search books by title, author, or keyword",
    "story_description": """The search functionality enables visitors to find books by title, author, or keyword with autocomplete suggestions.""",
    "story_requirements": [
        "Display search bar prominently in the header",
        "Implement autocomplete after 2+ characters",
        "Search across book titles, author names, ISBN",
        "Show up to 8 suggestions with thumbnail, title, author",
        "Display 'No results found' message when appropriate",
    ],
    "acceptance_criteria": [
        "Given I type 2+ characters, Then I see up to 8 autocomplete suggestions within 1 second",
        "Given I click on a suggestion, Then I navigate to that book's detail page",
        "Given no matches, Then I see 'No results found' message",
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
    print("Developer V2 - Two Stories Sequential Test")
    print("=" * 70)
    
    workspace_name = "test_two_stories"
    workspace_path = PROJECTS_DIR / workspace_name
    
    # Cleanup
    if workspace_path.exists():
        shutil.rmtree(workspace_path, ignore_errors=True)
    
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    runner = SimpleDeveloperRunner(str(workspace_path), template="nextjs")
    
    results = []
    total_start = datetime.now()
    
    # Story 1
    print(f"\n[STORY 1] {STORY_1['story_title']}")
    start = datetime.now()
    try:
        result1 = await runner.run_story(STORY_1)
        elapsed = (datetime.now() - start).total_seconds()
        results.append({"story_id": STORY_1["story_id"], "success": True, "elapsed": elapsed})
        print(f"[DONE] Story 1 in {elapsed:.1f}s - Status: {result1.get('run_status')}")
    except Exception as e:
        results.append({"story_id": STORY_1["story_id"], "success": False, "error": str(e)})
        print(f"[FAIL] Story 1: {e}")
    
    # Story 2
    print(f"\n[STORY 2] {STORY_2['story_title']}")
    start = datetime.now()
    try:
        result2 = await runner.run_story(STORY_2)
        elapsed = (datetime.now() - start).total_seconds()
        results.append({"story_id": STORY_2["story_id"], "success": True, "elapsed": elapsed})
        print(f"[DONE] Story 2 in {elapsed:.1f}s - Status: {result2.get('run_status')}")
    except Exception as e:
        results.append({"story_id": STORY_2["story_id"], "success": False, "error": str(e)})
        print(f"[FAIL] Story 2: {e}")
    
    total_elapsed = (datetime.now() - total_start).total_seconds()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"[{status}] {r['story_id']} - {r.get('elapsed', 0):.1f}s")
    print(f"\nTotal: {total_elapsed:.1f}s")
    print(f"Workspace: {workspace_path}")
    
    return results


async def test_story_1_only():
    """Quick test with Story 1 only."""
    return await test_story(STORY_1, workspace_name="test_story1")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Developer V2")
    parser.add_argument("--story1", action="store_true", help="Run only Story 1")
    parser.add_argument("--story2", action="store_true", help="Run only Story 2")
    parser.add_argument("--both", action="store_true", help="Run both stories (default)")
    args = parser.parse_args()
    
    if args.story1:
        result = asyncio.run(test_story_1_only())
        success = result.get("success", False)
    elif args.story2:
        result = asyncio.run(test_story(STORY_2, workspace_name="test_story2"))
        success = result.get("success", False)
    else:
        results = asyncio.run(test_two_stories_sequential())
        success = all(r["success"] for r in results) if results else False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
