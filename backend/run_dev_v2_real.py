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


class SimpleDeveloperRunner:
    """Simple runner for DeveloperV2 without full agent infrastructure."""
    
    def __init__(self, workspace_path: str = None):
        self.name = "DeveloperV2"
        self.role_type = "developer"
        self.project_id = uuid4()
        
        # Create workspace if not provided
        if workspace_path:
            self.workspace_path = Path(workspace_path)
        else:
            self.workspace_path = Path(__file__).parent / "projects" / f"project_{self.project_id}"
        
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize graph
        self.graph = DeveloperGraph(agent=self)
        
        logger.info(f"[{self.name}] Initialized with workspace: {self.workspace_path}")
    
    async def message_user(self, msg_type: str, message: str):
        """Print message to console (handle encoding for Windows)."""
        try:
            print(f"\n{'='*60}")
            print(f"[{self.name}] {msg_type.upper()}")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
        except UnicodeEncodeError:
            # Fallback: remove non-ASCII characters
            import re
            clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
            print(f"\n{'='*60}")
            print(f"[{self.name}] {msg_type.upper()}")
            print(f"{'='*60}")
            print(clean_msg)
            print(f"{'='*60}\n")
    
    async def run_story(self, story: dict) -> dict:
        """Run a story through the graph."""
        
        # Build initial state
        initial_state = {
            "story_id": story.get("story_id", str(uuid4())),
            "story_title": story.get("title", "Untitled"),
            "story_content": story.get("content", ""),
            "acceptance_criteria": story.get("acceptance_criteria", []),
            "project_id": str(self.project_id),
            "task_id": str(uuid4()),
            "user_id": str(uuid4()),
            "langfuse_handler": None,
            
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
            
            # Run code - skip tests for React (no test framework)
            "run_status": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "test_command": ["echo", "Skipping tests"],  # Skip actual tests
            
            # Debug - reduce attempts
            "debug_count": 0,
            "max_debug": 1,  # Only 1 debug attempt
            "debug_history": [],
            "last_debug_file": None,
        }
        
        logger.info(f"[{self.name}] Starting story: {story.get('title', 'Untitled')}")
        print("\n" + "="*60)
        print(f"STARTING: {story.get('title', 'Untitled')}")
        print("="*60)
        
        # Run graph
        final_state = await self.graph.graph.ainvoke(initial_state)
        
        return final_state


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
    
    # Create runner with workspace for learning website
    workspace_name = f"learning_website_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    workspace_path = Path(__file__).parent / "projects" / workspace_name
    runner = SimpleDeveloperRunner(workspace_path=str(workspace_path))
    
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
