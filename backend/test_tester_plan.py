"""Test Tester Agent - Plan Step Only.

Usage: cd backend && uv run python test_tester_plan.py

This tests only the plan_tests step without running implementation or tests.
Useful for debugging and validating test planning logic.
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from uuid import UUID, uuid4

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

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3", "git"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Enable tester logs
logging.getLogger("app.agents.tester").setLevel(logging.INFO)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.core.db import engine
from app.models import Project, Story, StoryStatus, Agent as AgentModel


def get_projects_with_tester() -> list[dict]:
    """Get all projects that have a tester agent."""
    with Session(engine) as session:
        projects = session.exec(
            select(Project).where(Project.project_path.isnot(None))
        ).all()
        
        result = []
        for project in projects:
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
                })
        return result


def get_stories_in_review(project_id: str) -> list[dict]:
    """Get stories in REVIEW status."""
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
            }
            for s in stories
        ]


def get_all_stories(project_id: str) -> list[dict]:
    """Get all stories for selection."""
    with Session(engine) as session:
        stories = session.exec(
            select(Story).where(Story.project_id == UUID(project_id))
        ).all()
        
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "status": s.status.value,
            }
            for s in stories
        ]


async def test_plan_only(project_id: str, story_ids: list[str]):
    """Test only the plan_tests step."""
    from app.agents.tester.src.nodes.plan_tests import plan_tests
    from app.agents.tester.src.nodes.setup_workspace import setup_workspace
    from app.agents.tester.src.skills import SkillRegistry
    
    # Get project info
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if not project:
            print(f"[!] Project not found: {project_id}")
            return
        
        tester = session.exec(
            select(AgentModel).where(
                AgentModel.project_id == project.id,
                AgentModel.role_type == "tester"
            )
        ).first()
        
        # Get stories
        stories = []
        for sid in story_ids:
            story = session.get(Story, UUID(sid))
            if story:
                stories.append({
                    "id": str(story.id),
                    "title": story.title,
                    "description": story.description or "",
                    "acceptance_criteria": story.acceptance_criteria or "",
                })
    
    if not stories:
        print("[!] No stories found")
        return
    
    print("\n" + "=" * 60)
    print("TEST PLAN ONLY")
    print("=" * 60)
    print(f"Project: {project.name}")
    print(f"Stories: {len(stories)}")
    for s in stories:
        print(f"  - {s['title']}")
    print("=" * 60)
    
    # Build initial state
    workspace_path = project.project_path
    tech_stack = "nextjs"  # Default
    
    # Try to detect tech stack
    if workspace_path:
        package_json = Path(workspace_path) / "package.json"
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    tech_stack = "nextjs"
                elif "react" in deps:
                    tech_stack = "nodejs-react"
            except:
                pass
    
    print(f"\n[*] Tech stack: {tech_stack}")
    print(f"[*] Workspace: {workspace_path}")
    
    # Load skill registry
    skill_registry = SkillRegistry.load(tech_stack)
    print(f"[*] Loaded {len(skill_registry.skills)} skills")
    
    # Create state for plan_tests
    state = {
        "project_id": project_id,
        "user_id": None,
        "task_id": str(uuid4()),
        "task_type": "write_tests",
        "story_ids": story_ids,
        "user_message": "",
        "is_auto": True,
        "langfuse_handler": None,
        "main_workspace": workspace_path,
        "workspace_path": workspace_path,
        "branch_name": "test_plan_only",
        "workspace_ready": True,
        "tech_stack": tech_stack,
        "skill_registry": skill_registry,
        "stories": stories,  # Key must be "stories" for plan_tests node
        "review_stories": stories,
        "action": "PLAN_TESTS",
    }
    
    print("\n[*] Running plan_tests node...")
    print("-" * 40)
    
    try:
        result = await plan_tests(state, agent=None)
        
        print("\n" + "=" * 60)
        print("PLAN RESULT")
        print("=" * 60)
        
        test_plan = result.get("test_plan", [])
        print(f"\nTotal steps: {len(test_plan)}")
        
        for step in test_plan:
            test_type = step.get("type", "unknown")
            icon = "🧩" if test_type == "unit" else "🔧"
            print(f"\n{step.get('order', '?')}. {icon} {test_type.upper()}")
            print(f"   Story: {step.get('story_title', 'N/A')}")
            print(f"   File: {step.get('file_path', 'N/A')}")
            print(f"   Description: {step.get('description', 'N/A')}")
            print(f"   Skills: {step.get('skills', [])}")
            scenarios = step.get("scenarios", [])
            if scenarios:
                print(f"   Scenarios ({len(scenarios)}):")
                for sc in scenarios[:5]:
                    print(f"     - {sc}")
                if len(scenarios) > 5:
                    print(f"     ... and {len(scenarios) - 5} more")
        
        print("\n" + "=" * 60)
        print(f"Dependencies pre-loaded: {len(result.get('dependencies_content', {}))}")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def select_project() -> str | None:
    """Select project interactively."""
    projects = get_projects_with_tester()
    
    if not projects:
        print("\n[!] No projects found with tester agent")
        return None
    
    print("\nProjects:")
    print("-" * 40)
    for i, p in enumerate(projects, 1):
        print(f"{i}. {p['name']}")
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


def select_stories(project_id: str) -> list[str]:
    """Select stories interactively."""
    stories = get_all_stories(project_id)
    
    if not stories:
        print("\n[!] No stories found")
        return []
    
    print("\nStories:")
    print("-" * 40)
    for i, s in enumerate(stories, 1):
        print(f"{i}. [{s['status']:10}] {s['title']}")
    print()
    
    try:
        choice = input("Select story numbers (comma-separated) or 'review' for REVIEW stories: ").strip()
        
        if choice.lower() == "review":
            review_stories = get_stories_in_review(project_id)
            return [s["id"] for s in review_stories]
        
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        return [stories[i]["id"] for i in indices if 0 <= i < len(stories)]
    except (ValueError, EOFError):
        pass
    
    return []


async def main():
    print("\n" + "=" * 60)
    print("TESTER AGENT - PLAN TEST ONLY")
    print("=" * 60)
    print("Tests only the plan_tests step")
    print()
    
    # Check for command line args
    if len(sys.argv) >= 3:
        project_id = sys.argv[1]
        story_ids = sys.argv[2].split(",")
        print(f"[*] Using CLI args: project={project_id}, stories={story_ids}")
    else:
        # Select project
        project_id = select_project()
        if not project_id:
            return
        
        # Select stories
        story_ids = select_stories(project_id)
        if not story_ids:
            print("[!] No stories selected")
            return
    
    print(f"\n[*] Selected {len(story_ids)} stories")
    
    # Run plan test
    await test_plan_only(project_id, story_ids)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
