"""Tester Agent Interactive Runner.

Usage: cd backend && python test_tester_real.py

Test the Tester agent with sample stories or custom input.
"""

# Load environment variables FIRST
from dotenv import load_dotenv

load_dotenv()

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True
)
logger = logging.getLogger(__name__)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Enable tester logs
tester_logger = logging.getLogger("app.agents.tester")
tester_logger.setLevel(logging.INFO)
tester_logger.propagate = True

logging.getLogger().setLevel(logging.INFO)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.tester.src.graph import TesterGraph
from app.agents.tester.src.state import TesterState

# =============================================================================
# SAMPLE STORIES
# =============================================================================

SAMPLE_STORIES = [
    {
        "id": "story-login-001",
        "title": "User Login",
        "description": """
As a user, I want to login to the application so that I can access my account.

Requirements:
- POST /api/auth/login endpoint
- Validate email and password
- Return JWT token on success
- Return 401 on invalid credentials
""",
        "acceptance_criteria": """
- Given valid credentials, when I login, then I receive a JWT token
- Given invalid password, when I login, then I receive 401 error
- Given non-existent email, when I login, then I receive 401 error
""",
    },
    {
        "id": "story-product-002",
        "title": "Create Product",
        "description": """
As an admin, I want to create a new product so that it appears in the catalog.

Requirements:
- POST /api/products endpoint
- Validate product name, price, description
- Only admin can create products
- Return created product with ID
""",
        "acceptance_criteria": """
- Given I am admin, when I create product with valid data, then product is created
- Given I am not admin, when I try to create product, then I receive 403 error
- Given invalid data, when I create product, then I receive 400 error with validation messages
""",
    },
]


# =============================================================================
# TESTER RUNNER
# =============================================================================


class SimpleTesterRunner:
    """Runner for Tester agent without full infrastructure."""

    def __init__(self, project_path: str, project_id: str = None):
        self.name = "Tester"
        self.project_id = project_id or str(uuid4())
        self.project_path = Path(project_path)

        # Verify project exists
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Initialize graph
        self.graph = TesterGraph(agent=self)

        logger.info(f"[{self.name}] Initialized with project: {self.project_path}")

    async def message_user(self, msg_type: str, message: str):
        """Print message to console."""
        print(f"\n[TESTER] {message}")

    async def message_story(
        self, story_id, content: str, message_type: str = "info", details: dict = None
    ):
        """Print story message to console."""
        print(f"\n[STORY {str(story_id)[:8]}] {content}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2)}")

    async def update_story_agent_state(
        self, story_id, new_state: str, progress_message: str = ""
    ):
        """Print state update to console."""
        print(f"\n[STATE] Story {str(story_id)[:8]}: {new_state}")
        if progress_message:
            print(f"  {progress_message[:100]}")

    async def run(self, stories: list = None, user_message: str = None, query_db: bool = False) -> dict:
        """Run tester graph.

        Args:
            stories: List of story dicts to generate tests for
            user_message: Optional user message for conversation mode
            query_db: If True, query stories from DB instead of using provided stories
        """
        # Setup Langfuse if enabled
        langfuse_handler = None
        if os.getenv("ENABLE_LANGFUSE", "false").lower() == "true":
            try:
                from langfuse.langchain import CallbackHandler

                langfuse_handler = CallbackHandler()
                logger.info(f"[{self.name}] Langfuse tracing enabled")
            except Exception as e:
                logger.warning(f"Langfuse setup error: {e}")

        # Determine if auto mode (query DB or use provided stories)
        is_auto = query_db or bool(stories)

        # Build initial state
        initial_state: TesterState = {
            "project_id": self.project_id,
            "user_id": str(uuid4()),
            "task_id": str(uuid4()),
            "task_type": "auto" if is_auto else "message",
            "langfuse_handler": langfuse_handler,
            # Input
            "user_message": user_message or "",
            "story_ids": [s["id"] for s in stories] if stories else [],
            "is_auto": is_auto,
            # Will be populated by router (empty if query_db=True to trigger DB query)
            "stories": [] if query_db else (stories or []),
            "tech_stack": "nextjs",
            # Plan phase
            "test_plan": [],
            "total_steps": 0,
            "current_step": 0,
            # Implement phase
            "files_created": [],
            "files_modified": [],
            # Run phase
            "run_status": None,
            "run_result": {},
            "run_stdout": "",
            "run_stderr": "",
            # Debug
            "debug_count": 0,
            "max_debug": 3,
            "error_analysis": None,
            "debug_history": [],
            # Output
            "message": None,
            "error": None,
        }

        print("\n" + "=" * 60)
        if query_db:
            print(f"RUNNING TESTER: Query DB mode (project_id={self.project_id})")
        elif stories:
            print(f"RUNNING TESTER: {len(stories)} stories")
            for s in stories:
                print(f"  - {s['title']}")
        else:
            print("RUNNING TESTER: Conversation mode")
            print(f"  Message: {user_message}")
        print("=" * 60)
        print("\n[*] Running graph...\n")
        sys.stdout.flush()

        try:
            final_state = await self.graph.graph.ainvoke(
                initial_state, config={"recursion_limit": 50}
            )
            print("\n[*] Graph completed!")
            return final_state

        except Exception as e:
            logger.error(f"[{self.name}] Graph error: {e}", exc_info=True)
            raise


# =============================================================================
# HELPERS
# =============================================================================


def print_result(result: dict, project_path: Path):
    """Print execution result."""
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Action: {result.get('action')}")
    print(f"Run Status: {result.get('run_status', 'N/A')}")
    print(f"Debug Count: {result.get('debug_count', 0)}")

    # Test plan
    test_plan = result.get("test_plan", [])
    if test_plan:
        print(f"\nTest Plan ({len(test_plan)} steps):")
        for step in test_plan:
            print(
                f"  {step.get('order', '?')}. [{step.get('type')}] {step.get('description', 'N/A')[:50]}"
            )

    # Files created
    files_created = result.get("files_created", [])
    if files_created:
        print(f"\nFiles Created ({len(files_created)}):")
        for f in files_created[:10]:
            print(f"  - {f}")
        if len(files_created) > 10:
            print(f"  ... and {len(files_created) - 10} more")

    # Run result
    run_result = result.get("run_result", {})
    if run_result:
        print("\nTest Results:")
        print(f"  Passed: {run_result.get('passed', 0)}")
        print(f"  Failed: {run_result.get('failed', 0)}")

    # Message
    message = result.get("message", "")
    if message:
        print(f"\nMessage:\n{message[:500]}")

    # Error
    error = result.get("error")
    if error:
        print(f"\nError: {error}")

    print("\n" + "-" * 40)
    print(f"PROJECT: {project_path}")


def print_help():
    """Print available commands."""
    print("\n" + "-" * 40)
    print("COMMANDS:")
    print("  run       - Run tester with sample stories (local)")
    print("  db        - Run tester with stories from DB (REVIEW status)")
    print("  custom    - Enter custom story")
    print("  chat      - Chat with tester (conversation mode)")
    print("  status    - Show test files in project")
    print("  help      - Show this help")
    print("  exit      - Exit")
    print("-" * 40)


def list_test_files(project_path: Path):
    """List test files in project."""
    print("\n" + "-" * 40)
    print("TEST FILES:")

    test_patterns = ["**/*.test.ts", "**/*.test.js", "**/*.spec.ts", "**/*.spec.js"]
    test_files = []

    for pattern in test_patterns:
        test_files.extend(project_path.glob(pattern))

    # Filter out node_modules
    test_files = [f for f in test_files if "node_modules" not in str(f)]

    if not test_files:
        print("  No test files found")
    else:
        print(f"  Found {len(test_files)} test files:")
        for f in sorted(test_files)[:20]:
            rel_path = f.relative_to(project_path)
            print(f"  - {rel_path}")
        if len(test_files) > 20:
            print(f"  ... and {len(test_files) - 20} more")
    print("-" * 40)


def select_project() -> Path:
    """Select project path interactively."""
    print("\nEnter project path (or press Enter for demo):")

    # Default demo path
    demo_path = Path(__file__).parent / "app" / "agents" / "tester" / "demo"

    try:
        path_input = input(f"Path [{demo_path}]: ").strip()
    except EOFError:
        path_input = ""

    if not path_input:
        path = demo_path
    else:
        path = Path(path_input)

    if not path.exists():
        print(f"Path does not exist: {path}")
        print("Creating directory...")
        path.mkdir(parents=True, exist_ok=True)

    return path


def enter_custom_story() -> dict:
    """Enter custom story interactively."""
    print("\nEnter custom story:")

    try:
        title = input("Title: ").strip() or "Custom Story"
        description = input("Description: ").strip() or "Custom story description"
        criteria = input("Acceptance Criteria: ").strip() or ""
    except EOFError:
        return None

    return {
        "id": f"custom-{uuid4().hex[:8]}",
        "title": title,
        "description": description,
        "acceptance_criteria": criteria,
    }


# =============================================================================
# MAIN
# =============================================================================


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("TESTER AGENT - INTERACTIVE RUNNER")
    print("=" * 60)
    print("Press Ctrl+C to exit")

    # Select project path
    project_path = select_project()
    print(f"\nProject: {project_path}")

    # Ask for project_id (optional - for DB queries)
    print("\nEnter project_id from DB (or press Enter to skip):")
    try:
        project_id = input("Project ID: ").strip() or None
    except EOFError:
        project_id = None

    if project_id:
        print(f"Using project_id: {project_id}")
    else:
        print("No project_id - will use sample stories only")

    # Create runner
    try:
        runner = SimpleTesterRunner(project_path=str(project_path), project_id=project_id)
    except Exception as e:
        print(f"Error initializing runner: {e}")
        return

    # Interactive loop
    print_help()

    while True:
        try:
            cmd = input("\n[tester] > ").strip().lower()

            if not cmd:
                continue

            if cmd == "help" or cmd == "?":
                print_help()

            elif cmd == "exit" or cmd == "quit" or cmd == "q":
                break

            elif cmd == "status":
                list_test_files(project_path)

            elif cmd == "run":
                print("\nRunning with sample stories...")
                try:
                    result = await runner.run(stories=SAMPLE_STORIES)
                    print_result(result, project_path)
                except Exception as e:
                    print(f"Error: {e}")

            elif cmd == "db":
                if not project_id:
                    print("Error: No project_id provided. Restart and enter a project_id.")
                    continue
                print("\nQuerying stories from DB (REVIEW status)...")
                try:
                    result = await runner.run(query_db=True)
                    print_result(result, project_path)
                except Exception as e:
                    print(f"Error: {e}")

            elif cmd == "custom":
                story = enter_custom_story()
                if story:
                    print(f"\nRunning with custom story: {story['title']}")
                    try:
                        result = await runner.run(stories=[story])
                        print_result(result, project_path)
                    except Exception as e:
                        print(f"Error: {e}")

            elif cmd == "chat":
                try:
                    message = input("Message: ").strip()
                    if message:
                        result = await runner.run(user_message=message)
                        print_result(result, project_path)
                except EOFError:
                    pass

            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")

        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n[!] Interrupted!")
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
