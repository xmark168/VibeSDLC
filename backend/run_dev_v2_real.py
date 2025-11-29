"""Run Developer V2 with a real task - no mocking.

This script sends a real task to DeveloperV2 and lets it process
with actual LLM calls.

Usage:
    cd backend
    python run_dev_v2_real.py
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
    
    try:
        # Copy entire template directory
        if target_path.exists():
            shutil.rmtree(target_path)
        
        shutil.copytree(source_path, target_path)
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
    
    Note: message_user calls in nodes.py are disabled for this mode.
    """
    
    def __init__(self, workspace_path: str = None, template: str = None):
        self.name = "DeveloperV2"
        self.role_type = "developer"
        self.project_id = uuid4()
        self.template = template
        self.template_applied = False
        
        # Create workspace if not provided
        if workspace_path:
            self.workspace_path = Path(workspace_path)
        else:
            self.workspace_path = Path(__file__).parent / "projects" / f"project_{self.project_id}"
        
        # Apply boilerplate template if specified
        if template:
            self.template_applied = copy_boilerplate(template, self.workspace_path)
            if self.template_applied:
                logger.info(f"[{self.name}] Applied '{template}' boilerplate template")
        else:
            self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize graph (agent=self but message_user is no-op)
        self.graph = DeveloperGraph(agent=self)
        
        logger.info(f"[{self.name}] Initialized with workspace: {self.workspace_path}")
    
    async def message_user(self, msg_type: str, message: str):
        """No-op - message_user calls in nodes.py are disabled."""
        pass  # Disabled for local runner mode
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        
        # Setup Langfuse tracing
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            langfuse = get_client()
            # Create parent span for entire graph execution
            langfuse_ctx = langfuse.start_as_current_observation(
                as_type="span",
                name="developer_v2_graph"
            )
            langfuse_span = langfuse_ctx.__enter__()
            langfuse_span.update_trace(
                user_id=str(uuid4()),
                session_id=str(self.project_id),
                input={"story": story.get("title", "")[:200]},
                metadata={"agent": self.name, "template": self.template}
            )
            langfuse_handler = CallbackHandler()
            logger.info(f"[{self.name}] Langfuse tracing enabled")
        except Exception as e:
            logger.debug(f"Langfuse setup: {e}")
        
        # Build initial state
        initial_state = {
            "story_id": story.get("story_id", str(uuid4())),
            "story_title": story.get("title", "Untitled"),
            "story_content": story.get("content", ""),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": str(self.project_id),
            "task_id": str(uuid4()),
            "user_id": str(uuid4()),
            "langfuse_handler": langfuse_handler,
            
            # Workspace
            "workspace_path": str(self.workspace_path),
            "branch_name": f"story_{story.get('story_id', 'main')[:8]}",
            "main_workspace": str(self.workspace_path),
            "workspace_ready": True,
            "index_ready": False,
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
            "current_step": 0,
            "total_steps": 0,
            "validation_result": None,
            "message": None,
            "confidence": None,
            
            # Code review - reduce iterations for faster completion
            "code_review_k": 1,  # Only 1 review iteration
            "code_review_passed": False,
            "code_review_iteration": 0,
            "code_review_results": [],
            
            # Run code - let detect_test_command figure out the right command
            "run_status": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "test_command": None,  # Auto-detect test framework (pnpm/npm/jest/pytest)
            
            # Debug
            "debug_count": 0,
            "max_debug": 3,  # Allow 3 debug attempts
            "debug_history": [],
            "last_debug_file": None,
        }
        
        logger.info(f"[{self.name}] Starting story: {story.get('title', 'Untitled')}")
        print("\n" + "="*60)
        print(f"STARTING: {story.get('title', 'Untitled')}")
        print("="*60)
        
        try:
            # Run graph
            final_state = await self.graph.graph.ainvoke(initial_state)
            
            # Update Langfuse trace output
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "action": final_state.get("action"),
                        "files_created": final_state.get("files_created", []),
                        "run_status": final_state.get("run_status"),
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return final_state
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph error: {e}", exc_info=True)
            # Cleanup Langfuse on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                except Exception:
                    pass
            raise


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


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point."""
    
    print("\n" + "="*60)
    print("DEVELOPER V2 - REAL TASK RUNNER")
    print("="*60)
    print("\nSelect a story to run:")
    print("1. Simple Calculator (Python)")
    print("2. Login Form (React)")
    print("3. Learning Website (React) [DEFAULT]")
    print("4. Custom story (enter your own)")
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
    
    # Run story
    try:
        result = await runner.run_story(story)
        
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        print(f"Action: {result.get('action')}")
        print(f"Task Type: {result.get('task_type')}")
        print(f"Complexity: {result.get('complexity')}")
        print(f"Files Created: {len(result.get('files_created', []))}")
        print(f"Files Modified: {len(result.get('files_modified', []))}")
        print(f"Code Review: {'PASSED' if result.get('code_review_passed') else 'PENDING'}")
        print(f"Tests: {result.get('run_status', 'N/A')}")
        
        # Show created files
        files_created = result.get('files_created', [])
        if files_created:
            print("\n" + "-"*40)
            print("FILES CREATED:")
            for f in files_created:
                print(f"  - {f}")
                # Check if file exists and show size
                file_path = workspace_path / f
                if file_path.exists():
                    size = file_path.stat().st_size
                    print(f"    ({size} bytes)")
        
        # Show code changes summary
        code_changes = result.get('code_changes', [])
        if code_changes:
            print("\n" + "-"*40)
            print(f"CODE CHANGES: {len(code_changes)} files")
            for change in code_changes[:5]:
                fp = change.get('file_path', 'unknown')
                print(f"  - {fp}")
        
        # Show workspace location
        print("\n" + "-"*40)
        print(f"WORKSPACE: {workspace_path}")
        print("\nTo view the files:")
        print(f"  cd {workspace_path}")
        print("  ls -la")
        
        # If React project, show how to run
        if "react" in story.get('title', '').lower() or "website" in story.get('title', '').lower():
            print("\nTo run the React app:")
            print(f"  cd {workspace_path}")
            print("  npm install")
            print("  npm run dev")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("\nPartial results may be in workspace:")
        print(f"  {workspace_path}")


if __name__ == "__main__":
    asyncio.run(main())
