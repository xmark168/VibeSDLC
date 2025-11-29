"""Run Developer V2 via Kafka events.

This script:
1. Creates workspace with boilerplate template
2. Fires story event to Kafka
3. Does NOT intervene or mock - lets the real system handle it

Usage:
    cd backend
    python run_dev_v2_kafka.py
"""

import asyncio
import json
import logging
import sys
import os
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES_DIR = Path(__file__).parent / "app" / "agents" / "templates" / "boilerplate"

AVAILABLE_TEMPLATES = {
    "nextjs": "nextjs-boilerplate",
    "react": "nextjs-boilerplate",
    "python": None,
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
    
    try:
        if target_path.exists():
            shutil.rmtree(target_path)
        
        shutil.copytree(source_path, target_path)
        file_count = sum(1 for _ in target_path.rglob("*") if _.is_file())
        logger.info(f"Copied {file_count} files from '{template_dir}' to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy boilerplate: {e}")
        target_path.mkdir(parents=True, exist_ok=True)
        return False


def detect_template_type(story: dict) -> str:
    """Detect which template to use based on story content."""
    title = story.get("title", "").lower()
    content = story.get("content", "").lower()
    combined = f"{title} {content}"
    
    react_keywords = ["react", "nextjs", "next.js", "tsx", "jsx", "component", "tailwind", "website"]
    if any(kw in combined for kw in react_keywords):
        return "nextjs"
    
    python_keywords = ["python", ".py", "pytest", "unittest", "django", "fastapi", "flask"]
    if any(kw in combined for kw in python_keywords):
        return "python"
    
    return "nextjs"


# =============================================================================
# KAFKA EVENT PUBLISHING
# =============================================================================

async def publish_story_event(story: dict, workspace_path: str, project_id: str):
    """Publish story event to Kafka for Developer agent to process."""
    try:
        from app.kafka.producer import KafkaProducerService
        
        producer = KafkaProducerService()
        
        # Create delegation event for Developer agent
        event = {
            "event_type": "STORY_ASSIGNED",
            "story_id": story.get("story_id"),
            "story_title": story.get("title"),
            "story_content": story.get("content"),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": project_id,
            "workspace_path": workspace_path,
            "assigned_to": "developer",
            "timestamp": datetime.now().isoformat(),
        }
        
        await producer.send_message(
            topic="DELEGATION_REQUESTS",
            key=story.get("story_id"),
            value=event
        )
        
        logger.info(f"Published story event to Kafka: {story.get('story_id')}")
        return True
        
    except ImportError as e:
        logger.warning(f"Kafka not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        return False


# =============================================================================
# STORY DEFINITIONS
# =============================================================================

LEARNING_WEBSITE_STORY = {
    "story_id": "learning-001",
    "title": "Create Learning Website with React",
    "content": """
## User Story
As a student, I want a beautiful learning website so that I can browse online courses.

## Requirements
Create a React learning website with these components:

1. **Navbar.tsx** - Navigation bar with logo, nav links, dark mode toggle
2. **HeroSection.tsx** - Hero section with gradient, headline, CTA
3. **CourseCard.tsx** - Course card with thumbnail, title, rating, price
4. **HomePage.tsx** - Main page combining all components

## Tech Stack
- React + TypeScript
- TailwindCSS
- Lucide React icons
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
As a user, I want a simple calculator so that I can perform basic math operations.

## Requirements
Create a Python calculator module with:
1. add(a, b) - Addition
2. subtract(a, b) - Subtraction
3. multiply(a, b) - Multiplication
4. divide(a, b) - Division with zero check

Include unit tests.
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
As a user, I want a login form so that I can authenticate to the application.

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
""",
    "acceptance_criteria": [
        "Email field validates format",
        "Password field has show/hide toggle",
        "Form shows validation errors",
        "Submit button disabled when invalid"
    ]
}


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point - creates workspace and fires Kafka event."""
    
    print("\n" + "="*60)
    print("DEVELOPER V2 - KAFKA EVENT PUBLISHER")
    print("="*60)
    print("\nSelect a story to publish:")
    print("1. Simple Calculator (Python)")
    print("2. Login Form (React)")
    print("3. Learning Website (React) [DEFAULT]")
    print("4. Custom story")
    print()
    
    try:
        choice = input("Enter choice (1-4) [default=3]: ").strip() or "3"
    except EOFError:
        choice = "3"
    
    if choice == "1":
        story = SIMPLE_CALCULATOR_STORY
    elif choice == "2":
        story = LOGIN_FORM_STORY
    elif choice == "3":
        story = LEARNING_WEBSITE_STORY
    elif choice == "4":
        print("\nEnter your story:")
        title = input("Title: ").strip()
        content = input("Description: ").strip()
        story = {
            "story_id": str(uuid4())[:8],
            "title": title,
            "content": content,
            "acceptance_criteria": []
        }
    else:
        print("Invalid choice, using Learning Website")
        story = LEARNING_WEBSITE_STORY
    
    print(f"\nSelected: {story['title']}")
    print("-"*40)
    
    # Detect template type
    template_type = detect_template_type(story)
    print(f"Template: {template_type}")
    
    # Create workspace
    project_id = str(uuid4())
    story_slug = story.get('title', 'project').lower().replace(' ', '_')[:20]
    workspace_name = f"{story_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    workspace_path = Path(__file__).parent / "projects" / workspace_name
    
    # Apply boilerplate
    template_applied = copy_boilerplate(template_type, workspace_path)
    
    print("-"*40)
    print(f"Workspace: {workspace_path}")
    if template_applied:
        file_count = sum(1 for _ in workspace_path.rglob("*") if _.is_file())
        print(f"Template files: {file_count}")
    print("-"*40)
    
    # Publish to Kafka
    print("\nPublishing story event to Kafka...")
    kafka_success = await publish_story_event(
        story=story,
        workspace_path=str(workspace_path),
        project_id=project_id
    )
    
    if kafka_success:
        print("✅ Event published to Kafka successfully!")
        print("\nThe Developer agent will process this story.")
        print("Check the agent logs for progress.")
    else:
        print("⚠️ Kafka not available. Running locally instead...")
        
        # Fallback: Run graph directly without Kafka
        from app.agents.developer_v2.src.graph import DeveloperGraph
        
        # Setup Langfuse tracing
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            langfuse = get_client()
            langfuse_ctx = langfuse.start_as_current_observation(
                as_type="span",
                name="developer_v2_graph"
            )
            langfuse_span = langfuse_ctx.__enter__()
            langfuse_span.update_trace(
                session_id=project_id,
                input={"story": story.get("title", "")[:200]},
                metadata={"agent": "DeveloperV2", "template": template_type}
            )
            langfuse_handler = CallbackHandler()
            print("📊 Langfuse tracing enabled")
        except Exception as e:
            logger.debug(f"Langfuse setup: {e}")
        
        # Create minimal agent mock (no message_user)
        class MinimalAgent:
            name = "DeveloperV2"
            role_type = "developer"
            async def message_user(self, *args, **kwargs):
                pass  # No-op
        
        agent = MinimalAgent()
        graph = DeveloperGraph(agent=agent)
        
        initial_state = {
            "story_id": story.get("story_id"),
            "story_title": story.get("title"),
            "story_content": story.get("content"),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": project_id,
            "task_id": str(uuid4()),
            "workspace_path": str(workspace_path),
            "workspace_ready": True,
            "code_review_k": 1,
            "max_debug": 1,
            "langfuse_handler": langfuse_handler,
        }
        
        print("\nRunning Developer graph...")
        result = await graph.graph.ainvoke(initial_state)
        
        # Close Langfuse span
        if langfuse_span and langfuse_ctx:
            try:
                langfuse_span.update_trace(output={
                    "action": result.get("action"),
                    "files_created": result.get("files_created", []),
                })
                langfuse_ctx.__exit__(None, None, None)
            except Exception:
                pass
        
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        print(f"Action: {result.get('action')}")
        print(f"Files Created: {len(result.get('files_created', []))}")
        print(f"Files Modified: {len(result.get('files_modified', []))}")
        
        files_created = result.get('files_created', [])
        if files_created:
            print("\nFILES CREATED:")
            for f in files_created[:10]:
                file_path = workspace_path / f
                if file_path.exists():
                    print(f"  - {f} ({file_path.stat().st_size} bytes)")
                else:
                    print(f"  - {f}")
    
    print("\n" + "-"*40)
    print(f"WORKSPACE: {workspace_path}")


if __name__ == "__main__":
    asyncio.run(main())
