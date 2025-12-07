"""Test Developer V2 Full Workflow with Detailed Logging.

Usage: cd backend && uv run python tests/test_dev_v2_full.py
"""

# Load environment variables FIRST
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

import asyncio
import logging
import time
from datetime import datetime
from uuid import uuid4

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("test_dev_v2_full")

# Enable all developer_v2 logs
for log_name in [
    "app.agents.developer_v2",
    "app.agents.developer_v2.src.nodes",
    "app.agents.developer_v2.src.nodes.implement",
    "app.agents.developer_v2.src.nodes.analyze_and_plan",
    "app.agents.developer_v2.src.nodes.review",
    "app.agents.developer_v2.src.tools",
]:
    logging.getLogger(log_name).setLevel(logging.INFO)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

# Import from run_dev_v2_real
from run_dev_v2_real import (
    HOMEPAGE_STORY,
    TEXTBOOK_SEARCH_STORY,
    LOGIN_FORM_STORY,
    SIMPLE_CALCULATOR_STORY,
    copy_boilerplate,
    detect_template_type,
)

from app.agents.developer_v2.src.graph import DeveloperGraph
from app.agents.developer_v2.src.utils.db_container import (
    start_postgres_container, 
    stop_postgres_container, 
    update_env_file
)


# =============================================================================
# STORIES
# =============================================================================

STORIES = [
    ("Homepage with Featured Books", HOMEPAGE_STORY),
    ("Textbook Search", TEXTBOOK_SEARCH_STORY),
    ("Login Form", LOGIN_FORM_STORY),
    ("Simple Calculator (Python)", SIMPLE_CALCULATOR_STORY),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    def __init__(self):
        self.project_id = str(uuid4())[:8]
        self.workspace_path = None
        self.graph = None
        self.start_time = None
        self.timings = {}
        
    def setup_workspace(self, story: dict) -> Path:
        """Setup workspace with boilerplate."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in story["title"][:20])
        
        projects_dir = backend_path / "projects"
        projects_dir.mkdir(exist_ok=True)
        
        workspace_path = projects_dir / f"{safe_title}_{timestamp}"
        
        template_type = detect_template_type(story)
        logger.info(f"Template: {template_type}")
        logger.info(f"Workspace: {workspace_path}")
        
        t0 = time.time()
        copy_boilerplate(template_type, workspace_path)
        self.timings["copy_boilerplate"] = time.time() - t0
        
        return workspace_path
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph with detailed logging."""
        self.start_time = time.time()
        
        print("\n" + "="*60)
        print(f"STORY: {story['title']}")
        print("="*60 + "\n")
        
        # Setup workspace
        self.workspace_path = self.setup_workspace(story)
        
        # Start database container
        logger.info("Starting PostgreSQL container...")
        t0 = time.time()
        db_info = start_postgres_container()
        self.timings["db_start"] = time.time() - t0
        logger.info(f"Database ready in {self.timings['db_start']:.2f}s at port {db_info.get('port')}")
        
        # Update .env with DATABASE_URL
        if db_info:
            update_env_file(str(self.workspace_path))
        
        # Run bun install
        logger.info("Running bun install...")
        t0 = time.time()
        import subprocess
        result = subprocess.run(
            "bun install --ignore-scripts",
            cwd=str(self.workspace_path),
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        self.timings["bun_install"] = time.time() - t0
        logger.info(f"bun install: {self.timings['bun_install']:.2f}s (exit: {result.returncode})")
        
        # Run prisma generate
        logger.info("Running prisma generate...")
        t0 = time.time()
        result = subprocess.run(
            "bunx prisma generate",
            cwd=str(self.workspace_path),
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        self.timings["prisma_generate"] = time.time() - t0
        logger.info(f"prisma generate: {self.timings['prisma_generate']:.2f}s")
        
        # Initialize graph
        logger.info("Initializing DeveloperGraph...")
        self.graph = DeveloperGraph()
        
        # Build initial state
        initial_state = {
            "story_id": story.get("story_id", str(uuid4())),
            "epic": story.get("epic", ""),
            "story_title": story.get("title", "Untitled"),
            "story_description": story.get("description", ""),
            "story_requirements": story.get("requirements", []),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": self.project_id,
            "task_id": str(uuid4()),
            "user_id": str(uuid4()),
            "langfuse_handler": None,
            "langfuse_client": None,
            "workspace_path": str(self.workspace_path),
            "branch_name": "",
            "main_workspace": str(self.workspace_path),
            "workspace_ready": False,
            "index_ready": False,
            "merged": False,
            "action": None,
            "task_type": None,
            "complexity": None,
            "analysis_result": None,
            "affected_files": [],
            "dependencies": [],
            "risks": [],
            "estimated_hours": 0.0,
            "implementation_plan": [],
            "current_step": 0,
            "total_steps": 0,
            "logic_analysis": [],
            "dependencies_content": {},
            "files_modified": [],
            "files_created": [],
            "error": None,
            "review_feedback": None,
            "review_count": 0,
            "run_status": None,
            "run_stderr": None,
            "run_stdout": None,
            "summarize_feedback": None,
            "error_analysis": None,
            "debug_count": 0,
            "skill_registry": None,
            "react_mode": True,
            "react_loop_count": 0,
            "tech_stack": "nextjs",  # String, not dict
            "project_config": {
                "tech_stack": {
                    "name": "nextjs",
                    "runtime": "bun",
                    "framework": "nextjs",
                    "orm": "prisma",
                    "service": ["app"],
                },
                "install_cmd": "bun install --ignore-scripts",
                "build_cmd": "bun run build",
                "typecheck_cmd": "bun run typecheck",
                "test_cmd": "bun run test",
                "run_cmd": "bun dev",
            },
        }
        
        print("\n" + "-"*60)
        print("[*] Running graph... (this may take several minutes)")
        print("-"*60 + "\n")
        
        try:
            # Run graph
            t0 = time.time()
            final_state = await self.graph.graph.ainvoke(
                initial_state,
                config={"recursion_limit": 100}
            )
            self.timings["graph"] = time.time() - t0
            
            self.timings["total"] = time.time() - self.start_time
            
            return final_state
            
        except Exception as e:
            logger.error(f"Graph error: {e}", exc_info=True)
            self.timings["total"] = time.time() - self.start_time
            raise
    
    def print_summary(self, result: dict):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        print(f"\nStatus: {result.get('action', 'UNKNOWN')}")
        print(f"Steps: {result.get('current_step', 0)}/{result.get('total_steps', 0)}")
        
        files = result.get('files_modified', [])
        print(f"Files modified: {len(files)}")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        
        if result.get('error'):
            print(f"\nError: {result.get('error')}")
        
        print(f"\nWorkspace: {self.workspace_path}")
        
        print("\n" + "-"*40)
        print("TIMING BREAKDOWN")
        print("-"*40)
        for key, value in self.timings.items():
            print(f"  {key}: {value:.2f}s")
        
    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
        stop_postgres_container()


def select_story(choice: int = None) -> dict:
    """Story selection. If choice is None, try interactive or use default."""
    print("\nAvailable stories:")
    for i, (name, _) in enumerate(STORIES, 1):
        default = " [DEFAULT]" if i == 1 else ""
        print(f"  {i}. {name}{default}")
    
    # If choice provided via argument
    if choice is not None:
        idx = choice - 1
        if 0 <= idx < len(STORIES):
            return STORIES[idx][1]
    
    # Try interactive input
    try:
        if sys.stdin.isatty():
            user_input = input(f"\nEnter choice (1-{len(STORIES)}) [default=1]: ").strip()
            if user_input:
                idx = int(user_input) - 1
                if 0 <= idx < len(STORIES):
                    return STORIES[idx][1]
    except (EOFError, ValueError, IndexError):
        pass
    
    print("\nUsing default: Homepage with Featured Books")
    return STORIES[0][1]


async def main():
    """Main test function."""
    print("="*60)
    print("Developer V2 Full Workflow Test")
    print("="*60)
    
    # Check for command line argument
    story_choice = None
    if len(sys.argv) > 1:
        try:
            story_choice = int(sys.argv[1])
        except ValueError:
            pass
    
    story = select_story(story_choice)
    print(f"\nSelected: {story['title']}")
    
    runner = TestRunner()
    
    try:
        result = await runner.run_story(story)
        runner.print_summary(result)
        
        if result.get('error'):
            return 1
        return 0
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        return 1
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    finally:
        runner.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
