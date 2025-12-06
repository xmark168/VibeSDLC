"""Developer V2 Interactive Runner.

Usage: cd backend && python run_dev_v2_real.py
Commands: run, test, exec, logs, status, clear, exit
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
from app.agents.developer_v2.src.tools import set_tool_context
from app.agents.developer_v2.src.tools.git_tools import git_create_branch, _git_commit

try:
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None


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
    """Copy boilerplate template to target workspace."""
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
    """Detect template type from story content."""
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
    """Runner for DeveloperV2 without full agent infrastructure."""
    
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
        """Setup git workspace and branch."""
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        
        workspace_ready = False
        
        try:
            if not GIT_AVAILABLE:
                logger.warning(f"[{self.name}] GitPython not installed")
                return {
                    "workspace_path": str(self.workspace_path),
                    "branch_name": branch_name,
                    "main_workspace": str(self.workspace_path),
                    "workspace_ready": False,
                }
            
            # Set tool context for git_tools
            set_tool_context(root_dir=str(self.workspace_path))
            
            # 1. Initialize git if needed
            git_dir = self.workspace_path / ".git"
            if not git_dir.exists():
                repo = Repo.init(str(self.workspace_path))
                logger.info(f"[{self.name}] Git init: {self.workspace_path}")
            else:
                repo = Repo(str(self.workspace_path))
            
            # 2. Initial commit if there are files (from boilerplate)
            if repo.untracked_files or repo.is_dirty():
                result = _git_commit("Initial boilerplate", ".")
                logger.info(f"[{self.name}] Initial commit: {result}")
            
            # 3. Create and checkout feature branch
            result = git_create_branch.invoke({"branch_name": branch_name})
            logger.info(f"[{self.name}] Branch '{branch_name}': {result}")
            
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
        """Get project config based on template type."""
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
        
        return {"tech_stack": {"name": "", "service": []}}
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        langfuse_handler = None
        langfuse_client = None
        
        if os.getenv("ENABLE_LANGFUSE", "false").lower() == "true":
            try:
                from langfuse import Langfuse
                from langfuse.langchain import CallbackHandler
                
                langfuse_client = Langfuse()
                langfuse_handler = CallbackHandler()
                logger.info("Langfuse tracing enabled")
            except Exception as e:
                logger.warning(f"Langfuse setup failed: {e}")
        
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
            "langfuse_handler": langfuse_handler,
            "langfuse_client": langfuse_client,
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
            "files_created": [],
            "files_modified": [],
            "message": None,
            "error": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "run_status": None,
            "test_command": None,
            "debug_count": 0,
            "max_debug": 5,
            "debug_history": [],
            "error_analysis": None,
            "react_mode": True,
            "react_loop_count": 0,
            "max_react_loop": 40,
            "tech_stack": "nextjs" if self.template in ["nextjs", "react"] else "python",
            "skill_registry": None,
            "available_skills": [],
            "project_context": None,
            "agents_md": None,
            "project_config": self._get_project_config(),
            "related_code_context": "",
            # Review
            "review_result": None,
            "review_feedback": None,
            "review_details": None,
            "review_count": 0,
            "total_lbtm_count": 0,
            # Summarize
            "summary": None,
            "todos": None,
            "is_pass": None,
            "summarize_feedback": None,
            "summarize_count": 0,
            "files_reviewed": None,
            "story_summary": None,
        }
        
        logger.info(f"[{self.name}] Starting story: {story.get('title', 'Untitled')}")
        print("\n" + "="*60)
        print(f"STARTING: {story.get('title', 'Untitled')}")
        print("="*60)
        print("\n[*] Running graph... (this may take several minutes)")
        print("[*] Progress will be shown below:\n")
        sys.stdout.flush()
        
        try:
            invoke_config = {"recursion_limit": 100}
            if langfuse_handler:
                invoke_config["callbacks"] = [langfuse_handler]
            
            final_state = await self.graph.graph.ainvoke(
                initial_state,
                config=invoke_config
            )
            print("\n[*] Graph completed!")
            
            # Flush Langfuse
            if langfuse_client:
                try:
                    langfuse_client.flush()
                    logger.info("Langfuse flushed")
                except Exception as e:
                    logger.warning(f"Langfuse flush error: {e}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph error: {e}", exc_info=True)
            if langfuse_client:
                try:
                    langfuse_client.flush()
                except Exception:
                    pass
            raise


# =============================================================================
# STORY DEFINITIONS (Standard Format)
# =============================================================================

HOMEPAGE_STORY = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "title": "Homepage with Featured Books",
    "description": """As a first-time visitor, I want to see a clear homepage layout with featured books so that I can quickly understand what the bookstore offers and start browsing.

Create the foundational homepage that serves as the entry point for all customers. This page must establish trust, showcase the bookstore's offerings, and provide clear navigation paths. The homepage should highlight popular textbooks, display trust indicators (return policy, genuine books guarantee), and make the search functionality immediately accessible. This is the first impression that determines whether visitors will continue shopping or leave.""",
    "requirements": [
        "Display hero section with main value proposition and call-to-action button",
        "Show featured/bestselling textbooks section with book covers, titles, prices, and stock status",
        "Include prominent search bar at the top of the page with placeholder text guiding users",
        "Display trust indicators: return policy (7-14 days), genuine books guarantee, contact information (phone, store address)",
        "Show category navigation menu organized by grade levels (6-12, university) and subjects",
        "Include footer with quick links to policies, about us, and contact information",
        "Ensure responsive design that works on mobile, tablet, and desktop devices",
        "Display loading states for dynamic content and handle empty states gracefully"
    ],
    "acceptance_criteria": [
        "Given a user visits the homepage, When the page loads, Then they see the hero section, featured books (at least 8 items), search bar, and trust indicators within 3 seconds",
        "Given a user views featured books, When they hover over a book, Then they see a visual indication (shadow/border) and can click to view details",
        "Given a user is on mobile device, When they access the homepage, Then all elements are properly sized and the layout adapts to screen width without horizontal scrolling",
        "Given the featured books section is empty, When the page loads, Then display a friendly message 'New books coming soon! Check back later' instead of blank space",
        "Given a user clicks on a category in navigation menu, When the page loads, Then they are directed to the filtered book listing page for that category",
        "Given a user clicks on trust indicators (return policy, guarantee), When clicked, Then they are directed to detailed policy pages with full information"
    ]
}


TEXTBOOK_SEARCH_STORY = {
    "story_id": "EPIC-001-US-002",
    "epic": "EPIC-001",
    "title": "Search Textbooks by Name, Author or Code",
    "description": """As a customer, I want to search for textbooks by name, author or code so that I can quickly find the book I need.

Người dùng có thể sử dụng thanh tìm kiếm để nhập tên sách, tác giả hoặc mã sách và nhận được kết quả phù hợp.""",
    "requirements": [
        "Implement search bar component with debounce (300ms)",
        "Search across textbook name, author, and code fields",
        "Display search results with book cover, title, author, price",
        "Show loading state while searching",
        "Handle empty results with friendly message"
    ],
    "acceptance_criteria": [
        "Given I am on the homepage, When I enter a book name, author or code in the search bar, Then I see a list of matching books with basic information",
        "Given no books match my search, When I submit the search, Then I see a message indicating no results found"
    ]
}


LOGIN_FORM_STORY = {
    "story_id": "EPIC-002-US-001",
    "epic": "EPIC-002",
    "title": "User Login Form",
    "description": """As a user, I want a login form so that I can authenticate to the application.

The login form should provide a secure and user-friendly way for customers to access their accounts.""",
    "requirements": [
        "Email input with validation (required, valid email format)",
        "Password input with show/hide toggle",
        "Remember me checkbox",
        "Submit button with loading state",
        "Forgot password link",
        "Form validation with error messages"
    ],
    "acceptance_criteria": [
        "Given I am on the login page, When I enter invalid email format, Then I see a validation error message",
        "Given I am on the login page, When I click the eye icon on password field, Then the password visibility toggles",
        "Given I have filled valid credentials, When I click submit, Then I see a loading state and the form submits",
        "Given I enter invalid credentials, When the form submits, Then I see an error message"
    ]
}


SIMPLE_CALCULATOR_STORY = {
    "story_id": "EPIC-003-US-001",
    "epic": "EPIC-003",
    "title": "Simple Calculator Module",
    "description": """As a user, I want a simple calculator so that I can perform basic math operations.

Create a Python calculator module with basic arithmetic operations and proper error handling.""",
    "requirements": [
        "Implement add(a, b) function for addition",
        "Implement subtract(a, b) function for subtraction",
        "Implement multiply(a, b) function for multiplication",
        "Implement divide(a, b) function with zero division check",
        "Include comprehensive unit tests"
    ],
    "acceptance_criteria": [
        "Given two numbers, When I call add(2, 3), Then it returns 5",
        "Given two numbers, When I call subtract(5, 3), Then it returns 2",
        "Given two numbers, When I call multiply(4, 5), Then it returns 20",
        "Given two numbers, When I call divide(10, 2), Then it returns 5",
        "Given division by zero, When I call divide(10, 0), Then it returns an error message"
    ]
}


# =============================================================================
# GLOBAL STATE
# =============================================================================

_active_branch = None
_active_workspace = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[!] Interrupted!")
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
    print("  exit    - Exit")
    print("  help    - Show this help")
    print("-"*40)


async def handle_command(cmd: str, branch_name: str, workspace_path: Path) -> bool:
    """Handle interactive command.
    
    Returns:
        True to continue, False to exit
    """
    cmd = cmd.strip().lower()
    
    if cmd == "help" or cmd == "?":
        print_help()
        return True
    
    elif cmd == "exit" or cmd == "quit" or cmd == "q":
        return False
    
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
    print("1. Homepage with Featured Books (React) [DEFAULT]")
    print("2. Textbook Search (React)")
    print("3. Login Form (React)")
    print("4. Simple Calculator (Python)")
    print("5. Custom story (enter your own)")
    print()
    
    try:
        choice = input("Enter choice (1-5) [default=1]: ").strip() or "1"
    except EOFError:
        choice = "1"
    
    if choice == "1":
        return HOMEPAGE_STORY
    elif choice == "2":
        return TEXTBOOK_SEARCH_STORY
    elif choice == "3":
        return LOGIN_FORM_STORY
    elif choice == "4":
        return SIMPLE_CALCULATOR_STORY
    elif choice == "5":
        print("\nEnter your story (standard format):")
        title = input("Title: ").strip()
        description = input("Description: ").strip()
        requirements_input = input("Requirements (comma-separated): ").strip()
        requirements = [r.strip() for r in requirements_input.split(",") if r.strip()]
        return {
            "story_id": f"CUSTOM-{str(uuid4())[:8]}",
            "epic": "CUSTOM",
            "title": title,
            "description": description,
            "requirements": requirements,
            "acceptance_criteria": []
        }
    else:
        print("Invalid choice, using Homepage story")
        return HOMEPAGE_STORY


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
