"""Tester Tools - LangChain tools for test context and execution."""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from uuid import UUID

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_project_path(project_id: str) -> Path | None:
    """Get project path from database."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Project
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            return Path(project.project_path)
    return None


@tool
def get_test_files(project_id: str) -> str:
    """List all test files in the project.
    
    Call this when:
    - Need to see what test files exist
    - User asks about test structure
    - Before analyzing test coverage
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of test files with paths
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        test_patterns = ["**/*.test.ts", "**/*.test.js", "**/*.spec.ts", "**/*.spec.js", "**/test_*.py", "**/*_test.py"]
        test_files = []
        
        for pattern in test_patterns:
            test_files.extend(project_path.glob(pattern))
        
        # Filter out node_modules
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        
        if not test_files:
            return "No test files found in project."
        
        lines = [f"Found {len(test_files)} test files:"]
        for f in sorted(test_files)[:20]:
            rel_path = f.relative_to(project_path)
            lines.append(f"- {rel_path}")
        
        if len(test_files) > 20:
            lines.append(f"... and {len(test_files) - 20} more")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.warning(f"[get_test_files] Error: {e}")
        return f"Error listing test files: {str(e)}"


@tool
def read_test_file(project_id: str, file_path: str) -> str:
    """Read content of a specific test file.
    
    Call this when:
    - Need to see test implementation details
    - User asks about specific tests
    - Analyzing test quality
    
    Args:
        project_id: The project UUID
        file_path: Relative path to test file
        
    Returns:
        Content of the test file (truncated if too long)
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        full_path = project_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"
        
        content = full_path.read_text(encoding='utf-8')
        
        # Truncate if too long
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncated)"
        
        return f"File: {file_path}\n\n{content}"
        
    except Exception as e:
        logger.warning(f"[read_test_file] Error: {e}")
        return f"Error reading file: {str(e)}"


@tool
def get_test_summary(project_id: str) -> str:
    """Get summary of tests: count by type, recent tests.
    
    Call this when:
    - User asks about test coverage or status
    - Need overview of testing state
    - Reporting on test progress
    
    Args:
        project_id: The project UUID
        
    Returns:
        Test summary with counts and types
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        # Count test files by type
        integration_tests = list(project_path.glob("**/integration*.test.*"))
        unit_tests = list(project_path.glob("**/*.test.*"))
        unit_tests = [f for f in unit_tests if f not in integration_tests]
        
        # Filter out node_modules
        integration_tests = [f for f in integration_tests if "node_modules" not in str(f)]
        unit_tests = [f for f in unit_tests if "node_modules" not in str(f)]
        
        # Count test cases in integration tests
        total_test_cases = 0
        for test_file in integration_tests:
            try:
                content = test_file.read_text(encoding='utf-8')
                # Count test('...') or it('...')
                test_cases = len(re.findall(r"(?:test|it)\s*\(['\"]", content))
                total_test_cases += test_cases
            except:
                pass
        
        lines = [
            "Test Summary:",
            f"- Integration test files: {len(integration_tests)}",
            f"- Unit test files: {len(unit_tests)}",
            f"- Total test cases (integration): {total_test_cases}",
        ]
        
        # Recent test files
        all_tests = integration_tests + unit_tests
        if all_tests:
            recent = sorted(all_tests, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            lines.append("\nRecent test files:")
            for f in recent:
                rel = f.relative_to(project_path)
                lines.append(f"- {rel}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.warning(f"[get_test_summary] Error: {e}")
        return f"Error getting test summary: {str(e)}"


@tool
def search_tests(project_id: str, query: str) -> str:
    """Search for tests by name or content.
    
    Call this when:
    - User asks about specific tests (e.g., "tests for login")
    - Need to find tests related to a feature
    - Looking for test patterns
    
    Args:
        project_id: The project UUID
        query: Search term (test name, feature, etc.)
        
    Returns:
        Matching tests with file and line info
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        test_files = list(project_path.glob("**/*.test.*")) + list(project_path.glob("**/*.spec.*"))
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        
        matches = []
        query_lower = query.lower()
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Check if it's a test definition
                        if re.search(r"(?:test|it|describe)\s*\(['\"]", line):
                            rel_path = test_file.relative_to(project_path)
                            matches.append(f"- {rel_path}:{i+1}: {line.strip()[:80]}")
            except:
                pass
        
        if not matches:
            return f"No tests found matching '{query}'"
        
        result = [f"Tests matching '{query}':"]
        result.extend(matches[:15])
        
        if len(matches) > 15:
            result.append(f"... and {len(matches) - 15} more matches")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.warning(f"[search_tests] Error: {e}")
        return f"Error searching tests: {str(e)}"


@tool
def get_stories_in_review(project_id: str) -> str:
    """Get stories currently in REVIEW status that need testing.
    
    Call this when:
    - Need to see what stories need tests
    - User asks about pending test work
    - Before generating tests
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of stories in REVIEW with details
    """
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Story, StoryStatus
        
        with Session(engine) as session:
            stories = session.exec(
                select(Story)
                .where(Story.project_id == UUID(project_id))
                .where(Story.status == StoryStatus.REVIEW)
                .order_by(Story.updated_at.desc())
            ).all()
            
            if not stories:
                return "No stories in REVIEW status."
            
            lines = [f"Stories in REVIEW ({len(stories)}):"]
            for s in stories:
                lines.append(f"- {s.title}")
                if s.acceptance_criteria:
                    lines.append(f"  Criteria: {s.acceptance_criteria[:100]}...")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_stories_in_review] Error: {e}")
        return f"Error fetching stories: {str(e)}"


# ============================================================================
# TEST EXECUTION TOOLS
# ============================================================================

def _detect_test_command(project_path: Path, test_type: str, test_file: str) -> str:
    """Detect the appropriate test command based on project structure."""
    # Check for package.json (Node.js project)
    if (project_path / "package.json").exists():
        try:
            pkg = json.loads((project_path / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            
            # Prefer pnpm, then npm
            runner = "pnpm" if (project_path / "pnpm-lock.yaml").exists() else "npm run"
            
            if test_file:
                # Run specific test file
                return f"{runner} test -- {test_file}"
            elif test_type == "integration" and "test:integration" in scripts:
                return f"{runner} test:integration"
            elif test_type == "unit" and "test:unit" in scripts:
                return f"{runner} test:unit"
            elif "test" in scripts:
                return f"{runner} test"
        except:
            pass
        return "pnpm test" if (project_path / "pnpm-lock.yaml").exists() else "npm test"
    
    # Check for pytest (Python project)
    if (project_path / "pytest.ini").exists() or (project_path / "pyproject.toml").exists():
        if test_file:
            return f"pytest {test_file} -v"
        elif test_type == "integration":
            return "pytest tests/integration -v"
        elif test_type == "unit":
            return "pytest tests/unit -v"
        return "pytest -v"
    
    return "echo 'No test framework detected'"


def _parse_jest_output(stdout: str, stderr: str) -> dict:
    """Parse Jest test output."""
    result = {
        "passed": 0,
        "failed": 0,
        "failed_tests": [],
        "coverage": None,
    }
    
    # Parse test counts
    # Pattern: "Tests: X failed, Y passed, Z total"
    match = re.search(r"Tests:\s*(?:(\d+)\s*failed,\s*)?(\d+)\s*passed", stdout + stderr)
    if match:
        result["failed"] = int(match.group(1) or 0)
        result["passed"] = int(match.group(2) or 0)
    
    # Parse failed test names
    # Pattern: "✕ test name (123ms)"
    failed_matches = re.findall(r"[✕✖]\s+(.+?)\s*\(\d+\s*ms\)", stdout + stderr)
    result["failed_tests"] = failed_matches[:10]  # Limit to 10
    
    # Parse coverage
    # Pattern: "All files | 85.5 | 80.2 | 90.1 | 85.5"
    cov_match = re.search(r"All files\s*\|\s*([\d.]+)", stdout + stderr)
    if cov_match:
        result["coverage"] = f"{cov_match.group(1)}%"
    
    return result


@tool
def run_tests(project_id: str, test_type: str = "all", test_file: str = "") -> str:
    """Run tests and return structured results.
    
    Call this to execute tests in the project and get pass/fail results.
    
    Args:
        project_id: The project UUID
        test_type: Type of tests to run - "all", "integration", or "unit"
        test_file: Specific test file to run (optional, relative path)
        
    Returns:
        JSON string with test results including passed/failed counts and coverage
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return json.dumps({"success": False, "error": "Project path not configured"})
        
        # Build test command
        cmd = _detect_test_command(project_path, test_type, test_file)
        logger.info(f"[run_tests] Executing: {cmd} in {project_path}")
        
        # Execute with timeout
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=180,
                env={**os.environ, "CI": "true", "FORCE_COLOR": "0"}
            )
        except subprocess.TimeoutExpired:
            return json.dumps({
                "success": False,
                "error": "Test execution timed out (180s)",
                "passed": 0,
                "failed": 0
            })
        
        # Parse results
        parsed = _parse_jest_output(result.stdout, result.stderr)
        
        return json.dumps({
            "success": result.returncode == 0,
            "passed": parsed["passed"],
            "failed": parsed["failed"],
            "failed_tests": parsed["failed_tests"],
            "coverage": parsed["coverage"],
            "output": (result.stdout + result.stderr)[-2000:],
            "error": result.stderr[-500:] if result.returncode != 0 else None
        })
        
    except Exception as e:
        logger.error(f"[run_tests] Error: {e}")
        return json.dumps({"success": False, "error": str(e)})


@tool
def create_bug_story(
    project_id: str,
    title: str,
    description: str,
    parent_story_id: str = ""
) -> str:
    """Create an Enabler story for bug fix when tests fail.
    
    Call this when tests fail to create a bug story for developers to fix.
    
    Args:
        project_id: The project UUID
        title: Short title describing the bug (e.g., "Login validation failing")
        description: Detailed description with failing tests and error messages
        parent_story_id: UUID of the original story (optional, for linking)
        
    Returns:
        Confirmation message with created story ID
    """
    try:
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story, StoryType, StoryStatus
        
        with Session(engine) as session:
            story = Story(
                project_id=UUID(project_id),
                type=StoryType.ENABLER_STORY,
                title=f"🐛 Fix: {title}",
                description=description,
                status=StoryStatus.TODO,
                parent_id=UUID(parent_story_id) if parent_story_id else None,
            )
            session.add(story)
            session.commit()
            session.refresh(story)
            
            logger.info(f"[create_bug_story] Created bug story: {story.id}")
            return f"Created bug story '{story.title}' (ID: {story.id}) in Todo"
            
    except Exception as e:
        logger.error(f"[create_bug_story] Error: {e}")
        return f"Error creating bug story: {str(e)}"


# Tool registry
TESTER_TOOLS = [
    get_test_files,
    read_test_file,
    get_test_summary,
    search_tests,
    get_stories_in_review,
]

# Extended tools for test execution
TESTER_EXECUTION_TOOLS = [
    run_tests,
    create_bug_story,
    get_test_files,
    read_test_file,
]


def get_tester_tools():
    """Get list of tools available to Tester for status/conversation."""
    return TESTER_TOOLS


def get_execution_tools():
    """Get tools for test execution and verification."""
    return TESTER_EXECUTION_TOOLS
