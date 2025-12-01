"""Run Developer V2 with a real task - no mocking.

This script sends a real task to DeveloperV2 and lets it process
with actual LLM calls.

Features:
- Interactive mode: After each run, waits for more commands
- Container persistence: Reuses containers between runs
- Graceful cleanup: Ctrl+C cleans up containers before exit

Usage:
    cd backend
    python run_dev_v2_real.py

Commands (after first run):
    run     - Run another story
    test    - Run tests in container
    exec    - Execute command in container
    logs    - Show container logs
    status  - Show container status
    clear   - Remove containers and exit
    exit    - Stop containers and exit (can resume later)
"""

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import asyncio
import atexit
import json
import logging
import signal
import sys
import os
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Setup logging - prevent duplicates
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Reset existing handlers
)
logger = logging.getLogger(__name__)
logger.propagate = False  # Prevent duplicate logs

# Create single handler
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3", "git"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Enable developer_v2 logs (show node progress)
dev_logger = logging.getLogger("app.agents.developer_v2")
dev_logger.setLevel(logging.INFO)
dev_logger.propagate = True  # Ensure logs propagate to root

# Set root logger to show all INFO
logging.getLogger().setLevel(logging.INFO)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.developer_v2.src.graph import DeveloperGraph
from app.agents.developer_v2.src.state import DeveloperState


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES_DIR = Path(__file__).parent / "app" / "agents" / "templates" / "boilerplate"

AVAILABLE_TEMPLATES = {
    "nextjs": "nextjs-boilerplate",
    "react": "nextjs-boilerplate",  # Use NextJS for React projects too
    "python": None,  # No boilerplate, start from scratch
}


def copy_boilerplate(template_name: str, target_path: Path) -> bool:
    """Copy boilerplate template to target workspace.
    
    Args:
        template_name: Name of template (nextjs, react, python)
        target_path: Destination workspace path
        
    Returns:
        True if copied successfully, False otherwise
    """
    template_dir = AVAILABLE_TEMPLATES.get(template_name.lower())
    
    if not template_dir:
        logger.info(f"No boilerplate for '{template_name}', starting with empty workspace")
        target_path.mkdir(parents=True, exist_ok=True)
        return False
    
    source_path = TEMPLATES_DIR / template_dir
    
    if not source_path.exists():
        logger.warning(f"Template not found: {source_path}")
        target_path.mkdir(parents=True, exist_ok=True)
        return False
    
    # Directories to ignore when copying
    IGNORE_DIRS = {'node_modules', '.next', '__pycache__', '.bun'}
    
    def ignore_patterns(directory, files):
        """Return list of files/dirs to ignore."""
        return [f for f in files if f in IGNORE_DIRS]
    
    try:
        # Copy entire template directory (excluding node_modules, .git, etc.)
        if target_path.exists():
            shutil.rmtree(target_path)
        
        shutil.copytree(source_path, target_path, ignore=ignore_patterns)
        logger.info(f"Copied boilerplate '{template_dir}' to {target_path}")
        
        # Count files copied
        file_count = sum(1 for _ in target_path.rglob("*") if _.is_file())
        logger.info(f"Copied {file_count} files from template")
        
        return True
    except Exception as e:
        logger.error(f"Failed to copy boilerplate: {e}")
        target_path.mkdir(parents=True, exist_ok=True)
        return False


def detect_template_type(story: dict) -> str:
    """Detect which template to use based on story content.
    
    Args:
        story: Story dictionary with title and content
        
    Returns:
        Template type: 'nextjs', 'react', or 'python'
    """
    title = story.get("title", "").lower()
    content = story.get("content", "").lower()
    combined = f"{title} {content}"
    
    # Check for React/NextJS indicators
    react_keywords = ["react", "nextjs", "next.js", "tsx", "jsx", "component", "tailwind", "website"]
    if any(kw in combined for kw in react_keywords):
        return "nextjs"
    
    # Check for Python indicators
    python_keywords = ["python", ".py", "pytest", "unittest", "django", "fastapi", "flask"]
    if any(kw in combined for kw in python_keywords):
        return "python"
    
    # Default to NextJS for web projects
    return "nextjs"


class SimpleDeveloperRunner:
    """Simple runner for DeveloperV2 without full agent infrastructure.
    
    This runner provides the `_setup_workspace` method that the graph's
    `setup_workspace` node expects. It handles:
    - Git init and branch creation
    - CocoIndex indexing for semantic search
    
    Note: message_user calls in nodes.py are disabled for this mode.
    """
    
    def __init__(self, workspace_path: str = None, template: str = None):
        self.name = "DeveloperV2"
        self.role_type = "developer"
        self.project_id = str(uuid4())
        self.template = template
        self.template_applied = False
        
        # Create workspace if not provided
        if workspace_path:
            self.workspace_path = Path(workspace_path)
        else:
            self.workspace_path = Path(__file__).parent / "projects" / f"project_{self.project_id}"
        
        # Apply boilerplate template if specified (workspace_ready stays False)
        if template:
            self.template_applied = copy_boilerplate(template, self.workspace_path)
            if self.template_applied:
                logger.info(f"[{self.name}] Applied '{template}' boilerplate template")
        else:
            self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize graph (agent=self, setup_workspace node will call _setup_workspace)
        self.graph = DeveloperGraph(agent=self)
        
        logger.info(f"[{self.name}] Initialized with workspace: {self.workspace_path}")
        logger.info(f"[{self.name}] Workspace ready: False (will be setup by graph)")
    
    def _setup_workspace(self, story_id: str) -> dict:
        """Setup workspace for the graph's setup_workspace node.
        
        This method is called by the setup_workspace node in graph.py.
        It handles:
        1. Git init (if not already)
        2. Create and checkout feature branch
        3. Initial commit of boilerplate (if any)
        
        Args:
            story_id: Story ID for branch naming
            
        Returns:
            dict with workspace_path, branch_name, main_workspace, workspace_ready
        """
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        
        workspace_ready = False
        
        try:
            from app.agents.developer.tools.git_python_tool import GitPythonTool
            
            git_tool = GitPythonTool(root_dir=str(self.workspace_path))
            
            # 1. Initialize git if needed
            git_dir = self.workspace_path / ".git"
            if not git_dir.exists():
                result = git_tool._run("init")
                logger.info(f"[{self.name}] Git init: {result}")
            
            # 2. Initial commit if there are files (from boilerplate)
            status = git_tool._run("status")
            if "nothing to commit" not in status.lower() and "untracked files" in status.lower():
                # Stage all files
                commit_result = git_tool._run("commit", message="Initial boilerplate", files=["."])
                logger.info(f"[{self.name}] Initial commit: {commit_result}")
            
            # 3. Create and checkout feature branch
            create_result = git_tool._run("create_branch", branch_name=branch_name)
            logger.info(f"[{self.name}] Create branch '{branch_name}': {create_result}")
            
            checkout_result = git_tool._run("checkout_branch", branch_name=branch_name)
            logger.info(f"[{self.name}] Checkout branch '{branch_name}': {checkout_result}")
            
            workspace_ready = True
            logger.info(f"[{self.name}] Workspace setup complete: branch={branch_name}")
            
        except Exception as e:
            logger.warning(f"[{self.name}] Git setup failed: {e}")
            workspace_ready = False
        
        return {
            "workspace_path": str(self.workspace_path),
            "branch_name": branch_name,
            "main_workspace": str(self.workspace_path),
            "workspace_ready": workspace_ready,
        }
    
    async def message_user(self, msg_type: str, message: str):
        """No-op - message_user calls in nodes.py are disabled."""
        pass  # Disabled for local runner mode
    
    def _get_project_config(self) -> dict:
        """Get project config based on template type.
        
        Returns:
            tech_stack format: {"name": "project_name", "service": [...]}
            {"tech_stack": {"name": "my-app", "service": [{"name": "app", ...}, ...]}}
        """
        # Default config for NextJS boilerplate (single service)
        if self.template in ["nextjs", "react"]:
            return {
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
            }
        
        # Python projects (single service)
        if self.template == "python":
            return {
                "tech_stack": {
                    "name": "python-app",
                    "service": [
                        {
                            "name": "app",
                            "path": ".",
                            "runtime": "python",
                            "framework": "fastapi",
                            "orm": "sqlalchemy",
                            "db_type": "postgresql",
                            "validation": "pydantic",
                            "install_cmd": "pip install -e .",
                            "test_cmd": "pytest -v",
                            "run_cmd": "uvicorn app.main:app --reload",
                            "build_cmd": "",
                            "lint_cmd": "ruff check .",
                            "lint_fix_cmd": "ruff check --fix .",
                            "format_cmd": "ruff format .",
                            "needs_db": False,
                            "db_cmds": [],
                        }
                    ]
                }
            }
        
        # Fullstack monorepo (multi-service)
        if self.template == "fullstack":
            return {
                "tech_stack": {
                    "name": "fullstack-monorepo",
                    "service": [
                        {
                            "name": "frontend",
                            "path": "frontend",
                            "runtime": "bun",
                            "framework": "nextjs",
                            "validation": "zod",
                            "auth": "next-auth",
                            "install_cmd": "bun install",
                            "test_cmd": "bun run test",
                            "run_cmd": "bun dev",
                            "build_cmd": "bun run build",
                            "lint_cmd": "bun run lint",
                            "lint_fix_cmd": "bunx eslint --fix . --ext .ts,.tsx,.js,.jsx",
                            "format_cmd": "bunx prettier --write .",
                            "needs_db": False,
                            "db_cmds": [],
                        },
                        {
                            "name": "backend",
                            "path": "backend",
                            "runtime": "python",
                            "framework": "fastapi",
                            "orm": "sqlalchemy",
                            "db_type": "postgresql",
                            "validation": "pydantic",
                            "install_cmd": "pip install -e .",
                            "test_cmd": "pytest -v",
                            "run_cmd": "uvicorn app.main:app --reload",
                            "build_cmd": "",
                            "lint_cmd": "ruff check .",
                            "lint_fix_cmd": "ruff check --fix .",
                            "format_cmd": "ruff format .",
                            "needs_db": True,
                            "db_cmds": ["alembic upgrade head"],
                        },
                    ]
                }
            }
        
        # Default: empty service triggers error in nodes.py
        return {"tech_stack": {"name": "", "service": []}}
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        
        # Setup Langfuse tracing (controlled by ENABLE_LANGFUSE env var)
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        enable_langfuse = os.getenv("ENABLE_LANGFUSE", "false").lower() == "true"
        
        if enable_langfuse:
            try:
                from langfuse import get_client
                from langfuse.langchain import CallbackHandler
                
                # Create parent span for entire graph execution (Team Leader pattern)
                langfuse = get_client()
                langfuse_ctx = langfuse.start_as_current_observation(
                    as_type="span",
                    name="developer_v2_story_execution"
                )
                
                # Enter context and get span object
                langfuse_span = langfuse_ctx.__enter__()
                
                # Update trace with metadata
                langfuse_span.update_trace(
                    user_id=str(uuid4()),
                    session_id=str(self.project_id),
                    input={
                        "story_id": story.get("story_id", "unknown"),
                        "title": story.get("title", "Untitled"),
                        "content": story.get("content", "")[:200]
                    },
                    tags=["developer_v2", "story_execution", self.template or "no_template"],
                    metadata={
                        "agent": self.name,
                        "template": self.template,
                        "template_applied": self.template_applied
                    }
                )
                
                # Handler inherits trace context automatically
                langfuse_handler = CallbackHandler()
                
                logger.info(f"[{self.name}] Langfuse tracing enabled (session={self.project_id})")
            except Exception as e:
                logger.error(f"Langfuse setup error: {e}")
        else:
            logger.info(f"[{self.name}] Langfuse disabled (set ENABLE_LANGFUSE=true to enable)")
        
        # Build initial state
        # Note: workspace_path is provided but workspace_ready=False
        # The setup_workspace node will call agent._setup_workspace() to:
        # - Initialize git
        # - Create and checkout feature branch
        # - Index codebase with CocoIndex
        initial_state = {
            "story_id": story.get("story_id", str(uuid4())),
            "story_title": story.get("title", "Untitled"),
            "story_content": story.get("content", ""),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": self.project_id,
            "task_id": str(uuid4()),
            "user_id": str(uuid4()),
            "langfuse_handler": langfuse_handler,
            
            # Workspace - setup_workspace node will handle git/branch/indexing
            "workspace_path": str(self.workspace_path),  # Pre-set path (may have boilerplate)
            "branch_name": None,  # Will be set by setup_workspace node
            "main_workspace": str(self.workspace_path),
            "workspace_ready": False,  # Will be set to True by setup_workspace node
            "index_ready": False,  # Will be set to True after CocoIndex indexing
            "merged": False,
            
            # Workflow state
            "action": None,
            "task_type": None,
            "complexity": None,
            "analysis_result": None,
            "implementation_plan": [],
            "code_changes": [],
            "files_created": [],
            "files_modified": [],
            "affected_files": [],
            "current_step": 0,
            "total_steps": 0,
            "validation_result": None,
            "message": None,
            "confidence": None,
            "reason": None,
            
            # Design document (merged into plan node)
            "design_doc": None,
            
            # Run code - let detect_test_command figure out the right command
            "run_status": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "test_command": None,  # Auto-detect test framework (bun/npm/jest/pytest)
            "error_logs": "",
            
            # Debug
            "debug_count": 0,
            "max_debug": 5,  # Allow 5 debug attempts (MetaGPT pattern)
            "debug_history": [],
            "last_debug_file": None,
            
            # React mode (MetaGPT Engineer2 pattern)
            "react_mode": True,
            "react_loop_count": 0,
            "max_react_loop": 40,
            
            # Project context
            "project_context": None,
            "agents_md": None,
            "related_code_context": "",
            "research_context": "",
            
            # Project config (tech stack, commands)
            "project_config": self._get_project_config(),
        }
        
        logger.info(f"[{self.name}] Starting story: {story.get('title', 'Untitled')}")
        print("\n" + "="*60)
        print(f"STARTING: {story.get('title', 'Untitled')}")
        print("="*60)
        print("\n[*] Running graph... (this may take several minutes)")
        print("[*] Progress will be shown below:\n")
        sys.stdout.flush()
        
        try:
            # Run graph with high recursion limit for multi-step workflows
            final_state = await self.graph.graph.ainvoke(
                initial_state,
                config={"recursion_limit": 100}
            )
            print("\n[*] Graph completed!")
            
            # Update trace output and close span (Team Leader pattern)
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "action": final_state.get("action"),
                        "task_type": final_state.get("task_type"),
                        "complexity": final_state.get("complexity"),
                        "files_created": len(final_state.get("files_created", [])),
                        "files_modified": len(final_state.get("files_modified", [])),
                        "run_status": final_state.get("run_status"),
                        "debug_count": final_state.get("debug_count", 0),
                        "react_loop_count": final_state.get("react_loop_count", 0)
                    })
                    langfuse_ctx.__exit__(None, None, None)
                    logger.info(f"[{self.name}] Langfuse span closed successfully")
                except Exception as e:
                    logger.error(f"Langfuse span close error: {e}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph error: {e}", exc_info=True)
            
            # Cleanup langfuse span on error (Team Leader pattern)
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    logger.info(f"[{self.name}] Langfuse span closed (on error)")
                except Exception as cleanup_err:
                    logger.error(f"Langfuse cleanup error: {cleanup_err}")
            
            raise


# =============================================================================
# STORY DEFINITIONS
# =============================================================================

LEARNING_WEBSITE_STORY = {
    "story_id": "learning-001",
    "title": "Create Learning Website ",
    "content": """
## User Story
As a student, I want a beautiful learning website so that I can browse online courses.

## Requirements
Create a learning website with these components:

1. **Navbar.tsx** - Navigation bar with:
   - Logo (LearnHub)
   - Nav links: Home, Courses, About
   - Login/Register buttons
   - Dark mode toggle

2. **HeroSection.tsx** - Hero section with:
   - Gradient background (blue to purple)
   - Headline: "Learn Programming Online"
   - Subtext: "Join 10,000+ students"
   - CTA button: "Browse Courses"
   - Stats: 500+ courses, 50+ instructors

3. **CourseCard.tsx** - Course card with:
   - Thumbnail image placeholder
   - Course title
   - Instructor name
   - Rating (stars)
   - Price
   - "Enroll" button

4. **HomePage.tsx** - Main page combining:
   - Navbar
   - HeroSection
   - Grid of 3 CourseCards
   - Simple footer

## Tech Stack
- React + TypeScript
- TailwindCSS
- Lucide React icons

## Design
- Primary: #3B82F6 (blue)
- Dark mode support
- Responsive
""",
    "acceptance_criteria": [
        "Navbar with logo and navigation",
        "Hero section with gradient and CTA",
        "Course cards with title, price, rating",
        "Responsive layout",
        "Dark mode toggle works"
    ]
}


SIMPLE_CALCULATOR_STORY = {
    "story_id": "calc-001",
    "title": "Create Simple Calculator",
    "content": """
## User Story
As a user, I want a simple calculator
so that I can perform basic math operations.

## Requirements
Create a Python calculator module with:
1. add(a, b) - Addition
2. subtract(a, b) - Subtraction
3. multiply(a, b) - Multiplication
4. divide(a, b) - Division with zero check

## Acceptance Criteria
- All functions work correctly
- Division by zero returns error message
- Include unit tests
""",
    "acceptance_criteria": [
        "add(2, 3) returns 5",
        "subtract(5, 3) returns 2",
        "multiply(4, 5) returns 20",
        "divide(10, 2) returns 5",
        "divide(10, 0) returns error"
    ]
}


LOGIN_FORM_STORY = {
    "story_id": "login-001",
    "title": "Create Login Form Component",
    "content": """
## User Story
As a user, I want a login form
so that I can authenticate to the application.

## Requirements
Create a React login form with:
1. Email input with validation
2. Password input with show/hide toggle
3. Remember me checkbox
4. Submit button
5. "Forgot password" link

## Tech Stack
- React + TypeScript
- TailwindCSS
- React Hook Form for validation

## Validation Rules
- Email: Required, valid email format
- Password: Required, min 8 characters
""",
    "acceptance_criteria": [
        "Email field validates format",
        "Password field has show/hide toggle",
        "Form shows validation errors",
        "Submit button disabled when invalid",
        "Loading state on submit"
    ]
}


TEXTBOOK_SEARCH_STORY = {
    "story_id": "US-001",
    "title": "Search Textbooks by Name, Author or Code",
    "content": """
## As a customer, I want to search for textbooks by name, author or code so that I can quickly find the book I need

*ID:* US-001  
*Epic:* EPIC-001

### Description
Người dùng có thể sử dụng thanh tìm kiếm để nhập tên sách, tác giả hoặc mã sách và nhận được kết quả phù hợp.
""",
    "acceptance_criteria": [
        "Given I am on the homepage when I enter a book name, author or code in the search bar then I see a list of matching books with basic information",
        "Given no books match my search when I submit the search then I see a message indicating no results found"
    ]
}


# =============================================================================
# GLOBAL STATE FOR CLEANUP
# =============================================================================

_active_branch = None
_active_workspace = None
_should_cleanup = False


def cleanup_containers(remove: bool = False):
    """Cleanup containers on exit."""
    global _active_branch
    
    if not _active_branch:
        return
    
    try:
        from app.agents.developer_v2.src.tools.container_tools import dev_container_manager
        
        if remove:
            print(f"\n[*] Removing containers for {_active_branch}...")
            dev_container_manager.remove(_active_branch)
            print("[*] Containers removed.")
        else:
            print(f"\n[*] Stopping containers for {_active_branch}...")
            dev_container_manager.stop(_active_branch)
            print("[*] Containers stopped (can resume later).")
    except Exception as e:
        logger.debug(f"Cleanup error: {e}")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _should_cleanup
    
    print("\n\n[!] Interrupted! Cleaning up...")
    _should_cleanup = True
    cleanup_containers(remove=True)
    sys.exit(0)


# Register signal handler
signal.signal(signal.SIGINT, signal_handler)


# =============================================================================
# INTERACTIVE COMMANDS
# =============================================================================

def print_help():
    """Print available commands."""
    print("\n" + "-"*40)
    print("COMMANDS:")
    print("  run     - Run another story")
    print("  test    - Run tests in container")
    print("  exec    - Execute command in container")
    print("  logs    - Show container logs")
    print("  status  - Show container status")
    print("  clear   - Remove containers and exit")
    print("  exit    - Stop containers and exit (can resume later)")
    print("  help    - Show this help")
    print("-"*40)


async def handle_command(cmd: str, branch_name: str, workspace_path: Path) -> bool:
    """Handle interactive command.
    
    Returns:
        True to continue, False to exit
    """
    from app.agents.developer_v2.src.tools.container_tools import dev_container_manager
    
    cmd = cmd.strip().lower()
    
    if cmd == "help" or cmd == "?":
        print_help()
        return True
    
    elif cmd == "exit" or cmd == "quit" or cmd == "q":
        cleanup_containers(remove=False)
        return False
    
    elif cmd == "clear":
        cleanup_containers(remove=True)
        return False
    
    elif cmd == "status":
        try:
            status = dev_container_manager.status(branch_name)
            print("\n" + json.dumps(status, indent=2))
        except Exception as e:
            print(f"Error: {e}")
        return True
    
    elif cmd == "logs":
        try:
            logs = dev_container_manager.get_logs(branch_name, tail=50)
            print("\n" + "-"*40)
            print("CONTAINER LOGS (last 50 lines):")
            print("-"*40)
            print(logs)
        except Exception as e:
            print(f"Error: {e}")
        return True
    
    elif cmd == "test":
        try:
            print("\n[*] Running tests in container...")
            # Detect test command
            from app.agents.developer_v2.src.nodes import _detect_project_type
            project_info = _detect_project_type(str(workspace_path))
            test_cmd = project_info.get("test_cmd", "npm test")
            
            print(f"[*] Executing: {test_cmd}")
            result = dev_container_manager.exec(branch_name, test_cmd)
            print("\n" + "-"*40)
            print(f"Exit code: {result.get('exit_code')}")
            print("-"*40)
            print(result.get("output", ""))
        except Exception as e:
            print(f"Error: {e}")
        return True
    
    elif cmd.startswith("exec "):
        try:
            shell_cmd = cmd[5:].strip()
            if not shell_cmd:
                print("Usage: exec <command>")
                return True
            
            print(f"\n[*] Executing: {shell_cmd}")
            result = dev_container_manager.exec(branch_name, shell_cmd)
            print("\n" + "-"*40)
            print(f"Exit code: {result.get('exit_code')}")
            print("-"*40)
            print(result.get("output", ""))
        except Exception as e:
            print(f"Error: {e}")
        return True
    
    elif cmd == "run":
        return "run"  # Special signal to run another story
    
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands")
        return True


def print_result(result: dict, workspace_path: Path):
    """Print story execution result."""
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(f"Action: {result.get('action')}")
    print(f"Task Type: {result.get('task_type')}")
    print(f"Complexity: {result.get('complexity')}")
    print(f"Files Created: {len(result.get('files_created', []))}")
    print(f"Files Modified: {len(result.get('files_modified', []))}")
    print(f"Tests: {result.get('run_status', 'N/A')}")
    print(f"Debug Iterations: {result.get('debug_count', 0)}")
    print(f"React Loops: {result.get('react_loop_count', 0)}")
    
    # Show created files
    files_created = result.get('files_created', [])
    if files_created:
        print("\n" + "-"*40)
        print("FILES CREATED:")
        for f in files_created[:10]:
            print(f"  - {f}")
            file_path = workspace_path / f
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"    ({size} bytes)")
        if len(files_created) > 10:
            print(f"  ... and {len(files_created) - 10} more")
    
    # Show workspace location
    print("\n" + "-"*40)
    print(f"WORKSPACE: {workspace_path}")
    print(f"CONTAINER: {result.get('container_name', 'N/A')}")


def select_story() -> dict:
    """Interactive story selection."""
    print("\nSelect a story to run:")
    print("1. Textbook Search (React) [DEFAULT]")
    print("2. Simple Calculator (Python)")
    print("3. Login Form (React)")
    print("4. Learning Website (React)")
    print("5. Custom story (enter your own)")
    print()
    
    try:
        choice = input("Enter choice (1-5) [default=1]: ").strip() or "1"
    except EOFError:
        choice = "1"
    
    if choice == "1":
        return TEXTBOOK_SEARCH_STORY
    elif choice == "2":
        return SIMPLE_CALCULATOR_STORY
    elif choice == "3":
        return LOGIN_FORM_STORY
    elif choice == "4":
        return LEARNING_WEBSITE_STORY
    elif choice == "5":
        print("\nEnter your story:")
        title = input("Title: ").strip()
        content = input("Description: ").strip()
        return {
            "story_id": str(uuid4())[:8],
            "title": title,
            "content": content,
            "acceptance_criteria": []
        }
    else:
        print("Invalid choice, using Textbook Search")
        return TEXTBOOK_SEARCH_STORY


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point with interactive loop."""
    global _active_branch, _active_workspace
    
    print("\n" + "="*60)
    print("DEVELOPER V2 - INTERACTIVE RUNNER")
    print("="*60)
    print("Press Ctrl+C at any time to cleanup and exit")
    
    # Select first story
    story = select_story()
    
    print(f"\nSelected: {story['title']}")
    print("-"*40)
    
    # Detect template type based on story
    template_type = detect_template_type(story)
    print(f"Template: {template_type}")
    print("-"*40)
    
    # Create workspace name based on story
    story_slug = story.get('title', 'project').lower().replace(' ', '_')[:20]
    workspace_name = f"{story_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    workspace_path = Path(__file__).parent / "projects" / workspace_name
    
    # Create runner with boilerplate template
    runner = SimpleDeveloperRunner(workspace_path=str(workspace_path), template=template_type)
    
    if runner.template_applied:
        print(f"Boilerplate applied: {template_type}")
        file_count = sum(1 for _ in workspace_path.rglob("*") if _.is_file())
        print(f"Template files: {file_count}")
        print("-"*40)
    
    # Run first story
    try:
        result = await runner.run_story(story)
        
        # Update global state for cleanup
        _active_branch = result.get("branch_name") or story.get("story_id", "unknown")
        _active_workspace = workspace_path
        
        print_result(result, workspace_path)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("\nPartial results may be in workspace:")
        print(f"  {workspace_path}")
    
    # Interactive loop
    print_help()
    
    while True:
        try:
            cmd = input("\n[dev_v2] > ").strip()
            
            if not cmd:
                continue
            
            result = await handle_command(cmd, _active_branch, workspace_path)
            
            if result == "run":
                # Run another story
                story = select_story()
                print(f"\nRunning: {story['title']}")
                
                try:
                    result = await runner.run_story(story)
                    _active_branch = result.get("branch_name") or story.get("story_id", "unknown")
                    print_result(result, workspace_path)
                except Exception as e:
                    print(f"Error: {e}")
                    
            elif result is False:
                # Exit
                break
                
        except EOFError:
            # Handle pipe/redirect end
            cleanup_containers(remove=False)
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C in input
            print("\n[!] Interrupted!")
            cleanup_containers(remove=True)
            break
    
    print("\nGoodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Already handled by signal handler
