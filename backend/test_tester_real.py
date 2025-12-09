"""Tester Agent Real Runner - Simulates Frontend Flow.

Usage: cd backend && uv run python test_tester_real.py

This simulates the exact flow when a story is moved to REVIEW in the frontend:
1. Query stories from DB in REVIEW status
2. Create task context like the router does
3. Run tester agent's handle_task method

Supports:
- Integration tests (API routes, DB operations) → src/__tests__/integration/
- Unit tests (Components, utilities, hooks) → src/__tests__/unit/
"""

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import signal
import sys
import os
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3", "git"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Enable tester logs
tester_logger = logging.getLogger("app.agents.tester")
tester_logger.setLevel(logging.INFO)
tester_logger.propagate = True

logging.getLogger().setLevel(logging.INFO)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.core.db import engine
from app.models import Project, Story, StoryStatus, Agent as AgentModel
from app.kafka.event_schemas import AgentTaskType
from app.agents.core.base_agent import TaskContext


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[!] Interrupted!")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


# =============================================================================
# DATABASE QUERIES (Same as Router)
# =============================================================================

def get_projects_with_tester() -> list[dict]:
    """Get all projects that have a tester agent."""
    with Session(engine) as session:
        projects = session.exec(
            select(Project).where(Project.project_path.isnot(None))
        ).all()
        
        result = []
        for project in projects:
            # Check if project has a tester agent
            tester = session.exec(
                select(AgentModel).where(
                    AgentModel.project_id == project.id,
                    AgentModel.role_type == "tester"
                )
            ).first()
            
            if tester:
                result.append({
                    "id": str(project.id),
                    "name": project.name,
                    "path": project.project_path,
                    "tester_id": str(tester.id),
                    "tester_name": tester.human_name or tester.name,
                })
        
        return result


def get_stories_in_review(project_id: str) -> list[dict]:
    """Get stories in REVIEW status for a project (same query as router)."""
    with Session(engine) as session:
        stories = session.exec(
            select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW
            )
        ).all()
        
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "description": s.description,
                "acceptance_criteria": s.acceptance_criteria,
                "status": s.status.value,
            }
            for s in stories
        ]


def get_all_stories(project_id: str) -> list[dict]:
    """Get all stories for a project."""
    with Session(engine) as session:
        stories = session.exec(
            select(Story).where(Story.project_id == UUID(project_id))
        ).all()
        
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "description": s.description or "",
                "acceptance_criteria": s.acceptance_criteria or "",
                "status": s.status.value,
            }
            for s in stories
        ]


def move_story_to_review(story_id: str) -> bool:
    """Move a story to REVIEW status (simulates frontend action)."""
    with Session(engine) as session:
        story = session.get(Story, UUID(story_id))
        if story:
            old_status = story.status
            old_agent_state = story.agent_state
            story.status = StoryStatus.REVIEW
            story.agent_state = None  # Reset agent_state so tester can process it
            session.add(story)
            session.commit()
            logger.info(f"Moved story '{story.title}' from {old_status.value} to REVIEW (agent_state: {old_agent_state} → None)")
            return True
        return False


def reset_story_agent_state(story_id: str) -> bool:
    """Reset story agent_state to None so it can be reprocessed."""
    with Session(engine) as session:
        story = session.get(Story, UUID(story_id))
        if story:
            old_state = story.agent_state
            story.agent_state = None
            session.add(story)
            session.commit()
            logger.info(f"Reset story '{story.title}' agent_state: {old_state} → None")
            return True
        return False


def get_tester_agent(project_id: str) -> AgentModel | None:
    """Get tester agent model from database."""
    with Session(engine) as session:
        return session.exec(
            select(AgentModel).where(
                AgentModel.project_id == UUID(project_id),
                AgentModel.role_type == "tester"
            )
        ).first()


# =============================================================================
# TESTER RUNNER (Simulates Real Flow)
# =============================================================================

class RealTesterRunner:
    """Runner that simulates the exact flow from frontend.
    
    When story moves to REVIEW:
    1. Router queries tester agent
    2. Router creates TaskContext with trigger_type="status_review"
    3. Tester's handle_task is called with the context
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        
        # Get tester agent from DB
        self.agent_model = get_tester_agent(project_id)
        if not self.agent_model:
            raise ValueError(f"No tester agent found for project {project_id}")
        
        # Initialize actual Tester agent
        from app.agents.tester.tester import Tester
        self.tester = Tester(agent_model=self.agent_model)
        
        logger.info(f"[RealTesterRunner] Initialized")
        logger.info(f"  Project ID: {project_id}")
        logger.info(f"  Tester: {self.agent_model.human_name or self.agent_model.name}")
        logger.info(f"  Workspace: {self.tester.main_workspace}")

    async def run_for_stories_in_review(self) -> dict:
        """Run tester for all stories currently in REVIEW status.
        
        This is exactly what happens when router routes to tester.
        """
        stories = get_stories_in_review(self.project_id)
        
        if not stories:
            print("\n[!] No stories in REVIEW status")
            return {"error": "No stories in REVIEW status"}
        
        print(f"\n[*] Found {len(stories)} stories in REVIEW:")
        for s in stories:
            print(f"    - {s['title']} ({s['id'][:8]}...)")
        
        return await self._run_tester(stories, trigger_type="status_review")

    async def run_for_specific_stories(self, story_ids: list[str]) -> dict:
        """Run tester for specific story IDs."""
        with Session(engine) as session:
            stories = []
            for sid in story_ids:
                story = session.get(Story, UUID(sid))
                if story:
                    stories.append({
                        "id": str(story.id),
                        "title": story.title,
                        "description": story.description or "",
                        "acceptance_criteria": story.acceptance_criteria or "",
                        "status": story.status.value,
                    })
        
        if not stories:
            print("\n[!] No stories found with given IDs")
            return {"error": "Stories not found"}
        
        return await self._run_tester(stories, trigger_type="manual")

    async def _run_tester(self, stories: list[dict], trigger_type: str = "status_review") -> dict:
        """Run tester agent with given stories.
        
        Creates TaskContext exactly like the router does.
        """
        story_ids = [s["id"] for s in stories]
        story_titles = ", ".join(s["title"][:30] for s in stories[:3])
        
        # Create TaskContext exactly like router does
        task = TaskContext(
            task_id=uuid4(),
            task_type=AgentTaskType.WRITE_TESTS,
            priority="high",  # Router sets high priority for story status changes
            user_id=None,  # Auto-triggered, no user
            project_id=UUID(self.project_id),
            routing_reason="story_status_changed_to_review",
            content=f"Auto-generate tests for: {story_titles}",  # Supports both integration and unit tests
            context={
                "trigger_type": trigger_type,
                "story_ids": story_ids,
                "auto_generated": True,
            }
        )
        
        print("\n" + "=" * 60)
        print("SIMULATING: Story moved to REVIEW → Tester triggered")
        print("=" * 60)
        print(f"Task ID: {task.task_id}")
        print(f"Task Type: {task.task_type.value}")
        print(f"Routing Reason: {task.routing_reason}")
        print(f"Stories: {len(stories)}")
        for s in stories:
            print(f"  - [{s['status']}] {s['title']}")
        print("=" * 60)
        print("\n[*] Running tester.handle_task()...\n")
        sys.stdout.flush()
        
        try:
            # Call handle_task exactly like the agent consumer does
            result = await self.tester.handle_task(task)
            
            print("\n[*] handle_task() completed!")
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error_message,
                "structured_data": result.structured_data,
            }
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# =============================================================================
# HELPERS
# =============================================================================

def print_result(result: dict):
    """Print execution result."""
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Success: {result.get('success')}")
    
    if result.get("error"):
        print(f"Error: {result.get('error')}")
    
    structured = result.get("structured_data", {})
    if structured:
        print(f"\nAction: {structured.get('action')}")
        print(f"Run Status: {structured.get('run_status', 'N/A')}")
        print(f"Branch: {structured.get('branch_name', 'N/A')}")
        print(f"Merged: {structured.get('merged', False)}")
        
        files_created = structured.get("files_created", [])
        files_modified = structured.get("files_modified", [])
        all_files = list(set(files_created + files_modified))
        
        if all_files:
            print(f"\nFiles ({len(all_files)}):")
            for f in all_files[:10]:
                print(f"  - {f}")
            if len(all_files) > 10:
                print(f"  ... and {len(all_files) - 10} more")
    
    output = result.get("output", "")
    if output:
        print(f"\nOutput:\n{output[:500]}")
    
    print("=" * 60)


def print_help():
    """Print available commands."""
    print("\n" + "-" * 40)
    print("COMMANDS:")
    print("  review    - Run tester for stories in REVIEW status (like frontend)")
    print("  move      - Move a story to REVIEW then run tester")
    print("  reset     - Reset story agent_state so it can be reprocessed")
    print("  list      - List all stories in project")
    print("  status    - Show current REVIEW stories")
    print("  help      - Show this help")
    print("  exit      - Exit")
    print("-" * 40)


def select_project() -> str | None:
    """Select project interactively."""
    projects = get_projects_with_tester()
    
    if not projects:
        print("\n[!] No projects found with tester agent")
        return None
    
    print("\nProjects with Tester Agent:")
    print("-" * 40)
    for i, p in enumerate(projects, 1):
        print(f"{i}. {p['name']}")
        print(f"   ID: {p['id']}")
        print(f"   Tester: {p['tester_name']}")
        print(f"   Path: {p['path']}")
    print()
    
    try:
        choice = input(f"Select project (1-{len(projects)}) [1]: ").strip() or "1"
        idx = int(choice) - 1
        if 0 <= idx < len(projects):
            return projects[idx]["id"]
    except (ValueError, EOFError):
        pass
    
    return projects[0]["id"] if projects else None


def select_story_to_move(project_id: str) -> str | None:
    """Select a story to move to REVIEW."""
    stories = get_all_stories(project_id)
    
    # Filter out stories already in REVIEW or Done
    movable = [s for s in stories if s["status"] not in ("Review", "Done")]
    
    if not movable:
        print("\n[!] No stories available to move to REVIEW")
        return None
    
    print("\nStories that can be moved to REVIEW:")
    print("-" * 40)
    for i, s in enumerate(movable, 1):
        print(f"{i}. [{s['status']}] {s['title']}")
    print()
    
    try:
        choice = input(f"Select story (1-{len(movable)}): ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(movable):
            return movable[idx]["id"]
    except (ValueError, EOFError):
        pass
    
    return None


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("TESTER AGENT - REAL FLOW SIMULATION")
    print("=" * 60)
    print("Simulates: Story → REVIEW status → Tester auto-triggered")
    print("Press Ctrl+C to exit")
    print()
    
    # Select project
    project_id = select_project()
    if not project_id:
        print("No project selected. Exiting.")
        return
    
    print(f"\nSelected project: {project_id}")
    
    # Create runner
    try:
        runner = RealTesterRunner(project_id)
    except Exception as e:
        print(f"\nError initializing runner: {e}")
        return
    
    # Show help
    print_help()
    
    # Interactive loop
    while True:
        try:
            cmd = input("\n[tester] > ").strip().lower()
            
            if not cmd:
                continue
            
            if cmd == "help" or cmd == "?":
                print_help()
            
            elif cmd == "exit" or cmd == "quit" or cmd == "q":
                break
            
            elif cmd == "list":
                stories = get_all_stories(project_id)
                print(f"\nAll Stories ({len(stories)}):")
                print("-" * 40)
                for s in stories:
                    print(f"  [{s['status']:10}] {s['title']}")
            
            elif cmd == "status":
                stories = get_stories_in_review(project_id)
                if stories:
                    print(f"\nStories in REVIEW ({len(stories)}):")
                    print("-" * 40)
                    for s in stories:
                        print(f"  - {s['title']} ({s['id'][:8]}...)")
                else:
                    print("\n[!] No stories in REVIEW status")
            
            elif cmd == "review":
                # Run for stories already in REVIEW
                result = await runner.run_for_stories_in_review()
                print_result(result)
            
            elif cmd == "move":
                # Select and move a story to REVIEW, then run tester
                story_id = select_story_to_move(project_id)
                if story_id:
                    print(f"\nMoving story to REVIEW...")
                    if move_story_to_review(story_id):
                        print("Story moved to REVIEW!")
                        print("\nNow running tester (simulating router dispatch)...")
                        result = await runner.run_for_specific_stories([story_id])
                        print_result(result)
                    else:
                        print("Failed to move story")
            
            elif cmd == "reset":
                # Reset story agent_state so it can be reprocessed
                stories = get_all_stories(project_id)
                review_stories = [s for s in stories if s["status"] == "Review"]
                
                if not review_stories:
                    print("\n[!] No stories in REVIEW to reset")
                else:
                    print("\nStories in REVIEW:")
                    print("-" * 40)
                    for i, s in enumerate(review_stories, 1):
                        print(f"{i}. {s['title']}")
                    print()
                    
                    try:
                        choice = input(f"Select story to reset (1-{len(review_stories)}): ").strip()
                        idx = int(choice) - 1
                        if 0 <= idx < len(review_stories):
                            story_id = review_stories[idx]["id"]
                            if reset_story_agent_state(story_id):
                                print("Story agent_state reset!")
                                print("\nNow run 'review' to reprocess it.")
                            else:
                                print("Failed to reset story")
                    except (ValueError, EOFError):
                        print("Invalid choice")
            
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
